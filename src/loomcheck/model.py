"""Immutable data contracts for LoomCheck reports and schedules."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class Decision:
    """One scheduler decision at an explicit checkpoint boundary."""

    step: int
    chosen: str
    runnable: tuple[str, ...]
    labels: tuple[str, ...]


@dataclass(frozen=True)
class Failure:
    """A stable, user-facing failure fingerprint."""

    kind: str
    message: str
    task: str | None = None
    traceback: str | None = None

    @property
    def fingerprint(self) -> str:
        return ":".join((self.kind, self.task or "", self.message))


@dataclass(frozen=True)
class RunResult:
    """The complete result of one deterministic runtime execution."""

    success: bool
    requested_schedule: tuple[str, ...] = ()
    schedule: tuple[str, ...] = ()
    decisions: tuple[Decision, ...] = ()
    failure: Failure | None = None
    divergences: tuple[str, ...] = ()
    steps: int = 0
    duration_ms: float = 0.0

    @property
    def failed(self) -> bool:
        return not self.success

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ExplorationResult:
    """Summary of a bounded exploration campaign."""

    runs: tuple[RunResult, ...]
    exhausted: bool
    max_runs: int
    max_steps: int
    minimized_failure: RunResult | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @property
    def success(self) -> bool:
        return self.minimized_failure is None

    @property
    def failures(self) -> tuple[RunResult, ...]:
        return tuple(run for run in self.runs if run.failed)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Schedule:
    """Validated, JSON-friendly schedule prefix."""

    choices: tuple[str, ...] = ()

    @classmethod
    def from_value(cls, value: Any) -> Schedule:
        if value is None:
            return cls()
        if not isinstance(value, list | tuple):
            raise TypeError("schedule must be a JSON array or tuple of task names")
        if any(not isinstance(item, str) or not item for item in value):
            raise ValueError("every schedule choice must be a non-empty string")
        return cls(tuple(value))

    def to_list(self) -> list[str]:
        return list(self.choices)
