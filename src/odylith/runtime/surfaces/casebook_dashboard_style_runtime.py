"""Style helpers for the Casebook dashboard renderer."""

from __future__ import annotations

from odylith.runtime.surfaces import dashboard_ui_primitives
from odylith.runtime.surfaces import dashboard_ui_runtime_primitives
from odylith.runtime.surfaces import governance_surface_theme


def casebook_dashboard_style_bundle() -> dict[str, str]:
    page_body_css = dashboard_ui_primitives.page_body_typography_css(selector="body")
    surface_shell_root_css = dashboard_ui_primitives.standard_surface_shell_root_css()
    surface_shell_css = dashboard_ui_primitives.standard_surface_shell_css(
        selector=".shell",
        padding="18px 12px 30px",
        display="grid",
        gap_px=12,
    )
    header_typography_css = dashboard_ui_primitives.header_typography_css(
        kicker_selector=".kicker",
        title_selector=".hero-title",
        subtitle_selector=".subtitle",
        subtitle_max_width="78ch",
        desktop_single_line_subtitle=False,
        mobile_breakpoint_px=760,
        mobile_title_size_px=22,
        mobile_subtitle_size_px=13,
    )
    hero_panel_css = dashboard_ui_primitives.hero_panel_css(
        container_selector=".hero",
        margin_bottom="0",
    )
    kpi_card_surface_css = dashboard_ui_primitives.kpi_card_surface_css(card_selector=".kpi-card")
    kpi_grid_css = dashboard_ui_primitives.kpi_grid_layout_css(container_selector=".kpis")
    kpi_typography_css = dashboard_ui_primitives.governance_kpi_label_value_css(
        label_selector=".kpi-label",
        value_selector=".kpi-value",
    )
    sticky_filter_shell_css = dashboard_ui_primitives.sticky_filter_shell_css(
        shell_selector=".filters-shell",
        top_px=10,
    )
    sticky_filter_bar_css = dashboard_ui_primitives.sticky_filter_bar_css(
        container_selector=".filters-bar",
        columns="repeat(4, minmax(0, 1fr))",
        field_selector=".filter-control",
        focus_selector=".filter-control:focus",
        top_px=10,
    )
    control_label_css = dashboard_ui_primitives.control_label_css(
        selector=".control-label",
        color="var(--ink-muted)",
        size_px=11,
        letter_spacing_em=0.04,
    )
    workspace_layout_css = dashboard_ui_primitives.split_detail_workspace_css(
        selector=".workspace",
        left_min_px=340,
        left_max_px=430,
    )
    panel_surface_css = ""
    row_surface_css = "\n\n".join(
        (
            governance_surface_theme.selection_card_surface_css(selector=".bug-row"),
            ".bug-row {\n  margin-bottom: 8px;\n}",
        )
    )
    narrative_section_surface_css = dashboard_ui_primitives.panel_surface_css(
        selector=".empty-state",
        padding="12px 13px",
        radius_px=12,
        gap_px=8,
        shadow="none",
        background="linear-gradient(180deg, #ffffff, #fbfdff)",
    )
    label_surface_css = dashboard_ui_primitives.label_surface_css(
        selector=".meta-chip, .list-chip, .filter-chip",
        padding="4px 10px",
        background="#f6faf7",
        border_color="#dbe5df",
        color="#334155",
        border_radius_px=4,
        min_height_px=0,
    )
    label_typography_css = dashboard_ui_primitives.label_badge_typography_css(
        selector=".meta-chip, .list-chip, .filter-chip",
        color="#334155",
        size_px=11,
        line_height=1.0,
        letter_spacing_em=0.03,
    )
    label_tone_css = "\n\n".join(
        (
            dashboard_ui_primitives.subtle_label_tone_css(
                selector=".warn-chip",
                background="#fff7ed",
                border_color="#f3c58e",
                color="#9a3412",
            ),
            dashboard_ui_primitives.subtle_label_tone_css(
                selector=".critical-chip",
                background="#fef2f2",
                border_color="#fecaca",
                color="#b91c1c",
            ),
            dashboard_ui_primitives.subtle_label_tone_css(
                selector=".archive-chip",
                background="#eef2f7",
                border_color="#d7e0e9",
                color="#53687f",
            ),
        )
    )
    detail_action_chip_css = dashboard_ui_primitives.detail_action_chip_css(selector=".action-chip")
    identifier_typography_css = "\n\n".join(
        (
            dashboard_ui_primitives.surface_identifier_typography_css(
                selector=".component-subtitle, .ref-meta",
                color="var(--ink-muted)",
                line_height=1.45,
            ),
            dashboard_ui_primitives.surface_identifier_typography_css(
                selector=".bug-row-kicker",
                color="var(--ink-muted)",
                margin="0 0 4px",
                line_height=1.2,
                letter_spacing_em=0.08,
                text_transform="uppercase",
            ),
        )
    )
    tooltip_surface_css, tooltip_runtime_js = dashboard_ui_runtime_primitives.quick_tooltip_bundle(
        binding_guard_dataset_key="odylithCasebookTooltipBound",
        function_name="initCasebookQuickTooltips",
    )
    section_heading_css = "\n\n".join(
        (
            dashboard_ui_primitives.operator_readout_host_heading_css(
                selector=".section-heading",
                color="#27445e",
                size_px=12,
                letter_spacing_em=0.06,
                margin="0",
                line_height=1.2,
                weight=700,
            ),
            dashboard_ui_primitives.detail_disclosure_title_css(
                selector=".disclosure-title",
                color="#27445e",
                size_px=13,
                line_height=1.45,
                weight=700,
                letter_spacing_em=0.0,
                margin="0",
            ),
        )
    )
    panel_head_typography_css = "\n\n".join(
        (
            dashboard_ui_primitives.card_title_typography_css(
                selector=".panel-head-title",
                color="var(--ink)",
                size_px=15,
                line_height=1.35,
                letter_spacing_em=0.0,
                weight=700,
                margin="0",
            ),
            dashboard_ui_primitives.supporting_copy_typography_css(
                selector=".panel-head-meta",
                color="var(--ink-muted)",
                size_px=13,
                line_height=1.35,
                weight=600,
                letter_spacing_em=0.0,
            ),
        )
    )
    secondary_heading_css = "\n\n".join(
        (
            dashboard_ui_primitives.auxiliary_heading_css(
                selector=".meta-label",
                color="var(--ink-muted)",
                size_px=11,
                line_height=1.2,
                letter_spacing_em=0.07,
                margin="0",
            ),
            dashboard_ui_primitives.auxiliary_heading_css(
                selector=".bug-row-date",
                color="var(--ink-muted)",
                size_px=11,
                line_height=1.2,
                letter_spacing_em=0.07,
                margin="0",
            ),
            dashboard_ui_primitives.auxiliary_heading_css(
                selector=".pivot-title",
                color="var(--ink-muted)",
                size_px=11,
                line_height=1.2,
                letter_spacing_em=0.07,
                margin="0",
            ),
            dashboard_ui_primitives.operator_readout_label_typography_css(
                selector=".signal-label, .inline-note-label",
            ),
        )
    )
    compact_fact_css = dashboard_ui_primitives.compact_label_value_typography_css(
        label_selector=".summary-fact-label",
        value_selector=".summary-fact-value",
        label_color="var(--ink-muted)",
        value_color="#16324f",
    )
    inline_row_css = dashboard_ui_primitives.inline_label_value_copy_css(
        row_selectors=(
            ".narrative-row",
            ".coverage-note",
            ".component-note",
            ".link-row-note",
        ),
        label_selectors=(),
        size_px=14,
        line_height=1.55,
        color="var(--ink-soft)",
    )
    card_title_css = "\n\n".join(
        (
            dashboard_ui_primitives.card_title_typography_css(
                selector=".bug-row-title",
                color="var(--ink)",
                size_px=16,
                line_height=1.3,
                margin="0",
            ),
            dashboard_ui_primitives.card_title_typography_css(
                selector=".detail-title",
                color="var(--ink)",
                size_px=26,
                line_height=1.1,
                margin="0",
            ),
            dashboard_ui_primitives.card_title_typography_css(
                selector=".component-context-name",
                color="var(--ink)",
                size_px=14,
                line_height=1.2,
                margin="0",
            ),
        )
    )
    copy_css = "\n\n".join(
        (
            dashboard_ui_primitives.content_copy_css(
                selectors=(".bug-row-summary", ".detail-summary", ".detail-copy", ".empty-state"),
                size_px=14,
                line_height=1.5,
                color="var(--ink-soft)",
            ),
            dashboard_ui_primitives.supporting_copy_typography_css(
                selector=".meta-value, .summary-fallback",
                color="var(--ink-soft)",
                size_px=13,
                line_height=1.45,
            ),
        )
    )
    code_typography_css = dashboard_ui_primitives.code_typography_css(
        selector=".bug-row-summary code, .detail-copy code, .meta-value code",
        color="inherit",
        size_px=12,
        line_height=1.2,
    )
    return {
        "page_body_css": page_body_css,
        "surface_shell_root_css": surface_shell_root_css,
        "surface_shell_css": surface_shell_css,
        "hero_panel_css": hero_panel_css,
        "header_typography_css": header_typography_css,
        "kpi_grid_css": kpi_grid_css,
        "kpi_card_surface_css": kpi_card_surface_css,
        "kpi_typography_css": kpi_typography_css,
        "sticky_filter_shell_css": sticky_filter_shell_css,
        "sticky_filter_bar_css": sticky_filter_bar_css,
        "control_label_css": control_label_css,
        "workspace_layout_css": workspace_layout_css,
        "panel_surface_css": panel_surface_css,
        "row_surface_css": row_surface_css,
        "narrative_section_surface_css": narrative_section_surface_css,
        "label_surface_css": label_surface_css,
        "label_typography_css": label_typography_css,
        "label_tone_css": label_tone_css,
        "detail_action_chip_css": detail_action_chip_css,
        "section_heading_css": section_heading_css,
        "panel_head_typography_css": panel_head_typography_css,
        "secondary_heading_css": secondary_heading_css,
        "compact_fact_css": compact_fact_css,
        "inline_row_css": inline_row_css,
        "card_title_css": card_title_css,
        "copy_css": copy_css,
        "tooltip_surface_css": tooltip_surface_css,
        "tooltip_runtime_js": tooltip_runtime_js,
        "code_typography_css": code_typography_css,
        "identifier_typography_css": identifier_typography_css,
    }


def apply_casebook_dashboard_style_placeholders(html: str, styles: dict[str, str]) -> str:
    replacements = {
        "__CASEBOOK_PAGE_BODY__": styles["page_body_css"],
        "__CASEBOOK_SURFACE_SHELL_ROOT__": styles["surface_shell_root_css"],
        "__CASEBOOK_SURFACE_SHELL__": styles["surface_shell_css"],
        "__CASEBOOK_HERO_PANEL__": styles["hero_panel_css"],
        "__CASEBOOK_HEADER_TYPOGRAPHY__": styles["header_typography_css"],
        "__CASEBOOK_KPI_GRID__": styles["kpi_grid_css"],
        "__CASEBOOK_KPI_CARD__": styles["kpi_card_surface_css"],
        "__CASEBOOK_KPI_TYPOGRAPHY__": styles["kpi_typography_css"],
        "__CASEBOOK_FILTER_SHELL__": styles["sticky_filter_shell_css"],
        "__CASEBOOK_FILTER_BAR__": styles["sticky_filter_bar_css"],
        "__CASEBOOK_CONTROL_LABEL__": styles["control_label_css"],
        "__CASEBOOK_WORKSPACE__": styles["workspace_layout_css"],
        "__CASEBOOK_PANEL_SURFACE__": styles["panel_surface_css"],
        "__CASEBOOK_ROW_SURFACE__": styles["row_surface_css"],
        "__CASEBOOK_EMPTY_STATE_SURFACE__": styles["narrative_section_surface_css"],
        "__CASEBOOK_LABEL_SURFACE__": styles["label_surface_css"],
        "__CASEBOOK_LABEL_TYPOGRAPHY__": styles["label_typography_css"],
        "__CASEBOOK_LABEL_TONES__": styles["label_tone_css"],
        "__CASEBOOK_ACTION_CHIP__": styles["detail_action_chip_css"],
        "__CASEBOOK_SECTION_HEADING__": styles["section_heading_css"],
        "__CASEBOOK_PANEL_HEAD_TYPOGRAPHY__": styles["panel_head_typography_css"],
        "__CASEBOOK_SECONDARY_HEADINGS__": styles["secondary_heading_css"],
        "__CASEBOOK_COMPACT_FACT_TYPOGRAPHY__": styles["compact_fact_css"],
        "__CASEBOOK_INLINE_ROW_TYPOGRAPHY__": styles["inline_row_css"],
        "__CASEBOOK_CARD_TITLE__": styles["card_title_css"],
        "__CASEBOOK_COPY__": styles["copy_css"],
        "__CASEBOOK_TOOLTIP_SURFACE__": styles["tooltip_surface_css"],
        "__CASEBOOK_QUICK_TOOLTIP_RUNTIME__": styles["tooltip_runtime_js"],
        "__CASEBOOK_CODE_TYPOGRAPHY__": styles["code_typography_css"],
        "__CASEBOOK_IDENTIFIER_TYPOGRAPHY__": styles["identifier_typography_css"],
    }
    for marker, value in replacements.items():
        html = html.replace(marker, value)
    return html
