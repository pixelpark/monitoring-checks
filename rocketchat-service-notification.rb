#!/opt/puppetlabs/puppet/bin/ruby

# Author: Robert Waffen <robert.waffen@pixelpark.com>
# Date:   2020-01-14

require 'net/http'
require 'net/https'
require 'uri'
require 'json'

# get environment variables
icinga2_host   = ENV.fetch('ICINGA_HOST')
rc_webhook     = ENV.fetch('RC_WEBHOOK')

h_display      = ENV.fetch('HOSTDISPLAYNAME')
h_name         = ENV.fetch('HOSTNAME')

s_display      = ENV.fetch('SERVICEDISPLAYNAME')
s_output       = ENV.fetch('SERVICEOUTPUT')
s_state        = ENV.fetch('SERVICESTATE')

n_author       = ENV.fetch('NOTIFICATIONAUTHORNAME')
n_comment      = ENV.fetch('NOTIFICATIONCOMMENT')
n_type         = ENV.fetch('NOTIFICATIONTYPE')

debug          = ENV.fetch('DEBUG')
header         = { 'Content-Type': 'text/json' }
log_file       = '/var/log/icinga2/rocketchat-service-notification.log'
long_date_time = ENV.fetch('LONGDATETIME')

icon = case s_state
  when 'CRITICAL'
    ':rotating_light:'
  when 'WARNING'
    ':warning:'
  when 'OK'
    ':white_check_mark:'
  when 'UNKNOWN'
    ':question:'
  else
    ':white_medium_square:'
end

comment_message = n_comment.empty? ? '' : "*Comment*: #{n_author}: #{n_comment} |"

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
