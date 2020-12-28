#! /opt/puppetlabs/puppet/bin/ruby

# Author: Robert Waffen <robert.waffen@pixelpark.com>
# Date:   2020-11-10

# ./check_swap.rb -w 80 -c 90

# OK - SWAP: Total: 8.00 GiB - Used: 627.72 MiB / 7.66% - Available: 7.39 GiB / 92.34% | Used=658210816;;; Available=7931719680;;;

require 'optparse'

available       = %x(/opt/puppetlabs/puppet/bin/facter memory.swap.available).strip!
available_bytes = %x(/opt/puppetlabs/puppet/bin/facter memory.swap.available_bytes).strip!
used            = %x(/opt/puppetlabs/puppet/bin/facter memory.swap.used).strip!
used_bytes      = %x(/opt/puppetlabs/puppet/bin/facter memory.swap.used_bytes).strip!
total           = %x(/opt/puppetlabs/puppet/bin/facter memory.swap.total).strip!
total_bytes     = %x(/opt/puppetlabs/puppet/bin/facter memory.swap.total_bytes).strip!

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

output   = "#{status[1]} - SWAP: Total: #{total} - Used: #{used} / #{used_perc}% - Available: #{available} / #{available_perc}%"
perfdata = "Used=#{used_bytes};;; Available=#{available_bytes};;;"

puts "#{output} | #{perfdata}"

exit status[0]
