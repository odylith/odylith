from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from odylith.runtime.domain_intelligence import greenfield_proposals
from odylith.runtime.domain_intelligence.greenfield_quality_gate import greenfield_quality_issues
from tests.unit.runtime.test_greenfield_proposals import _host_reasoned_ecommerce_proposal


PRODUCT_INTENTS = [
    "draft a greenfield proposal for a city zoning permit review app",
    "draft a greenfield proposal for a food safety recall traceability system",
    "draft a greenfield proposal for a plant-care robot that waters and monitors houseplants",
    "draft a greenfield proposal for a quantum chemistry catalyst screening platform",
]


@pytest.mark.parametrize("prompt", PRODUCT_INTENTS)
def test_greenfield_propose_is_only_a_host_reasoning_request(tmp_path: Path, prompt: str) -> None:
    request = greenfield_proposals.build_greenfield_proposal(repo_root=tmp_path, prompt=prompt)

    assert request["mode"] == "host_reasoned_proposal_request"
    assert request["schema_version"] == "odylith.greenfield.reasoning_request.v1"
    assert request["provider_calls"] == 0
    assert "reasoning_contract" in request
    assert "host_instruction" in request
    assert "backlog" not in request
    assert "components" not in request
    assert "diagrams" not in request
    assert "project_intelligence" not in request
    assert "project_brief" not in request
    assert "Product Model" not in json.dumps(request)
    assert "Operator Workspace" not in json.dumps(request)


@pytest.mark.parametrize("prompt", PRODUCT_INTENTS)
def test_product_intent_confirmation_does_not_pretend_to_reason_the_product(tmp_path: Path, capsys, prompt: str) -> None:
    rc = greenfield_proposals.main(["propose", "--repo-root", str(tmp_path), "--prompt", prompt])
    output = capsys.readouterr().out

    assert rc == 0
    assert "Product Intent Confirmation needed" in output
    assert "Host reasoning task" in output
    assert "Write in chat" in output
    assert "Do not" in output
    assert "No files changed" in output
    assert "backlog" in output
    assert "Registry" in output
    assert "Atlas" in output
    assert "Product story" not in output
    assert "Primary user" not in output
    assert "Project operator" not in output
    assert "Evidence owner" not in output


def test_confirm_intent_returns_contract_not_generated_governance(tmp_path: Path, capsys) -> None:
    rc = greenfield_proposals.main(
        [
            "propose",
            "--repo-root",
            str(tmp_path),
            "--prompt",
            "draft a greenfield proposal for a plant-care robot that waters and monitors houseplants",
            "--confirm-intent",
            "--format",
            "json",
        ],
    )
    output = capsys.readouterr().out
    request = json.loads(output)

    assert rc == 0
    assert request["mode"] == "host_reasoned_proposal_request"
    assert "reasoning_contract" in request
    assert "backlog" not in request
    assert "components" not in request
    assert "diagrams" not in request


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


def test_project_title_echo_is_rejected_inside_artifact_content() -> None:
    proposal = _host_reasoned_ecommerce_proposal()
    title = "Commerce Launch Recovery Workflow For Independent Merchants"
    proposal["intent"]["title"] = title
    proposal["backlog"][1]["problem"] = f"{title} needs implementation planning before the product is clear."
    proposal["components"][1]["responsibility"] = f"{title} component owns everything."
    proposal["diagrams"][0]["summary"] = f"{title} diagram summary repeats the title."
    proposal["release_plan"]["strategy"] = f"{title} release strategy repeats the title."

    issues = greenfield_quality_issues(proposal)

    assert any("repeats the raw title" in issue for issue in issues)


def test_runtime_source_does_not_contain_canned_greenfield_domain_families() -> None:
    source_root = Path(__file__).resolve().parents[3] / "src" / "odylith" / "runtime"
    banned = {
        "capital_merchant_lending",
        "defi_risk",
        "clinical_trial",
        "legal_intake",
        "bioinformatics",
        "robot_swarm",
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
