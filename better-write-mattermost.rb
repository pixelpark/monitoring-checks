#!/opt/puppetlabs/puppet/bin/ruby

require 'net/http'
require 'net/https'
require 'uri'
require 'json'
require 'optparse'
require 'logger'

options = {}

# primary usage is via ENV variables to hide ARGS in ps view
%w[
  HOSTDISPLAYNAME
  HOSTNAME
  SERVICEDISPLAYNAME
  SERVICENAME
  STATE
  OUTPUT
  NOTIFICATIONAUTHORNAME
  NOTIFICATIONCOMMENT
  NOTIFICATIONTYPE
  ICINGA_HOST
  WEBHOOK
].each do |key|
  options[key.downcase.to_sym] = ENV.fetch(key) if ENV.include?(key)
end

OptionParser.new do |opts|
  opts.on('--custom_message=CUSTOM_MESSAGE')                 { |custom_message|         options[:custom_message]         = custom_message }
  opts.on('--hostdisplayname=HOSTDISPLAYNAME')               { |hostdisplayname|        options[:hostdisplayname]        = hostdisplayname }
  opts.on('--hostname=HOSTNAME')                             { |hostname|               options[:hostname]               = hostname }
  opts.on('--icinga_host=ICINGA_HOST')                       { |icinga_host|            options[:icinga_host]            = icinga_host }
  opts.on('--notificationauthorname=NOTIFICATIONAUTHORNAME') { |notificationauthorname| options[:notificationauthorname] = notificationauthorname }
  opts.on('--notificationcomment=NOTIFICATIONCOMMENT')       { |notificationcomment|    options[:notificationcomment]    = notificationcomment }
  opts.on('--notificationtype=NOTIFICATIONTYPE')             { |notificationtype|       options[:notificationtype]       = notificationtype.upcase }
  opts.on('--webhook=WEBHOOK')                               { |webhook|                options[:webhook]                = webhook }
  opts.on('--reason=REASON')                                 { |reason|                 options[:reason]                 = reason }
  opts.on('--servicedisplayname=SERVICEDISPLAYNAME')         { |servicedisplayname|     options[:servicedisplayname]     = servicedisplayname }
  opts.on('--servicename=SERVICENAME')                       { |servicename|            options[:servicename]            = servicename }
  opts.on('--output=OUTPUT')                                 { |output|                 options[:output]                 = output }
  opts.on('--state=STATE')                                   { |state|                  options[:state]                  = state.upcase }
  opts.on('--type=TYPE',
          'Really only needed for restart, otherwise it is automatically detected.') { |type| options[:type]             = type.upcase }
  opts.on('--username=USERNAME')                             { |username|               options[:username]               = username }
  opts.on('--icon_emoji=STRING')                             { |icon_emoji|             options[:icon_emoji]             = icon_emoji }
  opts.on('--debug')                                         { |debug|                  options[:debug]                  = debug }
end.parse!

# Logger setup
@logger = Logger.new('/var/log/icinga2/mattermost-better-write.log')
@logger.progname = "#{File.basename($PROGRAM_NAME)}[#{Process.pid}]"
@logger.level = options.include?(:debug) ? Logger::DEBUG : Logger::INFO

# The same message creation code from the original script
unless options.include?(:type)
  options[:type] = if options.include?(:reason) && !options[:reason].empty?
                     'TELEFON'
                   elsif options.include?(:servicename) && !options[:servicename].empty?
                     'SERVICE'
                   elsif options.include?(:hostname) && !options[:hostname].empty?
                     'HOST'
                   elsif options.include?(:custom_message) && !options[:custom_message].empty?
                     'CUSTOM'
                   end
end

msg_host = if options.include?(:hostdisplayname) && !options[:hostdisplayname].empty?
             options[:hostdisplayname]
           else
             options[:hostname]
           end
msg_service = if options.include?(:servicedisplayname) && !options[:servicedisplayname].empty?
                options[:servicedisplayname]
              elsif options.include?(:servicename) && !options[:servicename].empty?
                options[:servicename]
              end

case options[:type]
when 'HOST', 'SERVICE'
  options[:icon_emoji] = ':icinga:' unless options.include?(:icon_emoji)
  icon = case options[:notificationtype]
         when 'ACKNOWLEDGEMENT'
           ':heavy_check_mark:'
         when 'CUSTOM'
           ':speaker:'
         when 'FLAPPINGSTART', 'FLAPPINGEND'
           ':loop:'
         when 'DOWNTIMESTART', 'DOWNTIMEEND', 'DOWNTIMEREMOVED'
           ':electric_plug: '
         else
           case options[:state]
           when 'CRITICAL', 'DOWN'
             ':rotating_light:'
           when 'WARNING'
             ':warning:'
           when 'OK', 'UP'
             ':white_check_mark:'
           when 'UNKNOWN'
             ':question:'
           else
             ':white_medium_square:'
           end
         end

  message = "#{icon} #{options[:notificationtype]} | "
  message += if options.include?(:icinga_host)
               '[**'
             else
               '`'
             end
  message += msg_host
  message += " - #{msg_service}" unless msg_service.nil?
  message += if options.include?(:icinga_host)
               if options.include?(:servicename)
                 "**](https://#{options[:icinga_host]}/monitoring/service/show?host=#{options[:hostname]}&service=#{options[:servicename]})"
               else
                 "**](https://#{options[:icinga_host]}/monitoring/host/show?host=#{options[:hostname]})"
               end
             else
               '`'
             end
  message += ": #{options[:state]}"
  message += " | *Comment* by `#{options[:notificationauthorname]}`: `#{options[:notificationcomment]}`" if options.include?(:notificationcomment) && !options[:notificationcomment].empty?
  if options.include?(:output) && !options[:output].empty?
    # mattermost has a message length of 16383 chars
    output = if options[:output].length > 14_000
               "#{options[:output][0..14_000]}\n[truncated after 14000 characters]"
             else
               options[:output]
             end
    message += "\n ```\n#{output}\n```"
  end
when 'TELEFON'
  options[:icon_emoji] = ':icinga:' unless options.include?(:icon_emoji)
  icon = case options[:reason]
         when 'host_alert', 'service_alert', 'alert'
           ':telephone:'
         when 'host_delay', 'service_delay', 'delay'
           ':telephone_receiver:'
         else # rubocop:disable Lint/DuplicateBranch
           ':telephone:'
         end

  message = "#{icon} #{options[:type]} | "
  message += case options[:reason]
             when 'host_delay', 'service_delay', 'delay'
               'Delayed'
             else
               'Send'
             end
  message += ' call for '
  message += if options.include?(:icinga_host)
               '[**'
             else
               '`'
             end
  message += msg_host
  message += " - #{msg_service}" unless msg_service.nil?
  message += if options.include?(:icinga_host)
               if options.include?(:servicename)
                 "**](https://#{options[:icinga_host]}/monitoring/service/show?host=#{options[:hostname]}&service=#{options[:servicename]})"
               else
                 "**](https://#{options[:icinga_host]}/monitoring/host/show?host=#{options[:hostname]})"
               end
             else
               '`'
             end
  message += if options.include?(:notificationtype) && options[:notificationtype].upcase == 'CUSTOM'
               ": custom notification by `#{options[:notificationauthorname]}` with `#{options[:notificationcomment]}`"
             else
               ": #{options[:state]}"
             end
when 'RESTART'
  options[:icon_emoji] = ':icinga:' unless options.include?(:icon_emoji)
  message = ":recycle: #{options[:type]} | Restarting Service "
  message += if options.include?(:icinga_host)
               '[**'
             else
               '`'
             end
  message += msg_service
  message += if options.include?(:icinga_host)
               '** on **'
             else
               '` on `'
             end
  message += msg_host
  message += if options.include?(:icinga_host)
               "**](https://#{options[:icinga_host]}/monitoring/service/show?host=#{options[:hostname]}&service=#{options[:servicename]})"
             else
               '`'
             end
when 'CUSTOM'
  message = options[:custom_message]
end

payload = {
  text: message
}

payload[:icon_emoji] = options[:icon_emoji] if options.include?(:icon_emoji) && !options[:icon_emoji].empty?
payload[:username]   = options[:username] if options.include?(:username) && !options[:username].empty?
payload[:username]   = options[:icinga_host] if options.include?(:icinga_host) && !payload.include?(:username)
payload = payload.to_json

begin
  uri = URI.parse(options[:webhook])
  https = Net::HTTP.new(uri.host, uri.port)
  https.use_ssl = true

  req = Net::HTTP::Post.new(
    uri.path,
    {
      'Content-Type' => 'application/json',
      'Accept' => 'application/json'
    }
  )
  req.body = payload

  resp = https.request(req)
  if resp.is_a?(Net::HTTPSuccess)
    @logger.debug "Successful send message to Mattermost: #{payload.dump}"
  else
    @logger.error "Failed to send message to Mattermost: #{payload.dump}"
  end
rescue StandardError => e
  @logger.fatal "Error while sending message to Mattermost: #{e.message}"
end
