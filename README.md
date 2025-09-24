# Ansible Runner Service

A microservice for running Ansible playbooks with JSON/YAML configuration management, built with a clean architecture.

## Features

- **Dual format support**: JSON and YAML configuration files
- **Metadata tracking**: Run counts, limits, and execution history
- **Comprehensive logging**: Dedicated log directories with automatic rotation
- **Password file security**: Support for secure authentication files
- **SystemD integration**: Service and timer-based scheduled execution
- **CLI interface**: Command-line tool with multiple commands
- **Clean architecture**: Separated concerns with dependency injection
- **Legacy compatibility**: Works with existing scripts

## Architecture

```
src/
├── config/          # Configuration loading & validation
├── commands/        # Ansible command building
├── execution/       # Command execution & process management
├── metadata/        # Run tracking & limits
├── models/         # Data models & validation
└── ansible_service.py  # Main service orchestrator
```

## Installation

```bash
# Basic installation
pip install pyyaml

# Full installation
pip install -r requirements.txt
```

## CLI Usage

### Basic Commands

```bash
# Run a playbook (legacy compatibility)
python main.py config.json --dry-run

# Run with new syntax
python main.py run config.yaml --dry-run

# Get configuration info
python main.py info config.json

# Show command that would be executed
python main.py command config.yaml

# Validate configuration
python main.py validate config.json

# Log management
python main.py logs summary config.yaml
python main.py logs cleanup config.yaml --max-age-days 7
python main.py logs tail config.yaml --lines 100

# Systemd service management
python main.py systemd generate config.yaml
python main.py systemd install config.yaml
python main.py systemd status config.yaml
python main.py systemd start config.yaml
python main.py systemd uninstall config.yaml

# Systemd timer management (for scheduled execution)
python main.py systemd timer-start config.yaml
python main.py systemd timer-stop config.yaml
python main.py systemd timer-status config.yaml
```


## Configuration Format

Both JSON and YAML formats are supported:

```yaml
playbook: playbooks/deploy.yml
inventory: inventory/production
limit: webservers
working_directory: /opt/ansible-project  # Execute from this directory
extra_vars:
  app_version: "1.2.3"
  environment: production
tags: [deploy, configure]
verbose: 1
become: true
become_user: root
become_method: sudo
become_password_file: ~/.ansible/become_password
vault_password_file: ~/.ansible/vault_password
private_key: ~/.ssh/deploy_key
connection: ssh
connection_password_file: ~/.ansible/ssh_password
log_directory: ~/ansible_logs
log_level: INFO
metadata:
  name: "Production Deployment"
  description: "Deploy application to production"
  max_runs: 5
systemd:
  enabled: true
  user: ansible
  working_directory: /opt/ansible-runner  # Service working directory
  restart: always
  restart_sec: 10
  service_type: simple
  after:
    - network.target
  environment_file: /etc/ansible-runner/environment
```

### Working Directory Examples

```yaml
# Use current directory
working_directory: "."

# Use absolute path
working_directory: /opt/my-ansible-project

# Use home directory expansion
working_directory: ~/projects/ansible

# Relative paths in playbook will be resolved from working_directory
playbook: site.yml  # Will look for /opt/my-ansible-project/site.yml
inventory: inventories/prod  # Will look for /opt/my-ansible-project/inventories/prod
```

## SystemD Timer Configuration

For scheduled playbook execution, configure the systemd timer settings:

```yaml
systemd:
  enabled: true
  # Timer configuration
  timer_enabled: true
  on_calendar: "*:0/15"        # Every 15 minutes
  on_boot_sec: "5min"          # 5 minutes after boot
  randomized_delay_sec: "1min" # Random delay up to 1 minute
  persistent: true             # Run missed timers on startup
```

**Timer Schedule Examples:**
- `"*:0/15"` - Every 15 minutes
- `"Mon 02:00"` - Every Monday at 2:00 AM
- `"daily"` - Once per day (midnight)
- `"weekly"` - Once per week (Sunday midnight)
- `"*-*-* 06:30:00"` - Daily at 6:30 AM

**Timer Options:**
- `on_calendar`: Cron-like scheduling (systemd calendar format)
- `on_boot_sec`: Delay after system boot (e.g., "15min", "1h")
- `on_unit_active_sec`: Repeat interval after completion
- `randomized_delay_sec`: Random delay to spread load
- `persistent`: Run missed executions at startup

## Security Features

- **File path expansion**: Supports `~` for home directory
- **Permission validation**: Warns about insecure file permissions
- **Private key security**: Enforces secure permissions (600/400) for SSH keys
- **Password file security**: Warns if password files are world-readable
- **Working directory control**: Execute playbooks from specific directories

## Logging Features

- **Dedicated log directories**: Configurable log storage location
- **Automatic log naming**: Timestamp-based log file naming with run names
- **Log rotation**: Built-in cleanup of old log files by age and count
- **Log management commands**: CLI tools for log summary, cleanup, and viewing
- **Environment integration**: Sets ANSIBLE_LOG_PATH for Ansible logging

## Systemd Integration

- **Service file generation**: Auto-generate systemd unit files from configuration
- **Installation management**: Install/uninstall services as user or system services
- **Service control**: Start, stop, restart, enable, disable services via CLI
- **Status monitoring**: Check service status and health
- **Production ready**: Configurable restart policies, timeouts, and dependencies
- **Environment management**: Support for environment files and variables

## Development

The codebase follows clean architecture principles:
- **Models**: Data structures and validation
- **Config**: File loading and format detection
- **Commands**: Ansible command generation
- **Execution**: Process management and result handling
- **Metadata**: Run tracking and limits
