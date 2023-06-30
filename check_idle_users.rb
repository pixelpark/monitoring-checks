#! /opt/puppetlabs/puppet/bin/ruby

# Author: Robert Waffen <robert.waffen@pixelpark.com>
# Date:   2020-05-15

require 'optparse'

operatingsystem = `/opt/puppetlabs/bin/facter operatingsystem`.strip!
who_cmd = operatingsystem == 'Solaris' ? 'gwho' : 'who'
loggedin = `#{who_cmd} | awk '{print $1,$3}'`.strip!
loggedin = loggedin.nil? ? [] : loggedin.split(/\n/)
date = Time.now.strftime('%Y-%m-%d')
idle_user = []

@options = {}

OptionParser.new do |opts|
  opts.on('-w WARNING')  { |warning|  @options[:warning]  = warning  }
  opts.on('-c CRITICAL') { |critical| @options[:critical] = critical }
  opts.on('-e', TrueClass) { |extended| @options[:extended] = extended.nil? ? true : extended }
end.parse!

warn = @options[:warning].to_i
crit = @options[:critical].to_i
ext  = @options[:extended]

unless loggedin.empty?
  loggedin.each do |user|
    idle_user << user if user.split()[1] != date
  end
end

status = [0, 'OK']       if idle_user.count < warn
status = [1, 'WARNING']  if idle_user.count >= warn
status = [2, 'CRITICAL'] if idle_user.count >= crit

output = "#{status[1]} - Idle Users: #{idle_user.count}" unless ext
output = "#{status[1]} - Idle Users: #{idle_user.count} - Extended: #{idle_user.join(',')}" if ext
perfdata = "loggedin=#{idle_user.count};#{warn};#{crit};"

puts "#{output} | #{perfdata}"

exit status[0]
