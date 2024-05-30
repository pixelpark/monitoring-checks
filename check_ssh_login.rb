#! /opt/puppetlabs/puppet/bin/ruby

# Author: Robert Waffen <robert.waffen@pixelpark.com>
# Date:   2020-08-07

require 'net/ssh'
require 'optparse'

# gem dependencies
# - net-ssh
# - bcrypt_pbkdf
# - ed25519

@options = {}
OptionParser.new do |opts|
  opts.on('-H', '--hostname=HOSTNAME') { |hostname| @options[:hostname] = hostname }
  opts.on('-i', '--identity=IDENTITY') { |identity| @options[:identity] = identity }
  opts.on('-p', '--password=PASSWORD') { |password| @options[:password] = password }
  opts.on('-u', '--username=USERNAME') { |username| @options[:username] = username }
end.parse!

@hostname = @options[:hostname]
@username = @options[:username]
@identity = @options[:identity] unless @options[:identity].nil? || @options[:identity].empty?
@password = @options[:password] unless @options[:password].nil? || @options[:password].empty?

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
    result = Net::SSH.start(
      @hostname,
      @username,
      config: false,
      non_interactive: true,
      password: @password
    ) do |ssh|
      ssh.exec! '/opt/puppetlabs/puppet/bin/facter fqdn'
    end
  end

  unless @identity.nil?
    result = Net::SSH.start(
      @hostname,
      @username,
      config: false,
      non_interactive: true,
      keys: [@identity],
      keys_only: true
    ) do |ssh|
      ssh.exec! '/opt/puppetlabs/puppet/bin/facter fqdn'
    end
  end

  result.strip!
rescue Net::SSH::AuthenticationFailed => e
  result = e.message
  status = [2, 'CRITICAL', "not possible - #{result}"]
end

status = [0, 'OK', 'possible'] if @hostname == result

puts "#{status[1]} - SSH Login: #{status[2]}"

exit status[0]
