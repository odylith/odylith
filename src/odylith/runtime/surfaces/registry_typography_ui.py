"""Registry typography contracts built from shared dashboard primitives."""

from __future__ import annotations

from odylith.runtime.surfaces import dashboard_ui_primitives


def brief_section_label_css() -> str:
    """Return Registry section-label typography."""

    return dashboard_ui_primitives.control_label_css(
        selector=".answers-head",
        color="#1f4868",
        size_px=12,
        letter_spacing_em=0.06,
        line_height=1.2,
    )


def content_copy_css() -> str:
    """Return Registry readable-body typography."""

    return dashboard_ui_primitives.content_copy_css(
        selectors=(
            ".trigger-list",
            ".trigger-list li",
            ".spec-doc p",
            ".spec-doc ul",
            ".spec-doc li",
        ),
    )


def detail_identity_css() -> str:
    """Return Registry detail title/subtitle typography."""

    return dashboard_ui_primitives.detail_identity_typography_css(
        title_selector=".component-name",
        subtitle_selector=".component-full-name",
        title_size_px=24,
        title_letter_spacing_em=0.0,
        medium_title_size_px=22,
        small_title_size_px=19,
    )


def detail_panel_typography_css() -> str:
    """Return Registry detail-pane typography on the Radar reading scale."""

    summary_row_css = dashboard_ui_primitives.inline_label_value_copy_css(
        row_selectors=(".summary-row",),
        label_selectors=(".summary-row strong",),
        size_px=15,
        line_height=1.55,
        color="#27445e",
        label_color="#22496f",
    )
    return "\n\n".join(
        (
            dashboard_ui_primitives.section_heading_css(
                selector=".pane-head",
                color="#2a5078",
                size_px=13,
                line_height=1.2,
                letter_spacing_em=0.045,
                margin="0",
            ),
            dashboard_ui_primitives.auxiliary_heading_css(
                selector=".group-head",
                color="#547196",
                size_px=11,
                line_height=1.2,
                letter_spacing_em=0.07,
                margin="0",
            ),
            dashboard_ui_primitives.button_typography_css(
                selector=".select",
                color="#20456b",
                size_px=14,
                line_height=1.0,
                weight=700,
            ),
            dashboard_ui_primitives.card_title_typography_css(
                selector=".component-card-title",
                color="var(--ink, #0b1324)",
                size_px=14,
                line_height=1.3,
                margin="0",
            ),
            dashboard_ui_primitives.detail_disclosure_title_css(
                selector=".detail-disclosure-title",
                color="#22496f",
                size_px=15,
                line_height=1.55,
                weight=700,
                letter_spacing_em=0.0,
                margin="0",
            ),
            dashboard_ui_primitives.caption_typography_css(
                selector=".component-meta",
                color="var(--muted)",
                size_px=12,
                line_height=1.35,
            ),
            dashboard_ui_primitives.card_title_typography_css(
                selector=".context-count",
                color="#2f4563",
                size_px=13,
                line_height=1.0,
                letter_spacing_em=0.0,
                weight=800,
                margin="0",
            ),
            summary_row_css,
            dashboard_ui_primitives.card_title_typography_css(
                selector=".spec-doc h3",
                color="#21466d",
                size_px=15,
                line_height=1.15,
                letter_spacing_em=0.0,
                margin="0",
            ),
            dashboard_ui_primitives.card_title_typography_css(
                selector=".spec-doc h4",
                color="#21466d",
                size_px=14,
                line_height=1.15,
                letter_spacing_em=0.0,
                margin="0",
            ),
            dashboard_ui_primitives.card_title_typography_css(
                selector=".spec-doc h5",
                color="#21466d",
                size_px=13,
                line_height=1.15,
                letter_spacing_em=0.0,
                margin="0",
            ),
            dashboard_ui_primitives.content_copy_css(
                selectors=(".spec-table",),
                size_px=12,
                line_height=1.35,
                color="#2d496a",
            ),
            dashboard_ui_primitives.card_title_typography_css(
                selector=".spec-table thead th",
                color="#1f3b5b",
                size_px=12,
                line_height=1.35,
                letter_spacing_em=0.0,
                weight=700,
                margin="0",
            ),
        )
    )


def code_typography_css() -> str:
    """Return Registry code-token typography."""

    return dashboard_ui_primitives.code_typography_css(
        selector=".spec-doc code",
        color="inherit",
        size_px=12,
        line_height=1.2,
        font_family='ui-monospace, SFMono-Regular, Menlo, Consolas, monospace',
    )


def context_heading_css() -> str:
    """Return Registry context and evidence heading typography."""

    return "\n\n".join(
        (
            dashboard_ui_primitives.section_heading_css(
                selector=".context-title",
                color="#4b6283",
                size_px=11,
                line_height=1.2,
                letter_spacing_em=0.06,
                margin="0",
            ),
            dashboard_ui_primitives.auxiliary_heading_css(
                selector=".timeline-head",
                color="#34597f",
                size_px=11,
                line_height=1.0,
                letter_spacing_em=0.07,
                margin="0",
            ),
        )
    )


def auxiliary_button_typography_css() -> str:
    """Return Registry auxiliary button and disclosure typography."""

    return "\n\n".join(
        (
            dashboard_ui_primitives.details_disclosure_caret_css(
                details_selector=".trigger-expand",
                label_selector=".trigger-summary-title",
                color="#64748b",
                size_px=11,
                gap_px=6,
            ),
            dashboard_ui_primitives.details_disclosure_caret_css(
                details_selector=".spec-expand",
                label_selector=".spec-summary-title",
                color="#64748b",
                size_px=11,
                gap_px=6,
            ),
            dashboard_ui_primitives.details_disclosure_caret_css(
                details_selector=".context-section",
                label_selector=".context-toggle-label",
                color="#64748b",
                size_px=11,
                gap_px=6,
            ),
            dashboard_ui_primitives.button_typography_css(
                selector=".diagnostics > summary",
                color="#8a4b00",
                size_px=12,
                line_height=1.35,
                letter_spacing_em=0.01,
            ),
        )
    )


def auxiliary_copy_css() -> str:
    """Return Registry secondary-copy typography."""

    return "\n\n".join(
        (
            dashboard_ui_primitives.content_copy_css(
                selectors=(".desc",),
                size_px=13,
                line_height=1.45,
                color="#2b4667",
            ),
            dashboard_ui_primitives.supporting_copy_typography_css(
                selector=".empty",
                color="var(--muted)",
                size_px=13,
                line_height=1.4,
            ),
            dashboard_ui_primitives.supporting_copy_typography_css(
                selector=".diag-item",
                color="#7a4100",
                size_px=12,
                line_height=1.35,
            ),
        )
    )


def forensic_digest_typography_css() -> str:
    """Return Registry Forensic Evidence typography."""

    return "\n\n".join(
        (
            dashboard_ui_primitives.card_title_typography_css(
                selector=".forensic-health-title, .forensic-eyebrow",
                color="#22496f",
                size_px=15,
                line_height=1.3,
                letter_spacing_em=0.0,
                weight=700,
                margin="0",
            ),
            dashboard_ui_primitives.content_copy_css(
                selectors=(".forensic-health-copy", ".forensic-summary"),
                size_px=15,
                line_height=1.55,
                color="#27445e",
            ),
            dashboard_ui_primitives.supporting_copy_typography_css(
                selector=".forensic-meta-row, .forensic-meta-item",
                color="#64748b",
                size_px=12,
                line_height=1.35,
                weight=600,
            ),
            dashboard_ui_primitives.supporting_copy_typography_css(
                selector=".forensic-group-meta, .forensic-group-meta-item",
                color="#64748b",
                size_px=12,
                line_height=1.35,
                weight=600,
            ),
            dashboard_ui_primitives.card_title_typography_css(
                selector=".forensic-group-channel",
                color="#27445e",
                size_px=13,
                line_height=1.35,
                letter_spacing_em=0.0,
                weight=700,
                margin="0",
            ),
            dashboard_ui_primitives.compact_label_value_typography_css(
                label_selector=".forensic-stat-label",
                value_selector=".forensic-stat-value",
                label_color="#64748b",
                label_size_px=10,
                label_line_height=1.0,
                label_letter_spacing_em=0.06,
                label_weight=800,
                value_color="#173b63",
                value_size_px=15,
                value_line_height=1.0,
                value_weight=800,
            ),
            dashboard_ui_primitives.card_title_typography_css(
                selector=".forensic-group-disclosure > summary",
                color="#27445e",
                size_px=13,
                line_height=1.2,
                letter_spacing_em=0.0,
                weight=700,
                margin="0",
            ),
        )
    )
