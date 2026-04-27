"""Helpers for parsing foreign Python source during static analysis."""

from __future__ import annotations

import ast
import warnings

_PARSER_WARNING_CATEGORIES: tuple[type[Warning], ...] = (
    DeprecationWarning,
    FutureWarning,
    SyntaxWarning,
)


def parse_python_source_for_static_analysis(
    source: str,
    *,
    filename: str = "<unknown>",
    mode: str = "exec",
) -> ast.AST:
    """Parse repository Python source without leaking parser warnings.

    Odylith statically inspects Python files from arbitrary repositories during
    startup, graph compilation, and benchmark helper passes. Those files may
    contain warning-worthy but still parseable constructs such as legacy escape
    sequences inside docstrings. Static analysis should stay quiet while still
    returning an AST when parsing succeeds; syntax failures still propagate as
    normal.
    """

    with warnings.catch_warnings():
        for category in _PARSER_WARNING_CATEGORIES:
            warnings.simplefilter("ignore", category=category)
        return ast.parse(source, filename=filename, mode=mode)
