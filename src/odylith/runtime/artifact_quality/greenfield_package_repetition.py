"""Structured repetition findings for rendered greenfield packages."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any

from odylith.runtime.artifact_quality.greenfield_rendered_artifacts import RenderedArtifact
from odylith.runtime.artifact_quality.greenfield_rendered_artifacts import RenderedPackageQualityFinding
from odylith.runtime.artifact_quality.greenfield_rendered_artifacts import package_mapping as _as_mapping
from odylith.runtime.artifact_quality.greenfield_rendered_artifacts import package_quality_finding
from odylith.runtime.common.value_coercion import normalize_string
from odylith.runtime.domain_intelligence.greenfield_artifact_plan import artifact_plan_source_address_for_path
from odylith.runtime.domain_intelligence.greenfield_canonical_projection_facts import CanonicalProjectionFact
from odylith.runtime.domain_intelligence.greenfield_canonical_projection_facts import canonical_projection_facts
from odylith.runtime.domain_intelligence.greenfield_text import clip_text_at_word_boundary
from odylith.runtime.domain_intelligence.greenfield_text import text_values


_REPETITION_MIN_WORDS = 9
_REPETITION_MIN_CHARS = 68
_CODE = "package_repetition"


def package_repetition_quality_findings(
    package: Any,
    artifacts: Sequence[RenderedArtifact],
) -> list[RenderedPackageQualityFinding]:
    """Return source-owned package repetition findings with occurrence evidence."""

    generic_allowed, canonical_allowed = _allowed_repetition_keys(package)
    occurrences: dict[str, list[tuple[RenderedArtifact, str]]] = {}
    for artifact in artifacts:
        chunks = mermaid_label_chunks(artifact.text) if artifact.kind == "mermaid" else repetition_chunks(artifact.text)
        _record_repetition_chunks(occurrences, artifact, chunks, sentence_key, generic_allowed, canonical_allowed)
        if artifact.kind != "mermaid":
            _record_repetition_chunks(
                occurrences,
                artifact,
                markdown_section_body_chunks(artifact.text),
                repetition_key,
                generic_allowed,
                canonical_allowed,
            )
    findings: list[RenderedPackageQualityFinding] = []
    emitted_sample_keys: set[str] = set()
    for rows in occurrences.values():
        artifact_keys = tuple(dict.fromkeys((artifact.repair_path, artifact.identity) for artifact, _chunk in rows))
        if len(artifact_keys) < 3 and not (len(artifact_keys) == 1 and len(rows) >= 4):
            continue
        sample = rows[0][1]
        sample_key = repetition_key(_section_body_for_repetition(sample) or sample)
        if sample_key in emitted_sample_keys:
            continue
        if sample_key:
            emitted_sample_keys.add(sample_key)
        paths = tuple(dict.fromkeys(artifact.repair_path for artifact, _chunk in rows))
        projections = tuple(dict.fromkeys(artifact.projection_id for artifact, _chunk in rows))
        surfaces = tuple(dict.fromkeys(artifact.surface for artifact, _chunk in rows))
        projection = projections[0] if len(projections) == 1 else "artifact_draft_set"
        target_path = _single_projection_target(projection)
        repairability = "plan_patch" if artifact_plan_source_address_for_path(target_path) else "unrepairable"
        findings.append(
            package_quality_finding(
                "greenfield rendered package repeats noncanonical prose across "
                f"{len(artifact_keys)} artifact(s) and {len(rows)} occurrence(s): `{_clip(sample, 140)}`",
                projection_id=projection,
                target_path=target_path or "prewrite_package.package.copy_quality",
                code=_CODE,
                surface=projection if projection != "artifact_draft_set" else "post_confirm_package",
                semantic_node_id=_semantic_node_id(projection),
                severity="medium",
                repairability=repairability,
                owner=_owner(projection),
                source="package_repetition_quality",
                sample=sample,
                occurrence_count=len(rows),
                artifact_count=len(artifact_keys),
                occurrence_paths=paths,
                occurrence_projections=projections,
                occurrence_surfaces=surfaces,
            )
        )
    return findings


def _record_repetition_chunks(
    occurrences: dict[str, list[tuple[RenderedArtifact, str]]],
    artifact: RenderedArtifact,
    chunks: Sequence[str],
    key_fn: Any,
    generic_allowed: set[str],
    canonical_allowed: Mapping[str, tuple[CanonicalProjectionFact, ...]],
) -> None:
    for chunk in chunks:
        key = key_fn(chunk)
        if (
            key
            and not _allowed_repetition_chunk(chunk, key, generic_allowed, canonical_allowed, artifact)
            and not _allowed_structured_repetition_key(key)
        ):
            occurrences.setdefault(key, []).append((artifact, normalize_string(chunk)))


def _single_projection_target(projection: str) -> str:
    return {
        "atlas": "diagrams",
        "program": "program",
        "project_brief": "project_brief",
        "radar": "backlog",
        "registry": "components",
        "release": "release_plan",
    }.get(projection, "")


def _semantic_node_id(projection: str) -> str:
    return f"ArtifactPlanIR.{projection}" if projection and projection != "artifact_draft_set" else "ArtifactDraftSet.package"


def _owner(projection: str) -> str:
    return {
        "atlas": "atlas_renderer",
        "program": "program_planner",
        "project_brief": "project_brief_projector",
        "radar": "radar_projector",
        "registry": "registry_renderer",
        "release": "release_planner",
    }.get(projection, "typed_package_artifact_gate")


def _allowed_structured_repetition_key(key: str) -> bool:
    return key.startswith(
        (
            "boundary ",
            "control ",
            "customer ",
            "evidence ",
            "evidence contents ",
            "evidence record ",
            "gate ",
            "owner ",
            "proof ",
            "question ",
            "readiness gate ",
            "release wave ",
            "recovery gate ",
            "review condition ",
            "risk ",
            "scope gate ",
            "state object ",
            "state gate ",
            "trace requirement ",
            "validation gate ",
        )
    )


def _allowed_repetition_chunk(
    chunk: str,
    key: str,
    generic_allowed: set[str],
    canonical_allowed: Mapping[str, tuple[CanonicalProjectionFact, ...]],
    artifact: RenderedArtifact,
) -> bool:
    if key in generic_allowed or _canonical_repetition_allowed(key, canonical_allowed, artifact):
        return True
    body = _section_body_for_repetition(chunk)
    if not body:
        return False
    body_key = repetition_key(body)
    return bool(
        body_key
        and (
            body_key in generic_allowed
            or _canonical_repetition_allowed(body_key, canonical_allowed, artifact)
        )
    )


def _canonical_repetition_allowed(
    key: str,
    canonical_allowed: Mapping[str, tuple[CanonicalProjectionFact, ...]],
    artifact: RenderedArtifact,
) -> bool:
    for fact in canonical_allowed.get(key, ()):
        if artifact.projection_id in fact.allowed_projection_ids:
            return True
    return False


def _section_body_for_repetition(chunk: str) -> str:
    head, separator, body = normalize_string(chunk).partition(":")
    if not separator:
        return ""
    if not 1 <= len(word_tokens(head)) <= 5:
        return ""
    return body.strip(" .;-")


def _allowed_repetition_keys(package: Any) -> tuple[set[str], dict[str, tuple[CanonicalProjectionFact, ...]]]:
    proposal = _as_mapping(getattr(package, "proposal", None))
    intent = _as_mapping(proposal.get("intent"))
    semantic_model = _as_mapping(proposal.get("semantic_model"))
    first_path = _as_mapping(semantic_model.get("first_path_contract"))
    component_rows = proposal.get("components", [])
    component_sequence = component_rows if isinstance(component_rows, Sequence) and not isinstance(component_rows, str) else []
    components = [row for row in component_sequence if isinstance(row, Mapping)]
    values = [
        intent.get("title"),
        _actor_label_summary(text_values(intent.get("human_actors"))),
        *_semantic_label_repetition_values(first_path),
        *[
            f"{component.get('component_id', '')} {component.get('label', '')}"
            for component in components
            if normalize_string(component.get("component_id")) and normalize_string(component.get("label"))
        ],
        *[component.get("label") for component in components if normalize_string(component.get("label"))],
    ]
    keys: set[str] = set()
    for value in values:
        for chunk in repetition_chunks(str(value or "")):
            key = repetition_key(chunk)
            if key:
                keys.add(key)
    return keys, _canonical_repetition_keys(proposal)


def package_repetition_sample_matches_source_truth(package: Any, sample: str) -> bool:
    """Return whether a repeated package sample is accepted source-truth copy."""

    sample_text = normalize_string(sample)
    sample_key = repetition_key(sample_text)
    if not sample_text or not sample_key:
        return False
    proposal = _as_mapping(getattr(package, "proposal", None))
    for value in _source_truth_repetition_values(proposal):
        value_text = normalize_string(value)
        if not value_text:
            continue
        if sample_text.casefold() in value_text.casefold() or value_text.casefold() in sample_text.casefold():
            return True
        for chunk in repetition_chunks(value_text):
            if repetition_key(chunk) == sample_key:
                return True
    return False


def _source_truth_repetition_values(proposal: Mapping[str, Any]) -> list[str]:
    intent = _as_mapping(proposal.get("intent"))
    project_brief = _as_mapping(proposal.get("project_brief"))
    values: list[str] = []
    for source in (intent, project_brief):
        for key in (
            "first_path",
            "problem",
            "product_story",
            "product_view",
            "project_outcome",
            "proof_boundary",
            "purpose",
            "state_object",
        ):
            values.append(normalize_string(source.get(key)))
    values.extend(text_values(intent.get("assumptions")))
    values.extend(text_values(intent.get("success_metrics")))
    return [value for value in values if value]


def _canonical_repetition_keys(proposal: Mapping[str, Any]) -> dict[str, tuple[CanonicalProjectionFact, ...]]:
    rows: dict[str, list[CanonicalProjectionFact]] = {}
    for fact in canonical_projection_facts(proposal):
        for chunk in repetition_chunks(fact.text):
            key = repetition_key(chunk)
            if key:
                rows.setdefault(key, []).append(fact)
    return {key: tuple(facts) for key, facts in rows.items()}


def _semantic_label_repetition_values(first_path: Mapping[str, Any]) -> list[str]:
    short_values = [
        normalize_string(first_path.get("capability")),
        normalize_string(first_path.get("visible_result")),
    ]
    event_values: list[str] = []
    events = first_path.get("events")
    if isinstance(events, Sequence) and not isinstance(events, (str, bytes, bytearray)):
        for item in events:
            if not isinstance(item, Mapping):
                continue
            event_values.append(normalize_string(item.get("text") or item.get("mutation")))
            short_values.append(normalize_string(item.get("target_entity")))
    return [
        *[value for value in short_values if value and len(word_tokens(value)) <= 10],
        *[value for value in event_values if value],
    ]


def _actor_label_summary(values: list[str]) -> str:
    labels = []
    for value in values:
        label = normalize_string(value)
        for separator in (" - ", " -- ", f" {chr(8212)} ", ":"):
            label = label.split(separator, 1)[0]
        label = label.strip(" .")
        if label:
            labels.append(label)
    return ", ".join(labels[:4])


def repetition_chunks(value: str) -> list[str]:
    chunks: list[str] = []
    current: list[str] = []
    in_code_fence = False
    for raw_line in str(value or "").splitlines():
        line = raw_line.strip()
        if line.startswith("```"):
            in_code_fence = not in_code_fence
            continue
        if in_code_fence or skip_narrative_line(line):
            continue
        for index, char in enumerate(line):
            if is_sentence_boundary_char(line, index):
                append_chunk(chunks, current)
                current = []
            else:
                current.append(char)
        append_chunk(chunks, current)
        current = []
    return chunks


def markdown_section_body_chunks(value: str) -> list[str]:
    chunks: list[str] = []
    section = ""
    for raw_line in str(value or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("## "):
            section = line.lstrip("#").strip()
            continue
        if not section or line.startswith("#") or line.startswith("|") or line.startswith("```"):
            continue
        body = markdown_bullet_body(line) or line.strip(" -*")
        body = normalize_string(body).strip()
        if body:
            chunks.append(f"{section}: {body}")
        section = ""
    return chunks


def mermaid_label_chunks(value: str, *, chunker: Callable[[str], list[str]] = repetition_chunks) -> list[str]:
    labels: list[str] = []
    for raw_line in str(value or "").splitlines():
        line = raw_line.strip()
        if not line or skip_mermaid_line(line):
            continue
        labels.extend(_quoted_labels(line))
        participant_label = _participant_label(line)
        if participant_label:
            labels.append(participant_label)
    chunks: list[str] = []
    for label in labels:
        normalized = label.replace("<br/>", " ").replace("<br>", " ")
        chunks.extend(chunker(normalized))
    return chunks


def skip_narrative_line(line: str) -> bool:
    if not line:
        return True
    if line.startswith("|") or line.startswith("```"):
        return True
    if line.startswith("<!--") or line.startswith("::"):
        return True
    if line.endswith(":") and "_" in line:
        return True
    return _looks_like_governance_metadata_line(line)


def skip_mermaid_line(line: str) -> bool:
    lowered = line.casefold()
    return bool(
        lowered.startswith("%%")
        or lowered.startswith("flowchart ")
        or lowered.startswith("graph ")
        or lowered.startswith("sequencediagram")
        or lowered.startswith("class ")
        or lowered.startswith("classdef ")
        or lowered.startswith("style ")
        or lowered.startswith("linkstyle ")
        or lowered.startswith("subgraph ")
        or lowered == "end"
    )


def append_chunk(chunks: list[str], chars: list[str]) -> None:
    text = normalize_string("".join(chars)).strip(" -#*_`|")
    if len(word_tokens(text)) >= 2:
        chunks.append(text)


def is_sentence_boundary_char(line: str, index: int) -> bool:
    char = line[index] if 0 <= index < len(line) else ""
    if char in "?!\n\r":
        return True
    if char != ".":
        return False
    previous_char = line[index - 1] if index > 0 else ""
    next_char = line[index + 1] if index + 1 < len(line) else ""
    return not (previous_char.isdigit() and next_char.isdigit())


def word_tokens(value: str) -> list[str]:
    tokens: list[str] = []
    current: list[str] = []
    for char in str(value or ""):
        if char.isalnum() or char in {"'", "-"}:
            current.append(char)
            continue
        if current:
            tokens.append("".join(current).strip("-'"))
            current = []
    if current:
        tokens.append("".join(current).strip("-'"))
    return [token for token in tokens if token]


def markdown_bullet_body(value: str) -> str:
    text = str(value or "").strip()
    if text.startswith(("- ", "* ")):
        return normalize_string(text[2:])
    if len(text) > 3 and text[0].isdigit():
        index = 1
        while index < len(text) and text[index].isdigit():
            index += 1
        if index < len(text) - 1 and text[index] in {".", ")"} and text[index + 1] == " ":
            return normalize_string(text[index + 2 :])
    return ""


def sentence_key(value: str) -> str:
    tokens = [token.casefold() for token in word_tokens(value)]
    if len(tokens) < _REPETITION_MIN_WORDS:
        return ""
    key = " ".join(tokens)
    return key if len(key) >= _REPETITION_MIN_CHARS else ""


def repetition_key(value: str) -> str:
    sentence = sentence_key(value)
    if sentence:
        return sentence
    tokens = [token.casefold() for token in word_tokens(value)]
    if len(tokens) < 5:
        return ""
    key = " ".join(tokens)
    return key if len(key) >= 36 else ""


def _quoted_labels(line: str) -> list[str]:
    labels: list[str] = []
    index = 0
    while index < len(line):
        start = line.find('["', index)
        if start < 0:
            break
        label_start = start + 2
        end = line.find('"]', label_start)
        if end < 0:
            break
        labels.append(line[label_start:end])
        index = end + 2
    return labels


def _participant_label(line: str) -> str:
    prefix = "participant "
    marker = " as "
    lowered = line.casefold()
    if not lowered.startswith(prefix) or marker not in lowered:
        return ""
    marker_index = lowered.find(marker)
    return normalize_string(line[marker_index + len(marker) :])


def _looks_like_governance_metadata_line(value: str) -> bool:
    key, separator, _body = str(value or "").partition(":")
    if not separator:
        return False
    token = key.strip()
    if not token or len(token) > 48:
        return False
    return all(char.islower() or char.isdigit() or char == "_" for char in token)


def _clip(value: str, limit: int) -> str:
    source = normalize_string(value)
    text = clip_text_at_word_boundary(source, limit=limit, strip_edges=" ,;:.")
    return text if len(source) <= limit else text.rstrip(" ,;:.") + "..."


__all__ = [
    "append_chunk",
    "is_sentence_boundary_char",
    "markdown_bullet_body",
    "markdown_section_body_chunks",
    "mermaid_label_chunks",
    "package_repetition_sample_matches_source_truth",
    "package_repetition_quality_findings",
    "repetition_chunks",
    "sentence_key",
    "skip_mermaid_line",
    "skip_narrative_line",
    "word_tokens",
]
