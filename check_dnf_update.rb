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
  critical: 91,
  state_file: '/var/lib/dnf/verify_update_state.log'
}

OptionParser.new do |opts|
  opts.on('-w WARNING', Integer) { |warning| options[:warning] = warning }
  opts.on('-c CRITICAL', Integer) { |critical| options[:critical] = critical }
  opts.on('--state-file PATH', String) { |path| options[:state_file] = path }
end.parse!

last_upgrade = Time.parse('1970-01-01T00:00:00Z')
unless File.readable?(options[:state_file])
  puts "#{status[3]} - state file not existing or readable: #{options[:state_file]}"
  exit 3
end
File.open(options[:state_file], 'r') do |file|
  File.foreach(file) do |line|
    line = line.split
    next unless line[1] == '0'

    break if (last_upgrade = Time.parse(line[0]))
  end
end

current = Time.now.utc
threshold_crit = Time.utc(last_upgrade.year, last_upgrade.month, last_upgrade.day, 0, 0, 0) + (options[:critical] * 86_400)
threshold_warn = Time.utc(last_upgrade.year, last_upgrade.month, last_upgrade.day, 0, 0, 0) + (options[:warning] * 86_400)

# `/bin/dnf list updates` would also show versionlocked packages
check_update, check_update_status = Open3.capture2e('/bin/dnf --quiet --cacheonly check-update')
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
output = status[1]
output += ' - System needs restarting!' unless needs_restarting.success?
output += " - Last upgrade: #{last_upgrade}"
output += "\nUpdates available:\n#{check_update}" unless check_update_status.success?

puts output

exit status[0]
