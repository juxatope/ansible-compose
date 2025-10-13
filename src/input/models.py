from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from enum import Enum


class ExecutionMode(Enum):
    SERIAL = "serial"
    PARALLEL = "parallel"

######################################################
@dataclass
class SystemdConfig:
    enabled: bool = False
    user: Optional[str] = None
    working_directory: Optional[str] = None
    environment_file: Optional[str] = None
    restart: str = "on-failure"
    restart_sec: int = 5
    wanted_by: str = "multi-user.target"
    after: List[str] = field(default_factory=lambda: ["network.target"])
    requires: List[str] = field(default_factory=list)
    service_type: str = "simple"
    timeout_start_sec: int = 60
    timeout_stop_sec: int = 30
    # Timer configuration
    timer_enabled: bool = False
    on_calendar: Optional[str] = None  # e.g., "*:0/15" for every 15 minutes
    on_boot_sec: Optional[str] = None  # e.g., "15min" - delay after boot
    on_startup_sec: Optional[str] = None  # e.g., "30sec" - delay after systemd start
    on_unit_active_sec: Optional[str] = None  # e.g., "1h" - repeat interval after completion
    randomized_delay_sec: Optional[str] = None  # e.g., "5min" - random delay
    persistent: bool = False  # Run missed timers at startup

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SystemdConfig':
        # Filter to only include fields that exist in the dataclass
        valid_fields = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**valid_fields)

######################################################
@dataclass
class MetadataConfig:
    name: Optional[str] = None
    description: Optional[str] = None
    run_count: int = 0
    max_runs: Optional[int] = None
    last_run: Optional[str] = None
    schedule: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MetadataConfig':
        valid_fields = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**valid_fields)

#####################################################
@dataclass
class PlaybookConfig:
    """Configuration for a single playbook in a multi-playbook setup."""
    name: Optional[str] = None
    playbook: Optional[str] = None
    inventory: Optional[str] = None
    limit: Optional[str] = None
    extra_vars: Dict[str, Any] = field(default_factory=dict)
    tags: Optional[List[str] | str] = None
    skip_tags: Optional[List[str] | str] = None
    depends_on: List[str] = field(default_factory=list)  # List of playbook names to wait for
    timeout: Optional[int] = None
    max_retries: int = 0
    retry_delay: int = 5  # seconds
    continue_on_error: bool = False  # Continue other playbooks if this one fails

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PlaybookConfig':
        valid_fields = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**valid_fields)

#####################################################
@dataclass
class AnsibleConfig:
    # Single playbook (backwards compatible)
    playbook: Optional[str] = None
    # Multiple playbooks (new feature)
    playbooks: Optional[List[Union[str, PlaybookConfig]]] = None
    execution_mode: ExecutionMode = ExecutionMode.SERIAL
    inventory: Optional[str] = None
    limit: Optional[str] = None
    extra_vars: Dict[str, Any] = field(default_factory=dict)
    tags: Optional[List[str] | str] = None
    skip_tags: Optional[List[str] | str] = None
    check: bool = False
    diff: bool = False
    verbose: int = 0
    forks: Optional[int] = None
    become: bool = False
    become_user: Optional[str] = None
    become_method: Optional[str] = None
    become_password_file: Optional[str] = None
    vault_password_file: Optional[str] = None
    private_key: Optional[str] = None
    connection: Optional[str] = None
    connection_password_file: Optional[str] = None
    timeout: Optional[int] = None
    start_at_task: Optional[str] = None
    working_directory: Optional[str] = None
    log_directory: Optional[str] = None
    log_level: str = "INFO"
    metadata: MetadataConfig = field(default_factory=MetadataConfig)
    systemd: SystemdConfig = field(default_factory=SystemdConfig)

    def to_dict(self) -> Dict[str, Any]:
        # Use asdict but customize enum and nested object handling
        result = asdict(self)

        # Convert execution_mode enum to string
        result["execution_mode"] = self.execution_mode.value

        # Remove None values for cleaner serialization
        return {k: v for k, v in result.items() if v is not None}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AnsibleConfig':
        # Parse nested metadata config
        metadata = MetadataConfig.from_dict(data.get("metadata", {}))

        # Parse nested systemd config
        systemd = SystemdConfig.from_dict(data.get("systemd", {}))

        # Parse playbooks - handle both single and multiple formats
        playbooks = None
        if "playbooks" in data:
            playbooks = [
                pb if isinstance(pb, str) else PlaybookConfig.from_dict(pb)
                for pb in data["playbooks"]
            ]

        # Parse execution mode enum
        execution_mode = ExecutionMode.SERIAL
        if "execution_mode" in data:
            mode_str = data["execution_mode"].lower()
            execution_mode = ExecutionMode.PARALLEL if mode_str == "parallel" else ExecutionMode.SERIAL

        # Get valid fields, excluding nested objects and special cases
        exclude_fields = {"metadata", "systemd", "playbooks", "execution_mode"}
        valid_fields = {
            k: v for k, v in data.items()
            if k in cls.__dataclass_fields__ and k not in exclude_fields
        }

        # Combine everything
        return cls(
            **valid_fields,
            metadata=metadata,
            systemd=systemd,
            playbooks=playbooks,
            execution_mode=execution_mode
        )

    def validate(self) -> None:
        # Validate that either playbook or playbooks is provided
        if not self.playbook and not self.playbooks:
            raise ValueError("Either 'playbook' or 'playbooks' is required in configuration")

        # Validate that both aren't provided
        if self.playbook and self.playbooks:
            raise ValueError("Cannot specify both 'playbook' and 'playbooks' - use one or the other")

        # Validate playbooks if provided
        if self.playbooks:
            if not isinstance(self.playbooks, list) or len(self.playbooks) == 0:
                raise ValueError("'playbooks' must be a non-empty list")

            # Collect playbook names for dependency validation
            playbook_names = set()
            for i, pb in enumerate(self.playbooks):
                if isinstance(pb, str):
                    # Simple string format - no validation needed
                    continue
                elif isinstance(pb, PlaybookConfig):
                    if not pb.playbook:
                        raise ValueError(f"Playbook {i} missing 'playbook' field")

                    # Collect name for dependency validation
                    if pb.name:
                        if pb.name in playbook_names:
                            raise ValueError(f"Duplicate playbook name: '{pb.name}'")
                        playbook_names.add(pb.name)

                    # Validate dependencies
                    for dep in pb.depends_on:
                        if dep not in playbook_names:
                            # For now, just warn - we'll validate at runtime
                            pass
                else:
                    raise ValueError(f"Invalid playbook configuration at index {i}")

    def is_multi_playbook(self) -> bool:
        """Check if this configuration uses multiple playbooks."""
        return self.playbooks is not None

    def get_playbook_configs(self) -> List[PlaybookConfig]:
        """Get a list of PlaybookConfig objects for all playbooks."""
        if self.playbook:
            # Single playbook - convert to PlaybookConfig
            return [PlaybookConfig(
                name="default",
                playbook=self.playbook,
                inventory=self.inventory,
                limit=self.limit,
                extra_vars=self.extra_vars,
                tags=self.tags,
                skip_tags=self.skip_tags,
                timeout=self.timeout
            )]
        elif self.playbooks:
            # Multiple playbooks
            configs = []
            for i, pb in enumerate(self.playbooks):
                if isinstance(pb, str):
                    # Convert string to PlaybookConfig with defaults from main config
                    config = PlaybookConfig(
                        name=f"playbook_{i}",
                        playbook=pb,
                        inventory=self.inventory,
                        limit=self.limit,
                        extra_vars=self.extra_vars.copy(),
                        tags=self.tags,
                        skip_tags=self.skip_tags,
                        timeout=self.timeout
                    )
                    configs.append(config)
                else:
                    # Already a PlaybookConfig - merge with defaults
                    config = PlaybookConfig(
                        name=pb.name or f"playbook_{i}",
                        playbook=pb.playbook,
                        inventory=pb.inventory or self.inventory,
                        limit=pb.limit or self.limit,
                        extra_vars={**self.extra_vars, **pb.extra_vars},
                        tags=pb.tags or self.tags,
                        skip_tags=pb.skip_tags or self.skip_tags,
                        depends_on=pb.depends_on,
                        timeout=pb.timeout or self.timeout,
                        max_retries=pb.max_retries,
                        retry_delay=pb.retry_delay,
                        continue_on_error=pb.continue_on_error
                    )
                    configs.append(config)
            return configs
        else:
            return []