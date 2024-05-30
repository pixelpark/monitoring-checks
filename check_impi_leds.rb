#! /opt/puppetlabs/puppet/bin/ruby

# Author: Robert Waffen <robert.waffen@pixelpark.com>
# Date:   2019-08-09

system_name = %x(/opt/puppetlabs/bin/facter dmi.product.name).chomp.split.select.with_index do |_, index|
  [1, 2].include?(index)
end.join(' ')

impi_tool = '/usr/bin/ipmitool'     if File.exist?('/usr/bin/ipmitool')
impi_tool = '/usr/sbin/ipmitool'    if File.exist?('/usr/sbin/ipmitool')
impi_tool = '/usr/sfw/bin/ipmitool' if File.exist?('/usr/sfw/bin/ipmitool')
if impi_tool.nil?
  puts 'UNKOWN - Could not found ipmitool binary'
  exit 3
end

sudo = '/usr/bin/sudo' if File.exist?('/usr/bin/sudo')
sudo = '/opt/csw/bin/sudo' if File.exist?('/opt/csw/bin/sudo')
if sudo.nil?
  puts 'UNKOWN - Could not found sudo binary'
  exit 3
end

impi_version = %x(#{impi_tool} -V).strip

case system_name.downcase
when 'blade x6250', 'blade x6270', 'fire x4150', 'fire x4270', 'server x6-2', 'server x7-2'
  led_key        = 'sbled'
  impi_interface = 'bmc'
when 'fire x4100', 'fire x4200', 'fire x4600'
  led_key        = 'led'
  impi_interface = 'bmc'
else
  led_key        = 'sbled'
  impi_interface = 'open'
end

leds = %x(#{sudo} #{impi_tool} -I #{impi_interface} -U root sunoem #{led_key} get 2>/dev/null).lines(chomp: true).grep(/SERVICE/i)

if leds.count { |line| line !~ /OFF/i } == '0'
  puts 'OK - All Service LEDs are Off'
  puts leds
  puts impi_version
  exit 0
else
  puts 'CRITICAL - A Service LED is On'
  puts leds
  puts impi_version
  exit 2
end
