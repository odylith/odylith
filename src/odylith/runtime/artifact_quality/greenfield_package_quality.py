"""Whole-package clarity checks for rendered greenfield artifacts."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from odylith.runtime.artifact_quality.generated_copy_quality import generated_public_copy_issues
from odylith.runtime.common.prose_grammar import looks_like_action_clause
from odylith.runtime.common.prose_grammar import looks_like_finite_action
from odylith.runtime.common.value_coercion import normalize_string
from odylith.runtime.domain_intelligence.greenfield_text import text_values
from odylith.runtime.domain_intelligence.greenfield_text import unique_text


@dataclass(frozen=True)
class RenderedArtifact:
    surface: str
    name: str
    text: str
    kind: str = "prose"

    @property
    def identity(self) -> str:
        return f"{self.surface} `{self.name}`"


_BASE_FORM_CONTEXTS = frozenset({"can", "could", "may", "might", "must", "shall", "should", "to", "will", "would"})
_PREPOSITION_BASE_CONTEXTS = frozenset()
_DANGLING_TAIL_WORDS = frozenset(
    {
        "against",
        "alongside",
        "and",
        "around",
        "as",
        "at",
        "because",
        "between",
        "for",
        "from",
        "into",
        "of",
        "or",
        "plus",
        "through",
        "to",
        "toward",
        "towards",
        "until",
        "via",
        "when",
        "while",
        "with",
        "without",
    }
)
_MID_SENTENCE_CAPITALIZED_PRONOUNS = frozenset({"Her", "His", "Its", "Our", "Their", "Your"})
_POSSESSIVE_PRONOUNS = frozenset({"her", "his", "its", "our", "their", "your"})
_OBJECT_MARKERS = frozenset({"a", "an", "one", "the", "their", "this"})
_TITLE_CONNECTOR_WORDS = frozenset({"a", "an", "and", "as", "at", "by", "for", "from", "in", "of", "on", "or", "the", "to", "with"})
_LOWERCASE_FRAGMENT_STARTS = frozenset({"and", "for", "from", "or", "to", "with", "without"})
_TERMINAL_MODIFIER_WORDS = frozenset(
    {
        "actionable",
        "accepted",
        "clear",
        "complete",
        "concrete",
        "daily",
        "first",
        "reviewable",
        "safety",
        "specific",
        "trusted",
        "visible",
    }
)
_TERMINAL_MODIFIER_PRECEDERS = frozenset({"a", "an", "one", "the", "this", "that"})
_TERMINAL_ARTICLE_WORDS = frozenset({"a", "an", "that", "the", "their", "this"})
_INVALID_INFLECTIONS = frozenset({"seted"})
_VAGUE_MISSING_SUBJECTS = frozenset({"anything", "something", "stuff", "things"})
_CAPITALIZED_CLAUSE_STARTERS = frozenset({"How", "What", "When", "Where", "Whether", "Who", "Why"})
_MERMAID_EDGE_OPERATORS = ("-->>", "-.->", "==>", "-->", "->>", "---")
_REPETITION_MIN_WORDS = 9
_REPETITION_MIN_CHARS = 68
_COMPONENT_LABEL_MAX_WORDS = 8
_EXPLANATORY_COMPONENT_CONNECTORS = frozenset(
    {"because", "that", "when", "where", "which", "while", "who", "with", "without"}
)


def greenfield_rendered_package_quality_issues(package: Any) -> list[str]:
    """Return readability and graph-quality failures across a rendered package."""

    artifacts = _collect_rendered_artifacts(package)
    issues: list[str] = []
    for artifact in artifacts:
        issues.extend(_artifact_language_issues(artifact))
        if artifact.kind == "mermaid":
            issues.extend(_mermaid_connectivity_issues(artifact))
    issues.extend(_package_component_identity_issues(package))
    issues.extend(_package_repetition_issues(package, artifacts))
    return unique_text(issues)


def _collect_rendered_artifacts(package: Any) -> list[RenderedArtifact]:
    artifacts: list[RenderedArtifact] = []
    backlog_result = _as_mapping(getattr(package, "backlog_result", None))
    for path, text in _as_mapping(backlog_result.get("idea_files")).items():
        artifacts.append(RenderedArtifact("Radar workstream", _artifact_name(path), str(text or "")))
    index_text = normalize_string(backlog_result.get("backlog_index_text"))
    if index_text:
        artifacts.append(RenderedArtifact("Radar index", "INDEX.md", index_text))

    for name, text in _as_mapping(getattr(package, "rendered_component_specs", None)).items():
        artifacts.append(RenderedArtifact("Registry component spec", _artifact_name(name), str(text or "")))

    for path, source in _as_mapping(getattr(package, "rendered_atlas_sources", None)).items():
        artifacts.append(RenderedArtifact("Atlas Mermaid", _artifact_name(path), str(source or ""), kind="mermaid"))

    project_brief = _preview_text(getattr(package, "project_brief_preview", None))
    if project_brief:
        artifacts.append(RenderedArtifact("Project brief preview", "project_brief", project_brief))

    next_steps = _preview_text(getattr(package, "next_steps_preview", None))
    if next_steps:
        artifacts.append(RenderedArtifact("Operator next steps", "next_steps", next_steps))

    return artifacts


def _artifact_language_issues(artifact: RenderedArtifact) -> list[str]:
    chunks = _mermaid_label_chunks(artifact.text) if artifact.kind == "mermaid" else _narrative_chunks(artifact.text)
    issues: list[str] = []
    issues.extend(_artifact_surface_language_issues(artifact))
    for chunk in chunks:
        issues.extend(_chunk_language_issues(artifact, chunk))
    return issues


def _artifact_surface_language_issues(artifact: RenderedArtifact) -> list[str]:
    issues: list[str] = []
    issues.extend(generated_public_copy_issues(artifact.identity, artifact.text))
    if _has_doubled_sentence_punctuation(artifact.text):
        issues.append(f"{artifact.identity} has doubled sentence punctuation")
    if _has_vague_missing_input_copy(artifact.text):
        issues.append(f"{artifact.identity} uses vague missing-input copy")
    if _has_comma_spliced_capitalized_clause(artifact.text):
        issues.append(f"{artifact.identity} has comma-spliced capitalized clause drift")
    if _has_open_question_scope_boundary(artifact.text):
        issues.append(f"{artifact.identity} uses an open scope question as a boundary clause")
    if _has_clipped_boundary_phrase(artifact.text):
        issues.append(f"{artifact.identity} has clipped boundary phrase")
    for token in _word_tokens(artifact.text):
        if token.casefold().strip("'") in _INVALID_INFLECTIONS:
            issues.append(f"{artifact.identity} has invalid verb inflection near `{token}`")
    for chunk in _surface_terminal_chunks(artifact):
        tokens = _word_tokens(chunk)
        if _has_clipped_terminal_modifier(tokens):
            issues.append(f"{artifact.identity} has clipped modifier phrase ending in `{tokens[-2]} {tokens[-1]}`")
    for line in str(artifact.text or "").splitlines():
        bullet = _markdown_bullet_body(line)
        if not bullet:
            continue
        tokens = _word_tokens(bullet)
        if tokens and tokens[0].casefold() in _LOWERCASE_FRAGMENT_STARTS and tokens[0][:1].islower():
            issues.append(f"{artifact.identity} has sentence-fragment drift near `{_clip(bullet, 100)}`")
    return issues


def _chunk_language_issues(artifact: RenderedArtifact, chunk: str) -> list[str]:
    text = normalize_string(chunk).strip("`*_# ")
    if not text:
        return []
    tokens = _word_tokens(text)
    if not tokens:
        return []
    issues: list[str] = []
    lowered = [token.casefold() for token in tokens]
    for index, token in enumerate(lowered[:-1]):
        next_token = lowered[index + 1]
        if token in _BASE_FORM_CONTEXTS and _looks_like_finite_verb(next_token):
            issues.append(f"{artifact.identity} has modal/base-form grammar drift near `{tokens[index]} {tokens[index + 1]}`")
        if token in _PREPOSITION_BASE_CONTEXTS and _looks_like_finite_verb(next_token):
            issues.append(f"{artifact.identity} has preposition/action grammar drift near `{tokens[index]} {tokens[index + 1]}`")
    title_like_chunk = _looks_like_title_case_chunk(tokens)
    for index, token in enumerate(tokens[1:], start=1):
        if (
            token in _MID_SENTENCE_CAPITALIZED_PRONOUNS
            and not title_like_chunk
            and not _capitalized_pronoun_is_inside_title_suffix(tokens, index)
        ):
            issues.append(f"{artifact.identity} has mid-sentence capitalization drift near `{tokens[index]}`")
    for index, token in enumerate(lowered[:-2]):
        if token in _POSSESSIVE_PRONOUNS and lowered[index + 2] in _OBJECT_MARKERS:
            if looks_like_action_clause(f"{lowered[index + 1]} placeholder"):
                phrase = " ".join(tokens[index : index + 3])
                issues.append(f"{artifact.identity} has possessive/action title drift near `{phrase}`")
    issues.extend(_coordinated_modal_drift_issues(artifact, tokens, lowered))
    issues.extend(_adjacent_repeated_word_issues(artifact, text, tokens, lowered))
    tail = lowered[-1].strip("'")
    if tail in _INVALID_INFLECTIONS:
        issues.append(f"{artifact.identity} has invalid verb inflection near `{tokens[-1]}`")
    if tail in _TERMINAL_ARTICLE_WORDS:
        issues.append(f"{artifact.identity} has a clipped article phrase ending in `{tokens[-1]}`")
    if tail in _DANGLING_TAIL_WORDS:
        issues.append(f"{artifact.identity} has a clipped or dangling phrase ending in `{tokens[-1]}`")
    return issues


def _coordinated_modal_drift_issues(
    artifact: RenderedArtifact,
    tokens: Sequence[str],
    lowered: Sequence[str],
) -> list[str]:
    issues: list[str] = []
    for modal_index, token in enumerate(lowered):
        if token not in {"can", "could", "may", "might", "must", "shall", "should", "will", "would"}:
            continue
        if token == "can" and lowered[modal_index : modal_index + 3] == ["can", "be", "trusted"]:
            continue
        window_end = min(len(lowered), modal_index + 18)
        for index in range(modal_index + 1, window_end):
            if lowered[index] not in {"and", "or"}:
                continue
            candidate_index = index + 1
            if candidate_index < window_end and lowered[candidate_index].endswith("ly"):
                candidate_index += 1
            if candidate_index < window_end and _looks_like_finite_verb(lowered[candidate_index]):
                phrase = " ".join(tokens[index : candidate_index + 1])
                issues.append(f"{artifact.identity} has coordinated modal grammar drift near `{phrase}`")
    return issues


def _adjacent_repeated_word_issues(
    artifact: RenderedArtifact,
    text: str,
    tokens: Sequence[str],
    lowered: Sequence[str],
) -> list[str]:
    if _looks_like_link_or_path_chunk(text):
        return []
    issues: list[str] = []
    for index, token in enumerate(lowered[:-1]):
        if len(token) < 4:
            continue
        if token == lowered[index + 1]:
            issues.append(f"{artifact.identity} repeats adjacent word `{tokens[index]} {tokens[index + 1]}`")
    return issues


def _looks_like_link_or_path_chunk(value: str) -> bool:
    text = str(value or "")
    return bool("](" in text or "://" in text or "/" in text or "\\" in text)


def _looks_like_title_case_chunk(tokens: Sequence[str]) -> bool:
    if len(tokens) < 3 or len(tokens) > 24:
        return False
    meaningful = 0
    title_shaped = 0
    for token in tokens:
        stripped = token.strip("-'")
        if not stripped:
            continue
        lower = stripped.casefold()
        if lower in _TITLE_CONNECTOR_WORDS:
            continue
        meaningful += 1
        if stripped[:1].isupper() or stripped[:1].isdigit() or _looks_like_acronym_token(stripped):
            title_shaped += 1
    return meaningful >= 2 and title_shaped / meaningful >= 0.75


def _looks_like_acronym_token(value: str) -> bool:
    letters = [char for char in value if char.isalpha()]
    return len(letters) >= 2 and all(char.isupper() for char in letters)


def _capitalized_pronoun_is_inside_title_suffix(tokens: Sequence[str], index: int) -> bool:
    start_floor = max(0, index - 10)
    for start in range(start_floor, index + 1):
        suffix = tokens[start:]
        if len(suffix) < 3:
            continue
        if _looks_like_title_case_chunk(suffix):
            return True
    return False


def _surface_terminal_chunks(artifact: RenderedArtifact) -> list[str]:
    if artifact.kind == "mermaid":
        return _mermaid_label_surface_chunks(artifact.text)
    return _repetition_chunks(artifact.text)


def _mermaid_label_surface_chunks(value: str) -> list[str]:
    labels: list[str] = []
    for raw_line in str(value or "").splitlines():
        line = raw_line.strip()
        if not line or _skip_mermaid_line(line):
            continue
        labels.extend(_quoted_labels(line))
        participant_label = _participant_label(line)
        if participant_label:
            labels.append(participant_label)
    chunks: list[str] = []
    for label in labels:
        normalized = label.replace("<br/>", " ").replace("<br>", " ")
        chunks.extend(_repetition_chunks(normalized))
    return chunks


def _has_clipped_terminal_modifier(tokens: Sequence[str]) -> bool:
    if len(tokens) < 2:
        return False
    tail = tokens[-1].casefold().strip(".,;:'")
    previous = tokens[-2].casefold().strip(".,;:'")
    return tail in _TERMINAL_MODIFIER_WORDS and previous in _TERMINAL_MODIFIER_PRECEDERS


def _package_repetition_issues(package: Any, artifacts: list[RenderedArtifact]) -> list[str]:
    allowed = _allowed_repetition_keys(package)
    occurrences: dict[str, list[tuple[RenderedArtifact, str]]] = {}
    for artifact in artifacts:
        chunks = _mermaid_label_chunks(artifact.text) if artifact.kind == "mermaid" else _repetition_chunks(artifact.text)
        for chunk in chunks:
            key = _sentence_key(chunk)
            if key and key not in allowed and not _allowed_structured_repetition_key(key):
                occurrences.setdefault(key, []).append((artifact, normalize_string(chunk)))
    issues: list[str] = []
    for key, rows in occurrences.items():
        identities = sorted({artifact.identity for artifact, _chunk in rows})
        if len(identities) < 3:
            continue
        sample = rows[0][1]
        issues.append(
            "greenfield rendered package repeats a noncanonical sentence across "
            f"{len(identities)} artifacts: `{_clip(sample, 140)}`"
        )
    return issues


def _allowed_structured_repetition_key(key: str) -> bool:
    return key.startswith(
        (
            "boundary ",
            "control ",
            "gate ",
            "owner ",
            "proof ",
            "question ",
            "risk ",
            "state object ",
        )
    )


def _package_component_identity_issues(package: Any) -> list[str]:
    proposal = _as_mapping(getattr(package, "proposal", None))
    rows = proposal.get("components", [])
    if not isinstance(rows, Sequence) or isinstance(rows, str):
        return []
    issues: list[str] = []
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        label = normalize_string(row.get("label"))
        tokens = _word_tokens(label)
        if len(tokens) <= _COMPONENT_LABEL_MAX_WORDS:
            continue
        lowered = {token.casefold().strip("'") for token in tokens}
        if lowered & _EXPLANATORY_COMPONENT_CONNECTORS:
            component_id = normalize_string(row.get("component_id")) or "unknown"
            issues.append(
                f"greenfield component `{component_id}` has explanatory component label `{_clip(label, 120)}`"
            )
    return issues


def _allowed_repetition_keys(package: Any) -> set[str]:
    proposal = _as_mapping(getattr(package, "proposal", None))
    intent = _as_mapping(proposal.get("intent"))
    semantic_model = _as_mapping(proposal.get("semantic_model"))
    first_path = _as_mapping(semantic_model.get("first_path_contract"))
    ontology = _as_mapping(semantic_model.get("domain_ontology"))
    component_rows = proposal.get("components", [])
    component_sequence = (
        component_rows
        if isinstance(component_rows, Sequence) and not isinstance(component_rows, str)
        else []
    )
    components = [
        row
        for row in component_sequence
        if isinstance(row, Mapping)
    ]
    values = [
        intent.get("title"),
        intent.get("first_path"),
        intent.get("proof_boundary"),
        _actor_label_summary(text_values(intent.get("human_actors"))),
        first_path.get("raw_path"),
        first_path.get("capability"),
        first_path.get("visible_result"),
        ontology.get("proof_boundary"),
        *[
            f"{component.get('component_id', '')} {component.get('label', '')}"
            for component in components
            if normalize_string(component.get("component_id")) and normalize_string(component.get("label"))
        ],
    ]
    keys: set[str] = set()
    for value in values:
        for chunk in _repetition_chunks(str(value or "")):
            key = _sentence_key(chunk)
            if key:
                keys.add(key)
    return keys


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


def _mermaid_connectivity_issues(artifact: RenderedArtifact) -> list[str]:
    defined: set[str] = set()
    connected: set[str] = set()
    edge_count = 0
    for raw_line in artifact.text.splitlines():
        line = raw_line.strip()
        if not line or _skip_mermaid_line(line):
            continue
        node = _defined_node_id(line)
        if node:
            defined.add(node)
        edges = _edge_nodes(line)
        for left, right in edges:
            if left:
                connected.add(left)
            if right:
                connected.add(right)
        edge_count += len(edges)
    if not edge_count:
        return []
    issues: list[str] = []
    for node in sorted(defined - connected):
        issues.append(f"{artifact.identity} has disconnected Mermaid node `{node}`")
    return issues


def _narrative_chunks(value: str) -> list[str]:
    chunks: list[str] = []
    current: list[str] = []
    in_code_fence = False
    for raw_line in str(value or "").splitlines():
        line = raw_line.strip()
        if line.startswith("```"):
            in_code_fence = not in_code_fence
            continue
        if in_code_fence or _skip_narrative_line(line):
            continue
        for char in line:
            if char in ".!?\n\r":
                _append_chunk(chunks, current)
                current = []
            elif char in ",;":
                _append_chunk(chunks, current)
                _append_short_chunk(chunks, current)
                current = []
            else:
                current.append(char)
        _append_chunk(chunks, current)
        current = []
    return chunks


def _repetition_chunks(value: str) -> list[str]:
    chunks: list[str] = []
    current: list[str] = []
    in_code_fence = False
    for raw_line in str(value or "").splitlines():
        line = raw_line.strip()
        if line.startswith("```"):
            in_code_fence = not in_code_fence
            continue
        if in_code_fence or _skip_narrative_line(line):
            continue
        for char in line:
            if char in ".!?\n\r":
                _append_chunk(chunks, current)
                current = []
            else:
                current.append(char)
        _append_chunk(chunks, current)
        current = []
    return chunks


def _mermaid_label_chunks(value: str) -> list[str]:
    labels: list[str] = []
    for raw_line in str(value or "").splitlines():
        line = raw_line.strip()
        if not line or _skip_mermaid_line(line):
            continue
        labels.extend(_quoted_labels(line))
        participant_label = _participant_label(line)
        if participant_label:
            labels.append(participant_label)
    chunks: list[str] = []
    for label in labels:
        normalized = label.replace("<br/>", " ").replace("<br>", " ")
        chunks.extend(_narrative_chunks(normalized))
    return chunks


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


def _append_chunk(chunks: list[str], chars: list[str]) -> None:
    text = normalize_string("".join(chars)).strip(" -#*_`|")
    if len(_word_tokens(text)) >= 2:
        chunks.append(text)


def _append_short_chunk(chunks: list[str], chars: list[str]) -> None:
    text = normalize_string("".join(chars)).strip(" -#*_`|")
    if text.casefold() in _DANGLING_TAIL_WORDS:
        chunks.append(text)


def _skip_narrative_line(line: str) -> bool:
    if not line:
        return True
    if line.startswith("|") or line.startswith("```"):
        return True
    if line.startswith("<!--") or line.startswith("::"):
        return True
    if line.endswith(":") and "_" in line:
        return True
    return False


def _skip_mermaid_line(line: str) -> bool:
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


def _defined_node_id(line: str) -> str:
    node = _node_id_from_start(line)
    if not node:
        return ""
    rest = line[len(node) :].lstrip()
    return node if rest.startswith(("[", "(", "{")) else ""


def _edge_nodes(line: str) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    remaining = line
    while True:
        found = _first_edge_operator(remaining)
        if found is None:
            return rows
        position, width = found
        left = remaining[:position]
        right = remaining[position + width :]
        left_node = _node_id_from_tail(left)
        right_node = _node_id_from_start(right)
        if left_node or right_node:
            rows.append((left_node, right_node))
        remaining = right


def _first_edge_operator(line: str) -> tuple[int, int] | None:
    found: tuple[int, int] | None = _first_labeled_dashed_edge(line)
    for operator in _MERMAID_EDGE_OPERATORS:
        position = line.find(operator)
        if position < 0:
            continue
        if found is None or position < found[0]:
            found = (position, len(operator))
    return found


def _first_labeled_dashed_edge(line: str) -> tuple[int, int] | None:
    start = line.find("-.")
    if start < 0:
        return None
    end = line.find(".->", start + 2)
    if end < 0:
        return None
    return start, end + 3 - start


def _node_id_from_start(segment: str) -> str:
    text = segment.strip()
    if not text:
        return ""
    if text.startswith("|"):
        closing = text.find("|", 1)
        if closing >= 0:
            text = text[closing + 1 :].strip()
    chars: list[str] = []
    for char in text:
        if char.isalnum() or char in {"_", "-"}:
            chars.append(char)
            continue
        break
    token = "".join(chars)
    return token if token and not token[0].isdigit() else ""


def _node_id_from_tail(segment: str) -> str:
    text = segment.strip()
    if not text:
        return ""
    end = len(text)
    while end > 0 and not (text[end - 1].isalnum() or text[end - 1] in {"_", "-", "]", ")", "}"}):
        end -= 1
    text = text[:end].rstrip()
    if text.endswith(("]", ")", "}")):
        opener = {" ]": "[", ")": "(", "}": "{"}.get(text[-1], "")
        opener = "[" if text[-1] == "]" else opener
        position = text.rfind(opener) if opener else -1
        if position > 0:
            text = text[:position].rstrip()
    start = len(text)
    while start > 0 and (text[start - 1].isalnum() or text[start - 1] in {"_", "-"}):
        start -= 1
    token = text[start:]
    return token if token and not token[0].isdigit() else ""


def _preview_text(value: Any) -> str:
    if not isinstance(value, Mapping):
        return ""
    rows = [normalize_string(row).strip() for row in text_values(value)]
    bounded = [row if not row or row[-1] in ".!?" else f"{row}." for row in rows if row]
    return "\n".join(bounded)


def _as_mapping(value: Any) -> Mapping[Any, Any]:
    return value if isinstance(value, Mapping) else {}


def _artifact_name(value: Any) -> str:
    text = normalize_string(value)
    return text or "artifact"


def _word_tokens(value: str) -> list[str]:
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


def _markdown_bullet_body(value: str) -> str:
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


def _looks_like_finite_verb(token: str) -> bool:
    return looks_like_finite_action(f"{token} placeholder")


def _sentence_key(value: str) -> str:
    tokens = [token.casefold() for token in _word_tokens(value)]
    if len(tokens) < _REPETITION_MIN_WORDS:
        return ""
    key = " ".join(tokens)
    return key if len(key) >= _REPETITION_MIN_CHARS else ""


def _has_doubled_sentence_punctuation(value: str) -> bool:
    text = str(value or "")
    index = 0
    while index < len(text) - 1:
        pair = text[index : index + 2]
        if pair in {"?.", "!.", "??", "!!"}:
            return True
        if text[index : index + 3] in {'?".', '!".'}:
            return True
        if pair == "..":
            previous_char = text[index - 1] if index > 0 else ""
            next_char = text[index + 2] if index + 2 < len(text) else ""
            if previous_char != "." and next_char != ".":
                return True
        index += 1
    return False


def _has_comma_spliced_capitalized_clause(value: str) -> bool:
    text = str(value or "")
    for index, char in enumerate(text):
        if char != ",":
            continue
        word = _next_word_after(text, index + 1)
        if word in _CAPITALIZED_CLAUSE_STARTERS:
            return True
    return False


def _has_vague_missing_input_copy(value: str) -> bool:
    for chunk in _repetition_chunks(value):
        tokens = [token.casefold() for token in _word_tokens(chunk)]
        if len(tokens) < 3:
            continue
        if tokens[0] != "if":
            continue
        if "missing" not in tokens and "unavailable" not in tokens and "absent" not in tokens:
            continue
        if any(token in _VAGUE_MISSING_SUBJECTS for token in tokens[1:5]):
            return True
    return False


def _has_open_question_scope_boundary(value: str) -> bool:
    for chunk in _repetition_chunks(value):
        lowered = chunk.casefold()
        if "whether " in lowered and " in scope " in lowered and " until " in lowered:
            return True
    return False


def _has_clipped_boundary_phrase(value: str) -> bool:
    for chunk in _repetition_chunks(value):
        tokens = [token.casefold() for token in _word_tokens(chunk)]
        if len(tokens) >= 2 and tokens[-2:] == ["outside", "boundary"]:
            return True
    return False


def _next_word_after(value: str, start: int) -> str:
    index = start
    while index < len(value) and not value[index].isalpha():
        index += 1
    chars: list[str] = []
    while index < len(value) and value[index].isalpha():
        chars.append(value[index])
        index += 1
    return "".join(chars)


def _clip(value: str, limit: int) -> str:
    text = normalize_string(value)
    if len(text) <= limit:
        return text
    clipped = text[:limit].rstrip()
    if " " in clipped:
        clipped = clipped.rsplit(" ", 1)[0]
    return clipped.rstrip(" ,;:.") + "..."


__all__ = ["greenfield_rendered_package_quality_issues"]
