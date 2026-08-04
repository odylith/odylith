#!/usr/bin/env python3
"""Run the repository pytest corpus in deterministic fresh-process shards."""

from __future__ import annotations

import argparse
import subprocess
import sys
from collections.abc import Callable, Iterator, Sequence


DEFAULT_SHARD_SIZE = 200
RunCommand = Callable[..., subprocess.CompletedProcess[str]]


def parse_collected_nodeids(output: str) -> list[str]:
    """Return ordered pytest node IDs while ignoring collection summaries."""
    nodeids: list[str] = []
    seen: set[str] = set()
    for raw_line in output.splitlines():
        candidate = raw_line.strip()
        path = candidate.split("::", 1)[0]
        if "::" not in candidate or not path.startswith(("tests/", "tests\\")):
            continue
        if candidate not in seen:
            seen.add(candidate)
            nodeids.append(candidate)
    return nodeids


def collect_nodeids(*, run: RunCommand = subprocess.run) -> list[str]:
    """Collect the canonical test order without executing test bodies."""
    result = run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if result.returncode != 0:
        if result.stdout:
            sys.stdout.write(result.stdout)
        raise RuntimeError(f"pytest collection failed with exit code {result.returncode}")

    nodeids = parse_collected_nodeids(result.stdout or "")
    if not nodeids:
        raise RuntimeError("pytest collection returned no test node IDs")
    return nodeids


def iter_shards(nodeids: Sequence[str], shard_size: int) -> Iterator[list[str]]:
    """Yield stable contiguous shards from the collected pytest order."""
    if shard_size < 1:
        raise ValueError("shard size must be at least 1")
    for start in range(0, len(nodeids), shard_size):
        yield list(nodeids[start : start + shard_size])


def run_shards(
    nodeids: Sequence[str],
    *,
    shard_size: int,
    run: RunCommand = subprocess.run,
) -> int:
    """Execute every shard and return a single aggregate result."""
    shards = list(iter_shards(nodeids, shard_size))
    if not shards:
        raise ValueError("at least one pytest node ID is required")

    failures: list[tuple[int, int]] = []
    for index, shard in enumerate(shards, start=1):
        print(
            f"pytest shard {index}/{len(shards)}: {len(shard)} tests",
            flush=True,
        )
        result = run(
            [sys.executable, "-m", "pytest", "-q", *shard],
            check=False,
        )
        if result.returncode != 0:
            failures.append((index, result.returncode))
            print(
                f"pytest shard {index}/{len(shards)} failed with exit code "
                f"{result.returncode}; continuing",
                flush=True,
            )

    if failures:
        details = ", ".join(
            f"{index} (exit {returncode})" for index, returncode in failures
        )
        print(f"pytest shards failed: {details}", file=sys.stderr, flush=True)
        return 1

    print(
        f"pytest shards passed: {len(nodeids)} tests across {len(shards)} processes",
        flush=True,
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run pytest in bounded fresh-process shards."
    )
    parser.add_argument(
        "--shard-size",
        type=int,
        default=DEFAULT_SHARD_SIZE,
        help=f"maximum tests per process (default: {DEFAULT_SHARD_SIZE})",
    )
    parser.add_argument(
        "nodeids",
        nargs="*",
        help="optional explicit pytest node IDs; collect the full suite when omitted",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        nodeids = args.nodeids or collect_nodeids()
        print(f"pytest collection: {len(nodeids)} tests", flush=True)
        return run_shards(nodeids, shard_size=args.shard_size)
    except (RuntimeError, ValueError) as exc:
        print(f"pytest shard runner error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
