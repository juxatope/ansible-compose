import os
import pwd
import subprocess
from pathlib import Path
from typing import Optional

from ...models.ansible_config import AnsibleConfig


class SystemdServiceError(Exception):
    pass


class SystemdServiceGenerator:
    def __init__(self, config: AnsibleConfig, config_file_path: str):
        self.config = config
        self.config_file_path = Path(config_file_path).absolute()

    def generate_service_file_content(self) -> str:
        """Generate systemd service file content."""
        systemd_config = self.config.systemd
        metadata = self.config.metadata

        # Determine service name from metadata or config file
        service_name = metadata.name or f"ansible-runner-{self.config_file_path.stem}"
        safe_service_name = self._sanitize_service_name(service_name)

        # Determine working directory - priority: systemd config > ansible config > config file directory
        working_dir = (
            systemd_config.working_directory or
            self.config.working_directory or
            str(self.config_file_path.parent)
        )

        # Ensure working directory is absolute and expanded
        if working_dir:
            working_dir = os.path.expanduser(working_dir)
            if not os.path.isabs(working_dir):
                # If relative, make it relative to config file directory
                working_dir = str((self.config_file_path.parent / working_dir).resolve())
        else:
            working_dir = str(self.config_file_path.parent)

        # Get current Python executable path
        python_path = self._get_python_path()

        # Get main.py path relative to config file
        main_script = self.config_file_path.parent / "main.py"
        if not main_script.exists():
            # Try to find main.py in common locations
            for possible_path in [
                Path.cwd() / "main.py",
                Path(__file__).parent.parent.parent / "main.py"
            ]:
                if possible_path.exists():
                    main_script = possible_path
                    break

        # Create the service file content
        service_content = f"""[Unit]
Description={metadata.description or f'Ansible Runner Service: {service_name}'}
Documentation=https://github.com/your-org/ansible-runner
"""

        # Add After dependencies
        if systemd_config.after:
            service_content += f"After={' '.join(systemd_config.after)}\n"

        # Add Requires dependencies
        if systemd_config.requires:
            service_content += f"Requires={' '.join(systemd_config.requires)}\n"

        # Use oneshot type for timer-based services
        service_type = "oneshot" if systemd_config.timer_enabled else systemd_config.service_type

        service_content += f"""
[Service]
Type={service_type}
User={systemd_config.user or self._get_current_user()}
WorkingDirectory={working_dir}
ExecStart={python_path} {main_script} run {self.config_file_path}
"""

        # Only add restart settings for non-timer services
        if not systemd_config.timer_enabled:
            service_content += f"""Restart={systemd_config.restart}
RestartSec={systemd_config.restart_sec}
"""

        service_content += f"""TimeoutStartSec={systemd_config.timeout_start_sec}
TimeoutStopSec={systemd_config.timeout_stop_sec}
"""

        # Add environment file if specified
        if systemd_config.environment_file:
            env_file = os.path.expanduser(systemd_config.environment_file)
            service_content += f"EnvironmentFile={env_file}\n"

        # Add environment variables for our service
        service_content += f"""Environment=ANSIBLE_CONFIG_FILE={self.config_file_path}
Environment=PYTHONPATH={self.config_file_path.parent}
"""

        # Add log configuration
        if self.config.log_directory:
            log_dir = os.path.expanduser(self.config.log_directory)
            service_content += f"Environment=ANSIBLE_LOG_PATH={log_dir}/ansible-service.log\n"

        service_content += f"""
[Install]
WantedBy={systemd_config.wanted_by}
"""

        return service_content

    def generate_timer_file_content(self) -> str:
        """Generate systemd timer file content."""
        systemd_config = self.config.systemd
        metadata = self.config.metadata

        if not systemd_config.timer_enabled:
            raise SystemdServiceError("Timer is not enabled in configuration")

        # Determine service name from metadata or config file
        service_name = metadata.name or f"ansible-runner-{self.config_file_path.stem}"
        safe_service_name = self._sanitize_service_name(service_name)

        timer_content = f"""[Unit]
Description=Timer for {metadata.description or f'Ansible Runner Service: {service_name}'}
"""

        # Add Requires/After dependencies if specified
        if systemd_config.requires:
            timer_content += f"Requires={' '.join(systemd_config.requires)}\n"
        if systemd_config.after:
            timer_content += f"After={' '.join(systemd_config.after)}\n"

        timer_content += f"""
[Timer]
Unit={safe_service_name}.service
"""

        # Add timer triggers
        if systemd_config.on_calendar:
            timer_content += f"OnCalendar={systemd_config.on_calendar}\n"
        if systemd_config.on_boot_sec:
            timer_content += f"OnBootSec={systemd_config.on_boot_sec}\n"
        if systemd_config.on_startup_sec:
            timer_content += f"OnStartupSec={systemd_config.on_startup_sec}\n"
        if systemd_config.on_unit_active_sec:
            timer_content += f"OnUnitActiveSec={systemd_config.on_unit_active_sec}\n"

        # Add timer options
        if systemd_config.randomized_delay_sec:
            timer_content += f"RandomizedDelaySec={systemd_config.randomized_delay_sec}\n"
        if systemd_config.persistent:
            timer_content += "Persistent=true\n"

        timer_content += f"""
[Install]
WantedBy={systemd_config.wanted_by}
"""

        return timer_content

    def get_service_name(self) -> str:
        """Get the systemd service name."""
        service_name = self.config.metadata.name or f"ansible-runner-{self.config_file_path.stem}"
        return self._sanitize_service_name(service_name)

    def get_service_file_path(self, system_wide: bool = False) -> Path:
        """Get the path where the service file should be installed."""
        service_name = self.get_service_name()

        if system_wide:
            return Path(f"/etc/systemd/system/{service_name}.service")
        else:
            # User service
            user_systemd_dir = Path.home() / ".config" / "systemd" / "user"
            return user_systemd_dir / f"{service_name}.service"

    def get_timer_file_path(self, system_wide: bool = False) -> Path:
        """Get the path where the timer file should be installed."""
        service_name = self.get_service_name()

        if system_wide:
            return Path(f"/etc/systemd/system/{service_name}.timer")
        else:
            # User timer
            user_systemd_dir = Path.home() / ".config" / "systemd" / "user"
            return user_systemd_dir / f"{service_name}.timer"

    def install_service(self, system_wide: bool = False, enable: bool = True) -> str:
        """Install the systemd service and optionally timer."""
        service_content = self.generate_service_file_content()
        service_file_path = self.get_service_file_path(system_wide)

        # Create directory if it doesn't exist
        service_file_path.parent.mkdir(parents=True, exist_ok=True)

        # Write service file
        with open(service_file_path, 'w') as f:
            f.write(service_content)

        # Install timer if enabled
        timer_file_path = None
        if self.config.systemd.timer_enabled:
            timer_content = self.generate_timer_file_content()
            timer_file_path = self.get_timer_file_path(system_wide)

            with open(timer_file_path, 'w') as f:
                f.write(timer_content)

        # Reload systemd
        systemctl_cmd = ["systemctl"]
        if not system_wide:
            systemctl_cmd.append("--user")

        try:
            # Reload daemon
            subprocess.run(systemctl_cmd + ["daemon-reload"], check=True)

            # Enable service/timer if requested
            if enable and self.config.systemd.enabled:
                if self.config.systemd.timer_enabled:
                    # For timers, enable the timer unit (not the service)
                    timer_name = self.get_service_name() + ".timer"
                    subprocess.run(systemctl_cmd + ["enable", timer_name], check=True)
                else:
                    # For regular services, enable the service
                    subprocess.run(systemctl_cmd + ["enable", self.get_service_name()], check=True)

            if timer_file_path:
                return f"Service: {service_file_path}, Timer: {timer_file_path}"
            else:
                return str(service_file_path)

        except subprocess.CalledProcessError as e:
            raise SystemdServiceError(f"Failed to install systemd service: {e}")

    def uninstall_service(self, system_wide: bool = False) -> bool:
        """Uninstall the systemd service and timer."""
        service_name = self.get_service_name()
        service_file_path = self.get_service_file_path(system_wide)
        timer_file_path = self.get_timer_file_path(system_wide)

        systemctl_cmd = ["systemctl"]
        if not system_wide:
            systemctl_cmd.append("--user")

        try:
            # Stop and disable timer if it exists
            if self.config.systemd.timer_enabled and timer_file_path.exists():
                timer_name = service_name + ".timer"
                subprocess.run(systemctl_cmd + ["stop", timer_name], check=False)
                subprocess.run(systemctl_cmd + ["disable", timer_name], check=False)
                timer_file_path.unlink()

            # Stop service if running
            subprocess.run(systemctl_cmd + ["stop", service_name], check=False)

            # Disable service
            subprocess.run(systemctl_cmd + ["disable", service_name], check=False)

            # Remove service file
            if service_file_path.exists():
                service_file_path.unlink()

            # Reload daemon
            subprocess.run(systemctl_cmd + ["daemon-reload"], check=True)

            return True

        except subprocess.CalledProcessError as e:
            raise SystemdServiceError(f"Failed to uninstall systemd service: {e}")

    def get_service_status(self, system_wide: bool = False) -> dict:
        """Get the status of the systemd service."""
        service_name = self.get_service_name()
        systemctl_cmd = ["systemctl"]
        if not system_wide:
            systemctl_cmd.append("--user")

        try:
            # Get service status
            result = subprocess.run(
                systemctl_cmd + ["status", service_name],
                capture_output=True,
                text=True,
                check=False
            )

            # Get is-enabled status
            enabled_result = subprocess.run(
                systemctl_cmd + ["is-enabled", service_name],
                capture_output=True,
                text=True,
                check=False
            )

            # Get is-active status
            active_result = subprocess.run(
                systemctl_cmd + ["is-active", service_name],
                capture_output=True,
                text=True,
                check=False
            )

            return {
                "name": service_name,
                "active": active_result.stdout.strip(),
                "enabled": enabled_result.stdout.strip(),
                "status": result.stdout,
                "return_code": result.returncode
            }

        except subprocess.CalledProcessError as e:
            raise SystemdServiceError(f"Failed to get service status: {e}")

    def start_timer(self, system_wide: bool = False) -> bool:
        """Start the systemd timer."""
        if not self.config.systemd.timer_enabled:
            raise SystemdServiceError("Timer is not enabled in configuration")

        timer_name = self.get_service_name() + ".timer"
        systemctl_cmd = ["systemctl"]
        if not system_wide:
            systemctl_cmd.append("--user")

        try:
            subprocess.run(systemctl_cmd + ["start", timer_name], check=True)
            return True
        except subprocess.CalledProcessError as e:
            raise SystemdServiceError(f"Failed to start timer: {e}")

    def stop_timer(self, system_wide: bool = False) -> bool:
        """Stop the systemd timer."""
        if not self.config.systemd.timer_enabled:
            raise SystemdServiceError("Timer is not enabled in configuration")

        timer_name = self.get_service_name() + ".timer"
        systemctl_cmd = ["systemctl"]
        if not system_wide:
            systemctl_cmd.append("--user")

        try:
            subprocess.run(systemctl_cmd + ["stop", timer_name], check=True)
            return True
        except subprocess.CalledProcessError as e:
            raise SystemdServiceError(f"Failed to stop timer: {e}")

    def get_timer_status(self, system_wide: bool = False) -> dict:
        """Get the status of the systemd timer."""
        if not self.config.systemd.timer_enabled:
            raise SystemdServiceError("Timer is not enabled in configuration")

        timer_name = self.get_service_name() + ".timer"
        systemctl_cmd = ["systemctl"]
        if not system_wide:
            systemctl_cmd.append("--user")

        try:
            # Get timer status
            result = subprocess.run(
                systemctl_cmd + ["status", timer_name],
                capture_output=True,
                text=True,
                check=False
            )

            # Get is-enabled status
            enabled_result = subprocess.run(
                systemctl_cmd + ["is-enabled", timer_name],
                capture_output=True,
                text=True,
                check=False
            )

            # Get is-active status
            active_result = subprocess.run(
                systemctl_cmd + ["is-active", timer_name],
                capture_output=True,
                text=True,
                check=False
            )

            return {
                "name": timer_name,
                "active": active_result.stdout.strip(),
                "enabled": enabled_result.stdout.strip(),
                "status": result.stdout,
                "return_code": result.returncode
            }

        except subprocess.CalledProcessError as e:
            raise SystemdServiceError(f"Failed to get timer status: {e}")

    def _sanitize_service_name(self, name: str) -> str:
        """Sanitize service name for systemd."""
        # Replace spaces and special chars with hyphens, lowercase
        safe_name = "".join(c if c.isalnum() else "-" for c in name.lower())
        # Remove duplicate hyphens and strip leading/trailing hyphens
        safe_name = "-".join(filter(None, safe_name.split("-")))
        return safe_name

    def _get_current_user(self) -> str:
        """Get current user name."""
        try:
            return pwd.getpwuid(os.getuid()).pw_name
        except:
            return os.getenv("USER", "nobody")

    def _get_python_path(self) -> str:
        """Get the current Python interpreter path."""
        import sys
        return sys.executable