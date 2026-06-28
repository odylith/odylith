"""Quality checks for accepted-greenfield Project implementation prompts."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from odylith.runtime.artifact_quality.greenfield_rendered_artifacts import RenderedArtifact
from odylith.runtime.common.value_coercion import normalize_string
from odylith.runtime.domain_intelligence.greenfield_text import visible_words


_PROJECT_PROMPT_REQUIRED_FIELDS = ("label", "when", "prompt", "result", "stop")
_PROJECT_PROMPT_STALE_LABELS = frozenset(
    {
        "accept it",
        "implement first coding slice",
        "pause",
        "reject it",
        "revise it",
        "revise project direction",
        "start implementation plan",
    }
)
_PROJECT_PROMPT_GENERIC_PHRASES = (
    "change <what is wrong>",
    "refresh this dashboard",
    "open the first implementation plan",
    "implement the first coding slice",
)


def project_implementation_prompt_issues(artifact: RenderedArtifact) -> list[str]:
    """Return hard-gate issues for Project tab implementation handoff prompts."""

    if artifact.surface != "Project implementation prompt":
        return []
    fields = {key: normalize_string(value) for key, value in dict(artifact.fields).items()}
    issues: list[str] = []
    missing = [key for key in _PROJECT_PROMPT_REQUIRED_FIELDS if not fields.get(key)]
    if missing:
        issues.append(f"{artifact.identity} is missing prompt fields: {', '.join(missing)}")
    label = fields.get("label", "")
    label_key = label.casefold().strip()
    if label_key in _PROJECT_PROMPT_STALE_LABELS:
        issues.append(f"{artifact.identity} uses stale generic handoff prompt label")
    prompt = fields.get("prompt", "")
    stop = fields.get("stop", "")
    result = fields.get("result", "")
    combined = " ".join(value for value in (label, prompt, stop, result, fields.get("when", "")) if value)
    lowered = combined.casefold()
    if len(visible_words(prompt)) < 24:
        issues.append(f"{artifact.identity} has a shallow implementation prompt")
    if "<" in combined and ">" in combined:
        issues.append(f"{artifact.identity} contains unresolved placeholder copy")
    for phrase in _PROJECT_PROMPT_GENERIC_PHRASES:
        if phrase in lowered:
            issues.append(f"{artifact.identity} uses generic handoff copy `{phrase}`")
    if "accepted" not in lowered:
        issues.append(f"{artifact.identity} does not anchor to accepted product direction")
    if "stop" not in stop.casefold() and "do not" not in stop.casefold():
        issues.append(f"{artifact.identity} stop condition is not explicit enough")
    if _has_gerund_actor_drift(combined):
        issues.append(f"{artifact.identity} has gerundized actor or product-subject drift")
    issues.extend(_source_launch_prompt_scope_issues(artifact, fields))
    return issues


def _source_launch_prompt_scope_issues(artifact: RenderedArtifact, fields: Mapping[str, str]) -> list[str]:
    position = _prompt_position(fields)
    prompt = fields.get("prompt", "").casefold()
    stop = fields.get("stop", "").casefold()
    result = fields.get("result", "").casefold()
    combined = " ".join((prompt, stop, result))
    issues: list[str] = []
    if position == 1 and not _contains_all(combined, ("runtime", "test")):
        issues.append(f"{artifact.identity} does not make language/runtime/test tradeoffs explicit")
    if position == 2:
        if "governed target" not in combined and "governed workstream" not in combined:
            issues.append(f"{artifact.identity} does not bind the plan to a governed workstream")
        if not _contains_all(combined, ("source boundary", "files", "proof")):
            issues.append(f"{artifact.identity} does not require source boundary, files, and proof gates")
        if "validation" not in combined and "test commands" not in combined:
            issues.append(f"{artifact.identity} does not require validation commands")
        if "excluded" not in combined:
            issues.append(f"{artifact.identity} does not preserve excluded scope")
    if position == 3:
        if "governed workstream" not in combined:
            issues.append(f"{artifact.identity} does not bind implementation to a governed workstream")
        if not _contains_all(combined, ("target files", "build only", "input validation", "structured result")):
            issues.append(f"{artifact.identity} does not bound the implementation slice tightly")
        if "risk" not in combined or ("outside the slice" not in combined and "excluded" not in combined):
            issues.append(f"{artifact.identity} does not carry risk and excluded-scope controls")
    if position == 4:
        if "governed workstream" not in combined:
            issues.append(f"{artifact.identity} does not bind proof to a governed workstream")
        if not _contains_all(combined, ("valid input", "missing", "validation")):
            issues.append(f"{artifact.identity} does not require valid, missing-input, and validation proof")
        if "fails" not in stop:
            issues.append(f"{artifact.identity} does not stop on failed validation")
    if position == 5:
        if "governed workstream" not in combined:
            issues.append(f"{artifact.identity} does not bind refresh to a governed workstream")
        if "governed records" not in combined or "implemented behavior" not in combined:
            issues.append(f"{artifact.identity} does not bind governance refresh to implemented behavior")
        if "release readiness" not in stop:
            issues.append(f"{artifact.identity} can imply release readiness without source proof")
    return issues


def _prompt_position(fields: Mapping[str, str]) -> int:
    raw = fields.get("position", "")
    try:
        return int(raw)
    except ValueError:
        return 0


def _contains_all(value: str, terms: Sequence[str]) -> bool:
    return all(term in value for term in terms)


_ACTOR_OR_PRODUCT_SUBJECT_MARKERS = frozenset(
    {
        "analyst",
        "coordinator",
        "desk",
        "lead",
        "manager",
        "operator",
        "owner",
        "participant",
        "reviewer",
        "service",
        "system",
        "team",
        "user",
        "workspace",
    }
)


def _has_gerund_actor_drift(value: str) -> bool:
    segments = _proof_action_segments(value)
    return any(_segment_has_gerund_actor_drift(segment) for segment in segments)


def _proof_action_segments(value: str) -> tuple[str, ...]:
    text = normalize_string(value)
    lowered = text.casefold()
    segments: list[str] = []
    for marker in ("proof gates for", "evidence covering", "covering"):
        start = lowered.find(marker)
        if start >= 0:
            segments.append(_bounded_proof_action_segment(text[start + len(marker) :]))
    return tuple(segments)


def _bounded_proof_action_segment(value: str) -> str:
    text = normalize_string(value)
    lowered = text.casefold()
    end = len(text)
    for marker in (
        ", and excluded scope:",
        ". governed target:",
        ". coding-readiness",
        ". validation commands",
        ".",
    ):
        index = lowered.find(marker)
        if index >= 0:
            end = min(end, index)
    return text[:end]


def _segment_has_gerund_actor_drift(value: str) -> bool:
    raw_words = [word.strip("'") for word in visible_words(value)]
    words = [word.casefold() for word in raw_words]
    for index, word in enumerate(words):
        raw_word = raw_words[index]
        if len(word) < 7 or not word.endswith("ing"):
            continue
        if raw_word[:1] and not raw_word[:1].islower():
            continue
        window = words[index + 1 : index + 6]
        for marker_offset, token in enumerate(window):
            if token not in _ACTOR_OR_PRODUCT_SUBJECT_MARKERS:
                continue
            tail_index = index + marker_offset + 2
            if tail_index < len(words) and _looks_like_finite_prompt_verb(words[tail_index]):
                return True
    return False


def _looks_like_finite_prompt_verb(value: str) -> bool:
    word = value.casefold().strip("'")
    if word in {"has", "is", "needs", "owns", "reads", "sees", "uses"}:
        return True
    return len(word) > 3 and word.endswith(("ed", "es", "s"))


__all__ = ["project_implementation_prompt_issues"]
