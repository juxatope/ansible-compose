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