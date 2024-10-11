from pydantic import BaseModel, AliasGenerator, ConfigDict, Field
from pydantic.alias_generators import to_camel
from typing import Literal


class CamelCaseModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=AliasGenerator(alias=to_camel, validation_alias=to_camel),
        populate_by_name=True,
    )


class LogQuery(CamelCaseModel):
    """
    A Pydantic model representing a log query.
    """

    log_name: str = Field(default=..., description="The name of the log file.")
    amount: int = Field(
        default=100,
        description="The amount of log entries to retrieve.",
        ge=0,
        le=10000,
    )
    severity: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO", description="The severity level of the log entries to retrieve."
    )
    order: Literal["asc", "desc"] = Field(
        default="asc",
        description="The order in which to retrieve the log entries. Ascending means oldest first, descending means newest first.",
    )


class LogEntry(CamelCaseModel):
    """
    A Pydantic model representing a log entry.
    """

    timestamp: str
    severity: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    source: str
    message: str


class LogFile(CamelCaseModel):
    """
    A Pydantic model representing a log file.
    """

    name: str = Field(default=..., description="The name of the log file.")
    amount: int = Field(
        default=..., description="The amount of log entries in the log file."
    )


class LogFiles(CamelCaseModel):
    """
    A Pydantic model representing a list of log files.
    """

    log_files: list[LogFile] = Field(default=..., description="A list of log files.")
