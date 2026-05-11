from __future__ import annotations

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
INTERPRETATION_CONTRACT = (
    REPO_ROOT / "docs" / "research" / "BENCHMARK_INTERPRETATION_CONTRACT.md"
)
BENCHMARK_CONTRACT_POINTER = (
    REPO_ROOT / "docs" / "benchmarks" / "BENCHMARK_INTERPRETATION_CONTRACT.md"
)
REMOVED_CONTRACT_PATHS = (
    "docs/benchmarks/" + "BENCHMARK_" + "FORMAL_MODEL.md",
    "docs/research/" + "BENCHMARK_" + "FORMAL_MODEL.md",
)
LINK_SOURCE_PATHS = (
    REPO_ROOT / "README.md",
    REPO_ROOT / "docs" / "benchmarks" / "README.md",
    REPO_ROOT / "docs" / "research" / "README.md",
    REPO_ROOT / "odylith" / "runtime" / "source" / "release-notes" / "v0.1.14.md",
    REPO_ROOT
    / "src"
    / "odylith"
    / "bundle"
    / "assets"
    / "odylith"
    / "runtime"
    / "source"
    / "release-notes"
    / "v0.1.14.md",
)
EXPECTED_LINK_TARGETS = {
    REPO_ROOT / "README.md": "docs/research/BENCHMARK_INTERPRETATION_CONTRACT.md",
    REPO_ROOT
    / "docs"
    / "benchmarks"
    / "README.md": "../research/BENCHMARK_INTERPRETATION_CONTRACT.md",
    REPO_ROOT / "docs" / "research" / "README.md": (
        "BENCHMARK_INTERPRETATION_CONTRACT.md"
    ),
    REPO_ROOT
    / "odylith"
    / "runtime"
    / "source"
    / "release-notes"
    / "v0.1.14.md": (
        "../../../../docs/research/BENCHMARK_INTERPRETATION_CONTRACT.md"
    ),
    REPO_ROOT
    / "src"
    / "odylith"
    / "bundle"
    / "assets"
    / "odylith"
    / "runtime"
    / "source"
    / "release-notes"
    / "v0.1.14.md": (
        "../../../../docs/research/BENCHMARK_INTERPRETATION_CONTRACT.md"
    ),
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
    "## Public Report Readability",
    "## Core Entities",
    "## Product Turn Gate Contract",
    "## Decision Vocabulary",
    "## Early-Exit Proof Contract",
    "## Scenario Model",
    "## Matched-Lane Fairness",
    "## Metric Interpretation",
    "## Generalization Boundary",
    "## Evidence Boundary",
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
    "validation_results.status_basis",
    "validator_execution_mode",
    "validator_status_basis",
    "preflight_evidence_mode",
    "preflight_evidence_result_status",
    "candidate_write_paths",
    "failure_artifacts.workspace_state_post_codex",
    "fairness_findings",
    "prompt_token_delta",
    "total_payload_token_delta",
    "latency_delta_ms",
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
    "validator_execution_mode",
)


def _math_fence_regions(markdown: str) -> list[str]:
    return re.findall(r"```math\n(.*?)\n```", markdown, flags=re.DOTALL)


def test_benchmark_interpretation_contract_uses_github_safe_latex_math() -> None:
    markdown = INTERPRETATION_CONTRACT.read_text(encoding="utf-8")
    math_text = "\n".join(_math_fence_regions(markdown))

    for marker in GITHUB_FRAGILE_MATH_DELIMITERS:
        assert marker not in markdown
    for macro in BLOCKED_LATEX_MACROS:
        assert macro not in math_text
    for token in DURABLE_UNDERSCORE_TOKENS:
        assert token not in math_text
    assert len(_math_fence_regions(markdown)) >= 8
    assert "\\Delta Q" not in math_text
    assert "\\mathbb{E}" not in math_text
    assert "Q_w" not in math_text
    assert "\\kappa" not in math_text
    assert "O_s \\subseteq R_s" not in math_text
    assert "\\mathrm{" in math_text
    assert "```text" in markdown


def test_benchmark_interpretation_contract_does_not_overstate_math() -> None:
    markdown = INTERPRETATION_CONTRACT.read_text(encoding="utf-8")

    assert "benchmark validity specification" in markdown
    assert "mathematical proof of product quality" in markdown
    assert "does not claim universal product generalization" in markdown
    assert "Cost and risk terms should not be merged" in markdown
    assert "operating-policy benchmark" in markdown
    assert "core" in markdown and "product claim" in markdown
    assert "audit-friendly" in markdown
    assert "raw host CLI baseline" in markdown
    assert "model-intelligence contest" in markdown
    assert "file path and title" not in markdown
    assert "private success path" not in markdown
    assert "hidden theorem" not in markdown
    assert "latent leaderboard" not in markdown
    assert "workspace_delta_paths" not in markdown
    assert "w^\\top" not in markdown
    assert "scalar utility" not in markdown
    assert "## Generalization Claim" not in markdown
    assert "LaTeX utility form" not in markdown


def test_benchmark_interpretation_contract_exposes_public_contract() -> None:
    markdown = INTERPRETATION_CONTRACT.read_text(encoding="utf-8")

    for heading in EXPECTED_SECTIONS:
        assert heading in markdown
    for field in REQUIRED_REPORT_FIELDS:
        assert field in markdown
    for token in DURABLE_UNDERSCORE_TOKENS:
        assert token in markdown


def test_benchmark_interpretation_contract_links_use_new_filename() -> None:
    assert INTERPRETATION_CONTRACT.exists()
    assert not (
        REPO_ROOT / "docs" / "research" / ("BENCHMARK_" + "FORMAL_MODEL.md")
    ).exists()
    assert not (
        REPO_ROOT / "docs" / "benchmarks" / ("BENCHMARK_" + "FORMAL_MODEL.md")
    ).exists()
    pointer_text = BENCHMARK_CONTRACT_POINTER.read_text(encoding="utf-8")
    assert "../research/BENCHMARK_INTERPRETATION_CONTRACT.md" in pointer_text
    assert "## Decision Classes" not in pointer_text

    for path in LINK_SOURCE_PATHS:
        text = path.read_text(encoding="utf-8")
        for old_path in REMOVED_CONTRACT_PATHS:
            assert old_path not in text
        assert EXPECTED_LINK_TARGETS[path] in text
