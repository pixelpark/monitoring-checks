#! /opt/puppetlabs/puppet/bin/ruby

# Author: Robert Waffen <robert.waffen@pixelpark.com>
# Date:   2020-05-15

require 'optparse'

operatingsystem = %x( /opt/puppetlabs/bin/facter operatingsystem ).strip!

if operatingsystem == 'Solaris'
  who_cmd = "gwho"
else
  who_cmd = "who"
end

loggedin = %x( #{who_cmd} | awk '{print $1,$3}' ).strip!

if loggedin.nil?
  loggedin = Array.new
else
  loggedin = loggedin.split(/\n/)
end

date = Time.now.strftime("%Y-%m-%d")
idle_user = []

@options = {}

OptionParser.new do |opts|
  opts.on("-w WARNING")  { |warning|  @options[:warning]  = warning  }
  opts.on("-c CRITICAL") { |critical| @options[:critical] = critical }
  opts.on("-e", TrueClass) { |extended| @options[:extended] = extended.nil? ? true : extended }
end.parse!

warn = @options[:warning].to_i
crit = @options[:critical].to_i
ext  = @options[:extended]

loggedin.each do |user|
  if user.split(' ')[1] != date
    idle_user << user
  end
end unless loggedin.empty?

status = [0, 'OK']       if idle_user.count < warn
status = [1, 'WARNING']  if idle_user.count >= warn
status = [2, 'CRITICAL'] if idle_user.count >= crit

output = "#{status[1]} - Idle Users: #{idle_user.count}" unless ext
output = "#{status[1]} - Idle Users: #{idle_user.count} - Extended: #{idle_user.join(",")}" if ext
perfdata = "loggedin=#{idle_user.count};#{warn};#{crit};"

puts "#{output} | #{perfdata}"

exit status[0]
