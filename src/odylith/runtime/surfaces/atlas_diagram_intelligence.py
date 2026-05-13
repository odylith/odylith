"""Graph-derived Atlas diagram narration.

The Atlas UI should explain the diagram the operator is looking at, not recite
generic Mermaid reading advice. This module keeps that narration deterministic
and host-agnostic by deriving copy from the Mermaid graph structure itself.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from typing import Any, Mapping, Sequence


_NODE_SHAPE_RE = re.compile(
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
_STATE_ALIAS_RE = re.compile(r'^state\s+"(?P<label>[^"]+)"\s+as\s+(?P<id>[A-Za-z][\w.-]*)\s*$', re.IGNORECASE)
_STATE_LABEL_RE = re.compile(r'^(?P<id>[A-Za-z][\w.-]*)\s*:\s*(?P<label>.+?)\s*$')
_STATE_EDGE_RE = re.compile(
    r"^(?P<src>\[\*\]|[A-Za-z][\w.-]*)\s*(?P<arrow>-+>|-->|==>|\.?-+>|<-+|<--)\s*"
    r"(?P<dst>\[\*\]|[A-Za-z][\w.-]*)(?:\s*:\s*(?P<label>.+?))?\s*$"
)
_FLOW_PIPE_EDGE_RE = re.compile(
    r"^(?P<src>[A-Za-z][\w.-]*)\s*(?:-->|==>|-\.->|-.->)\s*\|\s*(?P<label>[^|]+?)\s*\|\s*"
    r"(?P<dst>[A-Za-z][\w.-]*)\s*$"
)
_FLOW_DASH_EDGE_RE = re.compile(
    r"^(?P<src>[A-Za-z][\w.-]*)\s*(?:--|==|-\.|-\.)\s*(?P<label>.+?)\s*(?:-->|==>|\.->|->)\s*"
    r"(?P<dst>[A-Za-z][\w.-]*)\s*$"
)
_FLOW_EDGE_RE = re.compile(
    r"^(?P<src>[A-Za-z][\w.-]*)\s*(?:-->|==>|-\.->|-.->|---)\s*(?P<dst>[A-Za-z][\w.-]*)\s*$"
)
_WORD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9'-]*")
_FAILURE_RE = re.compile(
    r"\b(blocked|block|fault|fail|failed|failure|error|missing|stale|unsafe|risk|rejected|reject|denied|unresolved)\b",
    re.IGNORECASE,
)
_SUCCESS_RE = re.compile(
    r"\b(stable|done|complete|completed|approved|valid|validated|verified|ready|released|success|safe|accepted)\b",
    re.IGNORECASE,
)
_ACTION_RE = re.compile(
    r"\b(action|execute|execution|run|runner|dose|dosing|pump|write|create|generate|apply|approve|review|coordinate|ship|release)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class MermaidEdge:
    """One Mermaid transition between visible nodes."""

    source_id: str
    target_id: str
    label: str = ""


@dataclass(frozen=True)
class MermaidGraph:
    """Normalized Mermaid graph used for reader-facing narration."""

    kind: str
    nodes: Mapping[str, str]
    edges: tuple[MermaidEdge, ...]

    def label(self, node_id: str) -> str:
        """Return the reader-facing label for a node id."""
        token = str(node_id or "").strip()
        if token == "[*]":
            return "Start"
        return self.nodes.get(token, _humanize_identifier(token))

    def incoming(self, node_id: str) -> tuple[MermaidEdge, ...]:
        """Return incoming edges for a node."""
        return tuple(edge for edge in self.edges if edge.target_id == node_id)

    def outgoing(self, node_id: str) -> tuple[MermaidEdge, ...]:
        """Return outgoing edges for a node."""
        return tuple(edge for edge in self.edges if edge.source_id == node_id)

    def node_ids(self) -> tuple[str, ...]:
        """Return visible non-start node ids in source order."""
        return tuple(node_id for node_id in self.nodes if node_id != "[*]")


@dataclass(frozen=True)
class DiagramNarrative:
    """Diagram-level explanation fields used by Atlas."""

    summary: str
    read_guide: str
    generated: bool


def build_diagram_narrative(
    *,
    title: str,
    kind: str,
    summary: str,
    read_guide: str,
    source_text: str,
) -> DiagramNarrative:
    """Return stronger diagram copy when Mermaid structure carries enough signal."""

    graph = parse_mermaid_graph(source_text)
    if len(graph.node_ids()) < 3 or len(graph.edges) < 2:
        return DiagramNarrative(summary=_sentence(summary), read_guide=_sentence(read_guide), generated=False)

    generated_summary = _diagram_summary(graph=graph, title=title, kind=kind)
    generated_read_guide = _diagram_read_guide(graph=graph, kind=kind)
    if not generated_summary or not generated_read_guide:
        return DiagramNarrative(summary=_sentence(summary), read_guide=_sentence(read_guide), generated=False)

    if _copy_is_specific(summary, graph) and _copy_is_specific(read_guide, graph):
        return DiagramNarrative(summary=_sentence(summary), read_guide=_sentence(read_guide), generated=False)
    return DiagramNarrative(summary=generated_summary, read_guide=generated_read_guide, generated=True)


def parse_mermaid_graph(source_text: str) -> MermaidGraph:
    """Parse enough Mermaid structure to explain flowcharts and state diagrams."""

    kind = ""
    nodes: dict[str, str] = {}
    edges: list[MermaidEdge] = []

    for raw_line in str(source_text or "").splitlines():
        line = raw_line.split("%%", 1)[0].strip().rstrip(";")
        if not line:
            continue
        lowered = line.lower()
        if lowered.startswith(("flowchart", "graph ", "statediagram")):
            kind = line.split(None, 1)[0].strip()
            continue
        if lowered in {"end"} or lowered.startswith(("classdef ", "class ", "style ", "linkstyle ", "direction ")):
            continue
        if lowered.startswith("subgraph "):
            continue

        alias = _STATE_ALIAS_RE.match(line)
        if alias is not None:
            nodes[alias.group("id")] = _clean_label(alias.group("label"))
            continue
        state_label = _STATE_LABEL_RE.match(line)
        if state_label is not None and "--" not in line and "->" not in line:
            nodes[state_label.group("id")] = _clean_label(state_label.group("label"))
            continue

        for match in _NODE_SHAPE_RE.finditer(line):
            node_id = str(match.group("id") or "").strip()
            label = _first_group_label(match)
            if node_id and label:
                nodes.setdefault(node_id, label)

        normalized_line = _NODE_SHAPE_RE.sub(lambda match: str(match.group("id") or ""), line)
        edge = _parse_edge(normalized_line)
        if edge is None:
            continue
        if edge.source_id == "[*]":
            nodes.setdefault(edge.source_id, "Start")
        else:
            nodes.setdefault(edge.source_id, _humanize_identifier(edge.source_id))
        if edge.target_id == "[*]":
            nodes.setdefault(edge.target_id, "End")
        else:
            nodes.setdefault(edge.target_id, _humanize_identifier(edge.target_id))
        edges.append(edge)

    return MermaidGraph(kind=kind, nodes=nodes, edges=tuple(edges))


def node_explanation_from_graph(*, label: str, source_text: str) -> str:
    """Describe what a visible node does by using its graph position."""

    graph = parse_mermaid_graph(source_text)
    target_id = _node_id_for_label(label=label, graph=graph)
    if not target_id:
        return ""
    return describe_graph_node(graph=graph, node_id=target_id)


def describe_graph_node(*, graph: MermaidGraph, node_id: str) -> str:
    """Return an action-oriented description of one node in its diagram context."""

    label = graph.label(node_id)
    incoming = graph.incoming(node_id)
    visible_incoming = tuple(edge for edge in incoming if edge.source_id != "[*]")
    outgoing = graph.outgoing(node_id)
    incoming_sources = _label_list([graph.label(edge.source_id) for edge in incoming if edge.source_id != "[*]"], limit=3)
    outgoing_targets = _label_list([graph.label(edge.target_id) for edge in outgoing if edge.target_id != "[*]"], limit=3)
    incoming_conditions = _label_list([edge.label for edge in incoming if edge.label], limit=3)
    outgoing_conditions = _label_list([edge.label for edge in outgoing if edge.label], limit=3)
    subject = _sentence_subject(label)

    if _is_exception_label(label):
        route = incoming_conditions or incoming_sources
        if route:
            return f"{subject} stops normal progress when {route} makes the next step unsafe or incomplete."
        return f"{subject} is the recovery state; work should stay here until the missing proof, owner action, or fault is cleared."
    if _is_success_label(label) and incoming:
        proof = incoming_conditions or incoming_sources
        if proof:
            return f"{subject} is the trusted outcome reached after {proof}; it should mean the diagram's success condition is satisfied."
        return f"{subject} is the trusted outcome state for this path."
    if not visible_incoming and outgoing:
        if outgoing_conditions:
            return f"{subject} starts the path and moves forward when {outgoing_conditions} is true."
        if outgoing_targets:
            return f"{subject} starts the path and hands off to {outgoing_targets}."
        return f"{subject} starts the path and hands off to {outgoing_targets or 'the next step'}."
    if len(outgoing) > 1:
        branches = outgoing_conditions or "the labeled or visual branches"
        return f"{subject} is the branch point; it sends the flow toward {outgoing_targets or 'different outcomes'} based on {branches or 'the labeled conditions'}."
    if _ACTION_RE.search(label) and outgoing:
        trigger = incoming_conditions or incoming_sources
        if trigger:
            return f"{subject} performs the bounded action after {trigger}, then hands off to {outgoing_targets or 'verification'} for proof or recovery."
        return f"{subject} performs the bounded action, then hands off to {outgoing_targets or 'verification'} for proof or recovery."
    if len(incoming) > 1 and outgoing:
        trigger = incoming_conditions or incoming_sources
        return f"{subject} joins inputs from {incoming_sources or 'earlier steps'} and advances when {trigger or outgoing_conditions or 'the next condition'} is satisfied."
    if incoming and outgoing:
        trigger = incoming_conditions or incoming_sources
        if outgoing_conditions:
            return f"{subject} carries the state forward after {trigger or 'the prerequisite'} and moves next when {outgoing_conditions} is true."
        return f"{subject} carries the state forward after {trigger or 'the prerequisite'} and hands off to {outgoing_targets or 'the next step'}."
    if incoming:
        trigger = incoming_conditions or incoming_sources
        return f"{subject} is reached after {trigger or 'the incoming condition'} and closes this path unless another recovery edge is added."
    return f"{subject} is a named state or responsibility in this diagram."


def _parse_edge(line: str) -> MermaidEdge | None:
    text = " ".join(str(line or "").split())
    if not text:
        return None
    for pattern in (_FLOW_PIPE_EDGE_RE, _FLOW_DASH_EDGE_RE, _FLOW_EDGE_RE, _STATE_EDGE_RE):
        match = pattern.match(text)
        if match is None:
            continue
        source = str(match.group("src") or "").strip()
        target = str(match.group("dst") or "").strip()
        if not source or not target:
            continue
        label = _clean_label(match.groupdict().get("label", ""))
        return MermaidEdge(source_id=source, target_id=target, label=label)
    return None


def _diagram_summary(*, graph: MermaidGraph, title: str, kind: str) -> str:
    starts = _start_nodes(graph)
    branches = _branch_nodes(graph)
    actions = _action_nodes(graph)
    successes = _success_nodes(graph)
    exceptions = _exception_nodes(graph)
    starts_text = _label_list([graph.label(node_id) for node_id in starts], limit=2)
    branches_text = _label_list([graph.label(node_id) for node_id in branches], limit=2)
    actions_text = _label_list([graph.label(node_id) for node_id in actions], limit=2)
    successes_text = _label_list([graph.label(node_id) for node_id in successes], limit=2)
    exceptions_text = _label_list([graph.label(node_id) for node_id in exceptions], limit=2)
    edge_conditions = _label_list([edge.label for edge in graph.edges if edge.label], limit=4)

    if _is_state_kind(kind, graph):
        pieces = [
            f"This state model shows how the work moves from {starts_text or graph.label(graph.node_ids()[0])}",
        ]
        if branches_text:
            pieces.append(f"through {branches_text}")
        if actions_text:
            pieces.append(f"into {actions_text}")
        if successes_text or exceptions_text:
            outcomes = _join_nonempty([successes_text, exceptions_text], joiner=" or ")
            pieces.append(f"and ends in {outcomes}")
        sentence = " ".join(pieces) + "."
        if edge_conditions:
            sentence += f" The important transitions are {edge_conditions}."
        return _sentence(sentence)

    path = _main_path_labels(graph)
    if path:
        sentence = f"This diagram follows {path}."
    else:
        sentence = f"This diagram explains {str(title or 'the system').strip()}."
    if branches_text:
        sentence += f" The main branch point is {branches_text}."
    if exceptions_text:
        sentence += f" Exception or recovery work collects at {exceptions_text}."
    return _sentence(sentence)


def _diagram_read_guide(*, graph: MermaidGraph, kind: str) -> str:
    starts = _start_nodes(graph)
    start = graph.label(starts[0]) if starts else graph.label(graph.node_ids()[0])
    branch_nodes = _branch_nodes(graph)
    exception_nodes = _exception_nodes(graph)
    success_nodes = _success_nodes(graph)
    action_nodes = _action_nodes(graph)
    conditions = _label_list([edge.label for edge in graph.edges if edge.label], limit=5)

    if _is_state_kind(kind, graph):
        lines = [f"Read this as a guarded loop, not as a one-way checklist. Start at {start}."]
        if branch_nodes:
            branch = branch_nodes[0]
            branch_edges = graph.outgoing(branch)
            branch_copy = _edge_choice_copy(graph=graph, edges=branch_edges, limit=3)
            if branch_copy:
                lines.append(f"At {graph.label(branch)}, the labeled conditions decide the next path: {branch_copy}.")
        if action_nodes:
            lines.append(f"{_label_list([graph.label(node_id) for node_id in action_nodes], limit=2)} is where the allowed action happens before the diagram asks for proof or recovery.")
        if success_nodes:
            lines.append(f"{_label_list([graph.label(node_id) for node_id in success_nodes], limit=2)} is the trusted outcome.")
        if exception_nodes:
            lines.append(f"{_label_list([graph.label(node_id) for node_id in exception_nodes], limit=2)} means the system should stop and wait for owner action, repair, or stronger evidence.")
        return " ".join(lines)

    lines = [f"Read from {start} through the arrows."]
    if branch_nodes:
        lines.append(f"Use {_label_list([graph.label(node_id) for node_id in branch_nodes], limit=2)} to find where the path can split.")
    if conditions:
        lines.append(f"The edge labels explain why movement is allowed: {conditions}.")
    success_text = _label_list([graph.label(node_id) for node_id in success_nodes], limit=2)
    exception_text = _label_list([graph.label(node_id) for node_id in exception_nodes], limit=2)
    if success_text and exception_text:
        lines.append(f"Compare the trusted outcomes ({success_text}) with the blocked or recovery outcomes ({exception_text}).")
    elif success_text:
        lines.append(f"Use {success_text} as the trusted outcome and verify which upstream conditions make that state safe.")
    elif exception_text:
        lines.append(f"Treat {exception_text} as the stop or recovery point; those nodes show where proof, owner action, or repair is still needed.")
    return " ".join(lines)


def _start_nodes(graph: MermaidGraph) -> tuple[str, ...]:
    visible = graph.node_ids()
    starts = [node_id for node_id in visible if not graph.incoming(node_id) and graph.outgoing(node_id)]
    if not starts:
        starts = [edge.target_id for edge in graph.edges if edge.source_id == "[*]" and edge.target_id != "[*]"]
    return tuple(_unique(starts))


def _branch_nodes(graph: MermaidGraph) -> tuple[str, ...]:
    return tuple(node_id for node_id in graph.node_ids() if len(graph.outgoing(node_id)) > 1)


def _success_nodes(graph: MermaidGraph) -> tuple[str, ...]:
    return tuple(node_id for node_id in graph.node_ids() if _is_success_label(graph.label(node_id)))


def _exception_nodes(graph: MermaidGraph) -> tuple[str, ...]:
    return tuple(node_id for node_id in graph.node_ids() if _is_exception_label(graph.label(node_id)) or any(_is_exception_label(edge.label) for edge in graph.incoming(node_id)))


def _action_nodes(graph: MermaidGraph) -> tuple[str, ...]:
    return tuple(node_id for node_id in graph.node_ids() if _ACTION_RE.search(graph.label(node_id)))


def _main_path_labels(graph: MermaidGraph) -> str:
    starts = _start_nodes(graph)
    if not starts:
        return ""
    path: list[str] = []
    node_id = starts[0]
    seen: set[str] = set()
    for _ in range(6):
        if node_id in seen or node_id == "[*]":
            break
        seen.add(node_id)
        path.append(graph.label(node_id))
        outgoing = [edge for edge in graph.outgoing(node_id) if edge.target_id != "[*]"]
        if not outgoing:
            break
        preferred = sorted(
            outgoing,
            key=lambda edge: (
                _is_exception_label(edge.label) or _is_exception_label(graph.label(edge.target_id)),
                len(graph.incoming(edge.target_id)),
            ),
        )[0]
        node_id = preferred.target_id
    return _label_list(path, limit=5)


def _edge_choice_copy(*, graph: MermaidGraph, edges: Sequence[MermaidEdge], limit: int) -> str:
    parts: list[str] = []
    for edge in edges[:limit]:
        target = graph.label(edge.target_id)
        if edge.label:
            parts.append(f"{edge.label} leads to {target}")
        else:
            parts.append(target)
    return _join_list(parts)


def _copy_is_specific(value: str, graph: MermaidGraph) -> bool:
    text = str(value or "")
    if len(_WORD_RE.findall(text)) < 24:
        return False
    labels = [graph.label(node_id).casefold() for node_id in graph.node_ids()]
    labels += [edge.label.casefold() for edge in graph.edges if edge.label]
    hits = sum(1 for label in labels if label and label in text.casefold())
    return hits >= 3


def _node_id_for_label(*, label: str, graph: MermaidGraph) -> str:
    wanted = _label_key(label)
    if not wanted:
        return ""
    for node_id in graph.node_ids():
        if _label_key(graph.label(node_id)) == wanted:
            return node_id
    return ""


def _first_group_label(match: re.Match[str]) -> str:
    for name, value in match.groupdict().items():
        if name != "id" and value:
            return _clean_label(value)
    return ""


def _clean_label(value: Any) -> str:
    text = html.unescape(str(value or "")).strip()
    text = re.sub(r"<\s*br\s*/?\s*>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.strip().strip('"').strip("'")
    return " ".join(text.split())


def _humanize_identifier(value: str) -> str:
    token = str(value or "").strip()
    if token == "[*]":
        return "Start"
    token = re.sub(r"[_-]+", " ", token)
    token = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", token)
    token = " ".join(token.split())
    return token[:1].upper() + token[1:] if token else ""


def _label_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").casefold()).strip()


def _sentence(value: str) -> str:
    text = " ".join(str(value or "").split())
    if not text:
        return ""
    return text if text[-1:] in {".", "!", "?"} else f"{text}."


def _sentence_subject(label: str) -> str:
    text = _clean_label(label).rstrip(".")
    return text[:1].upper() + text[1:] if text else "This node"


def _label_list(values: Sequence[str], *, limit: int) -> str:
    clean = _unique([_clean_label(value) for value in values if _clean_label(value)])
    return _join_list(clean[:limit])


def _join_list(values: Sequence[str]) -> str:
    items = [str(value).strip() for value in values if str(value).strip()]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return f"{', '.join(items[:-1])}, and {items[-1]}"


def _join_nonempty(values: Sequence[str], *, joiner: str) -> str:
    return joiner.join(value for value in values if value)


def _unique(values: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for raw in values:
        value = _clean_label(raw)
        key = value.casefold()
        if value and key not in seen:
            seen.add(key)
            result.append(value)
    return result


def _is_exception_label(value: str) -> bool:
    return bool(_FAILURE_RE.search(str(value or "")))


def _is_success_label(value: str) -> bool:
    return bool(_SUCCESS_RE.search(str(value or "")))


def _is_state_kind(kind: str, graph: MermaidGraph) -> bool:
    token = str(kind or graph.kind or "").casefold()
    return "state" in token or str(graph.kind or "").casefold().startswith("statediagram")
