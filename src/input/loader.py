import json
import yaml
from typing import Dict, Any
from pathlib import Path

from .models import AnsibleConfig
from .validator import FileValidator


class ConfigFormatError(Exception):
    pass


class ConfigLoader:
    def __init__(self, config_path: str | Path):
        self.config_path = Path(config_path)
        self.file_format = self._detect_format()

    def _detect_format(self) -> str:
        suffix = self.config_path.suffix.lower()
        if suffix in ['.yml', '.yaml']:
            return 'yaml'
        elif suffix == '.json':
            return 'json'
        else:
            # Try to detect based on content or default to JSON
            return 'json'

    def load(self) -> AnsibleConfig:
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")

        try:
            with open(self.config_path, 'r') as f:
                if self.file_format == 'yaml':
                    data = yaml.safe_load(f)
                else:
                    data = json.load(f)

            if not isinstance(data, dict):
                raise ConfigFormatError("Configuration must be a JSON object or YAML document")

            config = AnsibleConfig.from_dict(data)
            config.validate()

            # Expand file paths (handle ~ for home directory)
            FileValidator.expand_file_paths(config)

            # Validate files and show warnings
            warnings = FileValidator.validate_ansible_files(config)
            for warning in warnings:
                print(warning)

            return config

        except (json.JSONDecodeError, yaml.YAMLError) as e:
            raise ConfigFormatError(f"Invalid {self.file_format.upper()} in configuration file: {e}")
        except Exception as e:
            raise ConfigFormatError(f"Error loading configuration: {e}")

    def save(self, config: AnsibleConfig) -> None:
        try:
            data = config.to_dict()
            with open(self.config_path, 'w') as f:
                if self.file_format == 'yaml':
                    yaml.dump(data, f, default_flow_style=False, indent=2)
                else:
                    json.dump(data, f, indent=2)
        except Exception as e:
            raise ConfigFormatError(f"Error saving configuration: {e}")

    @property
    def format(self) -> str:
        return self.file_format