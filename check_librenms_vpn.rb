#! /opt/puppetlabs/puppet/bin/ruby

# Author: Robert Waffen <robert.waffen@pixelpark.com>
# Date:   2020-07-29

require 'json'
require 'net/http'
require 'optparse'
require 'uri'

def librenms_api(auth_token, librenms_host, query)
  uri = URI("https://#{librenms_host}/#{query}")
  http = Net::HTTP.new(uri.host, uri.port)
  http.use_ssl = true
  request  = Net::HTTP::Get.new(uri.request_uri, {'Accept' => 'application/json', 'X-Auth-Token' => auth_token})
  response = http.request(request)
  JSON.load(response.body)
end

@options = Hash.new

OptionParser.new do |opts|
  opts.on("-n NAME") { |name| @options[:name] = name }
  opts.on("-a AUTH") { |auth| @options[:auth] = auth }
  opts.on("-l LIBRENMS") { |librenms| @options[:librenms] = librenms }
end.parse!

librenms_ports = librenms_api(auth_token = @options[:auth], librenms_host = @options[:librenms], query = "api/v0/ports?columns=ifName,port_id")

librenms_ports['ports'].each do |port|
  if port['ifName'] == @options[:name]
    vpn_status  = librenms_api(auth_token = @options[:auth], query="api/v0/ports/#{port['port_id']}")
    operstatus  = vpn_status['port'][0]['ifOperStatus']
    adminstatus = vpn_status['port'][0]['ifAdminStatus']
    status      = [0, 'OK'] if operstatus == 'up' && adminstatus == 'up'
    status      = [1, 'WARNING'] if adminstatus == 'down'
    status      = [2, 'CRITICAL'] if operstatus  == 'down'
    message     = "ifAdminStatus: #{adminstatus}, ifOperStatus: #{operstatus}"

    puts "#{status[1]} - #{port['ifName']} - #{message}"
    exit status[0]
  end
end
