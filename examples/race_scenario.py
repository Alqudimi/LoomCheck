"""A deliberately racy scenario used by the README and CLI examples."""

from __future__ import annotations

import asyncio

from loomcheck import Loom


async def lost_update(loom: Loom) -> None:
    state = {"value": 0}

    async def worker(name: str) -> None:
        await loom.checkpoint(f"{name}:read")
        current = state["value"]
        await loom.checkpoint(f"{name}:write")
        state["value"] = current + 1

    tasks = [loom.start_soon(worker(name), name=name) for name in ("alpha", "beta")]
    await asyncio.gather(*tasks)
    if state["value"] != 2:
        raise AssertionError(f"lost update: expected 2, got {state['value']}")


async def safe(loom: Loom) -> None:
    async def worker(name: str) -> None:
        await loom.checkpoint(f"{name}:work")

    await asyncio.gather(
        loom.start_soon(worker("alpha"), name="alpha"),
        loom.start_soon(worker("beta"), name="beta"),
    )
