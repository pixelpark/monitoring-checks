#!/opt/puppetlabs/puppet/bin/ruby

# Author: Robert Waffen <robert.waffen@pixelpark.com>
# Date:   2020-01-14

require 'net/http'
require 'net/https'
require 'uri'
require 'json'

# get environment variables
icinga2_host   = ENV['ICINGA_HOST']
rc_webhook     = ENV['RC_WEBHOOK']

h_display      = ENV['HOSTDISPLAYNAME']
h_name         = ENV['HOSTNAME']

s_display      = ENV['SERVICEDISPLAYNAME']
s_output       = ENV['SERVICEOUTPUT']
s_state        = ENV['SERVICESTATE']

n_author       = ENV['NOTIFICATIONAUTHORNAME']
n_comment      = ENV['NOTIFICATIONCOMMENT']
n_type         = ENV['NOTIFICATIONTYPE']

debug          = ENV['DEBUG']
header         = {'Content-Type': 'text/json'}
log_file       = '/var/log/icinga2/rocketchat-service-notification.log'
long_date_time = ENV['LONGDATETIME']

case s_state
when "CRITICAL"
  icon = ":rotating_light:"
when "WARNING"
  icon = ":warning:"
when "OK"
  icon = ":white_check_mark:"
when "UNKNOWN"
  icon = ":question:"
else
  icon = ":white_medium_square:"
end

unless n_comment.empty?
  comment_message = "*Comment*: #{n_author}: #{n_comment} |"
else
  comment_message = ''
end

# Send message to Rocket.Chat
payload = {
  text: "#{icon} #{n_type} | * `#{h_display}` - [#{s_display}](https://#{icinga2_host}/monitoring/service/show?host=#{h_name}&service=#{s_display})*: [#{s_state}] | #{comment_message} *Output*: ```#{s_output}```"
}

# write payload to log
File.open(log_file, 'a') do |file|
  file.write("#{long_date_time} PAYLOAD: #{payload.to_json}\n")
end

# Create the HTTP objects
uri = URI.parse(rc_webhook)
https = Net::HTTP.new(uri.host, uri.port)
https.use_ssl = true

# Send the request
req = Net::HTTP::Post.new uri.path
req.set_form_data payload
resp = https.request req

File.open(log_file, 'a') do |file|
  file.write("#{long_date_time} RESPONSE: #{resp.code} - #{resp.body} - #{payload.to_json}\n")
end
