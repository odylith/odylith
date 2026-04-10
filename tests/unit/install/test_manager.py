from __future__ import annotations

from pathlib import Path

from odylith.install import manager


def test_ensure_odylith_gitignore_entry_writes_all_local_state_rules(tmp_path: Path) -> None:
    updated = manager._ensure_odylith_gitignore_entry(repo_root=tmp_path)  # noqa: SLF001

    assert updated is True
    text = (tmp_path / ".gitignore").read_text(encoding="utf-8")
    assert "/.odylith/" in text
    assert "/odylith/compass/runtime/refresh-state.v1.json" in text


def test_ensure_odylith_gitignore_entry_backfills_refresh_state_rule(tmp_path: Path) -> None:
    path = tmp_path / ".gitignore"
    path.write_text("/.odylith/\n", encoding="utf-8")

    updated = manager._ensure_odylith_gitignore_entry(repo_root=tmp_path)  # noqa: SLF001

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

    updated = manager._ensure_odylith_gitignore_entry(repo_root=tmp_path)  # noqa: SLF001

    assert updated is False
    assert path.read_text(encoding="utf-8") == (
        "/.odylith/\n/odylith/compass/runtime/refresh-state.v1.json\n"
    )


def test_customer_bootstrap_guidance_carries_live_proof_claim_gate() -> None:
    guidance = manager._customer_bootstrap_guidance()  # noqa: SLF001

    assert "never say `fixed`, `cleared`, or `resolved` without qualification" in guidance
    assert "same fingerprint as the last falsification or not" in guidance
