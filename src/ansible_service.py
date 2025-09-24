from pathlib import Path
from typing import Optional

from .config.loader import ConfigLoader
from .commands.builder import CommandBuilder
from .execution.executor import AnsibleExecutor, ExecutionResult
from .metadata.manager import MetadataManager, RunLimitExceeded
from .models.ansible_config import AnsibleConfig
from .logging.log_manager import LogManager
from .systemd.service_generator import SystemdServiceGenerator


class AnsibleService:
    def __init__(self, config_file: str | Path, capture_output: bool = False):
        self.config_loader = ConfigLoader(config_file)

        # Initialize log manager based on config
        config = self.load_config()
        self.log_manager = LogManager(
            log_directory=config.log_directory,
            log_level=config.log_level
        ) if config.log_directory else None

        self.executor = AnsibleExecutor(
            capture_output=capture_output,
            log_manager=self.log_manager
        )
        self.metadata_manager = MetadataManager(self.config_loader)
        self.systemd_generator = SystemdServiceGenerator(config, str(config_file))

    def load_config(self) -> AnsibleConfig:
        return self.config_loader.load()

    def run_playbook(self, dry_run: bool = False, skip_metadata_update: bool = False) -> ExecutionResult:
        config = self.load_config()

        # Check run limits
        try:
            self.metadata_manager.validate_run_limits(config)
        except RunLimitExceeded as e:
            raise e

        # Build command
        command_builder = CommandBuilder(config)
        command = command_builder.build()

        if dry_run:
            print("Dry run - would execute:")
            print(command_builder.get_command_string())
            return ExecutionResult(return_code=0, command=command)

        # Display metadata
        run_info = self.metadata_manager.get_run_info(config)
        if run_info["name"]:
            print(f"Running: {run_info['name']}")
        if run_info["description"]:
            print(f"Description: {run_info['description']}")

        print(f"Command: {command_builder.get_command_string()}")
        print("-" * 50)

        # Execute command with run name for logging
        run_name = run_info["name"]
        result = self.executor.execute(
            command,
            dry_run=dry_run,
            run_name=run_name,
            working_directory=config.working_directory
        )

        # Update metadata if execution was successful or if configured to always update
        if not skip_metadata_update and (result.return_code == 0 or not dry_run):
            updated_config = self.metadata_manager.update_run_metadata(config)
            self.metadata_manager.save_metadata(updated_config)

        return result

    def get_run_info(self) -> dict:
        config = self.load_config()
        return self.metadata_manager.get_run_info(config)

    def build_command(self) -> str:
        config = self.load_config()
        command_builder = CommandBuilder(config)
        return command_builder.get_command_string()

    def validate_config(self) -> AnsibleConfig:
        config = self.load_config()
        config.validate()
        return config

    @property
    def config_format(self) -> str:
        return self.config_loader.format

    def get_log_summary(self) -> Optional[dict]:
        """Get summary of log files."""
        if self.log_manager:
            return self.log_manager.get_log_summary()
        return None

    def cleanup_old_logs(self, max_age_days: int = 30, max_files: int = 100) -> int:
        """Clean up old log files."""
        if self.log_manager:
            return self.log_manager.cleanup_old_logs(max_age_days, max_files)
        return 0

    def get_recent_log_content(self, lines: int = 50) -> Optional[str]:
        """Get recent log content."""
        if self.log_manager:
            return self.log_manager.tail_log(lines)
        return None

    def generate_systemd_service(self) -> str:
        """Generate systemd service file content."""
        return self.systemd_generator.generate_service_file_content()

    def install_systemd_service(self, system_wide: bool = False, enable: bool = True) -> str:
        """Install systemd service."""
        return self.systemd_generator.install_service(system_wide, enable)

    def uninstall_systemd_service(self, system_wide: bool = False) -> bool:
        """Uninstall systemd service."""
        return self.systemd_generator.uninstall_service(system_wide)

    def get_systemd_service_status(self, system_wide: bool = False) -> dict:
        """Get systemd service status."""
        return self.systemd_generator.get_service_status(system_wide)

    def get_systemd_service_name(self) -> str:
        """Get systemd service name."""
        return self.systemd_generator.get_service_name()

    def generate_systemd_timer(self) -> str:
        """Generate systemd timer file content."""
        return self.systemd_generator.generate_timer_file_content()

    def start_systemd_timer(self, system_wide: bool = False) -> bool:
        """Start systemd timer."""
        return self.systemd_generator.start_timer(system_wide)

    def stop_systemd_timer(self, system_wide: bool = False) -> bool:
        """Stop systemd timer."""
        return self.systemd_generator.stop_timer(system_wide)

    def get_systemd_timer_status(self, system_wide: bool = False) -> dict:
        """Get systemd timer status."""
        return self.systemd_generator.get_timer_status(system_wide)