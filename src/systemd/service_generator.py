import os
import pwd
import subprocess
from pathlib import Path
from typing import Optional

from ..models.ansible_config import AnsibleConfig


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

        service_content += f"""
[Service]
Type={systemd_config.service_type}
User={systemd_config.user or self._get_current_user()}
WorkingDirectory={working_dir}
ExecStart={python_path} {main_script} run {self.config_file_path}
Restart={systemd_config.restart}
RestartSec={systemd_config.restart_sec}
TimeoutStartSec={systemd_config.timeout_start_sec}
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

    def install_service(self, system_wide: bool = False, enable: bool = True) -> str:
        """Install the systemd service."""
        service_content = self.generate_service_file_content()
        service_file_path = self.get_service_file_path(system_wide)

        # Create directory if it doesn't exist
        service_file_path.parent.mkdir(parents=True, exist_ok=True)

        # Write service file
        with open(service_file_path, 'w') as f:
            f.write(service_content)

        # Reload systemd
        systemctl_cmd = ["systemctl"]
        if not system_wide:
            systemctl_cmd.append("--user")

        try:
            # Reload daemon
            subprocess.run(systemctl_cmd + ["daemon-reload"], check=True)

            # Enable service if requested
            if enable and self.config.systemd.enabled:
                subprocess.run(systemctl_cmd + ["enable", self.get_service_name()], check=True)

            return str(service_file_path)

        except subprocess.CalledProcessError as e:
            raise SystemdServiceError(f"Failed to install systemd service: {e}")

    def uninstall_service(self, system_wide: bool = False) -> bool:
        """Uninstall the systemd service."""
        service_name = self.get_service_name()
        service_file_path = self.get_service_file_path(system_wide)

        systemctl_cmd = ["systemctl"]
        if not system_wide:
            systemctl_cmd.append("--user")

        try:
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