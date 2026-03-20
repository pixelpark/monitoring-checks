#!/opt/puppetlabs/puppet/bin/ruby

require 'optparse'
require 'open3'
require 'time'

STATES = {
  0 => 'OK',
  1 => 'WARNING',
  2 => 'CRITICAL',
  3 => 'UNKOWN'
}.freeze

options = {
  warning: 90,
  critical: 91
}

OptionParser.new do |opts|
  opts.on('-w WARNING', Integer) { |warning| options[:warning] = warning }
  opts.on('-c CRITICAL', Integer) { |critical| options[:critical] = critical }
end.parse!

# `/bin/dnf list updates` would also show versionlocked packages
check_update, check_update_status = Open3.capture2e('/bin/dnf --quiet --cacheonly check-update')

kernel, = Open3.capture2e('/bin/dnf repoquery --quiet --cacheonly --qf=\'%{name}-%{version}-%{release}.%{arch} %{installtime}\' --installed kernel') # rubocop:disable Style/FormatStringToken
kernel = kernel.lines(chomp: true).to_h { |x| x.split(nil, 2) }.max { |a, b| a[1] <=> b[1] }.last
kernel = Time.parse("#{kernel} UTC")

current = Time.now.utc
threshold_crit = Time.utc(kernel.year, kernel.month, kernel.day, 10, 0, 0) + (options[:critical] * 86_400)
threshold_warn = Time.utc(kernel.year, kernel.month, kernel.day, 10, 0, 0) + (options[:warning] * 86_400)

_, needs_restarting = Open3.capture2e('/usr/bin/needs-restarting --reboothint')

status = if (current >= threshold_crit && check_update_status.exitstatus == 100) || !needs_restarting.success?
           [2, 'CRITICAL']
         elsif current >= threshold_warn && check_update_status.exitstatus == 100
           [1, 'WARNING']
         elsif check_update_status.success?
           [0, 'OK']
         else
           [3, 'UNKOWN']
         end
output = "#{status[1]} -"
output += ' System needs restarting!' unless needs_restarting.success?
output += " Last kernel install: #{kernel}"
output += ", Updates available:\n#{check_update}" unless check_update_status.success?

puts output

exit status[0]
