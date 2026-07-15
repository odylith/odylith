from __future__ import annotations

from odylith.runtime.domain_intelligence.greenfield_preconfirm_completion import GreenfieldCompletionPackage
from odylith.runtime.domain_intelligence.greenfield_preconfirm_patchset import patchset_request_from_findings
from odylith.runtime.domain_intelligence.greenfield_preconfirm_structured_rescue_proof import (
    STRUCTURED_RESCUE_PROOF_CODE,
)
from odylith.runtime.domain_intelligence.greenfield_preconfirm_structured_rescue_proof import (
    STRUCTURED_RESCUE_PROOF_ENV,
)
from odylith.runtime.domain_intelligence.greenfield_preconfirm_structured_rescue_proof import (
    STRUCTURED_RESCUE_PROOF_TARGET_PATH,
)
from odylith.runtime.domain_intelligence.greenfield_preconfirm_structured_rescue_proof import (
    STRUCTURED_RESCUE_PROOF_TOKEN,
)
from odylith.runtime.domain_intelligence.greenfield_preconfirm_structured_rescue_proof import (
    structured_rescue_proof_findings,
)
from odylith.runtime.domain_intelligence.greenfield_preconfirm_structured_rescue_proof import (
    structured_rescue_proof_repaired,
)


def test_structured_rescue_proof_requires_exact_token_and_host_patch(monkeypatch) -> None:
    package = GreenfieldCompletionPackage(proposal={"semantic_model": {"domain_ontology": {}}})

    assert structured_rescue_proof_findings(package) == ()
    monkeypatch.setenv(STRUCTURED_RESCUE_PROOF_ENV, "1")
    assert structured_rescue_proof_findings(package) == ()

    monkeypatch.setenv(STRUCTURED_RESCUE_PROOF_ENV, STRUCTURED_RESCUE_PROOF_TOKEN)
    finding = structured_rescue_proof_findings(package)[0]
    request = patchset_request_from_findings((finding,)).to_dict()
    operation = request["operations"][0]

    assert finding.code == STRUCTURED_RESCUE_PROOF_CODE
    assert operation["target_layer"] == "semantic_model"
    assert operation["target_path"] == STRUCTURED_RESCUE_PROOF_TARGET_PATH
    assert operation["operation_kind"] == "semantic_external_systems"
    assert operation["replacement_fact"] == ""
    assert operation["confidence"] == 0.2

    repaired = {
        "semantic_patch_ledger": [
            {
                "issue_code": STRUCTURED_RESCUE_PROOF_CODE,
                "target_path": STRUCTURED_RESCUE_PROOF_TARGET_PATH,
                "applied_field": STRUCTURED_RESCUE_PROOF_TARGET_PATH,
            }
        ]
    }
    assert structured_rescue_proof_repaired(repaired) is True
    assert structured_rescue_proof_findings(GreenfieldCompletionPackage(proposal=repaired)) == ()
