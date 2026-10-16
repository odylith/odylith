"""Selected readers must observe normalized Casebook truth in one sync session."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from odylith.runtime.common import agent_runtime_contract
from odylith.runtime.context_engine import odylith_context_engine_store as store
from odylith.runtime.context_engine import odylith_context_cache
from odylith.runtime.context_engine import odylith_context_engine_projection_search_runtime as projection
from odylith.runtime.context_engine import projection_repo_state_runtime
from odylith.runtime.governance import sync_casebook_bug_index
from odylith.runtime.governance import sync_session
from odylith.runtime.governance import sync_workstream_artifacts as sync
from odylith.runtime.reasoning import odylith_reasoning
from odylith.runtime.surfaces import compass_dashboard_base
from odylith.runtime.surfaces import render_casebook_dashboard as casebook


@pytest.mark.parametrize("runtime_mode", ["standalone", "auto"])
def test_selective_sync_readers_observe_reopened_casebook_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, runtime_mode: str
) -> None:
    bug_path = tmp_path / "odylith/casebook/bugs/2026-09-07-reopened-status.md"
    bug_path.parent.mkdir(parents=True)
    closed_source = (
        "# Reopened status\n\n"
        "- Bug ID: CB-001\n- Status: Closed\n- Created: 2026-09-07\n"
        "- Severity: P2\n- Reproducibility: High\n- Type: Product\n"
        "- Components Affected: casebook\n\n"
        "- Description: Reopening a bug must update every selected reader.\n"
    )
    bug_path.write_text(closed_source, encoding="utf-8")
    index_path = sync_casebook_bug_index.sync_casebook_bug_index(repo_root=tmp_path)
    reopened_source = closed_source.replace("- Status: Closed", "- Status: Open")
    bug_path.write_text(reopened_source, encoding="utf-8")
    bug_path.chmod(0o640)
    reopened_bytes = bug_path.read_bytes()
    reopened_mode = bug_path.stat().st_mode & 0o777
    assert "| Closed |" in index_path.read_text(encoding="utf-8")

    provider_attempts: list[str] = []

    def forbid_provider(config, **kwargs):
        # The real factory returns None at this gate, before provider construction.
        if kwargs.get("require_auto_mode", True) and config.mode != "auto":
            return None
        provider_attempts.append("provider_from_config")
        pytest.fail("Selective Casebook freshness proof must not construct a provider")

    monkeypatch.setenv("ODYLITH_REASONING_MODE", "disabled")
    monkeypatch.setenv("ODYLITH_COMPASS_STANDUP_BACKGROUND_DISABLE", "1")
    monkeypatch.setattr(odylith_reasoning, "provider_from_config", forbid_provider)
    observations: dict[str, list[str]] = {}

    def read_compass_bugs(*, repo_root: Path, normalized_runtime_mode: str):
        # Keep the actual Compass read owner; omit unrelated refresh/narration work.
        rows = compass_dashboard_base._parse_bugs_rows(
            repo_root=repo_root,
            index_path=index_path,
            runtime_mode=normalized_runtime_mode,
        )
        observations["compass"] = [row["Status"] for row in rows]
        return {"rc": 0, "status": "passed"}

    monkeypatch.setattr(
        sync.compass_dashboard_refresh_inputs,
        "run_compass_dashboard_refresh",
        read_compass_bugs,
    )
    build_payload = casebook._build_payload

    def capture_casebook_payload(**kwargs):
        payload = build_payload(**kwargs)
        observations["casebook"] = [row["status"] for row in payload["bugs"]]
        return payload

    monkeypatch.setattr(casebook, "_build_payload", capture_casebook_payload)

    def run_casebook(*, repo_root: Path, args, heartbeat_label: str, **kwargs):
        assert args[:3] == (
            "python", "-m", "odylith.runtime.surfaces.render_casebook_dashboard"
        )
        return casebook.main(list(args[3:]))

    plan = sync._build_truth_only_selective_sync_plan(
        repo_root=tmp_path,
        args=SimpleNamespace(),
        changed_paths=(
            str(bug_path.relative_to(tmp_path)),
            agent_runtime_contract.candidate_stream_tokens()[0],
        ),
        sync_failure_command="odylith sync --repo-root .",
        runtime_mode=runtime_mode,
    )
    store.clear_runtime_process_caches(repo_root=tmp_path)
    session = sync_session.GovernedSyncSession(repo_root=tmp_path)
    try:
        with sync_session.activate_sync_session(session):
            result = sync._execute_plan(
                repo_root=tmp_path,
                plan_name="Casebook freshness regression",
                plan=plan,
                run_impl=run_casebook,
                runtime_fallback_used=False,
            )
        assert result == 0
        assert provider_attempts == []
        assert bug_path.read_bytes() == reopened_bytes
        assert bug_path.stat().st_mode & 0o777 == reopened_mode
        assert "| Open |" in index_path.read_text(encoding="utf-8")
        assert observations == {"compass": ["Open"], "casebook": ["Open"]}
    finally:
        store.clear_runtime_process_caches(repo_root=tmp_path)


def test_selective_sync_rejects_invalid_casebook_source_before_any_reader(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    bug_path = tmp_path / "odylith/casebook/bugs/2026-09-07-invalid-reopen.md"
    bug_path.parent.mkdir(parents=True)
    valid_source = (
        "# Reopened status\n\n"
        "- Bug ID: CB-001\n- Status: Closed\n- Created: 2026-09-07\n"
        "- Severity: P2\n- Reproducibility: High\n- Type: Product\n"
        "- Description: The stale index must not reach selected readers.\n"
    )
    bug_path.write_text(valid_source, encoding="utf-8")
    index_path = sync_casebook_bug_index.sync_casebook_bug_index(
        repo_root=tmp_path, migrate_bug_ids=False,
    )
    bug_path.write_text(
        valid_source.replace("- Status: Closed", "- Status: Open").replace(
            "- Reproducibility: High", "- Reproducibility: High; invalid value"
        ),
        encoding="utf-8",
    )
    bug_path.chmod(0o640)
    before_bug = (bug_path.read_bytes(), bug_path.stat().st_mode & 0o777)
    before_index = (index_path.read_bytes(), index_path.stat().st_mode & 0o777)
    plan = sync._build_truth_only_selective_sync_plan(
        repo_root=tmp_path,
        args=SimpleNamespace(),
        changed_paths=(
            str(bug_path.relative_to(tmp_path)),
            agent_runtime_contract.candidate_stream_tokens()[0],
        ),
        sync_failure_command="odylith sync --repo-root .",
        runtime_mode="standalone",
    )
    assert plan.steps[0].paths == ("odylith/casebook/bugs/INDEX.md",)
    monkeypatch.setattr(
        sync.compass_dashboard_refresh_inputs,
        "run_compass_dashboard_refresh",
        lambda **_: pytest.fail("Compass read invalid Casebook source"),
    )

    def forbid_render(**_):
        pytest.fail("Casebook render followed failed source validation")

    rc = sync._execute_plan(
        repo_root=tmp_path,
        plan_name="Casebook invalid-source regression",
        plan=plan,
        run_impl=forbid_render,
        runtime_fallback_used=False,
    )

    assert rc == 2
    assert (bug_path.read_bytes(), bug_path.stat().st_mode & 0o777) == before_bug
    assert (index_path.read_bytes(), index_path.stat().st_mode & 0o777) == before_index
    assert not (tmp_path / "odylith/casebook/casebook.html").exists()


def test_direct_casebook_refresh_updates_index_without_changing_valid_bug_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    bug_path = tmp_path / "odylith/casebook/bugs/2026-09-07-direct-reopen.md"
    bug_path.parent.mkdir(parents=True)
    closed_source = (
        "# Direct refresh\n\n- Bug ID: CB-001\n- Status: Closed\n"
        "- Created: 2026-09-07\n- Severity: P2\n- Reproducibility: High\n"
        "- Type: Product\n- Description: Direct refresh follows the source status.\n"
    )
    bug_path.write_text(closed_source, encoding="utf-8")
    index_path = sync_casebook_bug_index.sync_casebook_bug_index(
        repo_root=tmp_path, migrate_bug_ids=False,
    )
    bug_path.write_text(closed_source.replace("- Status: Closed", "- Status: Open"), encoding="utf-8")
    bug_path.chmod(0o640)
    before_bug = (bug_path.read_bytes(), bug_path.stat().st_mode & 0o777)
    monkeypatch.setenv("ODYLITH_REASONING_MODE", "disabled")

    def run_casebook(*, repo_root: Path, args, heartbeat_label: str, **kwargs):
        assert args[:3] == (
            "python", "-m", "odylith.runtime.surfaces.render_casebook_dashboard"
        )
        return casebook.main(list(args[3:]))

    monkeypatch.setattr(sync.sync_command_execution, "run_command", run_casebook)
    rc = sync.refresh_dashboard_surfaces(
        repo_root=tmp_path, surfaces=("casebook",), runtime_mode="standalone", force=True,
    )

    assert rc == 0
    assert (bug_path.read_bytes(), bug_path.stat().st_mode & 0o777) == before_bug
    assert "| Open |" in index_path.read_text(encoding="utf-8")
    assert "Open" in (tmp_path / "odylith/casebook/casebook-payload.v1.js").read_text(encoding="utf-8")


def test_parallel_dashboard_refresh_stops_before_compass_on_invalid_casebook(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    bug_path = tmp_path / "odylith/casebook/bugs/2026-09-07-invalid-parallel.md"
    bug_path.parent.mkdir(parents=True)
    bug_path.write_text(
        "# Invalid source\n\n- Bug ID: CB-001\n- Status: Open\n"
        "- Created: 2026-09-07\n- Severity: P2\n"
        "- Reproducibility: High; invalid value\n- Type: Product\n"
        "- Description: Readers must stop before publication.\n",
        encoding="utf-8",
    )
    before_bug = bug_path.read_bytes()
    monkeypatch.setattr(
        sync.compass_dashboard_refresh_inputs,
        "run_compass_dashboard_refresh",
        lambda **_: pytest.fail("Compass ran after invalid Casebook source"),
    )
    monkeypatch.setattr(
        sync.sync_command_execution,
        "run_command",
        lambda **_: pytest.fail("A surface rendered after invalid Casebook source"),
    )

    rc = sync.refresh_dashboard_surfaces(
        repo_root=tmp_path,
        surfaces=("compass", "casebook"),
        runtime_mode="standalone",
        force=True,
    )

    assert rc == 2
    assert bug_path.read_bytes() == before_bug
    assert not (bug_path.parent / "INDEX.md").exists()
    assert not (tmp_path / "odylith/compass/compass.html").exists()


def test_multisurface_refresh_updates_index_without_migrating_legacy_bug_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    bug_path = tmp_path / "odylith/casebook/bugs/2026-09-07-legacy-source.md"
    bug_path.parent.mkdir(parents=True)
    bug_path.write_text(
        "# Legacy source\n\n- Status: Open\n- Created: 2026-09-07\n"
        "- Severity: P2\n- Reproducibility: High\n- Type: Product\n"
        "- Description: Upgrade refresh must preserve this authored record.\n",
        encoding="utf-8",
    )
    bug_path.chmod(0o640)
    before_bug = (bug_path.read_bytes(), bug_path.stat().st_mode & 0o777)
    observed: list[str] = []
    monkeypatch.setenv("ODYLITH_REASONING_MODE", "disabled")

    def run_casebook(*, repo_root: Path, args, heartbeat_label: str, **kwargs):
        assert args[:3] == (
            "python", "-m", "odylith.runtime.surfaces.render_casebook_dashboard"
        )
        return casebook.main(list(args[3:]))

    def read_compass(*, repo_root: Path, normalized_runtime_mode: str):
        index = repo_root / "odylith/casebook/bugs/INDEX.md"
        assert "| Open |" in index.read_text(encoding="utf-8")
        assert (bug_path.read_bytes(), bug_path.stat().st_mode & 0o777) == before_bug
        observed.append("compass")
        return {"rc": 0, "status": "passed"}

    monkeypatch.setattr(sync.sync_command_execution, "run_command", run_casebook)
    monkeypatch.setattr(sync.compass_dashboard_refresh_inputs, "run_compass_dashboard_refresh", read_compass)
    rc = sync.refresh_dashboard_surfaces(
        repo_root=tmp_path, surfaces=("compass", "casebook"),
        runtime_mode="standalone", force=True,
    )

    assert rc == 0
    assert observed == ["compass"]
    assert (bug_path.read_bytes(), bug_path.stat().st_mode & 0o777) == before_bug


@pytest.mark.parametrize("fingerprint_kind", ["path", "shallow_glob"])
def test_repo_cache_clear_recomputes_index_fingerprint_and_preserves_sibling(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fingerprint_kind: str
) -> None:
    root = tmp_path / "consumer"
    sibling = tmp_path / "consumer-other"
    for repo in (root, sibling):
        index = repo / "odylith/casebook/bugs/INDEX.md"
        index.parent.mkdir(parents=True)
        index.write_text("| CB-001 | Closed |\n", encoding="utf-8")

    inspected_paths: list[Path] = []
    path_signature = odylith_context_cache.path_signature

    def record_signature(path: Path):
        inspected_paths.append(Path(path))
        return path_signature(path)

    monkeypatch.setattr(odylith_context_cache, "path_signature", record_signature)

    def fingerprint(repo: Path) -> str:
        bugs = repo / "odylith/casebook/bugs"
        if fingerprint_kind == "path":
            return projection._path_fingerprint(bugs / "INDEX.md", repo_root=repo)
        return projection._shallow_glob_fingerprint(bugs, repo_root=repo, glob="*.md")

    try:
        before = fingerprint(root)
        sibling_before = fingerprint(sibling)
        token_before = projection_repo_state_runtime.projection_repo_state_token(repo_root=root)
        (root / "odylith/casebook/bugs/INDEX.md").write_text(
            "| CB-001 | Open |\n", encoding="utf-8"
        )
        store.clear_runtime_process_caches(repo_root=root)
        # A non-Git consumer has no workspace-diff signal for this derived write.
        # Explicit invalidation must work even when the coarse token is unchanged.
        assert projection_repo_state_runtime.projection_repo_state_token(repo_root=root) == token_before
        inspections_before_sibling_read = len(inspected_paths)
        assert fingerprint(sibling) == sibling_before
        assert len(inspected_paths) == inspections_before_sibling_read
        assert fingerprint(root) != before
    finally:
        store.clear_runtime_process_caches()
