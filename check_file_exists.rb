#!/opt/puppetlabs/puppet/bin/ruby

require 'optparse'
require 'shellwords'

STATES = {
  0 => 'OK',
  1 => 'WARNING',
  2 => 'CRITICAL',
  3 => 'UNKOWN'
}.freeze

options = {
  file_path: [],
  crit: 1,
  warn: 1,
  showdata: false,
  perfdata: true
}
OptionParser.new do |opts|
  opts.on('-f PATH', '--file PATH', String,
          'File path to check against.',
          'Supports glob syntax and repeated usage.') do |value|
    options[:file_path] << value
  end
  opts.on('-c INTEGER', '--crit INTEGER', Integer,
          'More that this count of files will return critical state.',
          'If 0 or less than warn, state logic is reversed.',
          "Default: #{options[:crit]}") do |value|
    options[:crit] = value
  end
  opts.on('-w INTEGER', '--warn INTEGER', Integer,
          'More than this count of files will return warning state.',
          'If more than crit, state logic is reversed.',
          "Default: #{options[:warn]}") do |value|
    options[:warn] = value
  end
  opts.on('--[no-]showdata', TrueClass,
          "Default: #{options[:showdata]}") do |value|
    options[:showdata] = value
  end
  opts.on('-p', '--[no-]perfdata', TrueClass,
          "Default: #{options[:perfdata]}") do |value|
    options[:perfdata] = value
  end
  opts.on('-h', '--help', 'Prints this help') do
    puts opts
    exit
  end
end.parse!

files = Dir.glob(options[:file_path])

exitstate = if options[:crit] < options[:warn] || options[:crit].zero?
              if files.count <= options[:crit]
                2
              elsif files.count <= options[:warn]
                1
              else
                0
              end
            elsif files.count >= options[:crit]
              2
            elsif files.count >= options[:warn]
              1
            else
              0
            end
result = if files.empty?
           'no matching files found'
         else
           "#{files.count} files found"
         end
result += "|file_count=#{files.count};#{options[:warn]};#{options[:crit]};0" if options[:perfdata]

puts "#{STATES[exitstate]} - #{result}"
puts files.map(&:shellescape).join("\n") if options[:showdata]
exit exitstate
