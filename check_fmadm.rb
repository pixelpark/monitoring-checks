#! /opt/puppetlabs/puppet/bin/ruby

# Author: Robert Waffen <robert.waffen@pixelpark.com>
# Date:   2019-08-09

fmadm_ouput = %x( sudo /usr/sbin/fmadm faulty -s)

if fmadm_ouput.empty?
  puts "OK - no faults"
  exit 0
else
  puts "CRITICAL - There are faults:"
  puts fmadm_ouput
  exit 2
end
