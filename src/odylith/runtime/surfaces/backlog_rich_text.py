"""Bounded markdown-ish rendering helpers for backlog-derived surfaces."""

from __future__ import annotations

import html
import re
from pathlib import Path

_INLINE_TOKEN_RE = re.compile(r"`([^`\n]+)`|\[([^\]]+)\]\(([^)\s]+)\)")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=(?:[`\"'(\[]*[A-Za-z0-9]))")
_PARAGRAPH_TRANSITION_RE = re.compile(
    r"^(?:Another|Fresh|Release|Canonical|The same day|Today|Now|Meanwhile|Finally|Instead|Primary:|Secondary:|A \d{4}-\d{2}-\d{2})\b"
)
def _host():
    from odylith.runtime.surfaces import render_backlog_ui as host

    return host


def render_inline_html(*, repo_root: Path, text: str) -> str:
    """Render the small inline markdown subset used in backlog specs."""

    host = _host()
    rewritten = host._rewrite_section_text(repo_root=repo_root, text=str(text or ""))  # noqa: SLF001
    if not rewritten:
        return ""

    parts: list[str] = []
    cursor = 0
    for match in _INLINE_TOKEN_RE.finditer(rewritten):
        start, end = match.span()
        if start > cursor:
            parts.append(html.escape(rewritten[cursor:start]))

        code_text = match.group(1)
        if code_text is not None:
            parts.append(f"<code>{html.escape(code_text)}</code>")
        else:
            label = str(match.group(2) or "").strip()
            href = str(match.group(3) or "").strip()
            if not label or not href:
                parts.append(html.escape(match.group(0)))
            else:
                safe_href = html.escape(href, quote=True)
                safe_label = html.escape(label)
                external = href.startswith(("http://", "https://"))
                target_attr = ' target="_blank" rel="noopener noreferrer"' if external else ' target="_top"'
                parts.append(f'<a href="{safe_href}"{target_attr}>{safe_label}</a>')
        cursor = end

    if cursor < len(rewritten):
        parts.append(html.escape(rewritten[cursor:]))
    return "".join(parts)


def render_section_body(*, repo_root: Path, lines: list[str]) -> str:
    """Render a markdown-ish backlog section body into bounded HTML."""

    host = _host()

    def _render_text_fragment(text: str) -> str:
        return render_inline_html(repo_root=repo_root, text=text)

    def _render_list_block(items: list[tuple[int, str]]) -> str:
        parsed_checklist: list[tuple[int, bool, str]] = []
        for level, text in items:
            match = host._CHECKBOX_LINE_RE.match(text)  # noqa: SLF001
            if match is None:
                parsed_checklist = []
                break
            parsed_checklist.append(
                (
                    level,
                    str(match.group("mark")).lower() == "x",
                    str(match.group("body")).strip(),
                )
            )

        if parsed_checklist:
            base_level = min(level for level, _, _ in parsed_checklist)
            rows = "".join(
                (
                    f'<div class="check-item" style="--level:{max(0, level - base_level)}">'
                    f'<input class="check-box" type="checkbox" disabled{" checked" if checked else ""} />'
                    f'<div class="check-text">{_render_text_fragment(body)}</div>'
                    "</div>"
                )
                for level, checked, body in parsed_checklist
            )
            return f'<div class="checklist">{rows}</div>'

        item_html = "".join(
            f"<li>{_render_text_fragment(text)}</li>"
            for _, text in items
        )
        return f"<ul>{item_html}</ul>"

    def _bullet_level(raw_line: str) -> int:
        leading_spaces = len(raw_line) - len(raw_line.lstrip(" "))
        return max(0, leading_spaces // 2)

    def _split_dense_paragraph(text: str) -> list[str]:
        normalized = " ".join(str(text or "").split())
        if len(normalized) < 420:
            return [normalized]

        sentences = [token.strip() for token in _SENTENCE_SPLIT_RE.split(normalized) if token.strip()]
        if len(sentences) < 3:
            return [normalized]

        paragraphs: list[str] = []
        current: list[str] = []
        current_len = 0

        def _flush() -> None:
            nonlocal current, current_len
            if current:
                paragraphs.append(" ".join(current).strip())
            current = []
            current_len = 0

        for sentence in sentences:
            sentence_len = len(sentence)
            should_start_new = bool(
                current
                and (
                    _PARAGRAPH_TRANSITION_RE.match(sentence)
                    or current_len >= 260
                    or len(current) >= 2
                )
            )
            if should_start_new:
                _flush()
            current.append(sentence)
            current_len = current_len + sentence_len + (1 if current_len else 0)

        _flush()
        compact = [paragraph for paragraph in paragraphs if paragraph]
        return compact if len(compact) >= 2 else [normalized]

    blocks: list[str] = []
    idx = 0
    total = len(lines)
    while idx < total:
        current = lines[idx].rstrip()
        current_stripped = current.strip()
        if not current_stripped:
            idx += 1
            continue

        if current_stripped.startswith("```"):
            lang = current_stripped[3:].strip().lower()
            idx += 1
            code_lines: list[str] = []
            while idx < total:
                token = lines[idx].rstrip()
                if token.strip().startswith("```"):
                    idx += 1
                    break
                code_lines.append(token)
                idx += 1
            code_body = "\n".join(code_lines).rstrip()
            if lang == "mermaid":
                blocks.append(
                    f'<div class="mermaid-wrap"><div class="mermaid">{html.escape(code_body)}</div></div>'
                )
            else:
                class_token = f' language-{host._slug_token(lang)}' if lang else ""  # noqa: SLF001
                blocks.append(
                    f'<pre class="code{class_token}"><code>{html.escape(code_body)}</code></pre>'
                )
            continue

        if current.lstrip().startswith("- "):
            items: list[list[object]] = []
            while idx < total:
                token = lines[idx].rstrip()
                token_stripped = token.strip()
                if not token_stripped:
                    break
                if token.lstrip().startswith("- "):
                    normalized = token.lstrip()
                    items.append([_bullet_level(token), normalized[2:].strip()])
                    idx += 1
                    continue
                if (
                    items
                    and token.startswith(" ")
                    and not token.startswith("### ")
                    and not token_stripped.startswith("```")
                ):
                    items[-1][1] = f"{items[-1][1]} {token_stripped}".strip()
                    idx += 1
                    continue
                if token.startswith("### ") or token_stripped.startswith("```"):
                    break
                break
            blocks.append(_render_list_block([(int(level), str(text)) for level, text in items]))
            continue

        if current.startswith("### "):
            blocks.append(
                f'<h3>{render_inline_html(repo_root=repo_root, text=current[4:].strip())}</h3>'
            )
            idx += 1
            continue

        paragraph: list[str] = [current_stripped]
        idx += 1
        while idx < total:
            token = lines[idx].rstrip()
            token_stripped = token.strip()
            if (
                not token_stripped
                or token.lstrip().startswith("- ")
                or token.startswith("### ")
                or token_stripped.startswith("```")
            ):
                break
            paragraph.append(token_stripped)
            idx += 1
        paragraph_text = " ".join(paragraph)
        blocks.extend(
            f'<p>{render_inline_html(repo_root=repo_root, text=chunk)}</p>'
            for chunk in _split_dense_paragraph(paragraph_text)
        )

    if not blocks:
        return "<p>Not captured in this section.</p>"
    return "".join(blocks)
