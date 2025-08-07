#! /opt/puppetlabs/puppet/bin/ruby

# Author: Robert Waffen <robert.waffen@pixelpark.com>
# Date:   2020-05-15

require 'optparse'
require 'rbconfig'

who_cmd = case RbConfig::CONFIG['host_os']
          when /solaris|sunos/i
            'gwho'
          else
            'who'
          end

loggedin = %x(#{who_cmd}).lines(chomp: true).map do |line|
  line.split.select.with_index do |_, index|
    [0, 2].include?(index)
  end
end

date = Time.now.strftime('%Y-%m-%d')
idle_user = []

@options = {
  warning: 1,
  critical: 1
}

OptionParser.new do |opts|
  opts.on('-w WARNING')    { |warning|  @options[:warning]  = warning  }
  opts.on('-c CRITICAL')   { |critical| @options[:critical] = critical }
  opts.on('-e', TrueClass) { |extended| @options[:extended] = extended.nil? || extended }
end.parse!

warn = @options[:warning].to_i
crit = @options[:critical].to_i
ext  = @options[:extended]

loggedin.each do |entry|
  idle_user << entry.join(' ') unless entry[1] == date
end

status = [0, 'OK']       if idle_user.count < warn
status = [1, 'WARNING']  if idle_user.count >= warn
status = [2, 'CRITICAL'] if idle_user.count >= crit

output = "#{status[1]} - Idle Users: #{idle_user.count}" unless ext
output = "#{status[1]} - Idle Users: #{idle_user.count} - Extended: #{idle_user.join(',')}" if ext
perfdata = "loggedin=#{idle_user.count};#{warn};#{crit};"

puts "#{output} | #{perfdata}"

exit status[0]
