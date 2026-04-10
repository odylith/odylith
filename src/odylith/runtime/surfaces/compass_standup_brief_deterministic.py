"""Deterministic Compass standup brief helpers."""

from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

_WORKSTREAM_ID_RE = re.compile(r"\((B-\d+)\)")
_WORKSTREAM_LABEL_RE = re.compile(r"^(?P<label>.+?)\s*\((?P<id>B-\d+)\)\s*$")
_WORKSTREAM_FRAGMENT_RE = re.compile(r"([A-Z][^()]*?\(B-\d+\))")
_WORKSTREAM_COUNT_RE = re.compile(r"\b(\d+)\s+workstreams?\b", re.IGNORECASE)


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
    if section_key == "risks_to_watch":
        return _risks_to_watch_bullets(rows, summary=summary)
    return _fallback_bullets(rows, limit=2)


def _fact_id(fact: Mapping[str, Any]) -> str:
    return str(fact.get("id", "")).strip()


def _fact_text(fact: Mapping[str, Any]) -> str:
    return _clean_text(str(fact.get("text", "")).strip())


def _fact_kind(fact: Mapping[str, Any]) -> str:
    return str(fact.get("kind", "")).strip().lower()


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
    facts: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    fact_ids: list[str] = []
    for fact in facts:
        fact_id = _fact_id(fact)
        if fact_id and fact_id not in fact_ids:
            fact_ids.append(fact_id)
    return {
        "text": _clean_text(text),
        "fact_ids": fact_ids,
    }


def _storyline(summary: Mapping[str, Any]) -> dict[str, Any]:
    return _mapping(summary.get("storyline"))


def _compact_clause(text: str, *, max_words: int = 22) -> str:
    cleaned = _clean_text(text).rstrip(" .")
    if len(cleaned.split()) > max_words:
        cleaned = " ".join(cleaned.split()[:max_words]).rstrip(" ,;:")
    return _sentence(cleaned)


def _label_ref(label: str) -> str:
    workstream_id = _workstream_id(label)
    if workstream_id:
        return f"`{workstream_id}`"
    return _workstream_core(label)


def _join_workstream_refs(ids: Sequence[str]) -> str:
    refs = [f"`{str(token).strip()}`" for token in ids if str(token).strip()]
    if not refs:
        return ""
    if len(refs) == 1:
        return refs[0]
    if len(refs) == 2:
        return f"{refs[0]} and {refs[1]}"
    return f"{', '.join(refs[:-1])}, and {refs[-1]}"


def _workstream_count(text: str) -> int | None:
    match = _WORKSTREAM_COUNT_RE.search(_clean_text(text))
    if not match:
        return None
    return int(match.group(1))


def _workstream_count_phrase(count: int | None, *, fallback: str = "those workstreams") -> str:
    if count is None:
        return fallback
    suffix = "" if count == 1 else "s"
    return f"{count} workstream{suffix}"


def _first_fact(facts: Sequence[Mapping[str, Any]], *, kind: str) -> dict[str, Any] | None:
    kind_token = str(kind).strip().lower()
    return next((dict(fact) for fact in facts if _fact_kind(fact) == kind_token), None)


def _fallback_bullets(facts: Sequence[Mapping[str, Any]], *, limit: int) -> list[dict[str, Any]]:
    bullets: list[dict[str, Any]] = []
    for fact in facts[:limit]:
        bullets.append(
            _bullet(
                _fact_text(fact),
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


def _normalize_completion_core(core: str) -> str:
    cleaned = _clean_text(core).strip().lower()
    if not cleaned:
        return ""
    replacements = {
        "completed release members stay visible until explicit ga": "the rule that keeps completed release members visible until explicit GA",
        "current active release visibility until explicit ga": "the rule that keeps the current active release visible until explicit GA",
        "first-turn bootstrap and short-form grounding commands": "first-turn bootstrap and short grounding commands",
        "product self governance and repo boundary": "product self-governance and repo boundary",
    }
    if cleaned in replacements:
        return replacements[cleaned]
    cleaned = cleaned.replace(" explicit ga", " explicit GA")
    cleaned = cleaned.replace(" self governance ", " self-governance ")
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
        core = _normalize_completion_core(_workstream_core(label))
        if workstream_id and core:
            clauses.append(f"`{workstream_id}` finished {core}")
            seen_ids.add(workstream_id)
        elif core:
            clauses.append(f"{core} is done")
        if len(clauses) >= 2:
            break
    return clauses


def _completed_bullets(
    facts: Sequence[Mapping[str, Any]],
    *,
    window_key: str,
) -> list[dict[str, Any]]:
    bullets: list[dict[str, Any]] = []
    plan_completion = _first_fact(facts, kind="plan_completion")
    if plan_completion is not None:
        text = _fact_text(plan_completion)
        closeout_clauses = _completed_closeout_clauses(text)
        if closeout_clauses:
            bullets.append(
                _bullet(
                    f"{'; '.join(closeout_clauses)}.",
                    facts=[plan_completion],
                )
            )
        else:
            bullets.append(
                _bullet(
                    text,
                    facts=[plan_completion],
                )
            )

    highlight = _first_fact(facts, kind="execution_highlight")
    if highlight is not None:
        summary = _strip_prefix(_fact_text(highlight), "Most concrete portfolio movement:")
        summary = _strip_prefix(summary, "Most concrete movement:")
        summary = summary.rstrip(".")
        lower = summary.lower()
        workstream_count = _workstream_count(summary)
        if "lineage" in lower and "merge" in lower:
            text = (
                f"Lineage was merged back together across {_workstream_count_phrase(workstream_count)}. "
                "The plans and links match again."
                if window_key == "48h"
                else f"Lineage was merged back together across {_workstream_count_phrase(workstream_count)}. "
                "The plans and links line up again."
            )
        elif lower.startswith("added product code + runtime tests"):
            text = (
                f"Product code and runtime tests landed across {_workstream_count_phrase(workstream_count)}. "
                "It made it into the repo, not just the notes."
                if window_key == "48h"
                else f"Product code and runtime tests landed across {_workstream_count_phrase(workstream_count)}. "
                "It is in the repo now, not just the notes."
            )
        elif "preflight failed because the product repo is not in pinned dogfood posture" in lower:
            text = (
                "Self-host release preflight is still refusing to bless a product repo that has not returned to "
                "pinned dogfood posture."
            )
        elif lower.startswith("decision: scoped compass is fail-closed"):
            text = (
                "Scoped Compass is now fail-closed. If a workstream brief is missing, Compass says so instead of "
                "borrowing the global brief."
            )
        elif lower.startswith("decision: compass voice is a product invariant"):
            text = (
                "Compass voice is now treated as product behavior, not copy polish. Cached and fallback briefs do "
                "not get to slide back into stock framing."
            )
        elif lower.startswith("implementation checkpoint in ") and ": completed " in lower:
            if "readme" in lower or "grounding benchmark" in lower:
                text = (
                    "The README now draws a harder line around the Grounding Benchmark, which gives the rest of the "
                    "proof something firmer to align to."
                )
            else:
                detail = summary.split(": completed ", 1)[1].strip()
                text = f"{detail} is now complete."
        elif "release prep" in lower and "benchmark hardening" in lower:
            text = (
                "Release prep and benchmark hardening are now moving together, which is where weak claims finally get "
                "exposed."
            )
        elif lower.startswith("workstream lineage split update across "):
            text = f"{summary} landed. The surrounding plans and links now line up better."
        elif lower.startswith("workstream lineage reopen update across "):
            verb = "was" if workstream_count == 1 else "were"
            text = (
                f"{_workstream_count_phrase(workstream_count).capitalize()} {verb} reopened. "
                "The active lanes are visible again."
            )
        elif lower.startswith("updated product code + odylith artifacts"):
            text = "Product code and Odylith artifacts moved together this window."
        elif lower.startswith("updated odylith artifacts across "):
            text = "Odylith artifacts were refreshed alongside the code they describe."
        elif lower.startswith("prepare "):
            text = f"{summary[8:].strip()} is in place."
        else:
            text = f"{summary}."
        bullets.append(_bullet(text, facts=[highlight]))

    return bullets[:2] if bullets else _fallback_bullets(facts, limit=2)


def _direction_bullet(
    fact: Mapping[str, Any],
    *,
    window_key: str,
) -> dict[str, Any]:
    text = _fact_text(fact)
    match = re.match(r"(?P<label>.+?) is .*? because (?P<reason>.+)$", text)
    if not match:
        return _bullet(text, facts=[fact])
    label = _clean_text(match.group("label"))
    reason = _clean_text(match.group("reason")).rstrip(".")
    workstream_id = _workstream_id(label)
    focus_ref = f"`{workstream_id}`" if workstream_id else _workstream_core(label)
    lower_reason = reason.lower()
    if "maintainer execution" in lower_reason and "consumer execution" in lower_reason:
        focus = reason.split(":", 1)[1].strip() if ":" in reason else reason
        focus = focus.replace("inside repos", "in repos")
        text = (
            f"{focus_ref} is still blocked on lane boundary clarity. People still read {focus} like one runtime contract "
            "when they are not."
        )
        return _bullet(text, facts=[fact])
    if "compact benchmark lane" in lower_reason:
        return _bullet(
            f"{focus_ref} has moved out of easy-win territory. "
            "The compact benchmark already clears; now the question is whether the proof survives a harder repo shape "
            "without getting easier to game.",
            facts=[fact],
        )
    if "once the benchmark starts shaping product claims" in lower_reason:
        return _bullet(
            f"{focus_ref} is trying to make the benchmark hard to game. "
            "If it starts carrying product claims, it cannot quietly reshape itself to make those claims look better.",
            facts=[fact],
        )
    if "right time to process release feedback is right after the release" in lower_reason:
        return _bullet(
            f"{focus_ref} is working through release feedback while the evidence is still fresh. "
            "That is the moment to clean up the bad exceptions before they settle in.",
            facts=[fact],
        )
    if "cost of local heuristics" in lower_reason:
        return _bullet(
            f"{focus_ref} is trying to stop each surface from guessing scope importance on its own. "
            "Compass already showed how expensive that gets.",
            facts=[fact],
        )
    return _bullet(
        f"{focus_ref}: {_sentence(reason)}",
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
            "The product repo is still running detached `source-local`. Release gating should stay blocked until the pinned runtime is back.",
            facts=[fact],
        )
    if posture == "pinned_release" and release_eligible is True:
        runtime = active_version or pinned_version or "the pinned runtime"
        return _bullet(
            f"The product repo is on pinned dogfood runtime `{runtime}`. The release gate is using the same path "
            "maintainers are meant to use.",
            facts=[fact],
        )
    return _bullet(_fact_text(fact), facts=[fact])


def _portfolio_bullet(fact: Mapping[str, Any]) -> dict[str, Any]:
    text = _fact_text(fact)
    if "Live focus lanes:" not in text:
        return _bullet(text, facts=[fact])
    focus_tail = text.split("Live focus lanes:", 1)[1].strip()
    labels = [_clean_text(match.group(1)) for match in _WORKSTREAM_FRAGMENT_RE.finditer(focus_tail)]
    if len(labels) < 2:
        return _bullet(text, facts=[fact])
    primary = labels[0]
    primary_id = _workstream_id(primary)
    primary_ref = f"`{primary_id}`" if primary_id else _workstream_core(primary)
    companion = labels[1]
    companion_id = _workstream_id(companion)
    companion_ref = f"`{companion_id}`" if companion_id else _workstream_core(companion)
    companion_lower = companion.lower()
    if "benchmark" in companion_lower or "proof" in companion_lower or "integrity" in companion_lower:
        return _bullet(
            f"{companion_ref} is right beside {primary_ref}. The proof work is close enough to tell us whether those changes actually hold.",
            facts=[fact],
        )
    if "self-governance" in companion_lower or "repo boundary" in companion_lower:
        return _bullet(
            f"{companion_ref} is right beside {primary_ref} too. The repo-boundary cleanup is being finished in the same pass.",
            facts=[fact],
        )
    return _bullet(
        f"{primary_ref} and {companion_ref} are still moving together.",
        facts=[fact],
    )


def _window_coverage_bullet(fact: Mapping[str, Any]) -> dict[str, Any]:
    text = _fact_text(fact)
    if text.startswith("Most of the movement this window sat in "):
        tail = text.split("Most of the movement this window sat in ", 1)[1].rstrip(".")
        ids = re.findall(r"`?(B-\d+)`?", tail)
        if ids:
            joined = _join_workstream_refs(ids)
            return _bullet(f"This window mostly ran through {joined}.", facts=[fact])
        return _bullet(f"This window mostly ran through {tail}.", facts=[fact])
    if text.startswith("A lot moved in this window."):
        ids = re.findall(r"`?(B-\d+)`?", text)
        if ids:
            joined = _join_workstream_refs(ids)
            return _bullet(f"This window mostly ran through {joined}.", facts=[fact])
    return _bullet(text, facts=[fact])


def _signal_bullet(fact: Mapping[str, Any], *, window_key: str) -> dict[str, Any]:
    summary = _strip_prefix(_fact_text(fact), "Primary execution signal:").rstrip(".")
    lower = summary.lower()
    if lower.startswith("implementation checkpoint in ") and ": completed " in lower:
        detail = summary.split(": completed ", 1)[1].strip()
        if "readme" in lower or "grounding benchmark" in lower:
            return _bullet(
                "The benchmark got a firmer anchor. The README now draws a harder line around the Grounding "
                "Benchmark, so the rest of the truth surfaces have something more stable to align to.",
                facts=[fact],
            )
        return _bullet(
            f"{detail} is now complete.",
            facts=[fact],
        )
    if lower.startswith("added "):
        return _bullet(
            f"{summary} moved proof into code.",
            facts=[fact],
        )
    if "self-host release preflight failed" in lower and "pinned dogfood posture" in lower:
        return _bullet(
            "The most useful signal right now is still a failure: self-host preflight is refusing to bless a "
            "repo that has not come back to pinned dogfood posture.",
            facts=[fact],
        )
    return _bullet(
        f"{summary} still reads the same when you widen the window to 48h." if window_key == "48h" else _sentence(summary),
        facts=[fact],
    )


def _checklist_bullet(fact: Mapping[str, Any]) -> dict[str, Any]:
    text = _fact_text(fact)
    match = re.search(r"checklist progress is\s+(\d+)/(\d+);", text, re.IGNORECASE)
    if not match:
        return _bullet(text, facts=[fact])
    done_tasks = int(match.group(1))
    total_tasks = int(match.group(2))
    remaining = max(0, total_tasks - done_tasks)
    if total_tasks <= 0:
        return _bullet(
            "The lane still needs a first concrete checkpoint.",
            facts=[fact],
        )
    if done_tasks <= 0:
        return _bullet(
            "The plan is there, but the first checklist item is still open.",
            facts=[fact],
        )
    if remaining <= 0:
        return _bullet(
            "The scoped checklist is fully closed, so the remaining work is proving the lane cleanly.",
            facts=[fact],
        )
    return _bullet(
        f"{remaining} checklist items are still open.",
        facts=[fact],
    )


def _timeline_bullet(fact: Mapping[str, Any]) -> dict[str, Any]:
    detail = _strip_prefix(_fact_text(fact), "Timeline signal:")
    detail = _strip_prefix(detail, "Timeline signal on the primary lane:")
    detail = detail.rstrip(".")
    lower = detail.lower()
    if lower.startswith("projected at"):
        return _bullet(_sentence(detail), facts=[fact])
    return _bullet(_sentence(detail), facts=[fact])


def _freshness_bullet(fact: Mapping[str, Any]) -> dict[str, Any]:
    text = _fact_text(fact)
    if text.lower().startswith("freshness signal is stale:"):
        detail = _strip_prefix(text, "Freshness signal is stale:")
        return _bullet(_sentence(detail), facts=[fact])
    if text.lower().startswith("freshness signal is aging:"):
        detail = _strip_prefix(text, "Freshness signal is aging:")
        return _bullet(_sentence(detail), facts=[fact])
    return _bullet(text, facts=[fact])


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
    window_coverage = _first_fact(facts, kind="window_coverage")
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
    if window_coverage is not None and len(bullets) < 4:
        bullets.append(_window_coverage_bullet(window_coverage))
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
        detail_tail = re.sub(
            r"^turn\s+the\s+next\s+open\s+checklist\s+item\s+into\s+a\s+named\s+checkpoint(?:\s+for\s+.+?)?\s+so\s+",
            "",
            cleaned,
            count=1,
            flags=re.IGNORECASE,
        ).rstrip(" .;:,")
        if detail_tail != cleaned.rstrip(" .;:,"):
            lower_tail = detail_tail.lower()
            if "maintainer execution" in lower_tail and "consumer execution" in lower_tail:
                return (
                    "the next open checklist item still needs a name so the lane boundary stops blurring "
                    "maintainer and consumer execution"
                )
            if len(detail_tail.split()) > 18:
                detail_tail = " ".join(detail_tail.split()[:18]).rstrip(" ,;:")
            return f"the next open checklist item still needs a name so {detail_tail}"
        return "the next open checklist item still needs a name"
    if "lag the readme" in lower and "registry" in lower:
        return (
            "bring Registry and the other benchmark truth surfaces back into line with the README so the "
            "benchmark story stops drifting across surfaces"
        )
    if lower.startswith("bring registry, radar, atlas, compass, and the benchmark docs back into"):
        return (
            "bring Registry, Radar, Atlas, Compass, and the benchmark docs back into line with each other so the "
            "benchmark story stops drifting across surfaces"
        )
    if "developer-core local coding slices" in lower or "higher-signal developer shapes" in lower:
        return (
            "the corpus still needs more real maintainer coding work in it. Otherwise the benchmark gets cleaner "
            "without saying much about the work people actually do"
        )
    if "tracked corpus" in lower and "cli contract" in lower:
        return "the corpus also needs more real maintainer coding work, starting with the CLI contract"
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
            text = (
                f"{next_ref} now needs {detail_text}."
                if detail_text.lower().startswith("the ")
                else f"{next_ref} now needs to {detail_text}."
            )
        else:
            text = _sentence(detail_text)
        bullets.append(_bullet(text, facts=[forcing_function]))
    if follow_on is not None:
        _label, detail = _action_fact_parts(_fact_text(follow_on))
        detail_text = _next_detail(detail)
        bullets.append(
            _bullet(
                _sentence(detail_text[3:].strip() if detail_text.lower().startswith("to ") else detail_text),
                facts=[follow_on],
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
    blocker_match = re.match(r"Primary blocker is an open\s+(P\d+)\s+bug:\s*(?P<detail>.+)$", text, re.IGNORECASE)
    if blocker_match is not None:
        severity = str(blocker_match.group(1)).upper()
        detail = _clean_text(str(blocker_match.group("detail")).strip())
        detail = detail.replace("forensics miss ", "forensics missing ")
        detail = detail.replace("source owned", "source-owned")
        detail = detail.replace("mid corpus", "mid-corpus")
        detail = detail.replace("can wedge ", "wedging ")
        detail = detail.replace("and block ", "and blocking ")
        return _bullet(
            f"The sharpest open risk is still the {severity} around {detail.rstrip(' .')}.",
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
            f"{remaining} plan items remain open on {ref}.",
            facts=[fact],
        )
    if lower.startswith("primary watch item is execution coherence across "):
        labels = [_clean_text(match.group(1)) for match in _WORKSTREAM_FRAGMENT_RE.finditer(text)]
        left_ref = _label_ref(labels[0]) if len(labels) >= 1 else ""
        right_ref = _label_ref(labels[1]) if len(labels) >= 2 else ""
        if left_ref and right_ref:
            return _bullet(
                f"{left_ref} and {right_ref} still need to move in step. If they drift, the proof gets cleaner faster than it gets more trustworthy.",
                facts=[fact],
            )
    snapshot = _self_host_snapshot(summary)
    if "release gating stays blocked until" in lower and str(snapshot.get("posture", "")).strip() == "detached_source_local":
        pinned_version = str(snapshot.get("pinned_version", "")).strip() or "unknown"
        return _bullet(
            f"Release gating stays constrained while the repo is running detached `source-local` instead of the "
            f"pinned `{pinned_version}` runtime.",
            facts=[fact],
        )
    return _bullet(text, facts=[fact])


def _risks_to_watch_bullets(
    facts: Sequence[Mapping[str, Any]],
    *,
    summary: Mapping[str, Any],
) -> list[dict[str, Any]]:
    bullets = [_risk_bullet(fact, summary=summary) for fact in facts[:3]]
    return bullets if bullets else _fallback_bullets(facts, limit=3)
