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

from odylith.runtime.domain_intelligence.greenfield_deferral_predicates import terminal_deferral_subject
from odylith.runtime.surfaces import display_text


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
_FLOW_QUOTED_EDGE_RE = re.compile(
    r"^(?P<src>[A-Za-z][\w.-]*)\s*(?:--|==|-\.|-\.)\s*['\"](?P<label>.+?)['\"]\s*"
    r"(?:-->|==>|\.->|->)\s*(?P<dst>[A-Za-z][\w.-]*)(?:\s*(?:-->|==>|-\.->|-.->|---)\s*.*)?$"
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
    r"\b(action|execute|execution|run|runner|write|create|generate|apply|approve|review|coordinate|release)\b",
    re.IGNORECASE,
)
_MECHANICAL_COPY_RE = re.compile(
    r"\b("
    r"this view shows|this diagram shows|this diagram follows|read from .+ through the arrows|"
    r"through the arrows|arrows are|boxes are the|"
    r"this box represents|none named|shows the path from|"
    r"generic mermaid|diagram box|follow its arrows|carries a concrete step|"
    r"walk the accepted first path|component cards to decode|messages are calls, handoffs|"
    r"read the main spine|where the path splits|available next responsibilities|"
    r"sends normal work toward|read .+ as the evidence boundary"
    r")\b",
    re.IGNORECASE,
)
_PLACEHOLDER_NODE_LABEL_RE = re.compile(r"\b(?:actor|component|external|service|system|node)\d+\b", re.IGNORECASE)
_LEGACY_GREENFIELD_COPY_RE = re.compile(
    r"\b("
    r"walk the accepted first path|walk the accepted first workflow|"
    r"component cards to decode|messages are calls, handoffs|"
    r"read first path sequence from top to bottom|read first workflow sequence from top to bottom"
    r")\b",
    re.IGNORECASE,
)
_DECISION_RE = re.compile(
    r"\?|"
    r"\b(choice|choose|decision|decide|mode|reusable|allowed|gate|approval|classifier|classify|route|select|plan)\b",
    re.IGNORECASE,
)
_PROOF_RE = re.compile(
    r"\b(proof|prove|validated?|verification|validator|benchmark|browser|matrix|check|audit|evidence|receipt|"
    r"ledger|record|closure|accountability|claim|sync --check|readiness)\b",
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

    legacy_narrative = _legacy_greenfield_narrative(title=title, kind=kind, summary=summary, read_guide=read_guide)
    if legacy_narrative is not None:
        return legacy_narrative

    graph = parse_mermaid_graph(source_text)
    if len(graph.node_ids()) < 3 or len(graph.edges) < 2:
        return DiagramNarrative(summary=_sentence(summary), read_guide=_sentence(read_guide), generated=False)

    summary_is_useful = _authored_copy_is_useful(summary, graph=graph, min_words=8)
    read_guide_is_useful = _authored_copy_is_useful(read_guide, graph=graph, min_words=14)
    if summary_is_useful and read_guide_is_useful:
        return DiagramNarrative(summary=_sentence(summary), read_guide=_sentence(read_guide), generated=False)

    generated_summary = _diagram_summary(graph=graph, title=title, kind=kind)
    generated_read_guide = _diagram_read_guide(graph=graph, kind=kind)
    fallback_summary = _sentence(summary)
    fallback_read_guide = _sentence(read_guide)
    final_summary = fallback_summary if summary_is_useful else generated_summary
    final_read_guide = fallback_read_guide if read_guide_is_useful else generated_read_guide
    if not final_summary:
        final_summary = fallback_summary
    if not final_read_guide:
        final_read_guide = fallback_read_guide
    if not final_summary or not final_read_guide:
        return DiagramNarrative(summary=fallback_summary, read_guide=fallback_read_guide, generated=False)

    return DiagramNarrative(
        summary=final_summary,
        read_guide=final_read_guide,
        generated=not (summary_is_useful and read_guide_is_useful),
    )


def _legacy_greenfield_narrative(*, title: str, kind: str, summary: str, read_guide: str) -> DiagramNarrative | None:
    """Replace old greenfield Atlas prose that embedded full paths or diagram mechanics."""

    combined = f"{summary}\n{read_guide}"
    if not _LEGACY_GREENFIELD_COPY_RE.search(combined):
        return None
    kind_token = str(kind or "").casefold()
    title_label = _clean_title(title)
    if "sequence" in kind_token:
        path = _brief_path_from_legacy_summary(summary)
        path_clause = f" for {path}" if path else ""
        return DiagramNarrative(
            summary=_sentence(
                f"{title_label} shows what the first release must prove{path_clause}. "
                "It keeps the first product action, product responsibilities, and proof boundary visible before implementation expands scope."
            ),
            read_guide=(
                "Start with the first product action. Follow each named product responsibility. Treat proof or blocker notes "
                "as the conditions that must hold before source work or release trust."
            ),
            generated=True,
        )
    if "state" in kind_token:
        return DiagramNarrative(
            summary=_sentence(f"{title_label} explains the allowed lifecycle and the proof required before state advances."),
            read_guide=(
                "Read this as the allowed lifecycle. States describe what can be true; arrows describe permitted movement; "
                "blocked or rejected states mark conditions that need proof or owner action before advancement."
            ),
            generated=True,
        )
    return DiagramNarrative(
        summary=_sentence(
            f"{title_label} maps product-owned responsibilities, outside dependencies, and proof boundaries for the first release."
        ),
        read_guide=(
            "Read this as a boundary map. Start with the people, inputs, or trigger, then follow the path into "
            "product-owned responsibilities; outside boxes are dependencies, not first-release capabilities."
        ),
        generated=True,
    )


def _brief_path_from_legacy_summary(value: str) -> str:
    text = _sentence(value)
    text = re.sub(r"^walk the accepted first path in product terms:\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(
        r"^the first complete path (?:the product )?(?:must|should) prove (?:before broader scope )?is\s+",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\s+(?:flow|journey|path)\s*:\s*.*$", "", text, flags=re.IGNORECASE)
    text = re.split(r"\s+\d+\.\s+", text, maxsplit=1)[0]
    text = text.split(". ", 1)[0]
    return _trim_words(text.strip(" .:"), max_words=12)


def _trim_words(value: str, *, max_words: int) -> str:
    words = str(value or "").split()
    if len(words) <= max_words:
        return " ".join(words)
    return " ".join(words[:max_words]).rstrip(" ,;:")


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
                nodes[node_id] = label

        normalized_line = _NODE_SHAPE_RE.sub(lambda match: str(match.group("id") or ""), line)
        chained_edges = _parse_chained_edges(normalized_line)
        if chained_edges:
            for edge in chained_edges:
                nodes.setdefault(edge.source_id, _humanize_identifier(edge.source_id))
                nodes.setdefault(edge.target_id, _humanize_identifier(edge.target_id))
            edges.extend(chained_edges)
            continue
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


def node_role_from_graph(*, label: str, source_text: str) -> str:
    """Return a compact role badge for a visible node."""

    graph = parse_mermaid_graph(source_text)
    target_id = _node_id_for_label(label=label, graph=graph)
    if not target_id:
        return ""
    return describe_graph_node_role(graph=graph, node_id=target_id)


def describe_graph_node(*, graph: MermaidGraph, node_id: str) -> str:
    """Return an action-oriented description of one node in its diagram context."""

    label = graph.label(node_id)
    incoming = graph.incoming(node_id)
    visible_incoming = tuple(edge for edge in incoming if edge.source_id != "[*]")
    outgoing = graph.outgoing(node_id)
    incoming_sources = _node_label_list([graph.label(edge.source_id) for edge in incoming if edge.source_id != "[*]"], limit=3)
    outgoing_targets = _node_label_list([graph.label(edge.target_id) for edge in outgoing if edge.target_id != "[*]"], limit=3)
    incoming_conditions = _label_list([edge.label for edge in incoming if edge.label], limit=3)
    outgoing_conditions = _label_list([edge.label for edge in outgoing if edge.label], limit=3)
    subject = _sentence_subject(_primary_label(label))

    if _looks_like_actor_node(node_id=node_id, label=label):
        if outgoing_targets:
            return f"{subject} starts this path and supplies the action, decision, or review needed by {outgoing_targets}."
        return f"{subject} is a participant in this path and should have a clear responsibility, input, or result."
    if _is_exception_label(_primary_label(label)):
        route = incoming_conditions or incoming_sources
        if route:
            return f"{subject} stops normal progress when {route} makes the next step unsafe or incomplete."
        return f"{subject} is the recovery state; work should stay here until the missing proof, owner action, or fault is cleared."
    if _is_success_label(_primary_label(label)) and incoming:
        proof = incoming_conditions or incoming_sources
        if proof:
            return f"{subject} is the trusted outcome reached after {proof}; it should mean the diagram's success condition is satisfied."
        return f"{subject} is the trusted outcome state for this path."
    if not visible_incoming and outgoing:
        if outgoing_conditions:
            return f"{subject} is the entry responsibility. It produces the next trusted state when {outgoing_conditions} is true."
        if outgoing_targets:
            return f"{subject} is the entry responsibility that creates the input needed by {outgoing_targets}."
        return f"{subject} is the entry responsibility for this diagram."
    if len(outgoing) > 1:
        branches = outgoing_conditions or "the labeled or visual branches"
        return f"{subject} decides between {outgoing_targets or 'different outcomes'} using {branches or 'the labeled conditions'}."
    if _looks_like_action_label(label) and outgoing:
        trigger = incoming_conditions or incoming_sources
        if trigger:
            return f"{subject} performs the bounded action after {trigger} and produces evidence for {outgoing_targets or 'verification'}."
        return f"{subject} performs the bounded action and produces evidence for {outgoing_targets or 'verification'}."
    if len(incoming) > 1 and outgoing:
        trigger = incoming_conditions or incoming_sources
        return f"{subject} joins inputs from {incoming_sources or 'earlier steps'} and advances when {trigger or outgoing_conditions or 'the next condition'} is satisfied."
    if incoming and outgoing:
        trigger = incoming_conditions or incoming_sources
        if outgoing_conditions:
            return f"{subject} carries the state forward after {trigger or 'the prerequisite'} and moves next when {outgoing_conditions} is true."
        return f"{subject} carries the state forward after {trigger or 'the prerequisite'} and produces the input for {outgoing_targets or 'the next step'}."
    if incoming:
        trigger = incoming_conditions or incoming_sources
        return f"{subject} is reached after {trigger or 'the incoming condition'} and closes this path unless another recovery edge is added."
    return f"{subject} is a named state or responsibility in this diagram."


def describe_graph_node_role(*, graph: MermaidGraph, node_id: str) -> str:
    """Return a compact role badge for one graph node."""

    label = graph.label(node_id)
    incoming = graph.incoming(node_id)
    visible_incoming = tuple(edge for edge in incoming if edge.source_id != "[*]")
    outgoing = graph.outgoing(node_id)
    lowered = _primary_label(label).casefold()
    if _looks_like_actor_node(node_id=node_id, label=label):
        return "Actor"
    if _is_exception_label(_primary_label(label)):
        return "Safety stop"
    if _is_success_label(_primary_label(label)) and incoming:
        return "Outcome"
    if not visible_incoming and outgoing:
        return "Start"
    if _looks_like_action_label(lowered):
        return "Action"
    if len(outgoing) > 1:
        return "Decision"
    if re.search(r"\b(log|record|ledger|evidence|audit|receipt|proof|history)\b", lowered):
        return "Evidence"
    if re.search(r"\b(sensor|signal|classifier|resolver|registry|source|manifest|schema|input)\b", lowered):
        return "Input"
    if incoming and not outgoing:
        return "End"
    return "Step"


def _authored_copy_is_useful(value: str, *, graph: MermaidGraph, min_words: int) -> bool:
    text = _sentence(value)
    if len(_WORD_RE.findall(text)) < min_words:
        return False
    if _PLACEHOLDER_NODE_LABEL_RE.search(text):
        return False
    mechanical = _MECHANICAL_COPY_RE.search(text) is not None
    terms = _graph_terms(graph)
    if not terms:
        return not mechanical or _authored_copy_has_substance(text)
    text_key = _label_key(text)
    hits = 0
    for term in terms:
        term_key = _label_key(term)
        if term_key and term_key in text_key:
            hits += 1
    if hits >= min(2, len(terms)):
        return True
    if mechanical:
        return False
    return _authored_copy_has_substance(text)


def _authored_copy_has_substance(text: str) -> bool:
    """Return true when authored copy has enough real responsibility/proof signal.

    Catalog summaries often explain cross-node contracts rather than repeating
    literal Mermaid labels. Keep those when they name concrete responsibilities,
    evidence, state, validation, or runtime boundaries; reject pure diagram
    mechanics and placeholder prose.
    """

    lowered = str(text or "").lower()
    signal_patterns = (
        r"\b(boundar(?:y|ies)|contract|responsibilit(?:y|ies)|ownership|surface|component|system)\b",
        r"\b(state|runtime|session|memory|packet|ledger|record|history|source|evidence)\b",
        r"\b(proof|validate|validation|benchmark|gate|readiness|claim|decision|accepted|trusted)\b",
        r"\b(flow|loop|route|routing|profile|policy|control|recovery|fallback|handoff)\b",
    )
    signals = sum(1 for pattern in signal_patterns if re.search(pattern, lowered))
    return signals >= 2 and len(_WORD_RE.findall(text)) >= 12


def _graph_terms(graph: MermaidGraph) -> tuple[str, ...]:
    terms: list[str] = []
    for node_id in graph.node_ids():
        primary = _primary_label(graph.label(node_id))
        if len(primary) >= 4:
            terms.append(primary)
        detail = _detail_label(graph.label(node_id))
        for piece in re.split(r"[,;/]|\band\b|\bor\b", detail):
            piece = _clean_label(piece)
            if len(piece) >= 6:
                terms.append(piece)
    for edge in graph.edges:
        if edge.label and len(edge.label) >= 5:
            terms.append(edge.label)
    return tuple(_unique(terms))


def _parse_edge(line: str) -> MermaidEdge | None:
    text = " ".join(str(line or "").split())
    if not text:
        return None
    for pattern in (_FLOW_PIPE_EDGE_RE, _FLOW_QUOTED_EDGE_RE, _FLOW_DASH_EDGE_RE, _FLOW_EDGE_RE, _STATE_EDGE_RE):
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


def _parse_chained_edges(line: str) -> tuple[MermaidEdge, ...]:
    text = " ".join(str(line or "").split())
    if "|" in text or ":" in text:
        return ()
    pieces = [piece.strip() for piece in re.split(r"\s*(?:-->|==>|-\.->|-.->|---)\s*", text) if piece.strip()]
    if len(pieces) < 3:
        return ()
    if any(not re.fullmatch(r"\[\*\]|[A-Za-z][\w.-]*", piece) for piece in pieces):
        return ()
    return tuple(MermaidEdge(source_id=source, target_id=target) for source, target in zip(pieces, pieces[1:]))


def _diagram_summary(*, graph: MermaidGraph, title: str, kind: str) -> str:
    starts = _start_nodes(graph)
    branches = _branch_nodes(graph)
    actions = _action_nodes(graph)
    through = _state_through_nodes(graph)
    successes = _success_nodes(graph)
    exceptions = _exception_nodes(graph)
    starts_text = _node_label_list([graph.label(node_id) for node_id in starts], limit=2)
    branches_text = _node_label_list([graph.label(node_id) for node_id in branches], limit=2)
    actions_text = _node_label_list([graph.label(node_id) for node_id in actions], limit=2)
    through_text = _node_label_list([graph.label(node_id) for node_id in through], limit=2)
    successes_text = _node_label_list([graph.label(node_id) for node_id in successes], limit=2)
    exceptions_text = _node_label_list([graph.label(node_id) for node_id in exceptions], limit=2)
    edge_conditions = _label_list([edge.label for edge in graph.edges if edge.label], limit=4)

    if _is_state_kind(kind, graph):
        pieces = [
            f"The state model starts at {starts_text or graph.label(graph.node_ids()[0])}",
        ]
        if branches_text:
            pieces.append(f"through {branches_text}")
        if actions_text:
            pieces.append(f"into {actions_text}")
        elif through_text:
            pieces.append(f"via {through_text}")
        if successes_text or exceptions_text:
            outcomes = _join_nonempty([successes_text, exceptions_text], joiner=" or ")
            pieces.append(f"and ends in {outcomes}")
        sentence = " ".join(pieces) + "."
        if edge_conditions:
            sentence += f" The important transitions are {edge_conditions}."
        return _sentence(sentence)

    return _flow_summary(graph=graph, title=title)


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
            lines.append(f"{_node_label_list([graph.label(node_id) for node_id in action_nodes], limit=2)} is where the allowed action happens before the diagram asks for proof or recovery.")
        if success_nodes:
            lines.append(f"{_node_label_list([graph.label(node_id) for node_id in success_nodes], limit=2)} is the trusted outcome.")
        if exception_nodes:
            lines.append(f"{_node_label_list([graph.label(node_id) for node_id in exception_nodes], limit=2)} means the system should stop and wait for owner action, repair, or stronger evidence.")
        return " ".join(lines)

    return _flow_read_guide(graph=graph, start=start, branch_nodes=branch_nodes, conditions=conditions)


def _flow_summary(*, graph: MermaidGraph, title: str) -> str:
    start_ids = _start_nodes(graph)
    start = _main_start_node(graph) or (start_ids[0] if start_ids else (graph.node_ids()[0] if graph.node_ids() else ""))
    control = _primary_control_node(graph)
    fanout = _primary_fanout_node(graph, exclude={control} if control else set())
    exceptions = _exception_nodes(graph)
    proof_nodes = _ranked_proof_nodes(graph)
    start_label = _primary_label(graph.label(start)) if start else ""
    title_label = _clean_title(title)

    if control:
        control_label = _primary_label(graph.label(control))
        spine = _path_between(graph=graph, start_id=start, stop_id=control)
        middle = [_primary_label(graph.label(node_id)) for node_id in spine if node_id not in {start, control}]
        if "?" in control_label:
            lines = [f'{title_label} centers on the question "{control_label}".']
            if start_label:
                lines.append(f"Work enters at {start_label}.")
        else:
            lines = [
                f"{title_label} turns {start_label or 'the starting input'} into a controlled decision at {control_label}."
            ]
        if middle:
            lines.append(f"The spine first passes through {_join_list(middle[:4])}.")
        choice_copy = _edge_choice_copy(graph=graph, edges=graph.outgoing(control), limit=3)
        if choice_copy:
            lines.append(f"{control_label} separates the path: {choice_copy}.")
        if fanout:
            normal_targets, stop_targets = _branch_targets(graph=graph, branch_id=fanout)
            fanout_label = _primary_label(graph.label(fanout))
            if normal_targets:
                lines.append(f"{fanout_label} is the fan-out point for {_join_list(normal_targets)}.")
            if stop_targets:
                lines.append(f"Unsafe or unresolved paths stop at {_join_list(stop_targets)}.")
        elif exceptions:
            lines.append(
                f"Recovery or blocked work is captured at {_node_label_list([graph.label(node_id) for node_id in exceptions], limit=2)}."
            )
        proof_text = _node_label_list([graph.label(node_id) for node_id in proof_nodes], limit=3)
        if proof_text:
            lines.append(f"The path is trusted only after {proof_text}.")
        return " ".join(lines)

    branch = _dominant_branch_node(graph)
    if branch:
        branch_label = _primary_label(graph.label(branch))
        spine = _path_between(graph=graph, start_id=start, stop_id=branch)
        middle = [_primary_label(graph.label(node_id)) for node_id in spine if node_id not in {start, branch}]
        normal_targets, stop_targets = _branch_targets(graph=graph, branch_id=branch)
        incoming_sources = _node_label_list(
            [graph.label(edge.source_id) for edge in graph.incoming(branch) if edge.source_id != "[*]"],
            limit=3,
        )
        lines = [f"{title_label} centers on {branch_label} as the owned boundary for this path."]
        if incoming_sources:
            lines.append(f"It receives input from {incoming_sources}.")
        if middle:
            lines.append(f"The path first passes through {_join_list(middle[:4])}.")
        if normal_targets:
            lines.append(f"The responsibilities that depend on it are {_join_list(normal_targets)}.")
        if stop_targets:
            lines.append(f"Unsafe or unresolved paths stop at {_join_list(stop_targets)}.")
        elif exceptions:
            lines.append(
                f"Recovery or blocked work is captured at {_node_label_list([graph.label(node_id) for node_id in exceptions], limit=2)}."
            )
        proof_text = _node_full_label_list([graph.label(node_id) for node_id in proof_nodes], limit=3)
        if proof_text:
            lines.append(f"Release trust depends on {proof_text}.")
        return " ".join(lines)

    path = _main_path_ids(graph)
    labels = [_primary_label(graph.label(node_id)) for node_id in path]
    if len(labels) >= 2:
        return _sentence(f"{title_label} follows {labels[0]} through {_join_list(labels[1:-1]) or 'the intermediate steps'} to {labels[-1]}.")
    return _sentence(f"{title_label} explains the system boundary and the evidence needed to trust it.")


def _flow_read_guide(
    *,
    graph: MermaidGraph,
    start: str,
    branch_nodes: Sequence[str],
    conditions: str,
) -> str:
    control = _primary_control_node(graph)
    branch = control or _dominant_branch_node(graph) or (branch_nodes[0] if branch_nodes else "")
    if branch:
        start_id = _main_start_node(graph) or _node_id_for_label(label=start, graph=graph) or branch
        spine = _path_between(graph=graph, start_id=start_id, stop_id=branch)
        spine_labels = [_primary_label(graph.label(node_id)) for node_id in spine]
        normal_targets, stop_targets = _branch_targets(graph=graph, branch_id=branch)
        branch_label = _primary_label(graph.label(branch))
        fanout = _primary_fanout_node(graph, exclude={branch})
        lines = [f"Use this view to separate inputs, owned responsibilities, and release evidence."]
        if len(graph.incoming(branch)) > 1:
            lines.append(f"Boxes pointing into {branch_label} are people, sources, or prerequisites.")
        elif len(spine_labels) > 1:
            lines.append(f"Start with {spine_labels[0]} and read toward {branch_label}.")
        else:
            lines.append(f"Start at {_primary_label(start)} and read toward {branch_label}.")
        if normal_targets:
            lines.append(f"Boxes leaving {branch_label} are the responsibilities that depend on that boundary.")
        if stop_targets:
            lines.append(f"The stop or recovery branch is {_join_list(stop_targets)}, which means the flow should not mutate state until the missing proof or unsafe condition is cleared.")
        if fanout:
            fanout_label = _primary_label(graph.label(fanout))
            fanout_targets, fanout_stops = _branch_targets(graph=graph, branch_id=fanout)
            if fanout_targets:
                lines.append(f"{fanout_label} shows which owned paths run in parallel.")
            if fanout_stops and not stop_targets:
                lines.append(f"{_join_list(fanout_stops)} is where unsafe or incomplete work stops.")
        condition_copy = _condition_reading_copy(graph=graph, limit=4)
        if condition_copy:
            lines.append(condition_copy)
        proof_nodes = _ranked_proof_nodes(graph)
        proof_text = _node_full_label_list([graph.label(node_id) for node_id in proof_nodes], limit=3)
        if proof_text:
            lines.append(f"Check {proof_text} before treating the path as release-ready.")
        return " ".join(lines)

    lines = [f"Start at {_primary_label(start)}, then read each connected decision, action, proof, or recovery point."]
    if conditions:
        lines.append(f"Use the connection labels as the conditions that permit movement: {conditions}.")
    success_nodes = _success_nodes(graph)
    exception_nodes = _exception_nodes(graph)
    success_text = _node_label_list([graph.label(node_id) for node_id in success_nodes], limit=2)
    exception_text = _node_label_list([graph.label(node_id) for node_id in exception_nodes], limit=2)
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
    return tuple(node_id for node_id in graph.node_ids() if _is_success_label(_primary_label(graph.label(node_id))))


def _exception_nodes(graph: MermaidGraph) -> tuple[str, ...]:
    return tuple(
        node_id
        for node_id in graph.node_ids()
        if _is_exception_label(_primary_label(graph.label(node_id)))
        or any(_is_exception_label(edge.label) for edge in graph.incoming(node_id))
    )


def _action_nodes(graph: MermaidGraph) -> tuple[str, ...]:
    return tuple(node_id for node_id in graph.node_ids() if _looks_like_action_label(_primary_label(graph.label(node_id))))


def _looks_like_action_label(value: str) -> bool:
    text = _primary_label(value).casefold()
    return bool(_ACTION_RE.search(text) or re.search(r"\b[a-z][a-z0-9-]{2,}ing\b", text))


def _looks_like_actor_node(*, node_id: str, label: str) -> bool:
    key = str(node_id or "").casefold()
    if key == "actor" or re.fullmatch(r"actor\d*", key):
        return True
    lowered = _primary_label(label).casefold()
    tokens = re.findall(r"[a-z][a-z0-9'-]*", lowered)
    if not tokens or len(tokens) > 7:
        return False
    system_tokens = {
        "adapter",
        "app",
        "application",
        "command",
        "console",
        "dashboard",
        "desk",
        "engine",
        "form",
        "interface",
        "intake",
        "ledger",
        "model",
        "platform",
        "portal",
        "product",
        "queue",
        "register",
        "registry",
        "service",
        "store",
        "surface",
        "system",
        "tool",
        "tracker",
        "view",
        "workspace",
    }
    if any(token in system_tokens for token in tokens):
        return False
    if re.match(
        r"^(?:assign|check|choose|collect|compare|create|display|download|enter|export|fix|generate|import|inspect|log|open|prove|record|repair|review|route|save|select|send|show|submit|triage|update|upload|validate|view)\b",
        lowered,
    ):
        return False
    person_tokens = {
        "actor",
        "actors",
        "applicant",
        "applicants",
        "beneficiary",
        "beneficiaries",
        "client",
        "clients",
        "customer",
        "customers",
        "lead",
        "leads",
        "operator",
        "operators",
        "participant",
        "participants",
        "performer",
        "performers",
        "requester",
        "requesters",
        "reviewer",
        "reviewers",
        "stakeholder",
        "stakeholders",
        "user",
        "users",
    }
    return any(token in person_tokens for token in tokens)


def _state_through_nodes(graph: MermaidGraph) -> tuple[str, ...]:
    excluded = {*_start_nodes(graph), *_branch_nodes(graph), *_success_nodes(graph), *_exception_nodes(graph)}
    return tuple(
        node_id
        for node_id in graph.node_ids()
        if node_id not in excluded and graph.incoming(node_id) and graph.outgoing(node_id)
    )


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
                _is_exception_label(edge.label) or _is_exception_label(_primary_label(graph.label(edge.target_id))),
                len(graph.incoming(edge.target_id)),
            ),
        )[0]
        node_id = preferred.target_id
    return _label_list(path, limit=5)


def _main_path_ids(graph: MermaidGraph) -> tuple[str, ...]:
    starts = _start_nodes(graph)
    if not starts:
        return graph.node_ids()[:6]
    stop = _dominant_branch_node(graph)
    if stop:
        return tuple(_path_between(graph=graph, start_id=starts[0], stop_id=stop))
    path: list[str] = []
    node_id = starts[0]
    seen: set[str] = set()
    for _ in range(8):
        if not node_id or node_id in seen or node_id == "[*]":
            break
        seen.add(node_id)
        path.append(node_id)
        outgoing = [edge for edge in graph.outgoing(node_id) if edge.target_id != "[*]"]
        if not outgoing:
            break
        preferred = sorted(
            outgoing,
            key=lambda edge: (
                _is_exception_label(edge.label) or _is_exception_label(_primary_label(graph.label(edge.target_id))),
                len(graph.incoming(edge.target_id)),
            ),
        )[0]
        node_id = preferred.target_id
    return tuple(path)


def _dominant_branch_node(graph: MermaidGraph) -> str:
    branches = _branch_nodes(graph)
    if not branches:
        return ""
    starts = set(_start_nodes(graph))
    reachable = _reachable_nodes(graph=graph, starts=starts) if starts else set(graph.node_ids())
    candidates = [node_id for node_id in branches if node_id in reachable]
    if not candidates:
        candidates = list(branches)
    return sorted(
        candidates,
        key=lambda node_id: (
            -len(graph.outgoing(node_id)),
            _is_exception_label(_primary_label(graph.label(node_id))),
            list(graph.node_ids()).index(node_id),
        ),
    )[0]


def _main_start_node(graph: MermaidGraph) -> str:
    starts = _start_nodes(graph)
    if not starts:
        return ""
    return sorted(
        starts,
        key=lambda node_id: (
            -len(_reachable_nodes(graph=graph, starts={node_id})),
            list(graph.node_ids()).index(node_id),
        ),
    )[0]


def _primary_control_node(graph: MermaidGraph) -> str:
    branches = _branch_nodes(graph)
    if not branches:
        return ""
    main_start = _main_start_node(graph)
    starts = {main_start} if main_start else set(_start_nodes(graph))
    candidates = [
        node_id
        for node_id in branches
        if _DECISION_RE.search(graph.label(node_id)) or any(_DECISION_RE.search(edge.label) for edge in graph.outgoing(node_id))
    ]
    if not candidates:
        return ""
    return sorted(
        candidates,
        key=lambda node_id: (
            _min_distance_from_starts(graph=graph, starts=starts, target=node_id),
            -len(graph.outgoing(node_id)),
            list(graph.node_ids()).index(node_id),
        ),
    )[0]


def _primary_fanout_node(graph: MermaidGraph, *, exclude: set[str] | None = None) -> str:
    blocked = set(exclude or set())
    candidates = [node_id for node_id in _branch_nodes(graph) if node_id not in blocked and len(graph.outgoing(node_id)) >= 3]
    if not candidates:
        return ""
    main_start = _main_start_node(graph)
    starts = {main_start} if main_start else set(_start_nodes(graph))
    return sorted(
        candidates,
        key=lambda node_id: (
            -len(graph.outgoing(node_id)),
            _min_distance_from_starts(graph=graph, starts=starts, target=node_id),
            list(graph.node_ids()).index(node_id),
        ),
    )[0]


def _proof_nodes(graph: MermaidGraph) -> tuple[str, ...]:
    candidates: list[str] = []
    for node_id in graph.node_ids():
        label = graph.label(node_id)
        if _is_proof_node_label(label):
            candidates.append(node_id)
            continue
        if any(_PROOF_RE.search(edge.label) for edge in graph.incoming(node_id)):
            candidates.append(node_id)
    return tuple(_unique(candidates))


def _is_proof_node_label(label: str) -> bool:
    primary = _primary_label(label).casefold()
    full = _clean_label(label).casefold()
    if re.search(
        r"\b(public accountability|release claim|browser|benchmark|validator|sync --check|check-only|proof|"
        r"evidence|validated|audit|receipt|durable .*ledger|ledger record|history record)\b",
        full,
    ):
        return True
    if re.search(r"\b(ledger|record|verification)\b", primary):
        return "stale" not in full and "input" not in full
    if re.search(r"\b(accountability|claim|readiness)\b", primary):
        return True
    return False


def _ranked_proof_nodes(graph: MermaidGraph) -> tuple[str, ...]:
    nodes = list(_proof_nodes(graph))
    if not nodes:
        return ()
    source_order = list(graph.node_ids())
    return tuple(
        sorted(
            nodes,
            key=lambda node_id: (
                _proof_node_rank(graph.label(node_id)),
                -len(graph.incoming(node_id)),
                _label_starts_with_id(_primary_label(graph.label(node_id))),
                source_order.index(node_id) if node_id in source_order else 999,
            ),
        )
    )


def _proof_node_rank(label: str) -> int:
    lowered = _primary_label(label).casefold()
    full = _clean_label(label).casefold()
    if re.search(r"\b(public accountability|release claim|closure|close)\b", full):
        return 0
    if re.search(r"\b(browser|benchmark|validator|sync --check|check-only|proof)\b", full):
        return 1
    if re.search(r"\b(evidence|verified|verification|validated|audit|receipt|ledger|record)\b", full):
        return 2
    if re.search(r"\b(accountability|claim|readiness)\b", lowered):
        return 3
    return 4


def _label_starts_with_id(label: str) -> bool:
    return bool(re.match(r"^[A-Z]{1,3}-\d+\b", str(label or "").strip()))


def _min_distance_from_starts(*, graph: MermaidGraph, starts: set[str], target: str) -> int:
    if not starts:
        return 999
    best = 999
    for start in starts:
        distance = _distance_between(graph=graph, start_id=start, target_id=target)
        if distance < best:
            best = distance
    return best


def _distance_between(*, graph: MermaidGraph, start_id: str, target_id: str) -> int:
    if start_id == target_id:
        return 0
    queue: list[tuple[str, int]] = [(start_id, 0)]
    seen: set[str] = set()
    while queue:
        node_id, distance = queue.pop(0)
        if node_id in seen:
            continue
        seen.add(node_id)
        for edge in graph.outgoing(node_id):
            if edge.target_id == target_id:
                return distance + 1
            if edge.target_id not in seen and edge.target_id != "[*]":
                queue.append((edge.target_id, distance + 1))
    return 999


def _reachable_nodes(*, graph: MermaidGraph, starts: set[str]) -> set[str]:
    seen: set[str] = set()
    queue = list(starts)
    while queue:
        node_id = queue.pop(0)
        if not node_id or node_id in seen:
            continue
        seen.add(node_id)
        queue.extend(edge.target_id for edge in graph.outgoing(node_id) if edge.target_id not in seen)
    return seen


def _path_between(*, graph: MermaidGraph, start_id: str, stop_id: str) -> tuple[str, ...]:
    if not start_id or not stop_id:
        return ()
    queue: list[tuple[str, tuple[str, ...]]] = [(start_id, (start_id,))]
    seen: set[str] = set()
    while queue:
        node_id, path = queue.pop(0)
        if node_id == stop_id:
            return path
        if node_id in seen:
            continue
        seen.add(node_id)
        outgoing = sorted(
            graph.outgoing(node_id),
            key=lambda edge: (
                _is_exception_label(edge.label) or _is_exception_label(_primary_label(graph.label(edge.target_id))),
                len(graph.incoming(edge.target_id)),
            ),
        )
        for edge in outgoing:
            if edge.target_id not in seen and edge.target_id != "[*]":
                queue.append((edge.target_id, (*path, edge.target_id)))
    return (stop_id,)


def _branch_targets(*, graph: MermaidGraph, branch_id: str) -> tuple[list[str], list[str]]:
    normal: list[str] = []
    stops: list[str] = []
    for edge in graph.outgoing(branch_id):
        target = _primary_label(graph.label(edge.target_id))
        if not target or edge.target_id == "[*]":
            continue
        is_stop = _is_exception_label(edge.label) or _is_exception_label(target)
        if is_stop:
            stops.append(target)
        else:
            normal.append(target)
    return _unique(normal)[:4], _unique(stops)[:3]


def _edge_choice_copy(*, graph: MermaidGraph, edges: Sequence[MermaidEdge], limit: int) -> str:
    parts: list[str] = []
    for edge in edges[:limit]:
        target = _primary_label(graph.label(edge.target_id))
        if edge.label:
            parts.append(f"{edge.label} leads to {target}")
        else:
            parts.append(target)
    return _join_list(parts)


def _condition_reading_copy(*, graph: MermaidGraph, limit: int) -> str:
    labels = _unique([edge.label for edge in graph.edges if edge.label])[:limit]
    if not labels:
        return ""
    if len(labels) == 1:
        return f"The labeled edge, {labels[0]}, is the condition that explains why movement is allowed or blocked."
    return f"Use the labeled edges as gates; the most important conditions here are {_join_list(labels)}."


def _proof_boundary_read_sentence(*, proof_text: str, proof_count: int) -> str:
    if proof_count <= 1:
        return f"Read {proof_text} as the evidence boundary: that node explains why the final outcome can be trusted."
    return f"Read {proof_text} as the evidence boundary: those nodes explain why the final outcome can be trusted."


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
        node_label = graph.label(node_id)
        if _label_key(node_label) == wanted or _label_key(_primary_label(node_label)) == wanted:
            return node_id
    return ""


def _first_group_label(match: re.Match[str]) -> str:
    for name, value in match.groupdict().items():
        if name != "id" and value:
            return _clean_label(value)
    return ""


def _clean_label(value: Any) -> str:
    text = html.unescape(str(value or "")).strip()
    text = re.sub(r"<\s*br\s*/?\s*>", " · ", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = display_text.strip_inline_markdown_emphasis(text)
    text = text.strip().strip('"').strip("'")
    compact = " ".join(text.split())
    return terminal_deferral_subject(compact) or compact


def _primary_label(value: str) -> str:
    text = _clean_label(value)
    for separator in (" · ", "\n"):
        if separator in text:
            return text.split(separator, 1)[0].strip()
    return text


def _detail_label(value: str) -> str:
    text = _clean_label(value)
    for separator in (" · ", "\n"):
        if separator in text:
            return text.split(separator, 1)[1].strip()
    return ""


def _clean_title(value: str) -> str:
    title = _clean_label(value).strip()
    return title if title else "The diagram"


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
    text = display_text.strip_inline_markdown_emphasis(value)
    if not text:
        return ""
    return text if text[-1:] in {".", "!", "?"} else f"{text}."


def _sentence_subject(label: str) -> str:
    text = _clean_label(label).rstrip(".")
    return text[:1].upper() + text[1:] if text else "This node"


def _label_list(values: Sequence[str], *, limit: int) -> str:
    clean = _unique([_clean_label(value) for value in values if _clean_label(value)])
    return _join_list(clean[:limit])


def _node_label_list(values: Sequence[str], *, limit: int) -> str:
    clean = _unique([_primary_label(value) for value in values if _primary_label(value)])
    return _join_list(clean[:limit])


def _node_full_label_list(values: Sequence[str], *, limit: int) -> str:
    clean = _unique([_full_label(value) for value in values if _full_label(value)])
    return _join_list(clean[:limit])


def _full_label(value: str) -> str:
    text = _clean_label(value)
    return re.sub(r"\s*·\s*", " ", text).strip()


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
