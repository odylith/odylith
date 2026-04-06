"""Shared dashboard UI CSS primitives for governance surfaces.

This module centralizes reusable visual contracts that must remain consistent
across generated dashboard tools (for example Radar, Registry, and Shell).
"""

from __future__ import annotations

BODY_FONT_FAMILY = '"Avenir Next", "Segoe UI", "Helvetica Neue", sans-serif'
MONO_FONT_FAMILY = 'ui-monospace, Menlo, Monaco, Consolas, "Liberation Mono", monospace'


def _selector_list(selector: str) -> tuple[str, ...]:
    """Normalize a potentially comma-separated selector string.

    Interactive helpers append pseudo states, so each selector member must be
    expanded independently. Without normalization, a selector list such as
    `.pill, .chip-link` would emit malformed rules that apply hover/focus state
    to the unsuffixed selectors permanently.
    """

    return tuple(part.strip() for part in selector.split(",") if part.strip())


def _joined_selector_list(selector: str) -> str:
    """Return a canonical comma-separated selector list string."""

    return ", ".join(_selector_list(selector))


def _selector_state_list(selector: str, suffix: str) -> str:
    """Return a selector list with a pseudo/class suffix applied per member."""

    return ", ".join(f"{part}{suffix}" for part in _selector_list(selector))


def page_body_typography_css(
    *,
    selector: str,
    color: str = "var(--ink, #0b1324)",
    font_family: str = BODY_FONT_FAMILY,
    size_px: int = 14,
    line_height: float = 1.5,
) -> str:
    """Return the canonical page/body typography contract for dashboard surfaces."""

    return f"""
{selector} {{
  font-family: {font_family};
  font-size: {int(size_px)}px;
  line-height: {float(line_height):g};
  color: {color};
}}
""".strip()


def supporting_copy_typography_css(
    *,
    selector: str,
    color: str = "var(--ink-muted, #64748b)",
    size_px: int = 13,
    line_height: float = 1.45,
    weight: int = 400,
    letter_spacing_em: float = 0.0,
) -> str:
    """Return shared subtitle/helper-copy typography for dashboard surfaces."""

    return f"""
{selector} {{
  color: {color};
  font-size: {int(size_px)}px;
  line-height: {float(line_height):g};
  font-weight: {int(weight)};
  letter-spacing: {float(letter_spacing_em):g}em;
}}
""".strip()


def caption_typography_css(
    *,
    selector: str,
    color: str = "var(--ink-muted, #64748b)",
    size_px: int = 12,
    line_height: float = 1.35,
    weight: int = 400,
    letter_spacing_em: float = 0.0,
) -> str:
    """Return shared caption/meta typography for small dashboard copy."""

    return f"""
{selector} {{
  color: {color};
  font-size: {int(size_px)}px;
  line-height: {float(line_height):g};
  font-weight: {int(weight)};
  letter-spacing: {float(letter_spacing_em):g}em;
}}
""".strip()


def chart_axis_typography_css(
    *,
    selector: str,
    fill: str = "#64748b",
    size_px: int = 11,
    font_family: str = BODY_FONT_FAMILY,
    weight: int = 400,
    letter_spacing_em: float = 0.0,
) -> str:
    """Return shared SVG/chart-axis typography for dashboard visualizations."""

    return f"""
{selector} {{
  fill: {fill};
  font-family: {font_family};
  font-size: {int(size_px)}px;
  font-weight: {int(weight)};
  letter-spacing: {float(letter_spacing_em):g}em;
}}
""".strip()


def section_heading_css(
    *,
    selector: str,
    color: str = "#334155",
    size_px: int = 12,
    line_height: float = 1.2,
    letter_spacing_em: float = 0.08,
    weight: int = 700,
    text_transform: str = "uppercase",
    margin: str = "0",
) -> str:
    """Return shared section-heading typography for dashboard modules."""

    return f"""
{selector} {{
  margin: {margin};
  color: {color};
  font-size: {int(size_px)}px;
  line-height: {float(line_height):g};
  letter-spacing: {float(letter_spacing_em):g}em;
  font-weight: {int(weight)};
  text-transform: {text_transform};
}}
""".strip()


def split_detail_workspace_css(
    *,
    selector: str,
    left_min_px: int = 330,
    left_max_px: int = 420,
    right_track: str = "minmax(0, 1fr)",
    gap_px: int = 12,
    align_items: str = "start",
) -> str:
    """Return the canonical two-pane dashboard workspace layout contract.

    Radar's backlog list + detail workspace is the baseline layout for the
    governance dashboards that use a persistent left selector/list rail with a
    larger detail pane on the right. Sibling surfaces such as Registry and
    Shell should consume this helper instead of carrying its own slightly
    different left-pane widths.
    """

    return f"""
{selector} {{
  display: grid;
  grid-template-columns: minmax({int(left_min_px)}px, {int(left_max_px)}px) {right_track};
  gap: {int(gap_px)}px;
  align-items: {align_items};
}}
""".strip()


def auxiliary_heading_css(
    *,
    selector: str,
    color: str = "#475569",
    size_px: int = 11,
    line_height: float = 1.2,
    letter_spacing_em: float = 0.07,
    weight: int = 700,
    margin: str = "0",
    text_transform: str = "uppercase",
) -> str:
    """Return the shared smaller uppercase heading tier for auxiliary labels.

    This tier sits below the primary section-heading rhythm and is intended for
    contextual subheads such as traceability bucket labels, artifact labels,
    timeline utility headings, and other quiet structural markers.
    """

    return section_heading_css(
        selector=selector,
        color=color,
        size_px=size_px,
        line_height=line_height,
        letter_spacing_em=letter_spacing_em,
        weight=weight,
        margin=margin,
        text_transform=text_transform,
    )


def label_badge_typography_css(
    *,
    selector: str,
    color: str = "#334155",
    size_px: int = 11,
    line_height: float = 1.0,
    letter_spacing_em: float = 0.01,
    weight: int = 700,
    text_transform: str = "none",
) -> str:
    """Return shared non-interactive label/tag typography for dashboard surfaces."""

    return f"""
{selector} {{
  color: {color};
  font-size: {int(size_px)}px;
  line-height: {float(line_height):g};
  letter-spacing: {float(letter_spacing_em):g}em;
  font-weight: {int(weight)};
  text-transform: {text_transform};
}}
""".strip()


def label_surface_css(
    *,
    selector: str,
    padding: str = "4px 10px",
    background: str = "#f6faf7",
    border_color: str = "#d7e2dc",
    color: str = "#334155",
    border_radius_px: int = 4,
    border_width_px: int = 1,
    min_height_px: int = 0,
    text_decoration: str = "none",
    cursor: str = "default",
) -> str:
    """Return the shared passive dashboard label surface contract.

    Passive dashboard metadata should render as one coherent label family:
    compact, bordered, softly toned, and clearly distinct from rounded
    interactive buttons/chips. Renderers should route semantic metadata through
    this helper instead of copying local zero-radius/no-border label shells.
    """

    return f"""
{selector} {{
  --label-bg: {background};
  --label-border: {border_color};
  --label-text: {color};
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: {int(border_width_px)}px solid var(--label-border);
  border-radius: {int(border_radius_px)}px;
  min-height: {int(min_height_px)}px;
  padding: {padding};
  color: var(--label-text);
  background: var(--label-bg);
  box-shadow: none;
  text-decoration: {text_decoration};
  white-space: nowrap;
  vertical-align: middle;
  cursor: {cursor};
}}
""".strip()


def label_chip_surface_css(
    *,
    selector: str,
    min_height_px: int = 22,
    padding: str = "0 8px",
    radius_px: int = 999,
    border_width_px: int = 1,
    border_color: str = "#c9dbf3",
    background: str = "#f4f8fd",
    color: str = "#24466f",
) -> str:
    """Return shared passive metadata-chip surface CSS for dashboard surfaces."""

    return f"""
{selector} {{
  --label-bg: {background};
  --label-border: {border_color};
  --label-text: {color};
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: {int(min_height_px)}px;
  padding: {padding};
  border-radius: {int(radius_px)}px;
  border: {int(border_width_px)}px solid var(--label-border);
  background: var(--label-bg);
  color: var(--label-text);
  box-shadow: none;
  white-space: nowrap;
  vertical-align: middle;
  cursor: default;
  pointer-events: none;
  user-select: none;
}}
""".strip()


def action_chip_surface_css(
    *,
    selector: str,
    min_height_px: int = 24,
    padding: str = "0 11px",
    radius_px: int = 999,
    border_color: str = "#b9c7db",
    background: str = "#f3f6fb",
    color: str = "#334155",
    hover_border_color: str = "#9aaec9",
    hover_background: str = "#e8eef7",
    hover_color: str = "#1e293b",
    focus_outline: str = "#bfdbfe",
) -> str:
    """Return shared interactive chip/link surface CSS for dashboard actions."""

    base_selector = _joined_selector_list(selector)
    hover_selector = _selector_state_list(selector, ":hover")
    focus_selector = _selector_state_list(selector, ":focus-visible")

    return f"""
{base_selector} {{
  --chip-link-border: {border_color};
  --chip-link-bg: {background};
  --chip-link-text: {color};
  --chip-link-border-hover: {hover_border_color};
  --chip-link-bg-hover: {hover_background};
  --chip-link-text-hover: {hover_color};
  appearance: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: {int(min_height_px)}px;
  padding: {padding};
  border-radius: {int(radius_px)}px;
  border: 1px solid var(--chip-link-border);
  background: var(--chip-link-bg);
  color: var(--chip-link-text);
  box-shadow: none;
  white-space: nowrap;
  vertical-align: middle;
  cursor: pointer;
  text-decoration: none;
  transition: border-color 120ms ease, background 120ms ease, color 120ms ease;
}}

{hover_selector},
{focus_selector} {{
  border-color: var(--chip-link-border-hover);
  background: var(--chip-link-bg-hover);
  color: var(--chip-link-text-hover);
}}

{focus_selector} {{
  outline: 2px solid {focus_outline};
  outline-offset: 1px;
}}
""".strip()


def detail_action_chip_css(
    *,
    selector: str,
    color: str = "var(--chip-link-text)",
    min_height_px: int = 0,
    padding: str = "4px 12px",
    radius_px: int = 999,
    border_color: str = "#b9c7db",
    background: str = "#f3f6fb",
    hover_border_color: str = "#9aaec9",
    hover_background: str = "#e8eef7",
    hover_color: str = "#1e293b",
    focus_outline: str = "#bfdbfe",
    size_px: int = 11,
    line_height: float = 1.0,
    letter_spacing_em: float = 0.01,
    weight: int = 700,
) -> str:
    """Return the shared small interactive chip contract for detail-pane links.

    Radar's detail links are the reference visual treatment for dense governance
    detail panes. Registry, Shell, and sibling surfaces should reuse this
    helper for inline linked chips instead of carrying local copies of the same
    height, padding, and typography contract.
    """

    return "\n\n".join(
        (
            action_chip_surface_css(
                selector=selector,
                min_height_px=min_height_px,
                padding=padding,
                radius_px=radius_px,
                border_color=border_color,
                background=background,
                color=color,
                hover_border_color=hover_border_color,
                hover_background=hover_background,
                hover_color=hover_color,
                focus_outline=focus_outline,
            ),
            button_typography_css(
                selector=selector,
                color=color,
                size_px=size_px,
                line_height=line_height,
                letter_spacing_em=letter_spacing_em,
                weight=weight,
            ),
        )
    )


def detail_label_chip_css(
    *,
    selector: str,
    color: str = "var(--label-text)",
    min_height_px: int = 0,
    padding: str = "4px 10px",
    radius_px: int = 4,
    border_width_px: int = 1,
    border_color: str = "#d7e2dc",
    background: str = "#f6faf7",
    size_px: int = 11,
    line_height: float = 1.0,
    letter_spacing_em: float = 0.01,
    weight: int = 700,
) -> str:
    """Return the shared compact passive-chip contract paired with detail actions.

    Some dashboard surfaces need passive chips that share the same dense size
    and type rhythm as the Radar relations control without becoming interactive
    affordances. Execution-wave posture chips are the main current example.
    """

    return "\n\n".join(
        (
            label_surface_css(
                selector=selector,
                padding=padding,
                background=background,
                border_color=border_color,
                color=color,
                border_radius_px=radius_px,
                border_width_px=border_width_px,
                min_height_px=min_height_px,
            ),
            button_typography_css(
                selector=selector,
                color=color,
                size_px=size_px,
                line_height=line_height,
                letter_spacing_em=letter_spacing_em,
                weight=weight,
            ),
        )
    )


def detail_toggle_chip_css(
    *,
    selector: str,
    active_selector: str,
    color: str = "var(--chip-link-text)",
    min_height_px: int = 0,
    padding: str = "4px 12px",
    radius_px: int = 999,
    border_color: str = "#b9c7db",
    background: str = "#f3f6fb",
    hover_border_color: str = "#9aaec9",
    hover_background: str = "#e8eef7",
    hover_color: str = "#1e293b",
    active_border_color: str = "#4f86db",
    active_background: str = "#d7e6ff",
    active_color: str = "#173f83",
    active_hover_border_color: str | None = None,
    active_hover_background: str | None = None,
    active_hover_color: str | None = None,
    active_box_shadow: str = "none",
    focus_outline: str = "#bfdbfe",
    size_px: int = 11,
    line_height: float = 1.0,
    letter_spacing_em: float = 0.01,
    weight: int = 700,
) -> str:
    """Return the shared compact toggle-button contract for selected-state controls.

    Some dashboard controls use the same compact geometry and typography as the
    Radar relations chip, but also need a durable selected state. Examples
    include tooling-shell surface tabs and Radar chart-mode toggles. This
    helper keeps those controls on the same button family instead of allowing
    renderer-local active-state shells to drift.
    """

    resolved_active_hover_border = active_hover_border_color or active_border_color
    resolved_active_hover_background = active_hover_background or active_background
    resolved_active_hover_color = active_hover_color or active_color
    active_box_shadow_rule = f"\n  box-shadow: {active_box_shadow};" if active_box_shadow else ""
    normalized_active_selector = _joined_selector_list(active_selector)
    return "\n\n".join(
        (
            detail_action_chip_css(
                selector=selector,
                color=color,
                min_height_px=min_height_px,
                padding=padding,
                radius_px=radius_px,
                border_color=border_color,
                background=background,
                hover_border_color=hover_border_color,
                hover_background=hover_background,
                hover_color=hover_color,
                focus_outline=focus_outline,
                size_px=size_px,
                line_height=line_height,
                letter_spacing_em=letter_spacing_em,
                weight=weight,
            ),
            f"""
{normalized_active_selector} {{
  --chip-link-border: {active_border_color};
  --chip-link-bg: {active_background};
  --chip-link-text: {active_color};
  --chip-link-border-hover: {resolved_active_hover_border};
  --chip-link-bg-hover: {resolved_active_hover_background};
  --chip-link-text-hover: {resolved_active_hover_color};{active_box_shadow_rule}
}}
""".strip(),
        )
    )


def shell_tab_surface_css(
    *,
    selector: str,
    active_selector: str,
    min_height_px: int = 32,
    padding: str = "7px 14px 8px",
    radius_css: str = "14px 14px 0 0",
    border_color: str = "var(--chip-line, #9ec0f6)",
    background: str = "var(--chip-bg, #edf4ff)",
    color: str = "#2b4a74",
    hover_border_color: str = "#83ace8",
    hover_background: str = "#e7f0ff",
    hover_color: str = "#244d89",
    active_border_color: str = "var(--chip-active-line, #4f86db)",
    active_background: str = "var(--chip-active-bg, #d7e6ff)",
    active_color: str = "var(--chip-active-ink, #173f83)",
    focus_outline: str = "#bfdbfe",
    size_px: int = 11,
    line_height: float = 1.0,
    letter_spacing_em: float = 0.01,
    weight: int = 700,
) -> str:
    """Return the shared tooling-shell navigation tab surface contract.

    The shell tabs are a specialized nav treatment built on the same chip
    language as the rest of the governance dashboards, but they need a stronger
    active state than passive detail chips so the selected surface is obvious.
    Centralize that contrast here instead of allowing renderer-local drift.
    """

    base_selector = _joined_selector_list(selector)
    hover_selector = _selector_state_list(selector, ":hover")
    focus_selector = _selector_state_list(selector, ":focus-visible")
    normalized_active_selector = _joined_selector_list(active_selector)

    surface_css = f"""
{base_selector} {{
  appearance: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: {int(min_height_px)}px;
  padding: {padding};
  border-radius: {radius_css};
  border: 1px solid {border_color};
  border-bottom: 0;
  background: {background};
  color: {color};
  box-shadow: none;
  white-space: nowrap;
  cursor: pointer;
  text-decoration: none;
  margin-bottom: -1px;
  position: relative;
  z-index: 1;
  transition: border-color 120ms ease, background 120ms ease, color 120ms ease;
}}

{hover_selector},
{focus_selector} {{
  border-color: {hover_border_color};
  background: {hover_background};
  color: {hover_color};
}}

{focus_selector} {{
  outline: 2px solid {focus_outline};
  outline-offset: 1px;
}}

{normalized_active_selector} {{
  border-color: {active_border_color};
  background: {active_background};
  color: {active_color};
  z-index: 2;
}}
""".strip()
    typography_css = button_typography_css(
        selector=base_selector,
        color="currentColor",
        size_px=size_px,
        line_height=line_height,
        letter_spacing_em=letter_spacing_em,
        weight=weight,
    )
    return "\n\n".join((surface_css, typography_css))


def details_disclosure_caret_css(
    *,
    details_selector: str,
    label_selector: str,
    color: str = "#64748b",
    size_px: int = 11,
    gap_px: int = 6,
    transition_ms: int = 160,
) -> str:
    """Return the shared triangle disclosure affordance for detail summaries.

    Governance dashboards should use one disclosure pattern for expandable
    detail regions: a quiet triangle/caret on the summary label, rotating open
    when the surrounding ``<details>`` element is expanded. This replaces
    renderer-local button copy such as ``Show``/``Expand``/``Collapse``.
    """

    return f"""
{details_selector} > summary::-webkit-details-marker {{
  display: none;
}}

{label_selector} {{
  display: inline-flex;
  align-items: center;
  gap: {int(gap_px)}px;
}}

{label_selector}::before {{
  content: "▸";
  flex: none;
  color: {color};
  font-size: {int(size_px)}px;
  line-height: 1;
  transition: transform {int(transition_ms)}ms ease;
}}

{details_selector}[open] {label_selector}::before {{
  transform: rotate(90deg);
}}
""".strip()


def subtle_label_tone_css(
    *,
    selector: str,
    background: str,
    border_color: str,
    color: str,
) -> str:
    """Return shared muted surface-tone CSS for non-interactive dashboard labels.

    Governance dashboards use many small labels and chips. This helper keeps
    those affordances visually quiet while still letting renderers separate
    semantics via distinct tone families.
    """

    return f"""
{selector} {{
  --label-bg: {background};
  --label-border: {border_color};
  --label-text: {color};
}}
""".strip()


def subtle_link_label_tone_css(
    *,
    selector: str,
    border_color: str,
    background: str,
    color: str,
    hover_border_color: str,
    hover_background: str,
    hover_color: str,
) -> str:
    """Return shared muted variable-tones for interactive chip/link labels."""

    return f"""
{selector} {{
  --chip-link-border: {border_color};
  --chip-link-bg: {background};
  --chip-link-text: {color};
  --chip-link-border-hover: {hover_border_color};
  --chip-link-bg-hover: {hover_background};
  --chip-link-text-hover: {hover_color};
}}
""".strip()


def subtle_labeled_surface_tone_css(
    *,
    selector: str,
    background: str,
    border_color: str,
    color: str,
) -> str:
    """Return shared muted tone CSS for labeled dashboard surfaces and buckets."""

    return f"""
{selector} {{
  background: {background};
  border-color: {border_color};
  color: {color};
}}
""".strip()


def button_typography_css(
    *,
    selector: str,
    font_family: str = "inherit",
    color: str = "inherit",
    size_px: int = 12,
    line_height: float = 1.0,
    letter_spacing_em: float = 0.0,
    weight: int = 700,
    text_transform: str = "none",
) -> str:
    """Return shared interactive-button typography for dashboard surfaces."""

    return f"""
{selector} {{
  font-family: {font_family};
  color: {color};
  font-size: {int(size_px)}px;
  line-height: {float(line_height):g};
  letter-spacing: {float(letter_spacing_em):g}em;
  font-weight: {int(weight)};
  text-transform: {text_transform};
}}
""".strip()


def value_emphasis_typography_css(
    *,
    selector: str,
    color: str = "var(--ink, #0f172a)",
    size_px: int = 14,
    line_height: float = 1.35,
    weight: int = 700,
    letter_spacing_em: float = 0.0,
    white_space: str | None = None,
    overflow_wrap: str | None = None,
    word_break: str | None = None,
    text_wrap: str | None = None,
    overflow: str | None = None,
    text_overflow: str | None = None,
) -> str:
    """Return shared emphasized-value typography for compact data readouts."""

    optional_rules: list[str] = []
    if white_space is not None:
        optional_rules.append(f"  white-space: {white_space};")
    if overflow_wrap is not None:
        optional_rules.append(f"  overflow-wrap: {overflow_wrap};")
    if word_break is not None:
        optional_rules.append(f"  word-break: {word_break};")
    if text_wrap is not None:
        optional_rules.append(f"  text-wrap: {text_wrap};")
    if overflow is not None:
        optional_rules.append(f"  overflow: {overflow};")
    if text_overflow is not None:
        optional_rules.append(f"  text-overflow: {text_overflow};")
    optional_block = ("\n" + "\n".join(optional_rules)) if optional_rules else ""

    return f"""
{selector} {{
  color: {color};
  font-size: {int(size_px)}px;
  line-height: {float(line_height):g};
  font-weight: {int(weight)};
  letter-spacing: {float(letter_spacing_em):g}em;
{optional_block}
}}
""".strip()


def card_title_typography_css(
    *,
    selector: str,
    color: str = "#0b1324",
    size_px: int = 14,
    line_height: float = 1.3,
    letter_spacing_em: float = -0.01,
    weight: int = 700,
    text_transform: str = "none",
    margin: str = "0",
) -> str:
    """Return shared mid-level title typography for cards, rows, and details."""

    return f"""
{selector} {{
  margin: {margin};
  color: {color};
  font-size: {int(size_px)}px;
  line-height: {float(line_height):g};
  letter-spacing: {float(letter_spacing_em):g}em;
  font-weight: {int(weight)};
  text-transform: {text_transform};
}}
""".strip()


def header_typography_css(
    *,
    kicker_selector: str,
    title_selector: str,
    subtitle_selector: str,
    subtitle_max_width: str = "100%",
    kicker_color: str = "#0b7f77",
    kicker_size_px: int = 12,
    kicker_weight: int = 700,
    kicker_letter_spacing_em: float = 0.09,
    kicker_margin: str = "0 0 6px",
    title_margin: str = "0 0 8px",
    title_size_px: int = 31,
    title_line_height: float = 1.08,
    title_letter_spacing_em: float = -0.01,
    title_weight: int = 700,
    subtitle_margin: str = "0",
    subtitle_color: str = "var(--ink-soft, #334155)",
    subtitle_size_px: int = 14,
    subtitle_line_height: float = 1.5,
    subtitle_weight: int = 400,
    desktop_single_line_subtitle: bool = True,
    mobile_breakpoint_px: int | None = None,
    mobile_title_size_px: int | None = None,
    mobile_subtitle_size_px: int | None = None,
) -> str:
    """Return Radar-canonical header typography CSS for a dashboard surface."""

    responsive_rules: list[str] = []
    if mobile_title_size_px is not None:
        responsive_rules.append(
            f"""  {title_selector} {{
    font-size: {int(mobile_title_size_px)}px;
  }}"""
        )
    if mobile_subtitle_size_px is not None:
        responsive_rules.append(
            f"""  {subtitle_selector} {{
    font-size: {int(mobile_subtitle_size_px)}px;
  }}"""
        )
    if desktop_single_line_subtitle:
        responsive_rules.append(
            f"""  {subtitle_selector} {{
    white-space: normal;
  }}"""
        )
    responsive_block = ""
    if mobile_breakpoint_px is not None and responsive_rules:
        responsive_block = "\n\n@media (max-width: " + str(int(mobile_breakpoint_px)) + "px) {\n"
        responsive_block += "\n".join(responsive_rules)
        responsive_block += "\n}"

    return f"""
{kicker_selector} {{
  text-transform: uppercase;
  letter-spacing: {float(kicker_letter_spacing_em):g}em;
  color: {kicker_color};
  font-size: {int(kicker_size_px)}px;
  font-weight: {int(kicker_weight)};
  margin: {kicker_margin};
}}

{title_selector} {{
  margin: {title_margin};
  font-size: {int(title_size_px)}px;
  line-height: {float(title_line_height):g};
  letter-spacing: {float(title_letter_spacing_em):g}em;
  font-weight: {int(title_weight)};
}}

{subtitle_selector} {{
  margin: {subtitle_margin};
  color: {subtitle_color};
  max-width: {subtitle_max_width};
  line-height: {float(subtitle_line_height):g};
  font-size: {int(subtitle_size_px)}px;
  font-weight: {int(subtitle_weight)};
  white-space: {"nowrap" if desktop_single_line_subtitle else "normal"};
}}{responsive_block}
""".strip()


def hero_panel_css(
    *,
    container_selector: str,
    margin_bottom: str = "0",
    padding: str = "18px 18px 14px",
    radius_px: int = 18,
    gap_px: int = 10,
    shadow: str = "0 14px 30px rgba(15, 23, 42, 0.08)",
) -> str:
    """Return Radar-canonical hero panel CSS for a dashboard surface."""

    return f"""
{container_selector} {{
  background: linear-gradient(145deg, #ffffff, #ecfeff 58%, #eff6ff);
  border: 1px solid var(--line);
  border-radius: {int(radius_px)}px;
  padding: {padding};
  box-shadow: {shadow};
  display: grid;
  gap: {int(gap_px)}px;
  margin-bottom: {margin_bottom};
}}
""".strip()


def sticky_filter_shell_css(
    *,
    shell_selector: str,
    top_px: int = 10,
    z_index: int = 24,
    gap_px: int = 8,
) -> str:
    """Return shared sticky filter wrapper CSS for dashboard surfaces."""

    return f"""
{shell_selector} {{
  display: grid;
  gap: {int(gap_px)}px;
  position: sticky;
  top: {int(top_px)}px;
  z-index: {int(z_index)};
}}
""".strip()


def sticky_filter_bar_css(
    *,
    container_selector: str,
    columns: str,
    field_selector: str,
    focus_selector: str,
    top_px: int = 10,
) -> str:
    """Return Radar-canonical sticky filter bar CSS for a dashboard surface."""

    return f"""
{container_selector} {{
  position: sticky;
  top: {int(top_px)}px;
  z-index: 20;
  display: grid;
  grid-template-columns: {columns};
  gap: 8px;
  padding: 10px;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid #bfdbfe;
  border-radius: 14px;
  backdrop-filter: blur(8px);
  margin-bottom: 12px;
  box-shadow: 0 4px 14px rgba(15, 23, 42, 0.07);
}}

{field_selector} {{
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #cbd5e1;
  border-radius: 10px;
  background: #fff;
  color: var(--ink, #0b1324);
  font-size: 14px;
}}

{focus_selector} {{
  outline: 2px solid #bfdbfe;
  border-color: var(--focus, #2563eb);
}}
""".strip()


def control_label_css(
    *,
    selector: str,
    color: str = "#49678b",
    size_px: int = 11,
    letter_spacing_em: float = 0.04,
    line_height: float = 1.0,
) -> str:
    """Return shared control-label typography CSS for dashboard surfaces."""

    return f"""
{selector} {{
  font-size: {int(size_px)}px;
  text-transform: uppercase;
  letter-spacing: {float(letter_spacing_em):g}em;
  color: {color};
  font-weight: 700;
  line-height: {float(line_height):g};
}}
""".strip()


def display_title_typography_css(
    *,
    title_selector: str,
    subtitle_selector: str | None = None,
    title_font_family: str = BODY_FONT_FAMILY,
    title_size: str = "clamp(20px, 2.2vw, 26px)",
    title_line_height: float = 1.15,
    title_letter_spacing_em: float = -0.02,
    title_weight: int = 700,
    title_color: str = "#0b1324",
    subtitle_margin: str = "0",
    subtitle_size_px: int = 13,
    subtitle_line_height: float = 1.45,
    subtitle_color: str = "#516a83",
    subtitle_max_width: str | None = None,
) -> str:
    """Return shared display-title typography for hero-style governance surfaces.

    Atlas diagram detail pages and the parent tooling shell both use this
    larger display-title treatment. Keeping it centralized prevents the shell
    from drifting into a utility-heading style while Atlas uses a proper
    presentation title.
    """

    subtitle_block = ""
    if subtitle_selector:
        max_width_rule = f"\n  max-width: {subtitle_max_width};" if subtitle_max_width else ""
        subtitle_block = f"""

{subtitle_selector} {{
  margin: {subtitle_margin};
  color: {subtitle_color};{max_width_rule}
  font-size: {int(subtitle_size_px)}px;
  line-height: {float(subtitle_line_height):g};
}}"""

    return f"""
{title_selector} {{
  margin: 0;
  font-family: {title_font_family};
  font-size: {title_size};
  line-height: {float(title_line_height):g};
  color: {title_color};
  letter-spacing: {float(title_letter_spacing_em):g}em;
  font-weight: {int(title_weight)};
}}{subtitle_block}
""".strip()


def content_copy_css(
    *,
    selectors: tuple[str, ...],
    size_px: int = 15,
    line_height: float = 1.55,
    color: str = "#27445e",
) -> str:
    """Return the shared Radar-led readable body-copy CSS for dashboard surfaces.

    This primitive is for normal descriptive text only: narrative paragraphs,
    section bodies, inline detail explanations, and evidence summaries. It is
    intentionally not for headings, labels, pills, or subtitles.
    """

    joined = ", ".join(token.strip() for token in selectors if str(token).strip())
    if not joined:
        return ""
    return f"""
{joined} {{
  font-size: {int(size_px)}px;
  line-height: {float(line_height):g};
  color: {color};
}}
""".strip()


def inline_label_value_copy_css(
    *,
    row_selectors: tuple[str, ...],
    label_selectors: tuple[str, ...],
    size_px: int = 15,
    line_height: float = 1.55,
    color: str = "#27445e",
    label_color: str = "#22496f",
    label_weight: int = 700,
) -> str:
    """Return shared typography for inline explanatory label/value rows.

    This keeps rows such as "What it is: ...", "Why tracked: ...", and similar
    inline operational facts on the readable body scale while giving the label
    only modest emphasis. The goal is to keep the explanation louder than the
    prefix or count.
    """

    joined_rows = ", ".join(token.strip() for token in row_selectors if str(token).strip())
    joined_labels = ", ".join(token.strip() for token in label_selectors if str(token).strip())
    blocks: list[str] = []
    if joined_rows:
        blocks.append(
            f"""
{joined_rows} {{
  font-size: {int(size_px)}px;
  line-height: {float(line_height):g};
  color: {color};
  font-weight: 400;
}}
""".strip()
        )
    if joined_labels:
        blocks.append(
            f"""
{joined_labels} {{
  font-size: inherit;
  line-height: inherit;
  color: {label_color};
  font-weight: {int(label_weight)};
}}
""".strip()
        )
    return "\n\n".join(blocks)


def detail_disclosure_title_css(
    *,
    selector: str,
    color: str = "#22496f",
    size_px: int = 15,
    line_height: float = 1.55,
    weight: int = 700,
    letter_spacing_em: float = 0.0,
    margin: str = "0",
) -> str:
    """Return the shared title tier for expandable detail summaries.

    Dense detail panes should not mix card-title, utility-heading, and
    button-label scales for disclosure labels. This tier aligns stand-alone
    disclosure headings with the readable inline label/value rhythm already
    used by rows like ``What it is`` and ``Why tracked``.
    """

    return f"""
{selector} {{
  margin: {margin};
  color: {color};
  font-size: {int(size_px)}px;
  line-height: {float(line_height):g};
  letter-spacing: {float(letter_spacing_em):g}em;
  font-weight: {int(weight)};
}}
""".strip()


def compact_label_value_typography_css(
    *,
    label_selector: str,
    value_selector: str,
    label_color: str = "#5c728b",
    label_size_px: int = 11,
    label_line_height: float = 1.2,
    label_letter_spacing_em: float = 0.04,
    label_weight: int = 700,
    label_text_transform: str = "uppercase",
    value_color: str = "#16324f",
    value_size_px: int = 13,
    value_line_height: float = 1.3,
    value_letter_spacing_em: float = 0.0,
    value_weight: int = 700,
) -> str:
    """Return shared compact label/value typography for summary pills and mini-stats.

    Shell summary pills and similar compact dashboard readouts should reuse
    one shared contract instead of re-assembling local label/value scales.
    """

    return f"""
{label_selector} {{
  margin: 0;
  color: {label_color};
  font-size: {int(label_size_px)}px;
  line-height: {float(label_line_height):g};
  letter-spacing: {float(label_letter_spacing_em):g}em;
  font-weight: {int(label_weight)};
  text-transform: {label_text_transform};
}}

{value_selector} {{
  margin: 0;
  color: {value_color};
  font-size: {int(value_size_px)}px;
  line-height: {float(value_line_height):g};
  letter-spacing: {float(value_letter_spacing_em):g}em;
  font-weight: {int(value_weight)};
}}
""".strip()


def code_typography_css(
    *,
    selector: str,
    color: str = "#e2e8f0",
    size_px: int = 12,
    line_height: float = 1.5,
    weight: int = 400,
    font_family: str = MONO_FONT_FAMILY,
    letter_spacing_em: float = 0.0,
) -> str:
    """Return shared code/monospace content typography for dashboard surfaces."""

    return f"""
{selector} {{
  color: {color};
  font-family: {font_family};
  font-size: {int(size_px)}px;
  line-height: {float(line_height):g};
  font-weight: {int(weight)};
  letter-spacing: {float(letter_spacing_em):g}em;
}}
""".strip()


def kpi_card_surface_css(
    *,
    card_selector: str,
    padding: str = "10px 12px",
) -> str:
    """Return shared KPI card surface CSS for dashboard surfaces."""

    return f"""
{card_selector} {{
  border: 1px solid #dbeafe;
  border-radius: 12px;
  background: #ffffff;
  padding: {padding};
  min-height: 0;
  display: grid;
  grid-template-rows: 2.35em auto;
  align-content: start;
}}
""".strip()


def kpi_grid_layout_css(
    *,
    container_selector: str,
    min_col_width_px: int = 150,
    gap_px: int = 10,
    margin_top: str = "12px",
) -> str:
    """Return shared KPI/stats grid layout CSS for dashboard hero shells."""

    return f"""
{container_selector} {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax({int(min_col_width_px)}px, 1fr));
  gap: {int(gap_px)}px;
  margin-top: {margin_top};
}}
""".strip()


def panel_surface_css(
    *,
    selector: str,
    padding: str = "12px 14px",
    radius_px: int = 14,
    gap_px: int = 8,
    border_color: str = "#dbeafe",
    background: str = "linear-gradient(180deg, #ffffff, #fbfdff)",
    shadow: str = "0 6px 18px rgba(15, 23, 42, 0.04)",
) -> str:
    """Return shared narrative/detail panel surface CSS for dashboard sections."""

    return f"""
{selector} {{
  border: 1px solid {border_color};
  border-radius: {int(radius_px)}px;
  background: {background};
  padding: {padding};
  box-shadow: {shadow};
  display: grid;
  gap: {int(gap_px)}px;
  align-content: start;
}}
""".strip()


def intelligence_card_surface_css(
    *,
    selector: str,
    padding: str = "10px 11px",
    radius_px: int = 12,
    gap_px: int = 6,
    border_color: str = "rgba(3, 105, 161, 0.16)",
    background: str = "rgba(255, 255, 255, 0.96)",
    shadow: str = "none",
    accent_width_px: int = 4,
    accent_color: str = "rgba(37, 99, 235, 0.5)",
) -> str:
    """Return Atlas-canonical delivery-intelligence card surface CSS.

    Atlas is the canonical visual contract for intelligence cards. Other
    dashboard surfaces should reuse this primitive rather than reintroducing
    one-off card treatments, fonts, or border systems.
    """

    return f"""
{selector} {{
  border: 1px solid {border_color};
  border-left: {int(accent_width_px)}px solid {accent_color};
  border-radius: {int(radius_px)}px;
  background: {background};
  padding: {padding};
  box-shadow: {shadow};
  display: grid;
  gap: {int(gap_px)}px;
  align-content: start;
  min-width: 0;
}}
""".strip()


def intelligence_card_variant_css(
    *,
    selector: str,
    accent_color: str,
) -> str:
    """Return Atlas-canonical accent override CSS for an intelligence card."""

    return f"""
{selector} {{
  border-left-color: {accent_color};
}}
""".strip()


def intelligence_card_heading_css(
    *,
    selector: str,
    color: str = "#1f4868",
    size_px: int = 12,
    letter_spacing_em: float = 0.06,
    margin: str = "0 0 6px 0",
    line_height: float = 1.2,
    weight: int = 700,
) -> str:
    """Return Atlas-canonical intelligence card heading typography."""

    return f"""
{selector} {{
  margin: {margin};
  font-size: {int(size_px)}px;
  text-transform: uppercase;
  letter-spacing: {float(letter_spacing_em):g}em;
  color: {color};
  line-height: {float(line_height):g};
  font-weight: {int(weight)};
}}
""".strip()


def intelligence_card_body_css(
    *,
    selector: str,
    color: str = "#27445e",
    size_px: int = 15,
    line_height: float = 1.55,
    weight: int = 400,
    letter_spacing_em: float = 0.0,
    margin: str = "0",
) -> str:
    """Return Atlas-canonical intelligence card body typography."""

    return f"""
{selector} {{
  margin: {margin};
  font-size: {int(size_px)}px;
  line-height: {float(line_height):g};
  color: {color};
  font-weight: {int(weight)};
  letter-spacing: {float(letter_spacing_em):g}em;
}}
""".strip()


def intelligence_meta_pill_css(
    *,
    selector: str,
    background: str = "#edf4ff",
    border_color: str = "#dbeafe",
    color: str = "#35567e",
    size_px: int = 11,
    weight: int = 700,
    line_height: float = 1.1,
    letter_spacing_em: float = 0.04,
    padding: str = "4px 9px",
    radius_px: int = 999,
) -> str:
    """Return shared Radar-led meta-pill styling for intelligence surfaces."""

    return f"""
{selector} {{
  display: inline-flex;
  align-items: center;
  width: fit-content;
  padding: {padding};
  border-radius: {int(radius_px)}px;
  background: {background};
  color: {color};
  border: 1px solid {border_color};
  font-size: {int(size_px)}px;
  font-weight: {int(weight)};
  line-height: {float(line_height):g};
  text-transform: uppercase;
  letter-spacing: {float(letter_spacing_em):g}em;
  max-width: 100%;
  white-space: normal;
  overflow: visible;
  text-overflow: clip;
}}
""".strip()


def _scope_operator_readout_selector(selector: str) -> str:
    """Return an Operator Readout selector that wins against host panel CSS.

    Several dashboard surfaces use generic container rules such as `.block p`
    or `.card p`. Those selectors are more specific than a bare
    `.operator-readout-copy` class, which means the "shared" readout contract
    can still lose in the final cascade. Scoping readout subparts under the
    shared article root keeps the fix centralized and renderer-agnostic.
    """

    parts = [part.strip() for part in str(selector or "").split(",") if part.strip()]
    scoped: list[str] = []
    for part in parts:
        if "operator-readout-shell" in part:
            scoped.append(part)
            continue
        if part == ".operator-readout" or part.startswith(".operator-readout ") or part.startswith(".operator-readout.") or part.startswith(".operator-readout:"):
            scoped.append(part)
            continue
        if ".operator-readout-" in part:
            scoped.append(f".operator-readout {part}")
            continue
        scoped.append(part)
    return ", ".join(scoped)


def operator_readout_layout_css(
    *,
    container_selector: str,
    meta_selector: str,
    main_selector: str,
    details_selector: str,
    section_selector: str,
    proof_selector: str,
    footnote_selector: str,
) -> str:
    """Return shared stacked-layout CSS for the homogeneous Operator Readout component.

    The delivery-intelligence hard cut deliberately avoids a card-grid
    presentation. One operator diagnosis should read as one vertically stacked
    incident block across every surface.
    """

    return f"""
{container_selector} {{
  border: 1px solid rgba(3, 105, 161, 0.16);
  border-left: 4px solid rgba(37, 99, 235, 0.5);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.96);
  font-family: {BODY_FONT_FAMILY};
  padding: 12px 14px;
  display: grid;
  gap: 10px;
  min-width: 0;
}}

{meta_selector} {{
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
  min-width: 0;
}}

{main_selector} {{
  display: grid;
  gap: 8px;
  max-width: min(100%, 84ch);
}}

{details_selector} {{
  display: grid;
  gap: 2px;
  max-width: min(100%, 84ch);
}}

{section_selector} {{
  display: grid;
  gap: 8px;
  padding-top: 10px;
  border-top: 1px solid rgba(148, 163, 184, 0.18);
}}

{section_selector}:first-child {{
  padding-top: 0;
  border-top: 0;
}}

{proof_selector} {{
  display: grid;
  gap: 8px;
  justify-items: start;
  min-width: 0;
}}

{proof_selector} > * {{
  max-width: min(100%, 78ch);
  min-width: 0;
}}

{proof_selector} a {{
  display: inline-block;
  width: fit-content;
  max-width: 100%;
  font-family: inherit;
  font-size: inherit;
  color: #244d89;
  font-weight: 500;
  line-height: 1.4;
  letter-spacing: 0;
  text-decoration: none;
  border-bottom: 1px solid #c5d5f1;
}}

{proof_selector} a:hover,
{proof_selector} a:focus-visible {{
  color: #173b74;
  border-bottom-color: #7ca4de;
  outline: none;
}}

{footnote_selector} {{
  margin: 0;
}}
""".strip()


def operator_readout_host_shell_css(
    *,
    shell_selector: str,
    heading_selector: str,
    body_selector: str,
    gap_px: int = 10,
) -> str:
    """Return shared outer-shell layout CSS for Operator Readout host sections.

    The readout article is centralized, but the surrounding host section title
    and body rhythm also need one contract so the block stops changing visual
    identity from surface to surface.
    """

    return f"""
{shell_selector} {{
  display: grid;
  font-family: {BODY_FONT_FAMILY};
  gap: {int(gap_px)}px;
  min-width: 0;
}}

{heading_selector} {{
  margin: 0;
}}

{body_selector} {{
  min-width: 0;
}}
""".strip()


def operator_readout_host_heading_css(
    *,
    selector: str,
    color: str = "#27445e",
    size_px: int = 12,
    letter_spacing_em: float = 0.06,
    margin: str = "0",
    line_height: float = 1.2,
    weight: int = 700,
) -> str:
    """Return shared section-title typography for Operator Readout host shells."""

    return section_heading_css(
        selector=selector,
        color=color,
        size_px=size_px,
        letter_spacing_em=letter_spacing_em,
        margin=margin,
        line_height=line_height,
        weight=weight,
    )


def operator_readout_label_typography_css(
    *,
    selector: str,
    color: str = "#475569",
    size_px: int = 11,
    letter_spacing_em: float = 0.07,
    margin: str = "0",
    line_height: float = 1.2,
    weight: int = 700,
) -> str:
    """Return the shared Radar-led label typography for Operator Readout blocks."""

    return auxiliary_heading_css(
        selector=_scope_operator_readout_selector(selector),
        color=color,
        size_px=size_px,
        letter_spacing_em=letter_spacing_em,
        margin=margin,
        line_height=line_height,
        weight=weight,
    )


def operator_readout_copy_typography_css(
    *,
    selector: str,
    color: str = "#27445e",
    size_px: int = 15,
    line_height: float = 1.55,
    weight: int = 400,
    letter_spacing_em: float = 0.0,
    margin: str = "0",
    emit_link_styles: bool = False,
    link_color: str = "#1b4e9f",
    link_hover_color: str = "#173b74",
    link_border_color: str = "#b9cff7",
    link_hover_border_color: str = "#5f95e6",
    link_weight: int = 600,
) -> str:
    """Return the shared Radar-led body-copy typography for Operator Readout blocks."""

    scoped_selector = _scope_operator_readout_selector(selector)
    base_css = intelligence_card_body_css(
        selector=_scope_operator_readout_selector(selector),
        color=color,
        size_px=size_px,
        line_height=line_height,
        weight=weight,
        letter_spacing_em=letter_spacing_em,
        margin=margin,
    )
    if not emit_link_styles:
        return base_css
    link_css = f"""
{scoped_selector} a {{
  color: {link_color};
  font-family: inherit;
  font-size: inherit;
  line-height: inherit;
  font-weight: {int(link_weight)};
  text-decoration: none;
  border-bottom: 1px solid {link_border_color};
}}

{scoped_selector} a:hover,
{scoped_selector} a:focus-visible {{
  color: {link_hover_color};
  border-bottom-color: {link_hover_border_color};
  outline: none;
}}
""".strip()
    return "\n\n".join((base_css, link_css))


def operator_readout_meta_pill_css(
    *,
    selector: str,
    background: str = "#f4f7fb",
    border_color: str = "#dde5ef",
    color: str = "#617389",
    size_px: int = 10,
    weight: int = 700,
    line_height: float = 1.1,
    letter_spacing_em: float = 0.06,
    padding: str = "4px 8px",
    radius_px: int = 999,
) -> str:
    """Return the shared Radar-led meta-pill styling for Operator Readout blocks."""

    return intelligence_meta_pill_css(
        selector=_scope_operator_readout_selector(selector),
        background=background,
        border_color=border_color,
        color=color,
        size_px=size_px,
        weight=weight,
        line_height=line_height,
        letter_spacing_em=letter_spacing_em,
        padding=padding,
        radius_px=radius_px,
    )


def operator_readout_meta_semantic_css(
    *,
    selector: str,
) -> str:
    """Return shared semantic tone overrides for Operator Readout metadata chips.

    The readout meta row should communicate three different kinds of operator
    context. Distinct subtle tones make the row learnable across surfaces
    without turning it into a loud badge strip.
    """

    scoped_selector = _scope_operator_readout_selector(selector)
    return f"""
{scoped_selector}.operator-readout-meta-scenario {{
  background: #eff3fb;
  border-color: #d6e0ee;
  color: #5a6f89;
}}

{scoped_selector}.operator-readout-meta-severity {{
  background: #f7f2ec;
  border-color: #e8d9c8;
  color: #87664a;
}}

{scoped_selector}.operator-readout-meta-source {{
  background: #f4f7f9;
  border-color: #dce4ea;
  color: #627588;
}}
""".strip()


def kpi_typography_css(
    *,
    label_selector: str,
    value_selector: str,
    label_size_px: int = 12,
    label_line_height: float = 1.15,
    label_letter_spacing_em: float = 0.06,
    value_size_px: int = 23,
    value_line_height: float = 1.0,
    value_letter_spacing_em: float = -0.01,
) -> str:
    """Return shared KPI/metric card typography CSS for dashboard surfaces."""

    return f"""
{label_selector} {{
  font-size: {int(label_size_px)}px;
  line-height: {float(label_line_height):g};
  letter-spacing: {float(label_letter_spacing_em):g}em;
}}

{value_selector} {{
  font-size: {int(value_size_px)}px;
  line-height: {float(value_line_height):g};
  letter-spacing: {float(value_letter_spacing_em):g}em;
}}
""".strip()


def governance_kpi_label_value_css(
    *,
    label_selector: str,
    value_selector: str,
    label_color: str = "var(--ink-muted, #64748b)",
    label_margin: str = "0",
    label_weight: int = 400,
    label_text_transform: str = "uppercase",
    label_display: str = "flex",
    label_align_items: str = "flex-start",
    label_size_px: int = 12,
    label_line_height: float = 1.15,
    label_letter_spacing_em: float = 0.06,
    value_color: str = "var(--ink, #0b1324)",
    value_margin: str = "4px 0 0",
    value_weight: int = 700,
    value_size_px: int = 23,
    value_line_height: float = 1.0,
    value_letter_spacing_em: float = -0.01,
) -> str:
    """Return the shared Radar-led KPI label/value typography contract.

    Radar, Compass, Registry, and Shell all present top-line governance KPIs
    with the same reading pattern: quiet uppercase label followed by a compact
    emphasized value. This helper keeps the full presentation contract
    centralized so renderers do not drift by re-implementing local label casing,
    spacing, weight, or color rules around the shared stat tiles.
    """

    return f"""
{label_selector} {{
  margin: {label_margin};
  color: {label_color};
  font-size: {int(label_size_px)}px;
  line-height: {float(label_line_height):g};
  letter-spacing: {float(label_letter_spacing_em):g}em;
  font-weight: {int(label_weight)};
  text-transform: {label_text_transform};
  display: {label_display};
  align-items: {label_align_items};
}}

{value_selector} {{
  margin: {value_margin};
  color: {value_color};
  font-size: {int(value_size_px)}px;
  line-height: {float(value_line_height):g};
  letter-spacing: {float(value_letter_spacing_em):g}em;
  font-weight: {int(value_weight)};
}}
""".strip()


def mono_identifier_typography_css(
    *,
    selector: str,
    color: str = "var(--ink-muted, #64748b)",
    size_px: int = 12,
    line_height: float = 1.2,
    weight: int = 400,
    letter_spacing_em: float = 0.0,
    margin: str = "0",
) -> str:
    """Return shared monospace identifier typography for ids and trace tokens."""

    return f"""
{selector} {{
  margin: {margin};
  color: {color};
  font-family: {MONO_FONT_FAMILY};
  font-size: {int(size_px)}px;
  line-height: {float(line_height):g};
  font-weight: {int(weight)};
  letter-spacing: {float(letter_spacing_em):g}em;
}}
""".strip()


def detail_identity_typography_css(
    *,
    title_selector: str,
    subtitle_selector: str,
    title_margin: str = "8px 0 4px",
    title_size_px: int = 26,
    title_line_height: float = 1.15,
    title_letter_spacing_em: float = -0.02,
    title_color: str = "var(--ink, #0b1324)",
    title_weight: int = 700,
    subtitle_margin: str = "0",
    subtitle_size_px: int = 13,
    subtitle_line_height: float = 1.2,
    subtitle_color: str = "var(--ink-muted, #64748b)",
    subtitle_font_family: str = MONO_FONT_FAMILY,
    medium_breakpoint_px: int = 1100,
    medium_title_size_px: int = 23,
    small_breakpoint_px: int = 920,
    small_title_size_px: int = 20,
) -> str:
    """Return shared detail header title/subtitle typography CSS.

    This primitive mirrors Radar's workstream-detail title rhythm and is reused
    by Registry component detail headers for cross-dashboard consistency.
    """

    return f"""
{title_selector} {{
  margin: {title_margin};
  color: {title_color};
  font-size: {int(title_size_px)}px;
  line-height: {float(title_line_height):g};
  letter-spacing: {float(title_letter_spacing_em):g}em;
  font-weight: {int(title_weight)};
}}

{subtitle_selector} {{
  margin: {subtitle_margin};
  color: {subtitle_color};
  font-size: {int(subtitle_size_px)}px;
  line-height: {float(subtitle_line_height):g};
  font-family: {subtitle_font_family};
}}

@media (max-width: {int(medium_breakpoint_px)}px) {{
  {title_selector} {{
    font-size: {int(medium_title_size_px)}px;
  }}
}}

@media (max-width: {int(small_breakpoint_px)}px) {{
  {title_selector} {{
    font-size: {int(small_title_size_px)}px;
  }}
}}
""".strip()


def quick_tooltip_surface_css(
    *,
    selector: str,
    visible_selector: str | None = None,
    max_width: str = "min(340px, calc(100vw - 20px))",
    background: str = "#0f172a",
    border_color: str = "rgba(191, 219, 254, 0.5)",
    border_radius_px: int = 8,
    padding: str = "6px 8px",
    shadow: str = "0 10px 24px rgba(15, 23, 42, 0.32)",
    hidden_opacity: float = 0.0,
    hidden_translate_y_px: int = 2,
    transition: str = "opacity 70ms linear, transform 70ms ease-out",
    pointer_events: str = "none",
) -> str:
    """Return shared quick-tooltip surface CSS for dashboard hover affordances.

    Radar, Atlas, Compass, Registry, and Shell all use the same floating
    tooltip treatment. Keep the surface contract centralized here so renderers
    only own typography overrides or explicit per-surface exceptions.
    """

    resolved_visible_selector = visible_selector or f"{selector}.visible"
    return f"""
{selector} {{
  position: fixed;
  z-index: 9999;
  pointer-events: {pointer_events};
  max-width: {max_width};
  background: {background};
  border: 1px solid {border_color};
  border-radius: {int(border_radius_px)}px;
  padding: {padding};
  box-shadow: {shadow};
  opacity: {float(hidden_opacity):g};
  transform: translateY({int(hidden_translate_y_px)}px);
  transition: {transition};
  white-space: normal;
  overflow-wrap: break-word;
}}

{resolved_visible_selector} {{
  opacity: 1;
  transform: translateY(0);
}}
""".strip()


def tooltip_typography_css(
    *,
    selector: str,
    color: str = "#f8fafc",
    size_px: int = 12,
    line_height: float = 1.25,
    weight: int = 600,
    letter_spacing_em: float = 0.0,
) -> str:
    """Return shared tooltip typography for dashboard hover affordances."""

    return f"""
{selector} {{
  color: {color};
  font-size: {int(size_px)}px;
  line-height: {float(line_height):g};
  font-weight: {int(weight)};
  letter-spacing: {float(letter_spacing_em):g}em;
}}
""".strip()


__all__ = [
    "BODY_FONT_FAMILY",
    "MONO_FONT_FAMILY",
    "auxiliary_heading_css",
    "button_typography_css",
    "card_title_typography_css",
    "caption_typography_css",
    "chart_axis_typography_css",
    "compact_label_value_typography_css",
    "code_typography_css",
    "control_label_css",
    "content_copy_css",
    "detail_disclosure_title_css",
    "display_title_typography_css",
    "detail_identity_typography_css",
    "detail_action_chip_css",
    "detail_toggle_chip_css",
    "governance_kpi_label_value_css",
    "header_typography_css",
    "hero_panel_css",
    "intelligence_card_body_css",
    "intelligence_card_heading_css",
    "intelligence_card_surface_css",
    "intelligence_card_variant_css",
    "intelligence_meta_pill_css",
    "kpi_card_surface_css",
    "kpi_typography_css",
    "label_badge_typography_css",
    "label_surface_css",
    "label_chip_surface_css",
    "mono_identifier_typography_css",
    "operator_readout_layout_css",
    "operator_readout_host_shell_css",
    "operator_readout_host_heading_css",
    "operator_readout_label_typography_css",
    "operator_readout_copy_typography_css",
    "operator_readout_meta_pill_css",
    "operator_readout_meta_semantic_css",
    "panel_surface_css",
    "page_body_typography_css",
    "quick_tooltip_surface_css",
    "section_heading_css",
    "shell_tab_surface_css",
    "sticky_filter_shell_css",
    "sticky_filter_bar_css",
    "split_detail_workspace_css",
    "action_chip_surface_css",
    "subtle_labeled_surface_tone_css",
    "subtle_label_tone_css",
    "subtle_link_label_tone_css",
    "supporting_copy_typography_css",
    "tooltip_typography_css",
    "value_emphasis_typography_css",
]
