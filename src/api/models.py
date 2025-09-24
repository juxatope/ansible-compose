from pydantic import BaseModel
from typing import Optional, Dict, Any, List


class RunRequest(BaseModel):
    config_file: str
    dry_run: bool = False
    capture_output: bool = False


class RunResponse(BaseModel):
    success: bool
    return_code: int
    command: str
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    duration: Optional[float] = None
    error_message: Optional[str] = None


class ConfigInfoResponse(BaseModel):
    name: Optional[str]
    description: Optional[str]
    run_count: int
    max_runs: Optional[int]
    last_run: Optional[str]
    schedule: Optional[str]
    format: str


class CommandResponse(BaseModel):
    command: str
    valid: bool
    error_message: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    service: str = "ansible-runner-service"