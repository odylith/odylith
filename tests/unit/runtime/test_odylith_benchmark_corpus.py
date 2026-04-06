from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PUBLIC_CORPUS = ROOT / "odylith" / "runtime" / "source" / "optimization-evaluation-corpus.v1.json"
BUNDLE_CORPUS = (
    ROOT / "src" / "odylith" / "bundle" / "assets" / "odylith" / "runtime" / "source" / "optimization-evaluation-corpus.v1.json"
)


def _load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_public_and_bundle_benchmark_corpus_stay_aligned() -> None:
    assert _load(PUBLIC_CORPUS) == _load(BUNDLE_CORPUS)


def test_benchmark_corpus_covers_complex_repo_agentic_scenarios() -> None:
    corpus = _load(PUBLIC_CORPUS)
    assert isinstance(corpus.get("scenarios"), list)
    assert isinstance(corpus.get("architecture_scenarios"), list)
    assert "cases" not in corpus
    assert "architecture_cases" not in corpus
    scenarios = list(corpus.get("scenarios", []))
    architecture_scenarios = list(corpus.get("architecture_scenarios", []))
    families = {str(case.get("family", "")).strip() for case in scenarios}
    scenario_ids = {str(case.get("case_id", "")).strip() for case in scenarios}
    architecture_ids = {str(case.get("case_id", "")).strip() for case in architecture_scenarios}
    architecture_by_id = {
        str(case.get("case_id", "")).strip(): case
        for case in architecture_scenarios
        if isinstance(case, dict)
    }

    assert len(scenarios) >= 33
    assert len(architecture_scenarios) >= 4
    assert {
        "install_upgrade_runtime",
        "release_publication",
        "browser_surface_reliability",
        "daemon_security",
        "component_governance",
        "compass_brief_freshness",
        "agent_activation",
        "cross_surface_governance_sync",
        "cli_contract_regression",
        "consumer_profile_compatibility",
        "runtime_state_integrity",
    }.issubset(families)
    assert {
        "consumer-install-upgrade-runtime-contract",
        "managed-runtime-repair-and-rollback-contract",
        "release-benchmark-publication-proof",
        "shell-and-compass-browser-reliability",
        "tooling-dashboard-onboarding-browser-contract",
        "context-engine-daemon-security-hardening",
        "benchmark-component-governance-truth",
        "compass-brief-freshness-and-reactivity",
        "install-time-agent-activation-contract",
        "cli-install-first-run-onboarding-contract",
        "consumer-profile-truth-root-compatibility",
        "product-runtime-state-js-companion-contract",
        "cross-surface-governance-sync-truth",
        "benchmark-raw-baseline-publication-contract",
        "benchmark-raw-baseline-runner-gate",
        "benchmark-docs-and-readme-closeout",
        "benchmark-corpus-expansion-mirror-integrity",
    }.issubset(scenario_ids)
    assert {
        "architecture-release-install-runtime-boundary",
        "architecture-benchmark-proof-publication-lane",
        "architecture-benchmark-honest-baseline-contract",
    }.issubset(architecture_ids)
    release_boundary_required_paths = [
        str(token).strip()
        for token in architecture_by_id["architecture-release-install-runtime-boundary"].get("benchmark", {}).get("required_paths", [])
        if str(token).strip()
    ]
    assert "odylith/registry/source/components/odylith/CURRENT_SPEC.md" in release_boundary_required_paths
    assert "odylith/registry/source/components/odylith-chatter/CURRENT_SPEC.md" not in release_boundary_required_paths


def test_benchmark_corpus_keeps_final_only_odylith_assist_closeout_contract() -> None:
    corpus = _load(PUBLIC_CORPUS)
    program = dict(corpus.get("program", {}))
    contract = dict(program.get("closeout_contract", {}))

    assert contract.get("odylith_brand_note") == "final_only_evidence_backed"
    assert contract.get("allowed_label") == "Odylith assist:"
    assert contract.get("preferred_markdown_label") == "**Odylith assist:**"
    assert contract.get("benchmark_tax_policy") == "metadata_only"
    rules = [str(item).strip() for item in contract.get("rules", []) if str(item).strip()]

    assert len(rules) >= 8
    assert any("mid-task narration task-first" in rule for rule in rules)
    assert any("at most one short Odylith assist line" in rule for rule in rules)
    assert any("bold Markdown label" in rule for rule in rules)
    assert any("Lead with the user win" in rule for rule in rules)
    assert any("broader unguided path" in rule for rule in rules)
    assert any("soulful, friendly, authentic, and factual" in rule for rule in rules)
    assert any("observed counts, measured deltas, or validation outcomes" in rule for rule in rules)
    assert any("clear user-facing delta" in rule for rule in rules)
    assert any("metadata-only" in rule and "required paths" in rule for rule in rules)


def test_benchmark_closeout_contract_does_not_add_odylith_chatter_required_paths() -> None:
    corpus = _load(PUBLIC_CORPUS)
    benchmark_scenarios = [case for case in corpus.get("scenarios", []) if isinstance(case, dict) and "benchmark" in str(case.get("case_id", ""))]

    assert benchmark_scenarios
    for case in benchmark_scenarios:
        benchmark = dict(case.get("benchmark", {}))
        required_paths = [str(token).strip() for token in benchmark.get("required_paths", []) if str(token).strip()]
        validation_commands = [str(token).strip() for token in benchmark.get("validation_commands", []) if str(token).strip()]

        assert "odylith/registry/source/components/odylith-chatter/CURRENT_SPEC.md" not in required_paths
        assert not any("odylith-chatter" in command for command in validation_commands)


def test_grounded_hot_path_expectations_allow_compact_packets_for_current_runtime() -> None:
    corpus = _load(PUBLIC_CORPUS)
    scenarios = {
        str(case.get("case_id", "")).strip(): case
        for case in corpus.get("scenarios", [])
        if isinstance(case, dict)
    }

    exact_anchor = dict(scenarios["exact-workstream-anchor-density"].get("expect", {}))
    cross_file = dict(scenarios["cross-file-feature-budget-discipline"].get("expect", {}))

    assert "compact" in exact_anchor.get("packet_state", [])
    assert "compact" in cross_file.get("packet_state", [])


def test_correctness_critical_benchmark_cases_are_validation_and_path_backed() -> None:
    corpus = _load(PUBLIC_CORPUS)
    critical_cases = [
        case
        for case in corpus.get("scenarios", [])
        if isinstance(case, dict)
        and isinstance(case.get("benchmark"), dict)
        and bool(case["benchmark"].get("correctness_critical"))
    ]

    assert critical_cases
    for case in critical_cases:
        benchmark = dict(case.get("benchmark", {}))
        required_paths = [str(token).strip() for token in benchmark.get("required_paths", []) if str(token).strip()]
        critical_paths = [str(token).strip() for token in benchmark.get("critical_paths", []) if str(token).strip()]
        validation_commands = [str(token).strip() for token in benchmark.get("validation_commands", []) if str(token).strip()]

        assert required_paths, f"{case.get('case_id')} is correctness-critical but has no required paths"
        assert critical_paths, f"{case.get('case_id')} is correctness-critical but has no critical paths"
        assert validation_commands, f"{case.get('case_id')} is correctness-critical but has no validation commands"


def test_publication_benchmark_cases_preload_narrow_focused_checks() -> None:
    corpus = _load(PUBLIC_CORPUS)
    scenarios = {
        str(case.get("case_id", "")).strip(): case
        for case in corpus.get("scenarios", [])
        if isinstance(case, dict)
    }

    proof = dict(scenarios["release-benchmark-publication-proof"].get("benchmark", {}))
    raw = dict(scenarios["benchmark-raw-baseline-publication-contract"].get("benchmark", {}))

    proof_checks = [str(token).strip() for token in proof.get("focused_local_checks", []) if str(token).strip()]
    raw_checks = [str(token).strip() for token in raw.get("focused_local_checks", []) if str(token).strip()]

    assert proof_checks == [proof["validation_commands"][1]]
    assert raw_checks == [raw["validation_commands"][0]]
