from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from odylith.runtime.domain_intelligence import greenfield_proposals
from odylith.runtime.domain_intelligence.greenfield_quality_gate import _meaningful_terms
from odylith.runtime.domain_intelligence.greenfield_quality_gate import _path_needs_events
from odylith.runtime.domain_intelligence.greenfield_quality_gate import greenfield_quality_issues
from tests.unit.runtime.greenfield_proposal_fixtures import _confirmed_intent
from tests.unit.runtime.greenfield_proposal_fixtures import _host_reasoned_ecommerce_proposal
from tests.unit.runtime.greenfield_proposal_fixtures import _write_confirmed_intent


PRODUCT_INTENTS = [
    "draft a greenfield proposal for a city zoning permit review app",
    "draft a greenfield proposal for a food safety recall traceability system",
    "draft a greenfield proposal for a plant-care irrigation device that waters and monitors houseplants",
    "draft a greenfield proposal for a quantum chemistry catalyst screening platform",
]

CONFIRMED_PRODUCT_INTENTS = [
    "draft a greenfield proposal for a city zoning permit review app",
    "draft a greenfield proposal for a municipal permit review workspace",
]

@pytest.mark.parametrize("prompt", CONFIRMED_PRODUCT_INTENTS)
def test_confirmed_greenfield_proposal_is_apply_ready_without_domain_profiles(tmp_path: Path, prompt: str) -> None:
    request = greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt=prompt,
        confirmed_intent=_confirmed_intent(),
    )

    greenfield_proposals.validate_host_reasoned_proposal(request)
    assert request["mode"] == "host_reasoned_greenfield_proposal"
    assert request["schema_version"] == "odylith.greenfield.proposal.v1"
    assert request["provider_calls"] == 0
    assert "reasoning_contract" not in request
    assert "host_instruction" not in request
    assert len(request["backlog"]) >= 4
    assert len(request["components"]) >= 3
    assert len(request["diagrams"]) >= 3
    assert request["project_intelligence"]["intent"]
    assert request["project_brief"]["blueprint_sections"]
    assert "Product Model" not in json.dumps(request)
    assert "Operator Workspace" not in json.dumps(request)


@pytest.mark.parametrize("prompt", PRODUCT_INTENTS)
def test_product_intent_confirmation_requests_sectioned_host_reasoning_without_records(
    tmp_path: Path, capsys, prompt: str
) -> None:
    rc = greenfield_proposals.main(["propose", "--repo-root", str(tmp_path), "--prompt", prompt])
    output = capsys.readouterr().out

    assert rc == 0
    assert "Product Intent Confirmation" in output
    assert "Product story" in output
    assert "State object" in output
    assert "First complete path" in output
    assert "Human actors" in output
    assert "External systems" in output
    assert "Internal product systems" in output
    assert "Proof boundary" in output
    assert "**Choose one command**" in output
    assert "- **CONFIRM** - Accept this interpretation." in output
    assert "- **EDIT** - Reply with corrections." in output
    assert "- **REJECT** - Stop here." in output
    assert "Host reasoning task" not in output
    assert "Visible format contract" not in output
    assert "No files changed" not in output
    assert "Registry" not in output
    assert "Atlas" not in output
    assert "Primary user" not in output
    assert "Project operator" not in output
    assert "Evidence owner" not in output


def test_greenfield_title_strips_operator_directives(tmp_path: Path) -> None:
    request = greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt=(
            "Draft a product-first greenfield proposal for a municipal permit review workspace. "
            "Show the interpretation and direction choices first. Do not write records until I confirm."
        ),
        confirmed_intent=_confirmed_intent(),
    )

    assert request["intent"]["title"] == "Municipal Permit Review Workspace"
    assert "Show The Interpretation" not in request["intent"]["title"]
    assert "Do Not Write" not in request["intent"]["title"]


def test_confirm_intent_returns_apply_ready_governance(tmp_path: Path, capsys) -> None:
    _write_confirmed_intent(tmp_path)
    rc = greenfield_proposals.main(
        [
            "propose",
            "--repo-root",
            str(tmp_path),
            "--prompt",
            "draft a greenfield proposal for a municipal permit review workspace",
            "--intent-file",
            ".odylith/runtime/greenfield/confirmed-intent.md",
            "--confirm-intent",
            "--format",
            "json",
        ],
    )
    output = capsys.readouterr().out
    request = json.loads(output)

    assert rc == 0
    assert request["mode"] == "host_reasoned_greenfield_proposal"
    assert "reasoning_contract" not in request
    assert len(request["backlog"]) >= 4
    assert len(request["components"]) >= 3
    assert len(request["diagrams"]) >= 3


def test_quality_gate_rejects_profile_scaffold_and_generic_persona_leaks() -> None:
    proposal = _host_reasoned_ecommerce_proposal()
    proposal["backlog"][1]["problem"] = "Project intelligence renderer should create generic product truth."
    proposal["backlog"][1]["domain_intelligence"]["actors"] = [
        "Primary user: generic placeholder.",
        "Project operator: generic placeholder.",
        "Evidence owner: generic placeholder.",
    ]
    proposal["components"][0]["label"] = "Operator Workspace"
    proposal["diagrams"][0]["summary"] = "Generated from GreenfieldDomainProfile and proposal_template."

    issues = greenfield_quality_issues(proposal)

    assert any("Project intelligence renderer" in issue for issue in issues)
    assert any("Primary user" in issue for issue in issues)
    assert any("Operator Workspace" in issue for issue in issues)
    assert any("GreenfieldDomainProfile" in issue for issue in issues)


def test_quality_gate_rejects_operator_directives_and_governance_prep_language() -> None:
    proposal = _host_reasoned_ecommerce_proposal()
    proposal["backlog"][0]["problem"] = (
        "Commerce Launch System needs an accepted execution spine before source exists, otherwise work will trace "
        "to product intent, components, diagrams, release gates, or validation proof."
    )
    proposal["backlog"][1]["product_view"] = "Show the interpretation and do not write records until I confirm."

    issues = greenfield_quality_issues(proposal)

    assert any("governance-prep phrase" in issue for issue in issues)
    assert any("operator instruction" in issue for issue in issues)


def test_quality_gate_rejects_mechanical_greenfield_scaffold_language() -> None:
    proposal = _host_reasoned_ecommerce_proposal()
    proposal["intent"]["prompt"] = "Draft a greenfield proposal for a community archive"
    proposal["intent"]["title"] = "Community Archive"
    proposal["project_brief"]["purpose"] = (
        "Release 0.0.1 proves the accepted first workflow, then replays the community archive state record "
        "and evidence packet."
    )
    proposal["backlog"][0]["problem"] = (
        "Start with the community archive first workflow, then replay community archive record and review "
        "community archive evidence packet."
    )
    proposal["backlog"][0]["customer"] = "Community Archive workflow lead and beneficiary."
    proposal["diagrams"][0]["components"][0]["description"] = (
        "Archivist is part of the path; incoming arrows show what must be true before it runs, and outgoing "
        "arrows show what it enables next."
    )

    issues = greenfield_quality_issues(proposal)

    assert any("generic first workflow" in issue for issue in issues)
    assert not any("evidence packet scaffold" in issue for issue in issues)
    assert any("workflow lead" in issue for issue in issues)
    assert any("diagram mechanics" in issue for issue in issues)


def test_quality_gate_allows_domain_specific_hyphenated_workflow_phrases() -> None:
    proposal = _host_reasoned_ecommerce_proposal()
    proposal["open_questions"][0] = (
        "Whether responders need a mobile-first workflow in the first release."
    )

    issues = greenfield_quality_issues(proposal)

    assert not any("generic first workflow" in issue for issue in issues)


def test_quality_gate_allows_domain_specific_actor_names_but_rejects_placeholders() -> None:
    proposal = _host_reasoned_ecommerce_proposal()
    proposal["backlog"][1]["domain_intelligence"]["actors"] = [
        "Plant operator reviews the care plan before the watering device changes any plant schedule.",
        "Operator: generic placeholder that does not explain the project role.",
    ]

    issues = greenfield_quality_issues(proposal)

    assert not any("Plant operator" in issue for issue in issues)
    assert any("generic actor label `Operator`" in issue for issue in issues)

    noun_phrase = _host_reasoned_ecommerce_proposal()
    noun_phrase["assumptions"] = [
        {"id": "ASM-001", "statement": "Reviewer notes are visible only to authorized staff."}
    ]
    assert not any("generic actor label `Reviewer`" in issue for issue in greenfield_quality_issues(noun_phrase))

    placeholder = _host_reasoned_ecommerce_proposal()
    placeholder["assumptions"] = [
        {"id": "ASM-001", "statement": "Reviewer records status without a project-specific role."}
    ]
    assert any("generic actor label `Reviewer`" in issue for issue in greenfield_quality_issues(placeholder))

    for label, action in (
        ("Reviewer", "handles final approval"),
        ("Operator", "coordinates escalations"),
        ("Maintainer", "triages drift"),
        ("Reviewer", "manages release exceptions"),
    ):
        generic_action = _host_reasoned_ecommerce_proposal()
        generic_action["assumptions"] = [
            {"id": "ASM-001", "statement": f"{label} {action} without a project-specific role."}
        ]
        assert any(f"generic actor label `{label}`" in issue for issue in greenfield_quality_issues(generic_action))

    domain_specific = _host_reasoned_ecommerce_proposal()
    domain_specific["assumptions"] = [
        {"id": "ASM-001", "statement": "Safety reviewer handles release exceptions for hazardous runs."}
    ]
    assert not any("generic actor label `Reviewer`" in issue for issue in greenfield_quality_issues(domain_specific))


def test_quality_gate_meaningful_terms_use_shared_domain_index() -> None:
    source_root = (
        Path(__file__).resolve().parents[3]
        / "src"
        / "odylith"
        / "runtime"
        / "domain_intelligence"
    )
    gate_source = (source_root / "greenfield_quality_gate.py").read_text(encoding="utf-8")
    term_index_source = (source_root / "greenfield_domain_term_index.py").read_text(encoding="utf-8")

    assert "greenfield_domain_term_index import ordered_terms" in gate_source
    assert "greenfield_text import progression_marker_count" in gate_source
    assert "normalize_domain_token" not in gate_source
    assert "for raw in re.findall" not in gate_source
    assert 'len(re.findall(r"\\b(?:and|then|later)\\b|[.;]"' not in gate_source
    assert "preserve_terms" in term_index_source
    assert _path_needs_events("Open intake, then show the review result.")
    assert not _path_needs_events("Open intake once")
    assert _meaningful_terms("AI CRM statuses and UI workflows") == (
        "ai",
        "crm",
        "status",
        "ui",
        "workflow",
    )


def test_validation_rejects_missing_host_authored_rationale_lines() -> None:
    proposal = _host_reasoned_ecommerce_proposal()
    proposal["backlog"][1].pop("rationale_lines")

    with pytest.raises(ValueError, match="rationale_lines"):
        greenfield_proposals.validate_host_reasoned_proposal(proposal)


def test_project_prompt_echo_is_rejected_inside_artifact_content() -> None:
    proposal = _host_reasoned_ecommerce_proposal()
    prompt = "Build a commerce launch recovery workflow for independent merchants with order retry proof"
    proposal["intent"]["prompt"] = prompt
    proposal["backlog"][1]["problem"] = f"{prompt} needs implementation planning before the product is clear."
    proposal["components"][1]["responsibility"] = f"{prompt} component owns everything."
    proposal["diagrams"][0]["summary"] = f"{prompt} diagram summary repeats the prompt."
    proposal["release_plan"]["strategy"] = f"{prompt} release strategy repeats the prompt."

    issues = greenfield_quality_issues(proposal)

    assert any("repeats the raw prompt" in issue for issue in issues)


def test_project_prompt_echo_is_rejected_inside_project_brief_content() -> None:
    prompt = "Build a commerce launch recovery workflow for independent merchants with order retry proof"
    title = "Commerce Launch Recovery Workflow"
    for field, repeated in (
        ("purpose", prompt),
        ("project_outcome", title),
        ("operating_principle", prompt),
    ):
        proposal = _host_reasoned_ecommerce_proposal()
        proposal["intent"]["prompt"] = prompt
        proposal["intent"]["title"] = title
        proposal["project_brief"][field] = f"{repeated} is repeated instead of being authored as project language."

        issues = greenfield_quality_issues(proposal)

        assert any("repeats the raw" in issue and f"project_brief.{field}" in issue for issue in issues)


def test_runtime_source_does_not_contain_canned_greenfield_domain_families() -> None:
    source_root = Path(__file__).resolve().parents[3] / "src" / "odylith" / "runtime"
    banned = {
        "capital_merchant_lending",
        "defi_risk",
        "clinical_trial",
        "legal_intake",
        "bioinformatics",
        "GreenfieldDomainProfile",
        "infer_greenfield_domain_profile",
        "proposal_scaffold",
        "_build_apply_ready_greenfield_proposal",
    }
    allowed_paths = {
        source_root / "domain_intelligence" / "greenfield_quality_gate.py",
    }
    leaks: list[tuple[str, str]] = []
    for path in source_root.rglob("*.py"):
        if path in allowed_paths:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                for phrase in banned:
                    if phrase in node.value:
                        leaks.append((str(path.relative_to(source_root)), phrase))

    assert leaks == []
