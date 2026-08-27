"""Deterministic cooperative scheduler for asyncio scenarios."""

from __future__ import annotations

import asyncio
import inspect
import time
import traceback
from collections.abc import Awaitable, Callable, Coroutine
from dataclasses import dataclass
from typing import Any, TypeVar, cast

from .model import Decision, Failure, RunResult, Schedule

T = TypeVar("T")
Scenario = Callable[["Loom"], Awaitable[None]]


class LoomError(Exception):
    """Base exception for invalid LoomCheck usage."""


@dataclass
class _Request:
    task: asyncio.Task[object]
    name: str
    label: str
    released: asyncio.Future[None]


class Loom:
    """Run cooperative async code under a deterministic scheduling policy.

    User code must call ``await loom.checkpoint("label")`` at meaningful
    state-transition boundaries. ``start_soon`` accepts already-created
    coroutine objects, mirroring the small part of asyncio's API needed by
    scenarios while keeping task ownership inside the runtime.
    """

    def __init__(
        self,
        *,
        schedule: Schedule | None = None,
        max_steps: int = 100,
    ) -> None:
        if max_steps < 1:
            raise ValueError("max_steps must be at least 1")
        self.schedule = schedule if schedule is not None else Schedule()
        self.max_steps = max_steps
        self._requests: dict[asyncio.Task[object], _Request] = {}
        self._tasks: set[asyncio.Task[object]] = set()
        self._wake = asyncio.Event()
        self._failure: Failure | None = None
        self._decisions: list[Decision] = []
        self._chosen: list[str] = []
        self._divergences: list[str] = []
        self._closed = False

    def start_soon(self, awaitable: Awaitable[object], *, name: str) -> asyncio.Task[object]:
        """Start a named child task owned by this run."""
        if self._closed:
            raise LoomError("cannot start a task after the run has closed")
        if not name or name.strip() != name:
            raise ValueError("task name must be non-empty and must not have outer whitespace")
        if any(task.get_name() == name for task in self._tasks):
            raise ValueError(f"duplicate task name: {name}")
        if not inspect.isawaitable(awaitable):
            raise TypeError("start_soon expects an awaitable")
        task: asyncio.Task[object] = asyncio.create_task(
            cast(Coroutine[Any, Any, object], awaitable), name=name
        )
        self._tasks.add(task)
        task.add_done_callback(self._on_task_done)
        return task

    async def checkpoint(self, label: str = "") -> None:
        """Yield at a named deterministic scheduling boundary."""
        if not isinstance(label, str):
            raise TypeError("checkpoint label must be a string")
        if self._closed:
            raise LoomError("checkpoint reached after the run closed")
        current = asyncio.current_task()
        if current is None:
            raise LoomError("checkpoint must run inside an asyncio task")
        name = current.get_name()
        if current not in self._tasks:
            self._tasks.add(current)
            current.add_done_callback(self._on_task_done)
        if current in self._requests:
            raise LoomError(f"task {name!r} reached a checkpoint twice without release")
        released: asyncio.Future[None] = asyncio.get_running_loop().create_future()
        self._requests[current] = _Request(current, name, label, released)
        self._wake.set()
        await released

    def run(self, scenario: Scenario, *, timeout: float = 5.0) -> RunResult:
        """Execute one scenario in a fresh event loop."""
        if not callable(scenario):
            raise TypeError("scenario must be callable as scenario(loom)")
        if timeout <= 0:
            raise ValueError("timeout must be greater than zero")
        started = time.perf_counter()
        try:
            result = asyncio.run(self._execute(scenario, timeout=timeout))
        except RuntimeError as exc:
            raise LoomError("Loom.run cannot be called from an active event loop") from exc
        elapsed = (time.perf_counter() - started) * 1000
        return RunResult(
            success=result.success,
            requested_schedule=self.schedule.choices,
            schedule=tuple(self._chosen),
            decisions=tuple(self._decisions),
            failure=result.failure,
            divergences=tuple(self._divergences),
            steps=len(self._decisions),
            duration_ms=round(elapsed, 3),
        )

    async def _execute(self, scenario: Scenario, *, timeout: float) -> RunResult:
        scenario_task: asyncio.Task[object] = asyncio.create_task(
            cast(Coroutine[Any, Any, object], scenario(self)), name="scenario"
        )
        self._tasks.add(scenario_task)
        scenario_task.add_done_callback(self._on_task_done)
        try:
            await asyncio.wait_for(self._drive(), timeout=timeout)
        except asyncio.TimeoutError:
            self._failure = Failure(
                "TimeoutFailure",
                f"scenario exceeded timeout of {timeout:.3f}s",
                task=None,
            )
        finally:
            self._closed = True
            for task in self._tasks:
                if not task.done():
                    task.cancel()
            if self._tasks:
                await asyncio.gather(*self._tasks, return_exceptions=True)
        return RunResult(
            success=self._failure is None,
            failure=self._failure,
        )

    async def _drive(self) -> None:
        while True:
            if self._failure is not None:
                return
            if len(self._decisions) >= self.max_steps and self._requests:
                self._failure = Failure(
                    "StepBudgetExceeded",
                    f"scenario exceeded max_steps={self.max_steps}",
                )
                return
            if self._requests:
                self._wake.clear()
                await asyncio.sleep(0)
                if self._failure is not None:
                    return
                self._release_one()
                await asyncio.sleep(0)
                continue
            if self._all_tasks_done():
                return
            self._wake.clear()
            await self._wake.wait()

    def _release_one(self) -> None:
        runnable = tuple(sorted(request.name for request in self._requests.values()))
        index = len(self._decisions)
        requested = self.schedule.choices[index] if index < len(self.schedule.choices) else None
        chosen = requested if requested in runnable else runnable[0]
        if requested is not None and requested not in runnable:
            self._divergences.append(
                f"step {index}: requested {requested!r}, runnable={list(runnable)!r}"
            )
        selected = next(request for request in self._requests.values() if request.name == chosen)
        labels = tuple(
            request.label
            for request in sorted(self._requests.values(), key=lambda item: item.name)
        )
        del self._requests[selected.task]
        self._chosen.append(chosen)
        self._decisions.append(
            Decision(step=index, chosen=chosen, runnable=runnable, labels=labels)
        )
        if not selected.released.done():
            selected.released.set_result(None)

    def _all_tasks_done(self) -> bool:
        return bool(self._tasks) and all(task.done() for task in self._tasks)

    def _on_task_done(self, task: asyncio.Task[object]) -> None:
        if task.cancelled() or self._failure is not None:
            self._wake.set()
            return
        try:
            error = task.exception()
        except asyncio.CancelledError:
            error = None
        if error is not None:
            self._failure = Failure(
                type(error).__name__,
                str(error) or repr(error),
                task=task.get_name(),
                traceback="".join(traceback.format_exception(error)),
            )
        self._wake.set()


def run(
    scenario: Scenario,
    *,
    schedule: Schedule | tuple[str, ...] | list[str] | None = None,
    max_steps: int = 100,
    timeout: float = 5.0,
) -> RunResult:
    """Convenience wrapper for one run."""
    normalized = schedule if isinstance(schedule, Schedule) else Schedule.from_value(schedule)
    return Loom(schedule=normalized, max_steps=max_steps).run(scenario, timeout=timeout)
