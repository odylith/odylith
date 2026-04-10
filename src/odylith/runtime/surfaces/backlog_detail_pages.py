"""Standalone backlog detail-page renderers extracted from the main Radar UI."""

from __future__ import annotations

import html
from pathlib import Path

from odylith.runtime.surfaces import backlog_rich_text


def _host():
    from odylith.runtime.surfaces import render_backlog_ui as host

    return host


def _render_idea_spec_html(
    *,
    repo_root: Path,
    index_output_path: Path,
    entry: dict[str, object],
    destination_output_path: Path | None = None,
) -> str:
    host = _host()
    _resolve_path = host._resolve_path
    _as_portable_relative_href = host._as_portable_relative_href
    _extract_sections_with_body = host._extract_sections_with_body
    _radar_route_href = host._radar_route_href
    _rewrite_section_text = host._rewrite_section_text
    _render_section_body = host._render_section_body
    dashboard_ui_primitives = host.dashboard_ui_primitives
    contract = host.contract

    idea_file = str(entry.get("idea_file", "")).strip()
    idea_path = _resolve_path(repo_root=repo_root, value=idea_file)
    if not idea_path.is_file():
        raise FileNotFoundError(f"missing idea markdown: {idea_path}")

    idea_output_path = destination_output_path or index_output_path
    index_href = _as_portable_relative_href(output_path=idea_output_path, target=index_output_path)

    spec = contract._parse_idea_spec(idea_path)
    metadata = spec.metadata
    sections = _extract_sections_with_body(idea_path)
    section_map: dict[str, list[str]] = {}
    for section_title, section_lines in sections:
        normalized_title = section_title.strip().lower()
        if normalized_title and normalized_title not in section_map:
            section_map[normalized_title] = section_lines

    promoted_to_plan_ui_file = str(entry.get("promoted_to_plan_ui_file", "")).strip()
    promoted_to_plan_ui_href = ""
    if promoted_to_plan_ui_file:
        promoted_to_plan_ui_href = _radar_route_href(
            source_output_path=idea_output_path,
            target_output_path=index_output_path,
            workstream_id=str(entry.get("idea_id", "")).strip(),
            view="plan",
        )

    meta_pairs = [
        ("Workstream ID", entry.get("idea_id", "")),
        ("Status", metadata.get("status", "")),
        ("Priority", metadata.get("priority", "")),
        ("Created Date", entry.get("idea_date_display", entry.get("idea_date", metadata.get("date", "")))),
        ("Age (days)", entry.get("idea_age_days", "")),
        ("Execution Start", entry.get("execution_start_date_display", entry.get("execution_start_date", ""))),
        ("Execution End", entry.get("execution_end_date_display", entry.get("execution_end_date", ""))),
        ("Execution Days", entry.get("execution_duration_days", entry.get("execution_age_days", ""))),
        ("Sizing", metadata.get("sizing", "")),
        ("Complexity", metadata.get("complexity", "")),
        ("Ordering Score", metadata.get("ordering_score", "")),
        ("Confidence", metadata.get("confidence", "")),
        ("Priority Override", metadata.get("founder_override", "")),
    ]
    meta_html = "".join(
        (
            f"<div class=\"meta-item\">"
            f"<div class=\"meta-key\">{html.escape(str(label))}</div>"
            f"<div class=\"meta-val\">{html.escape(str(value).strip() or '-')}</div>"
            f"</div>"
        )
        for label, value in meta_pairs
    )

    rationale_raw = entry.get("rationale_bullets", [])
    implemented_summary = str(entry.get("implemented_summary", "")).strip()
    rationale_bullets = (
        [str(item).strip() for item in rationale_raw if str(item).strip()]
        if isinstance(rationale_raw, list)
        else []
    )
    if not rationale_bullets:
        fallback = str(metadata.get("ordering_rationale", "")).strip()
        if fallback:
            rationale_bullets = [fallback]
    if len(rationale_bullets) > 1:
        rationale_html = _render_section_body(
            repo_root=repo_root,
            lines=[f"- {item}" for item in rationale_bullets],
        )
    elif len(rationale_bullets) == 1:
        rationale_html = _render_section_body(
            repo_root=repo_root,
            lines=[rationale_bullets[0]],
        )
    else:
        rationale_html = "<p>No decision-basis bullets recorded.</p>"
    product_view_lines = section_map.get("product view", section_map.get("founder pov", []))
    product_view_html = (
        _render_section_body(repo_root=repo_root, lines=product_view_lines)
        if product_view_lines
        else "<p>Not captured in the idea spec yet.</p>"
    )

    problem_section_html = "".join(
        (
            f"<section class=\"block\">"
            f"<h2>{html.escape(title)}</h2>"
            f"{_render_section_body(repo_root=repo_root, lines=lines)}"
            f"</section>"
        )
        for title, lines in sections
        if title.strip().lower() == "problem"
    )
    section_html = "".join(
        (
            f"<section class=\"block\">"
            f"<h2>{html.escape(title)}</h2>"
            f"{_render_section_body(repo_root=repo_root, lines=lines)}"
            f"</section>"
        )
        for title, lines in sections
        if title.strip().lower() not in {"product view", "founder pov", "problem"}
    )
    if not problem_section_html and not section_html:
        section_html = "<section class=\"block\"><h2>Content</h2><p>No markdown sections found.</p></section>"

    implemented_summary_html = (
        "<section class=\"block\">"
        "<h2>Implemented Summary</h2>"
        f"{_render_section_body(repo_root=repo_root, lines=[implemented_summary])}"
        "</section>"
        if implemented_summary
        else ""
    )

    plan_links: list[str] = []
    if promoted_to_plan_ui_href:
        plan_links.append(
            f"<a href=\"{html.escape(promoted_to_plan_ui_href)}\">Technical Implementation Plan</a>"
        )
    plan_link_html = (
        "".join(plan_links)
        if plan_links
        else "<span>No linked technical implementation plan</span>"
    )

    title = html.escape(str(entry.get("title", "")).strip() or "Workstream Spec")
    idea_id = html.escape(str(entry.get("idea_id", "")).strip())
    priority = html.escape(str(entry.get("priority", "")).strip())
    status = html.escape(str(entry.get("status", "")).strip())
    score = html.escape(str(entry.get("ordering_score", "")).strip())
    page_body_css = dashboard_ui_primitives.page_body_typography_css(
        selector="body",
        color="var(--ink)",
    )
    surface_shell_root_css = dashboard_ui_primitives.standard_surface_shell_root_css()
    surface_shell_css = dashboard_ui_primitives.standard_surface_shell_css(
        selector=".shell",
        padding="18px 14px 26px",
    )
    title_css = dashboard_ui_primitives.display_title_typography_css(
        title_selector="h1",
        title_size="29px",
        title_line_height=1.15,
        title_letter_spacing_em=-0.01,
    ) + "\n\nh1 {\n  margin: 0 0 6px;\n}"
    chip_surface_css = dashboard_ui_primitives.label_surface_css(
        selector="span.chip",
        min_height_px=0,
        padding="4px 10px",
        background="#f6faf7",
        border_color="#d6e2da",
        color="#314559",
        border_radius_px=4,
        border_width_px=1,
    )
    chip_css = dashboard_ui_primitives.label_badge_typography_css(
        selector="span.chip",
        color="#1e40af",
        size_px=11,
    )
    meta_key_css = dashboard_ui_primitives.section_heading_css(
        selector=".meta-key",
        color="var(--muted)",
        size_px=11,
        letter_spacing_em=0.06,
        margin="0 0 2px 0",
    )
    meta_value_css = dashboard_ui_primitives.value_emphasis_typography_css(
        selector=".meta-val",
        color="var(--ink)",
        size_px=15,
        line_height=1.25,
        weight=700,
    )
    block_heading_css = dashboard_ui_primitives.section_heading_css(
        selector=".block h2",
        color="#334155",
        size_px=12,
        letter_spacing_em=0.08,
        margin="0 0 8px 0",
    )
    block_subheading_css = dashboard_ui_primitives.section_heading_css(
        selector=".block h3",
        color="var(--ink)",
        size_px=14,
        line_height=1.25,
        letter_spacing_em=0.0,
        text_transform="none",
        margin="10px 0 6px 0",
    )
    body_copy_css = dashboard_ui_primitives.content_copy_css(
        selectors=(
            ".block p",
            ".block ul",
            ".block li",
            ".check-text",
        ),
        color="#27445e",
    )
    code_css = dashboard_ui_primitives.code_typography_css(
        selector=".code",
    )
    idea_id_css = dashboard_ui_primitives.mono_identifier_typography_css(
        selector=".id",
        color="var(--muted)",
    )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title}</title>
  <style>
    :root {{
      --bg: #f8fafc;
      --panel: #ffffff;
      --ink: #0f172a;
      --muted: #475569;
      --line: #cbd5e1;
      --brand: #1d4ed8;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: linear-gradient(180deg, #eef2ff, var(--bg));
    }}
    {page_body_css}
    {surface_shell_root_css}
    {surface_shell_css}
    .back {{
      display: inline-block;
      margin-bottom: 12px;
      text-decoration: none;
      color: var(--brand);
      font-weight: 600;
    }}
    .hero {{
      border: 1px solid var(--line);
      border-radius: 14px;
      background: var(--panel);
      padding: 14px 14px 12px;
      margin-bottom: 12px;
    }}
    h1 {{
      margin: 0 0 6px;
    }}
    {title_css}
    .id {{
      margin: 0;
      color: var(--muted);
    }}
    {idea_id_css}
    .chips {{
      margin-top: 10px;
      display: flex;
      gap: 6px;
      flex-wrap: wrap;
    }}
    {chip_surface_css}
    {chip_css}
    .meta-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
      gap: 8px;
      margin-bottom: 12px;
    }}
    .meta-item {{
      border: 1px solid var(--line);
      background: var(--panel);
      border-radius: 10px;
      padding: 8px 9px;
    }}
    .meta-key {{
      color: var(--muted);
      margin-bottom: 2px;
    }}
    {meta_key_css}
    .meta-val {{
    }}
    {meta_value_css}
    .founder-group {{
      border: 1px solid var(--line);
      background: var(--panel);
      border-radius: 12px;
      padding: 10px;
      margin-bottom: 10px;
      display: grid;
      gap: 10px;
    }}
    .founder-card {{
      margin-bottom: 0;
      min-width: 0;
    }}
    .block {{
      border: 1px solid var(--line);
      background: var(--panel);
      border-radius: 12px;
      padding: 11px 12px;
      margin-bottom: 10px;
    }}
    .block h2 {{
      margin: 0 0 8px;
    }}
    {block_heading_css}
    .block h3 {{
      margin: 10px 0 6px;
    }}
    {block_subheading_css}
    .block p {{
      margin: 0 0 8px;
    }}
    .block ul {{
      margin: 0;
      padding-left: 20px;
    }}
    .block code,
    .meta-val code {{
      font-family: {dashboard_ui_primitives.MONO_FONT_FAMILY};
      font-size: 0.92em;
      color: #1e3a8a;
      background: #eff6ff;
      border: 1px solid #dbeafe;
      border-radius: 6px;
      padding: 0.08em 0.38em;
      overflow-wrap: anywhere;
      word-break: break-word;
    }}
    .block a,
    .meta-val a {{
      color: var(--brand);
      text-decoration: none;
      border-bottom: 1px solid #bfdbfe;
    }}
    {body_copy_css}
    .checklist {{
      display: flex;
      flex-direction: column;
      gap: 7px;
    }}
    .check-item {{
      --level: 0;
      display: grid;
      grid-template-columns: 18px minmax(0, 1fr);
      gap: 9px;
      align-items: start;
      padding-left: calc(var(--level) * 28px);
    }}
    .check-box {{
      width: 16px;
      height: 16px;
      margin: 2px 0 0;
      accent-color: #0f766e;
      cursor: default;
      flex: 0 0 auto;
    }}
    .check-box:disabled {{
      opacity: 1;
    }}
    .check-text {{
      min-width: 0;
    }}
    .check-text > *:first-child {{
      margin-top: 0;
    }}
    .check-text > *:last-child {{
      margin-bottom: 0;
    }}
    .code {{
      margin: 0;
      border: 1px solid var(--line);
      border-radius: 10px;
      background: #0f172a;
      padding: 10px 11px;
      overflow: auto;
    }}
    {code_css}
    .code code {{
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      word-break: break-word;
    }}
    .mermaid-wrap {{
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: 10px;
      background: #ffffff;
      overflow: auto;
    }}
    .mermaid {{
      min-width: 320px;
    }}
    .links {{
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      font-size: 13px;
    }}
    .links a {{
      color: var(--brand);
      text-decoration: none;
      border-bottom: 1px dotted #93c5fd;
    }}
  </style>
</head>
<body>
  <main class="shell">
    <a class="back" href="{html.escape(index_href)}">Back to Backlog Radar</a>
    <header class="hero">
      <h1>{title}</h1>
      <p class="id">{idea_id}</p>
      <div class="chips">
        <span class="chip">{priority}</span>
        <span class="chip">{status}</span>
        <span class="chip">Score {score}</span>
      </div>
    </header>

    <section class="meta-grid">
      {meta_html}
    </section>

    <section class="block">
      <h2>Traceability</h2>
      <div class="links">
        {plan_link_html}
      </div>
    </section>

    {implemented_summary_html}

    {problem_section_html}

    <section class="founder-group">
      <article class="block founder-card">
        <h2>Product View</h2>
        {product_view_html}
      </article>
      <article class="block founder-card">
        <h2>Decision Basis</h2>
        {rationale_html}
      </article>
    </section>

    {section_html}
  </main>
  <script src="https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"></script>
  <script>
    (function() {{
      if (!window.mermaid || !document.querySelector(".mermaid")) return;
      window.mermaid.initialize({{
        startOnLoad: false,
        securityLevel: "strict",
        theme: "neutral"
      }});
      window.mermaid.run({{ querySelector: ".mermaid" }});
    }})();
  </script>
</body>
</html>
"""


def _extract_plan_metadata(path: Path) -> dict[str, str]:
    content = path.read_text(encoding="utf-8")
    lines = content.splitlines()
    parsed: dict[str, str] = {}
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        if line.startswith("## "):
            break
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        parsed[key.strip()] = value.strip()
    return parsed


def _render_plan_html(
    *,
    repo_root: Path,
    index_output_path: Path,
    entry: dict[str, object],
    destination_output_path: Path | None = None,
) -> str:
    host = _host()
    _resolve_path = host._resolve_path
    _as_portable_relative_href = host._as_portable_relative_href
    _radar_route_href = host._radar_route_href
    _extract_sections_with_body = host._extract_sections_with_body
    _render_section_body = host._render_section_body
    _rewrite_section_text = host._rewrite_section_text
    _collect_plan_traceability_paths = host._collect_plan_traceability_paths
    _TRACEABILITY_SECTION_NAME = host._TRACEABILITY_SECTION_NAME
    _TRACEABILITY_BUCKETS = host._TRACEABILITY_BUCKETS
    dashboard_ui_primitives = host.dashboard_ui_primitives

    plan_file = str(entry.get("promoted_to_plan_file", "")).strip()
    if not plan_file:
        raise FileNotFoundError("missing promoted_to_plan_file")
    plan_path = _resolve_path(repo_root=repo_root, value=plan_file)
    if not plan_path.is_file():
        raise FileNotFoundError(f"missing plan markdown: {plan_path}")

    plan_output_path = destination_output_path or index_output_path

    index_href = _as_portable_relative_href(output_path=plan_output_path, target=index_output_path)
    idea_ui_href = ""
    if str(entry.get("idea_id", "")).strip():
        idea_ui_href = _radar_route_href(
            source_output_path=plan_output_path,
            target_output_path=index_output_path,
            workstream_id=str(entry.get("idea_id", "")).strip(),
            view="spec",
        )

    plan_meta = _extract_plan_metadata(plan_path)
    sections = _extract_sections_with_body(plan_path)

    meta_order = (
        "Status",
        "Created",
        "Updated",
        "Goal",
        "Assumptions",
        "Constraints",
        "Reversibility",
        "Boundary Conditions",
    )
    meta_pairs = [(label, plan_meta.get(label, "")) for label in meta_order if plan_meta.get(label, "")]
    extra_keys = [key for key in plan_meta.keys() if key not in set(meta_order)]
    for key in extra_keys:
        meta_pairs.append((key, plan_meta.get(key, "")))
    if not meta_pairs:
        meta_pairs.append(("Status", "Unknown"))
    summary_keys = {"Status", "Created", "Updated"}
    summary_pairs = [(label, value) for label, value in meta_pairs if label in summary_keys]
    detail_pairs = [(label, value) for label, value in meta_pairs if label not in summary_keys]
    if not summary_pairs:
        summary_pairs = [meta_pairs[0]]
        detail_pairs = meta_pairs[1:]

    summary_html = "".join(
        (
            f"<div class=\"meta-item\">"
            f"<div class=\"meta-key\">{html.escape(label)}</div>"
            f"<div class=\"meta-val\">{backlog_rich_text.render_inline_html(repo_root=repo_root, text=value or '-')}</div>"
            f"</div>"
        )
        for label, value in summary_pairs
    )
    detail_html = "".join(
        (
            f"<div class=\"meta-row\">"
            f"<div class=\"meta-row-key\">{html.escape(label)}</div>"
            f"<div class=\"meta-row-val\">{_render_section_body(repo_root=repo_root, lines=[value or '-'])}</div>"
            f"</div>"
        )
        for label, value in detail_pairs
    )
    detail_block_html = f"<section class=\"meta-list\">{detail_html}</section>" if detail_html else ""

    section_html = "".join(
        (
            f"<section class=\"block\">"
            f"<h2>{html.escape(title)}</h2>"
            f"{_render_section_body(repo_root=repo_root, lines=lines)}"
            f"</section>"
        )
        for title, lines in sections
        if title.strip().lower() != _TRACEABILITY_SECTION_NAME.lower()
    )
    if not section_html:
        section_html = "<section class=\"block\"><h2>Content</h2><p>No markdown sections found.</p></section>"

    workstream_title = str(entry.get("title", "")).strip() or "Workstream"
    plan_title = f"{workstream_title} Technical Implementation Plan"
    plan_id = str(entry.get("idea_id", "")).strip()
    plan_status = str(plan_meta.get("Status", "")).strip() or "Unknown"

    workstream_traceability_html = (
        f"<a class=\"trace-workstream-link\" href=\"{html.escape(idea_ui_href)}\">Workstream Spec</a>"
        if idea_ui_href
        else "<span>No linked workstream page</span>"
    )
    plan_traceability = _collect_plan_traceability_paths(repo_root=repo_root, sections=sections)
    traceability_group_html = ""
    for label in _TRACEABILITY_BUCKETS:
        paths = plan_traceability.get(label, [])
        if not paths:
            continue
        items: list[str] = []
        for rel_path in paths:
            target = (repo_root / rel_path).resolve()
            display = html.escape(rel_path)
            file_name = html.escape(Path(rel_path).name or rel_path)
            if target.exists():
                href = _as_portable_relative_href(output_path=plan_output_path, target=target)
                items.append(
                    (
                        f"<a class=\"trace-link\" href=\"{html.escape(href)}\" title=\"{display}\">"
                        f"<span class=\"trace-file\">{file_name}</span>"
                        f"<span class=\"trace-path\">{display}</span>"
                        f"</a>"
                    )
                )
            else:
                items.append(
                    (
                        f"<div class=\"trace-link trace-link-missing\" title=\"{display}\">"
                        f"<span class=\"trace-file\">{file_name}</span>"
                        f"<span class=\"trace-path\">{display}</span>"
                        f"<span class=\"trace-state\">Missing</span>"
                        f"</div>"
                    )
                )
        traceability_group_html += (
            f"<section class=\"trace-group\">"
            f"<div class=\"trace-head\">"
            f"<h3>{html.escape(label)}</h3>"
            f"<span class=\"trace-count\">{len(paths)} file{'s' if len(paths) != 1 else ''}</span>"
            f"</div>"
            f"<div class=\"trace-list\">{''.join(items)}</div>"
            f"</section>"
        )
    traceability_block_html = (
        f"<div class=\"trace-groups\">{traceability_group_html}</div>"
        if traceability_group_html
        else "<p>No plan traceability section captured.</p>"
    )
    page_body_css = dashboard_ui_primitives.page_body_typography_css(
        selector="body",
        color="var(--ink)",
    )
    surface_shell_root_css = dashboard_ui_primitives.standard_surface_shell_root_css()
    surface_shell_css = dashboard_ui_primitives.standard_surface_shell_css(
        selector=".shell",
        padding="18px 14px 28px",
    )
    title_css = dashboard_ui_primitives.display_title_typography_css(
        title_selector="h1",
        title_size="30px",
        title_line_height=1.15,
        title_letter_spacing_em=-0.01,
    ) + "\n\nh1 {\n  margin: 0 0 6px;\n}"
    chip_surface_css = dashboard_ui_primitives.label_surface_css(
        selector="span.chip",
        min_height_px=0,
        padding="4px 10px",
        background="#f6faf7",
        border_color="#d6e2da",
        color="#314559",
        border_radius_px=4,
        border_width_px=1,
    )
    chip_css = dashboard_ui_primitives.label_badge_typography_css(
        selector="span.chip",
        color="#1e40af",
        size_px=11,
    )
    meta_key_css = dashboard_ui_primitives.section_heading_css(
        selector=".meta-key, .meta-row-key",
        color="var(--muted)",
        size_px=11,
        letter_spacing_em=0.08,
        margin="0",
    )
    meta_value_css = dashboard_ui_primitives.value_emphasis_typography_css(
        selector=".meta-val",
        color="var(--ink)",
        size_px=14,
        line_height=1.35,
        weight=700,
    )
    block_heading_css = dashboard_ui_primitives.section_heading_css(
        selector=".block h2, .trace-group h3",
        color="#334155",
        size_px=12,
        letter_spacing_em=0.08,
        margin="0 0 8px 0",
    )
    block_subheading_css = dashboard_ui_primitives.section_heading_css(
        selector=".block h3",
        color="var(--ink)",
        size_px=14,
        line_height=1.25,
        letter_spacing_em=0.0,
        text_transform="none",
        margin="10px 0 6px 0",
    )
    plan_body_copy_css = dashboard_ui_primitives.content_copy_css(
        selectors=(
            ".block p",
            ".block ul",
            ".block li",
            ".meta-val",
            ".meta-row-val",
            ".meta-row-val p",
            ".meta-row-val ul",
            ".meta-row-val li",
            ".check-text",
        ),
        color="#27445e",
    )
    code_css = dashboard_ui_primitives.code_typography_css(
        selector=".code",
    )
    trace_file_css = dashboard_ui_primitives.card_title_typography_css(
        selector=".trace-file",
        color="#1e293b",
        size_px=12,
        line_height=1.3,
        letter_spacing_em=0.0,
        margin="0",
    )
    trace_path_css = dashboard_ui_primitives.mono_identifier_typography_css(
        selector=".trace-path",
        color="#475569",
        size_px=12,
        line_height=1.3,
        margin="0",
    )
    trace_state_css = dashboard_ui_primitives.section_heading_css(
        selector=".trace-state",
        color="#9a3412",
        size_px=10,
        line_height=1.0,
        letter_spacing_em=0.06,
        margin="0",
    )
    trace_count_css = dashboard_ui_primitives.caption_typography_css(
        selector=".trace-count",
        color="#64748b",
        size_px=11,
        line_height=1.3,
        weight=600,
    )
    trace_link_button_css = dashboard_ui_primitives.button_typography_css(
        selector=".links a",
        color="var(--brand)",
        size_px=12,
        line_height=1.0,
        weight=600,
    )
    plan_id_css = dashboard_ui_primitives.mono_identifier_typography_css(
        selector=".id",
        color="var(--muted)",
    )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{html.escape(plan_title)}</title>
  <style>
    :root {{
      --bg: #f8fafc;
      --panel: #ffffff;
      --ink: #0f172a;
      --muted: #475569;
      --line: #cbd5e1;
      --brand: #1d4ed8;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: linear-gradient(180deg, #ecfeff, var(--bg));
    }}
    {page_body_css}
    {surface_shell_root_css}
    {surface_shell_css}
    .back {{
      display: inline-block;
      margin-bottom: 12px;
      text-decoration: none;
      color: var(--brand);
      font-weight: 600;
    }}
    .hero {{
      border: 1px solid var(--line);
      border-radius: 14px;
      background: var(--panel);
      padding: 14px 14px 12px;
      margin-bottom: 12px;
    }}
    h1 {{
      margin: 0 0 6px;
    }}
    {title_css}
    .id {{
      margin: 0;
      color: var(--muted);
    }}
    {plan_id_css}
    .chips {{
      margin-top: 10px;
      display: flex;
      gap: 6px;
      flex-wrap: wrap;
    }}
    {chip_surface_css}
    {chip_css}
    .meta-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
      gap: 8px;
      margin-bottom: 12px;
    }}
    .meta-item {{
      border: 1px solid var(--line);
      background: var(--panel);
      border-radius: 10px;
      padding: 8px 9px;
    }}
    .meta-key {{
      color: var(--muted);
      margin-bottom: 2px;
    }}
    .meta-val {{
    }}
    {meta_value_css}
    .meta-list {{
      border: 1px solid var(--line);
      border-radius: 12px;
      background: var(--panel);
      padding: 10px 11px;
      margin-bottom: 12px;
    }}
    .meta-row {{
      display: grid;
      grid-template-columns: minmax(170px, 220px) 1fr;
      gap: 12px;
      padding: 8px 0;
      border-bottom: 1px dashed #dbe4ef;
      align-items: start;
    }}
    .meta-row:last-child {{
      border-bottom: 0;
      padding-bottom: 2px;
    }}
    .meta-row-key {{
      color: var(--muted);
    }}
    {meta_key_css}
    .meta-row-val {{
      color: #0f172a;
      font-weight: 400;
    }}
    .block {{
      border: 1px solid var(--line);
      background: var(--panel);
      border-radius: 12px;
      padding: 11px 12px;
      margin-bottom: 10px;
    }}
    .block h2 {{
      margin: 0 0 8px;
    }}
    {block_heading_css}
    .block h3 {{
      margin: 10px 0 6px;
    }}
    {block_subheading_css}
    .block p {{
      margin: 0 0 8px;
    }}
    .block ul {{
      margin: 0;
      padding-left: 20px;
    }}
    .block code,
    .meta-val code,
    .meta-row-val code {{
      font-family: {dashboard_ui_primitives.MONO_FONT_FAMILY};
      font-size: 0.92em;
      color: #1e3a8a;
      background: #eff6ff;
      border: 1px solid #dbeafe;
      border-radius: 6px;
      padding: 0.08em 0.38em;
      overflow-wrap: anywhere;
      word-break: break-word;
    }}
    .block a,
    .meta-val a,
    .meta-row-val a {{
      color: var(--brand);
      text-decoration: none;
      border-bottom: 1px solid #bfdbfe;
    }}
    .meta-row-val > *:first-child {{
      margin-top: 0;
    }}
    .meta-row-val > *:last-child {{
      margin-bottom: 0;
    }}
    .meta-row-val p {{
      margin: 0 0 8px;
    }}
    .meta-row-val ul {{
      margin: 0;
      padding-left: 20px;
    }}
    {plan_body_copy_css}
    .checklist {{
      display: flex;
      flex-direction: column;
      gap: 7px;
    }}
    .check-item {{
      --level: 0;
      display: grid;
      grid-template-columns: 18px minmax(0, 1fr);
      gap: 9px;
      align-items: start;
      padding-left: calc(var(--level) * 28px);
    }}
    .check-box {{
      width: 16px;
      height: 16px;
      margin: 2px 0 0;
      accent-color: #0f766e;
      cursor: default;
      flex: 0 0 auto;
    }}
    .check-box:disabled {{
      opacity: 1;
    }}
    .check-text {{
      min-width: 0;
    }}
    .check-text > *:first-child {{
      margin-top: 0;
    }}
    .check-text > *:last-child {{
      margin-bottom: 0;
    }}
    .code {{
      margin: 0;
      border: 1px solid var(--line);
      border-radius: 10px;
      background: #0f172a;
      padding: 10px 11px;
      overflow: auto;
    }}
    {code_css}
    .code code {{
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      word-break: break-word;
    }}
    .mermaid-wrap {{
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: 10px;
      background: #ffffff;
      overflow: auto;
    }}
    .mermaid {{
      min-width: 320px;
    }}
    .links {{
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      font-size: 13px;
      margin-bottom: 10px;
    }}
    .links a {{
      color: var(--brand);
      text-decoration: none;
      border: 1px solid #bfdbfe;
      border-radius: 999px;
      background: #eff6ff;
      padding: 5px 10px;
    }}
    {trace_link_button_css}
    .trace-workstream-link:hover {{
      border-color: #60a5fa;
      background: #dbeafe;
    }}
    .trace-groups {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 11px;
      align-items: start;
      margin-top: 10px;
    }}
    .trace-group {{
      border: 1px solid var(--line);
      border-radius: 10px;
      background: #f8fafc;
      padding: 9px 10px;
    }}
    .trace-head {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      margin-bottom: 7px;
    }}
    .trace-group h3 {{
      margin: 0;
      color: #334155;
    }}
    .trace-count {{
    }}
    {trace_count_css}
    .trace-list {{
      display: flex;
      flex-direction: column;
      gap: 7px;
    }}
    .trace-link {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      grid-template-rows: auto auto;
      column-gap: 8px;
      row-gap: 2px;
      width: 100%;
      border: 1px solid #dbe4ef;
      border-radius: 8px;
      background: #ffffff;
      padding: 6px 8px;
      color: #0f172a;
      text-decoration: none;
      min-height: 0;
    }}
    .trace-link:hover {{
      border-color: #93c5fd;
      background: #f8fbff;
    }}
    .trace-file {{
      grid-column: 1 / 2;
      grid-row: 1 / 2;
    }}
    {trace_file_css}
    .trace-link-missing {{
      color: #7c2d12;
      border-color: #fed7aa;
      background: #fff7ed;
    }}
    .trace-path {{
      grid-column: 1 / 2;
      grid-row: 2 / 3;
      display: block;
      width: 100%;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }}
    {trace_path_css}
    .trace-state {{
      grid-column: 2 / 3;
      grid-row: 1 / 3;
      align-self: center;
    }}
    {trace_state_css}
    @media (max-width: 920px) {{
      .meta-row {{
        grid-template-columns: 1fr;
        gap: 5px;
      }}
      .meta-row-val {{
        font-size: 15px;
      }}
    }}
  </style>
</head>
<body>
  <main class="shell">
    <a class="back" href="{html.escape(index_href)}">Back to Backlog Workstream Radar</a>
    <header class="hero">
      <h1>{html.escape(plan_title)}</h1>
      <p class="id">{html.escape(plan_id)}</p>
      <div class="chips">
        <span class="chip">Technical Plan</span>
        <span class="chip">{html.escape(plan_status)}</span>
      </div>
    </header>

    <section class="meta-grid">
      {summary_html}
    </section>

    {detail_block_html}

    <section class="block">
      <h2>Traceability</h2>
      <div class="links">
        {workstream_traceability_html}
      </div>
      {traceability_block_html}
    </section>

    {section_html}
  </main>
  <script src="https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"></script>
  <script>
    (function() {{
      if (!window.mermaid || !document.querySelector(".mermaid")) return;
      window.mermaid.initialize({{
        startOnLoad: false,
        securityLevel: "strict",
        theme: "neutral"
      }});
      window.mermaid.run({{ querySelector: ".mermaid" }});
    }})();
  </script>
</body>
</html>
"""
