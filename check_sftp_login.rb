#! /opt/puppetlabs/puppet/bin/ruby

# Author: Robert Waffen <robert.waffen@pixelpark.com>
# Date:   2020-08-07

require 'net/sftp'
require 'optparse'

# gem dependencies
# - net-ssh
# - net-sftp
# - bcrypt_pbkdf
# - ed25519

@options = {}
OptionParser.new do |opts|
  opts.on('-H', '--hostname=HOSTNAME') { |hostname| @options[:hostname] = hostname }
  opts.on('-i', '--identity=IDENTITY') { |identity| @options[:identity] = identity }
  opts.on('-p', '--password=PASSWORD') { |password| @options[:password] = password }
  opts.on('-u', '--username=USERNAME') { |username| @options[:username] = username }
end.parse!

@hostname  = @options[:hostname]
@username  = @options[:username]
@identity  = @options[:identity] unless @options[:identity].nil? || @options[:identity].empty?
@password  = @options[:password] unless @options[:password].nil? || @options[:password].empty?
@connected = false

if @hostname.nil?
  puts 'Hostname missing'
  exit 1
end

if @username.nil?
  puts 'Username missing'
  exit 1
end

if @password.nil? && @identity.nil?
  puts 'Password or Identity has to be set!'
  exit 1
end

begin
  unless @password.nil?
    Net::SFTP.start(
      @hostname,
      @username,
      config: false,
      non_interactive: true,
      password: @password
    ) do |sftp|
      sftp.connect do
        @connected = true
      end
    end
  end

  unless @identity.nil?
    Net::SFTP.start(
      @hostname,
      @username,
      config: false,
      non_interactive: true,
      keys: [@identity],
      keys_only: true
    ) do |sftp|
      sftp.connect do
        @connected = true
      end
    end
  end
rescue Net::SSH::AuthenticationFailed => e
  result = e.message
  status = [2, 'CRITICAL', "not possible - #{result}"]
end

status = [0, 'OK', 'possible'] if @connected
puts "#{status[1]} - SFTP Login: #{status[2]}"

exit status[0]
