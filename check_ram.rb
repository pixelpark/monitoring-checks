#! /opt/puppetlabs/puppet/bin/ruby

# Author: Robert Waffen <robert.waffen@pixelpark.com>
# Date:   2020-03-20

require 'optparse'

available       = %x(/opt/puppetlabs/puppet/bin/facter memory.system.available).strip!
available_bytes = %x(/opt/puppetlabs/puppet/bin/facter memory.system.available_bytes).strip!
used            = %x(/opt/puppetlabs/puppet/bin/facter memory.system.used).strip!
used_bytes      = %x(/opt/puppetlabs/puppet/bin/facter memory.system.used_bytes).strip!
total           = %x(/opt/puppetlabs/puppet/bin/facter memory.system.total).strip!
total_bytes     = %x(/opt/puppetlabs/puppet/bin/facter memory.system.total_bytes).strip!

@options = {}

OptionParser.new do |opts|
  opts.on("-w WARNING")  { |warning| @options[:warning] = warning }
  opts.on("-c CRITICAL") { |critical| @options[:critical] = critical }
end.parse!

warn = @options[:warning].to_f
crit = @options[:critical].to_f

used_perc      = ((used_bytes.to_f / total_bytes.to_f) * 100).round(2)
available_perc = ((available_bytes.to_f / total_bytes.to_f) * 100).round(2)

status = [0, 'OK']       if used_perc < warn
status = [1, 'WARNING']  if used_perc >= warn
status = [2, 'CRITICAL'] if used_perc >= crit

output   = "#{status[1]} - RAM: Total: #{total} - Used: #{used} / #{used_perc}% - Available: #{available} / #{available_perc}%"
perfdata = "Used=#{used_bytes};;; Available=#{available_bytes};;;"

puts "#{output} | #{perfdata}"

exit status[0]
