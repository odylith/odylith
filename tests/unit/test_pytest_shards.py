from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from scripts import run_pytest_shards


ROOT = Path(__file__).resolve().parents[2]


def test_parse_collected_nodeids_preserves_order_and_ignores_summary() -> None:
    output = """tests/unit/test_alpha.py::test_one
tests/unit/test_alpha.py::test_param[value with spaces]
tests/unit/test_alpha.py::test_one

2 tests collected in 0.01s
"""

    assert run_pytest_shards.parse_collected_nodeids(output) == [
        "tests/unit/test_alpha.py::test_one",
        "tests/unit/test_alpha.py::test_param[value with spaces]",
    ]


def test_iter_shards_keeps_contiguous_bounded_groups() -> None:
    nodeids = [f"tests/unit/test_example.py::test_{index}" for index in range(5)]

    assert list(run_pytest_shards.iter_shards(nodeids, 2)) == [
        nodeids[0:2],
        nodeids[2:4],
        nodeids[4:5],
    ]


def test_iter_shards_rejects_non_positive_size() -> None:
    with pytest.raises(ValueError, match="at least 1"):
        list(run_pytest_shards.iter_shards(["tests/unit/test_example.py::test_one"], 0))


def test_run_shards_continues_after_failed_process(capsys: pytest.CaptureFixture[str]) -> None:
    nodeids = [f"tests/unit/test_example.py::test_{index}" for index in range(5)]
    returncodes = iter([0, -10, 0])
    commands: list[list[str]] = []

    def fake_run(command: list[str], *, check: bool) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        return subprocess.CompletedProcess(command, next(returncodes))

    assert run_pytest_shards.run_shards(nodeids, shard_size=2, run=fake_run) == 1
    assert len(commands) == 3
    assert [command[-1] for command in commands] == [nodeids[1], nodeids[3], nodeids[4]]
    output = capsys.readouterr()
    assert "shard 2/3 failed with exit code -10; continuing" in output.out
    assert "pytest shards failed: 2 (exit -10)" in output.err


def test_collect_nodeids_surfaces_collection_failure(capsys: pytest.CaptureFixture[str]) -> None:
    def fake_run(
        command: list[str],
        *,
        check: bool,
        stdout: int,
        stderr: int,
        text: bool,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 4, stdout="collection exploded\n")

    with pytest.raises(RuntimeError, match="exit code 4"):
        run_pytest_shards.collect_nodeids(run=fake_run)
    assert capsys.readouterr().out == "collection exploded\n"


def test_canonical_validate_uses_process_isolated_pytest_runner() -> None:
    validate = (ROOT / "bin" / "validate").read_text(encoding="utf-8")

    assert 'scripts/run_pytest_shards.py"' in validate
    assert '"$odylith_python" -m pytest -q' not in validate
