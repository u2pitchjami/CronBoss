# utils/types.py
from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
import subprocess
from typing import Literal, Protocol, TypedDict

# ---------- Schedule ----------
HoursField = Literal["any"] | list[int]
MinutesField = list[int]


class WeekdaySpec(TypedDict):
    weekday: list[int]  # 0=Mon .. 6=Sun


DaysField = Literal["any"] | list[int] | WeekdaySpec


# ---------- Notifications ----------
class NotificationsCfg(TypedDict, total=False):
    notify_on: list[Literal["failure", "success", "success_with_warnings", "retry"]]
    channels: list[str]


# ---------- Cleanup ----------
class CleanupRule(TypedDict, total=False):
    keep_days: int  # ex: 14
    keep_last: int  # ex: 30
    extensions: list[str] | Literal["all"]  # ["all"] ou liste d'extensions [".log", ".gz"]
    recursive: bool
    dry_run: bool


class CleanupCfg(TypedDict, total=False):
    paths: list[str]  # chemins de dossiers
    rule: CleanupRule


# ---------- Task ----------
class TaskConfig(TypedDict, total=False):
    type: Literal["python", "bash"]
    script: str
    args: str
    hours: HoursField
    minutes: MinutesField
    days: DaysField
    interpreter: str
    enabled: bool
    exclusive: bool
    cleanup: CleanupCfg
    notifications: NotificationsCfg
    retries: int
    retry_delay: int
    timeout: int
    timeout_mode: Literal["strict", "soft"]


# ---------- Runtime ----------
InterpretersMap = Mapping[str, str]


class StartHandle(TypedDict):
    proc: subprocess.Popen[str]


Status = Literal["success", "failure", "retry", "success_with_warnings", "Non"]


class TaskWithSource(TaskConfig, total=False):
    source_file: str


class RunHandle(StartHandle, total=False):
    cmd: list[str]
    script: str


class TaskLike(Protocol):
    """
    Interface minimale utilisée par les notifiers.
    """

    script: Path
    notifications: NotificationsCfg


class Notifier(Protocol):
    """
    Contrat pour tous les notifiers (Discord, Email, etc.).
    """

    def send(self, task: TaskLike, status: Status, **kwargs: object) -> None: ...
    def send_summary(self, content: str) -> None: ...


class SummaryPayload(TypedDict):
    success: int
    success_with_warnings: int
    failure: int
    total_duration: float
