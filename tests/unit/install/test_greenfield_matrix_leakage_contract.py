from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_ROOT = REPO_ROOT / "scripts" / "release"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import greenfield_matrix_leakage as leakage
import greenfield_matrix_quality_scoring as quality_scoring
import greenfield_preconfirm_matrix as matrix
from greenfield_matrix_corpus_provenance import GreenfieldCaseProvenance
from greenfield_preconfirm_matrix_cases import GreenfieldMatrixCase


def _case(*, tags: tuple[str, ...] = ()) -> GreenfieldMatrixCase:
    excerpt = (
        "AI agent skill that researches any topic across Reddit and the web, "
        "then synthesizes a grounded summary"
    )
    return GreenfieldMatrixCase(
        name="source-backed research product",
        prompt=(
            "Create a research product. Source repository: sample/research-skill. "
            f"Repository description: {excerpt}"
        ),
        required_terms=("research",),
        leakage_terms=("sample/research-skill",),
        tags=tags,
        provenance=GreenfieldCaseProvenance(
            corpus_tier="source_provenanced",
            source_excerpt=excerpt,
        ),
    )


def test_complete_product_path_allows_authoritative_source_text() -> None:
    case = _case(tags=("source-evidence-complete-product-path",))

    assert matrix._source_evidence_content_custody_issues(
        case=case,
        generated_text=case.provenance.source_excerpt,
    ) == ()


def test_background_source_text_copy_remains_rejected() -> None:
    case = _case()

    assert matrix._source_evidence_content_custody_issues(
        case=case,
        generated_text=case.provenance.source_excerpt,
    ) == ("source evidence text leaked into product artifacts",)


def test_complete_product_path_does_not_allow_source_identifier_copy() -> None:
    case = _case(tags=("source-evidence-complete-product-path",))

    assert leakage.source_evidence_custody_issues(
        case=case,
        generated_text="Build sample/research-skill into the product surface.",
    ) == (
        "source evidence identifier leaked into product artifacts: `sample/research-skill`",
    )


def test_platform_baseline_uses_generated_candidate_vocabulary(monkeypatch) -> None:
    case = _case(tags=("source-evidence-complete-product-path",))
    observed_terms: tuple[str, ...] = ()

    def scan_platform_custody(*, repo_root, dist_dir, terms):
        nonlocal observed_terms
        observed_terms = terms
        return (SimpleNamespace(term="grounded summary"),)

    monkeypatch.setattr(
        leakage.platform_domain_leakage,
        "scan_platform_custody",
        scan_platform_custody,
    )

    baseline = leakage.platform_baseline_required_terms(
        repo_root=REPO_ROOT,
        release_dir=REPO_ROOT,
        cases=(case,),
    )

    assert "grounded summary" in observed_terms
    assert baseline == ("grounded summary",)


def test_external_quality_failure_does_not_claim_readback_drift(monkeypatch) -> None:
    monkeypatch.setattr(quality_scoring, "write_committed", lambda _manifest: True)

    explanation = quality_scoring._score_explanation(
        score=0,
        scores={},
        counts=None,
        rendered_issues=(),
        prompt_issues=(),
        manifest={},
        create_returncode=0,
        lenses={},
        external_issues=("platform leakage contract failed",),
    )

    assert explanation == (
        "score forced to 0 because an external release-quality contract failed",
    )
