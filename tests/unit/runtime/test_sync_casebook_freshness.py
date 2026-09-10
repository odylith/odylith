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
        assert bug_path.read_text(encoding="utf-8") == reopened_source
        assert "| Open |" in index_path.read_text(encoding="utf-8")
        assert observations == {"compass": ["Open"], "casebook": ["Open"]}
    finally:
        store.clear_runtime_process_caches(repo_root=tmp_path)


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
