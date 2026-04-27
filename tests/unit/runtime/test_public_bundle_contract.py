from __future__ import annotations

from pathlib import Path

from odylith.runtime.surfaces import source_bundle_mirror


REPO_ROOT = Path(__file__).resolve().parents[3]
BUNDLE_ROOT = REPO_ROOT / "src" / "odylith" / "bundle" / "assets" / "odylith"


def test_consumer_source_bundle_contains_no_maintainer_truth_artifacts() -> None:
    unsafe = [
        path.relative_to(BUNDLE_ROOT).as_posix()
        for path in sorted(BUNDLE_ROOT.rglob("*"))
        if path.is_file()
        and not source_bundle_mirror.is_consumer_safe_bundle_relative_path(path.relative_to(BUNDLE_ROOT))
    ]

    assert unsafe == []


def test_consumer_source_bundle_contains_no_local_maintainer_paths() -> None:
    forbidden = (b"/Users/freedom", b"/private/var/folders")
    leaked = [
        path.relative_to(BUNDLE_ROOT).as_posix()
        for path in sorted(BUNDLE_ROOT.rglob("*"))
        if path.is_file() and any(token in path.read_bytes() for token in forbidden)
    ]

    assert leaked == []


def test_consumer_safe_bundle_contract_rejects_known_maintainer_truth_leak_classes() -> None:
    rejected = (
        "casebook/bugs/2026-04-16-intervention-hook-payloads-can-be-generated-but-never-reach-chat-visible-ux.md",
        "casebook/casebook-payload.v1.js",
        "casebook/casebook-detail-shard-001.v1.js",
        "compass/compass-payload.v1.js",
        "compass/compass-source-truth.v1.json",
        "compass/runtime/current.v1.json",
        "radar/source/INDEX.md",
        "radar/source/programs/B-096.execution-waves.v1.json",
        "technical-plans/done/2026-04/example.md",
        "registry/source/component_registry.v1.json",
        "registry/source/components/compass/CURRENT_SPEC.md",
        "registry/source/components/compass/FORENSICS.v1.json",
    )
    allowed = (
        "casebook/bugs/AGENTS.md",
        "compass/runtime/CLAUDE.md",
        "compass/compass-app.v1.js",
        "compass/compass-style-base.v1.css",
        "runtime/source/release-notes/v0.1.11.md",
        "skills/odylith-start/SKILL.md",
    )

    for token in rejected:
        assert not source_bundle_mirror.is_consumer_safe_bundle_relative_path(token)
    for token in allowed:
        assert source_bundle_mirror.is_consumer_safe_bundle_relative_path(token)
