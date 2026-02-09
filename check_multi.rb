#!/opt/puppetlabs/puppet/bin/ruby

require 'optparse'
require 'open3'
require 'etc'

STATES = {
  0 => 'OK',
  1 => 'WARNING',
  2 => 'CRITICAL',
  3 => 'UNKOWN'
}.freeze

options = {
  check: [],
  processes: Etc.nprocessors
}
OptionParser.new do |opts|
  opts.on('--check CHECK', String,
          'Check with full path and all parameters',
          'Use multiple times') do |check|
    options[:check] << check
  end
  opts.on('-p PROCESSES', Integer,
          'Count of paralell processes started at the same time',
          "Default is #{Etc.nprocessors} (ruby active usable cpu count)",
          'Note that always one group of checks must be finished before a the next one will be starting.') do |processes|
    options[:processes] << processes
  end
  opts.on('-h', '--help', 'Prints this help') do
    puts opts
    exit
  end
end.parse!

results = []
queue = Thread::Queue.new
options[:check].each { |check| queue << check }
threads = options[:processes].times.map do
  Thread.new do
    while (check = queue.pop(true))
      stdout_and_stderr_str, status = Open3.capture2e(check)
      results << {
        check: check,
        stdout_and_stderr: stdout_and_stderr_str,
        status: status
      }
    end
  rescue ThreadError
    # do nothing
  end
end
threads.map(&:join)

exitstate = results.map { |i| i[:status].exitstatus }.max

print "#{STATES[exitstate]} - check_multi with "
puts STATES.keys.reverse.map { |state|
  count = results.select { |i| i[:status].exitstatus == state }.count
  "#{count} #{STATES[state].downcase}" unless count <= 0
}.compact.join(', ')
puts results.sort_by { |i| [-i[:status].exitstatus, i[:check]] }.map { |i|
  "╠═ '#{i[:check]}'\n║ #{i[:stdout_and_stderr].strip.gsub("\n", "\n║ ")}"
}.join("\n")
exit exitstate
