"""Enforcement helpers for the Odylith governance proof state layer."""

from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

from odylith.runtime.common.value_coercion import normalize_string as _normalize_string
from .contract import build_claim_lint

_FIXED_PATTERN = re.compile(r"\bfixed\b(?!\s+(?:in\s+code|live)\b)(?!-)", re.IGNORECASE)
_CLEARED_PATTERN = re.compile(r"\bcleared\b(?!-)", re.IGNORECASE)
_RESOLVED_PATTERN = re.compile(r"\bresolved\b(?!-)", re.IGNORECASE)
_PATTERNS = {
    "fixed": _FIXED_PATTERN,
    "cleared": _CLEARED_PATTERN,
    "resolved": _RESOLVED_PATTERN,
}

def _claim_lint_payload(
    *,
    claim_guard: Mapping[str, Any] | Any = None,
    claim_lint: Mapping[str, Any] | Any = None,
) -> dict[str, Any]:
    if isinstance(claim_lint, Mapping):
        return dict(claim_lint)
    if isinstance(claim_guard, Mapping):
        return build_claim_lint(claim_guard)
    return build_claim_lint({})


def _match_case(*, replacement: str, original: str) -> str:
    token = str(replacement or "").strip()
    source = str(original or "")
    if not token:
        return source
    if source.isupper():
        return token.upper()
    if source[:1].isupper():
        return token[:1].upper() + token[1:]
    return token


def _term_hits(text: str, *, blocked_terms: Sequence[str]) -> list[str]:
    hits: list[str] = []
    for term in blocked_terms:
        pattern = _PATTERNS.get(str(term).strip().lower())
        if pattern is None:
            continue
        if pattern.search(text):
            hits.append(str(term).strip().lower())
    return hits


def enforce_claim_text(
    text: Any,
    *,
    claim_guard: Mapping[str, Any] | Any = None,
    claim_lint: Mapping[str, Any] | Any = None,
    surface: str = "",
) -> dict[str, Any]:
    original_text = str(text or "")
    lint = _claim_lint_payload(claim_guard=claim_guard, claim_lint=claim_lint)
    blocked_terms = [
        str(token).strip().lower()
        for token in lint.get("blocked_terms", [])
        if str(token).strip()
    ] if isinstance(lint.get("blocked_terms"), list) else []
    replacement_hint = _normalize_string(lint.get("replacement_hint")) or "diagnosed"
    if not original_text or not blocked_terms:
        return {
            "surface": str(surface or "").strip(),
            "original_text": original_text,
            "text": original_text,
            "changed": False,
            "blocked_term_hits": [],
            "gate": dict(lint.get("gate", {})) if isinstance(lint.get("gate"), Mapping) else {},
            "forced_checks": list(lint.get("forced_checks", [])) if isinstance(lint.get("forced_checks"), list) else [],
            "highest_truthful_claim": _normalize_string(lint.get("highest_truthful_claim")) or replacement_hint,
            "verdict": "live_ok" if str(lint.get("status", "")).strip() == "live_ok" else "clean",
        }
    updated_text = original_text
    hits = _term_hits(original_text, blocked_terms=blocked_terms)
    for term in blocked_terms:
        pattern = _PATTERNS.get(term)
        if pattern is None:
            continue
        updated_text = pattern.sub(
            lambda match: _match_case(replacement=replacement_hint, original=match.group(0)),
            updated_text,
        )
    return {
        "surface": str(surface or "").strip(),
        "original_text": original_text,
        "text": updated_text,
        "changed": updated_text != original_text,
        "blocked_term_hits": hits,
        "gate": dict(lint.get("gate", {})) if isinstance(lint.get("gate"), Mapping) else {},
        "forced_checks": list(lint.get("forced_checks", [])) if isinstance(lint.get("forced_checks"), list) else [],
        "highest_truthful_claim": _normalize_string(lint.get("highest_truthful_claim")) or replacement_hint,
        "verdict": (
            "rewritten"
            if updated_text != original_text
            else "restricted"
        ),
    }


def enforce_claim_payload(
    payload: Mapping[str, Any] | Any,
    *,
    claim_guard: Mapping[str, Any] | Any = None,
    claim_lint: Mapping[str, Any] | Any = None,
    text_keys: Sequence[str] = ("text", "plain_text", "markdown_text"),
    surface: str = "",
) -> dict[str, Any]:
    row = dict(payload) if isinstance(payload, Mapping) else {}
    lint = _claim_lint_payload(claim_guard=claim_guard, claim_lint=claim_lint)
    enforcement_rows: list[dict[str, Any]] = []
    for key in text_keys:
        value = row.get(key)
        if not isinstance(value, str):
            continue
        result = enforce_claim_text(value, claim_lint=lint, surface=surface or key)
        row[key] = result["text"]
        if result["changed"] or result["blocked_term_hits"]:
            enforcement_rows.append(
                {
                    "field": key,
                    "blocked_term_hits": list(result.get("blocked_term_hits", [])),
                    "verdict": str(result.get("verdict", "")).strip(),
                }
            )
    row["claim_enforcement"] = {
        "surface": str(surface or "").strip(),
        "applied": bool(enforcement_rows),
        "results": enforcement_rows,
        "gate": dict(lint.get("gate", {})) if isinstance(lint.get("gate"), Mapping) else {},
        "forced_checks": list(lint.get("forced_checks", [])) if isinstance(lint.get("forced_checks"), list) else [],
        "highest_truthful_claim": _normalize_string(lint.get("highest_truthful_claim")) or "diagnosed",
    }
    return row
