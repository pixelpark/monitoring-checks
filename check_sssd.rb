#! /opt/puppetlabs/puppet/bin/ruby

require 'English'

STATES = {
  0 => 'OK',
  1 => 'WARNING',
  2 => 'CRITICAL',
  3 => 'UNKOWN'
}.freeze
SUDO = case Process.uid
       when 0
         ''
       else
         '/bin/sudo '
       end.freeze

def config_check
  result = %x(#{SUDO} /sbin/sssctl config-check 2>&1)
  raise result unless $CHILD_STATUS.success?

  nil
rescue StandardError => e
  puts "#{STATES[2]} - config-check of sssd failed\n#{e.message}"
  exit 2
end

def domain_list
  result = %x(#{SUDO} /sbin/sssctl domain-list 2>&1)
  raise result unless $CHILD_STATUS.success?

  result.lines.map(&:chomp)
rescue StandardError => e
  puts "#{STATES[3]} - errors on collecting domain list from sssd\n#{e.message}"
  exit 3
end

def domain_status(domain)
  # Online status: Online
  #
  # Active servers:
  # LDAP: prd-ds.pixelpark.com
  #
  # Discovered LDAP servers:
  # - prd-ds.pixelpark.com
  #
  domain_status = %x(#{SUDO} /sbin/sssctl domain-status #{domain} 2>&1)
  raise domain_status unless $CHILD_STATUS.success?

  domain_status.split(/\n\n/m).to_h do |block|
    key, value = block.match(/^(?<key>[^:]+):\s*(?<value>.+)$/m).captures
    [
      key,
      case key
      when 'Active servers'
        value.lines.map do |line|
          line.chomp.match(/\A(?<type>[^:]+):\s+(?<server>.*)\z/).named_captures
        end
      when 'Discovered LDAP servers'
        value.lines.map do |line|
          line.chomp.gsub(/\A-\s+/, '')
        end
      else
        value.strip
      end
    ]
  end
rescue StandardError => e
  puts "#{STATES[3]} - errors on collecting domain status of '#{domain}'\n#{e.message}\n#{e.backtrace}"
  exit 3
end

config_check
domain_status = domain_list.to_h do |domain|
  [domain, domain_status(domain)]
end

offline_domains = domain_status.reject { |_domain, values| values['Online status'].casecmp('Online').zero? }
no_active_servers = domain_status.select { |_domain, values| values['Active servers'].length.zero? }
no_discovered_servers = domain_status.select { |_domain, values| values['Discovered LDAP servers'].length.zero? }

status, message = if offline_domains.length.positive?
                    [2, "domains offline: '#{offline_domains.keys.join('\', \'')}'"]
                  elsif no_active_servers.length.positive?
                    [1, "no active servers for domains: '#{no_active_servers.keys.join('\', \'')}'"]
                  elsif no_discovered_servers.length.positive?
                    [1, "no discovered servers for domains: '#{no_discovered_servers.keys.join('\', \'')}'"]
                  elsif domain_status.length.positive?
                    [0, "domains online: '#{domain_status.keys.join('\', \'')}'"]
                  else
                    [2, "no domains configured"]
                  end

output = [
  STATES[status],
  message
].join(' - ')
perfdata = [
  "no_discovered_servers=#{no_active_servers.length};1;;0;"
  "no_active_servers=#{no_active_servers.length};1;;0;"
  "domains_offline=#{offline_domains.length};;1;0;",
  "domains_online=#{domain_status.length};;;0;"
].join(' ')

puts "#{output} | #{perfdata}"
puts (domain_status.map do |domain, values|
  "domain '#{domain}':\n\t#{values.map { |key, value| "#{key}: #{value}" }.join("\n\t")}"
end).join("\n\n")
exit status
