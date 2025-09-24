from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import logging
from pathlib import Path

from .models import (
    RunRequest, RunResponse, ConfigInfoResponse,
    CommandResponse, HealthResponse
)
from ..ansible_service import AnsibleService
from ..metadata.manager import RunLimitExceeded
from ..config.loader import ConfigFormatError
from ..execution.executor import AnsibleExecutionError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Ansible Runner Service",
    description="A microservice for running Ansible playbooks with configuration management",
    version="1.0.0"
)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(status="healthy")


@app.post("/run", response_model=RunResponse)
async def run_playbook(request: RunRequest):
    try:
        service = AnsibleService(
            config_file=request.config_file,
            capture_output=request.capture_output
        )

        result = service.run_playbook(dry_run=request.dry_run)

        return RunResponse(
            success=result.return_code == 0,
            return_code=result.return_code,
            command=" ".join(result.command),
            stdout=result.stdout,
            stderr=result.stderr,
            duration=result.duration
        )

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    except RunLimitExceeded as e:
        raise HTTPException(status_code=429, detail=str(e))

    except ConfigFormatError as e:
        raise HTTPException(status_code=400, detail=str(e))

    except AnsibleExecutionError as e:
        return RunResponse(
            success=False,
            return_code=e.result.return_code,
            command=" ".join(e.result.command),
            stdout=e.result.stdout,
            stderr=e.result.stderr,
            duration=e.result.duration,
            error_message=str(e)
        )

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/config/{config_file:path}/info", response_model=ConfigInfoResponse)
async def get_config_info(config_file: str):
    try:
        if not Path(config_file).exists():
            raise HTTPException(status_code=404, detail=f"Configuration file not found: {config_file}")

        service = AnsibleService(config_file)
        run_info = service.get_run_info()

        return ConfigInfoResponse(
            name=run_info["name"],
            description=run_info["description"],
            run_count=run_info["run_count"],
            max_runs=run_info["max_runs"],
            last_run=run_info["last_run"],
            schedule=run_info["schedule"],
            format=service.config_format
        )

    except ConfigFormatError as e:
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        logger.error(f"Error getting config info: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/config/{config_file:path}/command", response_model=CommandResponse)
async def get_command(config_file: str):
    try:
        if not Path(config_file).exists():
            raise HTTPException(status_code=404, detail=f"Configuration file not found: {config_file}")

        service = AnsibleService(config_file)
        command = service.build_command()

        # Validate config
        try:
            service.validate_config()
            return CommandResponse(command=command, valid=True)
        except Exception as e:
            return CommandResponse(command=command, valid=False, error_message=str(e))

    except ConfigFormatError as e:
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        logger.error(f"Error building command: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={"detail": "Endpoint not found"}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)