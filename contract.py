"""Typed input and output declarations for Event Session Groups."""

from dataclasses import dataclass
from enum import Enum
from typing import Annotated

from slimconfig import Output


class Tool(Enum):
    RUN = "group_sessions"


class Task(Enum):
    RUN = "group-sessions"


@dataclass
class Event(Output):
    event_id: Annotated[str, "Globally unique event identifier"]
    user: Annotated[str, "User identifier"]
    minute: Annotated[int, "Integer event time from 0 through 1000000000"]


@dataclass
class ResultRow(Output):
    user: Annotated[str, "Session user identifier"]
    start: Annotated[int, "First event time"]
    end: Annotated[int, "Last event time, inclusive"]
    event_ids: Annotated[list[str], "Events ordered by (minute, event_id)"]


@dataclass
class TaskInput(Output):
    events: Annotated[list[Event], "At most 200 uniquely identified events"]
    gap: Annotated[int, "Maximum gap joining consecutive events, from 1 through 1440 minutes"]
    destination: Annotated[str, "New relative .json output path, never overwritten"]


@dataclass
class TaskOutput(Output):
    path: Annotated[str, "Artifact path matching destination"]
    records: Annotated[list[ResultRow], "Complete ordered task results"]
    total: Annotated[int, "Number of sessions across all users"]


TOOLS = {Tool.RUN: (TaskInput, TaskOutput)}
TASKS = {Task.RUN: (TaskInput, TaskOutput)}
