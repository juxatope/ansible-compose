import asyncio
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime

from ..input.models import AnsibleConfig, ExecutionMode
from .command_builder import CommandBuilder
from ..deliverables.logging import LogManager, MultiPlaybookLogger
from .executor import ExecutionResult, AnsibleExecutionError


@dataclass
class PlaybookExecutionResult:
    """Result of a single playbook execution."""
    name: str
    success: bool
    return_code: int
    stdout: str
    stderr: str
    start_time: float
    end_time: float
    retries_used: int = 0
    error_message: Optional[str] = None

    @property
    def duration(self) -> float:
        return self.end_time - self.start_time


@dataclass
class MultiPlaybookExecutionResult:
    """Result of multi-playbook execution."""
    success: bool
    playbook_results: List[PlaybookExecutionResult]
    total_duration: float
    execution_mode: str
    summary: Dict[str, Any]

    @property
    def failed_playbooks(self) -> List[PlaybookExecutionResult]:
        return [r for r in self.playbook_results if not r.success]

    @property
    def successful_playbooks(self) -> List[PlaybookExecutionResult]:
        return [r for r in self.playbook_results if r.success]


class MultiPlaybookExecutor:
    """Execute multiple Ansible playbooks in serial or parallel with progress monitoring."""

    def __init__(self, config: AnsibleConfig, capture_output: bool = False, log_manager: Optional[LogManager] = None,
                show_progress: bool = False):
        self.config = config
        self.capture_output = capture_output
        self.log_manager = log_manager
        self.show_progress = show_progress
        self.command_builder = CommandBuilder(config)

        # Initialize multi-playbook logger if log_manager is available
        self.multi_logger: Optional[MultiPlaybookLogger] = None
        if self.log_manager and self.log_manager.log_directory:
            run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
            self.multi_logger = self.log_manager.create_multi_playbook_logger(run_id)
            if self.show_progress:
                print(f"Multi-Playbook Execution Started - Run ID: {run_id}")
                print(f"Log Directory: {self.multi_logger.get_run_directory()}/")
                print("=" * 62)

    def execute(self, dry_run: bool = False) -> MultiPlaybookExecutionResult:
        """Execute all playbooks according to configuration."""
        start_time = time.time()

        commands = self.command_builder.build_all()
        playbook_results = []

        # Show execution plan if progress is enabled
        if self.show_progress:
            self._display_execution_plan(commands)

        # Log execution start
        if self.multi_logger:
            self.multi_logger.log_info(f"Starting {len(commands)} playbooks in {self.config.execution_mode.value} mode")

        if self.config.execution_mode == ExecutionMode.SERIAL:
            playbook_results = self._execute_serial(commands, dry_run)
        else:
            playbook_results = self._execute_parallel(commands, dry_run)

        end_time = time.time()
        total_duration = end_time - start_time

        # Calculate summary
        successful = len([r for r in playbook_results if r.success])
        failed = len(playbook_results) - successful
        overall_success = failed == 0

        summary = {
            'total_playbooks': len(playbook_results),
            'successful': successful,
            'failed': failed,
            'execution_groups': len(set(cmd['execution_group'] for cmd in commands)),
            'total_duration': total_duration,
            'average_duration': total_duration / len(playbook_results) if playbook_results else 0,
            'execution_mode': self.config.execution_mode.value,
            'start_time': start_time,
            'end_time': end_time,
            'playbook_results': [
                {
                    'name': r.name,
                    'success': r.success,
                    'duration': r.duration,
                    'retries_used': r.retries_used,
                    'error_message': r.error_message
                } for r in playbook_results
            ]
        }

        # Log final summary
        if self.multi_logger:
            self.multi_logger.log_execution_summary(summary)

        # Show final progress if enabled
        if self.show_progress:
            self._display_final_summary(playbook_results, total_duration, overall_success)

        return MultiPlaybookExecutionResult(
            success=overall_success,
            playbook_results=playbook_results,
            total_duration=total_duration,
            execution_mode=self.config.execution_mode.value,
            summary=summary
        )

    def _execute_serial(self, commands: List[Dict[str, Any]], dry_run: bool) -> List[PlaybookExecutionResult]:
        """Execute playbooks serially, respecting dependency groups."""
        results = []

        # Group by execution group
        groups = {}
        for cmd in commands:
            group = cmd['execution_group']
            if group not in groups:
                groups[group] = []
            groups[group].append(cmd)

        # Execute each group
        for group_index in sorted(groups.keys()):
            group_commands = groups[group_index]

            for cmd in group_commands:
                result = self._execute_single_playbook(cmd, dry_run)
                results.append(result)

                # Check if we should continue on error
                if not result.success and not cmd.get('continue_on_error', False):
                    # Stop execution if playbook failed and continue_on_error is False
                    self._log_error(f"Stopping execution due to failure in playbook: {cmd['name']}")
                    break

        return results

    def _execute_parallel(self, commands: List[Dict[str, Any]], dry_run: bool) -> List[PlaybookExecutionResult]:
        """Execute playbooks in parallel, respecting dependency groups."""
        results = []

        # Group by execution group
        groups = {}
        for cmd in commands:
            group = cmd['execution_group']
            if group not in groups:
                groups[group] = []
            groups[group].append(cmd)

        # Execute each group (groups are still sequential, but within group is parallel)
        for group_index in sorted(groups.keys()):
            group_commands = groups[group_index]

            if len(group_commands) == 1:
                # Single playbook in group - execute directly
                result = self._execute_single_playbook(group_commands[0], dry_run)
                results.append(result)
            else:
                # Multiple playbooks in group - execute in parallel
                group_results = self._execute_group_parallel(group_commands, dry_run)
                results.extend(group_results)

            # Check if any critical failures occurred
            group_failures = [r for r in results[-len(group_commands):] if not r.success]
            critical_failures = [
                r for r in group_failures
                if not any(cmd['continue_on_error'] for cmd in group_commands if cmd['name'] == r.name)
            ]

            if critical_failures:
                self._log_error(f"Stopping execution due to critical failures in group {group_index}")
                break

        return results

    def _execute_group_parallel(self, commands: List[Dict[str, Any]], dry_run: bool) -> List[PlaybookExecutionResult]:
        """Execute a group of playbooks in parallel using ThreadPoolExecutor."""
        results = []

        with ThreadPoolExecutor(max_workers=len(commands)) as executor:
            # Submit all tasks
            future_to_command = {
                executor.submit(self._execute_single_playbook, cmd, dry_run): cmd
                for cmd in commands
            }

            # Collect results as they complete
            for future in as_completed(future_to_command):
                result = future.result()
                results.append(result)

                # Log completion and show progress
                if result.success:
                    self._log_info(f"Playbook {result.name} completed: SUCCESS ({result.duration:.2f}s)")
                    if self.show_progress:
                        self._show_progress_update(result.name, "✓ SUCCESS", result.duration, result.retries_used)
                else:
                    self._log_error(f"Playbook {result.name} completed: FAILED ({result.duration:.2f}s)")
                    if self.show_progress:
                        self._show_progress_update(result.name, "✗ FAILED", result.duration, result.retries_used)

        return results

    def _execute_single_playbook(self, command_info: Dict[str, Any], dry_run: bool) -> PlaybookExecutionResult:
        """Execute a single playbook with retry logic."""
        name = command_info['name']
        command = command_info['command']
        max_retries = command_info.get('max_retries', 0)
        retry_delay = command_info.get('retry_delay', 5)

        self._log_info(f"Starting playbook: {name}")
        if self.show_progress:
            self._show_progress_start(name, command_info)

        for attempt in range(max_retries + 1):  # +1 for initial attempt
            if attempt > 0:
                self._log_info(f"Retrying playbook {name} (attempt {attempt + 1}/{max_retries + 1})")
                if self.show_progress:
                    print(f"  {name}: Retrying... (attempt {attempt + 1}/{max_retries + 1})")
                time.sleep(retry_delay)

            start_time = time.time()

            try:
                if dry_run:
                    # Add --check flag for dry run
                    command_with_check = command.copy()
                    if "--check" not in command_with_check:
                        command_with_check.append("--check")
                    result = self._run_command(command_with_check)
                else:
                    result = self._run_command(command)

                end_time = time.time()

                if result.returncode == 0:
                    self._log_info(f"Playbook {name} completed successfully")
                    return PlaybookExecutionResult(
                        name=name,
                        success=True,
                        return_code=result.returncode,
                        stdout=result.stdout,
                        stderr=result.stderr,
                        start_time=start_time,
                        end_time=end_time,
                        retries_used=attempt
                    )
                else:
                    error_msg = f"Playbook failed with return code {result.returncode}"
                    if attempt == max_retries:  # Last attempt
                        self._log_error(f"Playbook {name} failed after {attempt + 1} attempts")
                        return PlaybookExecutionResult(
                            name=name,
                            success=False,
                            return_code=result.returncode,
                            stdout=result.stdout,
                            stderr=result.stderr,
                            start_time=start_time,
                            end_time=end_time,
                            retries_used=attempt,
                            error_message=error_msg
                        )

            except Exception as e:
                end_time = time.time()
                error_msg = f"Exception during execution: {str(e)}"

                if attempt == max_retries:  # Last attempt
                    self._log_error(f"Playbook {name} failed with exception: {error_msg}")
                    return PlaybookExecutionResult(
                        name=name,
                        success=False,
                        return_code=-1,
                        stdout="",
                        stderr=str(e),
                        start_time=start_time,
                        end_time=end_time,
                        retries_used=attempt,
                        error_message=error_msg
                    )

    def _run_command(self, command: List[str]) -> subprocess.CompletedProcess:
        """Run a single ansible command."""
        # Set up environment and working directory
        env = self._setup_environment()
        cwd = Path(self.config.working_directory) if self.config.working_directory else None

        # Log the command being executed
        self._log_info(f"Executing: {' '.join(command)}")

        # Run the command
        if self.capture_output:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                env=env,
                cwd=cwd
            )
        else:
            result = subprocess.run(
                command,
                env=env,
                cwd=cwd
            )
            # Create a result-like object for consistency
            result.stdout = ""
            result.stderr = ""

        return result

    def _setup_environment(self) -> Dict[str, str]:
        """Set up environment variables for ansible execution."""
        env = dict(os.environ)

        # Set log file if we have multi-logger
        if self.multi_logger:
            # For multi-playbook, we set up individual log files per playbook
            # This will be handled in the playbook-specific execution
            pass
        elif self.log_manager:
            # Fallback to single log file
            log_file = self.log_manager.get_current_log_file()
            if log_file:
                env['ANSIBLE_LOG_PATH'] = str(log_file)

        return env

    def _log_info(self, message: str, playbook_name: str = None) -> None:
        """Log an info message."""
        if self.multi_logger:
            self.multi_logger.log_info(message, playbook_name)
        elif self.log_manager:
            self.log_manager.log_info(message)
        else:
            print(f"[MultiPlaybookExecutor] INFO: {message}")

    def _log_error(self, message: str, playbook_name: str = None) -> None:
        """Log an error message."""
        if self.multi_logger:
            self.multi_logger.log_error(message, playbook_name)
        elif self.log_manager:
            self.log_manager.log_error(message)
        else:
            print(f"[MultiPlaybookExecutor] ERROR: {message}")

    def _display_execution_plan(self, commands: List[Dict[str, Any]]) -> None:
        """Display the execution plan with progress monitoring."""
        print("\nExecution Plan:")
        print("-" * 40)

        # Group by execution group
        groups = {}
        for cmd in commands:
            group = cmd['execution_group']
            if group not in groups:
                groups[group] = []
            groups[group].append(cmd)

        for group_index in sorted(groups.keys()):
            group_commands = groups[group_index]
            group_type = "PARALLEL" if len(group_commands) > 1 else "SERIAL"

            print(f"\nGroup {group_index} ({len(group_commands)} playbook{'s' if len(group_commands) > 1 else ''} - {group_type}):")

            for cmd in group_commands:
                extras = []
                if cmd['dependencies']:
                    extras.append(f"depends on: {', '.join(cmd['dependencies'])}")
                if cmd['max_retries'] > 0:
                    extras.append(f"retries: {cmd['max_retries']}")
                if cmd.get('continue_on_error', False):
                    extras.append("continue on error")

                extra_info = f" [{', '.join(extras)}]" if extras else ""
                print(f"  • {cmd['name']}: {cmd['playbook_config'].playbook}{extra_info}")

        print()

    def _show_progress_start(self, name: str, command_info: Dict[str, Any]) -> None:
        """Show that a playbook has started."""
        extras = []
        if command_info['max_retries'] > 0:
            extras.append(f"retries: {command_info['max_retries']}")
        if command_info.get('continue_on_error', False):
            extras.append("continue on error")

        extra_info = f" [{', '.join(extras)}]" if extras else ""
        print(f"  {name}{extra_info}: ⏳ Running...")

    def _show_progress_update(self, name: str, status: str, duration: float, retries: int = 0) -> None:
        """Show progress update for a completed playbook."""
        retry_info = f" (retries: {retries})" if retries > 0 else ""
        print(f"  {name}: {status} ({duration:.2f}s){retry_info}")

    def _display_final_summary(self, results: List[PlaybookExecutionResult], total_duration: float, success: bool) -> None:
        """Display the final execution summary."""
        print("\n" + "=" * 62)
        status_color = "SUCCESS" if success else "FAILED"
        print(f"Execution Complete: {status_color}")
        print("=" * 62)

        successful = len([r for r in results if r.success])
        failed = len(results) - successful

        print(f"Total Duration: {total_duration:.2f}s")
        print(f"Successful: {successful}/{len(results)}")

        if failed > 0:
            print(f"Failed: {failed}")
            print("\nFailed Playbooks:")
            for result in results:
                if not result.success:
                    print(f"  • {result.name}: {result.error_message}")

        if self.multi_logger:
            print(f"\nLogs available at: {self.multi_logger.get_run_directory()}/")
        print()

    def get_execution_plan(self) -> Dict[str, Any]:
        """Get the execution plan for the configured playbooks."""
        return self.command_builder.get_execution_plan()


# Import os for environment setup
import os