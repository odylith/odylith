from __future__ import annotations

from pathlib import Path

from odylith.runtime.evaluation import odylith_benchmark_isolation as isolation


def _write(path: Path, text: str = "x\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_scenario_workspace_self_reference_strip_paths_hide_benchmark_scaffold_but_preserve_explicit_paths(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    _write(repo_root / ".odylith" / "runtime" / "odylith-benchmarks" / "latest-proof.v1.json", "{}\n")
    _write(repo_root / "docs" / "benchmarks" / "README.md")
    _write(repo_root / "docs" / "benchmarks" / "REVIEWER_GUIDE.md")
    _write(repo_root / "odylith" / "maintainer" / "agents-guidelines" / "RELEASE_BENCHMARKS.md")
    _write(
        repo_root / "odylith" / "maintainer" / "skills" / "release-benchmark-publishing" / "SKILL.md",
    )
    _write(repo_root / "odylith" / "runtime" / "source" / "optimization-evaluation-corpus.v1.json", "{}\n")
    _write(
        repo_root / "src" / "odylith" / "bundle" / "assets" / "odylith" / "runtime" / "source" / "optimization-evaluation-corpus.v1.json",
        "{}\n",
    )
    _write(repo_root / "src" / "odylith" / "runtime" / "evaluation" / "odylith_benchmark_runner.py")
    _write(repo_root / "src" / "odylith" / "runtime" / "evaluation" / "odylith_benchmark_graphs.py")
    _write(repo_root / "src" / "odylith" / "runtime" / "evaluation" / "odylith_reasoning.py")
    _write(repo_root / "tests" / "unit" / "runtime" / "test_odylith_benchmark_runner.py")

    rows = isolation.scenario_workspace_self_reference_strip_paths(
        repo_root=repo_root,
        scenario={"family": "browser_surface_reliability"},
        preserve_paths=[
            "docs/benchmarks/README.md",
            "src/odylith/runtime/evaluation/odylith_benchmark_runner.py",
        ],
    )

    assert Path("docs/benchmarks/README.md") not in rows
    assert Path("src/odylith/runtime/evaluation/odylith_benchmark_runner.py") not in rows
    assert Path("docs/benchmarks/REVIEWER_GUIDE.md") in rows
    assert Path("src/odylith/runtime/evaluation/odylith_benchmark_graphs.py") in rows
    assert Path("src/odylith/runtime/evaluation/odylith_reasoning.py") in rows
    assert Path("odylith/runtime/source/optimization-evaluation-corpus.v1.json") in rows
    assert Path("tests/unit/runtime/test_odylith_benchmark_runner.py") in rows
    assert Path(".odylith/runtime/odylith-benchmarks/latest-proof.v1.json") in rows


def test_scenario_workspace_self_reference_strip_paths_skip_benchmark_families(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    _write(repo_root / "docs" / "benchmarks" / "README.md")
    _write(repo_root / "src" / "odylith" / "runtime" / "evaluation" / "odylith_benchmark_runner.py")

    rows = isolation.scenario_workspace_self_reference_strip_paths(
        repo_root=repo_root,
        scenario={"family": "release_publication"},
    )

    assert rows == []
