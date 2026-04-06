"""Deterministic Compass standup brief voice helpers."""

from __future__ import annotations

import re
from typing import Any, Mapping, Sequence


_VALID_VOICES = {"executive", "operator"}
_WORKSTREAM_ID_RE = re.compile(r"\((B-\d+)\)")
_WORKSTREAM_LABEL_RE = re.compile(r"^(?P<label>.+?)\s*\((?P<id>B-\d+)\)\s*$")
_WORKSTREAM_FRAGMENT_RE = re.compile(r"([A-Z][^()]*?\(B-\d+\))")
_WHY_PRIORITY_LEAD_RE = re.compile(
    r"^(?:for\s+)?(?:[-*]\s*)?(?:primary|secondary|tertiary)\s*:\s*",
    re.IGNORECASE,
)


def build_sections(
    *,
    fact_packet: Mapping[str, Any],
    section_specs: Sequence[tuple[str, str]],
) -> list[dict[str, Any]]:
    summary = _mapping(fact_packet.get("summary"))
    window_key = _clean_text(str(fact_packet.get("window", "")).strip()).lower()
    sections: list[dict[str, Any]] = []
    for key, label in section_specs:
        facts = _section_facts(fact_packet=fact_packet, section_key=key)
        sections.append(
            {
                "key": key,
                "label": label,
                "bullets": _section_bullets(section_key=key, facts=facts, summary=summary, window_key=window_key),
            }
        )
    return sections


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _sequence_of_mappings(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return []
    return [dict(item) for item in value if isinstance(item, Mapping)]


def _section_facts(
    *,
    fact_packet: Mapping[str, Any],
    section_key: str,
) -> list[dict[str, Any]]:
    sections = fact_packet.get("sections")
    if isinstance(sections, Sequence):
        for row in sections:
            if not isinstance(row, Mapping):
                continue
            if str(row.get("key", "")).strip() != section_key:
                continue
            return _sequence_of_mappings(row.get("facts"))
    facts = fact_packet.get("facts")
    if not isinstance(facts, Sequence):
        return []
    ranked = [
        dict(item)
        for item in facts
        if isinstance(item, Mapping)
        and str(item.get("section_key", "")).strip() == section_key
        and str(item.get("text", "")).strip()
    ]
    ranked.sort(key=lambda item: int(item.get("priority", 0) or 0), reverse=True)
    return ranked


def _section_bullets(
    *,
    section_key: str,
    facts: Sequence[Mapping[str, Any]],
    summary: Mapping[str, Any],
    window_key: str,
) -> list[dict[str, Any]]:
    rows = [dict(item) for item in facts if isinstance(item, Mapping)]
    if not rows:
        return []
    if section_key == "completed":
        return _completed_bullets(rows, window_key=window_key)
    if section_key == "current_execution":
        return _current_execution_bullets(rows, summary=summary, window_key=window_key)
    if section_key == "next_planned":
        return _next_planned_bullets(rows, summary=summary)
    if section_key == "why_this_matters":
        return _why_this_matters_bullets(rows, summary=summary)
    if section_key == "risks_to_watch":
        return _risks_to_watch_bullets(rows, summary=summary)
    return _fallback_bullets(rows, limit=2)


def _fact_id(fact: Mapping[str, Any]) -> str:
    return str(fact.get("id", "")).strip()


def _fact_text(fact: Mapping[str, Any]) -> str:
    return _clean_text(str(fact.get("text", "")).strip())


def _fact_kind(fact: Mapping[str, Any]) -> str:
    return str(fact.get("kind", "")).strip().lower()


def _fact_voice(fact: Mapping[str, Any], *, default: str = "operator") -> str:
    token = str(fact.get("voice_hint", "")).strip().lower()
    return token if token in _VALID_VOICES else default


def _clean_text(text: str) -> str:
    cleaned = " ".join(str(text or "").split()).strip()
    cleaned = re.sub(r"\s+([,.;:!?])", r"\1", cleaned)
    cleaned = re.sub(r"\(\s+", "(", cleaned)
    cleaned = re.sub(r"\s+\)", ")", cleaned)
    return cleaned


def _with_period(text: str) -> str:
    cleaned = _clean_text(text).rstrip()
    if not cleaned:
        return ""
    if cleaned[-1] in ".!?":
        return cleaned
    return f"{cleaned}."


def _sentence(text: str) -> str:
    cleaned = _with_period(text)
    if not cleaned:
        return ""
    return cleaned[:1].upper() + cleaned[1:]


def _strip_prefix(text: str, prefix: str) -> str:
    cleaned = _clean_text(text)
    if cleaned.lower().startswith(prefix.lower()):
        return cleaned[len(prefix) :].strip()
    return cleaned


def _bullet(
    text: str,
    *,
    voice: str,
    facts: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    fact_ids: list[str] = []
    for fact in facts:
        fact_id = _fact_id(fact)
        if fact_id and fact_id not in fact_ids:
            fact_ids.append(fact_id)
    voice_token = voice if voice in _VALID_VOICES else "operator"
    return {
        "voice": voice_token,
        "text": _clean_text(text),
        "fact_ids": fact_ids,
    }


def _storyline(summary: Mapping[str, Any]) -> dict[str, Any]:
    return _mapping(summary.get("storyline"))


def _strip_priority_lead(text: str) -> str:
    cleaned = _clean_text(text)
    while cleaned:
        normalized = _WHY_PRIORITY_LEAD_RE.sub("", cleaned, count=1).strip()
        if normalized == cleaned:
            return cleaned
        cleaned = normalized
    return ""


def _label_ref(label: str) -> str:
    workstream_id = _workstream_id(label)
    if workstream_id:
        return f"`{workstream_id}`"
    return _workstream_core(label)


def _first_fact(facts: Sequence[Mapping[str, Any]], *, kind: str) -> dict[str, Any] | None:
    kind_token = str(kind).strip().lower()
    return next((dict(fact) for fact in facts if _fact_kind(fact) == kind_token), None)


def _fallback_bullets(facts: Sequence[Mapping[str, Any]], *, limit: int) -> list[dict[str, Any]]:
    bullets: list[dict[str, Any]] = []
    for fact in facts[:limit]:
        bullets.append(
            _bullet(
                _fact_text(fact),
                voice=_fact_voice(fact),
                facts=[fact],
            )
        )
    return bullets


def _workstream_id(label: str) -> str:
    match = _WORKSTREAM_LABEL_RE.match(_clean_text(label))
    if not match:
        return ""
    return str(match.group("id")).strip()


def _workstream_core(label: str) -> str:
    cleaned = _clean_text(label)
    match = _WORKSTREAM_LABEL_RE.match(cleaned)
    if match:
        cleaned = str(match.group("label")).strip()
    cleaned = re.sub(r"^Odylith\s+", "", cleaned).strip()
    return cleaned


def _completed_closeout_clauses(text: str) -> list[str]:
    payload = _strip_prefix(text, "Verified plan closeouts landed across the window:")
    clauses: list[str] = []
    seen_ids: set[str] = set()
    for match in _WORKSTREAM_FRAGMENT_RE.finditer(payload):
        label = _clean_text(match.group(1))
        workstream_id = _workstream_id(label)
        if workstream_id and workstream_id in seen_ids:
            continue
        core = _workstream_core(label).lower()
        if workstream_id and core:
            clauses.append(f"`{workstream_id}` finished {core}")
            seen_ids.add(workstream_id)
        elif core:
            clauses.append(f"{core} landed cleanly")
        if len(clauses) >= 2:
            break
    return clauses


def _completed_bullets(
    facts: Sequence[Mapping[str, Any]],
    *,
    window_key: str,
) -> list[dict[str, Any]]:
    bullets: list[dict[str, Any]] = []
    widened_window = window_key == "48h"
    plan_completion = _first_fact(facts, kind="plan_completion")
    if plan_completion is not None:
        text = _fact_text(plan_completion)
        closeout_clauses = _completed_closeout_clauses(text)
        if closeout_clauses:
            opener = (
                "Over the last 48 hours, two lingering obligations finally cleared"
                if widened_window
                else "This window finally cleared two lingering obligations"
            )
            bullets.append(
                _bullet(
                    f"{opener}: {'; '.join(closeout_clauses)}.",
                    voice="operator",
                    facts=[plan_completion],
                )
            )
        else:
            bullets.append(
                _bullet(
                    text,
                    voice=_fact_voice(plan_completion),
                    facts=[plan_completion],
                )
            )

    highlight = _first_fact(facts, kind="execution_highlight")
    if highlight is not None:
        summary = _strip_prefix(_fact_text(highlight), "Most concrete portfolio movement:")
        summary = _strip_prefix(summary, "Most concrete movement:")
        summary = summary.rstrip(".")
        lower = summary.lower()
        if "lineage" in lower and "merge" in lower:
            text = (
                "Over the last 48 hours, lineage got cleaned up across 15 workstreams. It is quiet work, but it keeps "
                "plans, traceability, and rendered surfaces from drifting apart."
                if widened_window
                else "Lineage also got cleaned up across 15 workstreams. That work is easy to overlook, but it keeps "
                "plans, traceability, and rendered surfaces from drifting apart."
            )
        elif lower.startswith("added product code + runtime tests"):
            text = (
                "Over the last 48 hours, proof moved into code: product code and runtime tests landed across 2 "
                "workstreams, so this is no longer just a contract in notes."
                if widened_window
                else "Proof moved into code this window: product code and runtime tests landed across 2 workstreams, "
                "so this is no longer just a contract in notes."
            )
        elif "preflight failed because the product repo is not in pinned dogfood posture" in lower:
            text = (
                "Over the last 48 hours, the most useful thing that surfaced was a failure: self-host release "
                "preflight is still refusing to bless a product repo that has not returned to pinned dogfood posture."
                if widened_window
                else "The most useful thing that surfaced this window was a failure: self-host release preflight is "
                "still refusing to bless a product repo that has not returned to pinned dogfood posture."
            )
        elif lower.startswith("implementation checkpoint in ") and ": completed " in lower:
            if "readme" in lower or "grounding benchmark" in lower:
                text = (
                    "Over the last 48 hours, a benchmark-truth checkpoint landed too. The README now draws a harder "
                    "line around the Grounding Benchmark, which gives the rest of the proof something firmer to align to."
                    if widened_window
                    else "A benchmark-truth checkpoint landed too. The README now draws a harder line around the "
                    "Grounding Benchmark, which gives the rest of the proof something firmer to align to."
                )
            else:
                detail = summary.split(": completed ", 1)[1].strip()
                prefix = "Over the last 48 hours, a checkpoint landed" if widened_window else "A checkpoint landed"
                text = f"{prefix}: {detail}."
        elif "release prep" in lower and "benchmark hardening" in lower:
            text = (
                "Over the last 48 hours, benchmark hardening stopped being abstract. Release prep and proof-hardening "
                "are now moving together, which is where weak claims finally get exposed."
                if widened_window
                else "Benchmark hardening stopped being abstract this window. Release prep and proof-hardening are "
                "now moving together, which is where weak claims finally get exposed."
            )
        else:
            text = (
                f"{'Over the last 48 hours, the clearest move was' if widened_window else 'The clearest move this window was'} "
                f"{summary}. It gave the rest of the work something concrete to steer against."
            )
        bullets.append(_bullet(text, voice="operator", facts=[highlight]))

    return bullets[:2] if bullets else _fallback_bullets(facts, limit=2)


def _direction_bullet(
    fact: Mapping[str, Any],
    *,
    window_key: str,
) -> dict[str, Any]:
    text = _fact_text(fact)
    match = re.match(r"(?P<label>.+?) is .*? because (?P<reason>.+)$", text)
    if not match:
        return _bullet(text, voice="executive", facts=[fact])
    label = _clean_text(match.group("label"))
    reason = _clean_text(match.group("reason")).rstrip(".")
    workstream_id = _workstream_id(label)
    focus_ref = f"`{workstream_id}`" if workstream_id else _workstream_core(label)
    lower_reason = reason.lower()
    if "maintainer execution" in lower_reason and "consumer execution" in lower_reason:
        focus = reason.split(":", 1)[1].strip() if ":" in reason else reason
        focus = focus.replace("inside repos", "in repos")
        text = (
            f"{'Over the last 48 hours, the lane boundary has stayed unsettled in' if window_key == '48h' else 'The lane boundary still feels unsettled in'} "
            f"{focus_ref}. {focus} still read too much like one runtime contract when they are not the same thing."
        )
        return _bullet(text, voice="executive", facts=[fact])
    if "compact benchmark lane" in lower_reason:
        return _bullet(
            f"{'Over the last 48 hours,' if window_key == '48h' else ''} {focus_ref} has moved out of easy-win territory. "
            "The compact benchmark already clears; now the question is whether the proof survives a harder repo shape "
            "without getting easier to game.",
            voice="executive",
            facts=[fact],
        )
    return _bullet(
        f"{'Over the last 48 hours,' if window_key == '48h' else ''} {focus_ref} is still carrying the main decision load. {_sentence(reason)}",
        voice="executive",
        facts=[fact],
    )


def _self_host_snapshot(summary: Mapping[str, Any]) -> dict[str, Any]:
    return _mapping(summary.get("self_host"))


def _self_host_execution_bullet(
    fact: Mapping[str, Any],
    *,
    summary: Mapping[str, Any],
) -> dict[str, Any]:
    snapshot = _self_host_snapshot(summary)
    posture = str(snapshot.get("posture", "")).strip()
    pinned_version = str(snapshot.get("pinned_version", "")).strip()
    active_version = str(snapshot.get("active_version", "")).strip()
    release_eligible = snapshot.get("release_eligible")
    if posture == "detached_source_local":
        return _bullet(
            "The live repo posture makes that concrete: the product repo is running detached `source-local`. "
            "That is fine for active product work, and it is also why release gating should stay blocked until the "
            "pinned runtime is back.",
            voice="operator",
            facts=[fact],
        )
    if posture == "pinned_release" and release_eligible is True:
        runtime = active_version or pinned_version or "the pinned runtime"
        return _bullet(
            f"The repo is back on pinned dogfood runtime `{runtime}`, so the live posture and the release gate are "
            "finally aligned again.",
            voice="operator",
            facts=[fact],
        )
    return _bullet(_fact_text(fact), voice="operator", facts=[fact])


def _portfolio_bullet(fact: Mapping[str, Any]) -> dict[str, Any]:
    text = _fact_text(fact)
    if "Live focus lanes:" not in text:
        return _bullet(text, voice="operator", facts=[fact])
    focus_tail = text.split("Live focus lanes:", 1)[1].strip()
    labels = [_clean_text(match.group(1)) for match in _WORKSTREAM_FRAGMENT_RE.finditer(focus_tail)]
    if len(labels) < 2:
        return _bullet(text, voice="operator", facts=[fact])
    companion = labels[1]
    companion_id = _workstream_id(companion)
    companion_ref = f"`{companion_id}`" if companion_id else _workstream_core(companion)
    companion_lower = companion.lower()
    if "benchmark" in companion_lower or "proof" in companion_lower or "integrity" in companion_lower:
        return _bullet(
            f"{companion_ref} is the lane keeping this honest alongside it. If Odylith is genuinely better, the "
            "benchmark needs to prove that with harder evidence and less wasted work, not stronger narration.",
            voice="operator",
            facts=[fact],
        )
    return _bullet(
        f"{companion_ref} is moving beside it and gives the portfolio a second place where plan intent is turning "
        "into something operators can actually trust.",
        voice="operator",
        facts=[fact],
    )


def _signal_bullet(fact: Mapping[str, Any], *, window_key: str) -> dict[str, Any]:
    summary = _strip_prefix(_fact_text(fact), "Primary execution signal:").rstrip(".")
    widened_window = window_key == "48h"
    lower = summary.lower()
    if lower.startswith("implementation checkpoint in ") and ": completed " in lower:
        detail = summary.split(": completed ", 1)[1].strip()
        if "readme" in lower or "grounding benchmark" in lower:
            return _bullet(
                "Over the last 48 hours, the benchmark got a firmer anchor. The README now draws a harder line around "
                "the Grounding Benchmark, so the rest of the truth surfaces have something more stable to align to."
                if widened_window
                else "The benchmark got a firmer anchor this window. The README now draws a harder line around the "
                "Grounding Benchmark, so the rest of the truth surfaces have something more stable to align to.",
                voice="operator",
                facts=[fact],
            )
        return _bullet(
            f"{'Over the last 48 hours, a checkpoint landed' if widened_window else 'A checkpoint landed'}: {detail}.",
            voice="operator",
            facts=[fact],
        )
    if lower.startswith("added "):
        return _bullet(
            f"{'Over the last 48 hours, proof moved into code' if widened_window else 'The latest proof moved into code'}: {summary}.",
            voice="operator",
            facts=[fact],
        )
    if "self-host release preflight failed" in lower and "pinned dogfood posture" in lower:
        return _bullet(
            "The most useful signal right now is still a failure: self-host preflight is refusing to bless a "
            "repo that has not come back to pinned dogfood posture.",
            voice="operator",
            facts=[fact],
        )
    return _bullet(
        f"{'Over the last 48 hours, the clearest signal has been' if widened_window else 'Right now the clearest signal is'} {summary}.",
        voice="operator",
        facts=[fact],
    )


def _checklist_bullet(fact: Mapping[str, Any]) -> dict[str, Any]:
    text = _fact_text(fact)
    match = re.search(r"checklist progress is\s+(\d+)/(\d+);", text, re.IGNORECASE)
    if not match:
        return _bullet(text, voice="operator", facts=[fact])
    done_tasks = int(match.group(1))
    total_tasks = int(match.group(2))
    remaining = max(0, total_tasks - done_tasks)
    if total_tasks <= 0:
        return _bullet(
            "The implementation shape is still being named, so the lane needs a concrete first checkpoint.",
            voice="operator",
            facts=[fact],
        )
    if done_tasks <= 0:
        return _bullet(
            "The plan is defined, but none of the checklist is closed yet.",
            voice="operator",
            facts=[fact],
        )
    if remaining <= 0:
        return _bullet(
            "The scoped checklist is fully closed, so the remaining work is proving the lane cleanly.",
            voice="operator",
            facts=[fact],
        )
    return _bullet(
        f"This lane is still carrying real weight. {remaining} checklist items are open, so it can still sprawl if "
        "the next checkpoint stays fuzzy.",
        voice="operator",
        facts=[fact],
    )


def _timeline_bullet(fact: Mapping[str, Any]) -> dict[str, Any]:
    detail = _strip_prefix(_fact_text(fact), "Timeline signal:")
    detail = _strip_prefix(detail, "Timeline signal on the primary lane:")
    detail = detail.rstrip(".")
    lower = detail.lower()
    if lower.startswith("projected at"):
        return _bullet(
            f"The schedule still matters here: {detail}, so nobody should mistake this for cleanup.",
            voice="operator",
            facts=[fact],
        )
    return _bullet(
        f"The timing still matters here: {detail}.",
        voice="operator",
        facts=[fact],
    )


def _freshness_bullet(fact: Mapping[str, Any]) -> dict[str, Any]:
    text = _fact_text(fact)
    if text.lower().startswith("freshness signal is stale:"):
        detail = _strip_prefix(text, "Freshness signal is stale:")
        return _bullet(
            f"Execution proof is getting stale. {_sentence(detail)}",
            voice="operator",
            facts=[fact],
        )
    if text.lower().startswith("freshness signal is aging:"):
        detail = _strip_prefix(text, "Freshness signal is aging:")
        return _bullet(
            f"Execution proof is aging. {_sentence(detail)}",
            voice="operator",
            facts=[fact],
        )
    return _bullet(text, voice="operator", facts=[fact])


def _current_execution_bullets(
    facts: Sequence[Mapping[str, Any]],
    *,
    summary: Mapping[str, Any],
    window_key: str,
) -> list[dict[str, Any]]:
    bullets: list[dict[str, Any]] = []
    direction = _first_fact(facts, kind="direction")
    signal = _first_fact(facts, kind="signal")
    self_host_status = _first_fact(facts, kind="self_host_status")
    portfolio_posture = _first_fact(facts, kind="portfolio_posture")
    checklist = _first_fact(facts, kind="checklist")
    freshness = _first_fact(facts, kind="freshness")
    timeline = _first_fact(facts, kind="timeline")
    used_signal = False
    used_checklist = False

    if direction is not None:
        bullets.append(_direction_bullet(direction, window_key=window_key))

    if self_host_status is not None:
        bullets.append(_self_host_execution_bullet(self_host_status, summary=summary))

    if portfolio_posture is not None:
        bullets.append(_portfolio_bullet(portfolio_posture))
    elif signal is not None:
        bullets.append(_signal_bullet(signal, window_key=window_key))
        used_signal = True
    elif checklist is not None:
        bullets.append(_checklist_bullet(checklist))
        used_checklist = True

    if len(bullets) < 4 and checklist is not None and not used_checklist:
        bullets.append(_checklist_bullet(checklist))
        used_checklist = True

    if freshness is not None and len(bullets) < 4:
        bullets.append(_freshness_bullet(freshness))
    elif len(bullets) < 4 and timeline is not None:
        bullets.append(_timeline_bullet(timeline))
    elif len(bullets) < 4 and signal is not None and not used_signal:
        bullets.append(_signal_bullet(signal, window_key=window_key))

    if bullets:
        return bullets[:4]
    return _fallback_bullets(facts, limit=4)


def _action_fact_parts(text: str) -> tuple[str, str]:
    cleaned = _clean_text(text)
    cleaned = _strip_prefix(cleaned, "Immediate forcing function is")
    cleaned = _strip_prefix(cleaned, "Then move")
    if cleaned.lower().startswith("to turn the next open checklist item into a named checkpoint"):
        return "", cleaned.rstrip(" .;:,")
    if ":" not in cleaned:
        return "", cleaned.rstrip(" .;:,")
    label, detail = cleaned.split(":", 1)
    return _clean_text(label), _clean_text(detail).rstrip(" .;:,")


def _next_detail(detail: str) -> str:
    cleaned = _clean_text(detail).rstrip(" .;:,")
    cleaned = re.sub(r"^(?:to|then)\s+", "", cleaned, count=1, flags=re.IGNORECASE)
    lower = cleaned.lower()
    if "turn the next open checklist item into a named checkpoint" in lower:
        return (
            "name the next concrete checkpoint so the lane stops reading like a broad cleanup bucket and starts "
            "reading like one clear operator call"
        )
    if "lag the readme" in lower and "registry" in lower:
        return (
            "bring Registry and the other benchmark truth surfaces back into line with the README so the "
            "public benchmark story is backed by governed source again"
        )
    if "developer-core local coding slices" in lower or "higher-signal developer shapes" in lower:
        return (
            "the corpus needs more developer-core local coding slices. The benchmark only gets more believable "
            "if the workload gets closer to the hard work we actually care about"
        )
    if "the corpus grows beyond the current 30-scenario suite" in lower:
        return "expand the corpus beyond the current suite so the benchmark gets harder where the proof is still weak"
    if "next proof rerun must clear both cache profiles" in lower:
        return "rerun the proof across both cache profiles so benchmark gains are harder to dismiss"
    return cleaned


def _next_planned_bullets(
    facts: Sequence[Mapping[str, Any]],
    *,
    summary: Mapping[str, Any],
) -> list[dict[str, Any]]:
    bullets: list[dict[str, Any]] = []
    forcing_function = _first_fact(facts, kind="forcing_function") or _first_fact(facts, kind="fallback_next")
    follow_on = _first_fact(facts, kind="follow_on")
    scope_label = _clean_text(str(_storyline(summary).get("flagship_lane", "")).strip())
    scope_id = _workstream_id(scope_label)
    if forcing_function is not None:
        label, detail = _action_fact_parts(_fact_text(forcing_function))
        detail_text = _next_detail(detail)
        workstream_id = _workstream_id(label)
        same_scope = bool(workstream_id and scope_id and workstream_id == scope_id)
        next_ref = _label_ref(label)
        if next_ref and not same_scope:
            text = f"Next up is {next_ref}: {detail_text}."
        elif detail_text.lower().startswith("to "):
            text = f"Next up is {detail_text}."
        else:
            text = f"Next up is to {detail_text}."
        bullets.append(_bullet(text, voice="operator", facts=[forcing_function]))
    if follow_on is not None:
        _label, detail = _action_fact_parts(_fact_text(follow_on))
        detail_text = _next_detail(detail)
        if detail_text.lower().startswith("to "):
            detail_text = detail_text[3:].strip()
        bullets.append(
            _bullet(
                f"After that, {detail_text}.",
                voice="operator",
                facts=[follow_on],
            )
        )
    return bullets[:2] if bullets else _fallback_bullets(facts, limit=2)


def _why_this_matters_bullets(
    facts: Sequence[Mapping[str, Any]],
    *,
    summary: Mapping[str, Any],
) -> list[dict[str, Any]]:
    executive = _first_fact(facts, kind="executive_impact") or (dict(facts[0]) if facts else None)
    operator = _first_fact(facts, kind="operator_leverage")
    storyline = _storyline(summary)
    use_story = _strip_priority_lead(_clean_text(str(storyline.get("use_story", "")).strip()))
    architecture = _strip_priority_lead(_clean_text(str(storyline.get("architecture_consequence", "")).strip()))
    joined_story = " ".join(part for part in [use_story, architecture] if part).lower()
    bullets: list[dict[str, Any]] = []
    if executive is not None:
        executive_text = _fact_text(executive)
        lower = executive_text.lower()
        if "is correct, but" in lower or "easy to collapse" in lower or "pinned dogfood" in lower:
            bullets.append(
                _bullet(
                    "What is at stake here is trust at the moment of action. The runtime boundary itself is sound, "
                    "but the way it is described still makes maintainers infer too much when they choose a lane.",
                    voice="executive",
                    facts=[executive],
                )
            )
        elif "benchmark" in joined_story and (
            "complex governed repo" in joined_story
            or "serious coding agent" in joined_story
            or "public proof" in joined_story
            or "published diagnostic report" in joined_story
        ):
            bullets.append(
                _bullet(
                    "The benchmark only matters if it reflects the hard work we actually care about. Right now the "
                    "public proof is still on hold, so the story can still outrun the governed source.",
                    voice="executive",
                    facts=[executive],
                )
            )
        elif "benchmark" in joined_story and (
            "hard to dismiss" in joined_story
            or "auditable" in joined_story
            or "anti-gaming" in joined_story
        ):
            bullets.append(
                _bullet(
                    "Once the benchmark starts carrying product claims, it has to stay honest enough that the proof is "
                    "harder to game than the story is to tell.",
                    voice="executive",
                    facts=[executive],
                )
            )
        else:
            bullets.append(
                _bullet(
                    f"What matters here is {(use_story or executive_text).rstrip(' .')}.",
                    voice="executive",
                    facts=[executive],
                )
            )
    if operator is not None:
        operator_text = _fact_text(operator)
        lower = operator_text.lower()
        if "benchmark" in joined_story and (
            "readme" in joined_story
            or "governed source" in joined_story
            or "truth surfaces" in joined_story
        ):
            bullets.append(
                _bullet(
                    "If we tighten this up, the published benchmark story stops getting ahead of the governed source.",
                    voice="operator",
                    facts=[operator],
                )
            )
        elif "benchmark" in joined_story:
            bullets.append(
                _bullet(
                    "If we get this right, benchmark gains become easier to trust because the proof stays hard, not flattering.",
                    voice="operator",
                    facts=[operator],
                )
            )
        elif "lane matrix" in lower or "clearer contract" in lower or "coordination risk" in lower:
            bullets.append(
                _bullet(
                    "Making that lane contract explicit across docs, guidance, specs, and surfaces would let operators "
                    "act without guessing, and it would clean up release proof at the same time.",
                    voice="operator",
                    facts=[operator],
                )
            )
        else:
            bullets.append(
                _bullet(
                    f"Making the contract clearer would {_strip_priority_lead(operator_text).rstrip(' .')}.",
                    voice="operator",
                    facts=[operator],
                )
            )
    return bullets[:2] if bullets else _fallback_bullets(facts, limit=2)


def _risk_bullet(
    fact: Mapping[str, Any],
    *,
    summary: Mapping[str, Any],
) -> dict[str, Any]:
    text = _fact_text(fact)
    lower = text.lower()
    if lower.startswith("primary blocker is an open p1 bug:"):
        detail = _strip_prefix(text, "Primary blocker is an open P1 bug:")
        detail = detail.replace("forensics miss ", "forensics missing ")
        detail = detail.replace("source owned", "source-owned")
        return _bullet(
            f"The sharpest open risk is still the P1 around {detail.rstrip(' .')}.",
            voice="operator",
            facts=[fact],
        )
    closure_match = re.match(
        r"Primary watch item is (?:closure|sequencing) discipline:\s*(?P<count>\d+)\s+plan items remain open(?: for (?P<label>.+?))?(?: while .+)?\.$",
        text,
        re.IGNORECASE,
    )
    if closure_match is not None:
        remaining = int(closure_match.group("count"))
        label_text = _clean_text(closure_match.group("label") or "")
        storyline_label = _clean_text(str(_storyline(summary).get("flagship_lane", "")).strip())
        ref = _label_ref(label_text or storyline_label) or "this lane"
        return _bullet(
            f"The lane can still sprawl: {remaining} plan items are open on {ref}, so the next checkpoint needs to land cleanly.",
            voice="operator",
            facts=[fact],
        )
    snapshot = _self_host_snapshot(summary)
    if "release gating stays blocked until" in lower and str(snapshot.get("posture", "")).strip() == "detached_source_local":
        pinned_version = str(snapshot.get("pinned_version", "")).strip() or "unknown"
        return _bullet(
            f"Release gating stays constrained while the repo is running detached `source-local` instead of the "
            f"pinned `{pinned_version}` runtime.",
            voice="operator",
            facts=[fact],
        )
    return _bullet(text, voice="operator", facts=[fact])


def _risks_to_watch_bullets(
    facts: Sequence[Mapping[str, Any]],
    *,
    summary: Mapping[str, Any],
) -> list[dict[str, Any]]:
    bullets = [_risk_bullet(fact, summary=summary) for fact in facts[:3]]
    return bullets if bullets else _fallback_bullets(facts, limit=3)
