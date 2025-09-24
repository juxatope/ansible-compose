import json
from typing import List
from ..models.ansible_config import AnsibleConfig


class CommandBuilder:
    def __init__(self, config: AnsibleConfig):
        self.config = config

    def build(self) -> List[str]:
        cmd = ["ansible-playbook"]

        # Required: playbook
        cmd.append(self.config.playbook)

        # Add optional parameters
        self._add_inventory(cmd)
        self._add_limit(cmd)
        self._add_extra_vars(cmd)
        self._add_tags(cmd)
        self._add_skip_tags(cmd)
        self._add_check_mode(cmd)
        self._add_diff_mode(cmd)
        self._add_verbosity(cmd)
        self._add_forks(cmd)
        self._add_become_options(cmd)
        self._add_vault_options(cmd)
        self._add_connection_options(cmd)
        self._add_timeout(cmd)
        self._add_start_at_task(cmd)

        return cmd

    def _add_inventory(self, cmd: List[str]) -> None:
        if self.config.inventory:
            cmd.extend(["-i", self.config.inventory])

    def _add_limit(self, cmd: List[str]) -> None:
        if self.config.limit:
            cmd.extend(["-l", self.config.limit])

    def _add_extra_vars(self, cmd: List[str]) -> None:
        if self.config.extra_vars:
            extra_vars = json.dumps(self.config.extra_vars)
            cmd.extend(["-e", extra_vars])

    def _add_tags(self, cmd: List[str]) -> None:
        if self.config.tags:
            if isinstance(self.config.tags, list):
                cmd.extend(["-t", ",".join(self.config.tags)])
            else:
                cmd.extend(["-t", str(self.config.tags)])

    def _add_skip_tags(self, cmd: List[str]) -> None:
        if self.config.skip_tags:
            if isinstance(self.config.skip_tags, list):
                cmd.extend(["--skip-tags", ",".join(self.config.skip_tags)])
            else:
                cmd.extend(["--skip-tags", str(self.config.skip_tags)])

    def _add_check_mode(self, cmd: List[str]) -> None:
        if self.config.check:
            cmd.append("--check")

    def _add_diff_mode(self, cmd: List[str]) -> None:
        if self.config.diff:
            cmd.append("--diff")

    def _add_verbosity(self, cmd: List[str]) -> None:
        if self.config.verbose > 0:
            cmd.append("-" + "v" * min(self.config.verbose, 4))  # Max 4 v's

    def _add_forks(self, cmd: List[str]) -> None:
        if self.config.forks:
            cmd.extend(["-f", str(self.config.forks)])

    def _add_become_options(self, cmd: List[str]) -> None:
        if self.config.become:
            cmd.append("--become")

            if self.config.become_user:
                cmd.extend(["--become-user", self.config.become_user])

            if self.config.become_method:
                cmd.extend(["--become-method", self.config.become_method])

            if self.config.become_password_file:
                cmd.extend(["--become-password-file", self.config.become_password_file])

    def _add_vault_options(self, cmd: List[str]) -> None:
        if self.config.vault_password_file:
            cmd.extend(["--vault-password-file", self.config.vault_password_file])

    def _add_connection_options(self, cmd: List[str]) -> None:
        if self.config.private_key:
            cmd.extend(["--private-key", self.config.private_key])

        if self.config.connection:
            cmd.extend(["-c", self.config.connection])

        if self.config.connection_password_file:
            cmd.extend(["--connection-password-file", self.config.connection_password_file])

    def _add_timeout(self, cmd: List[str]) -> None:
        if self.config.timeout:
            cmd.extend(["-T", str(self.config.timeout)])

    def _add_start_at_task(self, cmd: List[str]) -> None:
        if self.config.start_at_task:
            cmd.extend(["--start-at-task", self.config.start_at_task])

    def get_command_string(self) -> str:
        return " ".join(self.build())