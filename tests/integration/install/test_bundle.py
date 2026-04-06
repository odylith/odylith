from odylith.bundle import bundle_root


def test_bundle_root_contains_installed_agents_entrypoint() -> None:
    root = bundle_root()
    assert (root / "AGENTS.md").is_file()
    assert (root / "agents-guidelines").is_dir()
    assert (root / "skills").is_dir()
    assert (root / "skills" / "diagram-catalog" / "SKILL.md").is_file()


def test_bundle_root_contains_managed_governance_surface_assets() -> None:
    root = bundle_root()
    assert (root / "atlas" / "source" / "AGENTS.md").is_file()
    assert (root / "atlas" / "source" / "architecture-domains.v1.json").is_file()
    assert (root / "compass" / "runtime" / "AGENTS.md").is_file()
    assert (root / "radar" / "source" / "AGENTS.md").is_file()
    assert (root / "casebook" / "bugs" / "AGENTS.md").is_file()
    assert (root / "registry" / "source" / "AGENTS.md").is_file()
    assert (root / "registry" / "source" / "component_registry.v1.json").is_file()
    assert (root / "runtime" / "contracts" / "delivery_intelligence_snapshot.v4.schema.json").is_file()
    assert (root / "runtime" / "contracts" / "tribunal_case.v1.schema.json").is_file()
    assert (root / "runtime" / "contracts" / "tribunal_outcome.v1.schema.json").is_file()
    assert (root / "runtime" / "contracts" / "correction_packet.v1.schema.json").is_file()
    assert (root / "technical-plans" / "AGENTS.md").is_file()
    assert (root / "casebook" / "bugs" / "INDEX.md").is_file()


def test_bundle_root_does_not_ship_public_workstream_or_bug_records_into_consumer_truth_roots() -> None:
    root = bundle_root()
    assert not (root / "radar" / "source" / "ideas").exists()
    assert not (root / "technical-plans" / "in-progress").exists()
    assert not (root / "casebook" / "bugs" / "2026-02-15-mirror-registry-barrier-deadlock-in-tests.md").exists()
    assert not (root / "compass" / "runtime" / "codex-stream.v1.jsonl").exists()
    assert not (root / "compass" / "runtime" / "current.v1.json").exists()
    assert not (root / "compass" / "runtime" / "current.v1.js").exists()
    assert not (root / "compass" / "runtime" / "history").exists()
