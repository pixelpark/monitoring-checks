#!/opt/puppetlabs/puppet/bin/ruby

require 'optparse'
require 'openssl'
require 'etc'

STATES = {
  0 => 'OK',
  1 => 'WARNING',
  2 => 'CRITICAL',
  3 => 'UNKOWN'
}.freeze
DATEFORMAT = '%F %T'.freeze

options = {
  cert_dir: '/etc/puppetlabs/puppetserver/ca/signed',
  certs: [],
  ca_cert: '/etc/puppetlabs/puppetserver/ca/ca_crt.pem',
  ca_crl: '/etc/puppetlabs/puppetserver/ca/ca_crl.pem',
  warn: 30 * 86_400,
  crit: 7 * 86_400,
  processes: Etc.nprocessors
}
OptionParser.new do |opts|
  opts.on('--ca-cert PATH', String) { |path| options[:ca_cert] = path }
  opts.on('--ca-crl PATH', String) { |path| options[:ca_crl] = path }
  opts.on('--cert-dir PATH', String) { |path| options[:cert_dir] = path }
  opts.on('-p PROCESSES', Integer,
          'Count of paralell processes started at the same time',
          "Default is #{Etc.nprocessors} (ruby active usable cpu count)",
          'Note that always one group of checks must be finished before a the next one will be starting.') do |processes|
    options[:processes] << processes
  end
  opts.on('-c DAYS', Integer,
          'Critical if cert expire below that value of days',
          "Default is #{options[:crit]}") do |i|
    options[:crit] = i * 86_400
  end
  opts.on('-w DAYS', Integer,
          'Warning if cert expire below that value of days',
          "Default is #{options[:warn]}") do |i|
    options[:warn] = i * 86_400
  end
  opts.on('-h', '--help', 'Prints this help') do
    puts opts
    exit
  end
end.parse!

def check_cert(cert, file, critical, warning)
  currenttime = Time.now
  result = {
    message: ["#{STATES[2]} - issue while processing file"],
    file: File.basename(file),
    subject: cert.subject,
    issuer: cert.issuer,
    serial: cert.serial,
    not_after: cert.not_after || Time.at(0),
    not_before: cert.not_before || Time.at(0),
    status: 2
  }

  days = ((result[:not_after] - currenttime) / 86_400).floor
  status = if result[:not_before] > currenttime
             {
               message: ["#{STATES[2]} - Cert is not yet valid (system time issue?)"],
               status: 2
             }
           elsif result[:not_after] < currenttime
             {
               message: ["#{STATES[2]} - Cert has expired since #{result[:not_after].strftime(DATEFORMAT)}"],
               status: 2
             }
           elsif result[:not_after] < (currenttime + critical)
             {
               message: ["#{STATES[2]} - Cert will expire in #{days} days at #{result[:not_after].strftime(DATEFORMAT)}"],
               status: 2
             }
           elsif result[:not_after] < (currenttime + warning)
             {
               message: ["#{STATES[1]} - Cert will expire in #{days} days at #{result[:not_after].strftime(DATEFORMAT)}"],
               status: 1
             }
           else
             {
               message: ["#{STATES[0]} - Cert is valid until #{result[:not_after].strftime(DATEFORMAT)}"],
               status: 0
             }
           end

  result.merge!(status)
end

store = OpenSSL::X509::Store.new
store.add_file(options[:ca_cert])
store.add_file(options[:ca_crl])
store.flags = OpenSSL::X509::V_FLAG_CRL_CHECK | OpenSSL::X509::V_FLAG_CRL_CHECK_ALL

results = []
results << check_cert(OpenSSL::X509::Certificate.new(File.read(options[:ca_cert])), options[:ca_cert], options[:crit], options[:warn])
queue = Thread::Queue.new
Dir.glob("#{options[:cert_dir]}/*").each { |file| queue << file }
threads = options[:processes].times.map do
  Thread.new do
    while (file = queue.pop(true))
      next unless File.readable?(file)

      cert = OpenSSL::X509::Certificate.new(File.read(file)) # DER- or PEM-encoded
      result = check_cert(cert, file, options[:crit], options[:warn])

      unless store.verify(cert)
        result[:message].unshift("#{STATES[2]} - Cert verify failed (#{store.error_string})")
        result[:status] = 2
      end

      results << result
    end
  rescue ThreadError
    # do nothing
  end
end
threads.map(&:join)

exitstate = results.map { |i| i[:status] }.max

print "#{STATES[exitstate]} - certs with "
puts STATES.keys.reverse.map { |state|
  count = results.select { |i| i[:status] == state }.count
  "#{count} #{STATES[state].downcase}" unless count <= 0
}.compact.join(', ')
puts results.sort_by { |i| [-i[:status], i[:not_after], i[:cert]] }.map { |i|
  "╠═ '#{i[:file]}' - [#{i[:issuer]}] 0x#{i[:serial].to_s(16)} #{i[:subject]}\n║ #{i[:message].join("\n").gsub("\n", "\n║ ")}"
}.join("\n")
exit exitstate
