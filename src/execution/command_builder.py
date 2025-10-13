import json
from typing import List, Dict, Any, Callable
from ..input.models import AnsibleConfig, PlaybookConfig


class CommandBuilder:
    def __init__(self, config: AnsibleConfig):
        self.config = config
        self._option_builders = self._init_option_builders()

    def _init_option_builders(self) -> Dict[str, Callable[[List[str]], None]]:
        """Initialize mapping of config attributes to their command builders."""
        return {
            'inventory': lambda cmd: self._add_option(cmd, self.config.inventory, ["-i"]),
            'limit': lambda cmd: self._add_option(cmd, self.config.limit, ["-l"]),
            'extra_vars': lambda cmd: self._add_option(cmd, json.dumps(self.config.extra_vars) if self.config.extra_vars else None, ["-e"]),
            'tags': lambda cmd: self._add_list_option(cmd, self.config.tags, ["-t"]),
            'skip_tags': lambda cmd: self._add_list_option(cmd, self.config.skip_tags, ["--skip-tags"]),
            'check': lambda cmd: self._add_flag(cmd, self.config.check, "--check"),
            'diff': lambda cmd: self._add_flag(cmd, self.config.diff, "--diff"),
            'verbose': lambda cmd: cmd.append("-" + "v" * min(self.config.verbose, 4)) if self.config.verbose > 0 else None,
            'forks': lambda cmd: self._add_option(cmd, self.config.forks, ["-f"], str),
            'become': lambda cmd: self._add_conditional_options(cmd, self.config.become, [
                (True, ["--become"]),
                (self.config.become_user, ["--become-user", self.config.become_user]),
                (self.config.become_method, ["--become-method", self.config.become_method]),
                (self.config.become_password_file, ["--become-password-file", self.config.become_password_file])
            ]),
            'vault_password_file': lambda cmd: self._add_option(cmd, self.config.vault_password_file, ["--vault-password-file"]),
            'connection': lambda cmd: self._add_multiple_options(cmd, [
                (self.config.private_key, ["--private-key", self.config.private_key]),
                (self.config.connection, ["-c", self.config.connection]),
                (self.config.connection_password_file, ["--connection-password-file", self.config.connection_password_file])
            ]),
            'timeout': lambda cmd: self._add_option(cmd, self.config.timeout, ["-T"], str),
            'start_at_task': lambda cmd: self._add_option(cmd, self.config.start_at_task, ["--start-at-task"]),
        }

    def build(self) -> List[str]:
        cmd = ["ansible-playbook", self.config.playbook]

        # Apply all option builders
        for builder in self._option_builders.values():
            builder(cmd)

        return cmd

    def _add_option(self, cmd: List[str], value: Any, flags: List[str], converter: Callable = None) -> None:
        """Generic method to add command options."""
        if value:
            cmd.extend(flags)
            if converter:
                cmd.append(converter(value))
            else:
                cmd.append(str(value))

    def _add_flag(self, cmd: List[str], condition: bool, flag: str) -> None:
        """Add boolean flags to command."""
        if condition:
            cmd.append(flag)

    def _add_list_option(self, cmd: List[str], value: Any, flags: List[str]) -> None:
        """Add list options (tags, skip-tags) that need comma-joining."""
        if value:
            if isinstance(value, list):
                cmd.extend(flags + [",".join(value)])
            else:
                cmd.extend(flags + [str(value)])

    def _add_conditional_options(self, cmd: List[str], condition: bool, options: List[tuple]) -> None:
        """Add multiple options only if base condition is met."""
        if condition:
            for opt_condition, opt_args in options:
                if opt_condition:
                    cmd.extend(opt_args)

    def _add_multiple_options(self, cmd: List[str], options: List[tuple]) -> None:
        """Add multiple independent options."""
        for condition, args in options:
            if condition:
                cmd.extend(args)


    def build_all(self) -> List[Dict[str, Any]]:
        """Build commands for all playbooks (single or multiple) with execution metadata."""
        playbook_configs = self.config.get_playbook_configs()

        if len(playbook_configs) == 1:
            # Single playbook - return simple format
            return [{
                'name': playbook_configs[0].name or 'default',
                'command': self.build(),
                'playbook_config': playbook_configs[0],
                'dependencies': [],
                'execution_group': 0
            }]

        # Multiple playbooks - resolve dependencies and build commands
        dependency_groups = self._resolve_dependencies(playbook_configs)
        commands = []

        for group_index, group in enumerate(dependency_groups):
            commands.extend(
                self._build_command_for_playbook(playbook_config, group_index)
                for playbook_config in group
            )

        return commands

    def _resolve_dependencies(self, playbook_configs: List[PlaybookConfig]) -> List[List[PlaybookConfig]]:
        """Resolve dependencies into execution groups for parallel processing."""
        processed = set()
        groups = []

        while len(processed) < len(playbook_configs):
            # Find playbooks that can run now (dependencies satisfied)
            current_group = [
                config for config in playbook_configs
                if config.name not in processed and
                all(dep in processed for dep in config.depends_on)
            ]

            if not current_group:
                # Circular dependency or missing dependency
                remaining = [c.name for c in playbook_configs if c.name not in processed]
                raise ValueError(f"Circular dependency or missing dependency detected. Remaining playbooks: {remaining}")

            groups.append(current_group)
            processed.update(config.name for config in current_group)

        return groups

    def _build_command_for_playbook(self, playbook_config: PlaybookConfig, group_index: int) -> Dict[str, Any]:
        """Build a single command dict for a playbook."""
        # Create a temporary config for this specific playbook
        temp_config = self._create_single_config(playbook_config)
        temp_builder = CommandBuilder(temp_config)

        return {
            'name': playbook_config.name,
            'command': temp_builder.build(),
            'playbook_config': playbook_config,
            'dependencies': playbook_config.depends_on.copy(),
            'execution_group': group_index,
            'max_retries': playbook_config.max_retries,
            'retry_delay': playbook_config.retry_delay,
            'continue_on_error': playbook_config.continue_on_error
        }

    def _create_single_config(self, playbook_config: PlaybookConfig) -> AnsibleConfig:
        """Create a single-playbook AnsibleConfig from a PlaybookConfig."""
        # Start with base config as dict, then override with playbook-specific values
        base_dict = self.config.__dict__.copy()

        # Override with playbook-specific values
        playbook_overrides = {
            'playbook': playbook_config.playbook,
            'inventory': playbook_config.inventory,
            'limit': playbook_config.limit,
            'extra_vars': playbook_config.extra_vars,
            'tags': playbook_config.tags,
            'skip_tags': playbook_config.skip_tags,
            'timeout': playbook_config.timeout or self.config.timeout,
            'playbooks': None,  # Clear multi-playbook config
        }

        # Remove None values to avoid overriding base config with None
        playbook_overrides = {k: v for k, v in playbook_overrides.items() if v is not None}

        # Merge configurations
        merged_config = {**base_dict, **playbook_overrides}

        return AnsibleConfig(**merged_config)

    def get_execution_plan(self) -> Dict[str, Any]:
        """Get a human-readable execution plan."""
        commands = self.build_all()

        plan = {
            'execution_mode': self.config.execution_mode.value if hasattr(self.config, 'execution_mode') else 'serial',
            'total_playbooks': len(commands),
            'groups': []
        }

        # Group by execution group using functional approach
        from itertools import groupby
        from operator import itemgetter

        # Group commands by execution_group
        sorted_commands = sorted(commands, key=itemgetter('execution_group'))
        groups_map = {
            group_index: list(group_commands)
            for group_index, group_commands in groupby(sorted_commands, key=itemgetter('execution_group'))
        }

        plan['groups'] = [
            self._build_group_info(group_index, group_commands)
            for group_index, group_commands in groups_map.items()
        ]

        return plan

    def _build_group_info(self, group_index: int, group_commands: List[Dict]) -> Dict[str, Any]:
        """Build group info for execution plan."""
        return {
            'group': group_index,
            'parallel': len(group_commands) > 1 or (hasattr(self.config, 'execution_mode') and self.config.execution_mode.value == 'parallel'),
            'playbooks': [
                {
                    'name': cmd['name'],
                    'playbook': cmd['playbook_config'].playbook,
                    'dependencies': cmd['dependencies'],
                    'max_retries': cmd['max_retries'],
                    'continue_on_error': cmd['continue_on_error']
                }
                for cmd in group_commands
            ]
        }

    def get_command_string(self) -> str:
        return " ".join(self.build())