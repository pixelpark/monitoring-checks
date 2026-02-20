#!/opt/puppetlabs/puppet/bin/ruby

# Author: Robert Waffen <rw@betadots.de>
# Date:   2022-06-20

require 'net/https'
require 'uri'
require 'json'
require 'yaml'
require 'optparse'

@options = {
  api_url: 'https://localhost:5665/v1/objects/endpoints',
  timeout: 10
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

  opts.on('-a', '--api-url=API_URL')       { |api_url|     @options[:api_url]     = api_url }
  opts.on('-e', '--endpoint=ENDPOINT')     { |endpoint|    @options[:endpoint]    = endpoint }
  opts.on('-p', '--password=API_PASSWORD') { |password|    @options[:password]    = password }
  opts.on('-u', '--user=API_USER')         { |user|        @options[:user]        = user }
  opts.on('--config_yaml=PATH')            { |config_yaml| @options[:config_yaml] = config_yaml }
  opts.on('--timeout=SECONDS')             { |timeout|     @options[:timeout]     = timeout }
end.parse!

expected_keys = %i[api_url timeout]

raise 'Missing parameters - try --help' if (@options.keys - expected_keys).empty?
raise 'Use --password or --config_yaml, but not both!' if @options.key?(:password) && @options.key?(:config_yaml)

if @options.key?(:config_yaml)
  config   = YAML.load_file(@options[:config_yaml])
  user     = config['user']
  password = config['password']
  api_url  = config['api_url']
  endpoint = config['endpoint']
  timeout  = config['timeout']
else
  user     = @options[:user]
  password = @options[:password]
  api_url  = @options[:api_url]
  endpoint = @options[:endpoint]
  timeout  = @options[:timeout]
end

uri  = URI.parse(api_url)
http = Net::HTTP.new(uri.host, uri.port)
http.use_ssl      = true
http.verify_mode  = OpenSSL::SSL::VERIFY_NONE
http.open_timeout = timeout
request = Net::HTTP::Get.new("#{uri.path}/#{endpoint}")
request.basic_auth(user, password)
response = http.request(request)

all_result_list = []
not_connected_list = []

case response.code
when '404'
  all_result_list << false
  not_connected_list << endpoint
when '200'
  get_endpoint_result = JSON.parse(response.body)

  get_endpoint_result['results'].each do |result|
    all_result_list << result['attrs']['connected']
    not_connected_list << result['attrs']['name'] unless result['attrs']['connected']
  end
else
  raise StandardError, "ERROR #{response.code} - #{response.message}"
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
