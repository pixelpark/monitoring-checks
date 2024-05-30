#! /opt/puppetlabs/puppet/bin/ruby

# Author: Robert Waffen <robert.waffen@pixelpark.com>
# Date:   2019-08-09

if ['-h', '--help'].include?(ARGV[0])
  puts "Usage: #{$PROGRAM_NAME} Zone Unit"
  puts '---'
  puts 'Zone - Zone Name'
  puts 'Unit - b,k,m,g,t'
  exit 0
end

unless ARGV[0]
  puts 'Error: no Zone given'
  exit 1
end

zone_name = ARGV[0]
unit      = ARGV[1]

divisor = case unit
          when 'm'
            [1024, 'MB']
          when 'g'
            [1024 * 1024, 'GB']
          when 't'
            [1024 * 1024 * 1024, 'TB']
          else
            [1, 'KB']
          end

zone = %x(zoneadm -z #{zone_name} list -p).strip.split(':')
zone_space = %x(df -k #{zone[3]}).lines(chomp: true)[1].strip.split

o_total    = (zone_space[1].to_f / divisor[0]).round(2)
p_total    = zone_space[1]
o_used     = (zone_space[2].to_f / divisor[0]).round(2)
p_used     = zone_space[2]
o_free     = (zone_space[3].to_f / divisor[0]).round(2)
p_free     = zone_space[3]
capacity = zone_space[4]

puts "Status: #{zone[2]} Path: #{zone[3]} Brand: #{zone[5]} IP: #{zone[6]}"
puts "Total: #{o_total} #{divisor[1]} Used: #{o_used} #{divisor[1]} Free: #{o_free} #{divisor[1]} Capacity: #{capacity}"
puts "| Total=#{p_total};;; Used=#{p_used};;; Free=#{p_free};;; Capacity=#{capacity};;;"

exit 0 if zone[2] == 'running'
exit 2 if zone[2] != 'running'
