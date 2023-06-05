# Author: Robert Waffen <robert.waffen@pixelpark.com>
# Date:   2019-03-17

# @example
#   Get all duty definitions without weekend, holidays, christmas and new-year with 09:00 to 18:00.
#     ruby get_holidays.rb --invert --skip-weekday 0 --skip-weekday 6 --day-begin '09:00' --day-end '18:00' \
#       --holiday-date '2023-12-24' --holiday-date '2023-12-31' <API KEY> 2023

require 'date'
require 'json'
require 'net/https'
require 'pp'
require 'uri'
require 'yaml'
require 'optparse'

options = {
  invert: false,
  day_begin: '00:00',
  day_end: '24:00',
  holiday_date: [],
  skip_weekday: [],
  date_range: true,
}
optparse = OptionParser.new do |opts|
  opts.on('--[no-]invert',
    'Get everyday without holidays',
  ) { |i| options[:invert] = i }
  opts.on('--[no-]date-range',
    'Uses date ranges instead of an entry for each day',
  ) { |i| options[:invert] = i }
  opts.on('--holiday-date DATE', String,
    'A holiday date that be added to the list of holidays',
  ) { |date| options[:holiday_date] << Date.parse(date).iso8601 }
  opts.on('--skip-weekday DAY', Integer,
    'A week day that should be skipped in the output',
    'Only relevant in inverted mode.',
  ) { |day| options[:skip_weekday] << day }
  opts.on('--day-begin TIME', String,
    'The time each day range should start',
  ) { |time| options[:day_begin] = time }
  opts.on('--day-end TIME', String,
    'The time each day range should end',
  ) { |time| options[:day_end] = time }
end.parse!

# https://calendarific.com/api-documentation
# https://icinga.com/docs/icinga2/latest/doc/03-monitoring-basics/#notifications-users-from-hostservice

api_key = ARGV[0]
year    = ARGV[1].to_i

def to_date_ranges(a)
  prev = Date.parse(a[0])
  a.slice_before { |e|
    prev, prev2 = Date.parse(e), prev
    prev2.succ != prev
  }.map { |es|
    if es.first == es.last
      es.first
    else
      "#{es.first} - #{es.last}"
    end
  }
end

def get_json(api_key, type, year)
  uri = URI.parse("https://calendarific.com/api/v2/holidays?&api_key=#{api_key}&country=DE&year=#{year}&location=de-be&type=#{type}")
  response = Net::HTTP.get_response(uri)

  return JSON.parse(response.body) if response.code == '200'

  puts "API Response Code: #{response.code} - #{response}"
  exit 1
end

if api_key.nil?
  puts 'Error: You need a api key'
  exit 1
end

year = Date.today.year if year.nil?

holiday_all      = []
holiday_local    = get_json(api_key, 'local', year)
holiday_national = get_json(api_key, 'national', year)

holiday_local['response']['holidays'].each    { |holiday| holiday_all << holiday['date']['iso'] }
holiday_national['response']['holidays'].each { |holiday| holiday_all << holiday['date']['iso'] }

holiday_all.sort!
if options[:invert]
  duty_object = { 'duty' => { 'display_name' => 'Duty plan without holidays', 'ranges' => {} } }

  day_of_year = (Date.new(year) ... Date.new(year).next_year).map { |day|
    if options[:skip_weekday].include?(day.wday)
      nil
    else
      day.iso8601
    end
  }.compact!
  day_of_year -= holiday_all
  day_of_year -= options[:holiday_date]

  day_of_year = to_date_ranges(day_of_year)

  day_of_year.each { |day| duty_object['duty']['ranges'][day] = "#{options[:day_begin]}-#{options[:day_end]}" }

  puts duty_object.to_yaml
else
  holiday_object = { 'holiday' => { 'display_name' => 'Holidays', 'ranges' => {} } }

  holiday_all += options[:holiday_date]
  holiday_all.each { |holiday| holiday_object['holiday']['ranges'][holiday] = "#{options[:day_begin]}-#{options[:day_end]}" }

  puts holiday_object.to_yaml
end
