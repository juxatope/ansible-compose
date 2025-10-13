import os
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple
import shutil


class LogManager:
    def __init__(self, log_directory: Optional[str] = None, log_level: str = "INFO"):
        self.log_directory = Path(log_directory) if log_directory else None
        self.log_level = getattr(logging, log_level.upper(), logging.INFO)
        self.current_log_file = None

        if self.log_directory:
            self._ensure_log_directory()

    def _ensure_log_directory(self) -> None:
        """Create log directory if it doesn't exist."""
        if self.log_directory and not self.log_directory.exists():
            self.log_directory.mkdir(parents=True, exist_ok=True)

    def get_log_file_path(self, run_name: Optional[str] = None) -> Optional[Path]:
        """Generate a unique log file path for this execution."""
        if not self.log_directory:
            return None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if run_name:
            # Sanitize run name for filename
            safe_name = "".join(c for c in run_name if c.isalnum() or c in (' ', '-', '_')).strip()
            safe_name = safe_name.replace(' ', '_')
            filename = f"{safe_name}_{timestamp}.log"
        else:
            filename = f"ansible_run_{timestamp}.log"

        return self.log_directory / filename

    def setup_ansible_logging(self, run_name: Optional[str] = None) -> Optional[str]:
        """Setup logging for Ansible execution and return log file path."""
        if not self.log_directory:
            return None

        log_file = self.get_log_file_path(run_name)
        self.current_log_file = log_file

        # Set environment variable for Ansible to use our log file
        if log_file:
            os.environ['ANSIBLE_LOG_PATH'] = str(log_file)
            return str(log_file)

        return None

    def cleanup_old_logs(self, max_age_days: int = 30, max_files: int = 100) -> int:
        """Clean up old log files based on age and count."""
        if not self.log_directory or not self.log_directory.exists():
            return 0

        log_files = list(self.log_directory.glob("*.log"))
        removed_count = 0

        # Sort by modification time (newest first)
        log_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)

        # Remove files older than max_age_days
        cutoff_time = datetime.now().timestamp() - (max_age_days * 24 * 3600)
        for log_file in log_files[:]:
            if log_file.stat().st_mtime < cutoff_time:
                try:
                    log_file.unlink()
                    log_files.remove(log_file)
                    removed_count += 1
                except OSError:
                    pass

        # Remove excess files if we have more than max_files
        if len(log_files) > max_files:
            for log_file in log_files[max_files:]:
                try:
                    log_file.unlink()
                    removed_count += 1
                except OSError:
                    pass

        return removed_count

    def get_log_summary(self) -> dict:
        """Get summary information about logs."""
        if not self.log_directory or not self.log_directory.exists():
            return {
                "log_directory": None,
                "total_files": 0,
                "total_size_mb": 0,
                "oldest_log": None,
                "newest_log": None
            }

        log_files = list(self.log_directory.glob("*.log"))

        if not log_files:
            return {
                "log_directory": str(self.log_directory),
                "total_files": 0,
                "total_size_mb": 0,
                "oldest_log": None,
                "newest_log": None
            }

        # Calculate total size
        total_size = sum(f.stat().st_size for f in log_files)
        total_size_mb = total_size / (1024 * 1024)

        # Find oldest and newest
        log_files.sort(key=lambda x: x.stat().st_mtime)
        oldest = log_files[0]
        newest = log_files[-1]

        return {
            "log_directory": str(self.log_directory),
            "total_files": len(log_files),
            "total_size_mb": round(total_size_mb, 2),
            "oldest_log": {
                "file": oldest.name,
                "date": datetime.fromtimestamp(oldest.stat().st_mtime).isoformat()
            },
            "newest_log": {
                "file": newest.name,
                "date": datetime.fromtimestamp(newest.stat().st_mtime).isoformat()
            }
        }

    def tail_log(self, lines: int = 50) -> Optional[str]:
        """Get the last N lines from the current log file."""
        if not self.current_log_file or not self.current_log_file.exists():
            return None

        try:
            with open(self.current_log_file, 'r') as f:
                all_lines = f.readlines()
                return ''.join(all_lines[-lines:])
        except Exception:
            return None

    def get_log_content(self, log_filename: str) -> Optional[str]:
        """Get full content of a specific log file."""
        if not self.log_directory:
            return None

        log_file = self.log_directory / log_filename
        if not log_file.exists():
            return None

        try:
            with open(log_file, 'r') as f:
                return f.read()
        except Exception:
            return None

    def get_current_log_file(self) -> Optional[Path]:
        """Get the current log file path."""
        return self.current_log_file

    def log_info(self, message: str) -> None:
        """Log an info message to the current log file and console."""
        self._log_message(logging.INFO, message)

    def log_error(self, message: str) -> None:
        """Log an error message to the current log file and console."""
        self._log_message(logging.ERROR, message)

    def log_warning(self, message: str) -> None:
        """Log a warning message to the current log file and console."""
        self._log_message(logging.WARNING, message)

    def log_debug(self, message: str) -> None:
        """Log a debug message to the current log file and console."""
        self._log_message(logging.DEBUG, message)

    def _log_message(self, level: int, message: str) -> None:
        """Internal method to log messages."""
        # Create timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"

        # Log to console
        if level >= logging.ERROR:
            print(f"ERROR: {message}")
        elif level >= logging.WARNING:
            print(f"WARNING: {message}")
        elif level >= logging.INFO:
            print(f"INFO: {message}")
        elif level >= logging.DEBUG and self.log_level <= logging.DEBUG:
            print(f"DEBUG: {message}")

        # Log to file if we have a current log file
        if self.current_log_file:
            try:
                with open(self.current_log_file, 'a') as f:
                    f.write(formatted_message + '\n')
            except Exception as e:
                print(f"Failed to write to log file: {e}")

    def create_multi_playbook_logger(self, run_id: str) -> 'MultiPlaybookLogger':
        """Create a specialized logger for multi-playbook execution."""
        if not self.log_directory:
            raise ValueError("Log directory must be configured for multi-playbook logging")

        return MultiPlaybookLogger(self.log_directory, run_id, self.log_level)


class MultiPlaybookLogger:
    """Specialized logger for multi-playbook execution with individual playbook logs."""

    def __init__(self, base_log_directory: Path, run_id: str, log_level: int = logging.INFO):
        self.run_id = run_id
        self.log_level = log_level

        # Create run-specific directory
        self.run_log_directory = base_log_directory / "multi-playbook" / run_id
        self.run_log_directory.mkdir(parents=True, exist_ok=True)

        # Main execution log
        self.execution_log = self.run_log_directory / "execution.log"
        self.summary_file = self.run_log_directory / "execution-summary.json"

        # Individual playbook logs
        self.playbook_logs = {}

        # Initialize execution log
        self._log_to_file(self.execution_log, f"Multi-playbook execution started - Run ID: {run_id}")

    def get_playbook_logger(self, playbook_name: str) -> Path:
        """Get or create a log file for a specific playbook."""
        if playbook_name not in self.playbook_logs:
            log_file = self.run_log_directory / f"{playbook_name}.log"
            self.playbook_logs[playbook_name] = log_file
            self._log_to_file(log_file, f"Playbook '{playbook_name}' execution log started")

        return self.playbook_logs[playbook_name]

    def log_info(self, message: str, playbook_name: Optional[str] = None) -> None:
        """Log an info message to execution log and optionally to playbook log."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted_message = f"[{timestamp}] INFO: {message}"

        # Always log to execution log
        self._log_to_file(self.execution_log, formatted_message)

        # Log to specific playbook log if provided
        if playbook_name:
            playbook_log = self.get_playbook_logger(playbook_name)
            self._log_to_file(playbook_log, formatted_message)

        # Console output
        print(f"INFO: {message}")

    def log_error(self, message: str, playbook_name: Optional[str] = None) -> None:
        """Log an error message."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted_message = f"[{timestamp}] ERROR: {message}"

        self._log_to_file(self.execution_log, formatted_message)

        if playbook_name:
            playbook_log = self.get_playbook_logger(playbook_name)
            self._log_to_file(playbook_log, formatted_message)

        print(f"ERROR: {message}")

    def log_warning(self, message: str, playbook_name: Optional[str] = None) -> None:
        """Log a warning message."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted_message = f"[{timestamp}] WARNING: {message}"

        self._log_to_file(self.execution_log, formatted_message)

        if playbook_name:
            playbook_log = self.get_playbook_logger(playbook_name)
            self._log_to_file(playbook_log, formatted_message)

        print(f"WARNING: {message}")

    def log_playbook_start(self, playbook_name: str, command: list) -> None:
        """Log the start of a playbook execution."""
        message = f"Starting playbook '{playbook_name}': {' '.join(command)}"
        self.log_info(message, playbook_name)

    def log_playbook_complete(self, playbook_name: str, success: bool, duration: float, retries: int = 0) -> None:
        """Log the completion of a playbook."""
        status = "SUCCESS" if success else "FAILED"
        retry_info = f" (retries: {retries})" if retries > 0 else ""
        message = f"Playbook '{playbook_name}' completed: {status} ({duration:.2f}s){retry_info}"

        if success:
            self.log_info(message, playbook_name)
        else:
            self.log_error(message, playbook_name)

    def log_execution_summary(self, summary_data: dict) -> None:
        """Log the final execution summary."""
        import json

        # Write JSON summary
        with open(self.summary_file, 'w') as f:
            json.dump(summary_data, f, indent=2, default=str)

        # Log summary to execution log
        self.log_info("Execution completed")
        self.log_info(f"Total Duration: {summary_data.get('total_duration', 0):.2f}s")
        self.log_info(f"Successful: {summary_data.get('successful', 0)}/{summary_data.get('total_playbooks', 0)}")
        if summary_data.get('failed', 0) > 0:
            self.log_error(f"Failed: {summary_data.get('failed', 0)} playbooks")

    def get_run_directory(self) -> Path:
        """Get the run log directory path."""
        return self.run_log_directory

    def _log_to_file(self, file_path: Path, message: str) -> None:
        """Write a message to a specific log file."""
        try:
            with open(file_path, 'a') as f:
                f.write(message + '\n')
        except Exception as e:
            print(f"Failed to write to log file {file_path}: {e}")