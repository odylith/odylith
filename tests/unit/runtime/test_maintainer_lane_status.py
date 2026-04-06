from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from odylith.runtime.governance import maintainer_lane_status


class _FakeBenchmarkResult:
    def __init__(self, *, status: str, notes: tuple[str, ...] = ()) -> None:
        self.status = status
        self.notes = notes

    def as_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "notes": list(self.notes),
        }


def _patch_common(monkeypatch, tmp_path: Path, *, branch: str, clean_worktree: bool, session: dict[str, object], version_errors: list[str], benchmark_status: str) -> None:  # noqa: ANN001
    monkeypatch.setattr(
        maintainer_lane_status,
        "version_status",
        lambda **kwargs: SimpleNamespace(
            repo_role="product_repo",
            posture="pinned_release",
            runtime_source="pinned_runtime",
            release_eligible=True,
        ),
    )
    monkeypatch.setattr(maintainer_lane_status, "product_repo_role", lambda **kwargs: "product_repo")
    monkeypatch.setattr(maintainer_lane_status, "_current_branch", lambda repo_root: branch)
    monkeypatch.setattr(maintainer_lane_status, "_worktree_clean", lambda repo_root: clean_worktree)
    monkeypatch.setattr(maintainer_lane_status, "_load_release_session", lambda **kwargs: session)
    monkeypatch.setattr(
        maintainer_lane_status.version_truth,
        "render_version_truth",
        lambda **kwargs: {
            "repo_root": str(tmp_path),
            "errors": version_errors,
        },
    )
    monkeypatch.setattr(
        maintainer_lane_status.benchmark_compare,
        "compare_latest_to_baseline",
        lambda **kwargs: _FakeBenchmarkResult(status=benchmark_status, notes=("baseline note",)),
    )


def test_lane_status_blocks_main_branch_authoring_and_suggests_new_branch(monkeypatch, tmp_path: Path) -> None:
    _patch_common(
        monkeypatch,
        tmp_path,
        branch="main",
        clean_worktree=True,
        session={"state": "inactive"},
        version_errors=[],
        benchmark_status="pass",
    )

    payload = maintainer_lane_status.lane_status_payload(repo_root=tmp_path)
    rendered = maintainer_lane_status.render_lane_status(payload)

    assert payload["main_branch_authoring_block"]["blocked"] is True
    assert payload["next_command"].startswith("git switch -c ")
    assert "/freedom/" in payload["next_command"]
    assert "- main_branch_authoring_block: yes" in rendered


def test_lane_status_prefers_version_sync_before_release_candidate(monkeypatch, tmp_path: Path) -> None:
    _patch_common(
        monkeypatch,
        tmp_path,
        branch="2026/freedom/v0.1.6",
        clean_worktree=True,
        session={"state": "inactive"},
        version_errors=["package drift"],
        benchmark_status="pass",
    )

    payload = maintainer_lane_status.lane_status_payload(repo_root=tmp_path)

    assert payload["main_branch_authoring_block"]["blocked"] is False
    assert payload["next_command"] == "./.odylith/bin/odylith validate version-truth --repo-root . sync"


def test_lane_status_prefers_release_dispatch_for_active_session(monkeypatch, tmp_path: Path) -> None:
    _patch_common(
        monkeypatch,
        tmp_path,
        branch="2026/freedom/v0.1.6",
        clean_worktree=True,
        session={"state": "active", "tag": "v0.1.6", "version": "0.1.6"},
        version_errors=[],
        benchmark_status="pass",
    )

    payload = maintainer_lane_status.lane_status_payload(repo_root=tmp_path)

    assert payload["next_command"] == "make release-dispatch"
