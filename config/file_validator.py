import os
import stat
from pathlib import Path
from typing import List, Optional


class FileValidationError(Exception):
    pass


class FileValidator:
    @staticmethod
    def validate_file_exists(file_path: str, file_type: str = "file") -> None:
        """Validate that a file exists and is readable."""
        if not file_path:
            return  # Optional file not provided

        path = Path(file_path)
        if not path.exists():
            raise FileValidationError(f"{file_type} not found: {file_path}")

        if not path.is_file():
            raise FileValidationError(f"{file_type} is not a regular file: {file_path}")

        if not os.access(path, os.R_OK):
            raise FileValidationError(f"{file_type} is not readable: {file_path}")

    @staticmethod
    def validate_private_key_permissions(file_path: str) -> None:
        """Validate private key file has secure permissions (600 or 400)."""
        if not file_path:
            return

        FileValidator.validate_file_exists(file_path, "Private key file")

        path = Path(file_path)
        file_mode = path.stat().st_mode
        permissions = stat.filemode(file_mode)

        # Check if file is readable by owner only (600 or 400)
        if file_mode & 0o077:  # Check if group or others have any permissions
            raise FileValidationError(
                f"Private key file has insecure permissions {permissions}: {file_path}. "
                f"Should be 600 or 400 (owner read/write or owner read-only)"
            )

    @staticmethod
    def validate_password_file_permissions(file_path: str, file_type: str = "Password file") -> None:
        """Validate password file has secure permissions (600, 400, or at least not world-readable)."""
        if not file_path:
            return

        FileValidator.validate_file_exists(file_path, file_type)

        path = Path(file_path)
        file_mode = path.stat().st_mode
        permissions = stat.filemode(file_mode)

        # Check if file is world-readable (dangerous for password files)
        if file_mode & 0o004:  # Others have read permission
            raise FileValidationError(
                f"{file_type} is world-readable {permissions}: {file_path}. "
                f"This is insecure for password files"
            )

    @staticmethod
    def validate_ansible_files(config) -> List[str]:
        """Validate all file-based configuration options."""
        warnings = []

        try:
            # Validate password files
            if config.vault_password_file:
                FileValidator.validate_password_file_permissions(
                    config.vault_password_file, "Vault password file"
                )

            if config.become_password_file:
                FileValidator.validate_password_file_permissions(
                    config.become_password_file, "Become password file"
                )

            if config.connection_password_file:
                FileValidator.validate_password_file_permissions(
                    config.connection_password_file, "Connection password file"
                )

            # Validate private key with stricter permissions
            if config.private_key:
                FileValidator.validate_private_key_permissions(config.private_key)

            # Validate other files exist
            if config.inventory:
                FileValidator.validate_file_exists(config.inventory, "Inventory file")

            # Validate log directory
            if config.log_directory:
                FileValidator.validate_log_directory(config.log_directory)

        except FileValidationError as e:
            warnings.append(f"Warning: {e}")

        return warnings

    @staticmethod
    def expand_file_paths(config) -> None:
        """Expand user home directory (~) in file paths."""
        if config.vault_password_file:
            config.vault_password_file = os.path.expanduser(config.vault_password_file)

        if config.become_password_file:
            config.become_password_file = os.path.expanduser(config.become_password_file)

        if config.connection_password_file:
            config.connection_password_file = os.path.expanduser(config.connection_password_file)

        if config.private_key:
            config.private_key = os.path.expanduser(config.private_key)

        if config.inventory:
            config.inventory = os.path.expanduser(config.inventory)

        if config.log_directory:
            config.log_directory = os.path.expanduser(config.log_directory)

    @staticmethod
    def validate_log_directory(log_directory: str) -> None:
        """Validate log directory exists and is writable."""
        if not log_directory:
            return

        path = Path(log_directory)

        # Try to create directory if it doesn't exist
        if not path.exists():
            try:
                path.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                raise FileValidationError(f"Cannot create log directory: {log_directory} - {e}")

        # Check if it's a directory
        if not path.is_dir():
            raise FileValidationError(f"Log directory path is not a directory: {log_directory}")

        # Check if writable
        if not os.access(path, os.W_OK):
            raise FileValidationError(f"Log directory is not writable: {log_directory}")