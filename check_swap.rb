#! /opt/puppetlabs/puppet/bin/ruby

# Author: Robert Waffen <robert.waffen@pixelpark.com>
# Date:   2020-11-10

require 'optparse'
require 'json'

STATES = {
  0 => 'OK',
  1 => 'WARNING',
  2 => 'CRITICAL',
  3 => 'UNKOWN'
}.freeze

@options = {}
OptionParser.new do |opts|
  opts.on('-w WARNING', OptionParser::DecimalNumeric)  { |warning| @options[:warning] = warning.to_f }
  opts.on('-c CRITICAL', OptionParser::DecimalNumeric) { |critical| @options[:critical] = critical.to_f }
end.parse!
if @options[:warning].nil? || @options[:critical].nil?
  puts "#{STATES[3]} - warning and critical thresholds not defined"
  exit 3
end

begin
  facter = JSON.parse(%x(/opt/puppetlabs/puppet/bin/facter --json memory.swap))
rescue StandardError => e
  puts "#{STATES[3]} - errors on collecting memory stats\n#{e.message}"
  exit 3
end

used_perc      = ((facter['memory.swap']['used_bytes'].to_f / facter['memory.swap']['total_bytes']) * 100).round(2)
available_perc = ((facter['memory.swap']['available_bytes'].to_f / facter['memory.swap']['total_bytes']) * 100).round(2)

status = if used_perc >= @options[:critical]
           2
         elsif used_perc >= @options[:warning]
           1
         elsif used_perc < @options[:warning]
           0
         end
output = [
  STATES[status],
  "SWAP: Total: #{facter['memory.swap']['total']}",
  "Used: #{facter['memory.swap']['used']} / #{used_perc}%",
  "Available: #{facter['memory.swap']['available']} / #{available_perc}%"
].join(' - ')
perfdata = [
  "Used=#{facter['memory.swap']['used_bytes']};;;",
  "Available=#{facter['memory.swap']['available_bytes']};;;"
].join(' ')

puts "#{output} | #{perfdata}"
exit status
