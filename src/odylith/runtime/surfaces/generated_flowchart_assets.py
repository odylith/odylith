"""Static asset renderer for Odylith-generated Atlas flowcharts."""

from __future__ import annotations

from collections import OrderedDict, defaultdict, deque
from collections.abc import Mapping
from dataclasses import dataclass, field
import html
from pathlib import Path
import struct
import zlib

from odylith.runtime.surfaces import surface_path_helpers


_DEFAULT_FILL = "#FFFFFF"
_DEFAULT_STROKE = "#CBD5E1"
_DEFAULT_TEXT = "#132033"
_EDGE_COLOR = "#B9C7D8"


@dataclass
class FlowchartNode:
    node_id: str
    label: str
    group: str = ""
    classes: set[str] = field(default_factory=set)


@dataclass(frozen=True)
class FlowchartEdge:
    source: str
    target: str
    label: str = ""
    dashed: bool = False


@dataclass(frozen=True)
class FlowchartGroup:
    group_id: str
    label: str


@dataclass(frozen=True)
class FlowchartModel:
    direction: str
    nodes: tuple[FlowchartNode, ...]
    edges: tuple[FlowchartEdge, ...]
    groups: tuple[FlowchartGroup, ...]
    class_styles: Mapping[str, Mapping[str, str]]


@dataclass(frozen=True)
class NodeBox:
    x: int
    y: int
    width: int
    height: int
    lines: tuple[str, ...]


@dataclass(frozen=True)
class FlowchartLayout:
    width: int
    height: int
    boxes: Mapping[str, NodeBox]


def render_generated_flowchart_assets(
    *,
    repo_root: Path,
    source_mmd: str,
    source_svg: str,
    source_png: str,
) -> bool:
    """Render a generated flowchart subset without launching a browser."""

    root = Path(repo_root).resolve()
    source_path = surface_path_helpers.resolve_repo_path(repo_root=root, token=source_mmd)
    svg_path = surface_path_helpers.resolve_repo_path(repo_root=root, token=source_svg)
    png_path = surface_path_helpers.resolve_repo_path(repo_root=root, token=source_png)
    try:
        source = source_path.read_text(encoding="utf-8")
    except OSError:
        return False
    model = parse_generated_flowchart(source)
    if model is None:
        return False
    layout = _layout_flowchart(model)
    svg_path.parent.mkdir(parents=True, exist_ok=True)
    png_path.parent.mkdir(parents=True, exist_ok=True)
    svg_path.write_text(_render_svg(model, layout), encoding="utf-8")
    png_path.write_bytes(_render_png(model, layout))
    return True


def parse_generated_flowchart(source: str) -> FlowchartModel | None:
    lines = [line.strip() for line in str(source or "").splitlines()]
    first = next((line for line in lines if line and not line.startswith("%%")), "")
    lowered = first.casefold()
    if not (lowered.startswith("flowchart ") or lowered.startswith("graph ")):
        return None
    direction = "LR"
    parts = first.split()
    if len(parts) > 1 and parts[1].upper() in {"LR", "RL", "TB", "TD", "BT"}:
        direction = "TB" if parts[1].upper() in {"TB", "TD", "BT"} else "LR"

    nodes: OrderedDict[str, FlowchartNode] = OrderedDict()
    edges: list[FlowchartEdge] = []
    groups: OrderedDict[str, FlowchartGroup] = OrderedDict()
    group_stack: list[str] = []
    class_styles: dict[str, dict[str, str]] = {}
    class_assignments: dict[str, set[str]] = defaultdict(set)

    for raw_line in lines[1:]:
        line = raw_line.rstrip(";").strip()
        if not line or line.startswith("%%"):
            continue
        keyword = line.split(maxsplit=1)[0].casefold()
        if keyword in {"direction", "linkstyle"}:
            continue
        if keyword == "end":
            if group_stack:
                group_stack.pop()
            continue
        if keyword == "subgraph":
            group = _parse_group(line)
            if group is not None:
                groups[group.group_id] = group
                group_stack.append(group.group_id)
            continue
        if keyword == "classdef":
            name, style = _parse_class_def(line)
            if name:
                class_styles[name] = style
            continue
        if keyword == "class":
            for node_id, class_name in _parse_class_assignment(line):
                class_assignments[node_id].add(class_name)
            continue
        if keyword == "style":
            continue
        edge = _parse_edge_line(line, nodes=nodes, current_group=group_stack[-1] if group_stack else "")
        if edge is not None:
            edges.append(edge)
            continue
        node = _parse_node_token(line, current_group=group_stack[-1] if group_stack else "")
        if node is not None:
            _upsert_node(nodes, node)

    for node_id, classes in class_assignments.items():
        if node_id in nodes:
            nodes[node_id].classes.update(classes)
    if not nodes:
        return None
    return FlowchartModel(
        direction=direction,
        nodes=tuple(nodes.values()),
        edges=tuple(edge for edge in edges if edge.source in nodes and edge.target in nodes),
        groups=tuple(groups.values()),
        class_styles=class_styles,
    )


def _parse_group(line: str) -> FlowchartGroup | None:
    body = line.split(maxsplit=1)[1].strip() if " " in line else ""
    node = _parse_node_token(body, current_group="")
    if node is not None:
        return FlowchartGroup(group_id=node.node_id, label=node.label)
    token = body.strip()
    if not token:
        return None
    return FlowchartGroup(group_id=_node_id_from_token(token), label=_node_id_from_token(token))


def _parse_class_def(line: str) -> tuple[str, dict[str, str]]:
    body = line.split(maxsplit=1)[1].strip() if " " in line else ""
    if not body:
        return "", {}
    name, _, raw_style = body.partition(" ")
    style: dict[str, str] = {}
    for item in raw_style.split(","):
        key, separator, value = item.strip().partition(":")
        if separator and key in {"fill", "stroke", "color"}:
            style[key] = _safe_hex(value.strip(), fallback=_DEFAULT_TEXT if key == "color" else _DEFAULT_FILL)
    return name.strip(), style


def _parse_class_assignment(line: str) -> tuple[tuple[str, str], ...]:
    body = line.split(maxsplit=1)[1].strip() if " " in line else ""
    if not body:
        return ()
    parts = body.split()
    if len(parts) < 2:
        return ()
    class_name = parts[-1].strip()
    node_ids = [item.strip() for item in " ".join(parts[:-1]).split(",") if item.strip()]
    return tuple((node_id, class_name) for node_id in node_ids)


def _parse_edge_line(
    line: str,
    *,
    nodes: OrderedDict[str, FlowchartNode],
    current_group: str,
) -> FlowchartEdge | None:
    dashed = False
    label = ""
    if "-." in line and ".->" in line:
        start = line.find("-.")
        end = line.find(".->", start + 2)
        left = line[:start].strip()
        label = line[start + 2 : end].strip()
        right = line[end + 3 :].strip()
        dashed = True
    elif "-->" in line:
        left, right = [part.strip() for part in line.split("-->", 1)]
    else:
        return None
    source = _parse_node_token(left, current_group=current_group)
    target = _parse_node_token(right, current_group=current_group)
    if source is None or target is None:
        return None
    _upsert_node(nodes, source)
    _upsert_node(nodes, target)
    return FlowchartEdge(source=source.node_id, target=target.node_id, label=_clean_label(label), dashed=dashed)


def _parse_node_token(token: str, *, current_group: str) -> FlowchartNode | None:
    raw = token.strip().rstrip(";").strip()
    if not raw:
        return None
    bracket = raw.find("[")
    if bracket < 0:
        node_id = _node_id_from_token(raw)
        return FlowchartNode(node_id=node_id, label=node_id, group=current_group) if node_id else None
    node_id = _node_id_from_token(raw[:bracket])
    close = raw.rfind("]")
    if not node_id or close <= bracket:
        return None
    body = raw[bracket + 1 : close].strip()
    if len(body) >= 2 and body[0] in {'"', "'"} and body[-1] == body[0]:
        body = body[1:-1]
    return FlowchartNode(node_id=node_id, label=_clean_label(body), group=current_group)


def _node_id_from_token(token: str) -> str:
    value = token.strip().strip('"').strip("'").strip()
    for separator in (" ", "\t"):
        if separator in value:
            value = value.split(separator, 1)[0]
    return "".join(ch for ch in value if ch.isalnum() or ch == "_")


def _upsert_node(nodes: OrderedDict[str, FlowchartNode], candidate: FlowchartNode) -> None:
    existing = nodes.get(candidate.node_id)
    if existing is None:
        nodes[candidate.node_id] = candidate
        return
    if (not existing.label or existing.label == existing.node_id) and candidate.label:
        existing.label = candidate.label
    if not existing.group and candidate.group:
        existing.group = candidate.group


def _clean_label(value: str) -> str:
    text = html.unescape(str(value or ""))
    return (
        text.replace("<br/>", "\n")
        .replace("<br>", "\n")
        .replace("<br />", "\n")
        .replace("\\n", "\n")
        .strip()
    )


def _layout_flowchart(model: FlowchartModel) -> FlowchartLayout:
    layers = _node_layers(model)
    wrapped: dict[str, tuple[str, ...]] = {}
    boxes: dict[str, NodeBox] = {}
    margin_x = 56
    margin_y = 68
    gap_x = 92
    gap_y = 44
    for node in model.nodes:
        lines = _wrap_label(node.label)
        wrapped[node.node_id] = lines
    widths = {
        node.node_id: min(340, max(190, 46 + max((len(line) for line in wrapped[node.node_id]), default=8) * 7))
        for node in model.nodes
    }
    heights = {node.node_id: max(70, 36 + len(wrapped[node.node_id]) * 18) for node in model.nodes}
    max_width = max(widths.values(), default=220)
    max_height = max(heights.values(), default=76)
    layer_members: dict[int, list[str]] = defaultdict(list)
    for node in model.nodes:
        layer_members[layers.get(node.node_id, 0)].append(node.node_id)
    if model.direction == "LR":
        for layer, node_ids in layer_members.items():
            for row, node_id in enumerate(node_ids):
                boxes[node_id] = NodeBox(
                    x=margin_x + layer * (max_width + gap_x),
                    y=margin_y + row * (max_height + gap_y),
                    width=widths[node_id],
                    height=heights[node_id],
                    lines=wrapped[node_id],
                )
    else:
        for layer, node_ids in layer_members.items():
            for column, node_id in enumerate(node_ids):
                boxes[node_id] = NodeBox(
                    x=margin_x + column * (max_width + gap_x),
                    y=margin_y + layer * (max_height + gap_y),
                    width=widths[node_id],
                    height=heights[node_id],
                    lines=wrapped[node_id],
                )
    width = max((box.x + box.width for box in boxes.values()), default=800) + margin_x
    height = max((box.y + box.height for box in boxes.values()), default=480) + margin_y
    return FlowchartLayout(width=max(760, width), height=max(420, height), boxes=boxes)


def _node_layers(model: FlowchartModel) -> dict[str, int]:
    node_ids = [node.node_id for node in model.nodes]
    incoming: dict[str, int] = {node_id: 0 for node_id in node_ids}
    outgoing: dict[str, list[str]] = defaultdict(list)
    for edge in model.edges:
        outgoing[edge.source].append(edge.target)
        incoming[edge.target] = incoming.get(edge.target, 0) + 1
        incoming.setdefault(edge.source, 0)
    queue = deque(node_id for node_id in node_ids if incoming.get(node_id, 0) == 0)
    layers = {node_id: 0 for node_id in node_ids}
    visited: set[str] = set()
    while queue:
        node_id = queue.popleft()
        visited.add(node_id)
        for target in outgoing.get(node_id, []):
            layers[target] = max(layers.get(target, 0), layers[node_id] + 1)
            incoming[target] -= 1
            if incoming[target] == 0:
                queue.append(target)
    if len(visited) != len(node_ids):
        for index, node_id in enumerate(node_ids):
            layers.setdefault(node_id, index)
    return layers


def _wrap_label(value: str, *, width: int = 30, max_lines: int = 5) -> tuple[str, ...]:
    explicit_lines = [line.strip() for line in str(value or "").splitlines() if line.strip()]
    rows: list[str] = []
    for explicit in explicit_lines or ["Untitled"]:
        current = ""
        for word in explicit.split():
            candidate = f"{current} {word}".strip()
            if current and len(candidate) > width:
                rows.append(current)
                current = word
            else:
                current = candidate
        if current:
            rows.append(current)
    if len(rows) > max_lines:
        rows = [*rows[: max_lines - 1], rows[-1]]
    return tuple(rows or ("Untitled",))


def _render_svg(model: FlowchartModel, layout: FlowchartLayout) -> str:
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{layout.width}" height="{layout.height}" viewBox="0 0 {layout.width} {layout.height}" role="img">',
        "<defs>",
        f'<marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto" markerUnits="strokeWidth"><path d="M0,0 L0,6 L9,3 z" fill="{_EDGE_COLOR}" /></marker>',
        "</defs>",
        '<rect width="100%" height="100%" fill="#FFFFFF" />',
    ]
    parts.extend(_render_svg_groups(model, layout))
    for edge in model.edges:
        source = layout.boxes.get(edge.source)
        target = layout.boxes.get(edge.target)
        if source is None or target is None:
            continue
        parts.append(_edge_path(source, target, dashed=edge.dashed))
    for node in model.nodes:
        box = layout.boxes[node.node_id]
        fill, stroke, text_color = _node_colors(node, model.class_styles)
        parts.append(
            f'<g id="{html.escape(node.node_id)}"><rect x="{box.x}" y="{box.y}" width="{box.width}" height="{box.height}" rx="8" fill="{fill}" stroke="{stroke}" stroke-width="1.35" />'
        )
        start_y = box.y + (box.height - (len(box.lines) - 1) * 18) / 2
        for index, line in enumerate(box.lines):
            parts.append(
                f'<text x="{box.x + box.width / 2:.1f}" y="{start_y + index * 18:.1f}" text-anchor="middle" dominant-baseline="middle" fill="{text_color}" font-family="Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif" font-size="13">{html.escape(line)}</text>'
            )
        parts.append("</g>")
    parts.append("</svg>\n")
    return "\n".join(parts)


def _render_svg_groups(model: FlowchartModel, layout: FlowchartLayout) -> list[str]:
    rendered: list[str] = []
    by_group: dict[str, list[NodeBox]] = defaultdict(list)
    for node in model.nodes:
        if node.group and node.node_id in layout.boxes:
            by_group[node.group].append(layout.boxes[node.node_id])
    labels = {group.group_id: group.label for group in model.groups}
    for group_id, boxes in by_group.items():
        x1 = min(box.x for box in boxes) - 24
        y1 = min(box.y for box in boxes) - 38
        x2 = max(box.x + box.width for box in boxes) + 24
        y2 = max(box.y + box.height for box in boxes) + 24
        rendered.append(
            f'<g class="flowchart-group"><rect x="{x1}" y="{y1}" width="{x2 - x1}" height="{y2 - y1}" rx="14" fill="#FBFDFF" stroke="#D8E5F4" stroke-width="1.15" />'
        )
        rendered.append(
            f'<text x="{x1 + 16}" y="{y1 + 22}" fill="#293D52" font-family="Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif" font-size="12" font-weight="600">{html.escape(labels.get(group_id, group_id))}</text></g>'
        )
    return rendered


def _edge_path(source: NodeBox, target: NodeBox, *, dashed: bool) -> str:
    x1 = source.x + source.width
    y1 = source.y + source.height / 2
    x2 = target.x
    y2 = target.y + target.height / 2
    if target.x < source.x:
        x1 = source.x + source.width / 2
        y1 = source.y + source.height
        x2 = target.x + target.width / 2
        y2 = target.y
    mid = (x1 + x2) / 2
    dash = ' stroke-dasharray="6 6"' if dashed else ""
    return (
        f'<path d="M{x1:.1f},{y1:.1f} C{mid:.1f},{y1:.1f} {mid:.1f},{y2:.1f} {x2:.1f},{y2:.1f}" '
        f'fill="none" stroke="{_EDGE_COLOR}" stroke-width="1.25"{dash} marker-end="url(#arrow)" />'
    )


def _node_colors(node: FlowchartNode, class_styles: Mapping[str, Mapping[str, str]]) -> tuple[str, str, str]:
    fill = _DEFAULT_FILL
    stroke = _DEFAULT_STROKE
    text = _DEFAULT_TEXT
    for class_name in sorted(node.classes):
        style = class_styles.get(class_name)
        if not style:
            continue
        fill = style.get("fill", fill)
        stroke = style.get("stroke", stroke)
        text = style.get("color", text)
    return fill, stroke, text


def _safe_hex(value: str, *, fallback: str) -> str:
    token = str(value or "").strip()
    if len(token) == 7 and token.startswith("#") and all(ch in "0123456789abcdefABCDEF" for ch in token[1:]):
        return token.upper()
    return fallback


def _render_png(model: FlowchartModel, layout: FlowchartLayout) -> bytes:
    width = min(max(layout.width, 1), 1600)
    height = min(max(layout.height, 1), 1200)
    canvas = bytearray([255, 255, 255] * width * height)

    def pixel(x: int, y: int, color: tuple[int, int, int]) -> None:
        if 0 <= x < width and 0 <= y < height:
            index = (y * width + x) * 3
            canvas[index : index + 3] = bytes(color)

    def rect(x: int, y: int, w: int, h: int, fill: tuple[int, int, int], stroke: tuple[int, int, int]) -> None:
        for yy in range(max(0, y), min(height, y + h)):
            for xx in range(max(0, x), min(width, x + w)):
                pixel(xx, yy, fill)
        for xx in range(max(0, x), min(width, x + w)):
            pixel(xx, y, stroke)
            pixel(xx, min(height - 1, y + h - 1), stroke)
        for yy in range(max(0, y), min(height, y + h)):
            pixel(x, yy, stroke)
            pixel(min(width - 1, x + w - 1), yy, stroke)

    def line(x1: int, y1: int, x2: int, y2: int, color: tuple[int, int, int]) -> None:
        dx = abs(x2 - x1)
        dy = -abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        err = dx + dy
        while True:
            pixel(x1, y1, color)
            if x1 == x2 and y1 == y2:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x1 += sx
            if e2 <= dx:
                err += dx
                y1 += sy

    edge = _rgb(_EDGE_COLOR)
    for item in model.edges:
        source = layout.boxes.get(item.source)
        target = layout.boxes.get(item.target)
        if source is None or target is None:
            continue
        line(source.x + source.width, source.y + source.height // 2, target.x, target.y + target.height // 2, edge)
    for node in model.nodes:
        box = layout.boxes[node.node_id]
        fill, stroke, _text = _node_colors(node, model.class_styles)
        rect(box.x, box.y, box.width, box.height, _rgb(fill), _rgb(stroke))
        for index, rendered_line in enumerate(box.lines[:4]):
            bar_width = min(box.width - 36, max(42, len(rendered_line) * 5))
            bar_x = box.x + (box.width - bar_width) // 2
            bar_y = box.y + 22 + index * 14
            rect(bar_x, bar_y, bar_width, 4, _rgb("#293D52"), _rgb("#293D52"))
    return _png_bytes(width, height, bytes(canvas))


def _rgb(value: str) -> tuple[int, int, int]:
    safe = _safe_hex(value, fallback=_DEFAULT_STROKE).lstrip("#")
    return int(safe[0:2], 16), int(safe[2:4], 16), int(safe[4:6], 16)


def _png_bytes(width: int, height: int, rgb: bytes) -> bytes:
    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    scanlines = b"".join(b"\x00" + rgb[row * width * 3 : (row + 1) * width * 3] for row in range(height))
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)) + chunk(
        b"IDAT",
        zlib.compress(scanlines),
    ) + chunk(b"IEND", b"")


__all__ = ["parse_generated_flowchart", "render_generated_flowchart_assets"]
