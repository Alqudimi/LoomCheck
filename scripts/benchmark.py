"""Small reproducible benchmark for the current LoomCheck runtime."""

from __future__ import annotations

import asyncio
import statistics
import time

from loomcheck import Loom, explore


async def scenario(loom: Loom) -> None:
    async def worker(name: str) -> None:
        for index in range(10):
            await loom.checkpoint(f"{name}:{index}")

    await asyncio.gather(
        loom.start_soon(worker("alpha"), name="alpha"),
        loom.start_soon(worker("beta"), name="beta"),
    )


def main() -> None:
    samples: list[float] = []
    for _ in range(20):
        started = time.perf_counter()
        result = Loom(max_steps=30).run(scenario)
        assert result.success
        samples.append((time.perf_counter() - started) * 1000)
    campaign = explore(scenario, max_runs=20, max_steps=30)
    print(f"single_run_ms_median={statistics.median(samples):.3f}")
    print(f"single_run_ms_min={min(samples):.3f}")
    print(f"exploration_runs={len(campaign.runs)}")
    print(f"exploration_failures={len(campaign.failures)}")


if __name__ == "__main__":
    main()
