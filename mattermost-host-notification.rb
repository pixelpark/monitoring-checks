#!/opt/puppetlabs/puppet/bin/ruby

# Author: Robert Waffen <robert.waffen@pixelpark.com>
# Date:   2020-01-10
# Updated by Vasko Mihaylov on 2023-06-26 for Mattermost

require 'net/http'
require 'net/https'
require 'uri'
require 'json'
require 'logger'

# get environment variables
icinga2_host   = ENV['ICINGA_HOST']
rc_webhook     = ENV['MM_WEBHOOK']
h_address      = ENV['HOSTADDRESS']
h_display      = ENV['HOSTDISPLAYNAME']
h_name         = ENV['HOSTNAME']
h_output       = ENV['HOSTOUTPUT']
h_state        = ENV['HOSTSTATE']
n_author       = ENV['NOTIFICATIONAUTHORNAME']
n_comment      = ENV['NOTIFICATIONCOMMENT']
n_type         = ENV['NOTIFICATIONTYPE']
long_date_time = ENV['LONGDATETIME']
debug          = ENV['DEBUG']
header         = {'Content-Type': 'text/json'}
# Create a new logger that writes to your log file
log_file = Logger.new('/var/log/icinga2/mattermost-host-notification.log')

case h_state
when "DOWN"
  icon = ":rotating_light:"
when "UP"
  icon = ":white_check_mark:"
else
  icon = ":white_medium_square:"
end

unless n_comment.empty?
  comment_message = "*Comment*: #{n_author}: #{n_comment} |"
else
  comment_message = ''
end

# Send message to Mattermost.Chat
# payload = {
#   text: "#{icon} #{n_type} | *<https://#{icinga2_host}/monitoring/host/show?host=#{h_name} | #{h_name}>*: [#{h_state}] | #{comment_message} *Output*: ```#{h_output}```"
# }

payload = {
    text: "#{icon} #{n_type} | *<https://#{icinga2_host}/monitoring/host/show?host=#{h_name} | #{h_name}>*: [#{h_state}] | #{comment_message} *Output*:\n```less\n#{h_output}\n```"
}

payload_json = payload.to_json

# Log the payload
log_file.info("Payload: #{payload}")

begin
  # Create the HTTP objects
  uri = URI.parse(rc_webhook)
  https = Net::HTTP.new(uri.host, uri.port)
  https.use_ssl = true

  # Create a new POST request
  req = Net::HTTP::Post.new(uri.path)
  # Set the request body to JSON string
  req.body = payload.to_json
  # Set the 'Content-Type' header to 'application/json'
  req['Content-Type'] = 'application/json'
  # Send the request
  resp = https.request req

  # Log the response
  log_file.info("Response: #{resp.body}")
rescue StandardError => e
  # Log any errors
  log_file.error("Error: #{e.message}")
end
