from __future__ import annotations

from odylith.runtime.domain_intelligence.greenfield_preconfirm_completion import GreenfieldCompletionPackage
from odylith.runtime.domain_intelligence.greenfield_preconfirm_patchset import patchset_request_from_findings
from odylith.runtime.domain_intelligence.greenfield_preconfirm_rescue_probe import (
    RESCUE_PROBE_CODE,
)
from odylith.runtime.domain_intelligence.greenfield_preconfirm_rescue_probe import (
    RESCUE_PROBE_ENV,
)
from odylith.runtime.domain_intelligence.greenfield_preconfirm_rescue_probe import (
    RESCUE_PROBE_MARKER_KEY,
)
from odylith.runtime.domain_intelligence.greenfield_preconfirm_rescue_probe import (
    RESCUE_PROBE_MARKER_STATUS,
)
from odylith.runtime.domain_intelligence.greenfield_preconfirm_rescue_probe import (
    RESCUE_PROBE_TOKEN,
)
from odylith.runtime.domain_intelligence.greenfield_preconfirm_rescue_probe import (
    apply_rescue_probe_operations,
)
from odylith.runtime.domain_intelligence.greenfield_preconfirm_rescue_probe import (
    rescue_probe_findings,
)
from odylith.runtime.domain_intelligence.greenfield_preconfirm_rescue_probe import (
    rescue_probe_repaired,
)


def test_rescue_probe_uses_exact_internal_token_and_typed_patch(monkeypatch) -> None:
    package = GreenfieldCompletionPackage(proposal={"intent": {"title": "Probe"}})

    assert rescue_probe_findings(package) == ()

    monkeypatch.setenv(RESCUE_PROBE_ENV, "1")
    assert rescue_probe_findings(package) == ()

    monkeypatch.setenv(RESCUE_PROBE_ENV, RESCUE_PROBE_TOKEN)
    finding = rescue_probe_findings(package)[0]
    request = patchset_request_from_findings((finding,)).to_dict()
    operation = request["operations"][0]

    assert finding.code == RESCUE_PROBE_CODE
    assert operation["replacement_fact"][RESCUE_PROBE_MARKER_KEY]["status"] == RESCUE_PROBE_MARKER_STATUS

    proposal: dict[str, object] = {}
    assert apply_rescue_probe_operations(proposal, request["operations"])
    assert rescue_probe_repaired(proposal)
    assert rescue_probe_findings(GreenfieldCompletionPackage(proposal=proposal)) == ()
