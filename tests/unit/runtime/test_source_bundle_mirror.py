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


def test_sync_live_glob_updates_allowed_assets_and_removes_stale_bundle_mirrors(tmp_path: Path) -> None:
    repo_root = _product_repo_root(tmp_path)
    live_dir = repo_root / "odylith" / "compass"
    live_dir.mkdir(parents=True, exist_ok=True)
    active_one = live_dir / "compass-style-base.v1.css"
    active_two = live_dir / "compass-style-surface.v1.css"
    active_one.write_text("one\n", encoding="utf-8")
    active_two.write_text("two\n", encoding="utf-8")

    bundle_dir = repo_root / "src" / "odylith" / "bundle" / "assets" / "odylith" / "compass"
    bundle_dir.mkdir(parents=True, exist_ok=True)
    stale_bundle = bundle_dir / "compass-style-stale.v1.css"
    stale_bundle.write_text("stale\n", encoding="utf-8")

    mirrored = source_bundle_mirror.sync_live_glob(
        repo_root=repo_root,
        live_dir=live_dir,
        pattern="compass-style-*.css",
    )

    assert {path.name for path in mirrored} == {
        "compass-style-base.v1.css",
        "compass-style-surface.v1.css",
    }
    assert not stale_bundle.exists()
    assert (bundle_dir / "compass-style-base.v1.css").read_text(encoding="utf-8") == "one\n"
    assert (bundle_dir / "compass-style-surface.v1.css").read_text(encoding="utf-8") == "two\n"


def test_sync_live_glob_removes_empty_mirror_dir_when_live_dir_is_missing(tmp_path: Path) -> None:
    repo_root = _product_repo_root(tmp_path)
    live_dir = repo_root / "odylith" / "compass" / "runtime" / "history" / "archive"
    bundle_dir = (
        repo_root
        / "src"
        / "odylith"
        / "bundle"
        / "assets"
        / "odylith"
        / "compass"
        / "runtime"
        / "history"
        / "archive"
    )
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


def test_sync_live_paths_refuses_maintainer_truth_and_removes_existing_bundle_file(tmp_path: Path) -> None:
    repo_root = _product_repo_root(tmp_path)
    live_path = repo_root / "odylith" / "compass" / "compass-payload.v1.js"
    live_path.parent.mkdir(parents=True, exist_ok=True)
    live_path.write_text("window.__ODYLITH_COMPASS_SHELL_DATA__ = {workstreams: []};\n", encoding="utf-8")
    mirror_path = (
        repo_root
        / "src"
        / "odylith"
        / "bundle"
        / "assets"
        / "odylith"
        / "compass"
        / "compass-payload.v1.js"
    )
    mirror_path.parent.mkdir(parents=True, exist_ok=True)
    mirror_path.write_text("stale maintainer payload\n", encoding="utf-8")

    mirrored = source_bundle_mirror.sync_live_paths(repo_root=repo_root, live_paths=(live_path,))

    assert mirrored == ()
    assert not mirror_path.exists()


def test_repo_governance_docs_preserve_watcher_and_brief_contract_in_bundle_mirrors() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    checks = (
        (
            repo_root / "odylith" / "agents-guidelines" / "DELIVERY_AND_GOVERNANCE_SURFACES.md",
            repo_root
            / "src"
            / "odylith"
            / "bundle"
            / "assets"
            / "odylith"
            / "agents-guidelines"
            / "DELIVERY_AND_GOVERNANCE_SURFACES.md",
            "`odylith compass watch-transactions --repo-root .` is the supported change-driven local watcher",
        ),
        (
            repo_root / "odylith" / "skills" / "odylith-delivery-governance-surface-ops" / "SKILL.md",
            repo_root
            / "src"
            / "odylith"
            / "bundle"
            / "assets"
            / "odylith"
            / "skills"
            / "odylith-delivery-governance-surface-ops"
            / "SKILL.md",
            "./.odylith/bin/odylith compass watch-transactions --repo-root .",
        ),
        (
            repo_root / "odylith" / "skills" / "odylith-compass-executive" / "SKILL.md",
            repo_root
            / "src"
            / "odylith"
            / "bundle"
            / "assets"
            / "odylith"
            / "skills"
            / "odylith-compass-executive"
            / "SKILL.md",
            "Scoped selection does not buy a foreground provider exception.",
        ),
        (
            repo_root / "odylith" / "skills" / "odylith-session-context" / "SKILL.md",
            repo_root
            / "src"
            / "odylith"
            / "bundle"
            / "assets"
            / "odylith"
            / "skills"
            / "odylith-session-context"
            / "SKILL.md",
            "never turn an ordinary restart into a foreground provider refresh",
        ),
    )

    for live_path, mirror_path, expected_snippet in checks:
        live_text = live_path.read_text(encoding="utf-8")
        mirror_text = mirror_path.read_text(encoding="utf-8")
        assert expected_snippet in live_text
        assert expected_snippet in mirror_text
        assert live_text == mirror_text


def test_human_visible_clarity_floor_travels_to_bundle_mirrors() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    checks = (
        (
            "odylith/AGENTS.md",
            "src/odylith/bundle/assets/odylith/AGENTS.md",
            "Generated human-visible content has a non-negotiable clarity floor across all lanes",
        ),
        (
            "odylith/agents-guidelines/ANTI_SLOP_AND_DECOMPOSITION.md",
            "src/odylith/bundle/assets/odylith/agents-guidelines/ANTI_SLOP_AND_DECOMPOSITION.md",
            "grammatically coherent, and clear about the thing it describes",
        ),
        (
            "odylith/agents-guidelines/PRODUCT_SURFACES_AND_RUNTIME.md",
            "src/odylith/bundle/assets/odylith/agents-guidelines/PRODUCT_SURFACES_AND_RUNTIME.md",
            "what this is, why it matters, and what the reader should do or trust",
        ),
        (
            "odylith/agents-guidelines/DELIVERY_AND_GOVERNANCE_SURFACES.md",
            "src/odylith/bundle/assets/odylith/agents-guidelines/DELIVERY_AND_GOVERNANCE_SURFACES.md",
            "surface names, IDs, lifecycle states, and internal control-plane terms cannot",
        ),
        (
            "odylith/skills/odylith-greenfield-governance/SKILL.md",
            "src/odylith/bundle/assets/odylith/skills/odylith-greenfield-governance/SKILL.md",
            "Product meaning comes before artifact mapping",
        ),
        (
            "odylith/skills/odylith-component-registry/SKILL.md",
            "src/odylith/bundle/assets/odylith/skills/odylith-component-registry/SKILL.md",
            "Component specs must be component-specific, not repeated template copy",
        ),
        (
            "odylith/radar/source/AGENTS.md",
            "src/odylith/bundle/assets/odylith/radar/source/AGENTS.md",
            "Human-visible Radar copy must be plain-English",
        ),
        (
            "odylith/registry/source/AGENTS.md",
            "src/odylith/bundle/assets/odylith/registry/source/AGENTS.md",
            "Human-visible Registry copy must be simple",
        ),
        (
            "odylith/atlas/source/AGENTS.md",
            "src/odylith/bundle/assets/odylith/atlas/source/AGENTS.md",
            "Human-visible Atlas copy must explain",
        ),
        (
            "odylith/compass/runtime/AGENTS.md",
            "src/odylith/bundle/assets/odylith/compass/runtime/AGENTS.md",
            "Human-visible Compass copy must be concise",
        ),
    )

    for live_rel, mirror_rel, expected_snippet in checks:
        live_text = (repo_root / live_rel).read_text(encoding="utf-8")
        mirror_text = (repo_root / mirror_rel).read_text(encoding="utf-8")
        assert expected_snippet in live_text
        assert expected_snippet in mirror_text
        assert live_text == mirror_text


def test_migration_observer_agent_guidance_stays_maintainer_only() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    forbidden_tokens = (
        "migration-observer:<version>:<surface>:<fingerprint>",
        "Any consumer-visible Odylith surface change must assess installed consumer",
        "Any Odylith surface change must be assessed against already-installed",
        "Every consumer-visible surface change must be assessed for already-installed",
        "surface migration observer emits a missing migration-assessment",
    )
    consumer_safe_paths = (
        repo_root / "AGENTS.md",
        repo_root / "odylith" / "AGENTS.md",
        repo_root / "odylith" / "agents-guidelines" / "DELIVERY_AND_GOVERNANCE_SURFACES.md",
        repo_root / "odylith" / "agents-guidelines" / "UPGRADE_AND_RECOVERY.md",
        repo_root / "odylith" / "skills" / "odylith-code-hygiene-guard" / "SKILL.md",
        repo_root / "odylith" / "skills" / "odylith-sync" / "SKILL.md",
        repo_root / "src" / "odylith" / "bundle" / "assets" / "odylith" / "AGENTS.md",
        repo_root
        / "src"
        / "odylith"
        / "bundle"
        / "assets"
        / "odylith"
        / "agents-guidelines"
        / "DELIVERY_AND_GOVERNANCE_SURFACES.md",
        repo_root
        / "src"
        / "odylith"
        / "bundle"
        / "assets"
        / "odylith"
        / "agents-guidelines"
        / "UPGRADE_AND_RECOVERY.md",
        repo_root
        / "src"
        / "odylith"
        / "bundle"
        / "assets"
        / "odylith"
        / "skills"
        / "odylith-code-hygiene-guard"
        / "SKILL.md",
        repo_root
        / "src"
        / "odylith"
        / "bundle"
        / "assets"
        / "odylith"
        / "skills"
        / "odylith-sync"
        / "SKILL.md",
    )

    for path in consumer_safe_paths:
        text = path.read_text(encoding="utf-8")
        for token in forbidden_tokens:
            assert token not in text, path

    maintainer_agents = (repo_root / "odylith" / "maintainer" / "AGENTS.md").read_text(encoding="utf-8")
    maintainer_skill = (
        repo_root / "odylith" / "maintainer" / "skills" / "fail-closed-code-hygiene" / "SKILL.md"
    ).read_text(encoding="utf-8")

    assert "maintainer release-gate" in maintainer_agents
    assert "obligation only" in maintainer_agents
    assert "migration-observer:<version>:<surface>:<fingerprint>" in maintainer_agents
    assert "Keep that migration-observer rule maintainer-only" in maintainer_skill
    assert "migration-observer:<version>:<surface>:<fingerprint>" in maintainer_skill


def test_github_issue_pipeline_guidance_stays_maintainer_only() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    removed_paths = (
        repo_root / "odylith" / "agents-guidelines" / "GITHUB_ISSUE_PIPELINE.md",
        repo_root / "odylith" / "skills" / "odylith-github-issue-triage" / "SKILL.md",
        repo_root / "odylith" / "skills" / "odylith-github-release-closeout" / "SKILL.md",
        repo_root / ".agents" / "skills" / "odylith-github-issue-triage" / "SKILL.md",
        repo_root / ".agents" / "skills" / "odylith-github-release-closeout" / "SKILL.md",
        repo_root / ".claude" / "skills" / "odylith-github-issue-triage" / "SKILL.md",
        repo_root / ".claude" / "skills" / "odylith-github-release-closeout" / "SKILL.md",
        repo_root
        / "src"
        / "odylith"
        / "bundle"
        / "assets"
        / "odylith"
        / "agents-guidelines"
        / "GITHUB_ISSUE_PIPELINE.md",
        repo_root
        / "src"
        / "odylith"
        / "bundle"
        / "assets"
        / "odylith"
        / "skills"
        / "odylith-github-issue-triage"
        / "SKILL.md",
        repo_root
        / "src"
        / "odylith"
        / "bundle"
        / "assets"
        / "odylith"
        / "skills"
        / "odylith-github-release-closeout"
        / "SKILL.md",
        repo_root
        / "src"
        / "odylith"
        / "bundle"
        / "assets"
        / "project-root"
        / ".agents"
        / "skills"
        / "odylith-github-issue-triage"
        / "SKILL.md",
        repo_root
        / "src"
        / "odylith"
        / "bundle"
        / "assets"
        / "project-root"
        / ".agents"
        / "skills"
        / "odylith-github-release-closeout"
        / "SKILL.md",
        repo_root
        / "src"
        / "odylith"
        / "bundle"
        / "assets"
        / "project-root"
        / ".claude"
        / "skills"
        / "odylith-github-issue-triage"
        / "SKILL.md",
        repo_root
        / "src"
        / "odylith"
        / "bundle"
        / "assets"
        / "project-root"
        / ".claude"
        / "skills"
        / "odylith-github-release-closeout"
        / "SKILL.md",
    )
    for path in removed_paths:
        assert not path.exists(), path

    source_readme = (repo_root / "odylith" / "README.md").read_text(encoding="utf-8")
    assert "product-repo-only `maintainer/` subtree" in source_readme
    assert "That subtree is excluded from consumer bundle assets." in source_readme
    assert "Those live under `odylith/maintainer/`" not in source_readme
    assert "- `maintainer/`" not in source_readme

    bundle_readme = (
        repo_root / "src" / "odylith" / "bundle" / "assets" / "odylith" / "README.md"
    ).read_text(encoding="utf-8")
    assert "maintainer/" not in bundle_readme
    assert "maintainer-only" not in bundle_readme
    assert "product-repo-only" not in bundle_readme

    consumer_guidance_paths = (
        repo_root / "odylith" / "agents-guidelines" / "CODING_STANDARDS.md",
        repo_root / "odylith" / "agents-guidelines" / "PRODUCT_SURFACES_AND_RUNTIME.md",
        repo_root / "odylith" / "agents-guidelines" / "SECURITY_AND_TRUST.md",
        repo_root / "odylith" / "agents-guidelines" / "UPGRADE_AND_RECOVERY.md",
        repo_root / "odylith" / "agents-guidelines" / "VALIDATION_AND_TESTING.md",
        repo_root / "odylith" / "skills" / "odylith-guidance-behavior" / "SKILL.md",
        repo_root / "src" / "odylith" / "bundle" / "assets" / "odylith" / "AGENTS.md",
        repo_root / "src" / "odylith" / "bundle" / "assets" / "odylith" / "agents-guidelines" / "CODING_STANDARDS.md",
        repo_root
        / "src"
        / "odylith"
        / "bundle"
        / "assets"
        / "odylith"
        / "agents-guidelines"
        / "PRODUCT_SURFACES_AND_RUNTIME.md",
        repo_root
        / "src"
        / "odylith"
        / "bundle"
        / "assets"
        / "odylith"
        / "agents-guidelines"
        / "SECURITY_AND_TRUST.md",
        repo_root
        / "src"
        / "odylith"
        / "bundle"
        / "assets"
        / "odylith"
        / "agents-guidelines"
        / "UPGRADE_AND_RECOVERY.md",
        repo_root
        / "src"
        / "odylith"
        / "bundle"
        / "assets"
        / "odylith"
        / "agents-guidelines"
        / "VALIDATION_AND_TESTING.md",
        repo_root
        / "src"
        / "odylith"
        / "bundle"
        / "assets"
        / "odylith"
        / "skills"
        / "odylith-guidance-behavior"
        / "SKILL.md",
    )
    forbidden_consumer_fragments = (
        "odylith/maintainer/",
        "../maintainer",
        "maintainer/AGENTS.md",
        "maintainer/agents-guidelines",
        "maintainer-only release guidance",
        "explicit maintainer-only override",
        "product-repo-only IDs",
    )
    for path in consumer_guidance_paths:
        text = path.read_text(encoding="utf-8")
        for fragment in forbidden_consumer_fragments:
            assert fragment not in text, path

    maintainer_guideline = (repo_root / "odylith" / "maintainer" / "agents-guidelines" / "GITHUB_ISSUE_PIPELINE.md")
    maintainer_triage = repo_root / "odylith" / "maintainer" / "skills" / "odylith-github-issue-triage" / "SKILL.md"
    maintainer_closeout = (
        repo_root / "odylith" / "maintainer" / "skills" / "odylith-github-release-closeout" / "SKILL.md"
    )

    assert "Do not mirror this guideline into consumer-safe" in maintainer_guideline.read_text(encoding="utf-8")
    assert "maintainer-only skill" in maintainer_triage.read_text(encoding="utf-8")
    assert "maintainer-only skill" in maintainer_closeout.read_text(encoding="utf-8")
