from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from typing import Mapping
from typing import Sequence

from odylith.runtime.intervention_engine.contract import CaptureAction
from odylith.runtime.intervention_engine.contract import GovernanceFact
from odylith.runtime.intervention_engine import voice_contract


def _normalize_string(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _normalize_token(value: Any) -> str:
    return _normalize_string(value).lower().replace("-", "_").replace(" ", "_")


def _sentence(value: Any) -> str:
    token = _normalize_string(value)
    if not token:
        return ""
    return token if token.endswith((".", "!", "?")) else f"{token}."


def _strip_terminal_punctuation(value: Any) -> str:
    return _normalize_string(value).rstrip(".!? ")


def _sentence_token(value: Any) -> str:
    return _normalize_token(_strip_terminal_punctuation(value))


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


@dataclass(frozen=True)
class _VoiceProposition:
    claim: str
    consequence: str
    action: str


def _compact_text(value: Any, *, max_chars: int = 220) -> str:
    text = _normalize_string(value)
    if len(text) <= max_chars:
        return text
    window = text[: max_chars + 1]
    for separator in (". ", "; ", ", "):
        index = window.rfind(separator)
        if index >= max_chars // 2:
            return window[: index + 1].strip()
    return f"{window[:max_chars].rstrip()}..."


def _deduped_sentences(values: Sequence[Any], *, limit: int) -> list[str]:
    rows: list[str] = []
    seen: set[str] = set()
    for value in values:
        sentence = _sentence(_compact_text(value))
        token = _sentence_token(sentence)
        if not sentence or token in seen:
            continue
        if any(token and (token in previous or previous in token) for previous in seen):
            continue
        seen.add(token)
        rows.append(sentence)
        if len(rows) >= limit:
            break
    return rows


def _surface_label(surface: str) -> str:
    token = _normalize_token(surface)
    return {
        "radar": "Radar",
        "registry": "Registry",
        "atlas": "Atlas",
        "casebook": "Casebook",
    }.get(token, _normalize_string(surface).title() or "Surface")


def collect_action_surfaces(actions: Sequence[CaptureAction]) -> list[str]:
    surfaces: list[str] = []
    for action in actions:
        label = _surface_label(action.surface)
        if label not in surfaces:
            surfaces.append(label)
    return surfaces


def _fact_from_mapping(value: Any) -> GovernanceFact:
    if isinstance(value, GovernanceFact):
        return value
    payload = dict(value) if isinstance(value, Mapping) else {}
    return GovernanceFact(
        kind=_normalize_string(payload.get("kind")) or "capture_opportunity",
        headline=_normalize_string(payload.get("headline")),
        detail=_normalize_string(payload.get("detail")),
        evidence_classes=list(payload.get("evidence_classes", [])) if isinstance(payload.get("evidence_classes"), list) else [],
        refs=list(payload.get("refs", [])) if isinstance(payload.get("refs"), list) else [],
        priority=int(payload.get("priority") or 0),
    )


def _moment_kind(moment: Mapping[str, Any]) -> str:
    return _normalize_token(moment.get("kind")) or "insight"


def _primary_fact(moment: Mapping[str, Any], facts: Sequence[GovernanceFact]) -> GovernanceFact:
    row = _fact_from_mapping(moment.get("primary_fact"))
    if _normalize_string(row.headline):
        return row
    return facts[0] if facts else GovernanceFact(kind="capture_opportunity", headline="This slice is ready to become governed truth.")


def _supporting_fact(moment: Mapping[str, Any]) -> GovernanceFact | None:
    row = _fact_from_mapping(moment.get("supporting_fact"))
    return row if _normalize_string(row.headline) else None


def _fact_claim(primary: GovernanceFact) -> str:
    return (
        _strip_terminal_punctuation(primary.headline)
        or _strip_terminal_punctuation(primary.detail)
        or "This slice is ready to become governed truth"
    )


def _fact_consequence(primary: GovernanceFact, supporting: GovernanceFact | None) -> str:
    claim_token = _sentence_token(_fact_claim(primary))
    candidates = [
        primary.detail,
        supporting.headline if supporting is not None else "",
        supporting.detail if supporting is not None else "",
    ]
    for candidate in candidates:
        text = _strip_terminal_punctuation(candidate)
        token = _sentence_token(text)
        if text and token and token != claim_token and token not in claim_token and claim_token not in token:
            return text
    return ""


def _action_target(action: CaptureAction) -> str:
    return (
        _normalize_string(action.target_id)
        or _normalize_string(action.title)
        or _normalize_string(action.target_kind)
        or "the governed record"
    )


def _action_delta(action: CaptureAction) -> str:
    verb = _normalize_string(action.action).replace("_", " ").strip() or "capture"
    return f"{verb} {_action_target(action)}"


def _action_rationale(action: CaptureAction) -> str:
    return _strip_terminal_punctuation(action.rationale)


def _action_sentence(actions: Sequence[CaptureAction]) -> str:
    if not actions:
        return ""
    if len(actions) == 1:
        action = actions[0]
        rationale = _action_rationale(action)
        if rationale:
            return rationale
        return f"{_surface_label(action.surface)} can {_action_delta(action)}"
    surfaces = collect_action_surfaces(actions)
    joined = _join_human_list(surfaces)
    first_rationale = _action_rationale(actions[0])
    if first_rationale:
        return f"{joined} are the affected surfaces; {first_rationale[0].lower()}{first_rationale[1:]}"
    return f"{joined} are the affected surfaces for {len(actions)} proposed actions"


def _voice_proposition(
    *,
    primary: GovernanceFact,
    supporting: GovernanceFact | None,
    proposal_actions: Sequence[CaptureAction],
) -> _VoiceProposition:
    return _VoiceProposition(
        claim=_fact_claim(primary),
        consequence=_fact_consequence(primary, supporting),
        action=_action_sentence(proposal_actions),
    )


def _observation_line(
    *,
    primary: GovernanceFact,
    supporting: GovernanceFact | None,
    proposal_actions: Sequence[CaptureAction],
) -> str:
    proposition = _voice_proposition(
        primary=primary,
        supporting=supporting,
        proposal_actions=proposal_actions,
    )
    rows = _deduped_sentences(
        [
            proposition.claim,
            proposition.action if proposal_actions else proposition.consequence,
            proposition.consequence if proposal_actions else "",
        ],
        limit=2,
    )
    return " ".join(rows).strip()


def _teaser_text(*, primary: GovernanceFact, supporting: GovernanceFact | None) -> str:
    proposition = _voice_proposition(
        primary=primary,
        supporting=supporting,
        proposal_actions=[],
    )
    rows = _deduped_sentences(
        [
            f"Odylith is tracking this signal: {proposition.claim}",
            proposition.consequence,
        ],
        limit=2,
    )
    return " ".join(rows).strip()


def _proposal_reason(action: CaptureAction) -> str:
    return _action_rationale(action) or f"{_surface_label(action.surface)} owns this proposed action"


def _proposal_delta_short(action: CaptureAction) -> str:
    return _action_delta(action)


def _proposal_bullet(action: CaptureAction) -> str:
    detail = _sentence(_proposal_delta_short(action))
    why = _sentence(_proposal_reason(action))
    return f"- {_surface_label(action.surface)}: {detail} {why}".strip()


def _join_human_list(values: Sequence[str]) -> str:
    rows = [_normalize_string(value) for value in values if _normalize_string(value)]
    if not rows:
        return ""
    if len(rows) == 1:
        return rows[0]
    if len(rows) == 2:
        return f"{rows[0]} and {rows[1]}"
    return f"{', '.join(rows[:-1])}, and {rows[-1]}"


def _proposal_status_sentence(*, preview_only: bool) -> str:
    if preview_only:
        return "Some actions still need a safe apply lane before Odylith can apply them automatically"
    return "The supported actions can move through one confirmation"


def _proposal_intro(
    *,
    preview_only: bool,
    moment: Mapping[str, Any],
    actions: Sequence[CaptureAction],
) -> str:
    primary = _primary_fact(moment, [])
    supporting = _supporting_fact(moment)
    proposition = _voice_proposition(
        primary=primary,
        supporting=supporting,
        proposal_actions=[],
    )
    surfaces = collect_action_surfaces(actions)
    action_surface_sentence = (
        f"The proposed actions touch {_join_human_list(surfaces)}"
        if surfaces
        else ""
    )
    rows = _deduped_sentences(
        [
            f"Odylith Proposal: {proposition.claim}",
            proposition.consequence,
            action_surface_sentence,
            _proposal_status_sentence(preview_only=preview_only),
        ],
        limit=4,
    )
    if not rows:
        return f"Odylith Proposal: {_proposal_status_sentence(preview_only=preview_only)}."
    if not rows[0].startswith("Odylith Proposal:"):
        rows.insert(0, f"Odylith Proposal: {_fact_claim(primary)}.")
    return " ".join(rows)


def _proposal_confirmation_lines() -> tuple[str, str, str]:
    phrase = voice_contract.PROPOSAL_CONFIRMATION_PHRASE
    return (
        f'To apply, say "{phrase}".',
        f'To apply, say "{phrase}".',
        phrase,
    )


def summarize_proposal(
    *,
    actions: Sequence[CaptureAction],
    moment: Mapping[str, Any] | None = None,
) -> str:
    moment_payload = _mapping(moment)
    preview_only = any(not action.apply_supported for action in actions)
    surfaces = collect_action_surfaces(actions)
    if not surfaces:
        return "Odylith Proposal"
    joined_surfaces = ", ".join(surfaces[:3])
    if len(surfaces) > 3:
        joined_surfaces = f"{joined_surfaces}, and {len(surfaces) - 3} more"
    if preview_only:
        return f"Previewing a governed proposal across {joined_surfaces}."
    kind = _moment_kind(moment_payload)
    if kind == "guardrail":
        return f"Proposing a governed rule-preserving bundle across {joined_surfaces}."
    if kind == "recovery":
        return f"Proposing a governed recovery bundle across {joined_surfaces}."
    return f"Proposing a governed bundle across {joined_surfaces}."


def render_observation(
    *,
    facts: Sequence[GovernanceFact],
    proposal_actions: Sequence[CaptureAction],
    moment: Mapping[str, Any] | None = None,
    seed: str = "",
) -> tuple[str, str, str, str]:
    del seed
    moment_payload = _mapping(moment)
    primary = _primary_fact(moment_payload, facts)
    supporting = _supporting_fact(moment_payload)
    line = _observation_line(
        primary=primary,
        supporting=supporting,
        proposal_actions=proposal_actions,
    )
    headline = _normalize_string(primary.headline) or line or "Odylith has enough evidence to intervene."
    markdown_text = f"{voice_contract.OBSERVATION_LABEL_MARKDOWN} {line}".strip()
    plain_text = f"{voice_contract.OBSERVATION_LABEL_PLAIN} {line}".strip()
    teaser_text = _sentence(
        _teaser_text(
            primary=primary,
            supporting=supporting,
        )
    )
    return headline, markdown_text, plain_text, teaser_text


def render_ambient_signal(
    *,
    moment: Mapping[str, Any] | None,
    facts: Sequence[GovernanceFact],
    markdown: bool,
    seed: str = "",
) -> tuple[str, str]:
    del seed
    moment_payload = _mapping(moment)
    primary = _primary_fact(moment_payload, facts)
    supporting = _supporting_fact(moment_payload)
    label_kind = _normalize_token(moment_payload.get("ambient_label_kind")) or "insight"
    label = {
        "insight": "Odylith Insight:",
        "history": "Odylith History:",
        "risks": "Odylith Risks:",
    }.get(label_kind, "Odylith Insight:")
    if markdown:
        label = f"**{label}**"
    body = _observation_line(
        primary=primary,
        supporting=supporting,
        proposal_actions=[],
    )
    return label_kind, f"{label} {body}".strip()


def render_proposal(
    *,
    actions: Sequence[CaptureAction],
    moment: Mapping[str, Any] | None = None,
    seed: str = "",
) -> tuple[str, str, str]:
    moment_payload = _mapping(moment)
    preview_only = any(not action.apply_supported for action in actions)
    del seed
    markdown_lines = [
        "-----",
        _proposal_intro(preview_only=preview_only, moment=moment_payload, actions=actions),
        "",
    ]
    plain_lines = [
        "-----",
        _proposal_intro(preview_only=preview_only, moment=moment_payload, actions=actions),
        "",
    ]
    for action in actions:
        bullet = _proposal_bullet(action)
        markdown_lines.append(bullet)
        plain_lines.append(bullet)
    markdown_lines.append("")
    plain_lines.append("")
    confirmation_markdown, confirmation_plain, confirmation_text = _proposal_confirmation_lines()
    markdown_lines.append(confirmation_markdown)
    markdown_lines.append("-----")
    plain_lines.append(confirmation_plain)
    plain_lines.append("-----")
    return "\n".join(markdown_lines), "\n".join(plain_lines), confirmation_text
