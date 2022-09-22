#! /opt/puppetlabs/puppet/bin/ruby

# Author: Robert Waffen <robert.waffen@pixelpark.com>
# Date:   2022-09-22

require 'json'
require 'net/http'
require 'optparse'
require 'uri'
require 'time'
require 'date'

def api_call(query, opt = {})
  protocol     = opt.has_key?(:ssl) ? 'https' : 'http'
  host         = opt[:host] || 'localhost'
  port         = opt[:port] || opt.has_key?(:ssl) ? 8081 : 8080
  uri          = URI("#{protocol}://#{host}:#{port}/#{query}")
  http         = Net::HTTP.new(uri.host, uri.port)
  http.use_ssl = opt.has_key?(:ssl)
  if http.use_ssl?
    require 'openssl/x509'
    require 'openssl/pkey'

    http.ca_file = opt[:ca] if opt.has_key?(:ca)
    if opt.has_key?(:cert) and opt.has_key?(:key)
      http.cert = OpenSSL::X509::Certificate.new(File.read(opt[:cert]))
      http.key  = OpenSSL::PKey::RSA.new(File.read(opt[:key]))
    end
  end

  request  = Net::HTTP::Get.new(uri.request_uri, {'Accept' => 'application/json'})
  response = http.request(request)
  JSON.load(response.body)
end

@options  = Hash.new
@http_opt = Hash.new
OptionParser.new do |opts|
  opts.on('-n NODE', String, 'Node that will be searched for') { |node| @options[:node] = node }
  opts.on('-p PUPPETBOARD', String, 'FQDN of the puppetboard used for the link in the return message.') { |puppetboard| @options[:puppetboard] = puppetboard }
  opts.on('-t TTLSECONDS', Integer, 'Time until the node will be marked as expired.','Check will go critical when 90% of the time has reached.') { |ttl| @options[:ttl] = ttl }
  opts.on('--ssl', 'Enable https usage.') { |ssl| @http_opt[:ssl] = true }
  opts.on('--host HOST', String) { |host| @http_opt[:host] = host }
  opts.on('--port PORT', Integer, 'Used port for connection to puppetdb. Default is 8080.','When ssl is enabled the default is 8081') { |port| @http_opt[:port] = port }
  opts.on('--cert CERT', String, 'Path of the client certificate file that will be used for the connection.') { |cert| @http_opt[:cert] = cert }
  opts.on('--key KEY', String, 'Path of the key file of the client certificate that will be used for the connection.') { |key| @http_opt[:key] = key }
  opts.on('--ca CA', String, 'Path of the ca file that will be used for the connection.') { |ca| @http_opt[:ca] = ca }
  opts.on('-h', '--help', 'Prints this help') do
    puts opts
    exit
  end
end.parse!

puppet_node        = api_call(query="pdb/query/v4/nodes/#{@options[:node]}", @http_opt)
latest_report_hash = puppet_node['latest_report_hash']   || nil # do we have a report for this node?
last_catalog       = puppet_node['catalog_timestamp']    || nil # when was the last catalog for this node compiled?
last_status        = puppet_node['latest_report_status'] || nil # what was the last status from this node?
error              = puppet_node['error']                || nil

if error.nil?
  time_now = Time.now.utc.to_i
  time_cat = Time.parse(last_catalog).to_i
  time_dif = time_now - time_cat
  time_24h = 86400
end

if last_catalog.nil? || latest_report_hash.nil?
  message = 'No catalog found' if error.nil?
  message = error unless error.nil?
  status  = [3, 'UNKNOWN']
else
  if @options.key?(:ttl) && time_dif > ( @options[:ttl] * 0.9 )
    mm, ss = (@options[:ttl] - time_dif).divmod(60)
    hh, mm = mm.divmod(60)
    dd, hh = hh.divmod(24)
    message = "Node will be expire in #{dd} days, #{hh} hours, #{ss} seconds because Puppet hadn't run and a node-ttl of #{@options[:ttl]}s"
    status  = [2, 'CRITICAL']
  elsif time_dif > time_24h
    message = "Puppet hasn't run in 24h! - Last status: #{last_status}"
    message = "Puppet hasn't run in 24h! - Last status: #{last_status}\nPlease check https://#{@options[:puppetboard]}/node/#{@options[:node]}" if last_status == 'failed'
    status  = [1, 'WARNING'] if last_status == 'unchanged'
    status  = [1, 'WARNING'] if last_status == 'changed'
    status  = [2, 'CRITICAL'] if last_status == 'failed'
  else
    message = "Last run at #{Time.parse(last_catalog)} with status: #{last_status}"
    message = "Last run at #{Time.parse(last_catalog)} with status: #{last_status}\nPlease check https://#{@options[:puppetboard]}/node/#{@options[:node]}" if last_status == 'failed'
    status  = [0, 'OK'] if last_status == 'unchanged'
    status  = [0, 'OK'] if last_status == 'changed'
    status  = [2, 'CRITICAL'] if last_status == 'failed'
  end
end

puts "#{status[1]} - #{message}"
exit status[0]
