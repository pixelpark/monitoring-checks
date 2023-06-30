#!/opt/puppetlabs/puppet/bin/ruby

# Author: Robert Waffen <robert.waffen@pixelpark.com>
# Date:   2020-01-10

require 'net/http'
require 'net/https'
require 'uri'
require 'json'

# get environment variables
icinga2_host   = ENV.fetch('ICINGA_HOST')
rc_webhook     = ENV.fetch('RC_WEBHOOK')
h_address      = ENV.fetch('HOSTADDRESS')
h_display      = ENV.fetch('HOSTDISPLAYNAME')
h_name         = ENV.fetch('HOSTNAME')
h_output       = ENV.fetch('HOSTOUTPUT')
h_state        = ENV.fetch('HOSTSTATE')
n_author       = ENV.fetch('NOTIFICATIONAUTHORNAME')
n_comment      = ENV.fetch('NOTIFICATIONCOMMENT')
n_type         = ENV.fetch('NOTIFICATIONTYPE')
long_date_time = ENV.fetch('LONGDATETIME')
debug          = ENV.fetch('DEBUG')
header         = { 'Content-Type': 'text/json' }
log_file       = '/var/log/icinga2/rocketchat-host-notification.log'

icon = case h_state
  when 'DOWN'
    ':rotating_light:'
  when 'UP'
    ':white_check_mark:'
  else
    ':white_medium_square:'
end

comment_message = n_comment.empty? '' : "*Comment*: #{n_author}: #{n_comment} |"

# Send message to Rocket.Chat
payload = {
  text: "#{icon} #{n_type} | *<https://#{icinga2_host}/monitoring/host/show?host=#{h_name} | #{h_name}>*: [#{h_state}] | #{comment_message} *Output*: ```#{h_output}```"
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
