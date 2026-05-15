"""Atlas diagram-box extraction and reader-facing explanation rules."""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

from odylith.runtime.surfaces import atlas_diagram_intelligence


_PLACEHOLDER_RE = re.compile(r"\b(tbd|todo|n/a|none|placeholder|fixme)\b", re.IGNORECASE)
_MECHANICAL_DESCRIPTION_RE = re.compile(
    r"\b("
    r"part of the path|incoming arrows|outgoing arrows|hands off|branch point|"
    r"read the boxes inside|diagram mechanics|through the arrows"
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


@dataclass(frozen=True)
class DiagramBoxContext:
    """Context used to make generated box copy about the project, not the arrows."""

    title: str = ""
    summary: str = ""
    source_text: str = ""
    components: tuple[Mapping[str, str], ...] = ()

    @property
    def project_name(self) -> str:
        return _project_name(title=self.title, summary=self.summary, source_text=self.source_text)

    @property
    def tracked_object(self) -> str:
        return _tracked_object_phrase(self.search_text)

    @property
    def tracked_objects(self) -> str:
        singular = self.tracked_object
        if singular.endswith("y"):
            return f"{singular[:-1]}ies"
        if singular.endswith("s"):
            return singular
        return f"{singular}s"

    @property
    def search_text(self) -> str:
        component_text = " ".join(
            f"{row.get('name', '')} {row.get('description', '')}" for row in self.components
        )
        return " ".join((self.title, self.summary, self.source_text, component_text))


def _clean_label(value: str) -> str:
    text = html.unescape(str(value or ""))
    text = re.sub(r"<\s*br\s*/?\s*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    lines = [" ".join(line.split()) for line in text.splitlines()]
    lines = [line for line in lines if line]
    if not lines:
        return " ".join(text.split())
    if len(lines) == 1:
        return lines[0]
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


def _generated_container_description(label: str, context: DiagramBoxContext) -> str:
    project = context.project_name or _sentence_subject(label)
    if _label_key(label) == _label_key(project):
        return (
            f"{label} is the product boundary. It contains the actors, interfaces, records, controls, "
            "and evidence paths that must work together before the release claim can be trusted."
        )
    return (
        f"{label} is the product boundary for {project}. It contains the actors, interfaces, records, "
        "controls, and evidence paths that must work together before the release claim can be trusted."
    )


def _generated_node_description(
    label: str,
    container_stack: Sequence[str],
    context: DiagramBoxContext,
) -> str:
    role_sentence = _node_action_sentence(label, context=context)
    if container_stack:
        container = container_stack[-1]
        return f"Within {container}, {role_sentence}"
    return role_sentence


def _node_action_sentence(label: str, *, context: DiagramBoxContext) -> str:
    clean = _clean_label(label).strip()
    lowered = clean.lower()
    subject = _sentence_subject(clean)
    project = context.project_name or "the product"
    tracked_object = context.tracked_object
    tracked_objects = context.tracked_objects
    if _has_any(lowered, ("steward", "owner", "operator")) and not _has_any(
        lowered,
        ("web", "surface", "service", "interface", "status"),
    ):
        return (
            f"{subject} owns or manages the {tracked_objects} being tracked in {project}. "
            f"They need trustworthy identity, state, evidence, and history for each {tracked_object} before decisions move forward."
        )
    if _has_any(lowered, ("observer", "community monitor", "field monitor", "monitor")) and not _has_any(lowered, ("service", "provider", "adapter")):
        return (
            f"{subject} captures real-world observations for {tracked_objects}. "
            "Their input only becomes trusted when it carries source, time, location, evidence, and review context."
        )
    if _has_any(lowered, ("verifier", "auditor", "reviewer")):
        return (
            f"{subject} checks whether a {tracked_object} claim is supported. "
            "They need to trace the claim back to the active record, source evidence, derivation step, and audit history."
        )
    if _has_any(lowered, ("coordinator", "program lead", "program manager")):
        return (
            f"{subject} manages the program across owners, submitters, reviewers, and scoped {tracked_objects}. "
            "They need to know what is in scope, which evidence is missing, and what is ready for the first release."
        )
    if _has_any(
        lowered,
        (
            "remote-sensing provider",
            "remote-sensing providers",
            "remote sensing provider",
            "remote sensing providers",
            "imagery provider",
            "imagery providers",
            "satellite",
            "sensor provider",
            "sensor providers",
        ),
    ):
        return (
            f"{subject} is an external source of remote signals for {tracked_objects}. "
            "Those signals matter only when they retain provider, sensor, time, location, and provenance."
        )
    if _has_any(lowered, ("remote sensing adapter", "remote-sensing adapter", "imagery adapter")):
        return (
            f"{subject} turns remote-observation signals into project evidence. "
            f"It connects provider output to the right {tracked_object}, active boundary or state version, and provenance record."
        )
    if _has_any(lowered, ("boundary source", "cadastral", "geometry source", "land record")):
        return (
            f"{subject} supplies the external boundary or ownership reference for {tracked_objects}. "
            f"The release needs this because a claim is meaningless unless the product knows which {tracked_object} and version it describes."
        )
    if _has_any(lowered, ("identity provider", "idp")):
        return (
            f"{subject} supplies trusted actor and organization identity. "
            "It lets the product distinguish who submitted, changed, reviewed, or approved each record."
        )
    if _has_any(lowered, ("auth", "authentication", "authorization", "session")):
        return (
            f"{subject} attributes product actions to a known actor. "
            f"It matters because {tracked_object} changes, observations, evidence submissions, and reviews must be accountable."
        )
    if _has_any(lowered, ("privacy", "sharing", "redaction", "access")):
        return (
            f"{subject} governs who can see records, evidence, derived state, and audit history. "
            "It matters when project data is sensitive, partner-scoped, legally constrained, or unsafe to expose broadly."
        )
    if _has_any(lowered, ("notification", "sms", "email", "alert")):
        return (
            f"{subject} is a later-wave communication path. "
            "It should notify the right people when state changes, evidence is missing, or review is needed, but it should not define the first release proof boundary."
        )
    if _has_any(lowered, ("field capture", "capture surface", "mobile capture")):
        return (
            f"{subject} lets field users submit evidence against a known {tracked_object}. "
            "It should capture observation type, time, location, notes, media references, and source identity without overwriting prior history."
        )
    if _has_any(lowered, ("web surface", "portal", "console", "workspace", "dashboard", "ui", "interface")):
        return (
            f"{subject} is the primary user surface for reviewing and changing {tracked_objects}. "
            "It should show identity, current state, recent observations, evidence status, and review state in one coherent view."
        )
    if _has_any(lowered, ("core services", "record core", "evidence core", "core:")):
        return (
            f"{subject} owns the trusted record layer for {project}: records, state versions, evidence links, derivation, and audit history. "
            "It matters because the first release must turn scattered inputs into traceable claims."
        )
    matched_components = _matching_components(label=clean, context=context)
    if matched_components:
        return _component_grounded_sentence(
            subject=subject,
            label=clean,
            context=context,
            matched_components=matched_components,
        )
    if _has_any(lowered, ("product", "program", "release")):
        return f"{subject} defines the product scope, target outcome, and proof boundary that release work must satisfy."
    if _has_any(lowered, ("interface", "dashboard", "ui", "surface", "portal", "console", "app", "workspace")):
        return f"{subject} gives users the current state, available action, and supporting evidence for the part of the product they own."
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
    return (
        f"{subject} is a named responsibility in {project}. It should explain what it owns, what it receives or produces, "
        "and why that responsibility matters for the release proof."
    )


def _project_name(*, title: str, summary: str, source_text: str) -> str:
    title_text = _clean_label(title).strip()
    if title_text and not re.search(r"\b(context|sequence|ownership|proof|topology|diagram|view|state model)\b", title_text, re.IGNORECASE):
        return title_text
    summary_text = _clean_label(summary)
    match = re.search(
        r"\b(?:of|for|inside)\s+the\s+([A-Z][A-Za-z0-9 -]+?)(?:\s+showing|[,.]|$)",
        summary_text,
    )
    if match:
        return match.group(1).strip()
    subgraph = re.search(r"subgraph\s+\w+\s+\[\s*['\"]([^'\"]+)['\"]\s*\]", source_text)
    if subgraph:
        return _clean_label(subgraph.group(1))
    return title_text or "the product"


def _tracked_object_phrase(corpus: str) -> str:
    lowered = corpus.casefold()
    object_terms = (
        "parcel",
        "boundary",
        "observation",
        "evidence record",
        "state record",
        "plant",
        "order",
        "shipment",
        "account",
        "case",
        "request",
        "experiment",
        "asset",
        "document",
    )
    generic_modifiers = {
        "active",
        "available",
        "current",
        "derived",
        "external",
        "first",
        "known",
        "latest",
        "owned",
        "owns",
        "primary",
        "reviewed",
        "source",
        "stable",
        "trusted",
        "versioned",
        "view",
    }
    for term in object_terms:
        for match in re.finditer(rf"\b([a-z][a-z-]{{2,}})\s+({re.escape(term)})s?\b", lowered):
            if match.group(1) not in generic_modifiers:
                return f"{match.group(1)} {match.group(2)}"
    for phrase in object_terms:
        if re.search(rf"\b{re.escape(phrase)}s?\b", lowered):
            return phrase
    return "tracked record"


def _matching_components(*, label: str, context: DiagramBoxContext) -> tuple[Mapping[str, str], ...]:
    label_tokens = _meaningful_tokens(label)
    if not label_tokens:
        return ()
    matches: list[tuple[int, Mapping[str, str]]] = []
    for row in context.components:
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


def _component_grounded_sentence(
    *,
    subject: str,
    label: str,
    context: DiagramBoxContext,
    matched_components: Sequence[Mapping[str, str]],
) -> str:
    project = context.project_name or "the product"
    tracked_object = context.tracked_object
    tracked_objects = context.tracked_objects
    component_names = [str(row.get("name", "")).strip() for row in matched_components if str(row.get("name", "")).strip()]
    component_descriptions = [
        _first_sentence(str(row.get("description", "")).strip())
        for row in matched_components
        if str(row.get("description", "")).strip()
    ]
    if len(matched_components) > 1 or _has_any(label.casefold(), ("core services", "record core", "evidence core", "core:")):
        owned = _join_list(component_names) or "the core records, evidence, state, and audit responsibilities"
        detail = f" It includes {component_descriptions[0]}" if component_descriptions else ""
        return (
            f"{subject} is the trusted record core for {project}. It ties {owned} into one release boundary "
            f"so {tracked_object} claims can be traced from input to review.{detail}"
        )
    description = component_descriptions[0] if component_descriptions else ""
    if description:
        return (
            f"{subject} owns a concrete {project} responsibility: {description[0].lower() + description[1:]}. "
            f"It matters because release proof must show how this responsibility receives, preserves, or produces trusted {tracked_object} evidence."
        )
    return (
        f"{subject} owns a concrete {project} responsibility for {tracked_objects}. "
        "It matters because release proof must show what it receives, preserves, or produces."
    )


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


def _join_list(values: Sequence[str]) -> str:
    rows = [str(value).strip() for value in values if str(value).strip()]
    if not rows:
        return ""
    if len(rows) == 1:
        return rows[0]
    if len(rows) == 2:
        return f"{rows[0]} and {rows[1]}"
    return f"{', '.join(rows[:-1])}, and {rows[-1]}"


def _sentence_subject(label: str) -> str:
    text = _clean_label(label).strip().rstrip(".")
    text = re.sub(r"\s*\([^)]*\)\s*$", "", text).strip()
    return text[:1].upper() + text[1:] if text else "This step"


def _has_any(value: str, markers: Sequence[str]) -> bool:
    return any(re.search(rf"\b{re.escape(marker)}\b", value) for marker in markers)


def _looks_like_state_object(label: str) -> bool:
    lowered = label.lower().strip()
    if lowered.startswith(("one ", "a ", "an ", "the ")):
        return True
    return bool(re.search(r"\b(state|case|request|order|endpoint|contract|experiment|shipment|asset|record|object)\b", lowered))


def extract_diagram_boxes_from_mermaid(
    source_text: str,
    *,
    component_rows: Sequence[Mapping[str, str]] = (),
    diagram_title: str = "",
    diagram_summary: str = "",
) -> tuple[DiagramBoxExplanation, ...]:
    """Extract visible flowchart containers and node boxes from Mermaid source."""
    boxes: list[DiagramBoxExplanation] = []
    seen: set[str] = set()
    container_stack: list[str] = []
    graph = atlas_diagram_intelligence.parse_mermaid_graph(source_text)
    context = DiagramBoxContext(
        title=diagram_title,
        summary=diagram_summary,
        source_text=source_text,
        components=tuple(component_rows),
    )

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
                            description=_generated_container_description(label, context),
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
            graph_description = atlas_diagram_intelligence.node_explanation_from_graph(
                label=label,
                source_text=source_text,
            )
            semantic_description = _generated_node_description(label, container_stack, context)
            graph_role = atlas_diagram_intelligence.node_role_from_graph(
                label=label,
                source_text=source_text,
            )
            role = container_stack[-1] if container_stack else (graph_role or "Step")
            boxes.append(
                DiagramBoxExplanation(
                    label=label,
                    role=role,
                    description=_merge_node_description(
                        semantic_description=semantic_description,
                        graph_description=graph_description,
                    ),
                    generated=True,
                )
            )
            seen.add(key)
    for node_id in graph.node_ids():
        label = graph.label(node_id)
        key = _label_key(label)
        if not label or not key or key in seen:
            continue
        if _low_signal_generated_graph_label(label=label, node_id=node_id):
            continue
        boxes.append(
            DiagramBoxExplanation(
                label=label,
                role=atlas_diagram_intelligence.describe_graph_node_role(graph=graph, node_id=node_id),
                description=atlas_diagram_intelligence.describe_graph_node(graph=graph, node_id=node_id)
                or _generated_node_description(label, (), context),
                generated=True,
            )
        )
        seen.add(key)
    return tuple(boxes)


def _merge_node_description(*, semantic_description: str, graph_description: str) -> str:
    semantic = _clean_label(semantic_description)
    graph = _clean_label(graph_description)
    if not graph:
        return semantic
    if _MECHANICAL_DESCRIPTION_RE.search(graph):
        return semantic
    if semantic and "is a named responsibility" not in semantic:
        return semantic
    if not semantic or "is a named responsibility" in semantic:
        return graph
    if graph.casefold() == semantic.casefold() or graph.casefold() in semantic.casefold():
        return semantic
    return f"{semantic} {graph}"


def _low_signal_generated_graph_label(*, label: str, node_id: str) -> bool:
    clean_label = _clean_label(label)
    clean_id = _clean_label(node_id)
    if not clean_label:
        return True
    if clean_label.casefold() != clean_id.casefold():
        return False
    return bool(re.fullmatch(r"[A-Z]|\d+|node\d+", clean_label, flags=re.IGNORECASE))


def catalog_box_copy_errors(*, box: Mapping[str, Any], context: str) -> tuple[str, ...]:
    """Return authoring errors for hand-written Atlas diagram-box copy."""
    label = str(box.get("label", "")).strip()
    description = str(box.get("description", "")).strip()
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
    component_rows: Sequence[Mapping[str, str]] = (),
    diagram_title: str = "",
    diagram_summary: str = "",
) -> tuple[dict[str, str], ...]:
    """Merge Mermaid-derived box inventory with catalog-authored explanations."""
    generated = extract_diagram_boxes_from_mermaid(
        source_text,
        component_rows=component_rows,
        diagram_title=diagram_title,
        diagram_summary=diagram_summary,
    )
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
