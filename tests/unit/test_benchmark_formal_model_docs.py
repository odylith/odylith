from __future__ import annotations

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
FORMAL_MODEL = REPO_ROOT / "docs" / "research" / "BENCHMARK_FORMAL_MODEL.md"
LEGACY_FORMAL_MODEL = REPO_ROOT / "docs" / "benchmarks" / "BENCHMARK_FORMAL_MODEL.md"
OLD_FORMAL_MODEL_PATH = "docs/benchmarks/BENCHMARK_FORMAL_MODEL.md"
LINK_SOURCE_PATHS = (
    REPO_ROOT / "README.md",
    REPO_ROOT / "docs" / "benchmarks" / "README.md",
    REPO_ROOT / "docs" / "research" / "README.md",
    REPO_ROOT / "odylith" / "runtime" / "source" / "release-notes" / "v0.1.14.md",
)
EXPECTED_LINK_TARGETS = {
    REPO_ROOT / "README.md": "docs/research/BENCHMARK_FORMAL_MODEL.md",
    REPO_ROOT / "docs" / "benchmarks" / "README.md": "../research/BENCHMARK_FORMAL_MODEL.md",
    REPO_ROOT / "docs" / "research" / "README.md": "BENCHMARK_FORMAL_MODEL.md",
    REPO_ROOT
    / "odylith"
    / "runtime"
    / "source"
    / "release-notes"
    / "v0.1.14.md": "../../../../docs/research/BENCHMARK_FORMAL_MODEL.md",
}
GITHUB_FRAGILE_MATH_MARKERS = (
    "$$",
    "\\(",
    "\\)",
    "\\[",
    "\\]",
    "\\operatorname",
    "\\mathrm",
    "\\mathbb",
    "\\mathcal",
    "\\Delta",
)
EXPECTED_SECTIONS = (
    "## Scope",
    "## Rendering Contract",
    "## Core Entities",
    "## Product Turn Gate Contract",
    "## Decision Vocabulary",
    "## Early-Exit Proof Contract",
    "## Scenario Model",
    "## Matched-Lane Fairness",
    "## Utility Interpretation",
    "## Generalization Claim",
    "## Public Report Validity",
    "## Migration Interpretation",
    "## Invalid Row Conditions",
    "## Operational Reading",
)
REQUIRED_REPORT_FIELDS = (
    "turn_gate_decision",
    "turn_gate_receipt",
    "turn_gate_product_path_present",
    "execution_capsule",
    "tool_gate_summary",
    "stop_gate_summary",
    "status_basis",
    "validator_execution_mode",
    "validator_status_basis",
    "preflight_evidence_mode",
    "preflight_evidence_result_status",
    "candidate_write_paths",
    "workspace_delta_paths",
    "fairness_findings",
)
DURABLE_UNDERSCORE_TOKENS = (
    "answer_only",
    "early_exit_proof",
    "bounded_edit",
    "open_ended_implementation",
    "unsafe_needs_user_decision",
    "product_turn_gate",
    "turn_gate_early_exit_proof",
    "turn_gate_product_path_present",
    "candidate_write_paths",
    "workspace_delta_paths",
    "validator_execution_mode",
)


def test_benchmark_formal_model_uses_github_safe_plain_markdown() -> None:
    markdown = FORMAL_MODEL.read_text(encoding="utf-8")

    for marker in GITHUB_FRAGILE_MATH_MARKERS:
        assert marker not in markdown
    assert not re.search(r"\\[A-Za-z]+", markdown)
    assert "```text" in markdown


def test_benchmark_formal_model_exposes_public_interpretation_contract() -> None:
    markdown = FORMAL_MODEL.read_text(encoding="utf-8")

    for heading in EXPECTED_SECTIONS:
        assert heading in markdown
    for field in REQUIRED_REPORT_FIELDS:
        assert field in markdown
    for token in DURABLE_UNDERSCORE_TOKENS:
        assert token in markdown


def test_benchmark_formal_model_links_point_to_research_folder() -> None:
    assert FORMAL_MODEL.exists()
    legacy_text = LEGACY_FORMAL_MODEL.read_text(encoding="utf-8")
    assert "../research/BENCHMARK_FORMAL_MODEL.md" in legacy_text
    assert "## Decision Classes" not in legacy_text

    for path in LINK_SOURCE_PATHS:
        text = path.read_text(encoding="utf-8")
        assert OLD_FORMAL_MODEL_PATH not in text
        assert EXPECTED_LINK_TARGETS[path] in text
