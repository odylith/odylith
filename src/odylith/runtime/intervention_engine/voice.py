from __future__ import annotations

import hashlib
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


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _variant(seed: str, choices: Sequence[str]) -> str:
    rows = [_normalize_string(choice) for choice in choices if _normalize_string(choice)]
    if not rows:
        return ""
    digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()
    index = int(digest[:8], 16) % len(rows)
    return rows[index]


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


def _moment_seed(seed: str, *, kind: str, primary: GovernanceFact) -> str:
    return f"{seed}:{kind}:{_normalize_string(primary.headline)}"


def _support_clause(support: GovernanceFact | None) -> str:
    if support is None:
        return ""
    kind = _normalize_token(support.kind)
    if kind == "history":
        return "Casebook already has related memory in the frame."
    if kind == "topology":
        return "Atlas is touching the same boundary."
    if kind == "invariant":
        return "There is a hard rule in play here too."
    if kind == "governance_truth":
        return "The governed record is already anchored."
    if kind == "capture_opportunity":
        return "The evidence is already warm enough to capture cleanly."
    return ""


def _observation_lead(*, kind: str, seed: str, primary: GovernanceFact) -> str:
    headline = _strip_terminal_punctuation(primary.headline)
    if headline:
        fact_first = {
            "continuation": f"{headline}, so this should keep moving through the same governed thread",
            "ownership": f"{headline}, so let the owned boundary steer the next move",
            "boundary": f"{headline}, which makes the boundary the thing to capture next",
            "guardrail": f"{headline}, so treat it as a rule before the implementation outruns it",
            "recovery": f"{headline}, so reuse the earlier lesson instead of rediscovering it",
            "capture": f"{headline}, and the evidence is finally warm enough to preserve",
            "insight": headline,
        }
        if kind in fact_first:
            return fact_first[kind]
    variants = {
        "continuation": (
            "This is not a cold start.",
            "This already has a governed home.",
            "This slice is already anchored in the record.",
        ),
        "ownership": (
            "This just crossed into owned-boundary territory.",
            "This is a boundary decision, not just a feature discussion.",
            "The conversation is making a real ownership claim now.",
        ),
        "boundary": (
            "This is an owned-boundary moment.",
            "The interesting part here is the boundary, not the wording.",
            "This thread is leaning on topology now, not just intent.",
        ),
        "guardrail": (
            "This just turned into a hard rule.",
            "This stopped being a preference and became a constraint.",
            "This is system-rule territory now.",
        ),
        "recovery": (
            "This is brushing against memory we already paid for.",
            "We have learned this lesson once already.",
            "This thread is touching prior failure memory, not fresh ground.",
        ),
        "capture": (
            "The valuable truth is finally crisp enough to preserve.",
            "This is the moment to capture the real decision before it blurs.",
            "The thread has enough shape now to become governed truth.",
        ),
        "insight": (
            headline or "There is a sharper governed truth here than the thread is saying out loud.",
            "There is a more important governed truth here than the surface wording suggests.",
            "The conversation just exposed the real governed center of gravity.",
        ),
    }
    return _variant(_moment_seed(seed, kind=kind, primary=primary), variants.get(kind, variants["insight"]))


def _observation_next_move(*, kind: str, has_proposal: bool) -> str:
    if has_proposal:
        return {
            "continuation": "Extend the existing truth instead of splitting it.",
            "ownership": "Let the owned boundary steer the next move.",
            "boundary": "Let the boundary decide what gets captured next.",
            "guardrail": "Capture the rule before implementation outruns the record.",
            "recovery": "Reuse the lesson instead of rediscovering it in flight.",
            "capture": "Turn the moment into one clean governed bundle.",
            "insight": "Carry the sharp fact forward while it is still clear.",
        }.get(kind, "Carry the sharp fact forward while it is still clear.")
    return {
        "continuation": "Stay with the thread that already owns it.",
        "ownership": "Let the owned boundary steer the next move.",
        "boundary": "Use the boundary to narrow what happens next.",
        "guardrail": "Honor the rule before the implementation wanders.",
        "recovery": "Treat the prior memory as active guidance.",
        "capture": "Hold onto the signal until it is ready to capture cleanly.",
        "insight": "Follow the non-obvious fact, not the loudest wording.",
    }.get(kind, "Follow the non-obvious fact, not the loudest wording.")


def _observation_line(
    *,
    moment: Mapping[str, Any],
    primary: GovernanceFact,
    supporting: GovernanceFact | None,
    proposal_actions: Sequence[CaptureAction],
    seed: str,
) -> str:
    kind = _moment_kind(moment)
    lead = _observation_lead(kind=kind, seed=seed, primary=primary)
    support = _support_clause(supporting)
    next_move = _observation_next_move(kind=kind, has_proposal=bool(proposal_actions))
    parts = [lead, support, next_move]
    rows: list[str] = []
    seen: set[str] = set()
    for part in parts:
        sentence = _sentence(_strip_terminal_punctuation(part))
        token = _normalize_token(sentence)
        if not sentence or token in seen:
            continue
        seen.add(token)
        rows.append(sentence)
    return " ".join(rows[:2]).strip()


def _teaser_text(*, kind: str, seed: str) -> str:
    variants = {
        "continuation": (
            "Odylith can already feel that this is not a cold start. One more corroborating signal and it can turn that into a proposal.",
            "Odylith can already see an existing governed thread here. One more corroborating signal and it can turn that into a proposal.",
        ),
        "ownership": (
            "Odylith can already see an owned-boundary moment forming. One more corroborating signal and it can turn that into a proposal.",
            "Odylith can already feel the conversation crossing into owned-boundary territory. One more corroborating signal and it can turn that into a proposal.",
        ),
        "boundary": (
            "Odylith can already see the boundary becoming the important part. One more corroborating signal and it can turn that into a proposal.",
            "Odylith can already feel a topology moment taking shape. One more corroborating signal and it can turn that into a proposal.",
        ),
        "guardrail": (
            "Odylith can already see a hard rule taking shape. One more corroborating signal and it can turn that into a proposal.",
            "Odylith can already feel this turning into an invariant. One more corroborating signal and it can turn that into a proposal.",
        ),
        "recovery": (
            "Odylith can already see prior failure memory coming into frame. One more corroborating signal and it can turn that into a proposal.",
            "Odylith can already feel this brushing against an older lesson. One more corroborating signal and it can turn that into a proposal.",
        ),
        "capture": (
            "Odylith can already see governed truth starting to crystallize here. One more corroborating signal and it can turn that into a proposal.",
            "Odylith can already feel the real decision getting crisp enough to capture. One more corroborating signal and it can turn that into a proposal.",
        ),
        "insight": (
            "Odylith can already see a sharper governed truth here. One more corroborating signal and it can turn that into a proposal.",
            "Odylith can already feel the non-obvious truth taking shape here. One more corroborating signal and it can turn that into a proposal.",
        ),
    }
    return _variant(seed, variants.get(kind, variants["insight"]))


def _proposal_reason(action: CaptureAction) -> str:
    surface = _normalize_token(action.surface)
    action_name = _normalize_token(action.action)
    if surface == "radar":
        if action_name == "update":
            return "so this stays attached to the workstream that already owns it"
        if action_name == "create":
            return "so the slice gets a real governed home"
    if surface == "registry":
        if action_name == "update":
            return "so the runtime boundary stays aligned with the conversation truth"
        if action_name == "create":
            return "so the boundary becomes explicit instead of implied"
    if surface == "atlas":
        if action_name == "review_refresh":
            return "so the topology record stays honest"
        if action_name == "create":
            return "so the boundary has a real map"
    if surface == "casebook":
        if action_name == "reopen":
            return "so the older lesson stays attached to this moment"
        if action_name == "create":
            return "so the failure memory does not vanish back into chat"
    fallback = _strip_terminal_punctuation(action.rationale)
    return fallback or "because this is the governed home for the change"


def _proposal_delta_short(action: CaptureAction) -> str:
    title = _normalize_string(action.title)
    target_id = _normalize_string(action.target_id)
    action_name = _normalize_token(action.action)
    surface = _normalize_token(action.surface)
    if surface == "radar":
        if action_name == "create":
            return "create the workstream truth"
        if action_name == "update":
            return f"extend {target_id or title or 'the existing workstream'}"
    if surface == "registry":
        if action_name == "create":
            return f"register {title or target_id or 'the runtime boundary'}"
        if action_name == "update":
            return f"refresh {target_id or title or 'the existing boundary'}"
    if surface == "atlas":
        if action_name == "create":
            return f"scaffold {title or target_id or 'the topology record'}"
        if action_name == "review_refresh":
            return f"refresh {target_id or title or 'the existing diagram'}"
    if surface == "casebook":
        if action_name == "create":
            return "capture the failure memory"
        if action_name == "reopen":
            return f"reopen {target_id or title or 'the existing bug'}"
    return _normalize_string(action.action) or "capture the governed delta"


def _proposal_bullet(action: CaptureAction) -> str:
    detail = _sentence(_proposal_delta_short(action))
    why = _sentence(_proposal_reason(action))
    return f"- {_surface_label(action.surface)}: {detail} {why}".strip()


def _proposal_intro(*, preview_only: bool, kind: str, seed: str) -> str:
    preview_variants = {
        "continuation": (
            "Odylith Proposal: There is a clean way to extend the truth already in motion here. It is staying in preview until every action has a safe apply lane.",
            "Odylith Proposal: There is a clean governed bundle here, but it should stay in preview until every action has a safe apply lane.",
        ),
        "boundary": (
            "Odylith Proposal: There is a clean way to capture this boundary without turning the moment into paperwork. It is staying in preview until every action has a safe apply lane.",
            "Odylith Proposal: The boundary is clear enough to capture cleanly. It is staying in preview until every action has a safe apply lane.",
        ),
        "guardrail": (
            "Odylith Proposal: There is a clean way to preserve this rule before the implementation outruns it. It is staying in preview until every action has a safe apply lane.",
            "Odylith Proposal: The rule is clear enough to govern now. It is staying in preview until every action has a safe apply lane.",
        ),
        "recovery": (
            "Odylith Proposal: There is a clean way to carry forward the older lesson here. It is staying in preview until every action has a safe apply lane.",
            "Odylith Proposal: This can be captured without losing the older memory attached to it. It is staying in preview until every action has a safe apply lane.",
        ),
        "capture": (
            "Odylith Proposal: There is a clean governed bundle here. It is staying in preview until every action has a safe apply lane.",
            "Odylith Proposal: The moment is ready to capture cleanly. It is staying in preview until every action has a safe apply lane.",
        ),
        "insight": (
            "Odylith Proposal: There is a clean governed bundle here. It is staying in preview until every action has a safe apply lane.",
            "Odylith Proposal: The real decision can be captured cleanly now. It is staying in preview until every action has a safe apply lane.",
        ),
    }
    ready_variants = {
        "continuation": (
            "Odylith Proposal: There is a clean way to extend the truth already in motion here, and the whole bundle can move in one confirmation.",
            "Odylith Proposal: The governed path is clean here, and the whole bundle can move in one confirmation.",
        ),
        "boundary": (
            "Odylith Proposal: The boundary is clear enough to capture cleanly, and the whole bundle can move in one confirmation.",
            "Odylith Proposal: There is a clean way to preserve this boundary, and the whole bundle can move in one confirmation.",
        ),
        "guardrail": (
            "Odylith Proposal: The rule is clear enough to govern now, and the whole bundle can move in one confirmation.",
            "Odylith Proposal: There is a clean way to preserve this rule, and the whole bundle can move in one confirmation.",
        ),
        "recovery": (
            "Odylith Proposal: There is a clean way to carry forward the older lesson here, and the whole bundle can move in one confirmation.",
            "Odylith Proposal: The prior lesson is clear enough to preserve now, and the whole bundle can move in one confirmation.",
        ),
        "capture": (
            "Odylith Proposal: The moment is ready to capture cleanly, and the whole bundle can move in one confirmation.",
            "Odylith Proposal: There is a clean governed bundle here, and the whole bundle can move in one confirmation.",
        ),
        "insight": (
            "Odylith Proposal: There is a clean governed bundle here, and the whole bundle can move in one confirmation.",
            "Odylith Proposal: The real decision can move as one clean bundle now.",
        ),
    }
    variants = preview_variants if preview_only else ready_variants
    return _variant(seed, variants.get(kind, variants["insight"]))


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
    moment_payload = _mapping(moment)
    primary = _primary_fact(moment_payload, facts)
    supporting = _supporting_fact(moment_payload)
    kind = _moment_kind(moment_payload)
    line = _observation_line(
        moment=moment_payload,
        primary=primary,
        supporting=supporting,
        proposal_actions=proposal_actions,
        seed=seed or _normalize_string(primary.headline) or kind,
    )
    headline = _normalize_string(primary.headline) or line or "Odylith has enough evidence to intervene."
    markdown_text = f"{voice_contract.OBSERVATION_LABEL_MARKDOWN} {line}".strip()
    plain_text = f"{voice_contract.OBSERVATION_LABEL_PLAIN} {line}".strip()
    teaser_text = _sentence(
        _teaser_text(
            kind=kind,
            seed=seed or _normalize_string(primary.headline) or kind,
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
        moment=moment_payload,
        primary=primary,
        supporting=supporting,
        proposal_actions=[],
        seed=seed or _normalize_string(primary.headline) or label_kind,
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
    kind = _moment_kind(moment_payload)
    intro_seed = seed or f"{kind}:{len(actions)}"
    markdown_lines = [
        "-----",
        _proposal_intro(preview_only=preview_only, kind=kind, seed=intro_seed),
        "",
    ]
    plain_lines = [
        "-----",
        _proposal_intro(preview_only=preview_only, kind=kind, seed=intro_seed),
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
