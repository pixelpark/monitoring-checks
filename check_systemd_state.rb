#! /opt/puppetlabs/puppet/bin/ruby

require 'open3'
require 'json'

STATES = {
  0 => 'OK',
  1 => 'WARNING',
  2 => 'CRITICAL',
  3 => 'UNKOWN'
}.freeze

begin
  stdout, _stderr, _status = Open3.capture3('systemctl is-system-running')
  # Table 2. is-system-running output
  # ┌─────────────┬─────────────────────────────────────────────────────┬───────────┐
  # │Name         │ Description                                         │ Exit Code │
  # ├─────────────┼─────────────────────────────────────────────────────┼───────────┤
  # │initializing │ Early bootup, before basic.target is reached or the │ > 0       │
  # │             │ maintenance state entered.                          │           │
  # ├─────────────┼─────────────────────────────────────────────────────┼───────────┤
  # │starting     │ Late bootup, before the job queue becomes idle for  │ > 0       │
  # │             │ the first time, or one of the rescue targets are    │           │
  # │             │ reached.                                            │           │
  # ├─────────────┼─────────────────────────────────────────────────────┼───────────┤
  # │running      │ The system is fully operational.                    │ 0         │
  # ├─────────────┼─────────────────────────────────────────────────────┼───────────┤
  # │degraded     │ The system is operational but one or more units     │ > 0       │
  # │             │ failed.                                             │           │
  # ├─────────────┼─────────────────────────────────────────────────────┼───────────┤
  # │maintenance  │ The rescue or emergency target is active.           │ > 0       │
  # ├─────────────┼─────────────────────────────────────────────────────┼───────────┤
  # │stopping     │ The manager is shutting down.                       │ > 0       │
  # ├─────────────┼─────────────────────────────────────────────────────┼───────────┤
  # │offline      │ The manager is not running. Specifically, this is   │ > 0       │
  # │             │ the operational state if an incompatible program is │           │
  # │             │ running as system manager (PID 1).                  │           │
  # ├─────────────┼─────────────────────────────────────────────────────┼───────────┤
  # │unknown      │ The operational state could not be determined, due  │ > 0       │
  # │             │ to lack of resources or another error cause.        │           │
  # └─────────────┴─────────────────────────────────────────────────────┴───────────┘
  systemd_state = stdout.chomp
  status = case systemd_state
           when 'running'
             0
           when 'initializing', 'starting', 'maintenance', 'degraded'
             1
           when 'stopping', 'offline'
             2
           else # 'unknown'
             3
           end

  failed_units = if status.zero?
                   []
                 else
                   stdout, _stderr, _status = Open3.capture3('systemctl list-units --failed --output=json')
                   JSON.parse(stdout)
                 end

  message = "According to systemd, the overall state of the system is [#{systemd_state}]"
  unless failed_units.empty?
    keys = failed_units.first.keys
    max_lengths = keys.reduce({}) do |memo, key|
      memo.merge({ key => failed_units.max_by { |unit| unit[key].length }[key].length })
    end
    message << " with #{failed_units.length} failed units\n"
    message << keys.map do |key|
      key.upcase.ljust(max_lengths[key])
    end.join(' ')
    message << "\n"
    message << failed_units.map do |unit|
      keys.map do |key|
        unit[key].ljust(max_lengths[key])
      end.join(' ')
    end.join("\n")
  end
rescue StandardError => e
  puts "#{STATES[3]} - errors while checking state\n#{e.message}\n#{e.backtrace.join("\n")}"
  exit 3
else
  puts "#{STATES[status]} - #{message}"
  exit status
end
