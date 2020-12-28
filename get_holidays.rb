# Author: Robert Waffen <robert.waffen@pixelpark.com>
# Date:   2019-03-17

require 'date'
require 'json'
require 'net/https'
require 'pp'
require 'uri'
require 'yaml'

# https://calendarific.com/api-documentation
# https://icinga.com/docs/icinga2/latest/doc/03-monitoring-basics/#notifications-users-from-hostservice

api_key = ARGV[0]
year    = ARGV[1]

def get_json(api_key, type, year)
  uri = URI.parse("https://calendarific.com/api/v2/holidays?&api_key=#{api_key}&country=DE&year=#{year}&location=de-be&type=#{type}")
  response = Net::HTTP.get_response(uri)

  if response.code == '200'
    return JSON.load(response.body)
  else
    puts "API Response Code: #{response.code} - #{response}"
    exit 1
  end
end

if api_key.nil?
  puts "Error: You need a api key"
  exit 1
end

if year.nil?
  year = Date.today.year
end

holiday_all      = Array.new
holiday_local    = get_json(api_key, 'local', year)
holiday_national = get_json(api_key, 'national', year)
holiday_object   = { "holiday" => { "display_name" => 'Holidays', "ranges" => { } } }

holiday_local['response']['holidays'].each    { |holiday| holiday_all << holiday['date']['iso'] }
holiday_national['response']['holidays'].each { |holiday| holiday_all << holiday['date']['iso'] }

holiday_all.sort!
holiday_all.each { |holiday| holiday_object['holiday']['ranges'][holiday] = '00:00-24:00' }

holiday_object['holiday']['ranges']["#{year}-12-24"] = '12:00-24:00'
holiday_object['holiday']['ranges']["#{year}-12-31"] = '12:00-24:00'

puts holiday_object.to_yaml
