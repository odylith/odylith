from __future__ import annotations

from typing import Any, Mapping

from odylith.runtime.governance import proof_state


def enforce_payload(
    payload: Mapping[str, Any] | Any,
    *,
    claim_guard: Mapping[str, Any],
    claim_lint: Mapping[str, Any],
    surface: str,
) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        return {}
    return proof_state.enforce_claim_payload(
        payload,
        claim_guard=claim_guard,
        claim_lint=claim_lint,
        surface=surface,
    )


def build_claim_enforcement_summary(
    *,
    claim_lint: Mapping[str, Any],
    ambient_payloads: Mapping[str, Mapping[str, Any]],
    assist_payload: Mapping[str, Any],
    supplemental_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    return {
        "gate": dict(claim_lint.get("gate", {})) if isinstance(claim_lint.get("gate"), Mapping) else {},
        "forced_checks": list(claim_lint.get("forced_checks", [])) if isinstance(claim_lint.get("forced_checks"), list) else [],
        "ambient": {
            key: dict(payload.get("claim_enforcement", {})) if isinstance(payload.get("claim_enforcement"), Mapping) else {}
            for key, payload in ambient_payloads.items()
        },
        "closeout": {
            "assist": dict(assist_payload.get("claim_enforcement", {})) if isinstance(assist_payload.get("claim_enforcement"), Mapping) else {},
            "selected_supplemental": (
                dict(supplemental_payload.get("claim_enforcement", {}))
                if isinstance(supplemental_payload, Mapping) and isinstance(supplemental_payload.get("claim_enforcement"), Mapping)
                else {}
            ),
        },
    }
