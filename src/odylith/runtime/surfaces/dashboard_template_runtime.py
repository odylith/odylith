"""Shared template helpers for dashboard renderers.

Jinja2 is optional in local maintainer environments. Dashboard renderers should
still be able to produce deterministic HTML from the small source-owned shell
templates when that dependency is absent.
"""

from __future__ import annotations

from functools import lru_cache
import html
from pathlib import Path
import re
from typing import Any

try:  # pragma: no cover - exercised indirectly in environments with Jinja2.
    from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape
except ModuleNotFoundError:  # pragma: no cover - exercised in local fallback mode.
    Environment = None  # type: ignore[assignment]
    FileSystemLoader = None  # type: ignore[assignment]
    StrictUndefined = None  # type: ignore[assignment]
    select_autoescape = None  # type: ignore[assignment]


_PLACEHOLDER_RE = re.compile(r"{{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*(\|\s*safe\s*)?}}")


@lru_cache(maxsize=1)
def _template_root() -> Path:
    return Path(__file__).resolve().parent / "templates"


@lru_cache(maxsize=1)
def build_environment() -> Any:
    if Environment is None or FileSystemLoader is None or StrictUndefined is None or select_autoescape is None:
        raise RuntimeError("Jinja2 is not installed")
    template_root = _template_root()
    return Environment(
        loader=FileSystemLoader(str(template_root)),
        autoescape=select_autoescape(enabled_extensions=("html", "htm", "xml", "j2")),
        undefined=StrictUndefined,
        keep_trailing_newline=True,
        trim_blocks=False,
        lstrip_blocks=False,
    )


def _load_template_source(template_name: str) -> str:
    token = str(template_name or "").strip()
    if not token:
        raise ValueError("template_name must be non-empty")
    target = (_template_root() / token).resolve()
    template_root = _template_root().resolve()
    try:
        target.relative_to(template_root)
    except ValueError as exc:  # pragma: no cover - defensive path traversal guard.
        raise ValueError(f"template must live under {template_root}") from exc
    if not target.is_file():
        raise FileNotFoundError(f"template missing: {target}")
    return target.read_text(encoding="utf-8")


def _render_without_jinja(template_name: str, /, **context: object) -> str:
    source = _load_template_source(template_name)

    def _replace(match: re.Match[str]) -> str:
        key = str(match.group(1) or "").strip()
        if key not in context:
            raise KeyError(f"missing template context value: {key}")
        value = "" if context[key] is None else str(context[key])
        is_safe = bool(match.group(2))
        return value if is_safe else html.escape(value)

    return _PLACEHOLDER_RE.sub(_replace, source)


def render_template(template_name: str, /, **context: object) -> str:
    try:
        environment = build_environment()
    except RuntimeError:
        return _render_without_jinja(template_name, **context)
    return environment.get_template(template_name).render(**context)
