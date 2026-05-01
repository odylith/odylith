from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def test_benchmark_tree_identity_has_focused_owner() -> None:
    runner_path = ROOT / "src" / "odylith" / "runtime" / "evaluation" / "odylith_benchmark_runner.py"
    owner_path = (
        ROOT
        / "src"
        / "odylith"
        / "runtime"
        / "evaluation"
        / "odylith_benchmark_tree_identity.py"
    )
    owner_text = owner_path.read_text(encoding="utf-8")
    runner_text = runner_path.read_text(encoding="utf-8")
    assert "def benchmark_tree_identity(" in owner_text
    assert "def benchmark_report_matches_current_tree(" in owner_text
    assert "def report_snapshot_overlay_paths(" in owner_text
    for fragment in (
        "def benchmark_tree_identity(",
        "def benchmark_report_matches_current_tree(",
        "def _report_snapshot_overlay_paths(",
        "def _dirty_repo_paths(",
        "def _snapshot_overlay_fingerprint(",
    ):
        assert fragment not in runner_text, f"tree-identity ownership regressed into runner: {fragment}"
    for path in (
        runner_path,
        ROOT / "src" / "odylith" / "runtime" / "evaluation" / "benchmark_compare.py",
        ROOT / "src" / "odylith" / "runtime" / "evaluation" / "odylith_benchmark_publication.py",
        ROOT / "src" / "odylith" / "runtime" / "evaluation" / "odylith_benchmark_shard_merge.py",
    ):
        text = path.read_text(encoding="utf-8")
        assert "odylith_benchmark_tree_identity" in text, path.relative_to(ROOT)
        assert "runner.benchmark_report_matches_current_tree(" not in text
        assert "runner.benchmark_tree_identity(" not in text
