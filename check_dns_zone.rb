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
  warning: 7 * 86_400,
  critical: 4 * 86_400,
  dnssec: true
}

OptionParser.new do |opts|
  opts.on(
    '-w WARNING', String,
    'The threshold for warning about the remaining livetime of the RRSIG.'
  ) { |warning| options[:warning] = timespec(warning) }
  opts.on(
    '-c CRITICAL', String,
    'The threshold for warning about the remaining livetime of the RRSIG.'
  ) { |critical| options[:critical] = timespec(critical) }
  opts.on(
    '-s NAMESERVER', '--server NAMESERVER', String,
    'The nameserver to use for checking the zone.',
    'If omitted, one arbitrary nameserver from /etc/resolv.conf is used.'
  ) { |nameserver| options[:server] = nameserver }
  opts.on(
    '-z ZONE', '--zone ZONE', String,
    'The zone to check. Mandatory option.'
  ) { |zone| options[:zone] = zone }
  opts.on(
    '--[no-]dnssec', TrueClass,
    'Verify DNSSEC resolution and RRSIGN expire.'
  ) { |dnssec| options[:dnssec] = dnssec }
  opts.on_tail('-h', '--help', 'Show this message') do
    puts <<-HELP
      Checks the validity of the given DNS zone by retrieving the SOA for this zone.

      If the option --dnssec is given (default), additionally the DNSSEC RRSIG of the SOA is
      checked for its existence and its remaining livetime.
      Also the full DNSSEC trustchain is checked by using `delv` instead of `dig`.

      The threshold may be given as integers of seconds, or as minutes with the suffix 'm',
      as hours with the suffix 'h' or as days with the suffix 'd'.
    HELP
    puts opts
    puts "Defaults: #{options}"
    exit
  end
end.parse!

if options[:zone].nil?
  puts "#{STATES[3]} - No zone was given"
  exit 3
end
if options[:warning] < options[:critical]
  puts "#{STATES[3]} - The warning threshold (#{options[:warning]} seconds) is less than the critical threshold (#{options[:critical]} seconds), which is weird."
  exit 3
end

### Functions ##################################################################

def timespec(val)
  case val
  when /^(?<value>[0-9])m$/
    value * 60
  when /^(?<value>[0-9])h$/
    value * 3_600
  when /^(?<value>[0-9])d$/
    value * 86_400
  else
    val
  end
end

def humanize(secs)
  [[60, :seconds], [60, :minutes], [24, :hours], [Float::INFINITY, :days]].map do |count, name|
    next unless secs.positive?

    secs, n = secs.divmod(count)
    "#{n.to_i} #{name}" unless n.to_i.zero?
  end.compact.reverse.join(' ')
end

### Main #######################################################################
check = if options[:dnssec]
          "delv \"#{options[:zone]}\" +short +dnssec +vtrace +trust"
        else
          "dig \"#{options[:zone]}\" +short"
        end
check += " \"@#{options[:server]}\" " if options.key?(:server) && !options[:server].nil?
check += ' SOA'

output, _status = Open3.capture2e(check)

vtrace = output.scan(/^;;\s+.*$/)
trust = output.scan(/^;\s+.*$/)
soa = /^(?<mname>[a-zA-Z0-9.-_]+)\s+(?<rname>[a-zA-Z0-9.-_]+)\s+(?<serial>\d+)\s(?<refresh>\d+)\s+(?<retry>\d+)\s+(?<expire>\d+)\s(?<minimum>\d+)$/.match(output)&.named_captures
rrsig = %r{^(?<type>SOA)\s+(?<algo>\d+)\s+(?<labels>\d+)\s+(?<ttl>\d+)\s+(?<expiration>\d+)\s+(?<inception>\d+)\s+(?<key_tag>\d+)\s+(?<signer>[a-zA-Z0-9.-_]+)\s+(?<signature>[a-zA-Z0-9/ +=-]+)$}.match(output)&.named_captures

if soa.nil? || soa.empty?
  puts "#{STATES[2]} - Did not found SOA of zone '#{options[:zone]}'"
  exit 2
elsif !options[:dnssec]
  puts "#{STATES[0]} - Found SOA of zone '#{options[:zone]}'"
  exit 0
end

if rrsig.nil? || rrsig.empty?
  puts "#{STATES[2]} - Missing RRSIG response for SOA of '#{options[:zone]}'"
  exit 2
end

remaining = Time.parse("#{rrsig['expiration']}Z") - Time.now.utc
if remaining <= 0
  puts "#{STATES[2]} - Signatures in zone '#{options[:zone]}' are expired #{humanize(remaining)} ago."
  exit 2
elsif remaining <= options[:critical]
  puts "#{STATES[2]} - Remaining signature validity for zone '#{options[:zone]}' (#{humanize(remaining)}) is less than the critical threshold of #{humanize(options[:critical])}."
  exit 2
elsif trust.none? { |line| /^; fully validated$/.match(line) }
  puts "#{STATES[2]} - DNSSEC validation failed\n#{trust.join("\n")}\n#{vtrace.join("\n")}"
  exit 2
elsif remaining <= options[:warning]
  puts "#{STATES[1]} - Remaining signature validity for zone '#{options[:zone]}' (#{humanize(remaining)}) is less than the warning threshold of #{humanize(options[:warning])}."
  exit 1
end

puts "#{STATES[0]} - Remaining signature validity for zone '#{options[:zone]}' is #{humanize(remaining)}"
exit 0
