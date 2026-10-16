"""Shared surface-theme CSS contracts for Odylith governance dashboards."""

from __future__ import annotations


def selection_card_surface_css(
    *,
    selector: str,
    active_selector: str | None = None,
    padding: str = "10px 10px 9px",
) -> str:
    """Return the shared left-rail selection card surface contract."""

    active = active_selector or f"{selector}.active"
    return f"""
{selector} {{
  width: 100%;
  text-align: left;
  border: 1px solid #d6dce8;
  border-radius: 12px;
  background: #ffffff;
  padding: {padding};
  cursor: pointer;
  color: inherit;
  white-space: normal;
  overflow-wrap: anywhere;
  display: grid;
  gap: 6px;
  transition: border-color 120ms ease, box-shadow 120ms ease, transform 120ms ease;
}}
{selector}:hover {{
  border-color: #93c5fd;
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.09);
  transform: translateY(-1px);
}}
{active} {{
  border-color: #1d4ed8;
  background: linear-gradient(180deg, #ffffff, #f8fbff);
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.22);
}}
""".strip()


def narrative_stack_surface_css(*, selector: str, gap_px: int = 8) -> str:
    """Return a quiet narrative stack that avoids nested-card visual noise."""

    return f"""
{selector} {{
  border: 0;
  border-radius: 0;
  background: transparent;
  padding: 0;
  display: grid;
  gap: {int(gap_px)}px;
  min-width: 0;
}}
""".strip()


def evidence_note_surface_css(
    *,
    selector: str,
    accent_color: str = "#bfdbfe",
    border_color: str = "#dbeafe",
    background: str = "#fbfdff",
    padding: str = "12px 13px 12px 12px",
    radius_px: int = 12,
    gap_px: int = 7,
) -> str:
    """Return a quiet evidence note surface with a left confidence accent."""

    return f"""
{selector} {{
  border: 1px solid {border_color};
  border-left: 3px solid {accent_color};
  border-radius: {int(radius_px)}px;
  background: {background};
  padding: {padding};
  display: grid;
  gap: {int(gap_px)}px;
  min-width: 0;
}}
""".strip()


def evidence_list_row_surface_css(
    *,
    selector: str,
    padding: str = "12px",
    gap_px: int = 7,
    separator_color: str = "#e5eefb",
) -> str:
    """Return a low-noise evidence-list row that preserves nested links."""

    return f"""
{selector} {{
  border: 0;
  border-radius: 0;
  background: transparent;
  padding: {padding};
  display: grid;
  gap: {int(gap_px)}px;
  min-width: 0;
}}
{selector} + {selector} {{
  border-top: 1px solid {separator_color};
}}
""".strip()


def metric_strip_surface_css(
    *,
    selector: str,
    columns: int = 5,
    border_color: str = "#dbeafe",
    radius_px: int = 12,
    background: str = "#ffffff",
) -> str:
    """Return the shared horizontal metric-strip surface contract."""

    return f"""
{selector} {{
  display: grid;
  grid-template-columns: repeat({int(columns)}, minmax(0, 1fr));
  gap: 0;
  border: 1px solid {border_color};
  border-radius: {int(radius_px)}px;
  background: {background};
  overflow: hidden;
  min-width: 0;
}}
""".strip()


def metric_strip_item_css(
    *,
    selector: str,
    min_height_px: int = 58,
    padding: str = "14px 16px",
    align_items: str = "center",
) -> str:
    """Return shared horizontal metric-strip item layout CSS."""

    return f"""
{selector} {{
  border: 0;
  border-radius: 0;
  background: transparent;
  min-height: {int(min_height_px)}px;
  padding: {padding};
  display: flex;
  align-items: {align_items};
  justify-content: space-between;
  gap: 8px;
  min-width: 0;
}}
""".strip()


def quiet_panel_surface_css(
    *,
    selector: str,
    padding: str = "11px 12px",
    radius_px: int = 12,
    gap_px: int = 6,
    border_color: str = "#d9e6fa",
    background: str = "linear-gradient(180deg, #ffffff, #f8fbff)",
) -> str:
    """Return a low-noise panel surface for dashboard detail modules."""

    return f"""
{selector} {{
  border: 1px solid {border_color};
  border-radius: {int(radius_px)}px;
  background: {background};
  padding: {padding};
  display: grid;
  gap: {int(gap_px)}px;
  min-width: 0;
}}
""".strip()


__all__ = [
    "evidence_list_row_surface_css",
    "evidence_note_surface_css",
    "metric_strip_item_css",
    "metric_strip_surface_css",
    "narrative_stack_surface_css",
    "quiet_panel_surface_css",
    "selection_card_surface_css",
]
