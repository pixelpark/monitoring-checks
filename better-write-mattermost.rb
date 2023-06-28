#!/opt/puppetlabs/puppet/bin/ruby

# Author: Robert Waffen <robert.waffen@pixelpark.com>
# Date:   2020-04-01
# Updated by Vasko Mihaylov on 2023-06-26 for Mattermost

require 'net/http'
require 'net/https'
require 'uri'
require 'json'
require 'optparse'
require 'logger'

@options = {}

OptionParser.new do |opts|
  opts.on("--custom_message=CUSTOM_MESSAGE")                   { |custom_message|           @options[:custom_message]           = custom_message }
  opts.on("--hostname=HOSTNAME")                               { |hostname|                 @options[:hostname]                 = hostname }
  opts.on("--hostoutput=HOSTOUTPUT")                           { |hostoutput|               @options[:hostoutput]               = hostoutput }
  opts.on("--icinga2_host=ICINGA_HOST")                        { |icinga2_host|             @options[:icinga2_host]             = icinga2_host }
  opts.on("--long_date_time=LONGDATETIME")                     { |long_date_time|           @options[:long_date_time]           = long_date_time }
  opts.on("--notification_author_name=NOTIFICATIONAUTHORNAME") { |notification_author_name| @options[:notification_author_name] = notification_author_name }
  opts.on("--notification_comment=NOTIFICATIONCOMMENT")        { |notification_comment|     @options[:notification_comment]     = notification_comment }
  opts.on("--notification_type=NOTIFICATIONTYPE")              { |notification_type|        @options[:notification_type]        = notification_type }
  opts.on("--mm_webhook=MM_WEBHOOK")                           { |mm_webhook|               @options[:mm_webhook]               = mm_webhook }
  opts.on("--reason=REASON")                                   { |reason|                   @options[:reason]                   = reason }
  opts.on("--servicename=SERVICENAME")                         { |servicename|              @options[:servicename]              = servicename }
  opts.on("--serviceoutput=SERVICEOUTPUT")                     { |serviceoutput|            @options[:serviceoutput]            = serviceoutput }
  opts.on("--state=STATE")                                     { |state|                    @options[:state]                    = state }
  opts.on("--type=TYPE")                                  { |type|                     @options[:type]                     = type }
end.parse!

custom_message           = @options[:custom_message]
hostname                 = @options[:hostname]
hostoutput               = @options[:hostoutput]
# hostoutput               = ENV['HOSTOUTPUT']
icinga2_host             = @options[:icinga2_host]
long_date_time           = @options[:long_date_time]
notification_author_name = @options[:notification_author_name]
notification_comment     = @options[:notification_comment]
notification_type        = @options[:notification_type]
mm_webhook               = @options[:mm_webhook]
reason                   = @options[:reason]
servicename              = @options[:servicename]
serviceoutput            = @options[:serviceoutput]
# serviceoutput            = ENV['SERVICEOUTPUT']
state                    = @options[:state]
type                     = @options[:type]

header                   = {'Content-Type': 'text/json'}
# Create a new logger that writes to log file
logger = Logger.new('/var/log/icinga2/mattermost-better-write.log')

if notification_comment.nil?
  comment_message = ''
else
  comment_message = "*Comment*: #{notification_author_name}: #{notification_comment} |"
end

case type
when "host"
  icon = ":white_medium_square:"
  icon = ":rotating_light:"   if state == 'DOWN'
  icon = ":white_check_mark:" if state == 'UP'
  message = "#{icon} #{notification_type} | *<https://#{icinga2_host}/monitoring/host/show?host=#{hostname} | #{hostname}>*: [#{state}] | #{comment_message} *Output*: ```#{hostoutput}```"
when "service"
  icon = ":white_medium_square:"
  icon = ":rotating_light:"   if state == 'CRITICAL'
  icon = ":warning:"          if state == 'WARNING'
  icon = ":white_check_mark:" if state == 'OK'
  icon = ":question:"         if state == 'UNKNOWN'
  message = "#{icon} #{notification_type} | * `#{hostname}` - [#{servicename}](https://#{icinga2_host}/monitoring/service/show?host=#{hostname}&service=#{servicename})*: [#{state}] | #{comment_message} *Output*: ```#{serviceoutput}```"
when "telefon"
  icon = ":telephone:"
  message = "#{icon} #{type.upcase} | Send call for `#{hostname}`: [#{state}]" if reason == 'host_alert'
  message = "#{icon} #{type.upcase} | Send call for *`#{hostname}` - #{servicename}*: [#{state}]" if reason == 'service_alert'
  message = ":telephone_receiver: #{type.upcase} | Delayed call for `#{hostname}`: [#{state}]" if reason == 'host_delay'
  message = ":telephone_receiver: #{type.upcase} | Delayed call for *`#{hostname}` - #{servicename}*: [#{state}]" if reason == 'service_delay'
when "restart"
  icon = ":recycle:"
  message = "#{icon} #{type.upcase} | Restarting Service *#{servicename}* on `#{hostname}`"
when "custom"
  message = "#{icon} #{type.upcase} | #{custom_message}"
end

payload = {
  icon_emoji: ":icinga:",
  text: message
}

# Log the payload
logger.info("Payload: #{payload.to_json}")

begin
    # Create the HTTP objects
    uri = URI.parse(mm_webhook)
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
    logger.info("Response: #{resp.body}")
  rescue StandardError => e
    # Log any errors
    logger.error("Error: #{e.message}")
end