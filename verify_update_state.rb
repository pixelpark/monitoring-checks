#!/opt/puppetlabs/puppet/bin/ruby

# Usage with DNF:
#   dnf install python3-dnf-plugin-post-transaction-actions
#   echo '*:any:/path/to/verify_update_state.rb' > /etc/dnf/plugins/post-transaction-actions.d/verify_update_state.action

require 'open3'
require 'time'
require 'tempfile'

_, check_update_status = Open3.capture2e('/bin/dnf --quiet --cacheonly check-update')
history, = Open3.capture2e({ 'LC_ALL' => 'C', 'LANG' => 'C' }, '/bin/dnf --quiet --cacheonly history info last')
id = case history
     when /^Transaction ID\s+:\s+(?<status_code>\d+)$/
       Regexp.last_match(:status_code)
     else
       '-'
     end

Tempfile.open do |tempfile|
  tempfile.puts("#{Time.now.utc.strftime('%FT%TZ')} #{check_update_status.exitstatus} #{id}")
  File.open("/var/lib/dnf/#{File.basename(__FILE__, File.extname(__FILE__))}.log", File::RDWR | File::CREAT, 644) do |file|
    File.foreach(file).with_index do |line, i|
      break if i >= 200

      tempfile.puts(line)
    end
    file.rewind
    tempfile.rewind
    File.foreach(tempfile) do |line|
      file.puts(line)
    end
    file.truncate(file.pos)
  end
end

exit 0
