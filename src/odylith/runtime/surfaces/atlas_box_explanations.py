"""Atlas diagram-box extraction and reader-facing explanation rules."""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence


_PLACEHOLDER_RE = re.compile(r"\b(tbd|todo|n/a|none|placeholder|fixme)\b", re.IGNORECASE)
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
    """Reader-facing explanation for one visible Mermaid box."""

    label: str
    role: str
    description: str
    generated: bool = False

    def as_dict(self) -> dict[str, str]:
        """Return the box explanation as a JSON-ready Atlas payload row."""
        return {
            "label": self.label,
            "role": self.role,
            "description": self.description,
        }


def _clean_label(value: str) -> str:
    text = html.unescape(str(value or ""))
    text = re.sub(r"<\s*br\s*/?\s*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    lines = [" ".join(line.split()) for line in text.splitlines()]
    lines = [line for line in lines if line]
    return lines[0] if lines else " ".join(text.split())


def _label_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()


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


def _generated_container_description(label: str) -> str:
    return (
        f"This container groups the {label} part of the diagram. "
        "Read the boxes inside it as the concrete items that belong to that area."
    )


def _generated_node_description(label: str, container_stack: Sequence[str]) -> str:
    if container_stack:
        container = container_stack[-1]
        return (
            f"This box represents {label} inside {container}. "
            "Follow its arrows to see what feeds it and what it affects."
        )
    return (
        f"This box represents {label}. "
        "Follow its arrows to see what feeds it and what it affects."
    )


def extract_diagram_boxes_from_mermaid(source_text: str) -> tuple[DiagramBoxExplanation, ...]:
    """Extract visible flowchart containers and node boxes from Mermaid source."""
    boxes: list[DiagramBoxExplanation] = []
    seen: set[str] = set()
    container_stack: list[str] = []

    for raw_line in str(source_text or "").splitlines():
        line = raw_line.split("%%", 1)[0].strip()
        if not line:
            continue
        lowered = line.lower()
        if lowered == "end":
            if container_stack:
                container_stack.pop()
            continue
        if lowered.startswith(("flowchart", "graph ")):
            continue
        if lowered.startswith("subgraph "):
            label = _subgraph_label(line)
            if label:
                key = _label_key(label)
                if key and key not in seen:
                    boxes.append(
                        DiagramBoxExplanation(
                            label=label,
                            role="Container",
                            description=_generated_container_description(label),
                            generated=True,
                        )
                    )
                    seen.add(key)
                container_stack.append(label)
            continue
        for match in _NODE_LABEL_RE.finditer(line):
            node_id = str(match.group("id") or "").strip().lower()
            if node_id in {"subgraph", "flowchart", "graph", "style", "classdef", "linkstyle"}:
                continue
            label = _first_label_match(match)
            key = _label_key(label)
            if not label or not key or key in seen:
                continue
            role = container_stack[-1] if container_stack else "Diagram box"
            boxes.append(
                DiagramBoxExplanation(
                    label=label,
                    role=role,
                    description=_generated_node_description(label, container_stack),
                    generated=True,
                )
            )
            seen.add(key)
    return tuple(boxes)


def catalog_box_copy_errors(*, box: Mapping[str, Any], context: str) -> tuple[str, ...]:
    """Return authoring errors for hand-written Atlas diagram-box copy."""
    label = str(box.get("label", "")).strip()
    description = str(box.get("description", "")).strip()
    errors: list[str] = []
    if not label or not description:
        return (f"{context} requires non-empty `label` and `description`",)
    if _PLACEHOLDER_RE.search(description):
        errors.append(f"{context} description must not use placeholder copy")
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
        label = str(box.get("label", "")).strip()
        description = str(box.get("description", "")).strip()
        role = str(box.get("role", "")).strip()
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
                generated=False,
            )
        )
    return tuple(normalized)


def merge_diagram_box_explanations(
    *,
    source_text: str,
    catalog_boxes: Iterable[DiagramBoxExplanation],
) -> tuple[dict[str, str], ...]:
    """Merge Mermaid-derived box inventory with catalog-authored explanations."""
    generated = extract_diagram_boxes_from_mermaid(source_text)
    catalog_rows = tuple(catalog_boxes)
    catalog_by_label = {_label_key(box.label): box for box in catalog_rows if _label_key(box.label)}
    merged: list[DiagramBoxExplanation] = []
    used: set[str] = set()
    for generated_box in generated:
        key = _label_key(generated_box.label)
        override = catalog_by_label.get(key)
        if override is None:
            merged.append(generated_box)
        else:
            merged.append(
                DiagramBoxExplanation(
                    label=override.label,
                    role=override.role or generated_box.role,
                    description=override.description,
                    generated=False,
                )
            )
            used.add(key)
    for catalog_box in catalog_rows:
        key = _label_key(catalog_box.label)
        if key and key not in used and key not in {_label_key(box.label) for box in generated}:
            merged.append(catalog_box)
    return tuple(box.as_dict() for box in merged)


def diagram_box_labels(boxes: Iterable[Mapping[str, Any]]) -> tuple[str, ...]:
    """Return normalized labels for coverage checks."""
    return tuple(_label_key(str(box.get("label", ""))) for box in boxes if _label_key(str(box.get("label", ""))))
