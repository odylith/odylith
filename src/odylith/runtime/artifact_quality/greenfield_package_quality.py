"""Whole-package clarity checks for rendered greenfield artifacts."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import re
from typing import Any

from odylith.runtime.artifact_quality import greenfield_package_repetition as _package_repetition
from odylith.runtime.artifact_quality import greenfield_rendered_artifacts as _rendered_artifacts
from odylith.runtime.artifact_quality.generated_copy_quality import generated_public_copy_issues
from odylith.runtime.artifact_quality.generated_copy_quality import has_inline_role_casing_drift
from odylith.runtime.artifact_quality.greenfield_artifact_judgment import greenfield_artifact_judgment_issues
from odylith.runtime.artifact_quality.greenfield_project_judgment import greenfield_project_judgment_issues
from odylith.runtime.artifact_quality.greenfield_project_prompt_quality import project_implementation_prompt_issues
from odylith.runtime.common.prose_grammar import looks_like_action_clause
from odylith.runtime.common.prose_grammar import looks_like_finite_action
from odylith.runtime.common.value_coercion import normalize_string
from odylith.runtime.domain_intelligence.greenfield_text import unique_text


RenderedArtifact = _rendered_artifacts.RenderedArtifact
RenderedPackageQualityFinding = _rendered_artifacts.RenderedPackageQualityFinding

_BASE_FORM_CONTEXTS = frozenset({"can", "could", "may", "might", "must", "shall", "should", "to", "will", "would"})
_TO_NOUN_PRECEDER_VERBS = frozenset({"adds", "attaches", "connects", "links", "maps", "points", "relates", "replies", "responds", "routes", "sends"})
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
_ALLOWED_TERMINAL_PREPOSITION_BIGRAMS = frozenset(
    {
        ("accounted", "for"),
        ("asked", "for"),
        ("cared", "for"),
        ("checked", "for"),
        ("planned", "for"),
        ("paid", "for"),
        ("prepared", "for"),
        ("ready", "for"),
        ("searched", "for"),
        ("waited", "for"),
    }
)
_MID_SENTENCE_CAPITALIZED_PRONOUNS = frozenset({"Her", "His", "Its", "Our", "Their", "Your"})
_POSSESSIVE_PRONOUNS = frozenset({"her", "his", "its", "our", "their", "your"})
_OBJECT_MARKERS = frozenset({"a", "an", "one", "the", "their", "this"})
_TITLE_CONNECTOR_WORDS = frozenset({"a", "an", "and", "as", "at", "by", "for", "from", "in", "of", "on", "or", "the", "to", "with"})
_LOWERCASE_FRAGMENT_STARTS = frozenset({"and", "for", "from", "or", "to", "users", "with", "without"})
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
_INVALID_INFLECTIONS = frozenset({"flaging", "intaked", "runing", "seted", "stoping"})
_VAGUE_MISSING_SUBJECTS = frozenset({"anything", "something", "stuff", "things"})
_CAPITALIZED_CLAUSE_STARTERS = frozenset({"How", "What", "When", "Where", "Whether", "Who", "Why"})
_MERMAID_EDGE_OPERATORS = ("-->>", "-.->", "==>", "-->", "->>", "---")
_COMPONENT_LABEL_MAX_WORDS = 8
_EXPLANATORY_COMPONENT_CONNECTORS = frozenset(
    {"because", "that", "when", "where", "which", "while", "who", "without"}
)
_CONNECTOR_CONTINUATION_OPENERS = frozenset(
    {
        "after",
        "although",
        "as",
        "before",
        "because",
        "if",
        "once",
        "until",
        "when",
        "where",
        "while",
    }
)
def greenfield_rendered_package_quality_issues(package: Any) -> list[str]:
    """Return readability and graph-quality failures across a rendered package."""

    return unique_text(finding.message for finding in greenfield_rendered_package_quality_findings(package))


def greenfield_rendered_package_quality_findings(package: Any) -> list[RenderedPackageQualityFinding]:
    """Return typed readability failures across a rendered package."""

    artifacts = _rendered_artifacts.collect_rendered_package_artifacts(package)
    findings: list[RenderedPackageQualityFinding] = []
    for artifact in artifacts:
        findings.extend(
            _rendered_artifacts.artifact_quality_finding(artifact, issue)
            for issue in _artifact_language_issues(artifact)
        )
        if artifact.kind == "mermaid":
            findings.extend(
                _rendered_artifacts.artifact_quality_finding(artifact, issue)
                for issue in _mermaid_connectivity_issues(artifact)
            )
    findings.extend(_package_repetition.package_repetition_quality_findings(package, artifacts))
    findings.extend(
        _rendered_artifacts.package_quality_finding(issue)
        for issue in (
            *tuple(_package_component_identity_issues(package)),
            *tuple(greenfield_artifact_judgment_issues(package)),
            *tuple(greenfield_project_judgment_issues(package)),
        )
    )
    return _rendered_artifacts.unique_package_quality_findings(findings)


def _artifact_language_issues(artifact: RenderedArtifact) -> list[str]:
    chunks = (
        _package_repetition.mermaid_label_chunks(artifact.text, chunker=_narrative_chunks)
        if artifact.kind == "mermaid"
        else _narrative_chunks(artifact.text)
    )
    issues: list[str] = []
    issues.extend(_artifact_surface_language_issues(artifact))
    for chunk in chunks:
        issues.extend(_chunk_language_issues(artifact, chunk))
    return issues


def _artifact_surface_language_issues(artifact: RenderedArtifact) -> list[str]:
    issues: list[str] = []
    issues.extend(generated_public_copy_issues(artifact.identity, artifact.text))
    issues.extend(project_implementation_prompt_issues(artifact))
    issues.extend(_registry_component_contract_floor_issues(artifact))
    if re.search(r"(?m)^\s*(?:[-*]\s*)?TBD\.?\s*$", artifact.text, flags=re.IGNORECASE):
        issues.append(f"{artifact.identity} contains placeholder TBD copy")
    if re.search(r"\bvalidation\s+gates\s+pass\b", artifact.text, flags=re.IGNORECASE):
        issues.append(f"{artifact.identity} uses generic validation-gate copy")
    if has_inline_role_casing_drift(artifact.text):
        issues.append(f"{artifact.identity} has inline actor casing drift")
    if _has_doubled_sentence_punctuation(artifact.text):
        issues.append(f"{artifact.identity} has doubled sentence punctuation")
    if malformed := _malformed_connector_sequence(artifact.text):
        issues.append(f"{artifact.identity} has malformed connector sequence near `{malformed}`")
    if _has_vague_missing_input_copy(artifact.text):
        issues.append(f"{artifact.identity} uses vague missing-input copy")
    if _has_comma_spliced_capitalized_clause(artifact.text):
        issues.append(f"{artifact.identity} has comma-spliced capitalized clause drift")
    if _has_open_question_scope_boundary(artifact.text):
        issues.append(f"{artifact.identity} uses an open scope question as a boundary clause")
    if _has_clipped_boundary_phrase(artifact.text):
        issues.append(f"{artifact.identity} has clipped boundary phrase")
    if _has_repeated_visible_result_tail(artifact.text):
        issues.append(f"{artifact.identity} repeats the same visible result inside one sentence")
    for token in _package_repetition.word_tokens(artifact.text):
        if token.casefold().strip("'") in _INVALID_INFLECTIONS:
            issues.append(f"{artifact.identity} has invalid verb inflection near `{token}`")
    for chunk in _surface_terminal_chunks(artifact):
        tokens = _package_repetition.word_tokens(chunk)
        if _has_clipped_terminal_modifier(tokens):
            issues.append(f"{artifact.identity} has clipped modifier phrase ending in `{tokens[-2]} {tokens[-1]}`")
        if _has_clipped_terminal_final_phrase(chunk, tokens):
            issues.append(f"{artifact.identity} has a clipped or dangling phrase ending in `{tokens[-1]}`")
        if artifact.kind == "mermaid" and _has_clipped_terminal_key_label(chunk, tokens):
            issues.append(f"{artifact.identity} has a clipped or dangling phrase ending in `{tokens[-1]}`")
        if artifact.kind == "mermaid" and tokens and tokens[-1].casefold().strip(".,;:'") == "blocking":
            issues.append(f"{artifact.identity} has a clipped or dangling phrase ending in `{tokens[-1]}`")
        if artifact.kind == "mermaid" and _has_clipped_terminal_action_label(chunk, tokens):
            issues.append(f"{artifact.identity} has clipped action phrase ending in `{tokens[-1]}`")
    for line in str(artifact.text or "").splitlines():
        bullet = _package_repetition.markdown_bullet_body(line)
        if not bullet:
            continue
        tokens = _package_repetition.word_tokens(bullet)
        if tokens and tokens[0].casefold() in _LOWERCASE_FRAGMENT_STARTS and tokens[0][:1].islower():
            issues.append(f"{artifact.identity} has sentence-fragment drift near `{_clip(bullet, 100)}`")
    return issues


def _registry_component_contract_floor_issues(artifact: RenderedArtifact) -> list[str]:
    if artifact.surface != "Registry component spec":
        return []
    text = artifact.text.casefold()
    required = {
        "source boundary": ("source boundary",),
        "trace links": ("trace links",),
        "successful path evidence": ("successful path evidence", "success proof covers"),
        "blocked input evidence": ("blocked input evidence", "blocked path evidence", "missing or invalid input"),
        "replay evidence": ("replay evidence", "replay proof"),
    }
    issues: list[str] = []
    for label, options in required.items():
        if not any(option in text for option in options):
            issues.append(f"{artifact.identity} is missing {label}")
    return issues


def _chunk_language_issues(artifact: RenderedArtifact, chunk: str) -> list[str]:
    text = normalize_string(chunk).strip("`*_# ")
    if not text:
        return []
    tokens = _package_repetition.word_tokens(text)
    if not tokens:
        return []
    issues: list[str] = []
    lowered = [token.casefold() for token in tokens]
    for index, token in enumerate(lowered[:-1]):
        next_token = lowered[index + 1]
        if token in _BASE_FORM_CONTEXTS and _looks_like_finite_verb(next_token) and not _looks_like_to_plural_noun_context(lowered, index):
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
    if tail in _DANGLING_TAIL_WORDS and not _allowed_terminal_preposition_phrase(lowered):
        issues.append(f"{artifact.identity} has a clipped or dangling phrase ending in `{tokens[-1]}`")
    if _has_clipped_terminal_final_phrase(text, tokens):
        issues.append(f"{artifact.identity} has a clipped or dangling phrase ending in `{tokens[-1]}`")
    return issues


def _allowed_terminal_preposition_phrase(lowered: Sequence[str]) -> bool:
    if len(lowered) < 2:
        return False
    return (lowered[-2].strip("'"), lowered[-1].strip("'")) in _ALLOWED_TERMINAL_PREPOSITION_BIGRAMS


def _looks_like_to_plural_noun_context(lowered: Sequence[str], index: int) -> bool:
    if lowered[index].strip("'") != "to" or index <= 0 or index + 1 >= len(lowered):
        return False
    previous = lowered[index - 1].strip(".,;:'")
    target = lowered[index + 1].strip(".,;:'")
    return previous in _TO_NOUN_PRECEDER_VERBS and target.endswith("s")


def _has_clipped_terminal_final_phrase(chunk: str, tokens: Sequence[str]) -> bool:
    if not tokens:
        return False
    lowered = [token.casefold().strip(".,;:'") for token in tokens]
    if lowered[-1] != "final":
        return False
    return not _allowed_terminal_final_state_phrase(str(chunk or ""), lowered)


def _allowed_terminal_final_state_phrase(chunk: str, lowered: Sequence[str]) -> bool:
    if len(lowered) < 3:
        return False
    previous = lowered[-2]
    if previous in {"case", "match", "record", "result", "score", "status"}:
        return True
    if previous in {"is", "becomes", "became"} and any(
        token in {"decision", "review", "result", "status"} for token in lowered[:-2]
    ):
        return True
    if any(token in {"finalize", "finalizes", "finalized", "finalizing", "mark", "marked", "marks"} for token in lowered[:-1]):
        return True
    if previous == "to" and any(
        token in {"draft", "from", "live", "move", "moved", "moves", "moving", "scheduled", "state", "status", "transition", "transitions"}
        for token in lowered[:-2]
    ):
        return True
    if "," in str(chunk or "") and any(token in {"draft", "live", "scheduled", "state", "status"} for token in lowered[:-1]):
        return previous not in {"and", "or"}
    return False


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
            if candidate_index < window_end and _looks_like_coordinated_finite_action(tokens, lowered, candidate_index):
                phrase = " ".join(tokens[index : candidate_index + 1])
                issues.append(f"{artifact.identity} has coordinated modal grammar drift near `{phrase}`")
    return issues


def _looks_like_coordinated_finite_action(
    tokens: Sequence[str],
    lowered: Sequence[str],
    candidate_index: int,
) -> bool:
    if not _looks_like_finite_verb(lowered[candidate_index]):
        return False
    token = str(tokens[candidate_index]).strip(".,;:")
    next_token = str(tokens[candidate_index + 1]).strip(".,;:") if candidate_index + 1 < len(tokens) else ""
    if token[:1].isupper() and next_token[:1].isupper():
        return False
    if _looks_like_conjunction_noun_compound(lowered, candidate_index):
        return False
    return True


def _looks_like_conjunction_noun_compound(lowered: Sequence[str], candidate_index: int) -> bool:
    token = lowered[candidate_index].strip(".,;:")
    next_token = lowered[candidate_index + 1].strip(".,;:") if candidate_index + 1 < len(lowered) else ""
    if token in {"records", "reports", "reviews"} and next_token in {
        "archive",
        "dashboard",
        "evidence",
        "export",
        "history",
        "ledger",
        "log",
        "record",
        "service",
        "store",
        "summary",
        "surface",
        "trail",
        "view",
    }:
        return True
    return False


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


def _malformed_connector_sequence(value: str) -> str:
    match = re.search(r"\b(?:and|or|then|but)\s+(?:and|or|then|but)\b", str(value or ""), flags=re.IGNORECASE)
    return match.group(0) if match else ""


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
        return _package_repetition.mermaid_label_chunks(artifact.text)
    return _package_repetition.repetition_chunks(artifact.text)


def _has_clipped_terminal_modifier(tokens: Sequence[str]) -> bool:
    if len(tokens) < 2:
        return False
    tail = tokens[-1].casefold().strip(".,;:'")
    previous = tokens[-2].casefold().strip(".,;:'")
    return tail in _TERMINAL_MODIFIER_WORDS and previous in _TERMINAL_MODIFIER_PRECEDERS


def _has_clipped_terminal_action_label(chunk: str, tokens: Sequence[str]) -> bool:
    if len(tokens) < 6 or "," not in str(chunk or ""):
        return False
    tail_segment = str(chunk or "").rsplit(",", 1)[-1].strip(" .;:")
    tail_tokens = _package_repetition.word_tokens(tail_segment)
    if len(tail_tokens) != 1:
        return False
    tail = tail_tokens[0].casefold().strip(".,;:'")
    if not tail or tail in {"and", "or"}:
        return False
    if tail.endswith("ing") and len(tail) > 5:
        return True
    return looks_like_action_clause(f"{tail} placeholder") and not looks_like_finite_action(f"{tail} placeholder")


def _has_clipped_terminal_key_label(chunk: str, tokens: Sequence[str]) -> bool:
    if not tokens or tokens[-1].casefold().strip(".,;:'") != "key":
        return False
    text = str(chunk or "").casefold()
    return "," in text or re.search(r"\bwith\s+[^,]+,\s*key$", text)


def _has_repeated_visible_result_tail(value: str) -> bool:
    for chunk in _package_repetition.repetition_chunks(value):
        if _chunk_repeats_visible_result_tail(chunk):
            return True
    return False


def _chunk_repeats_visible_result_tail(value: str) -> bool:
    text = normalize_string(value)
    if len(text.split()) < 12:
        return False
    for pattern in (
        r",?\s+then\s+let\s+[^.;,]{1,120}?\s+(?:reach|see|use|view|read|receive)\s+(?P<tail>[^.;,]{18,180})",
        r"\band\s+lets?\s+[^.;,]{1,120}?\s+(?:reach|see|use|view|read|receive)\s+(?P<tail>[^.;,]{18,180})",
        r"\b(?:connects?|maps?|ties?)\s+[^.;]{1,220}?\s+to\s+(?P<tail>(?:a|an|the)\s+[^.;,]{18,180}?)(?:\s+without|\s+with|\s+before|[.;,]|$)",
    ):
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            tail_terms = _visible_result_tail_terms(match.group("tail"))
            head_terms = _visible_result_tail_terms(text[: match.start()])
            if len(tail_terms) >= 4 and tail_terms <= head_terms:
                return True
    return False


def _visible_result_tail_terms(value: str) -> set[str]:
    ignored = {
        "and",
        "can",
        "get",
        "gets",
        "getting",
        "reach",
        "reaches",
        "reaching",
        "read",
        "reads",
        "receive",
        "receives",
        "see",
        "sees",
        "the",
        "then",
        "use",
        "uses",
        "user",
        "users",
        "view",
        "views",
        "with",
        "without",
    }
    return {token.casefold().strip(".,;:'") for token in _package_repetition.word_tokens(value) if token.casefold().strip(".,;:'") not in ignored}


def _package_component_identity_issues(package: Any) -> list[str]:
    proposal = _rendered_artifacts.package_mapping(getattr(package, "proposal", None))
    rows = proposal.get("components", [])
    if not isinstance(rows, Sequence) or isinstance(rows, str):
        return []
    issues: list[str] = []
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        label = normalize_string(row.get("label"))
        tokens = _package_repetition.word_tokens(label)
        if len(tokens) <= _COMPONENT_LABEL_MAX_WORDS:
            continue
        lowered = {token.casefold().strip("'") for token in tokens}
        if lowered & _EXPLANATORY_COMPONENT_CONNECTORS:
            component_id = normalize_string(row.get("component_id")) or "unknown"
            issues.append(
                f"greenfield component `{component_id}` has explanatory component label `{_clip(label, 120)}`"
            )
    return issues


def _mermaid_connectivity_issues(artifact: RenderedArtifact) -> list[str]:
    defined: set[str] = set()
    connected: set[str] = set()
    edge_count = 0
    for raw_line in artifact.text.splitlines():
        line = raw_line.strip()
        if not line or _package_repetition.skip_mermaid_line(line):
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
        if in_code_fence or _package_repetition.skip_narrative_line(line):
            continue
        for index, char in enumerate(line):
            if _package_repetition.is_sentence_boundary_char(line, index):
                _package_repetition.append_chunk(chunks, current)
                current = []
            elif char in ",;" and not _punctuation_continues_connector_clause(line, index, current):
                _package_repetition.append_chunk(chunks, current)
                _append_short_chunk(chunks, current)
                current = []
            else:
                current.append(char)
        _package_repetition.append_chunk(chunks, current)
        current = []
    return chunks


def _punctuation_continues_connector_clause(line: str, index: int, current: Sequence[str]) -> bool:
    """Keep grammatical connector interrupters in one quality-check chunk."""

    if not current or index < 0 or index >= len(line) or line[index] != ",":
        return False
    tokens = _package_repetition.word_tokens("".join(current))
    if not tokens or tokens[-1].casefold().strip(".,;:'") not in {"and", "or"}:
        return False
    return _next_word(line[index + 1 :]) in _CONNECTOR_CONTINUATION_OPENERS


def _next_word(value: str) -> str:
    match = re.search(r"[A-Za-z][A-Za-z'-]*", str(value or ""))
    return match.group(0).casefold() if match else ""


def _append_short_chunk(chunks: list[str], chars: list[str]) -> None:
    text = normalize_string("".join(chars)).strip(" -#*_`|")
    if text.casefold() in _DANGLING_TAIL_WORDS:
        chunks.append(text)


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


def _looks_like_finite_verb(token: str) -> bool:
    return looks_like_finite_action(f"{token} placeholder")


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
    for chunk in _package_repetition.repetition_chunks(value):
        tokens = [token.casefold() for token in _package_repetition.word_tokens(chunk)]
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
    for chunk in _package_repetition.repetition_chunks(value):
        lowered = chunk.casefold()
        if "whether " in lowered and " in scope " in lowered and " until " in lowered:
            return True
    return False


def _has_clipped_boundary_phrase(value: str) -> bool:
    for chunk in _package_repetition.repetition_chunks(value):
        tokens = [token.casefold() for token in _package_repetition.word_tokens(chunk)]
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


__all__ = [
    "RenderedPackageQualityFinding",
    "greenfield_rendered_package_quality_findings",
    "greenfield_rendered_package_quality_issues",
]
