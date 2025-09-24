from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime


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
        return {
            "enabled": self.enabled,
            "user": self.user,
            "working_directory": self.working_directory,
            "environment_file": self.environment_file,
            "restart": self.restart,
            "restart_sec": self.restart_sec,
            "wanted_by": self.wanted_by,
            "after": self.after,
            "requires": self.requires,
            "service_type": self.service_type,
            "timeout_start_sec": self.timeout_start_sec,
            "timeout_stop_sec": self.timeout_stop_sec,
            "timer_enabled": self.timer_enabled,
            "on_calendar": self.on_calendar,
            "on_boot_sec": self.on_boot_sec,
            "on_startup_sec": self.on_startup_sec,
            "on_unit_active_sec": self.on_unit_active_sec,
            "randomized_delay_sec": self.randomized_delay_sec,
            "persistent": self.persistent
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SystemdConfig':
        return cls(
            enabled=data.get("enabled", False),
            user=data.get("user"),
            working_directory=data.get("working_directory"),
            environment_file=data.get("environment_file"),
            restart=data.get("restart", "on-failure"),
            restart_sec=data.get("restart_sec", 5),
            wanted_by=data.get("wanted_by", "multi-user.target"),
            after=data.get("after", ["network.target"]),
            requires=data.get("requires", []),
            service_type=data.get("service_type", "simple"),
            timeout_start_sec=data.get("timeout_start_sec", 60),
            timeout_stop_sec=data.get("timeout_stop_sec", 30),
            timer_enabled=data.get("timer_enabled", False),
            on_calendar=data.get("on_calendar"),
            on_boot_sec=data.get("on_boot_sec"),
            on_startup_sec=data.get("on_startup_sec"),
            on_unit_active_sec=data.get("on_unit_active_sec"),
            randomized_delay_sec=data.get("randomized_delay_sec"),
            persistent=data.get("persistent", False)
        )


@dataclass
class MetadataConfig:
    name: Optional[str] = None
    description: Optional[str] = None
    run_count: int = 0
    max_runs: Optional[int] = None
    last_run: Optional[str] = None
    schedule: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "run_count": self.run_count,
            "max_runs": self.max_runs,
            "last_run": self.last_run,
            "schedule": self.schedule
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MetadataConfig':
        return cls(
            name=data.get("name"),
            description=data.get("description"),
            run_count=data.get("run_count", 0),
            max_runs=data.get("max_runs"),
            last_run=data.get("last_run"),
            schedule=data.get("schedule")
        )


@dataclass
class AnsibleConfig:
    playbook: str
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
        result = {
            "playbook": self.playbook,
            "inventory": self.inventory,
            "limit": self.limit,
            "extra_vars": self.extra_vars,
            "tags": self.tags,
            "skip_tags": self.skip_tags,
            "check": self.check,
            "diff": self.diff,
            "verbose": self.verbose,
            "forks": self.forks,
            "become": self.become,
            "become_user": self.become_user,
            "become_method": self.become_method,
            "become_password_file": self.become_password_file,
            "vault_password_file": self.vault_password_file,
            "private_key": self.private_key,
            "connection": self.connection,
            "connection_password_file": self.connection_password_file,
            "timeout": self.timeout,
            "start_at_task": self.start_at_task,
            "working_directory": self.working_directory,
            "log_directory": self.log_directory,
            "log_level": self.log_level,
            "metadata": self.metadata.to_dict(),
            "systemd": self.systemd.to_dict()
        }
        # Remove None values for cleaner serialization
        return {k: v for k, v in result.items() if v is not None}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AnsibleConfig':
        metadata_data = data.get("metadata", {})
        metadata = MetadataConfig.from_dict(metadata_data) if metadata_data else MetadataConfig()

        systemd_data = data.get("systemd", {})
        systemd = SystemdConfig.from_dict(systemd_data) if systemd_data else SystemdConfig()

        return cls(
            playbook=data["playbook"],
            inventory=data.get("inventory"),
            limit=data.get("limit"),
            extra_vars=data.get("extra_vars", {}),
            tags=data.get("tags"),
            skip_tags=data.get("skip_tags"),
            check=data.get("check", False),
            diff=data.get("diff", False),
            verbose=data.get("verbose", 0),
            forks=data.get("forks"),
            become=data.get("become", False),
            become_user=data.get("become_user"),
            become_method=data.get("become_method"),
            become_password_file=data.get("become_password_file"),
            vault_password_file=data.get("vault_password_file"),
            private_key=data.get("private_key"),
            connection=data.get("connection"),
            connection_password_file=data.get("connection_password_file"),
            timeout=data.get("timeout"),
            start_at_task=data.get("start_at_task"),
            working_directory=data.get("working_directory"),
            log_directory=data.get("log_directory"),
            log_level=data.get("log_level", "INFO"),
            metadata=metadata,
            systemd=systemd
        )

    def validate(self) -> None:
        if not self.playbook:
            raise ValueError("playbook is required in configuration")