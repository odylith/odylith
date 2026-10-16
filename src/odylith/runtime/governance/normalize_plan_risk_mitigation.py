"""Normalize risk records with CommonMark ownership and source-preserving edits."""

from __future__ import annotations

import argparse
from html.parser import HTMLParser
from pathlib import Path
import re
from typing import Sequence

from markdown_it import MarkdownIt
from markdown_it.rules_inline import StateInline, emphasis, html_inline, newline, text as inline_text
from markdown_it.token import Token
from markdown_it.tree import SyntaxTreeNode


_PLAN_GLOBS: tuple[str, ...] = (
    "odylith/technical-plans/in-progress/**/*.md",
    "odylith/technical-plans/done/**/*.md",
)
_MARKDOWN = MarkdownIt("commonmark")
_RISK_HEADINGS = {"risks", "risks&mitigations", "risks/mitigations"}
_BULLET_RE = re.compile(r"^(?P<indent>[ \t]*)[-*+][ \t]+")
_CHECKBOX_RE = re.compile(r"\[(?P<mark>[xX ])\][ \t]*")
_LABEL_RE = re.compile(
    r"(?P<opening>\*\*)?(?P<label>Risk|Mitigation)(?P<closing>\*\*)?[ \t]*:"
    r"(?(opening)(?(closing)|\*\*))[ \t]*",
    re.IGNORECASE,
)
_PLACEHOLDER_MITIGATION = "TODO (add explicit mitigation)."
# HTML syntax: https://html.spec.whatwg.org/multipage/syntax.html#void-elements
_HTML_VOID_ELEMENTS = frozenset({
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta",
    "source", "track", "wbr",
})


def _record_prose(state: StateInline, silent: bool) -> bool:
    start = state.pos
    matched = inline_text(state, silent)
    if matched and not silent and not state.linkLevel and state.src is state.env.get("risk_source"):
        state.env["risk_prose"].append((start, state.pos))
    return matched


def _record_softbreak(state: StateInline, silent: bool) -> bool:
    start = state.pos
    matched = newline(state, silent)
    if (
        matched and not silent and not state.linkLevel
        and state.src is state.env.get("risk_source")
        and state.tokens[-1].type == "softbreak"
    ):
        state.env["risk_softbreaks"].append((start, state.pos))
    return matched


def _record_emphasis(state: StateInline, silent: bool) -> bool:
    start = state.pos
    matched = emphasis.tokenize(state, silent)
    if matched and not silent and state.src is state.env.get("risk_source"):
        for position, token in zip(range(start, state.pos), state.tokens[-(state.pos - start):]):
            token.meta["risk_position"] = position
    return matched


def _record_html(state: StateInline, silent: bool) -> bool:
    start = state.pos
    matched = html_inline(state, silent)
    if matched and not silent and state.src is state.env.get("risk_source"):
        state.tokens[-1].meta["risk_span"] = (start, state.pos)
    return matched


class _InlineHTMLBoundaries(HTMLParser):
    """Track enclosures only in HTML tokens already recognized by CommonMark."""

    def __init__(self) -> None:
        super().__init__()
        self.stack: list[tuple[str, int]] = []
        self.spans: list[tuple[int, int]] = []
        self.start = self.end = 0
        self.unmatched: list[int] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag not in _HTML_VOID_ELEMENTS:
            self.stack.append((tag, self.start))

    def handle_endtag(self, tag: str) -> None:
        if self.stack and self.stack[-1][0] == tag:
            _, start = self.stack.pop()
            self.spans.append((start, self.end))
        else:
            self.unmatched.append(self.start)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        # A slash does not close a normal HTML element. Without a matching
        # end tag, keep its remaining paragraph opaque rather than guessing.
        self.handle_starttag(tag, attrs)


def _inline_container_spans(tokens: list[Token], *, paragraph_end: int) -> list[tuple[int, int]]:
    html = _InlineHTMLBoundaries()
    spans: list[tuple[int, int]] = []
    emphasis_starts: list[int] = []
    for token in tokens:
        if "risk_position" in token.meta:
            position = token.meta["risk_position"]
            if token.nesting == 1:
                emphasis_starts.append(position - len(token.markup) + 1)
            elif token.nesting == -1:
                spans.append((emphasis_starts.pop(), position + len(token.markup)))
        elif token.type == "html_inline" and "risk_span" in token.meta:
            html.start, html.end = token.meta["risk_span"]
            html.feed(token.content)
    html.close()
    unresolved = [start for _, start in html.stack] + html.unmatched
    return spans + html.spans + [(start, paragraph_end) for start in unresolved]


# Source positions are captured by the real inline rules, before token joining.
# Eligibility is decided after delimiter pairing, with complete enclosures intact.
_MARKDOWN.inline.ruler.at("text", _record_prose)
_MARKDOWN.inline.ruler.at("newline", _record_softbreak)
_MARKDOWN.inline.ruler.at("emphasis", _record_emphasis)
_MARKDOWN.inline.ruler.at("html_inline", _record_html)


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments for plan risk/mitigation normalization."""
    parser = argparse.ArgumentParser(
        prog="odylith sync",
        description=(
            "Normalize `## Risks & Mitigations` sections so each top-level risk has nested mitigations."
        ),
    )
    parser.add_argument("--repo-root", default=".")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail closed when normalization would change files (no writes).",
    )
    return parser.parse_args(argv)


def _list_plan_files(*, repo_root: Path) -> list[Path]:
    """Return the plan markdown files covered by this normalizer."""
    files: list[Path] = []
    for pattern in _PLAN_GLOBS:
        files.extend(path for path in repo_root.glob(pattern) if path.is_file())
    return sorted(set(path.resolve() for path in files))


def _apply_edits(source: str, edits: list[tuple[int, int, str]]) -> str:
    for start, end, replacement in sorted(edits, reverse=True):
        source = source[:start] + replacement + source[end:]
    return source


def _format_record_paragraph(
    source: str, *, is_item: bool, env: dict, default_label: str | None = None,
    default_checked: bool = False,
) -> tuple[str | None, bool, str]:
    """Edit label syntax and real softbreaks, retaining all other source bytes."""
    bullet = _BULLET_RE.match(source) if is_item else None
    if is_item and bullet is None:
        return None, False, source
    indent = bullet.group("indent") if bullet else ""
    list_prefix = indent + "-" + bullet.group()[len(indent) + 1:] if bullet else "- "
    child_indent = " " * len(list_prefix.expandtabs(4))
    body_start = bullet.end() if bullet else 0
    checkbox = _CHECKBOX_RE.match(source, body_start)
    checked = checkbox.group("mark").lower() == "x" if checkbox else default_checked
    if checkbox:
        body_start = checkbox.end()
    body = source[body_start:].removesuffix("\n")
    inline_env = dict(env, risk_source=body, risk_prose=[], risk_softbreaks=[])
    inline_tokens = _MARKDOWN.inline.parse(body, _MARKDOWN, inline_env, [])
    containers = _inline_container_spans(inline_tokens, paragraph_end=len(body))
    labels = [
        match for match in _LABEL_RE.finditer(body)
        if any(start <= match.start("label") < match.end("label") <= end
               for start, end in inline_env["risk_prose"])
        and all(match.end() <= start or end <= match.start()
                or (match.start() <= start and end <= match.end())
                for start, end in containers)
    ]
    first = labels[0] if labels and labels[0].start() == 0 else None
    label = first.group("label").lower() if first else default_label
    if label is None:
        return None, checked, source
    if not checkbox and label != "mitigation":
        checked = False
    content_start = first.end() if first else 0
    mark = "x" if checked else " "
    edits = [(0, body_start + content_start, f"{list_prefix}[{mark}] {label.title()}: ")]
    inline = next((match for match in labels if (
        label == "risk" and match.start() > content_start
        and match.group("label").lower() == "mitigation"
        and body[match.start() - 1].isspace()
    )), None)
    split_start = inline.start() if inline else len(body)
    if inline:
        while split_start > content_start and body[split_start - 1].isspace():
            split_start -= 1
        edits.append((body_start + split_start, body_start + inline.end(),
                      f"\n{child_indent}- [{mark}] Mitigation: "))
    for start, end in inline_env["risk_softbreaks"]:
        if start < content_start or (inline and split_start <= start < inline.end()):
            continue
        if any(start < container_end and container_start < end
               for container_start, container_end in containers):
            continue
        separator = "" if start and body[start - 1] == " " else " "
        edits.append((body_start + start, body_start + end, separator))
    return "inline" if inline else label, checked, _apply_edits(source, edits)


def _normalize_risk_blocks(
    blocks: list[SyntaxTreeNode], *, source: str, lines: list[str], offsets: list[int], env: dict,
) -> list[tuple[int, int, str]]:
    edits: list[tuple[int, int, str]] = []
    risks: dict[SyntaxTreeNode, str] = {}
    mitigated: set[SyntaxTreeNode] = set()
    current_risk: SyntaxTreeNode | None = None
    current_checked = False
    current_indent = "  "

    def span(node: SyntaxTreeNode) -> tuple[int, int]:
        assert node.map is not None
        return offsets[node.map[0]], offsets[node.map[1]]

    def format_paragraph(node: SyntaxTreeNode, *, nested: bool = False) -> tuple[str | None, bool, str]:
        start, end = span(node)
        is_item = node.parent is not None and node.parent.type == "list_item"
        return _format_record_paragraph(
            source[start:end], is_item=is_item, env=env,
            default_label="mitigation" if nested else None,
            default_checked=current_checked if not is_item else False,
        )

    for block in blocks:
        nodes = block.children if block.type == "bullet_list" else [block]
        for node in nodes:
            paragraph = node.children[0] if node.type == "list_item" and node.children else node
            if paragraph.type != "paragraph":
                current_risk = None
                current_checked = False
                current_indent = "  "
                continue
            kind, checked, rendered = format_paragraph(paragraph)
            if kind is None:
                current_risk = None
                current_checked = False
                current_indent = "  "
                continue
            start, end = span(node)
            paragraph_start, paragraph_end = span(paragraph)
            item_edits = [(paragraph_start - start, paragraph_end - start, rendered)]
            if kind in {"risk", "inline"}:
                bullet = _BULLET_RE.match(rendered)
                assert bullet is not None
                current_indent = " " * len(bullet.group().expandtabs(4))
                risks[node] = current_indent
                current_risk, current_checked = node, checked
                if kind == "inline":
                    mitigated.add(node)
                # Only immediate child lists belong to this risk. Paragraphs,
                # fences and quotes between them do not end the owning item.
                for child_list in node.children if node.type == "list_item" else []:
                    if child_list.type != "bullet_list":
                        continue
                    for child in child_list.children:
                        if not child.children or child.children[0].type != "paragraph":
                            continue
                        child_paragraph = child.children[0]
                        child_kind, _, child_rendered = format_paragraph(child_paragraph, nested=True)
                        if child_kind != "mitigation":
                            continue
                        mitigated.add(node)
                        child_start, child_end = span(child_paragraph)
                        item_edits.append((child_start - start, child_end - start, child_rendered))
                edits.append((start, end, _apply_edits(source[start:end], item_edits)))
            else:
                rendered_item = _apply_edits(source[start:end], item_edits)
                # Relocation moves the entire item, including owned hardbreaks,
                # additional paragraphs and literal child blocks.
                bullet = _BULLET_RE.match(rendered_item)
                assert bullet is not None
                shift = " " * max(0, len(current_indent) - len(bullet.group("indent").expandtabs(4)))
                rendered_item = "".join(shift + line if line.strip() else line
                                        for line in rendered_item.splitlines(keepends=True))
                if current_risk is None:
                    rendered_item = "- [ ] Risk: Unspecified risk (legacy backfill).\n" + rendered_item
                    current_risk = node
                mitigated.add(current_risk)
                edits.append((start, end, rendered_item))

    for risk, indent in risks.items():
        if risk in mitigated:
            continue
        start, end = span(risk)
        # Keep separator blanks outside the inserted child, without trimming
        # any authored line or literal trailing whitespace.
        assert risk.map is not None
        last_line = risk.map[1]
        while last_line > risk.map[0] and not lines[last_line - 1].strip():
            last_line -= 1
        insertion = offsets[last_line]
        prefix = "" if insertion and source[insertion - 1] == "\n" else "\n"
        placeholder = f"{prefix}{indent}- [ ] Mitigation: {_PLACEHOLDER_MITIGATION}\n"
        # The owning item's edit already includes its complete source span.
        for index, (edit_start, edit_end, replacement) in enumerate(edits):
            if (edit_start, edit_end) == (start, end):
                trailing = source[insertion:end]
                boundary = len(replacement) - len(trailing)
                edits[index] = (start, end, replacement[:boundary] + placeholder + trailing)
                break
    return edits


def normalize_risk_mitigation_markdown(text: str) -> str:
    """Normalize top-level risk sections without rewriting unrelated document bytes."""
    env: dict = {}
    root = SyntaxTreeNode(_MARKDOWN.parse(text, env))
    lines = text.splitlines(keepends=True)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))
    edits: list[tuple[int, int, str]] = []
    for index, heading in enumerate(root.children):
        if heading.type != "heading" or heading.tag != "h2":
            continue
        title = heading.children[0].content
        if "".join(title.casefold().split()) not in _RISK_HEADINGS:
            continue
        assert heading.map is not None
        start, end = (offsets[line] for line in heading.map)
        ending = "\n" if text[start:end].endswith("\n") else ""
        edits.append((start, end, "## Risks & Mitigations" + ending))
        boundary = next((position for position in range(index + 1, len(root.children))
                         if root.children[position].type == "heading"
                         and root.children[position].tag in {"h1", "h2"}), len(root.children))
        edits.extend(_normalize_risk_blocks(
            root.children[index + 1:boundary], source=text, lines=lines, offsets=offsets, env=env,
        ))
    return _apply_edits(text, edits)


def normalize_plan_risk_mitigation(
    *, repo_root: Path, check_only: bool, plan_paths: Sequence[Path] | None = None,
) -> tuple[int, list[str]]:
    """Normalize all covered plan files, optionally in check-only mode."""
    changed: list[str] = []
    for plan_path in _list_plan_files(repo_root=repo_root) if plan_paths is None else plan_paths:
        source = plan_path.read_text(encoding="utf-8")
        rendered = normalize_risk_mitigation_markdown(source)
        if source == rendered:
            continue
        rel = plan_path.relative_to(repo_root).as_posix()
        changed.append(rel)
        if not check_only:
            plan_path.write_text(rendered, encoding="utf-8")
    return len(changed), changed


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entrypoint for repo-wide plan risk/mitigation normalization."""
    args = _parse_args(argv)
    repo_root = Path(str(args.repo_root)).expanduser().resolve()
    changed_count, changed_files = normalize_plan_risk_mitigation(
        repo_root=repo_root,
        check_only=bool(args.check),
    )

    if changed_count == 0:
        print("plan risk/mitigation normalization passed")
        print("- files changed: 0")
        return 0

    if args.check:
        print("plan risk/mitigation normalization FAILED")
        print("- run: odylith sync --repo-root . --force")
        for rel in changed_files:
            print(f"- would change: {rel}")
        return 2

    print("plan risk/mitigation normalization applied")
    print(f"- files changed: {changed_count}")
    for rel in changed_files:
        print(f"- updated: {rel}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
