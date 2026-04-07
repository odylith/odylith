from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from odylith.install.state import write_install_state
from odylith.install.state import load_upgrade_spotlight
from odylith.install.state import write_upgrade_spotlight
from odylith.install.state import write_version_pin
from odylith.runtime.surfaces import shell_onboarding


def test_build_welcome_state_suggests_components_diagrams_and_surface_flow(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    (tmp_path / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
    (tmp_path / "src" / "payments").mkdir(parents=True, exist_ok=True)
    (tmp_path / "src" / "billing").mkdir(parents=True, exist_ok=True)

    welcome = shell_onboarding.build_welcome_state(repo_root=tmp_path)

    assert welcome["show"] is True
    assert welcome["headline"] == "Start Odylith from one real code path"
    assert welcome["subhead"] == "Open the cheatsheet drawer on the left and try out commands in this repo."
    assert welcome["starter_prompt"] == shell_onboarding.STARTER_PROMPT
    assert welcome["auto_refresh_note"] == shell_onboarding.AUTO_REFRESH_NOTE
    assert welcome["dismiss_key"].startswith("welcome-v2|")
    assert welcome["notices"] == []
    assert welcome["quick_steps"] == [
        "Copy the starter prompt.",
        "Paste it into Codex or Claude Code.",
        "Let Odylith set up Radar, Registry, and Atlas.",
    ]
    assert welcome["chosen_slice"]["path"] in {"src/payments", "src/billing"}
    assert welcome["chosen_slice"]["title"] == "Example starting path"
    assert welcome["chosen_slice"]["reason"].startswith("Use `")
    assert welcome["chosen_slice"]["guidance"] == [
        "Start small with one real path instead of trying to map the whole repo.",
        "Odylith will use this same example to seed Radar, Registry, and Atlas.",
    ]
    assert [task["title"] for task in welcome["first_tasks"]] == [
        "Backlog",
        "Components",
        "Diagrams",
    ]
    assert welcome["first_tasks"][0]["prompts"][0]["text"].startswith("Open the Radar item for")
    assert welcome["first_tasks"][1]["prompts"][1]["text"].startswith("Tighten the Registry boundary")
    assert welcome["first_tasks"][2]["prompts"][2]["text"].startswith("Drop the Atlas diagram")
    assert any("odylith/registry/source/components/" in item for item in welcome["component_suggestions"])
    assert any("odylith/atlas/source/" in item for item in welcome["atlas_diagram_suggestions"])
    assert any(item.startswith("Likely first delivery surface:") for item in welcome["repo_readout"])
    boundary_label = welcome["chosen_slice"]["path"].split("/")[-1].replace("-", " ").title()
    assert welcome["surface_handoff"] == [
        f"Radar starts with `{welcome['chosen_slice']['path']}`.",
        f"Registry names the boundary around {boundary_label}.",
        f"Atlas makes `{welcome['chosen_slice']['path']}` visible before the repo gets busy.",
    ]
    assert [item["surface"] for item in welcome["surface_explainers"]] == [
        "Radar",
        "Registry",
        "Atlas",
        "Compass",
    ]
    assert welcome["surface_explainers"][0]["sentence"] == "Radar keeps a clear backlog so the repo always has one governed next step."
    assert welcome["surface_explainers"][1]["sentence"] == "Registry is the component ledger for boundaries, ownership, and contracts."
    assert welcome["surface_explainers"][2]["sentence"] == "Atlas keeps architecture visible with diagrams of topology and flow."
    assert welcome["surface_explainers"][3]["sentence"] == "Compass keeps briefs and timelines so the next move stays clear."


def test_build_welcome_state_hides_once_backlog_components_and_atlas_exist(tmp_path: Path) -> None:
    (tmp_path / "src" / "payments").mkdir(parents=True, exist_ok=True)
    ideas_root = tmp_path / "odylith" / "radar" / "source" / "ideas"
    ideas_root.mkdir(parents=True, exist_ok=True)
    (ideas_root / "B-001-example.md").write_text("# Example backlog item\n", encoding="utf-8")
    component_root = tmp_path / "odylith" / "registry" / "source" / "components" / "core"
    component_root.mkdir(parents=True, exist_ok=True)
    (component_root / "CURRENT_SPEC.md").write_text("# Core\n", encoding="utf-8")
    atlas_root = tmp_path / "odylith" / "atlas" / "source"
    atlas_root.mkdir(parents=True, exist_ok=True)
    (atlas_root / "core-boundary-map.mmd").write_text("graph TD\n  A[Core]\n", encoding="utf-8")

    welcome = shell_onboarding.build_welcome_state(repo_root=tmp_path)

    assert welcome["show"] is False
    assert welcome["chosen_slice"]["path"] == "src/payments"


def test_build_welcome_state_warns_when_repo_is_not_git_backed(tmp_path: Path) -> None:
    (tmp_path / "src" / "payments").mkdir(parents=True, exist_ok=True)

    welcome = shell_onboarding.build_welcome_state(repo_root=tmp_path)

    assert welcome["show"] is True
    assert welcome["notices"] == [
        {
            "tone": "warning",
            "title": "Git missing",
            "body": "Odylith installed here, but repo intelligence stays reduced until this folder is backed by Git.",
        }
    ]


def test_build_welcome_state_skips_fake_slice_when_only_repo_name_is_available(tmp_path: Path) -> None:
    welcome = shell_onboarding.build_welcome_state(repo_root=tmp_path)

    assert welcome["show"] is True
    assert welcome["chosen_slice"] == {
        "guidance": [
            "Create one real code folder first for the app, service, or package you actually plan to build.",
            "Then reopen setup and Odylith will recommend a grounded starting area automatically.",
        ],
        "reason": "Odylith cannot recommend a code path yet because this repo does not expose one real code area.",
        "title": "No starting path yet",
    }
    assert "|none|" in welcome["dismiss_key"]
    assert welcome["quick_steps"] == [
        "Copy the starter prompt.",
        "Paste it into Codex or Claude Code.",
        "Try commands in the cheatsheet.",
    ]
    assert not any(item.startswith("Likely first delivery surface:") for item in welcome["repo_readout"])
    assert any("has not inferred one grounded slice yet" in item for item in welcome["repo_readout"])


def test_build_welcome_state_adds_legacy_upgrade_notice_for_consumer_repo(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    (tmp_path / "src" / "payments").mkdir(parents=True, exist_ok=True)
    launcher_path = tmp_path / ".odylith" / "bin" / "odylith"
    launcher_path.parent.mkdir(parents=True, exist_ok=True)
    launcher_path.write_text("#!/usr/bin/env bash\nexec \"$PYTHON\" -m odylith.cli \"$@\"\n", encoding="utf-8")
    write_install_state(
        repo_root=tmp_path,
        payload={
            "active_version": "0.1.1",
            "activation_history": ["0.1.1"],
            "installed_versions": {"0.1.1": {"runtime_root": str(tmp_path / ".odylith" / "runtime" / "versions" / "0.1.1")}},
        },
    )
    write_version_pin(repo_root=tmp_path, version="0.1.1")

    welcome = shell_onboarding.build_welcome_state(repo_root=tmp_path)

    assert welcome["show"] is True
    assert any(notice["title"] == "Legacy upgrade path detected" for notice in welcome["notices"])
    legacy_notice = next(notice for notice in welcome["notices"] if notice["title"] == "Legacy upgrade path detected")
    assert legacy_notice["code"] == shell_onboarding.LATEST_INSTALL_COMMAND
    assert legacy_notice["copy_label"] == "Copy rescue install"


def test_build_welcome_state_keeps_notice_payload_when_onboarding_is_done(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    ideas_root = tmp_path / "odylith" / "radar" / "source" / "ideas"
    ideas_root.mkdir(parents=True, exist_ok=True)
    (ideas_root / "B-001-example.md").write_text("# Example backlog item\n", encoding="utf-8")
    component_root = tmp_path / "odylith" / "registry" / "source" / "components" / "core"
    component_root.mkdir(parents=True, exist_ok=True)
    (component_root / "CURRENT_SPEC.md").write_text("# Core\n", encoding="utf-8")
    atlas_root = tmp_path / "odylith" / "atlas" / "source"
    atlas_root.mkdir(parents=True, exist_ok=True)
    (atlas_root / "core-boundary-map.mmd").write_text("graph TD\n  A[Core]\n", encoding="utf-8")
    launcher_path = tmp_path / ".odylith" / "bin" / "odylith"
    launcher_path.parent.mkdir(parents=True, exist_ok=True)
    launcher_path.write_text("#!/usr/bin/env bash\nexec \"$PYTHON\" -m odylith.cli \"$@\"\n", encoding="utf-8")
    write_install_state(
        repo_root=tmp_path,
        payload={
            "active_version": "0.1.1",
            "activation_history": ["0.1.1"],
            "installed_versions": {"0.1.1": {"runtime_root": str(tmp_path / ".odylith" / "runtime" / "versions" / "0.1.1")}},
        },
    )

    welcome = shell_onboarding.build_welcome_state(repo_root=tmp_path)

    assert welcome["show"] is False
    assert any(notice["title"] == "Legacy upgrade path detected" for notice in welcome["notices"])


def test_build_release_spotlight_for_recent_consumer_upgrade(tmp_path: Path) -> None:
    write_install_state(
        repo_root=tmp_path,
        payload={
            "active_version": "0.1.4",
            "activation_history": ["0.1.3", "0.1.4"],
            "installed_versions": {
                "0.1.4": {"runtime_root": str(tmp_path / ".odylith" / "runtime" / "versions" / "0.1.4")}
            },
        },
    )
    write_upgrade_spotlight(
        repo_root=tmp_path,
        from_version="0.1.3",
        to_version="0.1.4",
        release_tag="v0.1.4",
        release_url="https://example.com/releases/v0.1.4",
        release_published_at="2026-03-30T14:00:00Z",
        release_body=(
            "Odylith now renders a sharper first-run launchpad and a clearer consumer upgrade moment.\n\n"
            "The dashboard refreshes immediately after upgrade so the shell reflects the new release."
        ),
        highlights=(
            "Sharper launchpad layout.",
            "Cleaner install hygiene.",
        ),
    )

    spotlight = shell_onboarding.build_release_spotlight(repo_root=tmp_path)

    assert spotlight["show"] is True
    assert spotlight["from_version"] == "0.1.3"
    assert spotlight["to_version"] == "0.1.4"
    assert spotlight["release_tag"] == "v0.1.4"
    assert spotlight["release_body"].startswith("Odylith now renders a sharper first-run launchpad")
    assert spotlight["highlights"] == ["Sharper launchpad layout.", "Cleaner install hygiene."]
    assert spotlight["summary"].startswith("Odylith now renders a sharper first-run launchpad")
    assert spotlight["detail"].startswith("The dashboard refreshes immediately after upgrade")
    assert spotlight["notes_label"] == "Open release note on GitHub"
    assert spotlight["notes_url"] == (
        "https://github.com/odylith/odylith/blob/v0.1.4/odylith/runtime/source/release-notes/v0.1.4.md"
    )


def test_build_release_spotlight_ignores_first_install_with_stale_payload(tmp_path: Path) -> None:
    write_install_state(
        repo_root=tmp_path,
        payload={
            "active_version": "0.1.4",
            "activation_history": ["0.1.4"],
            "installed_versions": {
                "0.1.4": {"runtime_root": str(tmp_path / ".odylith" / "runtime" / "versions" / "0.1.4")}
            },
        },
    )
    write_upgrade_spotlight(
        repo_root=tmp_path,
        from_version="0.1.3",
        to_version="0.1.4",
        release_tag="v0.1.4",
        release_url="https://example.com/releases/v0.1.4",
        release_published_at="2026-03-30T14:00:00Z",
        release_body="This should not render for a first install.",
        highlights=("Should stay hidden.",),
    )

    spotlight = shell_onboarding.build_release_spotlight(repo_root=tmp_path)

    assert spotlight == {}


def test_build_release_spotlight_prefers_authored_release_note_source(tmp_path: Path) -> None:
    write_install_state(
        repo_root=tmp_path,
        payload={
            "active_version": "0.1.5",
            "activation_history": ["0.1.4", "0.1.5"],
            "installed_versions": {
                "0.1.5": {"runtime_root": str(tmp_path / ".odylith" / "runtime" / "versions" / "0.1.5")}
            },
        },
    )
    write_upgrade_spotlight(
        repo_root=tmp_path,
        from_version="0.1.4",
        to_version="0.1.5",
        release_tag="v0.1.5",
        release_url="https://example.com/releases/v0.1.5",
        release_published_at="2026-03-30T14:00:00Z",
        release_body="Fallback body should be replaced.",
        highlights=("Fallback bullet.",),
    )
    notes_root = tmp_path / "odylith" / "runtime" / "source" / "release-notes"
    notes_root.mkdir(parents=True, exist_ok=True)
    (notes_root / "v0.1.5.md").write_text(
        (
            "---\n"
            "version: 0.1.5\n"
            "published_at: 2026-03-30T14:00:00Z\n"
            "summary: Release summary from source.\n"
            "highlights:\n"
            "  - Source highlight one.\n"
            "  - Source highlight two.\n"
            "---\n\n"
            "Release summary from source.\n\n"
            "The authored detail should become the spotlight detail."
        ),
        encoding="utf-8",
    )

    spotlight = shell_onboarding.build_release_spotlight(repo_root=tmp_path)

    assert spotlight["title"] == "v0.1.5"
    assert spotlight["release_body"].startswith("Release summary from source.")
    assert spotlight["highlights"] == ["Source highlight one.", "Source highlight two."]
    assert spotlight["summary"] == "Release summary from source."
    assert spotlight["detail"] == "The authored detail should become the spotlight detail."
    assert spotlight["notes_label"] == "Open release note on GitHub"
    assert spotlight["notes_url"] == (
        "https://github.com/odylith/odylith/blob/v0.1.5/odylith/runtime/source/release-notes/v0.1.5.md"
    )


def test_build_release_spotlight_replaces_placeholder_release_copy_with_real_fallback(tmp_path: Path) -> None:
    write_install_state(
        repo_root=tmp_path,
        payload={
            "active_version": "0.1.6",
            "activation_history": ["0.1.5", "0.1.6"],
            "installed_versions": {
                "0.1.6": {"runtime_root": str(tmp_path / ".odylith" / "runtime" / "versions" / "0.1.6")}
            },
        },
    )
    write_upgrade_spotlight(
        repo_root=tmp_path,
        from_version="0.1.5",
        to_version="0.1.6",
        release_tag="v0.1.6",
        release_url="https://example.com/releases/v0.1.6",
        release_published_at="2026-04-01T04:44:00Z",
        release_body="Odylith release v0.1.6",
        highlights=("Odylith release v0.1.6",),
    )

    spotlight = shell_onboarding.build_release_spotlight(repo_root=tmp_path)

    assert spotlight["title"] == "v0.1.6"
    assert spotlight["summary"] == ""
    assert spotlight["detail"] == ""
    assert spotlight["highlights"] == []


def test_build_release_spotlight_ages_out_but_version_story_remains(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    assert shell_onboarding._UPGRADE_SPOTLIGHT_MAX_AGE == timedelta(minutes=10)
    write_install_state(
        repo_root=tmp_path,
        payload={
            "active_version": "0.1.6",
            "activation_history": ["0.1.5", "0.1.6"],
            "installed_versions": {
                "0.1.6": {"runtime_root": str(tmp_path / ".odylith" / "runtime" / "versions" / "0.1.6")}
            },
        },
    )
    notes_root = tmp_path / "odylith" / "runtime" / "source" / "release-notes"
    notes_root.mkdir(parents=True, exist_ok=True)
    (notes_root / "v0.1.6.md").write_text(
        (
            "---\n"
            "version: 0.1.6\n"
            "published_at: 2026-04-01T04:44:00Z\n"
            "summary: Authored release summary.\n"
            "highlights:\n"
            "  - Authored highlight.\n"
            "---\n\n"
            "Authored release summary.\n\n"
            "Authored detail."
        ),
        encoding="utf-8",
    )
    write_upgrade_spotlight(
        repo_root=tmp_path,
        from_version="0.1.5",
        to_version="0.1.6",
        release_tag="v0.1.6",
        release_url="https://example.com/releases/v0.1.6",
        release_published_at="2026-04-01T04:44:00Z",
        release_body="Authored release summary.",
        highlights=("Authored highlight.",),
    )
    payload = load_upgrade_spotlight(repo_root=tmp_path)
    recorded_at = shell_onboarding._parse_iso_utc(payload["recorded_utc"])
    assert recorded_at is not None
    monkeypatch.setattr(
        shell_onboarding,
        "_utc_now",
        lambda: recorded_at + shell_onboarding._UPGRADE_SPOTLIGHT_MAX_AGE + timedelta(seconds=1),
    )

    assert shell_onboarding.build_release_spotlight(repo_root=tmp_path) == {}
    story = shell_onboarding.build_version_story(repo_root=tmp_path)
    assert story["show"] is True
    assert story["headline"] == "v0.1.6"
    assert story["reopen_label"] == "v0.1.6"
    assert story["summary"] == "Authored release summary."
    assert story["notes_url"] == (
        "https://github.com/odylith/odylith/blob/v0.1.6/odylith/runtime/source/release-notes/v0.1.6.md"
    )


def test_build_version_story_persists_recent_version_delta_for_consumer_repo(tmp_path: Path) -> None:
    write_install_state(
        repo_root=tmp_path,
        payload={
            "active_version": "0.1.5",
            "activation_history": ["0.1.4", "0.1.5"],
            "installed_versions": {
                "0.1.5": {"runtime_root": str(tmp_path / ".odylith" / "runtime" / "versions" / "0.1.5")}
            },
        },
    )
    notes_root = tmp_path / "odylith" / "runtime" / "source" / "release-notes"
    notes_root.mkdir(parents=True, exist_ok=True)
    (notes_root / "v0.1.5.md").write_text(
        (
            "---\n"
            "version: 0.1.5\n"
            "published_at: 2026-03-30T14:00:00Z\n"
            "summary: Odylith 0.1.5 clarified first contact.\n"
            "highlights:\n"
            "  - Release note highlight one.\n"
            "  - Release note highlight two.\n"
            "---\n\n"
            "Odylith 0.1.5 clarified first contact.\n\n"
            "The release note remains the short version-delta view."
        ),
        encoding="utf-8",
    )

    story = shell_onboarding.build_version_story(repo_root=tmp_path)

    assert story["show"] is True
    assert story["from_version"] == "0.1.4"
    assert story["to_version"] == "0.1.5"
    assert story["headline"] == "v0.1.5"
    assert story["cta_label"] == "Open release note on GitHub"
    assert story["reopen_label"] == "v0.1.5"
    assert story["summary"] == "Odylith 0.1.5 clarified first contact."
    assert story["highlights"] == ["Release note highlight one.", "Release note highlight two."]
    assert story["notes_url"] == (
        "https://github.com/odylith/odylith/blob/v0.1.5/odylith/runtime/source/release-notes/v0.1.5.md"
    )


def test_release_spotlight_and_version_story_stay_suppressed_in_product_repo(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='odylith'\n", encoding="utf-8")
    (tmp_path / "src" / "odylith").mkdir(parents=True, exist_ok=True)
    (tmp_path / "odylith").mkdir(parents=True, exist_ok=True)
    write_install_state(
        repo_root=tmp_path,
        payload={
            "active_version": "0.1.5",
            "activation_history": ["0.1.4", "0.1.5"],
            "installed_versions": {
                "0.1.5": {"runtime_root": str(tmp_path / ".odylith" / "runtime" / "versions" / "0.1.5")}
            },
        },
    )
    write_upgrade_spotlight(
        repo_root=tmp_path,
        from_version="0.1.4",
        to_version="0.1.5",
        release_tag="v0.1.5",
        release_body="Product-repo upgrades should not surface a consumer popup.",
        highlights=("Should stay hidden.",),
    )

    assert shell_onboarding.build_release_spotlight(repo_root=tmp_path) == {}
    assert shell_onboarding.build_version_story(repo_root=tmp_path) == {}


def test_build_welcome_state_dismiss_key_changes_when_onboarding_shape_changes(tmp_path: Path) -> None:
    blank = shell_onboarding.build_welcome_state(repo_root=tmp_path)
    (tmp_path / ".git").mkdir()
    (tmp_path / "src" / "payments").mkdir(parents=True, exist_ok=True)

    grounded = shell_onboarding.build_welcome_state(repo_root=tmp_path)

    assert blank["dismiss_key"] != grounded["dismiss_key"]
