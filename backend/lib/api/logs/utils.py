from typing import List, Literal, Optional, cast, Tuple, Generator, Any
from logging import DEBUG, INFO, WARNING, ERROR, CRITICAL
from pathlib import Path
from re import match, Match, DOTALL

from backend.lib.api.logs.models import LogEntry, LogFile, LogFiles
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


def read_logs_in_desc_order(log: Path) -> Generator[str, Any, None]:
    """
    Reads a log file in reverse order, yielding each log entry as a string.

    Args:
        log (Path): The path to the log file.

    Yields:
        str: The next log entry in reverse order.

    Notes:
        - The function reads the log file in binary mode to handle potential encoding issues.
        - It seeks to the end of the file and reads backwards, collecting bytes until it encounters a newline character.
        - It assumes that each log entry starts with a specific pattern, which is checked by the `is_start_of_log_entry` function.
        - The function decodes the collected bytes into a UTF-8 string and yields it.
    """
    with open(file=log, mode="rb") as log_file:
        log_file.seek(0, 2)
        buffer: List[bytes] = []
        pointer_location: int = log_file.tell()

        while pointer_location >= 0:
            log_file.seek(pointer_location)
            new_byte: bytes = log_file.read(1)

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


def read_logs_as_generator(
    log: Path, order: Literal["asc", "desc"]
) -> Generator[str, Any, None]:
    """
    Reads a log file line by line and yields each line as a generator.

    Args:
        log (Path): The path to the log file.

    Yields:
        str: Each line of the log file.

    Raises:
        FileNotFoundError: If the log file does not exist.
        IOError: If an error occurs while trying to read the log file.
    """
    if order == "asc":
        try:
            with open(file=log, mode="r") as log_file:
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
            yield from read_logs_in_desc_order(log=log)
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
        log=Path("backend", "logs", f"{log_name}.log"), order=order
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


def get_log_file_names_on_disk(dir: Path = Path("backend", "logs")) -> List[Path]:
    """
    Retrieves the names of all log files in the specified directory.

    Args:
        dir (Path): The directory to search for log files. Defaults to "backend/logs".

    Returns:
        List[Path]: A list of `Path` objects representing the names of all log files in the specified directory.
    """
    return [path for path in dir.iterdir() if path.is_file() and path.suffix == ".log"]


def get_amount_of_logs(path: Path) -> int:
    """
    Retrieves the number of log entries in a log file.

    Args:
        path (Path): The path object representing the log file to
        retrieve the number of log entries for.

    Returns:
        int: The number of log entries in the log file.
    """
    try:
        with open(file=path, mode="r") as log_file:
            return sum(1 for _ in log_file)
    except FileNotFoundError:
        logger.exception(msg="Log file not found")
        raise
    except IOError:
        logger.exception(msg="An error occurred while trying to read the logs")
        raise


def create_log_file_object(log_file: Path) -> LogFile:
    """
    Creates a `LogFile` object containing the name of the log file and the number of log entries in the log file.

    Args:
        log_file (Path): The path object representing the log file to create a `LogFile` object for.

    Returns:
        LogFile: A `LogFile` object containing the name of the log file and the number of log entries in the log file.
    """
    amount: int = get_amount_of_logs(path=log_file)
    return LogFile(name=log_file.stem, amount=amount)


def create_log_files_object(dir: Path = Path("backend", "logs")) -> LogFiles:
    """
    Creates a `LogFiles` object containing the names of all log files in the specified directory
    and the number of log entries in each log file.

    Args:
        dir (Path): The directory to search for log files. Defaults to "backend/logs".

    Returns:
        LogFiles: A `LogFiles` object containing the names of all log files in the specified directory
        and the number of log entries in each log file.
    """
    log_files: List[Path] = get_log_file_names_on_disk(dir=dir)

    log_files_with_amount: List[LogFile] = []

    for log_file in log_files:
        log_files_with_amount.append(create_log_file_object(log_file=log_file))

    return LogFiles(log_files=log_files_with_amount)
