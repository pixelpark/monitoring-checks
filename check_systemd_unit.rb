#! /opt/puppetlabs/puppet/bin/ruby

require 'optparse'
require 'open3'
require 'json'

STATES = {
  0 => 'OK',
  1 => 'WARNING',
  2 => 'CRITICAL',
  3 => 'UNKOWN'
}.freeze

begin
  options = {
    cgroup: []
  }
  OptionParser.new do |opts|
    opts.on('-u UNIT', '--unit UNIT', String,
            'the unitname for the check') do |unit|
      options[:unit] = unit
    end
    opts.on('-p PROCESS', '--process', String,
            'a cgroup process to check if running',
            'can be used multiple times') do |process|
      options[:cgroup] << process
    end
    opts.on('-h', '--help', 'Prints this help') do
      puts opts
      exit
    end
  end.parse!

  if options[:unit].nil? || options[:unit].empty?
    puts "#{STATES[3]} - No service name has been provided. Nothing to check."
    exit 3
  end

  supported_units = '.service'
  unless options[:unit] =~ /\.service\z/
    puts "#{STATES[3]} - Cannot determine which unit type or unit name is to be checked, as \"#{UNIT}\" does either not contain a unit name or unit type in its name. Supported units are: #{supported_units}"
    exit 3
  end

  messages = []
  stdout, _stderr, _status = Open3.capture3("systemctl list-units --output=json '#{options[:unit]}'")
  unit_status = JSON.parse(stdout)

  if unit_status.empty? || unit_status.none? { |x| x['unit'] == options[:unit] }
    puts "#{STATES[2]} - unit '#{options[:unit]}' not existing"
    exit 2
  end

  _stdout, _stderr, status = Open3.capture3("systemctl --quiet is-enabled '#{options[:unit]}'")
  messages << if status.exitstatus.zero?
                { state: 0, group: :state, message: 'unit is enabled' }
              else
                { state: 1, group: :state, message: 'unit NOT enabled' }
              end

  _stdout, _stderr, status = Open3.capture3("systemctl --quiet is-active '#{options[:unit]}'")
  messages << if status.exitstatus.zero?
                { state: 0, group: :state, message: 'unit is running' }
              else
                { state: 2, group: :state, message: 'unit NOT running' }
              end

  unless options[:cgroup].empty?
    stdout, _stderr, _status = Open3.capture3("systemctl -l -a -n 0 status '#{options[:unit]}'")
    options[:cgroup].each do |x|
      name = x.gsub(%r{(\A.*/| .*\z)}, '')
      messages << if stdout =~ /(├|└)─[[:space:]]*[0-9]+[[:space:]]#{x}([[:cntrl:]]|$)/
                    { state: 0, group: :cproc, message: "CPROC #{name} is running" }
                  else
                    { state: 2, group: :cproc, message: "CPROC #{name} is MISSING" }
                  end
    end
    messages << if messages.select { |x| x[:group] == :cproc }.max_by { |x| x[:state] }[:state].zero?
                  { state: 0, group: :state, message: 'CPROCs are running' }
                else
                  { state: 2, group: :state, message: 'CPROCs are MISSING' }
                end
  end
rescue StandardError => e
  puts "#{STATES[3]} - errors while checking state\n#{e.message}\n#{e.backtrace.join("\n")}"
  exit 3
else
  state = messages.max_by { |x| x[:state] }[:state]
  puts "#{STATES[state]} - unit '#{options[:unit]}' #{messages.select { |x| x[:group] == :state }.sort_by { |x| x[:state] }.reverse.map { |x| x[:message] }.join(', ')}"
  puts messages.select { |x| x[:group] == :cproc }.map { |x| x[:message] }.join("\n")
  exit state
end
