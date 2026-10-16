"""Faithful, non-executable Markdown presentation for authored Radar content."""

from __future__ import annotations

import html
import re
from collections.abc import Sequence
from pathlib import Path

from markdown_it import MarkdownIt
from markdown_it.common.normalize_url import validateLink
from markdown_it.renderer import RendererHTML
from markdown_it.token import Token
from markdown_it.utils import EnvType, OptionsDict

from odylith.runtime.governance import workstream_inference
from odylith.runtime.surfaces import display_text


def _slug_token(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(value or "").lower()).strip("-") or "idea"


def normalize_inline_repo_token(*, repo_root: Path, token: str) -> str:
    """Normalize a traceability token independently of authored prose rendering."""

    normalized = workstream_inference.normalize_repo_token(str(token or "").strip(), repo_root=repo_root)
    collapsed = str(normalized or "").strip().strip(".,;:")
    if not collapsed or " " in collapsed or "<" in collapsed or ">" in collapsed:
        return ""
    if collapsed.startswith(("http://", "https://")):
        return ""
    return collapsed


def strip_display_markdown_emphasis(value: object) -> str:
    """Normalize plain display metadata; never apply this to Markdown source."""

    return display_text.strip_inline_markdown_emphasis(value)


def _link_open(renderer: RendererHTML, tokens: Sequence[Token], index: int, options: OptionsDict, env: EnvType) -> str:
    if env.get("preview"):
        return '<span class="source-link">'
    token = tokens[index]
    external = str(token.attrGet("href") or "").lower().startswith(("http://", "https://"))
    token.attrSet("target", "_blank" if external else "_top")
    if external:
        token.attrSet("rel", "noopener noreferrer")
    return renderer.renderToken(tokens, index, options, env)


def _link_close(renderer: RendererHTML, tokens: Sequence[Token], index: int, options: OptionsDict, env: EnvType) -> str:
    return "</span>" if env.get("preview") else renderer.renderToken(tokens, index, options, env)


def _image(renderer: RendererHTML, tokens: Sequence[Token], index: int, options: OptionsDict, env: EnvType) -> str:
    # The authored description remains readable without fetching an image.
    return renderer.renderInline(tokens[index].children or [], options, env)


def _fence(renderer: RendererHTML, tokens: Sequence[Token], index: int, options: OptionsDict, env: EnvType) -> str:
    token = tokens[index]
    language = token.info.strip().lower()
    body = html.escape(token.content)
    if language == "mermaid" and not env.get("preview"):
        return f'<div class="mermaid-wrap"><div class="mermaid">{body}</div></div>\n'
    language_class = f" language-{_slug_token(language)}" if language else ""
    return f'<pre class="code{language_class}"><code>{body}</code></pre>\n'


def _list_item_open(renderer: RendererHTML, tokens: Sequence[Token], index: int, options: OptionsDict, env: EnvType) -> str:
    inline = tokens[index + 2] if index + 2 < len(tokens) else None
    children = inline.children if inline and inline.type == "inline" else None
    first = children[0] if children else None
    if not first or first.type != "text" or not inline.content.startswith(("[ ] ", "[x] ", "[X] ")):
        return renderer.renderToken(tokens, index, options, env)
    checked = first.content[1].lower() == "x"
    first.content = first.content[4:]
    for closing in tokens[index + 1:]:
        if closing.type == "list_item_close" and closing.level == tokens[index].level:
            closing.meta["checklist"] = True
            break
    if env.get("preview"):
        label, mark = ("Complete", "☑") if checked else ("Incomplete", "☐")
        control = f'<span class="check-box" role="img" aria-label="{label}">{mark}</span>'
    else:
        control = f'<input class="check-box" type="checkbox" disabled{" checked" if checked else ""} />'
    return f'<li><div class="check-item">{control}<div class="check-text">'


def _list_item_close(renderer: RendererHTML, tokens: Sequence[Token], index: int, options: OptionsDict, env: EnvType) -> str:
    if tokens[index].meta.get("checklist"):
        return "</div></div></li>\n"
    return renderer.renderToken(tokens, index, options, env)


_MARKDOWN = MarkdownIt("commonmark", {"html": False})
# CommonMark allows some data-image URLs; Radar does not activate any data URL.
_MARKDOWN.validateLink = lambda url: validateLink(url) and not url.strip().lower().startswith("data:")
for _name, _rule in (
    ("link_open", _link_open), ("link_close", _link_close), ("image", _image),
    ("fence", _fence), ("list_item_open", _list_item_open), ("list_item_close", _list_item_close),
):
    _MARKDOWN.add_render_rule(_name, _rule)


def render_inline_html(*, repo_root: Path, text: str) -> str:
    """Format authored inline Markdown with raw HTML and unsafe URLs disabled."""

    return _MARKDOWN.renderInline(str(text or ""))


def render_section_body(*, repo_root: Path, lines: list[str], preview: bool = False) -> str:
    """Format source blocks; previews cannot contain interactive or executable content."""

    source = "\n".join(lines)
    if not source.strip():
        return "<p>Not captured in this section.</p>"
    return _MARKDOWN.render(source, {"preview": preview})


def extract_section_bodies(source: str) -> list[tuple[str, list[str]]]:
    """Project top-level section source spans without treating fenced headings as boundaries."""

    lines = source.splitlines()
    tokens = _MARKDOWN.parse(source)
    headings = [
        (tokens[index + 1].content, token.map)
        for index, token in enumerate(tokens)
        if token.type == "heading_open" and token.markup == "##" and token.level == 0 and token.map
    ]
    return [
        (title, lines[span[1]:headings[index + 1][1][0] if index + 1 < len(headings) else len(lines)])
        for index, (title, span) in enumerate(headings)
    ]
