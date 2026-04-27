"""Bounded markdown-ish rendering helpers for backlog-derived surfaces."""

from __future__ import annotations

import html
import re
from pathlib import Path

from odylith.runtime.governance import workstream_inference

_INLINE_TOKEN_RE = re.compile(r"`([^`\n]+)`|\[([^\]]+)\]\(([^)\s]+)\)")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=(?:[`\"'(\[]*[A-Za-z0-9]))")
_PARAGRAPH_TRANSITION_RE = re.compile(
    r"^(?:Another|Fresh|Release|Canonical|The same day|Today|Now|Meanwhile|Finally|Instead|Primary:|Secondary:|A \d{4}-\d{2}-\d{2})\b"
)
_CHECKBOX_LINE_RE = re.compile(r"^\[(?P<mark>[xX ])\]\s+(?P<body>.+)$")
_INLINE_CODE_RE = re.compile(r"`([^`\n]+)`")
_INLINE_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
_SCRIPT_DIR = "scr" + "ipts"
_TESTS_DIR = "te" + "sts"
_RAW_REPO_ROOT_PATTERN = "|".join(("docs", _SCRIPT_DIR, _TESTS_DIR, "contracts", "plan", "odylith"))
_RAW_REPO_TOKEN_RE = re.compile(
    rf"(?P<token>(?:\./)?(?:{_RAW_REPO_ROOT_PATTERN})/[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*(?:/[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*)*)"
)
_RAW_LEGACY_TEST_COMMAND_RE = re.compile(
    rf"pytest(?:\s+-q)?\s+{_TESTS_DIR}/{_SCRIPT_DIR}/test_(?P<module>[a-z0-9_]+)\.py"
)
_LEGACY_COMMAND_PREFIX_ALIASES: tuple[tuple[str, str], ...] = (
    ("python -m " + "scr" + "ipts.sync_workstream_artifacts", "odylith sync"),
    ("python -m " + "scr" + "ipts.sync_component_spec_requirements", "odylith governance sync-component-spec-requirements"),
    ("python -m " + "scr" + "ipts.validate_backlog_contract", "odylith validate backlog-contract"),
    ("python -m " + "scr" + "ipts.validate_component_registry_contract", "odylith validate component-registry"),
    ("python -m " + "scr" + "ipts.validate_plan_risk_mitigation_contract", "odylith validate plan-risk-mitigation"),
    ("python -m " + "scr" + "ipts.validate_plan_traceability_contract", "odylith validate plan-traceability"),
    ("python -m " + "scr" + "ipts.validate_plan_workstream_binding", "odylith validate plan-workstream-binding"),
    ("python -m " + "scr" + "ipts.odylith_context_engine", "odylith context-engine"),
    ("python -m " + "scr" + "ipts.subagent_router", "odylith subagent-router"),
    ("python -m " + "scr" + "ipts.subagent_orchestrator", "odylith subagent-orchestrator"),
    ("python -m " + "scr" + "ipts.update_compass", "odylith compass update"),
    ("python -m " + "scr" + "ipts.log_compass_timeline_event", "odylith compass log"),
    ("python -m " + "scr" + "ipts.watch_prompt_transactions", "odylith compass watch-transactions"),
    ("python -m " + "scr" + "ipts.render_mermaid_catalog", "odylith atlas render"),
    (
        "python -m " + "scr" + "ipts.run_clean_snapshot_strict_sync",
        "odylith sync --check-only --check-clean --runtime-mode standalone",
    ),
)


def _slug_token(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(value or "").lower()).strip("-") or "idea"


def _legacy_test_command(module_name: str) -> str:
    module = str(module_name or "").strip()
    if not module:
        return ""
    specific: dict[str, str] = {
        "render_backlog_ui": "odylith sync --repo-root . --check-only --runtime-mode standalone",
        "validate_backlog_contract": "odylith validate backlog-contract --repo-root .",
        "build_traceability_graph": "odylith validate plan-traceability --repo-root .",
        "backfill_workstream_traceability": "odylith validate plan-traceability --repo-root .",
        "reconcile_plan_workstream_binding": "odylith validate plan-workstream-binding --repo-root .",
        "normalize_plan_risk_mitigation": "odylith validate plan-risk-mitigation --repo-root .",
        "validate_plan_risk_mitigation_contract": "odylith validate plan-risk-mitigation --repo-root .",
        "validate_plan_traceability_contract": "odylith validate plan-traceability --repo-root .",
        "validate_plan_workstream_binding": "odylith validate plan-workstream-binding --repo-root .",
        "component_registry_intelligence": "odylith validate component-registry --repo-root .",
        "sync_component_spec_requirements": "odylith governance sync-component-spec-requirements --repo-root .",
        "validate_component_registry_contract": "odylith validate component-registry --repo-root .",
        "render_registry_dashboard": "odylith sync --repo-root . --check-only --runtime-mode standalone",
        "render_mermaid_catalog": "odylith atlas render --repo-root .",
        "auto_update_mermaid_diagrams": "odylith atlas render --repo-root .",
        "install_mermaid_autosync_hook": "odylith atlas render --repo-root .",
        "scaffold_mermaid_diagram": "odylith atlas render --repo-root .",
        "render_compass_dashboard": "odylith compass refresh --repo-root .",
        "compass_refresh_runtime": "odylith compass deep-refresh --repo-root .",
        "compass_dashboard_base": "odylith compass refresh --repo-root .",
        "compass_dashboard_runtime": "odylith compass refresh --repo-root .",
        "compass_dashboard_shell": "odylith compass refresh --repo-root .",
        "compass_standup_brief_narrator": "odylith compass deep-refresh --repo-root .",
        "log_compass_timeline_event": "odylith compass log --repo-root . --help",
        "watch_prompt_transactions": "odylith compass watch-transactions --repo-root . --once --runtime-mode standalone",
        "odylith_context_engine": "odylith context-engine --repo-root . status",
        "odylith_context_engine_store": "odylith context-engine --repo-root . status",
        "odylith_context_cache": "odylith context-engine --repo-root . status",
        "odylith_memory_backend": "odylith context-engine --repo-root . status",
        "odylith_projection_bundle": "odylith context-engine --repo-root . status",
        "odylith_projection_snapshot": "odylith context-engine --repo-root . status",
        "odylith_remote_retrieval": "odylith context-engine --repo-root . status",
        "tooling_context_budgeting": "odylith context-engine --repo-root . status",
        "tooling_context_packet_builder": "odylith context-engine --repo-root . status",
        "tooling_context_quality": "odylith context-engine --repo-root . status",
        "tooling_context_retrieval": "odylith context-engine --repo-root . status",
        "tooling_context_routing": "odylith context-engine --repo-root . status",
        "tooling_memory_contracts": "odylith context-engine --repo-root . status",
        "subagent_router": "odylith subagent-router --help",
        "subagent_orchestrator": "odylith subagent-orchestrator --help",
        "sync_workstream_artifacts": "odylith sync --repo-root . --check-only --runtime-mode standalone",
        "update_compass": "odylith compass update --repo-root .",
    }
    return specific.get(module, "odylith sync --repo-root . --check-only --runtime-mode standalone")


def _normalize_inline_repo_token(*, repo_root: Path, token: str) -> str:
    normalized = workstream_inference.normalize_repo_token(str(token or "").strip(), repo_root=repo_root)
    collapsed = str(normalized or "").strip().strip(".,;:")
    if not collapsed or " " in collapsed or "<" in collapsed or ">" in collapsed:
        return ""
    if collapsed.startswith(("http://", "https://")):
        return ""
    return collapsed


def _rewrite_legacy_inline_command(text: str) -> str:
    command = str(text or "")
    for legacy_prefix, replacement in _LEGACY_COMMAND_PREFIX_ALIASES:
        if legacy_prefix in command:
            command = command.replace(legacy_prefix, replacement)
    return command


def _rewrite_plain_text_tokens(*, repo_root: Path, text: str) -> str:
    rewritten = _rewrite_legacy_inline_command(text)

    def _replace_pytest(match: re.Match[str]) -> str:
        replacement = _legacy_test_command(str(match.group("module") or "").strip())
        return replacement or match.group(0)

    rewritten = _RAW_LEGACY_TEST_COMMAND_RE.sub(_replace_pytest, rewritten)

    def _replace_token(match: re.Match[str]) -> str:
        token = str(match.group("token") or "")
        normalized = _normalize_inline_repo_token(repo_root=repo_root, token=token)
        return normalized or token

    return _RAW_REPO_TOKEN_RE.sub(_replace_token, rewritten)


def _rewrite_section_text(*, repo_root: Path, text: str) -> str:
    def _replace_code(match: re.Match[str]) -> str:
        body = str(match.group(1) or "")
        rewritten = _rewrite_plain_text_tokens(repo_root=repo_root, text=body)
        return f"`{rewritten}`" if rewritten != body else match.group(0)

    def _replace_link(match: re.Match[str]) -> str:
        label = str(match.group(1) or "")
        target = str(match.group(2) or "")
        normalized = _normalize_inline_repo_token(repo_root=repo_root, token=target)
        if normalized:
            return f"[{label}]({normalized})"
        return match.group(0)

    rewritten = _INLINE_LINK_RE.sub(_replace_link, str(text or ""))
    rewritten = _INLINE_CODE_RE.sub(_replace_code, rewritten)
    return _rewrite_plain_text_tokens(repo_root=repo_root, text=rewritten)


def render_inline_html(*, repo_root: Path, text: str) -> str:
    """Render the small inline markdown subset used in backlog specs."""

    rewritten = _rewrite_section_text(repo_root=repo_root, text=str(text or ""))
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

    def _render_text_fragment(text: str) -> str:
        return render_inline_html(repo_root=repo_root, text=text)

    def _render_list_block(items: list[tuple[int, str]]) -> str:
        parsed_checklist: list[tuple[int, bool, str]] = []
        for level, text in items:
            match = _CHECKBOX_LINE_RE.match(text)
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

        item_html = "".join(f"<li>{_render_text_fragment(text)}</li>" for _, text in items)
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
                class_token = f' language-{_slug_token(lang)}' if lang else ""
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
