"""Mermaid graph facts and source-authored Atlas diagram narrative."""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from typing import Any, Mapping

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
    """Source-authored diagram explanation fields used by Atlas."""

    summary: str
    read_guide: str


def build_diagram_narrative(
    *,
    title: str,
    kind: str,
    summary: str,
    read_guide: str,
    source_text: str,
) -> DiagramNarrative:
    """Keep source-authored diagram copy without inferring meaning from graph labels."""
    return DiagramNarrative(summary=summary, read_guide=read_guide)


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


def _humanize_identifier(value: str) -> str:
    token = str(value or "").strip()
    if token == "[*]":
        return "Start"
    token = re.sub(r"[_-]+", " ", token)
    token = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", token)
    token = " ".join(token.split())
    return token[:1].upper() + token[1:] if token else ""
