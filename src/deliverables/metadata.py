from datetime import datetime
from typing import Optional

from ..input.models import AnsibleConfig, MetadataConfig
from ..input.loader import ConfigLoader


class RunLimitExceeded(Exception):
    pass


class MetadataManager:
    def __init__(self, config_loader: ConfigLoader):
        self.config_loader = config_loader

    def check_run_limits(self, config: AnsibleConfig) -> bool:
        metadata = config.metadata
        if metadata.max_runs and metadata.run_count >= metadata.max_runs:
            return False
        return True

    def validate_run_limits(self, config: AnsibleConfig) -> None:
        if not self.check_run_limits(config):
            raise RunLimitExceeded(
                f"Maximum runs ({config.metadata.max_runs}) exceeded. "
                f"Current count: {config.metadata.run_count}"
            )

    def update_run_metadata(self, config: AnsibleConfig) -> AnsibleConfig:
        config.metadata.run_count += 1
        config.metadata.last_run = datetime.now().isoformat()
        return config

    def save_metadata(self, config: AnsibleConfig) -> None:
        try:
            self.config_loader.save(config)
        except Exception as e:
            # Log warning but don't fail the execution
            print(f"Warning: Could not update metadata: {e}")

    def get_run_info(self, config: AnsibleConfig) -> dict:
        metadata = config.metadata
        return {
            "name": metadata.name,
            "description": metadata.description,
            "run_count": metadata.run_count,
            "max_runs": metadata.max_runs,
            "last_run": metadata.last_run,
            "schedule": metadata.schedule
        }