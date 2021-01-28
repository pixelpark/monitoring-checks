#! /opt/puppetlabs/puppet/bin/ruby

# Author: Robert Waffen <robert.waffen@pixelpark.com>
#         Frank Brehm <frank.brehm@pixelpark.com>
# Date:   2021-01-27

# ./check_zfs.rb -p rpool -w 70 -c 80 -u g

# OK - rpool
# State: ONLINE
# Errors: No known data errors
# Action:
# Scan: none requested
# Capacity: 65.32% Total: 117.14 GB Used: 76.52 GB Free: 40.62 GB | Capacity=65.32%;70.0;80.0; Total=125778788352;;; Used=82161868288;;; Free=43616920064;;;

require 'optparse'
require 'pp'

Unit = Struct.new(:mu, :o_mu, :divisor)

def find_mu mu
    not_found = ->{ raise "No measuring unit found for mu #{mu}" }
    [ Unit.new('b', '', 1),
      Unit.new('k', 'K', 1024),
      Unit.new('m', 'M', 1024 * 1024),
      Unit.new('g', 'G', 1024 * 1024 * 1024),
      Unit.new('t', 'T', 1024 * 1024 * 1024 * 1024) ].find(not_found) do |u|
          u.mu == mu
    end
end

# Cross-platform way of finding an executable in the $PATH.
#
#   which('ruby') #=> /usr/bin/ruby
def which(cmd)
    std_paths = [ '/bin', '/sbin', '/usr/bin', '/usr/sbin', '/usr/local/bin', '/usr/local/sbin' ]
    exts = ENV['PATHEXT'] ? ENV['PATHEXT'].split(';') : ['']
    ENV['PATH'].split(File::PATH_SEPARATOR).each do |path|
        exts.each do |ext|
            exe = File.join(path, "#{cmd}#{ext}")
            return exe if File.executable?(exe) && !File.directory?(exe)
        end
    end
    std_paths.each do |path|
        exts.each do |ext|
            exe = File.join(path, "#{cmd}#{ext}")
            return exe if File.executable?(exe) && !File.directory?(exe)
        end
    end
    nil
end

class OptparseCheckZfs

    Version = '0.2.4'

    class ScriptOptions

        attr_accessor :verbose, :pools, :warn, :crit, :unit

        def initialize

            self.pools = []
            self.warn = 80.0
            self.crit = 90.0
            self.unit = find_mu('b')
            self.verbose = false

        end

        def define_options(parser)

            parser.accept(Unit) do |mu|
                find_mu mu
            end

            msg = "Nagios/Icinga plugin to check usage of a particular ZFS pool or all ZFS pools."
            msg += "\n\n"
            msg += "Usage: check_zfs.rb [-p POOL] [-w USAGE_PERCENT] [-c USAGE_PERCENT] [-u b|k|m|g|t]"
            parser.banner = msg
            parser.separator ""
            parser.separator "Check options:"

            # add check options
            define_pools(parser)
            define_unit(parser)
            define_warn(parser)
            define_crit(parser)
            boolean_verbose_option(parser)

            parser.separator ""
            parser.separator "Common options:"

            parser.on_tail("-h", "--help", "Show this message") do
                puts parser
                exit 0
            end

            parser.on_tail("-V", "--version", "Show version") do
                puts Version
                exit 0
            end

        end

        def define_pools(parser)
            parser.on("-p", "--pool POOL", Array,
                      "The ZFS pool to check, multiple pools as a comma separated list.",
                      "If not given, all pools are checked.") do |pool|
                # self.pools.push(pool)
                self.pools = pool
            end
        end

        def define_unit(parser)
            parser.on("-u", "--unit UNIT", Unit,
                      'The measuring unit for output of sizes - <b|k|m|g|t>') do |unit|
                self.unit = unit
            end
        end

        def define_warn(parser)
            parser.on("-w", "--warn USAGE_PERCENT", Float,
                      'The warning level of the pool(s) of percent usage.') do |warn|
                self.warn = warn
            end
        end

        def define_crit(parser)
            parser.on("-c", "--crit USAGE_PERCENT", Float,
                      'The critical level of the pool(s) of percent usage.') do |crit|
                self.crit = crit
            end
        end

        def boolean_verbose_option(parser)
            # Boolean switch.
            parser.on("-v", "--[no-]verbose", "Run verbosely") do |v|
                self.verbose = v
            end
        end

    end

    #
    # Return a structure describing the options.
    #
    def parse(args)
        # The options specified on the command line will be collected in
        # *options*.

        @options = ScriptOptions.new
        @args = OptionParser.new do |parser|
            @options.define_options(parser)
            parser.parse!(args)
        end
        @options
    end

    attr_reader :parser, :options

end  # class OptparseExample

checkfs = OptparseCheckZfs.new
options = checkfs.parse(ARGV)
if options.verbose then
    pp options # checkfs.options
end

zpool = which 'zpool'
unless zpool then
    puts "UNKNOWN - Command 'zpool' not found."
    exit 3
end
if options.verbose then
    pp zpool
end

zfs = which 'zfs'
unless zfs then
    puts "UNKNOWN - Command 'zfs' not found."
    exit 3
end
if options.verbose then
    pp zfs
end

if options.pools.empty? then
    pools = %x( #{zpool} list -H | awk '{print $1}' ).strip!.split(/\n/)
    if pools.empty? then
        puts "UNKNOWN - No ZFS pools found."
        exit 3
    end
else
    pools = options.pools
end
if options.verbose then
    pp pools
end


unit = options.unit.o_mu
divisor = options.unit.divisor

output = ''
perfdata = ''
state_total = [0, 'OK']

for pool in pools do

    uhu = %x( #{zpool} list #{pool} >/dev/null 2>&1 )
    unless $?.success? then
        puts "UNKNOWN - ZFS Pool '#{pool}' does not exists."
        exit 3
    end

    pool_values = %x( #{zfs} get -o value -Hp used,available #{pool}).split("\n")
    pool_state  = %x( #{zpool} status #{pool} | grep 'state:'  | awk -F':' '{print $2}' ).strip!
    pool_errors = %x( #{zpool} status #{pool} | grep 'errors:' | awk -F':' '{print $2}' ).strip!
    pool_action = %x( #{zpool} status #{pool} | grep 'action:' | awk -F':' '{print $2}' ).strip!
    pool_scan   = %x( #{zpool} status #{pool} | grep 'scan:'   | sed -e 's/[ 	]*scan://' ).strip!

    zused      = pool_values[0].to_i
    zavailable = pool_values[1].to_i
    ztotal     = zused + zavailable
    zusage     = ((zused.to_f / ztotal.to_f) * 100).round(2)

    if divisor != 1 then
        limit_usage_warn = (ztotal * options.warn / 100 / divisor).round(2)
        limit_usage_crit = (ztotal * options.crit / 100 / divisor).round(2)
    else
        limit_usage_warn = (ztotal * options.warn / 100).round(0)
        limit_usage_crit = (ztotal * options.crit / 100).round(0)
    end

    if state_total[0] < 2 then

        state_total = [1, 'WARNING']  if zusage >= options.warn
        state_total = [2, 'CRITICAL'] if zusage >= options.crit
        state_total = [2, 'CRITICAL'] if pool_state  != 'ONLINE'
        state_total = [2, 'CRITICAL'] if pool_errors != 'No known data errors'

    end

    output += "\n\nZFS Pool '#{pool}'\n"
    output += "State:  #{pool_state}\n"
    output += "Errors: #{pool_errors}\n"
    output += "Action: #{pool_action}\n"
    output += "Scan:   #{pool_scan}\n"
    output += "Usage:  #{zusage}%"

    unless perfdata == '' then
        perfdata += ' '
    end

    if divisor != 1 then
        o_zused      = (zused.to_f / divisor).round(2)
        o_zavailable = (zavailable.to_f / divisor).round(2)
        o_ztotal     = (ztotal.to_f / divisor).round(2)
    else
        o_zused      = zused
        o_zavailable = zavailable
        o_ztotal     = ztotal
    end

    perfdata += "usage_#{pool}=#{zusage}%;#{options.warn};#{options.crit}; "
    perfdata += "total_#{pool}=#{o_ztotal}#{unit};;; "
    perfdata += "used_#{pool}=#{o_zused}#{unit};#{limit_usage_warn};#{limit_usage_crit}; "
    perfdata += "free_#{pool}=#{o_zavailable}#{unit};;;"

end

puts "#{state_total[1]} - Status of ZFS pools#{output} | #{perfdata}"
exit state_total[0]

# vim: ts=4 et
