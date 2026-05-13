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
        f"{label} defines a responsibility zone in the diagram. "
        "Read the boxes inside it as the concrete work, data, decisions, or proof owned by that zone."
    )


def _generated_node_description(label: str, container_stack: Sequence[str]) -> str:
    role_sentence = _node_action_sentence(label)
    if container_stack:
        container = container_stack[-1]
        return f"Inside {container}, {role_sentence}"
    return role_sentence


def _node_action_sentence(label: str) -> str:
    clean = _clean_label(label).strip()
    lowered = clean.lower()
    subject = _sentence_subject(clean)
    if _has_any(lowered, ("product", "program", "release")):
        return f"{subject} defines the product scope, outcome, and proof boundary this diagram is organizing."
    if _has_any(lowered, ("interface", "dashboard", "ui", "surface", "portal", "console", "app", "workspace")):
        return f"{subject} shows the current state, available action, and evidence to the person using the system."
    if _has_any(lowered, ("radar", "backlog", "workstream", "queue")):
        return f"{subject} tracks the work choices, priorities, and next slices that need governed follow-through."
    if _has_any(lowered, ("atlas", "diagram", "topology", "map")):
        return f"{subject} shows the system shape, ownership boundaries, and flow relationships reviewers need to understand."
    if _has_any(lowered, ("compass", "timeline", "status")):
        return f"{subject} summarizes current runtime state, recent movement, and the evidence behind the status."
    if _has_any(lowered, ("plan", "plans", "implementation path", "implementation sequence")):
        return f"{subject} turns selected work into an implementation path, validation obligation, and release gate."
    if _has_any(lowered, ("router", "routing")):
        return f"{subject} chooses where work should go next and records why that route is admissible."
    if _has_any(lowered, ("orchestrator", "coordination")):
        return f"{subject} coordinates bounded work across owners and brings completion evidence back into the flow."
    if _has_any(lowered, ("broker", "proposal", "intervention", "observation", "assist")):
        return f"{subject} decides what should be shown to the operator and when it is safe to surface."
    if _has_any(lowered, ("chatter", "chat", "message", "narration")):
        return f"{subject} turns governed state into user-visible language without changing the underlying source truth."
    if _has_any(lowered, ("handshake", "contract")):
        return f"{subject} passes agreed state across a boundary and preserves the rules the next step must obey."
    if _has_any(lowered, ("owner", "operator", "reviewer", "approver", "advocate", "user", "customer", "patient", "merchant", "scientist", "engineer", "maintainer")):
        return f"{subject} makes or accepts the decisions this part of the flow depends on."
    if _has_any(lowered, ("sensor", "sensing", "monitor", "measurement", "telemetry", "signal", "probe", "scanner")):
        return f"{subject} measures the current state and feeds the decision or proof step that follows."
    if _has_any(lowered, ("decision", "policy", "rule", "eligibility", "approval", "review", "gate", "core", "engine", "tribunal")):
        return f"{subject} decides whether the next action is allowed, blocked, or ready for review."
    if _has_any(lowered, ("controller", "actuator", "pump", "dosing", "executor", "execution", "worker", "runner", "adapter")):
        return f"{subject} performs the bounded action and should expose the result for verification."
    if _has_any(lowered, ("log", "record", "ledger", "evidence", "audit", "receipt", "proof", "history", "casebook")):
        return f"{subject} records the evidence needed to review what happened and why it was allowed."
    if _has_any(lowered, ("repo", "registry", "catalog", "store", "database", "source", "memory", "bundle", "snapshot")):
        return f"{subject} stores the source information that downstream boxes read or update."
    if _has_any(lowered, ("connector", "gateway", "api", "integration", "webhook", "bridge", "rail")):
        return f"{subject} moves data or requests across a system boundary and should preserve handoff evidence."
    if _looks_like_state_object(clean):
        return f"{subject} is the object whose state changes as the flow moves from trigger to outcome."
    return f"{subject} carries a concrete step in the flow; its incoming arrows show prerequisites and its outgoing arrows show what it enables next."


def _sentence_subject(label: str) -> str:
    text = _clean_label(label).strip().rstrip(".")
    return text[:1].upper() + text[1:] if text else "This step"


def _has_any(value: str, markers: Sequence[str]) -> bool:
    return any(re.search(rf"\b{re.escape(marker)}\b", value) for marker in markers)


def _looks_like_state_object(label: str) -> bool:
    lowered = label.lower().strip()
    if lowered.startswith(("one ", "a ", "an ", "the ")):
        return True
    return bool(re.search(r"\b(state|case|request|order|endpoint|contract|experiment|shipment|asset|record|object)\b", lowered))


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
