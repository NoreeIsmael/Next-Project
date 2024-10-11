from typing import List, Literal, Optional, cast, Tuple, Generator, Any
from logging import DEBUG, INFO, WARNING, ERROR, CRITICAL
from pathlib import Path
from re import match, Match, DOTALL

from backend.lib.api.logs.models import LogEntry
from backend.lib.api.logs import logger

SEVERITY_LEVELS: dict[str, int] = {
    "DEBUG": DEBUG,
    "INFO": INFO,
    "WARNING": WARNING,
    "ERROR": ERROR,
    "CRITICAL": CRITICAL,
}

HasLogSeverity = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

# Captures the timestamp, log level, source and message of a log line into 4 groups, assuming the log line is in the format:
# [2024-09-17 10:44:45] [DEBUG   ] backend.lib.settings: autosave_on_exit is enabled; registering save method.
LOG_CAPTURE_PATTERN: str = (
    r"\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\] \[(\w+)\s*\] ([\w\s\.]+(?: \([\w\s]+\))?): (.+)"
)


def is_start_of_log_entry(line: str) -> bool:
    return match(pattern=LOG_CAPTURE_PATTERN, string=line) is not None


def parse_log_line(log_line: str) -> Optional[Tuple[str, str, str, str]]:
    _match: Optional[Match[str]] = match(
        pattern=LOG_CAPTURE_PATTERN, string=log_line, flags=DOTALL
    )
    if _match:
        return cast(Tuple[str, str, str, str], _match.groups())
    return None


def read_logs_as_generator(
    log_name: str, order: Literal["asc", "desc"]
) -> Generator[str, Any, None]:
    """
    Reads a log file line by line and yields each line as a generator.

    Args:
        log_name (str): The name of the log file (without extension) to read.

    Yields:
        str: Each line of the log file.

    Raises:
        FileNotFoundError: If the log file does not exist.
        IOError: If an error occurs while trying to read the log file.
    """
    file_path: Path = Path("backend/logs") / f"{log_name}.log"
    if order == "asc":
        try:
            with open(file=file_path, mode="r") as log_file:
                for log_line in log_file:
                    yield log_line

        except FileNotFoundError:
            logger.exception(msg="Log file not found")
            raise
        except IOError:
            logger.exception(msg="An error occurred while trying to read the logs")
            raise
    else:
        try:
            with open(file=file_path, mode="rb") as log_file:
                # Start at the end of the file, create a buffer to
                # store the bytes we read and set the pointer location
                # to the end of the file.
                log_file.seek(0, 2)
                buffer: List[bytes] = []
                pointer_location: int = log_file.tell()
                # Read the file backwards, one byte at a time until we
                # reach the start of the file, or the calling code stops
                while pointer_location >= 0:
                    log_file.seek(pointer_location)
                    new_byte: bytes = log_file.read(1)
                    # If we encounter a newline character and the buffer
                    # is not empty, we have reached the start of a log entry.
                    if new_byte == b"\n" and buffer:
                        line: str = b"".join(buffer[::-1]).decode(encoding="utf-8")
                        if is_start_of_log_entry(line=line):
                            yield line.replace("\r", "\n")
                            buffer = []
                    else:
                        buffer.append(new_byte)
                    pointer_location -= 1
                if buffer:
                    yield b"".join(buffer[::-1]).decode(encoding="utf-8")
        except FileNotFoundError:
            logger.exception(msg="Log file not found")
            raise
        except IOError:
            logger.exception(msg="An error occurred while trying to read the logs")
            raise


def read_logs(
    log_name: str,
    amount: int = 100,
    severity: HasLogSeverity = "INFO",
    order: Literal["asc", "desc"] = "asc",
) -> List[LogEntry]:
    logs: List = []
    log_generator: Generator[str, Any, None] = read_logs_as_generator(
        log_name=log_name, order=order
    )
    severity_level: int = SEVERITY_LEVELS[severity]

    for log_line in log_generator:
        if log_line.strip() == "":
            continue
        parsed_log_line: Optional[Tuple[str, str, str, str]] = parse_log_line(
            log_line=log_line
        )
        if parsed_log_line is None:
            if not len(logs) > 0:
                continue

            previous_log: LogEntry = logs[-1]
            if not SEVERITY_LEVELS[previous_log.severity] <= severity_level:
                continue

            previous_log.message += log_line
            continue

        if not len(logs) >= amount:
            timestamp: str = parsed_log_line[0]
            log_level: HasLogSeverity = cast(HasLogSeverity, parsed_log_line[1])
            source: str = parsed_log_line[2]
            message: str = parsed_log_line[3]
            if SEVERITY_LEVELS[log_level] <= severity_level:
                logs.append(
                    LogEntry(
                        timestamp=timestamp,
                        severity=log_level,
                        source=source,
                        message=message,
                    )
                )
        else:
            break

    return logs


def get_log_file_names_on_disk() -> List[str]:
    """
    Retrieves the names of all log files in the 'backend/logs' directory.

    Returns:
        List[str]: A list of log file names with a '.log' extension.
    """
    return [
        path.stem
        for path in Path("backend/logs").iterdir()
        if path.is_file() and path.suffix == ".log"
    ]
