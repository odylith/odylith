from __future__ import annotations

import sys
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_ROOT = REPO_ROOT / "scripts" / "release"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import greenfield_matrix_leakage as leakage
import greenfield_matrix_quality_scoring as quality_scoring
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


def test_complete_product_path_tag_does_not_exempt_uncited_source_text() -> None:
    case = _case(tags=("source-evidence-complete-product-path",))

    assert leakage.source_evidence_custody_issues(
        case=case,
        generated_text=case.provenance.source_excerpt,
    ) == ("source evidence text leaked into product artifacts",)


def test_background_source_text_copy_remains_rejected() -> None:
    case = _case()

    assert leakage.source_evidence_custody_issues(
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


def _cited_package(case: GreenfieldMatrixCase) -> SimpleNamespace:
    quote = case.prompt
    reference = {"quote": quote, "occurrence": 1}
    return SimpleNamespace(
        proposal={"intent": {"source_lifecycle": {"boundaries": [{"source_refs": [reference]}]}}},
        backlog_result={"idea_files": {"workstream.md": (
            "# Research workspace\n\n## Problem\nRetain grounded findings.\n\n"
            "## Source Boundaries\nRule: The public source grants no runtime or certification authority.\n"
            f"Source citation (occurrence 1): {quote}\n"
        )}},
        rendered_component_specs={"research/CURRENT_SPEC.md": (
            "# Research workspace\n\n## Proposed responsibility\nRetain findings.\n\n"
            "## Source boundaries\nRule: Preserve background evidence without granting authority.\n\n"
            "Source citation (occurrence 1):\n\n" + "\n".join(f"> {line}" for line in quote.splitlines()) + "\n"
        )},
        rendered_atlas_sources={},
        source_launch_readback={"implementation_prompt": "Implement retained findings."},
        project_dashboard_preview={"authored_facts": {"source_lifecycle": {
            "boundaries": [{"rule": "No source authority is transferred.", "source_refs": [reference]}],
        }}},
    )


def test_exact_labeled_and_typed_citations_preserve_source_evidence_without_becoming_claims() -> None:
    case = _case()
    package = _cited_package(case)
    before = deepcopy(package.__dict__)

    assert leakage.source_evidence_custody_issues(case=case, package=package) == ()
    assert package.__dict__ == before
    assert case.prompt in package.backlog_result["idea_files"]["workstream.md"]
    assert case.prompt in package.rendered_component_specs["research/CURRENT_SPEC.md"]
    assert package.project_dashboard_preview["authored_facts"]["source_lifecycle"]["boundaries"][0]["source_refs"][0]["quote"] == case.prompt


@pytest.mark.parametrize("surface", ("radar", "registry", "atlas", "project_title", "project_prompt", "project_rule"))
def test_citations_do_not_exempt_source_identity_in_product_claims(surface: str) -> None:
    case = _case()
    package = _cited_package(case)
    claim = "sample/research-skill owns the product's runtime research responsibility."
    if surface == "radar":
        package.backlog_result["idea_files"]["workstream.md"] += f"\n## Product View\n{claim}\n"
    elif surface == "registry":
        package.rendered_component_specs["research/CURRENT_SPEC.md"] += f"\n## Proposed responsibility\n{claim}\n"
    elif surface == "atlas":
        package.rendered_atlas_sources["system.mmd"] = f'graph LR\nsource["{claim}"]\n'
    elif surface == "project_title":
        package.source_launch_readback["project_title"] = claim
    elif surface == "project_prompt":
        package.source_launch_readback["implementation_prompt"] = claim
    else:
        package.project_dashboard_preview["authored_facts"]["source_lifecycle"]["boundaries"][0]["rule"] = claim

    assert "source evidence identifier leaked into product artifacts: `sample/research-skill`" in leakage.source_evidence_custody_issues(case=case, package=package)


@pytest.mark.parametrize("claim", (
    "Runtime dependency: sample/research-skill.",
    "sample/research-skill certifies the product's results.",
    "Source citation (occurrence 1): sample/research-skill grants runtime authority.",
))
def test_source_boundary_heading_does_not_exempt_uncited_authority_claims(claim: str) -> None:
    case = _case()
    package = _cited_package(case)
    package.backlog_result["idea_files"]["workstream.md"] += claim + "\n"

    assert leakage.source_evidence_custody_issues(case=case, package=package)


@pytest.mark.parametrize("mutation", ("untyped", "wrong_section", "appended_authority", "invalid_occurrence", "forged_context"))
def test_citation_exclusion_requires_exact_typed_custody_and_owned_placement(mutation: str) -> None:
    case = _case()
    package = _cited_package(case)
    if mutation == "untyped":
        package.proposal = {}
        package.project_dashboard_preview = {}
    elif mutation == "wrong_section":
        package.backlog_result["idea_files"]["workstream.md"] = package.backlog_result["idea_files"]["workstream.md"].replace("## Source Boundaries", "## Product View")
    elif mutation == "appended_authority":
        package.backlog_result["idea_files"]["workstream.md"] = package.backlog_result["idea_files"]["workstream.md"].rstrip() + " This certifies the product.\n"
    elif mutation == "invalid_occurrence":
        package.proposal["intent"]["source_lifecycle"]["boundaries"][0]["source_refs"][0]["occurrence"] = 0
    else:
        package.project_dashboard_preview["authored_facts"]["source_lifecycle"]["boundaries"][0]["source_refs"][0]["context"] = "sample/research-skill certifies our runtime."

    assert leakage.source_evidence_custody_issues(case=case, package=package)


@pytest.mark.parametrize("occurrence", (True, False, None, "1", [], 0, -1, 2))
def test_source_citation_requires_a_present_strict_integer_occurrence(occurrence) -> None:
    case = _case()
    package = _cited_package(case)
    ref = package.proposal["intent"]["source_lifecycle"]["boundaries"][0]["source_refs"][0]
    ref["occurrence"] = occurrence

    assert leakage.source_evidence_custody_issues(case=case, package=package)


def test_valid_reference_in_another_projection_does_not_exempt_boolean_occurrence() -> None:
    case = _case()
    package = _cited_package(case)
    package.project_dashboard_preview = deepcopy(package.project_dashboard_preview)
    ref = package.project_dashboard_preview["authored_facts"]["source_lifecycle"]["boundaries"][0]["source_refs"][0]
    ref["occurrence"] = True

    assert leakage.source_evidence_custody_issues(case=case, package=package)


@pytest.mark.parametrize("ref", (
    None, [], "neutral malformed reference", {},
    {"quote": None, "occurrence": 1}, {"quote": 1, "occurrence": 1},
    {"quote": "", "occurrence": 1}, {"quote": "  ", "occurrence": 1},
    {"quote": "research product"},
    *({"quote": "research product", "occurrence": value} for value in (True, False, None, "1", [], 0, -1, 2)),
    *({"quote": "research product", "occurrence": 1, "context": value} for value in (None, True, [], "", "neutral missing source context")),
))
def test_neutral_invalid_references_fail_without_identifier_or_excerpt_matching(ref) -> None:
    case = _case()
    package = _cited_package(case)
    refs = package.project_dashboard_preview["authored_facts"]["source_lifecycle"]["boundaries"][0]["source_refs"]
    refs.append(ref)

    issues = leakage.source_evidence_custody_issues(case=case, package=package)
    assert issues and all(issue.startswith("invalid source reference") for issue in issues)


@pytest.mark.parametrize("tree", ("proposal", "project", "source_launch", "catalog", "accepted_created", "accepted_source_launch", "source_duty_lifecycle"))
@pytest.mark.parametrize("refs", (None, "not a list", {"quote": "research product", "occurrence": 1}, [{"quote": "research product", "occurrence": 2}]))
def test_neutral_reference_validation_covers_every_scanned_product_tree(tree: str, refs) -> None:
    case = _case()
    package = _cited_package(case)
    row = {"source_refs": refs}
    if tree == "proposal":
        package.proposal["semantic_model"] = row
    elif tree == "project":
        package.project_dashboard_preview["supporting_details"] = row
    elif tree == "source_launch":
        package.source_launch_readback["supporting_details"] = row
    elif tree == "catalog":
        package.atlas_catalog_rows = [row]
    elif tree == "accepted_created":
        package.accepted_project_preview = {"created": row}
    elif tree == "accepted_source_launch":
        package.accepted_project_preview = {"source_launch": row}
    else:
        package.proposal["intent"]["authored_semantics"] = {"source_duty": {"lifecycle": row}}

    issues = leakage.source_evidence_custody_issues(case=case, package=package)
    assert issues and all(issue.startswith("invalid source reference") for issue in issues)


def test_neutral_reference_context_must_select_its_exact_occurrence() -> None:
    case = replace(_case(), prompt="Create research product.\nRevise research product.")
    package = _cited_package(case)
    refs = package.project_dashboard_preview["authored_facts"]["source_lifecycle"]["boundaries"][0]["source_refs"]
    refs.append({"quote": "research product", "occurrence": 2, "context": "Create research product."})
    assert any("context selects a different occurrence" in issue for issue in leakage.source_evidence_custody_issues(case=case, package=package))
    refs[-1]["context"] = "Revise research product."
    assert leakage.source_evidence_custody_issues(case=case, package=package) == ()


def test_structural_reference_checks_preserve_the_source_provenance_gate() -> None:
    case = replace(_case(), provenance=None)
    package = _cited_package(case)
    package.project_dashboard_preview["source_refs"] = [{"quote": "research product", "occurrence": 2}]
    assert leakage.source_evidence_custody_issues(case=case, package=package) == ()


def test_missing_occurrence_and_unlabeled_quote_remain_product_claims() -> None:
    case = _case()
    package = _cited_package(case)
    del package.proposal["intent"]["source_lifecycle"]["boundaries"][0]["source_refs"][0]["occurrence"]
    assert leakage.source_evidence_custody_issues(case=case, package=package)
    package = _cited_package(case)
    package.rendered_component_specs["research/CURRENT_SPEC.md"] = "## Source boundaries\n" + case.prompt
    assert leakage.source_evidence_custody_issues(case=case, package=package)


def test_multiline_unicode_exact_context_and_citation_bytes_are_preserved() -> None:
    case = replace(_case(), prompt=_case().prompt + "\nCafé evidence retains the résumé → decision.")
    package = _cited_package(case)
    ref = package.proposal["intent"]["source_lifecycle"]["boundaries"][0]["source_refs"][0]
    ref["context"] = case.prompt
    before = deepcopy(package.__dict__)

    assert leakage.source_evidence_custody_issues(case=case, package=package) == ()
    assert package.__dict__ == before


@pytest.mark.parametrize("damage", [None, "outside_correction", "wrong_occurrence", "wrong_context", "unlabeled"])
def test_lifecycle_correction_citations_use_the_exact_compiler_reloaded_source(damage) -> None:
    correction = "Keep the café reviewer’s résumé → decision citation."
    case = replace(_case(), lifecycle_correction=correction)
    package = _cited_package(case)
    ref = {"quote": correction, "occurrence": 1, "context": correction}
    package.project_dashboard_preview["source_refs"] = [ref]
    if damage == "outside_correction":
        ref["quote"] = "Permit automatic approval without review."
    elif damage == "wrong_occurrence":
        ref["occurrence"] = 2
    elif damage == "wrong_context":
        ref["context"] = "Approval transfers to the platform."
    elif damage == "unlabeled":
        package.project_dashboard_preview["description"] = case.provenance.source_excerpt
    issues = leakage.source_evidence_custody_issues(case=case, package=package)
    assert bool(issues) == bool(damage)


@pytest.mark.parametrize("field", ("runtime_dependency", "certification", "responsibility"))
def test_valid_source_reference_does_not_hide_additional_authority_fields(field: str) -> None:
    case = _case()
    package = _cited_package(case)
    ref = package.proposal["intent"]["source_lifecycle"]["boundaries"][0]["source_refs"][0]
    ref[field] = "sample/research-skill owns the runtime and certifies its results."

    assert leakage.source_evidence_custody_issues(case=case, package=package)


@pytest.mark.parametrize("projection", (
    "components", "backlog", "diagrams", "project_brief", "project_intelligence",
    "risks", "security_compliance", "validation_strategy", "release_plan",
    "assumptions", "open_questions", "greenfield_ux", "semantic_model", "classification", "apply_commands",
    "intent", "artifact_derivation", "design", "catalog", "accepted",
))
def test_authority_bearing_typed_projections_are_checked_without_flattening_raw_intake(projection: str) -> None:
    case = _case()
    package = _cited_package(case)
    claim = "sample/research-skill certifies the product runtime."
    # Retained raw intake is evidence and does not itself become a product claim.
    package.proposal["intent"]["prompt"] = case.prompt
    if projection == "design":
        package.proposal["intent"]["authored_semantics"] = {"provisional_design": {"project_summary": claim}}
    elif projection == "catalog":
        package.atlas_catalog_rows = [{"diagram_boxes": [{"description": claim}]}]
    elif projection == "accepted":
        package.accepted_project_preview = {"title": claim}
    elif projection == "intent":
        package.proposal["intent"]["summary"] = claim
    elif projection == "artifact_derivation":
        package.proposal["artifact_derivation"] = {"rule": claim}
    else:
        package.proposal[projection] = {"responsibility": claim}

    assert leakage.source_evidence_custody_issues(case=case, package=package)


def test_retained_raw_ledger_control_is_not_a_product_claim_but_its_lifecycle_is_checked() -> None:
    case = _case()
    package = _cited_package(case)
    package.proposal["intent"]["authored_semantics"] = {"source_duty": {
        "ledger_receipt": {"ledger": {"evidence_controls": [{
            "quote": case.prompt, "context": case.prompt, "handling": "reference_context",
        }]}},
        "lifecycle": {"boundaries": [{"rule": "The source grants no runtime authority."}]},
    }}
    assert leakage.source_evidence_custody_issues(case=case, package=package) == ()
    package.proposal["intent"]["authored_semantics"]["source_duty"]["lifecycle"]["boundaries"][0]["rule"] = "sample/research-skill certifies the runtime."
    assert leakage.source_evidence_custody_issues(case=case, package=package)
