from __future__ import annotations

from pathlib import Path

from odylith.install import manager
from odylith.install.gitignore_rules import ensure_odylith_gitignore_entry


def test_manager_bootstrap_assets_live_in_support_owner() -> None:
    manager_text = Path(manager.__file__).read_text(encoding="utf-8")

    assert "from odylith.install import bootstrap_assets" in manager_text
    assert "_customer_bootstrap_guidance = bootstrap_assets.customer_bootstrap_guidance" in manager_text
    assert "_ensure_customer_bootstrap = bootstrap_assets.ensure_customer_bootstrap" in manager_text
    assert "def _customer_bootstrap_guidance(" not in manager_text
    assert "def _ensure_customer_bootstrap(" not in manager_text


def test_ensure_odylith_gitignore_entry_writes_all_local_state_rules(tmp_path: Path) -> None:
    updated = ensure_odylith_gitignore_entry(repo_root=tmp_path)

    assert updated is True
    text = (tmp_path / ".gitignore").read_text(encoding="utf-8")
    assert "/.odylith/" in text
    assert "/odylith/compass/runtime/refresh-state.v1.json" in text


def test_ensure_odylith_gitignore_entry_backfills_refresh_state_rule(tmp_path: Path) -> None:
    path = tmp_path / ".gitignore"
    path.write_text("/.odylith/\n", encoding="utf-8")

    updated = ensure_odylith_gitignore_entry(repo_root=tmp_path)

    assert updated is True
    lines = path.read_text(encoding="utf-8").splitlines()
    assert lines == [
        "/.odylith/",
        "/odylith/compass/runtime/refresh-state.v1.json",
    ]


def test_ensure_odylith_gitignore_entry_is_noop_when_rules_already_present(tmp_path: Path) -> None:
    path = tmp_path / ".gitignore"
    path.write_text(
        "/.odylith/\n/odylith/compass/runtime/refresh-state.v1.json\n",
        encoding="utf-8",
    )

    updated = ensure_odylith_gitignore_entry(repo_root=tmp_path)

    assert updated is False
    assert path.read_text(encoding="utf-8") == (
        "/.odylith/\n/odylith/compass/runtime/refresh-state.v1.json\n"
    )


def test_customer_bootstrap_guidance_carries_live_proof_claim_gate() -> None:
    guidance = manager._customer_bootstrap_guidance()  # noqa: SLF001

    assert len(guidance.encode("utf-8")) < 17000
    assert "Keep startup, Context Engine, Execution Engine, memory substrate, Tribunal, Intervention Engine" in guidance
    assert "never say `fixed`, `cleared`, or `resolved` without qualification" in guidance
    assert "same fingerprint as the last falsification or not" in guidance
    assert "`odylith codex intervention-status` or `odylith claude" in guidance
    assert "low-latency delivery record for Teaser, Ambient Highlight, Observation," in guidance
    assert "Proposal, and Assist readiness" in guidance
    assert "Hook `systemMessage` or `additionalContext` generation is not proof of chat-visible UX" in guidance
    assert "reports `Activation: ready` and a chat-visibility line is confirmed" in guidance
    assert "Treat recorded-only and waiting-for-chat states as partial proof" in guidance
    assert (
        "fully quality-gated staged ProductCreateTransaction before it presents the only command rail"
        in guidance
    )
    assert "CONFIRM commits the shown hash-bound package" in guidance
    assert "does not parse or generate product content after CONFIRM" in guidance
    assert "only verifies the sealed receipt" in guidance
    assert "Markdown is a view, never product truth" in guidance
    assert ".odylith/runtime/greenfield/pending/<hash>/product-create-transaction.v1.json" in guidance
    assert "confirmed-intent.json" not in guidance
    assert "greenfield compile-transaction" not in guidance
    assert "ProductCreateTransaction" in guidance
    assert "--transaction-file" in guidance
    assert "--transaction-hash" in guidance
    assert "rollback guard" in guidance
