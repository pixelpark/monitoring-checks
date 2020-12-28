#! /opt/puppetlabs/puppet/bin/ruby

# Author: Robert Waffen <robert.waffen@pixelpark.com>
# Date:   2019-08-09

# ./check_zfs.rb -p rpool -w 70 -c 80 -u g

# OK - rpool
# State: ONLINE
# Errors: No known data errors
# Action:
# Scan: none requested
# Capacity: 65.32% Total: 117.14 GB Used: 76.52 GB Free: 40.62 GB | Capacity=65.32%;70.0;80.0; Total=125778788352;;; Used=82161868288;;; Free=43616920064;;;

require 'optparse'

@options = {}
OptionParser.new do |opts|
  opts.on("-p", "--pool=POOL") { |pool| @options[:pool] = pool }
  opts.on("-u", "--unit=UNIT") { |unit| @options[:unit] = unit }
  opts.on("-w", "--warn=WARN") { |warn| @options[:warn] = warn }
  opts.on("-c", "--crit=CRIT", 'b,k,m,g,t') { |crit| @options[:crit] = crit }
end.parse!

if not @options[:pool]
  puts 'Error: no Pool_Name given'
  exit 1
end

if not @options[:warn]
  puts 'Error: no Warn_Cap given'
  exit 1
end

if not @options[:crit]
  puts 'Error: no Crit_Cap given'
  exit 1
end

zpool    = @options[:pool]
warn_cap = @options[:warn].to_f
crit_cap = @options[:crit].to_f
unit     = @options[:unit]

case unit
when 'k'
  divisor = [1024, 'KB']
when 'm'
  divisor = [1024 * 1024, 'MB']
when 'g'
  divisor = [1024 * 1024 * 1024, 'GB']
when 't'
  divisor = [1024 * 1024 * 1024 * 1024, 'TB']
else
  divisor = [1, 'Bytes']
end

pool_values = %x( zfs get -o value -Hp used,available #{zpool}).split("\n")
pool_state  = %x( zpool status #{zpool} | grep 'state:'  | awk -F':' '{print $2}' ).strip!
pool_errors = %x( zpool status #{zpool} | grep 'errors:' | awk -F':' '{print $2}' ).strip!
pool_action = %x( zpool status #{zpool} | grep 'action:' | awk -F':' '{print $2}' ).strip!
pool_scan   = %x( zpool status #{zpool} | grep 'scan:'   | awk -F':' '{print $2}' ).strip!

zused      = pool_values[0].to_i
zavailable = pool_values[1].to_i
ztotal     = zused + zavailable
zcapacity  = ((zused.to_f / ztotal.to_f) * 100).round(2)

status = [0, 'OK']       if zcapacity < warn_cap
status = [1, 'WARNING']  if zcapacity >= warn_cap
status = [2, 'CRITICAL'] if zcapacity >= crit_cap
status = [2, 'CRITICAL'] if pool_state  != 'ONLINE'
status = [2, 'CRITICAL'] if pool_errors != 'No known data errors'

o_zused      = (zused.to_f / divisor[0]).round(2)
o_zavailable = (zavailable.to_f / divisor[0]).round(2)
o_ztotal     = (ztotal.to_f / divisor[0]).round(2)

perfdata = "Capacity=#{zcapacity}%;#{warn_cap};#{crit_cap}; Total=#{ztotal};;; Used=#{zused};;; Free=#{zavailable};;;"
pool_capacity = "#{zcapacity}% Total: #{o_ztotal} #{divisor[1]} Used: #{o_zused} #{divisor[1]} Free: #{o_zavailable} #{divisor[1]}"

puts "#{status[1]} - #{zpool}
State: #{pool_state}
Errors: #{pool_errors}
Action: #{pool_action}
Scan: #{pool_scan}
Capacity: #{pool_capacity} | #{perfdata}"

exit status[0]
