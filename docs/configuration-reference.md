# Configuration Reference

Complete reference for all configuration variables available in JSON and YAML configuration files.

## Format Support

Both JSON and YAML formats are supported. The system automatically detects the format based on the file extension:
- `.json` - JSON format
- `.yaml`, `.yml` - YAML format

## Complete Configuration Schema

### Core Ansible Settings

#### `playbook` (required)
- **Type**: `string`
- **Description**: Path to the Ansible playbook file
- **Example**: `"playbooks/site.yml"`

#### `inventory` (optional)
- **Type**: `string`
- **Description**: Path to inventory file or directory
- **Default**: Ansible's default inventory
- **Example**: `"inventory/hosts"`

#### `limit` (optional)
- **Type**: `string`
- **Description**: Limit execution to specific hosts or groups
- **Example**: `"webservers"`

#### `extra_vars` (optional)
- **Type**: `object`
- **Description**: Extra variables to pass to the playbook
- **Default**: `{}`
- **Example**:
```yaml
extra_vars:
  app_version: "1.2.3"
  environment: production
```

#### `tags` (optional)
- **Type**: `array of strings`
- **Description**: Only run plays and tasks tagged with these values
- **Example**: `["deploy", "configure"]`

#### `skip_tags` (optional)
- **Type**: `array of strings`
- **Description**: Skip plays and tasks with these tags
- **Example**: `["debug", "test"]`

#### `check` (optional)
- **Type**: `boolean`
- **Description**: Run in check mode (dry run)
- **Default**: `false`

#### `diff` (optional)
- **Type**: `boolean`
- **Description**: Show differences when changing files
- **Default**: `false`

#### `verbose` (optional)
- **Type**: `integer`
- **Description**: Verbosity level (0-4)
- **Default**: `0`
- **Example**: `2`

#### `forks` (optional)
- **Type**: `integer`
- **Description**: Number of parallel processes
- **Example**: `10`

### Authentication & Security

#### `become` (optional)
- **Type**: `boolean`
- **Description**: Enable privilege escalation
- **Default**: `false`

#### `become_user` (optional)
- **Type**: `string`
- **Description**: User to become when using privilege escalation
- **Default**: `"root"`

#### `become_method` (optional)
- **Type**: `string`
- **Description**: Privilege escalation method
- **Default**: `"sudo"`
- **Options**: `"sudo"`, `"su"`, `"pbrun"`, `"pfexec"`, `"runas"`

#### `become_password_file` (optional)
- **Type**: `string`
- **Description**: Path to file containing become password
- **Security**: File permissions are validated (warns if world-readable)
- **Path Expansion**: Supports `~` for home directory
- **Example**: `"~/.ansible/become_password"`

#### `vault_password_file` (optional)
- **Type**: `string`
- **Description**: Path to Ansible Vault password file
- **Security**: File permissions are validated
- **Path Expansion**: Supports `~` for home directory
- **Example**: `"~/.ansible/vault_password"`

#### `private_key` (optional)
- **Type**: `string`
- **Description**: Path to SSH private key file
- **Security**: Enforces secure permissions (600/400)
- **Path Expansion**: Supports `~` for home directory
- **Example**: `"~/.ssh/deploy_key"`

#### `connection` (optional)
- **Type**: `string`
- **Description**: Connection type to use
- **Default**: Ansible's default
- **Options**: `"ssh"`, `"local"`, `"winrm"`, etc.

#### `connection_password_file` (optional)
- **Type**: `string`
- **Description**: Path to file containing connection password
- **Security**: File permissions are validated
- **Path Expansion**: Supports `~` for home directory
- **Example**: `"~/.ansible/ssh_password"`

#### `timeout` (optional)
- **Type**: `integer`
- **Description**: Connection timeout in seconds
- **Example**: `30`

#### `start_at_task` (optional)
- **Type**: `string`
- **Description**: Start execution at a specific task
- **Example**: `"Install packages"`

### Execution Environment

#### `working_directory` (optional)
- **Type**: `string`
- **Description**: Directory to execute Ansible commands from
- **Path Expansion**: Supports `~` and relative paths
- **SystemD**: Used as WorkingDirectory in service files
- **Examples**:
  - `"."` - Current directory
  - `"/opt/ansible-project"` - Absolute path
  - `"~/projects/ansible"` - Home directory expansion

### Logging Configuration

#### `log_directory` (optional)
- **Type**: `string`
- **Description**: Directory for storing log files
- **Auto-creation**: Directory is created if it doesn't exist
- **Path Expansion**: Supports `~` for home directory
- **Example**: `"./ansible_logs"`

#### `log_level` (optional)
- **Type**: `string`
- **Description**: Logging level
- **Default**: `"INFO"`
- **Options**: `"DEBUG"`, `"INFO"`, `"WARNING"`, `"ERROR"`, `"CRITICAL"`

### Metadata Configuration

#### `metadata` (optional)
- **Type**: `object`
- **Description**: Metadata for tracking and identification

##### `metadata.name` (optional)
- **Type**: `string`
- **Description**: Human-readable name for this configuration
- **Used for**: SystemD service names, log identification
- **Example**: `"Production Deployment"`

##### `metadata.description` (optional)
- **Type**: `string`
- **Description**: Description of what this configuration does
- **Used for**: SystemD service descriptions, documentation
- **Example**: `"Deploy application to production servers"`

##### `metadata.run_count` (auto-managed)
- **Type**: `integer`
- **Description**: Number of times this configuration has been executed
- **Default**: `0`
- **Note**: Automatically updated on each run

##### `metadata.max_runs` (optional)
- **Type**: `integer` or `null`
- **Description**: Maximum number of allowed executions
- **Default**: `null` (no limit)
- **Example**: `5`

##### `metadata.last_run` (auto-managed)
- **Type**: `string` (ISO datetime) or `null`
- **Description**: Timestamp of last execution
- **Example**: `"2025-09-24T10:30:45.123456"`

##### `metadata.schedule` (optional)
- **Type**: `string` or `null`
- **Description**: Human-readable schedule description
- **Note**: For documentation only, actual scheduling via SystemD timers
- **Example**: `"Daily at 2:00 AM"`

### SystemD Service Configuration

#### `systemd` (optional)
- **Type**: `object`
- **Description**: SystemD service and timer configuration

##### `systemd.enabled` (optional)
- **Type**: `boolean`
- **Description**: Whether to enable the service/timer after installation
- **Default**: `false`

##### `systemd.user` (optional)
- **Type**: `string` or `null`
- **Description**: User to run the service as
- **Default**: `null` (current user)
- **Example**: `"ansible"`

##### `systemd.working_directory` (optional)
- **Type**: `string` or `null`
- **Description**: Working directory for the service (overrides global working_directory)
- **Path Resolution**: Converted to absolute path for SystemD
- **Example**: `"/opt/ansible-runner"`

##### `systemd.environment_file` (optional)
- **Type**: `string` or `null`
- **Description**: Path to environment file for the service
- **Path Expansion**: Supports `~` for home directory
- **Example**: `"/etc/ansible-runner/environment"`

##### `systemd.restart` (optional)
- **Type**: `string`
- **Description**: Service restart policy
- **Default**: `"on-failure"`
- **Options**: `"no"`, `"on-success"`, `"on-failure"`, `"on-abnormal"`, `"on-watchdog"`, `"on-abort"`, `"always"`
- **Note**: Ignored for timer-enabled services (oneshot services don't restart)

##### `systemd.restart_sec` (optional)
- **Type**: `integer`
- **Description**: Time to wait before restarting (seconds)
- **Default**: `5`

##### `systemd.wanted_by` (optional)
- **Type**: `string`
- **Description**: SystemD target that wants this service
- **Default**: `"multi-user.target"`

##### `systemd.after` (optional)
- **Type**: `array of strings`
- **Description**: Services/targets to start after
- **Default**: `["network.target"]`
- **Example**: `["network.target", "mysql.service"]`

##### `systemd.requires` (optional)
- **Type**: `array of strings`
- **Description**: Services/targets that must be running
- **Default**: `[]`
- **Example**: `["mysql.service", "redis.service"]`

##### `systemd.service_type` (optional)
- **Type**: `string`
- **Description**: SystemD service type
- **Default**: `"simple"`
- **Options**: `"simple"`, `"exec"`, `"forking"`, `"oneshot"`, `"dbus"`, `"notify"`, `"idle"`
- **Note**: Automatically set to `"oneshot"` when `timer_enabled` is `true`

##### `systemd.timeout_start_sec` (optional)
- **Type**: `integer`
- **Description**: Timeout for service start (seconds)
- **Default**: `60`

##### `systemd.timeout_stop_sec` (optional)
- **Type**: `integer`
- **Description**: Timeout for service stop (seconds)
- **Default**: `30`

### SystemD Timer Configuration

#### `systemd.timer_enabled` (optional)
- **Type**: `boolean`
- **Description**: Enable SystemD timer for scheduled execution
- **Default**: `false`
- **Effect**: Changes service type to `oneshot`, creates `.timer` unit file

#### `systemd.on_calendar` (optional)
- **Type**: `string` or `null`
- **Description**: Calendar-based scheduling (systemd.time format)
- **Examples**:
  - `"*:0/15"` - Every 15 minutes
  - `"Mon 02:00"` - Every Monday at 2:00 AM
  - `"daily"` - Once per day (midnight)
  - `"weekly"` - Once per week (Sunday midnight)
  - `"*-*-* 06:30:00"` - Daily at 6:30 AM
  - `"Mon..Fri 09:00"` - Weekdays at 9:00 AM

#### `systemd.on_boot_sec` (optional)
- **Type**: `string` or `null`
- **Description**: Time to wait after boot before first execution
- **Format**: Systemd time spans (e.g., "15min", "1h", "30sec")
- **Example**: `"5min"`

#### `systemd.on_startup_sec` (optional)
- **Type**: `string` or `null`
- **Description**: Time to wait after systemd startup before first execution
- **Format**: Systemd time spans
- **Example**: `"30sec"`

#### `systemd.on_unit_active_sec` (optional)
- **Type**: `string` or `null`
- **Description**: Time to wait after service completion before next execution
- **Format**: Systemd time spans
- **Example**: `"1h"`
- **Note**: Creates repeating timer based on completion

#### `systemd.randomized_delay_sec` (optional)
- **Type**: `string` or `null`
- **Description**: Maximum random delay to add to scheduled times
- **Purpose**: Spread system load across time
- **Format**: Systemd time spans
- **Example**: `"5min"`

#### `systemd.persistent` (optional)
- **Type**: `boolean`
- **Description**: Run missed timer executions at startup
- **Default**: `false`
- **Use case**: Ensure execution happens even if system was down during scheduled time

## Complete Example Configuration

```yaml
# Core Ansible settings
playbook: playbooks/deploy.yml
inventory: inventory/production
limit: webservers
extra_vars:
  app_version: "1.2.3"
  environment: production
  debug: false
tags: [deploy, configure]
skip_tags: [test]
check: false
diff: true
verbose: 2
forks: 10

# Authentication
become: true
become_user: root
become_method: sudo
become_password_file: ~/.ansible/become_password
vault_password_file: ~/.ansible/vault_password
private_key: ~/.ssh/deploy_key
connection: ssh
connection_password_file: ~/.ansible/ssh_password
timeout: 30

# Execution environment
working_directory: /opt/ansible-project

# Logging
log_directory: ~/ansible_logs
log_level: INFO

# Metadata
metadata:
  name: "Production Deployment"
  description: "Deploy application to production servers"
  max_runs: null

# SystemD configuration
systemd:
  enabled: true
  user: ansible
  working_directory: /opt/ansible-runner
  environment_file: /etc/ansible-runner/environment
  restart: on-failure
  restart_sec: 10
  wanted_by: multi-user.target
  after: [network.target, mysql.service]
  requires: [mysql.service]
  service_type: simple
  timeout_start_sec: 120
  timeout_stop_sec: 60

  # Timer configuration for scheduled execution
  timer_enabled: true
  on_calendar: "Mon..Fri 02:00"
  on_boot_sec: "10min"
  randomized_delay_sec: "5min"
  persistent: true
```

## Validation

Use the built-in validation command to check your configuration:

```bash
python main.py validate path/to/config.yaml
```

This will verify:
- Required fields are present
- File paths exist and have proper permissions
- SystemD timer configuration is valid
- All field types are correct

## Migration Notes

### From Basic to Timer Configuration

When migrating from a basic service to a timer-based service:

1. Set `systemd.timer_enabled: true`
2. Add scheduling with `systemd.on_calendar`
3. Consider setting `systemd.persistent: true` for reliability
4. Remove or set `systemd.restart: "no"` (oneshot services don't restart)
5. Add randomization with `systemd.randomized_delay_sec` if running on multiple systems

### Path Resolution

All file paths support:
- **Absolute paths**: `/opt/ansible/playbook.yml`
- **Relative paths**: `playbooks/site.yml` (relative to working_directory or config file location)
- **Home expansion**: `~/ansible/vault_password` (expands to user's home directory)

SystemD services automatically convert all paths to absolute paths for reliable execution.