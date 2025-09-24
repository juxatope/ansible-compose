#!/usr/bin/env python3

import sys
import os
import argparse
import logging
from pathlib import Path

# Add src to path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.ansible_service import AnsibleService
from src.metadata.manager import RunLimitExceeded
from src.config.loader import ConfigFormatError
from src.execution.executor import AnsibleExecutionError


def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def run_cli(args):
    try:
        service = AnsibleService(
            config_file=args.config,
            capture_output=args.verbose
        )

        result = service.run_playbook(
            dry_run=args.dry_run,
            skip_metadata_update=args.no_metadata_update
        )

        if args.verbose and result.stdout:
            print("STDOUT:", result.stdout)
        if args.verbose and result.stderr:
            print("STDERR:", result.stderr)

        return result.return_code

    except FileNotFoundError as e:
        print(f"Error: {e}")
        return 1

    except RunLimitExceeded as e:
        print(f"Error: {e}")
        return 1

    except ConfigFormatError as e:
        print(f"Configuration Error: {e}")
        return 1

    except AnsibleExecutionError as e:
        print(f"Execution Error: {e}")
        return e.result.return_code

    except Exception as e:
        print(f"Unexpected Error: {e}")
        return 1


def run_server(args):
    try:
        import uvicorn
        from src.api.app import app

        print(f"Starting Ansible Runner Service on {args.host}:{args.port}")
        uvicorn.run(
            app,
            host=args.host,
            port=args.port,
            log_level="info" if args.verbose else "warning"
        )
    except ImportError:
        print("Error: FastAPI and uvicorn are required for server mode")
        print("Install with: pip install fastapi uvicorn")
        return 1
    except Exception as e:
        print(f"Server Error: {e}")
        return 1


def info_command(args):
    try:
        service = AnsibleService(args.config)
        run_info = service.get_run_info()

        print(f"Configuration: {args.config}")
        print(f"Format: {service.config_format}")
        print(f"Name: {run_info['name'] or 'N/A'}")
        print(f"Description: {run_info['description'] or 'N/A'}")
        print(f"Run Count: {run_info['run_count']}")
        print(f"Max Runs: {run_info['max_runs'] or 'Unlimited'}")
        print(f"Last Run: {run_info['last_run'] or 'Never'}")
        print(f"Schedule: {run_info['schedule'] or 'N/A'}")

        return 0

    except Exception as e:
        print(f"Error: {e}")
        return 1


def command_command(args):
    try:
        service = AnsibleService(args.config)
        command = service.build_command()
        print(command)
        return 0

    except Exception as e:
        print(f"Error: {e}")
        return 1


def validate_command(args):
    try:
        service = AnsibleService(args.config)
        config = service.validate_config()
        print(f"Configuration is valid: {args.config}")
        return 0

    except Exception as e:
        print(f"Validation Error: {e}")
        return 1


def logs_command(args):
    try:
        service = AnsibleService(args.config)

        if args.logs_action == "summary":
            summary = service.get_log_summary()
            if not summary:
                print("No log directory configured.")
                return 1

            print(f"Log Directory: {summary['log_directory']}")
            print(f"Total Files: {summary['total_files']}")
            print(f"Total Size: {summary['total_size_mb']} MB")

            if summary['oldest_log']:
                print(f"Oldest Log: {summary['oldest_log']['file']} ({summary['oldest_log']['date']})")
            if summary['newest_log']:
                print(f"Newest Log: {summary['newest_log']['file']} ({summary['newest_log']['date']})")

        elif args.logs_action == "cleanup":
            removed = service.cleanup_old_logs(args.max_age_days, args.max_files)
            print(f"Cleaned up {removed} log files")

        elif args.logs_action == "tail":
            content = service.get_recent_log_content(args.lines)
            if content:
                print(content)
            else:
                print("No recent log content available.")

        return 0

    except Exception as e:
        print(f"Error: {e}")
        return 1


def systemd_command(args):
    try:
        import subprocess
        service = AnsibleService(args.config)
        system_wide = getattr(args, 'system', False)

        if args.systemd_action == "generate":
            content = service.generate_systemd_service()
            print(content)

        elif args.systemd_action == "install":
            enable = not getattr(args, 'no_enable', False)
            service_file = service.install_systemd_service(system_wide, enable)
            print(f"Service installed: {service_file}")

        elif args.systemd_action == "uninstall":
            success = service.uninstall_systemd_service(system_wide)
            if success:
                print("Service uninstalled successfully")
            else:
                print("Service uninstallation failed")
                return 1

        elif args.systemd_action == "status":
            status = service.get_systemd_service_status(system_wide)
            print(f"Service: {status['name']}")
            print(f"Active: {status['active']}")
            print(f"Enabled: {status['enabled']}")
            print("\nStatus Details:")
            print(status['status'])

        elif args.systemd_action in ["start", "stop", "restart", "enable", "disable"]:
            service_name = service.get_systemd_service_name()
            systemctl_cmd = ["systemctl"]
            if not system_wide:
                systemctl_cmd.append("--user")

            try:
                subprocess.run(systemctl_cmd + [args.systemd_action, service_name], check=True)
                print(f"Service {service_name} {args.systemd_action}ed successfully")
            except subprocess.CalledProcessError as e:
                print(f"Failed to {args.systemd_action} service: {e}")
                return 1

        return 0

    except Exception as e:
        print(f"Error: {e}")
        return 1


def main():
    parser = argparse.ArgumentParser(
        description="Ansible Runner - Execute Ansible playbooks with JSON/YAML configuration"
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Run command (default behavior)
    run_parser = subparsers.add_parser("run", help="Run an Ansible playbook")
    run_parser.add_argument(
        "config",
        help="Path to configuration file (JSON or YAML)"
    )
    run_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be executed without running"
    )
    run_parser.add_argument(
        "--no-metadata-update",
        action="store_true",
        help="Skip updating run metadata"
    )

    # Server command
    server_parser = subparsers.add_parser("server", help="Start HTTP API server")
    server_parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind server to (default: 0.0.0.0)"
    )
    server_parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind server to (default: 8000)"
    )

    # Info command
    info_parser = subparsers.add_parser("info", help="Show configuration information")
    info_parser.add_argument(
        "config",
        help="Path to configuration file"
    )

    # Command command
    cmd_parser = subparsers.add_parser("command", help="Show the command that would be executed")
    cmd_parser.add_argument(
        "config",
        help="Path to configuration file"
    )

    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate configuration file")
    validate_parser.add_argument(
        "config",
        help="Path to configuration file"
    )

    # Logs command
    logs_parser = subparsers.add_parser("logs", help="Manage log files")
    logs_subparsers = logs_parser.add_subparsers(dest="logs_action", help="Log management actions")

    # Logs summary
    summary_parser = logs_subparsers.add_parser("summary", help="Show log summary")
    summary_parser.add_argument("config", help="Path to configuration file")

    # Logs cleanup
    cleanup_parser = logs_subparsers.add_parser("cleanup", help="Clean up old log files")
    cleanup_parser.add_argument("config", help="Path to configuration file")
    cleanup_parser.add_argument("--max-age-days", type=int, default=30, help="Maximum age in days (default: 30)")
    cleanup_parser.add_argument("--max-files", type=int, default=100, help="Maximum number of files (default: 100)")

    # Logs tail
    tail_parser = logs_subparsers.add_parser("tail", help="Show recent log content")
    tail_parser.add_argument("config", help="Path to configuration file")
    tail_parser.add_argument("--lines", type=int, default=50, help="Number of lines to show (default: 50)")

    # Systemd command
    systemd_parser = subparsers.add_parser("systemd", help="Manage systemd service")
    systemd_subparsers = systemd_parser.add_subparsers(dest="systemd_action", help="Systemd management actions")

    # Generate service file
    generate_parser = systemd_subparsers.add_parser("generate", help="Generate systemd service file")
    generate_parser.add_argument("config", help="Path to configuration file")

    # Install service
    install_parser = systemd_subparsers.add_parser("install", help="Install systemd service")
    install_parser.add_argument("config", help="Path to configuration file")
    install_parser.add_argument("--system", action="store_true", help="Install as system service (requires sudo)")
    install_parser.add_argument("--no-enable", action="store_true", help="Don't enable service after installation")

    # Uninstall service
    uninstall_parser = systemd_subparsers.add_parser("uninstall", help="Uninstall systemd service")
    uninstall_parser.add_argument("config", help="Path to configuration file")
    uninstall_parser.add_argument("--system", action="store_true", help="Remove system service (requires sudo)")

    # Service status
    status_parser = systemd_subparsers.add_parser("status", help="Show systemd service status")
    status_parser.add_argument("config", help="Path to configuration file")
    status_parser.add_argument("--system", action="store_true", help="Check system service")

    # Service control (start/stop/restart)
    for action in ["start", "stop", "restart", "enable", "disable"]:
        action_parser = systemd_subparsers.add_parser(action, help=f"{action.title()} systemd service")
        action_parser.add_argument("config", help="Path to configuration file")
        action_parser.add_argument("--system", action="store_true", help="Control system service")

    # Handle legacy usage first (before parsing subcommands)
    if len(sys.argv) >= 2 and not sys.argv[1].startswith('-') and sys.argv[1] not in ['run', 'server', 'info', 'command', 'validate', 'logs', 'systemd']:
        # Legacy mode: python main.py config.json [--dry-run]
        config_file = sys.argv[1]
        if Path(config_file).exists():
            # Create a mock args object for legacy support
            class LegacyArgs:
                config = config_file
                dry_run = "--dry-run" in sys.argv
                no_metadata_update = False
                verbose = "--verbose" in sys.argv or "-v" in sys.argv

            setup_logging(LegacyArgs.verbose)
            return run_cli(LegacyArgs())

    args = parser.parse_args()
    setup_logging(args.verbose)

    # Handle subcommands
    if args.command == "run":
        return run_cli(args)
    elif args.command == "server":
        return run_server(args)
    elif args.command == "info":
        return info_command(args)
    elif args.command == "command":
        return command_command(args)
    elif args.command == "validate":
        return validate_command(args)
    elif args.command == "logs":
        return logs_command(args)
    elif args.command == "systemd":
        return systemd_command(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())