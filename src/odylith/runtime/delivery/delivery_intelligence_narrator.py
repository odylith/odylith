"""Guarded narrative rendering for delivery-intelligence snapshots.

This module never decides posture. The deterministic engine remains the source
of truth for scores, modes, and evidence context. The narrator may optionally
rewrite the five canonical cards when a provider is supplied, but every
provider result is validated and any failure falls back to deterministic cards.

Invariants:
- provider output must preserve the five-card schema;
- provider output may not introduce raw artifact paths into lead narrative;
- provider output may not contradict deterministic posture labels or omit cards;
- CI/tests should run with narration disabled or with fake providers only.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
import re
from typing import Any, Mapping, Protocol

_CARD_KEYS: tuple[str, ...] = (
    "executive_thesis",
    "delivery_tension",
    "why_now",
    "blast_radius",
    "next_forcing_function",
)
_SOURCE_RULES = "rules"
_SOURCE_MODEL = "hybrid-model"
_MAX_CARD_LENGTH = 320
_PATH_TOKEN_RE = re.compile(r"(?:[A-Za-z0-9_.-]+/){1,}[A-Za-z0-9_.-]+")


class NarrativeProvider(Protocol):
    """Provider-neutral narration interface."""

    def generate_cards(self, *, prompt_payload: Mapping[str, Any]) -> Mapping[str, Any] | None:
        """Return narrative card text or ``None`` when narration is unavailable."""


@dataclass(frozen=True)
class NarrationResult:
    """Validated narration result."""

    source: str
    cards: dict[str, str]
    diagnostics: list[str]


def narration_mode_from_env() -> str:
    """Resolve narration mode from environment."""

    token = str(os.environ.get("ODYLITH_DELIVERY_INTELLIGENCE_NARRATION_MODE", "disabled")).strip().lower()
    return token if token in {"disabled", "auto"} else "disabled"


def build_prompt_payload(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    """Build bounded prompt facts for optional narration providers."""

    cards = snapshot.get("cards", {}) if isinstance(snapshot.get("cards"), Mapping) else {}
    evidence_context = (
        snapshot.get("evidence_context", {})
        if isinstance(snapshot.get("evidence_context"), Mapping)
        else {}
    )
    return {
        "scope_type": str(snapshot.get("scope_type", "")).strip(),
        "scope_id": str(snapshot.get("scope_id", "")).strip(),
        "scope_label": str(snapshot.get("scope_label", "")).strip(),
        "posture_mode": str(snapshot.get("posture_mode", "")).strip(),
        "trajectory": str(snapshot.get("trajectory", "")).strip(),
        "confidence": str(snapshot.get("confidence", "")).strip(),
        "scores": dict(snapshot.get("scores", {})) if isinstance(snapshot.get("scores"), Mapping) else {},
        "explanation_facts": [
            str(item).strip()
            for item in snapshot.get("explanation_facts", [])
            if str(item).strip()
        ][:7],
        "evidence_context": {
            "basis": str(evidence_context.get("basis", "")).strip(),
            "freshness": str(evidence_context.get("freshness", "")).strip(),
            "linked_workstreams": list(evidence_context.get("linked_workstreams", []))[:5],
            "linked_components": list(evidence_context.get("linked_components", []))[:5],
            "linked_diagrams": list(evidence_context.get("linked_diagrams", []))[:5],
            "linked_surfaces": list(evidence_context.get("linked_surfaces", []))[:5],
        },
        "deterministic_cards": {key: str(cards.get(key, "")).strip() for key in _CARD_KEYS},
        "allowed_card_keys": list(_CARD_KEYS),
        "banned_patterns": [
            "raw artifact paths",
            "counts as the primary story",
            "explicit/inferred confusion",
            "schema omissions",
        ],
    }


def _validate_cards(
    *,
    cards: Mapping[str, Any] | None,
    deterministic_cards: Mapping[str, Any],
    posture_mode: str,
) -> tuple[dict[str, str] | None, list[str]]:
    diagnostics: list[str] = []
    if cards is None:
        diagnostics.append("provider returned no cards")
        return None, diagnostics
    if not isinstance(cards, Mapping):
        diagnostics.append("provider returned non-object cards")
        return None, diagnostics

    validated: dict[str, str] = {}
    for key in _CARD_KEYS:
        value = str(cards.get(key, "")).strip()
        if not value:
            diagnostics.append(f"missing card: {key}")
            continue
        if len(value) > _MAX_CARD_LENGTH:
            diagnostics.append(f"card too long: {key}")
            continue
        if _PATH_TOKEN_RE.search(value):
            diagnostics.append(f"raw path in card: {key}")
            continue
        validated[key] = value

    if len(validated) != len(_CARD_KEYS):
        return None, diagnostics

    joined = " ".join(validated.values()).lower()
    if posture_mode and posture_mode.replace("_", " ") not in joined:
        diagnostics.append("provider cards did not restate posture mode token")

    for key in _CARD_KEYS:
        baseline = str(deterministic_cards.get(key, "")).strip()
        if baseline and not validated[key]:
            diagnostics.append(f"empty rewrite for deterministic card: {key}")
            return None, diagnostics

    return validated, diagnostics


def narrate_snapshot(
    *,
    snapshot: Mapping[str, Any],
    provider: NarrativeProvider | None = None,
    mode: str = "disabled",
) -> NarrationResult:
    """Return validated cards for a snapshot."""

    cards = snapshot.get("cards", {}) if isinstance(snapshot.get("cards"), Mapping) else {}
    deterministic_cards = {key: str(cards.get(key, "")).strip() for key in _CARD_KEYS}
    if mode != "auto" or provider is None:
        return NarrationResult(source=_SOURCE_RULES, cards=deterministic_cards, diagnostics=[])

    prompt_payload = build_prompt_payload(snapshot)
    provider_cards = provider.generate_cards(prompt_payload=prompt_payload)
    validated, diagnostics = _validate_cards(
        cards=provider_cards,
        deterministic_cards=deterministic_cards,
        posture_mode=str(snapshot.get("posture_mode", "")).strip(),
    )
    if validated is None:
        return NarrationResult(source=_SOURCE_RULES, cards=deterministic_cards, diagnostics=diagnostics)
    return NarrationResult(source=_SOURCE_MODEL, cards=validated, diagnostics=diagnostics)


__all__ = [
    "NarrationResult",
    "NarrativeProvider",
    "build_prompt_payload",
    "narrate_snapshot",
    "narration_mode_from_env",
]
