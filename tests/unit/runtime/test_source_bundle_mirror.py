from __future__ import annotations

from pathlib import Path

from odylith.runtime.surfaces import source_bundle_mirror


def _product_repo_root(tmp_path: Path) -> Path:
    (tmp_path / "odylith").mkdir(parents=True, exist_ok=True)
    (tmp_path / "src" / "odylith" / "bundle" / "assets" / "odylith").mkdir(parents=True, exist_ok=True)
    return tmp_path


def test_sync_live_paths_copies_live_surface_file_into_bundle_mirror(tmp_path: Path) -> None:
    repo_root = _product_repo_root(tmp_path)
    live_path = repo_root / "odylith" / "compass" / "compass-shared.v1.js"
    live_path.parent.mkdir(parents=True, exist_ok=True)
    live_path.write_text("window.__test__ = true;\n", encoding="utf-8")

    mirrored = source_bundle_mirror.sync_live_paths(
        repo_root=repo_root,
        live_paths=(live_path,),
    )

    mirror_path = repo_root / "src" / "odylith" / "bundle" / "assets" / "odylith" / "compass" / "compass-shared.v1.js"
    assert mirrored == (mirror_path.resolve(),)
    assert mirror_path.read_text(encoding="utf-8") == "window.__test__ = true;\n"


def test_sync_live_glob_updates_active_shards_and_removes_stale_bundle_mirrors(tmp_path: Path) -> None:
    repo_root = _product_repo_root(tmp_path)
    live_dir = repo_root / "odylith" / "casebook"
    live_dir.mkdir(parents=True, exist_ok=True)
    active_one = live_dir / "casebook-detail-shard-001.v1.js"
    active_two = live_dir / "casebook-detail-shard-002.v1.js"
    active_one.write_text("one\n", encoding="utf-8")
    active_two.write_text("two\n", encoding="utf-8")

    bundle_dir = repo_root / "src" / "odylith" / "bundle" / "assets" / "odylith" / "casebook"
    bundle_dir.mkdir(parents=True, exist_ok=True)
    stale_bundle = bundle_dir / "casebook-detail-shard-099.v1.js"
    stale_bundle.write_text("stale\n", encoding="utf-8")

    mirrored = source_bundle_mirror.sync_live_glob(
        repo_root=repo_root,
        live_dir=live_dir,
        pattern="casebook-detail-shard-*.v1.js",
    )

    assert {path.name for path in mirrored} == {
        "casebook-detail-shard-001.v1.js",
        "casebook-detail-shard-002.v1.js",
    }
    assert not stale_bundle.exists()
    assert (bundle_dir / "casebook-detail-shard-001.v1.js").read_text(encoding="utf-8") == "one\n"
    assert (bundle_dir / "casebook-detail-shard-002.v1.js").read_text(encoding="utf-8") == "two\n"


def test_sync_live_glob_removes_empty_mirror_dir_when_live_dir_is_missing(tmp_path: Path) -> None:
    repo_root = _product_repo_root(tmp_path)
    live_dir = repo_root / "odylith" / "compass" / "runtime" / "history" / "archive"
    bundle_dir = repo_root / "src" / "odylith" / "bundle" / "assets" / "odylith" / "compass" / "runtime" / "history" / "archive"
    bundle_dir.mkdir(parents=True, exist_ok=True)
    stale_bundle = bundle_dir / "2026-03-01.v1.json.gz"
    stale_bundle.write_text("stale\n", encoding="utf-8")

    mirrored = source_bundle_mirror.sync_live_glob(
        repo_root=repo_root,
        live_dir=live_dir,
        pattern="*.v1.json.gz",
    )

    assert mirrored == ()
    assert not stale_bundle.exists()
    assert not bundle_dir.exists()


def test_repo_governance_docs_preserve_watcher_and_brief_contract_in_bundle_mirrors() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    checks = (
        (
            repo_root / "odylith" / "agents-guidelines" / "DELIVERY_AND_GOVERNANCE_SURFACES.md",
            repo_root / "src" / "odylith" / "bundle" / "assets" / "odylith" / "agents-guidelines" / "DELIVERY_AND_GOVERNANCE_SURFACES.md",
            "`odylith compass watch-transactions --repo-root .` is the supported change-driven local watcher",
        ),
        (
            repo_root / "odylith" / "skills" / "odylith-delivery-governance-surface-ops" / "SKILL.md",
            repo_root / "src" / "odylith" / "bundle" / "assets" / "odylith" / "skills" / "odylith-delivery-governance-surface-ops" / "SKILL.md",
            "./.odylith/bin/odylith compass watch-transactions --repo-root .",
        ),
        (
            repo_root / "odylith" / "skills" / "odylith-compass-executive" / "SKILL.md",
            repo_root / "src" / "odylith" / "bundle" / "assets" / "odylith" / "skills" / "odylith-compass-executive" / "SKILL.md",
            "Scoped selection does not buy a foreground provider exception.",
        ),
        (
            repo_root / "odylith" / "skills" / "odylith-session-context" / "SKILL.md",
            repo_root / "src" / "odylith" / "bundle" / "assets" / "odylith" / "skills" / "odylith-session-context" / "SKILL.md",
            "never turn an ordinary restart into a foreground provider refresh",
        ),
    )

    for live_path, mirror_path, expected_snippet in checks:
        assert expected_snippet in live_path.read_text(encoding="utf-8")
        assert expected_snippet in mirror_path.read_text(encoding="utf-8")
