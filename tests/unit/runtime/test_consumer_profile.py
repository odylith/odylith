import json
from pathlib import Path

from odylith.runtime.common.consumer_profile import (
    canonical_truth_token,
    default_consumer_profile,
    is_component_forensics_path,
    is_component_spec_path,
    is_runbook_path,
    legacy_truth_aliases,
    load_consumer_profile,
    truth_path_kind,
    write_consumer_profile,
)


def test_default_consumer_profile_is_generic(tmp_path: Path) -> None:
    repo_root = tmp_path / "consumer-repo"
    repo_root.mkdir()
    profile = default_consumer_profile(repo_root=repo_root)
    assert profile["consumer_id"] == "consumer-repo"
    assert profile["truth_roots"]["runbooks"] == "docs/runbooks"
    assert profile["odylith_write_policy"] == {
        "odylith_fix_mode": "feedback_only",
        "allow_odylith_mutations": False,
        "protected_roots": ["odylith", ".odylith"],
    }
    assert "".join(("ori", "on")) not in json.dumps(profile).lower()


def test_default_consumer_profile_prefers_repo_specific_runbooks_dir(tmp_path: Path) -> None:
    repo_root = tmp_path / "acme-consumer"
    (repo_root / "docs" / "runbooks" / "consumer").mkdir(parents=True)
    profile = default_consumer_profile(repo_root=repo_root)
    assert profile["truth_roots"]["runbooks"] == "docs/runbooks/consumer"


def test_default_consumer_profile_uses_installed_registry_truth_roots_even_when_consumer_docs_exist(tmp_path: Path) -> None:
    repo_root = tmp_path / "consumer-repo"
    (repo_root / "odylith" / "registry" / "source").mkdir(parents=True)
    (repo_root / "odylith" / "registry" / "source" / "component_registry.v1.json").write_text("{}\n", encoding="utf-8")
    (repo_root / "odylith" / "runtime").mkdir(parents=True)
    (repo_root / "odylith" / "runtime" / "CONTEXT_ENGINE_OPERATIONS.md").write_text("# Runbook\n", encoding="utf-8")
    (repo_root / "odylith" / "SPEC.md").write_text("# Odylith\n", encoding="utf-8")
    (repo_root / "docs" / "runbooks" / "consumer").mkdir(parents=True)

    profile = default_consumer_profile(repo_root=repo_root)

    assert profile["truth_roots"]["component_registry"] == "odylith/registry/source/component_registry.v1.json"
    assert profile["truth_roots"]["component_specs"] == "odylith/registry/source/components"
    assert profile["truth_roots"]["runbooks"] == "docs/runbooks"


def test_load_consumer_profile_preserves_explicit_consumer_truth_roots_when_installed_odylith_tree_exists(tmp_path: Path) -> None:
    repo_root = tmp_path / "consumer-repo"
    (repo_root / "consumer-registry" / "source" / "components").mkdir(parents=True)
    (repo_root / "consumer-registry" / "source" / "component_registry.v1.json").write_text("{}\n", encoding="utf-8")
    (repo_root / "odylith" / "registry" / "source").mkdir(parents=True)
    (repo_root / "odylith" / "registry" / "source" / "component_registry.v1.json").write_text("{}\n", encoding="utf-8")
    (repo_root / "consumer-runbooks").mkdir(parents=True)

    profile_path = repo_root / ".odylith" / "consumer-profile.json"
    profile_path.parent.mkdir(parents=True)
    profile_path.write_text(
        json.dumps(
            {
                "version": "v1",
                "consumer_id": "consumer-repo",
                "truth_roots": {
                    "component_registry": "consumer-registry/source/component_registry.v1.json",
                    "component_specs": "consumer-registry/source/components",
                    "runbooks": "consumer-runbooks",
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    payload = load_consumer_profile(repo_root=repo_root)

    assert payload["truth_roots"]["component_registry"] == "consumer-registry/source/component_registry.v1.json"
    assert payload["truth_roots"]["component_specs"] == "consumer-registry/source/components"
    assert payload["truth_roots"]["runbooks"] == "consumer-runbooks"


def test_load_consumer_profile_keeps_explicit_consumer_truth_roots_when_removed_legacy_roots_exist(tmp_path: Path) -> None:
    repo_root = tmp_path / "consumer-repo"
    (repo_root / "consumer-registry" / "source" / "components").mkdir(parents=True)
    (repo_root / "consumer-registry" / "source" / "component_registry.v1.json").write_text("{}\n", encoding="utf-8")
    (repo_root / "odylith" / "registry" / "source" / "components").mkdir(parents=True)
    (repo_root / "odylith" / "registry" / "source" / "component_registry.v1.json").write_text("{}\n", encoding="utf-8")
    (repo_root / "docs" / "components" / "specs").mkdir(parents=True)
    (repo_root / "contracts").mkdir(parents=True)
    (repo_root / "contracts" / "component_registry.v1.json").write_text("{}\n", encoding="utf-8")
    (repo_root / "consumer-runbooks").mkdir(parents=True)

    profile_path = repo_root / ".odylith" / "consumer-profile.json"
    profile_path.parent.mkdir(parents=True)
    profile_path.write_text(
        json.dumps(
            {
                "version": "v1",
                "consumer_id": "consumer-repo",
                "truth_roots": {
                    "component_registry": "consumer-registry/source/component_registry.v1.json",
                    "component_specs": "consumer-registry/source/components",
                    "runbooks": "consumer-runbooks",
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    payload = load_consumer_profile(repo_root=repo_root)

    assert payload["truth_roots"]["component_registry"] == "consumer-registry/source/component_registry.v1.json"
    assert payload["truth_roots"]["component_specs"] == "consumer-registry/source/components"
    assert payload["truth_roots"]["runbooks"] == "consumer-runbooks"


def test_write_consumer_profile_merges_overrides(tmp_path: Path) -> None:
    repo_root = tmp_path / "consumer-repo"
    repo_root.mkdir()
    path = write_consumer_profile(
        repo_root=repo_root,
        payload={
            "consumer_id": "acme",
            "truth_roots": {"runbooks": "consumer-runbooks/custom"},
        },
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["consumer_id"] == "acme"
    assert payload["truth_roots"]["runbooks"] == "consumer-runbooks/custom"
    assert payload["truth_roots"]["radar_source"] == "odylith/radar/source"


def test_write_consumer_profile_preserves_existing_values_when_no_payload_passed(tmp_path: Path) -> None:
    repo_root = tmp_path / "consumer-repo"
    repo_root.mkdir()
    existing = {
        "version": "v1",
        "consumer_id": "consumer-repo",
        "truth_roots": {"runbooks": "consumer-runbooks/custom"},
        "surface_roots": {"runtime_root": ".odylith-custom"},
    }
    profile_path = repo_root / ".odylith" / "consumer-profile.json"
    profile_path.parent.mkdir(parents=True)
    profile_path.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")

    path = write_consumer_profile(repo_root=repo_root)
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["truth_roots"]["runbooks"] == "consumer-runbooks/custom"
    assert payload["surface_roots"]["runtime_root"] == ".odylith-custom"


def test_write_consumer_profile_invalidates_process_cache(tmp_path: Path) -> None:
    repo_root = tmp_path / "consumer-repo"
    (repo_root / "consumer-runbooks-a").mkdir(parents=True)
    (repo_root / "consumer-runbooks-b").mkdir(parents=True)
    profile_path = repo_root / ".odylith" / "consumer-profile.json"
    profile_path.parent.mkdir(parents=True)
    profile_path.write_text(
        json.dumps(
            {
                "version": "v1",
                "consumer_id": "consumer-repo",
                "truth_roots": {
                    "runbooks": "consumer-runbooks-a",
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    before = load_consumer_profile(repo_root=repo_root)
    write_consumer_profile(
        repo_root=repo_root,
        payload={
            "version": "v1",
            "consumer_id": "consumer-repo",
            "truth_roots": {
                "runbooks": "consumer-runbooks-b",
            },
        },
    )
    after = load_consumer_profile(repo_root=repo_root)

    assert before["truth_roots"]["runbooks"] == "consumer-runbooks-a"
    assert after["truth_roots"]["runbooks"] == "consumer-runbooks-b"


def test_load_consumer_profile_keeps_explicit_consumer_truth_roots(tmp_path: Path) -> None:
    repo_root = tmp_path / "odylith"
    (repo_root / "src" / "odylith").mkdir(parents=True)
    (repo_root / "odylith" / "registry" / "source").mkdir(parents=True)
    (repo_root / "odylith" / "registry" / "source" / "component_registry.v1.json").write_text(
        "{}\n",
        encoding="utf-8",
    )
    (repo_root / "odylith" / "registry" / "source" / "components" / "odylith").mkdir(parents=True)
    (repo_root / "odylith" / "SPEC.md").write_text("# Odylith\n", encoding="utf-8")
    (repo_root / "odylith" / "INSTALL_AND_UPGRADE_RUNBOOK.md").write_text("# Runbook\n", encoding="utf-8")
    (repo_root / "pyproject.toml").write_text("[project]\nname='odylith'\n", encoding="utf-8")

    profile_path = repo_root / ".odylith" / "consumer-profile.json"
    profile_path.parent.mkdir(parents=True)
    profile_path.write_text(
        json.dumps(
            {
                "version": "v1",
                "consumer_id": "odylith",
                "truth_roots": {
                    "component_registry": "odylith/registry/source/component_registry.v1.json",
                    "component_specs": "odylith/registry/source/components",
                    "runbooks": "odylith",
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    payload = load_consumer_profile(repo_root=repo_root)

    assert payload["truth_roots"]["component_registry"] == "odylith/registry/source/component_registry.v1.json"
    assert payload["truth_roots"]["component_specs"] == "odylith/registry/source/components"
    assert payload["truth_roots"]["runbooks"] == "odylith"


def test_write_consumer_profile_keeps_explicit_public_odylith_truth_roots(tmp_path: Path) -> None:
    repo_root = tmp_path / "odylith"
    (repo_root / "src" / "odylith").mkdir(parents=True)
    (repo_root / "odylith" / "registry" / "source").mkdir(parents=True)
    (repo_root / "odylith" / "registry" / "source" / "component_registry.v1.json").write_text(
        "{}\n",
        encoding="utf-8",
    )
    (repo_root / "odylith" / "registry" / "source" / "components" / "odylith").mkdir(parents=True)
    (repo_root / "odylith" / "SPEC.md").write_text("# Odylith\n", encoding="utf-8")
    (repo_root / "odylith" / "INSTALL_AND_UPGRADE_RUNBOOK.md").write_text("# Runbook\n", encoding="utf-8")
    (repo_root / "pyproject.toml").write_text("[project]\nname='odylith'\n", encoding="utf-8")

    profile_path = repo_root / ".odylith" / "consumer-profile.json"
    profile_path.parent.mkdir(parents=True)
    profile_path.write_text(
        json.dumps(
            {
                "version": "v1",
                "consumer_id": "odylith",
                "truth_roots": {
                    "component_registry": "odylith/registry/source/component_registry.v1.json",
                    "component_specs": "odylith/registry/source/components",
                    "runbooks": "odylith",
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    path = write_consumer_profile(repo_root=repo_root)
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["truth_roots"]["component_registry"] == "odylith/registry/source/component_registry.v1.json"
    assert payload["truth_roots"]["component_specs"] == "odylith/registry/source/components"
    assert payload["truth_roots"]["runbooks"] == "odylith"


def test_default_consumer_profile_allows_odylith_mutations_in_public_product_repo(tmp_path: Path) -> None:
    repo_root = tmp_path / "odylith"
    (repo_root / "src" / "odylith").mkdir(parents=True)
    (repo_root / "odylith").mkdir()
    (repo_root / "pyproject.toml").write_text("[project]\nname='odylith'\n", encoding="utf-8")

    profile = default_consumer_profile(repo_root=repo_root)

    assert profile["odylith_write_policy"] == {
        "odylith_fix_mode": "maintainer_authorized",
        "allow_odylith_mutations": True,
        "protected_roots": [],
    }


def test_canonical_truth_token_preserves_unknown_consumer_tokens(tmp_path: Path) -> None:
    repo_root = tmp_path / "consumer-repo"
    repo_root.mkdir()
    write_consumer_profile(
        repo_root=repo_root,
        payload={
            "truth_roots": {
                "component_specs": "odylith/registry/source/components",
                "runbooks": "consumer-runbooks/platform",
            }
        },
    )
    assert canonical_truth_token("legacy/components/compass.md", repo_root=repo_root) == "legacy/components/compass.md"
    assert canonical_truth_token("legacy/components/odylith-context-engine.md", repo_root=repo_root) == "legacy/components/odylith-context-engine.md"
    assert canonical_truth_token("legacy/runbooks/platform/subagent-router-operations.md", repo_root=repo_root) == "legacy/runbooks/platform/subagent-router-operations.md"


def test_component_spec_and_runbook_detection_follow_canonical_installed_paths(tmp_path: Path) -> None:
    repo_root = tmp_path / "consumer-repo"
    (repo_root / "odylith" / "compass").mkdir(parents=True)
    (repo_root / "odylith" / "runtime").mkdir(parents=True)
    (repo_root / "odylith" / "compass" / "SPEC.md").write_text("# Compass\n", encoding="utf-8")
    write_consumer_profile(
        repo_root=repo_root,
        payload={
            "truth_roots": {
                "component_specs": "odylith/registry/source/components",
                "runbooks": "consumer-runbooks/platform",
            }
        },
    )

    assert is_component_spec_path("odylith/registry/source/components/compass/CURRENT_SPEC.md", repo_root=repo_root) is True
    assert is_component_spec_path("odylith/registry/source/components/compass/FORENSICS.v1.json", repo_root=repo_root) is False
    assert is_component_forensics_path("odylith/registry/source/components/compass/FORENSICS.v1.json", repo_root=repo_root) is True
    assert truth_path_kind("odylith/registry/source/components/compass/CURRENT_SPEC.md", repo_root=repo_root) == "component_spec"
    assert truth_path_kind("odylith/registry/source/components/compass/FORENSICS.v1.json", repo_root=repo_root) == "component_forensics"
    assert (
        is_component_forensics_path(
            "odylith/registry/source/components/compass/FORENSICS.v1.json",
            repo_root=repo_root,
        )
        is True
    )
    assert is_runbook_path("consumer-runbooks/platform/odylith-context-engine-operations.md", repo_root=repo_root) is True
    assert truth_path_kind("consumer-runbooks/platform/odylith-context-engine-operations.md", repo_root=repo_root) == "runbook"


def test_truth_path_kind_uses_custom_consumer_truth_roots(tmp_path: Path) -> None:
    repo_root = tmp_path / "consumer-repo"
    (repo_root / "consumer-registry" / "source" / "components" / "compass").mkdir(parents=True)
    (repo_root / "consumer-runbooks" / "platform").mkdir(parents=True)
    write_consumer_profile(
        repo_root=repo_root,
        payload={
            "truth_roots": {
                "component_specs": "consumer-registry/source/components",
                "runbooks": "consumer-runbooks/platform",
            }
        },
    )

    assert truth_path_kind("consumer-registry/source/components/compass/CURRENT_SPEC.md", repo_root=repo_root) == "component_spec"
    assert truth_path_kind("consumer-registry/source/components/compass/FORENSICS.v1.json", repo_root=repo_root) == "component_forensics"
    assert truth_path_kind("consumer-runbooks/platform/router.md", repo_root=repo_root) == "runbook"


def test_canonical_truth_token_maps_legacy_product_modules_to_owned_specs() -> None:
    assert canonical_truth_token("scripts/render_backlog_ui.py") == "odylith/registry/source/components/radar/CURRENT_SPEC.md"
    assert canonical_truth_token("scripts/odylith_context_engine.py") == "odylith/registry/source/components/odylith-context-engine/CURRENT_SPEC.md"
    assert canonical_truth_token("tests/scripts/test_subagent_router.py") == "odylith/registry/source/components/subagent-router/CURRENT_SPEC.md"
    assert canonical_truth_token("scripts/release/publish_release_assets.py") == "odylith/registry/source/components/release/CURRENT_SPEC.md"
    assert canonical_truth_token("scripts/release/local_release_smoke.py") == "odylith/registry/source/components/release/CURRENT_SPEC.md"
    assert canonical_truth_token("scripts/release_semver.py") == "odylith/registry/source/components/release/CURRENT_SPEC.md"
    assert canonical_truth_token("scripts/release_version_session.py") == "odylith/registry/source/components/release/CURRENT_SPEC.md"
    assert canonical_truth_token("scripts/audit_third_party_licenses.py") == "odylith/registry/source/components/release/CURRENT_SPEC.md"
    assert (
        canonical_truth_token("scripts/templates/tooling_dashboard/page.html.j2")
        == "odylith/registry/source/components/dashboard/CURRENT_SPEC.md"
    )


def test_canonical_truth_token_preserves_unknown_public_doc_paths() -> None:
    assert canonical_truth_token("odylith/docs/legacy/odylith-context-engine.md") == "odylith/docs/legacy/odylith-context-engine.md"
    assert canonical_truth_token("odylith/docs/legacy/dashboard.md") == "odylith/docs/legacy/dashboard.md"
    assert canonical_truth_token("odylith/docs/legacy/casebook.md") == "odylith/docs/legacy/casebook.md"
    assert canonical_truth_token("odylith/docs/legacy/delivery-governance-surfaces.md") == "odylith/docs/legacy/delivery-governance-surfaces.md"


def test_legacy_truth_aliases_keep_only_direct_product_spec_aliases() -> None:
    aliases = legacy_truth_aliases()
    assert aliases["odylith/SPEC.md"] == "odylith/registry/source/components/odylith/CURRENT_SPEC.md"
    assert "odylith/docs/legacy/odylith.md" not in aliases


def test_canonical_truth_token_preserves_unknown_contract_paths() -> None:
    assert canonical_truth_token("contracts/legacy-snapshot.v4.schema.json") == "contracts/legacy-snapshot.v4.schema.json"
    assert canonical_truth_token("contracts/legacy-case.v1.schema.json") == "contracts/legacy-case.v1.schema.json"
    assert canonical_truth_token("contracts/legacy-outcome.v1.schema.json") == "contracts/legacy-outcome.v1.schema.json"
    assert canonical_truth_token("contracts/legacy-correction.v1.schema.json") == "contracts/legacy-correction.v1.schema.json"
