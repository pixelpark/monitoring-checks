#!/opt/puppetlabs/puppet/bin/ruby

# Author: Robert Waffen <rw@betadots.de>
# Date:   2022-06-20

require 'net/http'
require 'net/https'
require 'uri'
require 'json'
require 'optparse'

@options = {
  api_url: 'https://localhost:5665/v1/objects/endpoints'
}

usage = [
  'Usage: check_endpoint_connected.rb [options]',
  ' ',
  'Pass -e to check one endpoint, or leave it out to check all endpoints.',
  "Api Url is set to: #{@options[:api_url]}.",
  ' '
]

OptionParser.new do |opts|
  opts.banner = usage.join("\n")

  opts.on('-a', '--api-url=API_URL')   { |api_url|  @options[:api_url]  = api_url }
  opts.on('-e', '--endpoint=ENDPOINT') { |endpoint| @options[:endpoint] = endpoint }
  opts.on('-p', '--password=API_PASSWORD') { |password| @options[:password] = password }
  opts.on('-u', '--user=API_USER')         { |user|     @options[:user]     = user }
end.parse!

get_endpoint_uri = URI.parse(@options[:api_url])

get_endpoint = Net::HTTP.new(get_endpoint_uri.host, get_endpoint_uri.port)
get_endpoint.use_ssl = true
get_endpoint.verify_mode = OpenSSL::SSL::VERIFY_NONE

get_endpoint_req = Net::HTTP::Get.new("#{get_endpoint_uri.path}/#{@options[:endpoint]}")
get_endpoint_req.basic_auth(@options[:user], @options[:password])

get_endpoint_resp = get_endpoint.request(get_endpoint_req)
raise StandardError, "ERROR #{get_endpoint_resp.code} - #{get_endpoint_resp.message}" unless get_endpoint_resp.code == '200'

get_endpoint_result = JSON.parse(get_endpoint_resp.body)

all_result_list = []
not_connected_list = []

get_endpoint_result['results'].each do |result|
  not_connected_list << result['attrs']['name'] unless result['attrs']['connected']
  all_result_list << result['attrs']['connected']
end

# check if all endpoints report connect = true
# a list of booleans give back true if they are ".all?" the same
# and false if there is at least one other value in there
status = if all_result_list.all?
           [0, 'OK']
         else
           [2, 'CRITICAL']
         end

puts "#{status[1]} - All Nodes connected" if all_result_list.all?
puts "#{status[1]} - #{all_result_list.count(false)} Node(s) not connected: #{not_connected_list.join(', ')}" unless all_result_list.all?

exit status[0]
