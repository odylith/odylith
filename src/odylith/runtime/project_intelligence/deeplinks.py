"""Inline Project-tab deeplinks for source-backed governance references."""

from __future__ import annotations

import html
import re
from collections.abc import Mapping
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Iterator
from urllib.parse import quote

from odylith.runtime.surfaces.dashboard_shell_links import shell_href
from odylith.runtime.surfaces.dashboard_shell_links import surface_href

_WORKSTREAM_RE = r"\bB-\d+\b"
_BUG_RE = r"\bCB-\d+\b"
_DIAGRAM_RE = r"\bD-\d+\b"
_PLAN_RE = r"\bodylith/technical-plans/(?:in-progress|done/[0-9]{4}-[0-9]{2}|done/legacy)/[A-Za-z0-9._/\-]+\.md\b"
_SURFACE_RE = r"(?<![/\w.-])(?:Registry|Radar|Compass|Atlas|Casebook)(?![/\w.-])"
_REFERENCE_RE = re.compile(
    rf"{_PLAN_RE}|{_BUG_RE}|{_WORKSTREAM_RE}|{_DIAGRAM_RE}|{_SURFACE_RE}",
    re.IGNORECASE,
)
_TITLE_CONTEXT: ContextVar[dict[str, str]] = ContextVar("project_deeplink_titles", default={})


def _clean_title(value: object) -> str:
    return " ".join(str(value or "").replace("`", "").split())


def _canonical_reference(token: object) -> str:
    value = str(token or "").strip()
    if re.fullmatch(_BUG_RE, value, re.IGNORECASE):
        return value.upper()
    if re.fullmatch(_WORKSTREAM_RE, value, re.IGNORECASE):
        return value.upper()
    if re.fullmatch(_DIAGRAM_RE, value, re.IGNORECASE):
        return value.upper()
    if re.fullmatch(_PLAN_RE, value, re.IGNORECASE):
        return value
    return ""


def _title_index(titles: Mapping[str, object] | None) -> dict[str, str]:
    if not isinstance(titles, Mapping):
        return {}
    index: dict[str, str] = {}
    for raw_ref, raw_title in titles.items():
        title = _clean_title(raw_title)
        if not title:
            continue
        ref = _canonical_reference(raw_ref)
        if ref:
            index[ref] = title
        for match in re.finditer(r"\b(?:B|CB|D)-\d+\b", str(raw_ref or ""), re.IGNORECASE):
            index[match.group(0).upper()] = title
    return index


@contextmanager
def deeplink_title_context(titles: Mapping[str, object] | None) -> Iterator[None]:
    """Temporarily bind governance artifact titles for Project deeplink rendering."""

    token = _TITLE_CONTEXT.set(_title_index(titles))
    try:
        yield
    finally:
        _TITLE_CONTEXT.reset(token)


def _canonical_surface(token: str) -> str:
    return str(token or "").strip().lower().capitalize()


def _href_for_token(token: str) -> str:
    value = str(token or "").strip()
    canonical = value.upper()
    if re.fullmatch(_BUG_RE, value, re.IGNORECASE):
        return shell_href(tab="casebook", bug=canonical)
    if re.fullmatch(_WORKSTREAM_RE, value, re.IGNORECASE):
        return shell_href(tab="radar", workstream=canonical)
    if re.fullmatch(_DIAGRAM_RE, value, re.IGNORECASE):
        return shell_href(tab="atlas", diagram=canonical)
    if re.fullmatch(_PLAN_RE, value, re.IGNORECASE):
        return quote(value.removeprefix("odylith/"))
    if re.fullmatch(_SURFACE_RE, value, re.IGNORECASE):
        return surface_href(_canonical_surface(value))
    return ""


def _tooltip_for_token(token: str, titles: Mapping[str, object] | None = None) -> str:
    value = str(token or "").strip()
    canonical = value.upper()
    title_index = _title_index(titles) if titles is not None else _TITLE_CONTEXT.get({})
    artifact_title = title_index.get(canonical) or title_index.get(value)
    if re.fullmatch(_BUG_RE, value, re.IGNORECASE):
        if artifact_title:
            return artifact_title
        return f"Casebook bug {canonical}. Open Casebook context."
    if re.fullmatch(_WORKSTREAM_RE, value, re.IGNORECASE):
        if artifact_title:
            return artifact_title
        return f"Workstream {canonical}. Open Radar context."
    if re.fullmatch(_DIAGRAM_RE, value, re.IGNORECASE):
        if artifact_title:
            return artifact_title
        return f"Diagram {canonical}. Open Atlas context."
    return ""


def inline_deeplink_html(value: object, *, titles: Mapping[str, object] | None = None) -> str:
    """Escape text and link recognized Project references to their source surface."""

    raw = str(value or "")
    if not raw:
        return ""
    title_index = _title_index(titles) if titles is not None else _TITLE_CONTEXT.get({})
    parts: list[str] = []
    cursor = 0
    for match in _REFERENCE_RE.finditer(raw):
        start, end = match.span()
        if start > cursor:
            parts.append(html.escape(raw[cursor:start], quote=True))
        token = match.group(0)
        href = _href_for_token(token)
        if href:
            tooltip = _tooltip_for_token(token, title_index)
            class_name = "project-deeplink project-id-deeplink" if tooltip else "project-deeplink"
            tooltip_attrs = (
                f' data-tooltip="{html.escape(tooltip, quote=True)}"'
                f' aria-label="{html.escape(tooltip, quote=True)}"'
                f' title="{html.escape(tooltip, quote=True)}"'
                if tooltip
                else ""
            )
            parts.append(
                f'<a class="{class_name}" target="_top" '
                f'href="{html.escape(href, quote=True)}"{tooltip_attrs}>{html.escape(token, quote=True)}</a>'
            )
        else:
            parts.append(html.escape(token, quote=True))
        cursor = end
    if cursor < len(raw):
        parts.append(html.escape(raw[cursor:], quote=True))
    return "".join(parts)
