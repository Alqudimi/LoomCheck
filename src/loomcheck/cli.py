"""Command-line interface for LoomCheck."""

from __future__ import annotations

import argparse
import asyncio
import importlib
import json
import sys
from collections.abc import Awaitable
from pathlib import Path
from typing import Any, cast

from .explorer import explore
from .model import ExplorationResult, RunResult, Schedule
from .report import render
from .runtime import Loom, Scenario, run


def _load_target(spec: str) -> Scenario:
    if ":" not in spec:
        raise ValueError("target must use module:callable syntax")
    module_name, attribute = spec.split(":", 1)
    if not module_name or not attribute:
        raise ValueError("target must use module:callable syntax")
    module = importlib.import_module(module_name)
    target: Any = module
    for part in attribute.split("."):
        target = getattr(target, part)
    if not callable(target):
        raise TypeError(f"target is not callable: {spec}")
    return cast(Scenario, target)


def _write_output(content: str, output: str | None) -> None:
    if output:
        Path(output).write_text(content, encoding="utf-8")
        print(f"report written to {output}")
    else:
        print(content, end="")


def _demo_scenario(loom: Loom) -> Awaitable[None]:
    counter = 0

    async def race_worker(name: str) -> None:
        nonlocal counter
        await loom.checkpoint(f"{name}:read")
        current = counter
        await loom.checkpoint(f"{name}:write")
        counter = current + 1

    async def scenario() -> None:
        tasks = [loom.start_soon(race_worker(name), name=name) for name in ("alpha", "beta")]
        await asyncio.gather(*tasks)
        if counter != 2:
            raise AssertionError(f"lost update: expected 2, got {counter}")

    return scenario()


def _demo_target(loom: Loom) -> Any:
    return _demo_scenario(loom)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="loomcheck",
        description="Bounded deterministic schedule exploration for cooperative asyncio code.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("run", "explore"):
        sub = subparsers.add_parser(command, help=f"{command} a module:callable scenario")
        sub.add_argument("target", help="Python target using module:callable syntax")
        sub.add_argument("--max-steps", type=int, default=100)
        sub.add_argument("--timeout", type=float, default=5.0)
        sub.add_argument("--format", choices=("json", "markdown"), default="markdown")
        sub.add_argument("--output", help="write report to a file instead of stdout")
        if command == "explore":
            sub.add_argument("--max-runs", type=int, default=100)
            sub.add_argument("--schedule", help="JSON array of task names to replay first")
    demo = subparsers.add_parser("demo", help="run a built-in race-condition demonstration")
    demo.add_argument("name", choices=("race",))
    demo.add_argument("--max-runs", type=int, default=20)
    demo.add_argument("--max-steps", type=int, default=20)
    demo.add_argument("--format", choices=("json", "markdown"), default="markdown")
    demo.add_argument("--output", help="write report to a file instead of stdout")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result: RunResult | ExplorationResult
        if args.command == "run":
            result = run(_load_target(args.target), max_steps=args.max_steps, timeout=args.timeout)
        elif args.command == "explore":
            schedule = json.loads(args.schedule) if args.schedule else []
            result = explore(
                _load_target(args.target),
                max_runs=args.max_runs,
                max_steps=args.max_steps,
                timeout=args.timeout,
                initial_schedule=Schedule.from_value(schedule).choices,
            )
        else:
            result = explore(
                _demo_target,
                max_runs=args.max_runs,
                max_steps=args.max_steps,
            )
        _write_output(render(result, args.format), args.output)
        return 1 if not result.success else 0
    except (ImportError, AttributeError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(f"loomcheck: error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
