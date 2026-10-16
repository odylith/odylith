"""Atlas diagram-box extraction and reader-facing explanation rules."""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

from odylith.runtime.domain_intelligence.greenfield_confirmed_text import (
    capitalize_sentence_start_preserving_source_terms,
)
from odylith.runtime.domain_intelligence.greenfield_authored_atlas_design_views import atlas_box_details
from odylith.runtime.domain_intelligence.greenfield_deferral_predicates import terminal_deferral_subject
from odylith.runtime.surfaces import atlas_diagram_intelligence
from odylith.runtime.surfaces import display_text


_PLACEHOLDER_RE = re.compile(r"\b(tbd|todo|n/a|none|placeholder|fixme)\b", re.IGNORECASE)
_MECHANICAL_DESCRIPTION_RE = re.compile(
    r"\b("
    r"part of the path|incoming arrows|outgoing arrows|hands off|branch point|"
    r"read the boxes inside|diagram mechanics|through the arrows|"
    r"named state or responsibility in this diagram"
    r")\b",
    re.IGNORECASE,
)
_COMMON_COMPONENT_TOKENS = {
    "a",
    "an",
    "and",
    "app",
    "component",
    "control",
    "controls",
    "core",
    "for",
    "service",
    "services",
    "system",
    "the",
    "tracker",
    "view",
}
_OWNED_ACTION_RE = re.compile(
    r"^owns?\s+"
    r"(accepts?|assembles?|binds?|captures?|carries?|chooses?|computes?|converts?|coordinates?|derives?|engraves?|estimates?|exposes?|exports?|handles?|imports?|"
    r"issues?|links?|maintains?|normalizes?|optimizes?|performs?|predicts?|presents?|preserves?|pulls?|records?|renders?|"
    r"resolves?|shows?|stores?|supplies?|tracks?|turns?|validates?|writes?)\b",
    re.IGNORECASE,
)
_LEGACY_COMPONENT_APPENDIX_RE = re.compile(
    r"\b("
    r"for release\s+\S+,\s+it receives or produces|"
    r"it matters for release\s+\S+\s+because the first|"
    r"reviewers trust it only when|"
    r"proof must stay inside|"
    r"the first workflow depends on|"
    r"the first path depends on"
    r")\b",
    re.IGNORECASE,
)
_NODE_LABEL_RE = re.compile(
    r"""
    (?<![\w.-])
    (?P<id>[A-Za-z][\w.-]*)
    \s*
    (?:
      \[\[\s*(?P<bracket2>[^\]]+?)\s*\]\]
      |\[\s*"(?P<bracket_dq>[^"]+?)"\s*\]
      |\[\s*'(?P<bracket_sq>[^']+?)'\s*\]
      |\[\s*(?P<bracket>[^\]]+?)\s*\]
      |\{\{\s*(?P<brace2>[^}]+?)\s*\}\}
      |\{\s*(?P<brace>[^}]+?)\s*\}
      |\(\(\s*(?P<paren2>[^)]+?)\s*\)\)
      |\(\s*"(?P<paren_dq>[^"]+?)"\s*\)
      |\(\s*'(?P<paren_sq>[^']+?)'\s*\)
      |\(\s*(?P<paren>[^)]+?)\s*\)
    )
    """,
    re.VERBOSE,
)


@dataclass(frozen=True)
class DiagramBoxExplanation:
    """One Mermaid box label with optional catalog-authored explanation."""

    label: str
    role: str
    description: str
    details: tuple[Mapping[str, str], ...] | None = None

    def as_dict(self) -> dict[str, Any]:
        """Return the box explanation as a JSON-ready Atlas payload row."""
        row: dict[str, Any] = {
            "label": self.label,
            "role": self.role,
            "description": self.description,
        }
        if self.details is not None:
            row["details"] = [dict(detail) for detail in self.details]
        return row


def _clean_label(value: str) -> str:
    text = html.unescape(str(value or ""))
    text = re.sub(r"<\s*br\s*/?\s*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = display_text.strip_inline_markdown_emphasis_tokens(text)
    lines = [" ".join(line.split()) for line in text.splitlines()]
    lines = [line for line in lines if line]
    if not lines:
        compact = " ".join(text.split())
        return terminal_deferral_subject(compact) or compact
    deferred_subject = terminal_deferral_subject(" ".join(lines))
    if deferred_subject:
        return deferred_subject
    if len(lines) == 1:
        return terminal_deferral_subject(lines[0]) or lines[0]
    first = lines[0]
    if first.endswith(":"):
        return f"{first} {', '.join(line.rstrip(',') for line in lines[1:])}"
    result = first
    for line in lines[1:]:
        if (
            result.endswith("/")
            or line.startswith("(")
            or re.search(r"\b(and|or|of|for|with)$", result, flags=re.IGNORECASE)
            or (len(lines) == 2 and len(result.split()) <= 2 and len(line.split()) <= 2)
        ):
            result = f"{result} {line}"
        else:
            break
    return " ".join(result.split())


def _label_key(value: str) -> str:
    text = str(value or "")
    if "·" in text:
        text = text.split("·", 1)[0]
    if re.match(r"^\s*proof\s+boundary\b", text, flags=re.IGNORECASE):
        text = "proof boundary"
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def clean_component_description(*, name: str, description: str) -> str:
    """Return concise reader-facing component copy for Atlas payloads."""

    text = _clean_label(description).replace("`", "").strip()
    if not text:
        return ""
    split_match = _LEGACY_COMPONENT_APPENDIX_RE.search(text)
    if split_match is not None:
        text = text[: split_match.start()].strip(" ;,.-")
    stripped_name = _strip_leading_component_name(name=name, text=text)
    if stripped_name and _component_name_key(stripped_name):
        text = stripped_name
    stripped_kind = re.sub(
        r"^(?:service|component|surface|adapter|engine|store|model|resolver)\b\s*",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip()
    if stripped_kind:
        text = stripped_kind
    text = re.sub(
        r"^(?:is\s+)?(?:a|an)\s+[a-z -]+?\s+component\s+responsible\s+for\s+",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip()
    text = re.sub(r"^(?:is\s+)?responsible\s+for\s+", "", text, flags=re.IGNORECASE).strip()
    text = re.sub(
        r"\s+with\s+\S+\s+as\s+its\s+initial(?:\s+evidence\s+anchor)?\.?$",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip(" ;,")
    text = re.sub(r";\s*serve\s+as\b", "; serves as", text, flags=re.IGNORECASE)
    text = _OWNED_ACTION_RE.sub(lambda match: str(match.group(1)), text).strip()
    text = re.sub(r"^owns?\s+owns?\s+", "owns ", text, flags=re.IGNORECASE).strip()
    if not text:
        return ""
    if re.match(r"^owns?\b", text, flags=re.IGNORECASE):
        text = "Owns " + re.sub(r"^owns?\s+", "", text, flags=re.IGNORECASE).strip()
    else:
        text = capitalize_sentence_start_preserving_source_terms(text)
    return _first_sentence(text)


def _strip_leading_component_name(*, name: str, text: str) -> str:
    name_words = _component_name_key(name).split()
    if not name_words:
        return text
    for keep in range(len(name_words), 0, -1):
        pattern = r"^\s*" + r"[\s,/-]+".join(re.escape(word) for word in name_words[:keep]) + r"\b\s*"
        stripped = re.sub(pattern, "", text, count=1, flags=re.IGNORECASE).strip()
        if stripped != text.strip():
            return stripped or text
    return text


def _component_name_key(value: str) -> str:
    text = re.sub(
        r"\b(service|component|surface|adapter|engine|store|model|resolver)\b",
        " ",
        str(value or ""),
        flags=re.IGNORECASE,
    )
    text = re.sub(r"[^a-z0-9]+", " ", text.casefold())
    return " ".join(text.split())


def _subgraph_label(line: str) -> str:
    token = line.strip().split(None, 1)[1].strip() if len(line.strip().split(None, 1)) > 1 else ""
    bracket = re.search(r"\[\s*['\"]?(.+?)['\"]?\s*\]", token)
    if bracket:
        return _clean_label(bracket.group(1))
    quoted = re.match(r"['\"](.+?)['\"]", token)
    if quoted:
        return _clean_label(quoted.group(1))
    identifier = re.split(r"\s|\[", token, maxsplit=1)[0].strip()
    remainder = token[len(identifier) :].strip() if identifier else token
    return _clean_label(remainder or identifier)


def _first_label_match(match: re.Match[str]) -> str:
    for name, value in match.groupdict().items():
        if name != "id" and value:
            return _clean_label(value)
    return ""


def _matching_components(*, label: str, component_rows: Sequence[Mapping[str, str]]) -> tuple[Mapping[str, str], ...]:
    label_tokens = _meaningful_tokens(label)
    if not label_tokens:
        return ()
    label_key = _component_name_key(label)
    exact_matches = [
        row
        for row in component_rows
        if label_key and label_key == _component_name_key(str(row.get("name", "")).strip())
    ]
    if exact_matches:
        return tuple(exact_matches[:1])
    matches: list[tuple[int, Mapping[str, str]]] = []
    for row in component_rows:
        name = str(row.get("name", "")).strip()
        description = str(row.get("description", "")).strip()
        component_tokens = _meaningful_tokens(f"{name} {description}")
        if not component_tokens:
            continue
        overlap = label_tokens & component_tokens
        name_overlap = label_tokens & _meaningful_tokens(name)
        if len(name_overlap) >= 1 and len(overlap) >= 2:
            matches.append((len(overlap) + len(name_overlap), row))
        elif len(overlap) >= 3:
            matches.append((len(overlap), row))
    return tuple(row for _score, row in sorted(matches, key=lambda item: -item[0])[:4])


def _first_sentence(value: str) -> str:
    text = " ".join(str(value or "").split()).strip()
    if not text:
        return ""
    match = re.match(r"(.+?[.!?])(?:\s|$)", text)
    return match.group(1).strip() if match else text.rstrip(".") + "."


def _meaningful_tokens(value: str) -> set[str]:
    tokens = {
        token
        for token in re.findall(r"[a-z0-9][a-z0-9'-]*", str(value or "").casefold())
        if len(token) >= 3 and token not in _COMMON_COMPONENT_TOKENS
    }
    expansions: set[str] = set()
    for token in tokens:
        if token.endswith("ies") and len(token) > 4:
            expansions.add(f"{token[:-3]}y")
        elif token.endswith("s") and len(token) > 3:
            expansions.add(token[:-1])
    return tokens | expansions


def extract_diagram_boxes_from_mermaid(
    source_text: str,
    *,
    component_rows: Sequence[Mapping[str, str]] = (),
) -> tuple[DiagramBoxExplanation, ...]:
    """Extract visible Mermaid labels for exact catalog coverage checks."""
    boxes: list[DiagramBoxExplanation] = []
    seen: set[str] = set()
    explicit_node_ids: set[str] = set()
    graph = atlas_diagram_intelligence.parse_mermaid_graph(source_text)

    for raw_line in str(source_text or "").splitlines():
        line = raw_line.split("%%", 1)[0].strip()
        if not line:
            continue
        lowered = line.lower()
        if lowered == "end":
            continue
        if lowered.startswith(("flowchart", "graph ", "sequencediagram")):
            continue
        if lowered.startswith(("autonumber", "note ", "activate ", "deactivate ")):
            continue
        if lowered.startswith("participant "):
            label = _sequence_participant_label(line)
            display_label = _resolved_box_label(label=label, component_rows=component_rows)
            key = _label_key(display_label)
            if display_label and key and key not in seen:
                boxes.append(
                    DiagramBoxExplanation(
                        label=display_label,
                        role="",
                        description="",
                    )
                )
                seen.add(key)
            continue
        if lowered.startswith("subgraph "):
            label = _subgraph_label(line)
            if label:
                key = _label_key(label)
                if key and key not in seen:
                    boxes.append(
                        DiagramBoxExplanation(
                            label=label,
                            role="",
                            description="",
                        )
                    )
                    seen.add(key)
            continue
        for match in _NODE_LABEL_RE.finditer(line):
            node_id = str(match.group("id") or "").strip()
            if node_id.lower() in {"subgraph", "flowchart", "graph", "style", "classdef", "linkstyle"}:
                continue
            label = _first_label_match(match)
            key = _label_key(label)
            if not label or not key or key in seen:
                continue
            display_label = _resolved_box_label(label=label, component_rows=component_rows)
            display_key = _label_key(display_label)
            if display_key and display_key in seen:
                continue
            boxes.append(
                DiagramBoxExplanation(
                    label=display_label,
                    role="",
                    description="",
                )
            )
            seen.add(display_key or key)
            explicit_node_ids.add(node_id)
    for node_id in graph.node_ids():
        # Both parsers see these nodes, but may format their display labels differently.
        if node_id in explicit_node_ids:
            continue
        label = graph.label(node_id)
        key = _label_key(label)
        if not label or not key or key in seen:
            continue
        if _low_signal_generated_graph_label(label=label, node_id=node_id):
            continue
        display_label = _resolved_box_label(label=label, component_rows=component_rows)
        display_key = _label_key(display_label)
        if display_key and display_key in seen:
            continue
        boxes.append(
            DiagramBoxExplanation(
                label=display_label,
                role="",
                description="",
            )
        )
        seen.add(display_key or key)
    return tuple(boxes)


def _sequence_participant_label(line: str) -> str:
    """Return the visible label from a Mermaid sequence participant row."""
    match = re.match(
        r"^\s*(?:participant|actor)\s+\S+\s+as\s+(.+?)\s*$",
        line,
        flags=re.IGNORECASE,
    )
    if match:
        return _clean_label(match.group(1))
    match = re.match(r"^\s*(?:participant|actor)\s+(.+?)\s*$", line, flags=re.IGNORECASE)
    return _clean_label(match.group(1)) if match else ""


def _resolved_box_label(*, label: str, component_rows: Sequence[Mapping[str, str]]) -> str:
    """Resolve generated/truncated labels to full component labels when catalog truth is available."""
    clean = _clean_label(label)
    if "…" not in clean and "..." not in clean:
        return clean
    matches = _matching_components(label=clean, component_rows=component_rows)
    if len(matches) != 1:
        return clean
    name = str(matches[0].get("name", "")).strip()
    return name or clean


def _low_signal_generated_graph_label(*, label: str, node_id: str) -> bool:
    clean_label = _clean_label(label)
    clean_id = _clean_label(node_id)
    if not clean_label:
        return True
    if clean_label.casefold() in {"primary", "secondary", "later", "optional"}:
        return True
    if re.fullmatch(r"(?:component|actor|external|owner|proof|node)\d+", clean_label, flags=re.IGNORECASE):
        return True
    if clean_label.casefold() != clean_id.casefold():
        return False
    return bool(re.fullmatch(r"[A-Z]|\d+|node\d+", clean_label, flags=re.IGNORECASE))


def catalog_box_copy_errors(*, box: Mapping[str, Any], context: str) -> tuple[str, ...]:
    """Return authoring errors for hand-written Atlas diagram-box copy."""
    label = _clean_label(str(box.get("label", "")).strip())
    description = display_text.strip_inline_markdown_emphasis(box.get("description", ""))
    errors: list[str] = []
    if not label or not description:
        return (f"{context} requires non-empty `label` and `description`",)
    if _PLACEHOLDER_RE.search(description):
        errors.append(f"{context} description must not use placeholder copy")
    if _MECHANICAL_DESCRIPTION_RE.search(description):
        errors.append(f"{context} description must explain project meaning, not diagram mechanics")
    word_count = len(re.findall(r"[A-Za-z0-9][A-Za-z0-9'-]*", description))
    if word_count < 8:
        errors.append(f"{context} description must explain the box in a complete sentence")
    if description[-1:] not in {".", "!", "?"}:
        errors.append(f"{context} description must end with sentence punctuation")
    label_words = set(re.findall(r"[a-z0-9]+", label.lower()))
    description_words = set(re.findall(r"[a-z0-9]+", description.lower()))
    if label_words and description_words and description_words.issubset(label_words):
        errors.append(f"{context} description must add meaning beyond the label")
    return tuple(errors)


def normalize_catalog_diagram_boxes(
    *,
    raw_boxes: Any,
    context: str,
    errors: list[str],
) -> tuple[DiagramBoxExplanation, ...]:
    """Validate and normalize catalog-authored diagram box explanations."""
    if raw_boxes in (None, ""):
        return ()
    if not isinstance(raw_boxes, list):
        errors.append(f"{context}: `diagram_boxes` must be a list when present")
        return ()
    normalized: list[DiagramBoxExplanation] = []
    seen: set[str] = set()
    for box_idx, box in enumerate(raw_boxes):
        box_context = f"{context}: diagram_boxes[{box_idx}]"
        if not isinstance(box, Mapping):
            errors.append(f"{box_context} must be an object")
            continue
        errors.extend(catalog_box_copy_errors(box=box, context=box_context))
        label = _clean_label(str(box.get("label", "")).strip())
        description = display_text.strip_inline_markdown_emphasis(box.get("description", ""))
        role = str(box.get("role", "")).strip()
        details = None
        if "details" in box:
            try:
                details = tuple(atlas_box_details(box["details"]))
            except ValueError as exc:
                errors.append(f"{box_context}: {exc}")
                continue
        key = _label_key(label)
        if not label or not description:
            continue
        if key in seen:
            errors.append(f"{box_context} duplicates diagram box label `{label}`")
            continue
        seen.add(key)
        normalized.append(
            DiagramBoxExplanation(
                label=label,
                role=role,
                description=description,
                details=details,
            )
        )
    return tuple(normalized)


def merge_diagram_box_explanations(
    *,
    source_text: str,
    catalog_boxes: Iterable[DiagramBoxExplanation],
    component_rows: Sequence[Mapping[str, str]] = (),
    diagram_title: str = "",
    diagram_summary: str = "",
) -> tuple[dict[str, Any], ...]:
    """Keep source label inventory and add only catalog-authored explanations."""
    inventory = extract_diagram_boxes_from_mermaid(source_text, component_rows=component_rows)
    authored = tuple(catalog_boxes)
    authored_by_label = {_label_key(box.label): box for box in authored}
    merged: list[DiagramBoxExplanation] = []
    used: set[str] = set()
    for box in inventory:
        key = _label_key(box.label)
        override = authored_by_label.get(key)
        merged.append(override or box)
        if override is not None:
            used.add(key)
    merged.extend(box for box in authored if _label_key(box.label) not in used)
    return tuple(box.as_dict() for box in merged)


def diagram_box_labels(boxes: Iterable[Mapping[str, Any]]) -> tuple[str, ...]:
    """Return normalized labels for coverage checks."""
    return tuple(_label_key(str(box.get("label", ""))) for box in boxes if _label_key(str(box.get("label", ""))))
