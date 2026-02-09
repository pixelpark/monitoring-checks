#!/opt/puppetlabs/puppet/bin/ruby

require 'optparse'
require 'open3'
require 'json'

STATES = {
  0 => 'OK',
  1 => 'WARNING',
  2 => 'CRITICAL',
  3 => 'UNKOWN'
}.freeze

options = {
  warning: 10,
  critical: 20,
  perfdata: true
}
OptionParser.new do |opts|
  opts.on('-c INTEGER', '--critical INTEGER', Integer) do |value|
    options[:critical] = value
  end
  opts.on('-w INTEGER', '--warning INTEGER', Integer) do |value|
    options[:warning] = value
  end
  opts.on('-p', '--[no-]perfdata', TrueClass) do |value|
    options[:perfdata] = value
  end
  opts.on('-h', '--help', 'Prints this help') do
    puts opts
    exit
  end
end.parse!

stdout, stderr, status = Open3.capture3('postqueue -j')
queue_counts = {
  'incoming' => 0,
  'active' => 0,
  'deferred' => 0,
  'bounce' => 0,
  'hold' => 0,
  'corrupt' => 0
}

unless status.success?
  exitstate = 3
  puts "#{STATES[exitstate]} - 'postqueue -j' failed: #{stderr}"
  exit exitstate
end

begin
  queue_counts.merge!(stdout.split("\n").map { |line| JSON.parse(line) }.map { |object| object['queue_name'] }.tally) unless stdout.empty?
rescue StandardError => e
  exitstate = 3
  puts "#{STATES[exitstate]} - unknown error occurred during processing: #{e.message}"
  exit exitstate
end

exitstate = 0
result = queue_counts.sort_by { |_key, value| -value }.to_h.map do |key, value|
  if value >= options[:critical]
    exitstate = 2 unless exitstate > 2
  elsif value >= options[:warning]
    exitstate = 1 unless exitstate > 1
  else
    exitstate = 0 unless exitstate.positive?
  end
  "#{value} #{key}" unless value < 1
end.compact.join(', ')
result = if result.empty?
           'is empty'
         else
           "has #{result}"
         end
result += "|#{queue_counts.map { |key, value| "#{key}=#{value};#{options[:warning]};#{options[:critical]};0" }.join(' ')}" if options[:perfdata]

puts "#{STATES[exitstate]} - postqueue #{result}"
exit exitstate
