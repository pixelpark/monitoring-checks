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

require 'English'
require 'optparse'
require 'date'

STATES = {
  0 => 'OK',
  1 => 'WARNING',
  2 => 'CRITICAL',
  3 => 'UNKOWN'
}.freeze

Unit = Struct.new(:mu, :o_mu, :divisor)

def find_mu(measuring_unit)
  not_found = -> { raise "No measuring unit found for mu #{measuring_unit}" }
  [Unit.new('b', 'B', 1),
   Unit.new('k', 'KB', 1024),
   Unit.new('m', 'MB', 1024 * 1024),
   Unit.new('g', 'GB', 1024 * 1024 * 1024),
   Unit.new('t', 'TB', 1024 * 1024 * 1024 * 1024)].find(not_found) do |u|
    u.mu == measuring_unit
  end
end

# Cross-platform way of finding an executable in the $PATH.
#
#   which('ruby') #=> /usr/bin/ruby
def which(cmd)
  std_paths = ['/bin', '/sbin', '/usr/bin', '/usr/sbin', '/usr/local/bin', '/usr/local/sbin']
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
  VERSION = '0.3.0'.freeze

  class ScriptOptions
    attr_accessor :verbose, :pools, :warn, :crit, :unit, :check_scan

    def initialize
      self.pools = []
      self.warn = 80.0
      self.crit = 90.0
      self.unit = find_mu('b')
      self.check_scan = false
      self.verbose = false
    end

    def define_options(parser)
      parser.accept(Unit) do |measuring_unit|
        find_mu measuring_unit
      end

      msg = "Nagios/Icinga plugin to check usage of a particular ZFS pool or all ZFS pools.\n\n"
      msg += 'Usage: check_zfs.rb [-p POOL] [-w USAGE_PERCENT] [-c USAGE_PERCENT] [-u b|k|m|g|t] [-s]'
      parser.banner = msg
      parser.separator ''
      parser.separator 'Check options:'

      # add check options
      define_pools(parser)
      define_unit(parser)
      define_warn(parser)
      define_crit(parser)
      define_check_scan(parser)
      boolean_verbose_option(parser)

      parser.separator ''
      parser.separator 'Common options:'

      parser.on_tail('-h', '--help', 'Show this message') do
        puts parser
        exit 0
      end

      parser.on_tail('-V', '--version', 'Show version') do
        puts VERSION
        exit 0
      end
    end

    def define_pools(parser)
      parser.on('-p', '--pool POOL', Array,
                'The ZFS pool to check, multiple pools as a comma separated list.',
                'If not given, all pools are checked.') do |pool|
        # self.pools.push(pool)
        self.pools = pool
      end
    end

    def define_unit(parser)
      parser.on('-u', '--unit UNIT', Unit,
                'The measuring unit for output of sizes - <b|k|m|g|t>') do |unit|
        self.unit = unit
      end
    end

    def define_warn(parser)
      parser.on('-w', '--warn USAGE_PERCENT', Float,
                'The warning level of the pool(s) of percent usage.') do |warn|
        self.warn = warn
      end
    end

    def define_crit(parser)
      parser.on('-c', '--crit USAGE_PERCENT', Float,
                'The critical level of the pool(s) of percent usage.') do |crit|
        self.crit = crit
      end
    end

    def define_check_scan(parser)
      parser.on('-s', '--[no-]scan-check',
                'Check if an scan did run in the last 90 days.') do |check|
        self.check_scan = check
      end
    end

    def boolean_verbose_option(parser)
      # Boolean switch.
      parser.on('-v', '--[no-]verbose', 'Run verbosely') do |v|
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
end

def parse_status(input)
  #   pool: z0
  #  state: ONLINE
  # status: One or more devices has experienced an unrecoverable error.  An
  #     attempt was made to correct the error.  Applications are unaffected.
  # action: Determine if the device needs to be replaced, and clear the errors
  #     using 'zpool clear' or replace the device with 'zpool replace'.
  #    see: https://openzfs.github.io/openzfs-docs/msg/ZFS-8000-9P
  # config:
  #
  #     NAME        STATE     READ WRITE CKSUM
  #     z0          ONLINE       0     0     0
  #       sdb       ONLINE       0     2     0
  #
  # errors: No known data errors

  # the first element will is an phantom of the parsing and dropped by [1..]
  parsed = input.split(/(?:\n|^)\s*(\w*):\s*/m)[1..].each_slice(2).to_h
  # cleanup indent and unneeded linebreaks
  parsed = parsed.each do |key, value|
    value = value.split("\n").map(&:strip)
    parsed[key] = case key
                  when 'config'
                    header = value[0].split.map(&:strip)
                    value[1..].map do |line|
                      line.split.map.with_index do |value, index|
                        [header[index], value.strip]
                      end.to_h
                    end
                  else
                    value.join("\n\t")
                  end
  end
rescue StandardError => e
  puts "#{STATES[3]} - Pasing of zfs status failed\n#{e.message}"
  exit 3
end

checkfs = OptparseCheckZfs.new
options = checkfs.parse(ARGV)
pp options if options.verbose # checkfs.options

zpool = which 'zpool'
unless zpool
  puts "#{STATES[3]} - Command 'zpool' not found."
  exit 3
end
pp zpool if options.verbose

zfs = which 'zfs'
unless zfs
  puts "#{STATES[3]} - Command 'zfs' not found."
  exit 3
end
pp zfs if options.verbose

if options.pools.empty?
  pools = %x(#{zpool} list -H -o name).lines(chomp: true)
  if pools.empty?
    puts "#{STATES[3]} - No ZFS pools found."
    exit 3
  end
else
  pools = options.pools
end
pp pools if options.verbose

unit = options.unit.o_mu
divisor = options.unit.divisor

output = ''
perfdata = ''
status = 0
status_msg = 'Status of ZFS pools'

pools.each do |pool|
  pool_status = %x(#{zpool} status #{pool})
  unless $CHILD_STATUS.success?
    puts "#{STATES[3]} - Failed to get status of ZFS Pool '#{pool}'. It may not exist."
    exit 3
  end
  pool_status = parse_status(pool_status)

  zused, zavailable = %x(#{zfs} get -o value -Hp used,available #{pool}).lines(chomp: true).map(&:to_i)
  ztotal = zused + zavailable
  zusage = ((zused.to_f / ztotal) * 100).round(2)

  if divisor == 1
    limit_usage_warn = (ztotal * options.warn / 100).round(0)
    limit_usage_crit = (ztotal * options.crit / 100).round(0)
  else
    limit_usage_warn = (ztotal * options.warn / 100 / divisor).round(2)
    limit_usage_crit = (ztotal * options.crit / 100 / divisor).round(2)
  end

  if options.check_scan
    if !pool_status.key?('scan') || pool_status['scan'].empty?
      status = 2
      status_msg = 'No scan has been run yet.'
    elsif (var = pool_status['scan'].match('\son\s(.*)$'))
      if DateTime.strptime(var[1], '%c') <= (DateTime.now - 90)
        status = 2
        status_msg = 'Last scrub is longer than 90 days ago.'
      end
    elsif (var = pool_status['scan'].match('scrub in progress since (.*)$'))
      if (DateTime.strptime(var[1], '%c') + 1) <= DateTime.now
        status = 2
        status_msg = 'Current scrub is running over an day.'
      end
    else
      status = 3
      status_msg = '"scan" field could not been parsed for a date of last scrub.'
    end
  end

  if status < 2 &&
     (zusage >= options.crit ||
     pool_status['state']  != 'ONLINE' ||
     pool_status['errors'] != 'No known data errors')
    status = 2
  elsif status < 1 &&
        zusage >= options.warn
    status = 1
  elsif status < 1 &&
        ((pool_status.key?('status') && !pool_status['status'].empty?) ||
        (pool_status.key?('action') && !pool_status['action'].empty?))
    status = 1
    status_msg = 'See "status" or "action" field for information.'
  end

  output += "\n\nZFS Pool '#{pool}'\n"
  output += "State:  #{pool_status['state']}\n"
  output += "Errors: #{pool_status['errors']}\n"
  output += "Status: #{pool_status['status']}\n" if pool_status.key?('status')
  output += "Action: #{pool_status['action']}\n" if pool_status.key?('action')
  output += "See:    #{pool_status['see']}\n" if pool_status.key?('see')
  output += "Scan:   #{pool_status['scan']}\n"
  output += "Usage:  #{zusage}%"

  perfdata += ' ' unless perfdata.empty?

  if divisor == 1
    o_zused      = zused
    o_zavailable = zavailable
    o_ztotal     = ztotal
  else
    o_zused      = (zused.to_f / divisor).round(2)
    o_zavailable = (zavailable.to_f / divisor).round(2)
    o_ztotal     = (ztotal.to_f / divisor).round(2)
  end

  perfdata += "usage_#{pool}=#{zusage}%;#{options.warn};#{options.crit}; "
  perfdata += "total_#{pool}=#{o_ztotal}#{unit};;; "
  perfdata += "used_#{pool}=#{o_zused}#{unit};#{limit_usage_warn};#{limit_usage_crit}; "
  perfdata += "free_#{pool}=#{o_zavailable}#{unit};;;"
end

puts "#{STATES[status]} - #{status_msg}#{output} | #{perfdata}"
exit status

# vim: ts=2 et
