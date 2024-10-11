from fastapi import Request, APIRouter, HTTPException, Depends
from typing import List, Annotated
from pathlib import Path

from backend.lib.api.logs import logger
from backend.lib.api.logs.utils import (
    read_logs,
    create_log_files_object,
)
from backend.lib.api.logs.models import LogEntry, LogFiles, LogQuery

router = APIRouter()


@router.get(path="/logs/get", tags=["logs"], response_model=List[LogEntry])
def get_logs(
    request: Request, log_query: Annotated[LogQuery, Depends(dependency=LogQuery)]
) -> List[LogEntry]:
    try:
        logs: List[LogEntry] = read_logs(
            log_name=log_query.log_name,
            amount=log_query.amount,
            severity=log_query.severity,
            order=log_query.order,
        )
        return logs
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Log file not found")
    except Exception as e:
        logger.error(
            msg="An error occurred while trying to read the logs",
            exc_info=e,
        )
        raise HTTPException(
            status_code=500,
            detail=(
                "An error occurred while trying to read the logs. "
                "Please try again later. If the problem persists, "
                "contact the system administrator. If you are the "
                "system administrator, check the logs on the server "
                "for more information."
            ),
        )


@router.get(path="/logs/get-available", tags=["logs"], response_model=LogFiles)
def get_available_logs(
    request: Request,
) -> LogFiles:
    return create_log_files_object(dir=Path("backend", "logs"))
