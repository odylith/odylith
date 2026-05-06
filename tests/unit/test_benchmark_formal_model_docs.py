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
GITHUB_FRAGILE_MATH_DELIMITERS = (
    "$$",
    "\\(",
    "\\)",
    "\\[",
    "\\]",
)
BLOCKED_LATEX_MACROS = (
    "\\operatorname",
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


def _math_fence_regions(markdown: str) -> list[str]:
    return re.findall(r"```math\n(.*?)\n```", markdown, flags=re.DOTALL)


def test_benchmark_formal_model_uses_github_safe_latex_math() -> None:
    markdown = FORMAL_MODEL.read_text(encoding="utf-8")
    math_text = "\n".join(_math_fence_regions(markdown))

    for marker in GITHUB_FRAGILE_MATH_DELIMITERS:
        assert marker not in markdown
    for macro in BLOCKED_LATEX_MACROS:
        assert macro not in math_text
    for token in DURABLE_UNDERSCORE_TOKENS:
        assert token not in math_text
    assert len(_math_fence_regions(markdown)) >= 10
    assert "\\Delta Q" in math_text
    assert "\\mathbb{E}" in math_text
    assert "\\mathrm{" in math_text
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
