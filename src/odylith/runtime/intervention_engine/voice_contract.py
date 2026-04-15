from __future__ import annotations

OBSERVATION_LABEL_MARKDOWN = "**Odylith Observation:**"
OBSERVATION_LABEL_PLAIN = "Odylith Observation:"
PROPOSAL_LABEL = "Odylith Proposal"
ASSIST_LABEL_MARKDOWN = "**Odylith Assist:**"
ASSIST_LABEL_PLAIN = "Odylith Assist:"
PROPOSAL_CONFIRMATION_PHRASE = "apply this proposal"

DEFAULT_VOICE_DESCRIPTORS: tuple[str, ...] = (
    "friendly",
    "delightful",
    "soulful",
    "insightful",
    "simple",
    "clear",
    "accurate",
    "precise",
    "human",
)

EXPRESSION_TIERS: tuple[str, ...] = (
    "silent",
    "ambient_inline",
    "ambient_explicit",
    "teaser",
    "observation",
    "proposal",
    "assist",
)


def voice_contract_payload() -> dict[str, object]:
    return {
        "mode": "default_brand_voice",
        "descriptors": list(DEFAULT_VOICE_DESCRIPTORS),
        "templated_or_mechanical_forbidden": True,
        "voice_pack_ready": True,
        "voice_pack_release_target": "future",
        "labels": {
            "observation_markdown": OBSERVATION_LABEL_MARKDOWN,
            "observation_plain": OBSERVATION_LABEL_PLAIN,
            "proposal": PROPOSAL_LABEL,
            "assist_markdown": ASSIST_LABEL_MARKDOWN,
            "assist_plain": ASSIST_LABEL_PLAIN,
        },
        "confirmation_phrase": PROPOSAL_CONFIRMATION_PHRASE,
        "expression_tiers": list(EXPRESSION_TIERS),
    }
