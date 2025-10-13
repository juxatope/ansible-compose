import subprocess
import os
from typing import List, Optional
from dataclasses import dataclass
from pathlib import Path
from contextlib import contextmanager


@dataclass
class ExecutionResult:
    return_code: int
    command: List[str]
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    duration: Optional[float] = None
    log_file: Optional[str] = None


class AnsibleExecutionError(Exception):
    def __init__(self, message: str, result: ExecutionResult):
        super().__init__(message)
        self.result = result


class AnsibleExecutor:
    def __init__(self, capture_output: bool = False, log_manager=None):
        self.capture_output = capture_output
        self.log_manager = log_manager

    @contextmanager
    def _change_directory(self, working_directory: Optional[str]):
        """Context manager to temporarily change working directory."""
        if not working_directory:
            yield
            return

        original_dir = os.getcwd()
        try:
            os.chdir(working_directory)
            yield
        finally:
            os.chdir(original_dir)

    def execute(self, command: List[str], dry_run: bool = False, run_name: Optional[str] = None, working_directory: Optional[str] = None) -> ExecutionResult:
        if dry_run:
            return ExecutionResult(
                return_code=0,
                command=command,
                stdout="Dry run - would execute command",
                stderr=None
            )

        # Setup logging if log manager is available
        log_file_path = None
        if self.log_manager:
            log_file_path = self.log_manager.setup_ansible_logging(run_name)

        # Execute in the specified working directory
        with self._change_directory(working_directory):
            try:
                import time
                start_time = time.time()

                if self.capture_output:
                    result = subprocess.run(
                        command,
                        check=False,
                        capture_output=True,
                        text=True
                    )
                    execution_result = ExecutionResult(
                        return_code=result.returncode,
                        command=command,
                        stdout=result.stdout,
                        stderr=result.stderr,
                        duration=time.time() - start_time,
                        log_file=log_file_path
                    )
                else:
                    result = subprocess.run(command, check=False)
                    execution_result = ExecutionResult(
                        return_code=result.returncode,
                        command=command,
                        duration=time.time() - start_time,
                        log_file=log_file_path
                    )

                return execution_result

            except FileNotFoundError:
                raise AnsibleExecutionError(
                    "ansible-playbook command not found. Is Ansible installed?",
                    ExecutionResult(return_code=1, command=command, log_file=log_file_path)
                )
            except Exception as e:
                raise AnsibleExecutionError(
                    f"Error executing command: {e}",
                    ExecutionResult(return_code=1, command=command, log_file=log_file_path)
                )

    def execute_with_output(self, command: List[str], dry_run: bool = False, run_name: Optional[str] = None, working_directory: Optional[str] = None) -> ExecutionResult:
        original_capture = self.capture_output
        self.capture_output = True
        try:
            return self.execute(command, dry_run, run_name, working_directory)
        finally:
            self.capture_output = original_capture

    @staticmethod
    def format_command(command: List[str]) -> str:
        return " ".join(command)