from __future__ import annotations

import json
from pathlib import Path

from odylith import cli
from odylith.runtime.evaluation import benchmark_compare as _real_benchmark_compare


class _FakeBenchmarkResult:
    def __init__(self, status: str = "pass") -> None:
        self.status = status

    def as_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "candidate_report_id": "candidate-1",
            "candidate_product_version": "0.1.6",
            "baseline_report_id": "baseline-1",
            "baseline_product_version": "0.1.5",
            "baseline_source": "last-shipped",
            "summary": {},
            "deltas": {},
            "notes": ["compare note"],
            "blocking": self.status == "fail",
        }


def test_sync_refuses_product_repo_authoring_on_main(monkeypatch, tmp_path: Path, capsys) -> None:
    (tmp_path / "AGENTS.md").write_text("# Repo Root\n", encoding="utf-8")
    monkeypatch.setattr(cli, "_main_branch_guard_repo_role", lambda **kwargs: cli.PRODUCT_REPO_ROLE)
    monkeypatch.setattr(cli, "_current_git_branch", lambda **kwargs: "main")

    rc = cli.main(["sync", "--repo-root", str(tmp_path)])

    assert rc == 2
    assert "Maintainer authoring on `main` is forbidden" in capsys.readouterr().err


def test_sync_check_only_is_allowed_on_main(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    (tmp_path / "AGENTS.md").write_text("# Repo Root\n", encoding="utf-8")
    monkeypatch.setattr(cli, "product_repo_role", lambda **kwargs: "product_repo")
    monkeypatch.setattr(cli, "_current_git_branch", lambda **kwargs: "main")

    def fake_main(argv: list[str]) -> int:
        captured["argv"] = argv
        return 0

    monkeypatch.setattr(cli.sync_workstream_artifacts, "main", fake_main)

    rc = cli.main(["sync", "--repo-root", str(tmp_path), "--check-only", "--check-clean"])

    assert rc == 0
    assert captured["argv"] == ["--repo-root", str(tmp_path), "--check-only", "--check-clean"]


def test_lane_status_dispatches_to_maintainer_lane_status(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_main(argv: list[str]) -> int:
        captured["argv"] = argv
        return 0

    monkeypatch.setattr(cli.maintainer_lane_status, "main", fake_main)

    rc = cli.main(["lane", "status", "--repo-root", str(tmp_path), "--json"])

    assert rc == 0
    assert captured["argv"] == ["--repo-root", str(tmp_path), "--json"]


def test_benchmark_compare_renders_text_and_returns_fail_status(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.setattr(
        _real_benchmark_compare,
        "compare_latest_to_baseline",
        lambda **kwargs: _FakeBenchmarkResult(status="fail"),
    )
    monkeypatch.setattr(
        _real_benchmark_compare,
        "render_compare_text",
        lambda result: "odylith benchmark compare\n- status: fail\n- note: compare note",
    )

    rc = cli.main(["benchmark", "compare", "--repo-root", str(tmp_path), "--baseline", "last-shipped"])

    assert rc == 2
    assert "odylith benchmark compare" in capsys.readouterr().out


def test_benchmark_compare_warns_without_blocking(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.setattr(
        _real_benchmark_compare,
        "compare_latest_to_baseline",
        lambda **kwargs: _FakeBenchmarkResult(status="warn"),
    )
    monkeypatch.setattr(
        _real_benchmark_compare,
        "render_compare_text",
        lambda result: "odylith benchmark compare\n- status: warn\n- note: first-release warning",
    )

    rc = cli.main(["benchmark", "compare", "--repo-root", str(tmp_path), "--baseline", "last-shipped"])

    assert rc == 0
    assert "odylith benchmark compare" in capsys.readouterr().out


def test_benchmark_compare_renders_json(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.setattr(
        _real_benchmark_compare,
        "compare_latest_to_baseline",
        lambda **kwargs: _FakeBenchmarkResult(status="pass"),
    )

    rc = cli.main(["benchmark", "compare", "--repo-root", str(tmp_path), "--json"])
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert payload["status"] == "pass"
