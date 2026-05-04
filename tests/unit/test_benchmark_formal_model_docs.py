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


def _math_regions(markdown: str) -> list[str]:
    regions: list[str] = []
    for pattern in (r"\$\$(.*?)\$\$", r"\\\[(.*?)\\\]", r"\\\((.*?)\\\)"):
        regions.extend(match.group(1) for match in re.finditer(pattern, markdown, flags=re.DOTALL))
    return regions


def test_benchmark_formal_model_keeps_durable_tokens_out_of_latex_math() -> None:
    markdown = FORMAL_MODEL.read_text(encoding="utf-8")
    math_text = "\n".join(_math_regions(markdown))

    for token in DURABLE_UNDERSCORE_TOKENS:
        assert token not in math_text
    for command, body in re.findall(r"\\(mathrm|operatorname|text|mathbf)\{([^}]*)\}", math_text):
        assert "_" not in body, f"GitHub math may parse `{command}{{{body}}}` as nested subscripts"


def test_benchmark_formal_model_links_point_to_research_folder() -> None:
    assert FORMAL_MODEL.exists()
    legacy_text = LEGACY_FORMAL_MODEL.read_text(encoding="utf-8")
    assert "../research/BENCHMARK_FORMAL_MODEL.md" in legacy_text
    assert "## Decision Classes" not in legacy_text

    for path in LINK_SOURCE_PATHS:
        text = path.read_text(encoding="utf-8")
        assert OLD_FORMAL_MODEL_PATH not in text
        assert EXPECTED_LINK_TARGETS[path] in text
