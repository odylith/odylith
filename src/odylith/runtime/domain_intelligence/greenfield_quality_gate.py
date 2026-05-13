"""Fail-closed quality gates for greenfield proposal product content."""

from __future__ import annotations

from collections.abc import Mapping
import re
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_text import clean_text
from odylith.runtime.domain_intelligence.greenfield_text import text_values

_CONTROL_PLANE_LEAKS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("Radar", re.compile(r"\bRadar\b")),
    ("Registry", re.compile(r"\bRegistry\b")),
    ("Atlas", re.compile(r"\bAtlas\b")),
    ("Compass", re.compile(r"\bCompass\b")),
    ("Tribunal", re.compile(r"\bTribunal\b")),
    ("Odylith surfaces", re.compile(r"\bOdylith\s+surfaces\b", re.IGNORECASE)),
    ("Odylith owns", re.compile(r"\bOdylith\s+owns\b", re.IGNORECASE)),
    ("Odylith assumptions", re.compile(r"\bOdylith\s+assumptions\b", re.IGNORECASE)),
    ("governance surfaces", re.compile(r"\bgovernance\s+surfaces\b", re.IGNORECASE)),
    ("governance records", re.compile(r"\bgovernance\s+records\b", re.IGNORECASE)),
    ("surface refresh", re.compile(r"\bsurface\s+refresh\b", re.IGNORECASE)),
    ("refreshed surfaces", re.compile(r"\brefreshed\s+surfaces\b", re.IGNORECASE)),
    ("app-surface", re.compile(r"\bapp[-\s]+surface\b", re.IGNORECASE)),
    ("proof surface", re.compile(r"\bproof\s+surface\b", re.IGNORECASE)),
    ("governed control surface", re.compile(r"\bgoverned\s+control\s+surface\b", re.IGNORECASE)),
)

_STALE_GENERIC_TERMS: tuple[str, ...] = (
    "Experience Boundary",
    "Domain Core",
    "Verification Harness",
    "Project intelligence renderer",
    "Create or accept project truth",
    "Primary user",
    "Project operator",
    "Domain reviewer",
    "Implementation owner",
    "Evidence owner",
)

_GENERIC_ACTOR_LABELS: tuple[str, ...] = (
    "Operator",
    "Maintainer",
    "Reviewer",
    "Primary user",
    "Project operator",
    "Domain reviewer",
    "Implementation owner",
    "Evidence owner",
    "End-user advocate",
    "Workflow operator",
    "Risk reviewer",
    "Proof reviewer",
    "Build owner",
)

_DIRECTIVE_LEAKS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("show the interpretation", re.compile(r"\bshow\s+(?:the\s+)?interpretation\b", re.IGNORECASE)),
    ("show direction choices", re.compile(r"\bshow\s+(?:the\s+)?direction\s+choices\b", re.IGNORECASE)),
    ("do not write records", re.compile(r"\bdo\s+not\s+write\s+(?:any\s+)?records?\b", re.IGNORECASE)),
    ("until I confirm", re.compile(r"\buntil\s+i\s+confirm\b", re.IGNORECASE)),
    ("before I confirm", re.compile(r"\bbefore\s+i\s+confirm\b", re.IGNORECASE)),
    ("apply as-is", re.compile(r"\bapply\s+as[-\s]is\b", re.IGNORECASE)),
    ("greenfield propose", re.compile(r"\bgreenfield\s+propose\b", re.IGNORECASE)),
    ("repo-root", re.compile(r"--repo-root\b", re.IGNORECASE)),
)

_GOVERNANCE_PREP_PHRASES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("execution spine before source exists", re.compile(r"\bexecution\s+spine\s+before\s+source\s+exists\b", re.IGNORECASE)),
    ("trace to product intent", re.compile(r"\btrace\s+to\s+product\s+intent\b", re.IGNORECASE)),
    ("component, diagram, release gate framing", re.compile(r"\bcomponents?,\s*diagrams?,\s*release\s+gates?\b", re.IGNORECASE)),
    ("proposal-first product program", re.compile(r"\bproposal[-\s]first\s+product\s+program\b", re.IGNORECASE)),
    ("accepted product truth before artifacts", re.compile(r"\baccepted\s+product\s+truth\s+before\b", re.IGNORECASE)),
    ("accepted project story before artifacts", re.compile(r"\baccepted\s+project\s+story\s+before\b", re.IGNORECASE)),
)

_STALE_GENERIC_TITLES = {
    "define first operator workflow",
    "define domain contract and ownership",
    "add release proof and operations harness",
    "prove first product workflow",
    "define first domain contract",
    "prove release harness",
}

_SCAFFOLD_MARKERS: tuple[str, ...] = (
    "odylith_apply_ready_scaffold",
    "apply_ready_scaffold",
    "proposal_template",
    "canonical_proposal",
    "GreenfieldDomainProfile",
)

_EXCLUDED_PUBLIC_KEYS = {
    "accepted_aliases",
    "apply_commands",
    "classification",
    "component_id",
    "evidence_tier",
    "host_instruction",
    "host_independent_paths",
    "id",
    "intended_path",
    "kind",
    "link_state",
    "mode",
    "observed_source",
    "priority",
    "provider_calls",
    "artifact_derivation",
    "project_intelligence_binding",
    "qualification",
    "reasoning_contract",
    "reasoning_mode",
    "schema_version",
    "sizing",
    "slug",
    "source_html",
    "source_mmd",
    "source_png",
    "source_svg",
    "status",
    "watch_paths",
    "write_policy",
}

_EXCLUDED_KEY_SUFFIXES = (
    "_id",
    "_ids",
    "_path",
    "_paths",
    "_ref",
    "_refs",
    "_slug",
    "_slugs",
)

_TERM_STOPWORDS = {
    "a",
    "an",
    "and",
    "app",
    "application",
    "build",
    "create",
    "design",
    "draft",
    "for",
    "from",
    "govern",
    "governed",
    "greenfield",
    "help",
    "in",
    "into",
    "make",
    "me",
    "new",
    "of",
    "on",
    "platform",
    "product",
    "project",
    "proposal",
    "repo",
    "should",
    "system",
    "the",
    "to",
    "tool",
    "using",
    "with",
}

_SHORT_DOMAIN_TERMS = {"ai", "ml", "ui", "ux", "ar", "vr", "kyb", "aml", "smb", "crm", "erp"}


def greenfield_quality_issues(proposal: Mapping[str, Any]) -> list[str]:
    """Return greenfield product-quality failures that should block writes."""

    issues: list[str] = []
    public_leaves = list(_public_text_leaves(proposal))
    prompt_terms = _prompt_terms(proposal)
    issues.extend(_control_plane_leak_issues(public_leaves, prompt_terms=prompt_terms))
    issues.extend(_stale_generic_issues(public_leaves))
    issues.extend(_generic_actor_label_issues(public_leaves))
    issues.extend(_directive_leak_issues(public_leaves))
    issues.extend(_scaffold_marker_issues(public_leaves))
    issues.extend(_governance_prep_language_issues(proposal))
    if prompt_terms:
        issues.extend(_prompt_grounding_issues(proposal, prompt_terms=prompt_terms))
        issues.extend(_prompt_echo_issues(proposal, public_leaves=public_leaves))
    return _dedupe(issues)


def _control_plane_leak_issues(public_leaves: list[tuple[str, str]], *, prompt_terms: tuple[str, ...]) -> list[str]:
    issues: list[str] = []
    for label, pattern in _CONTROL_PLANE_LEAKS:
        if label in {"Radar", "Registry", "Atlas", "Compass", "Tribunal"} and _singular(label.casefold()) in prompt_terms:
            continue
        paths = [path for path, text in public_leaves if pattern.search(text)]
        if paths:
            issues.append(
                f"greenfield public product content leaks Odylith control-plane term `{label}` at {_path_preview(paths)}"
            )
    return issues


def _stale_generic_issues(public_leaves: list[tuple[str, str]]) -> list[str]:
    issues: list[str] = []
    for term in _STALE_GENERIC_TERMS:
        paths = [path for path, text in public_leaves if term in text]
        if paths:
            issues.append(f"greenfield public product content reuses stale generic label `{term}` at {_path_preview(paths)}")
    return issues


def _generic_actor_label_issues(public_leaves: list[tuple[str, str]]) -> list[str]:
    issues: list[str] = []
    for label in _GENERIC_ACTOR_LABELS:
        paths = [
            path
            for path, text in public_leaves
            if _starts_with_generic_actor_label(text, label)
        ]
        if paths:
            issues.append(
                f"greenfield public product content uses generic actor label `{label}` instead of a project-specific actor at {_path_preview(paths)}"
            )
    return issues


def _starts_with_generic_actor_label(text: str, label: str) -> bool:
    """Reject placeholder actor rows without rejecting domain-specific owners."""

    cleaned = clean_text(text)
    return bool(re.match(rf"^{re.escape(label)}(?:\s|:|[-–—]|$)", cleaned))


def _directive_leak_issues(public_leaves: list[tuple[str, str]]) -> list[str]:
    issues: list[str] = []
    for label, pattern in _DIRECTIVE_LEAKS:
        paths = [path for path, text in public_leaves if pattern.search(text)]
        if paths:
            issues.append(
                f"greenfield public product content leaks operator instruction `{label}` into product records at {_path_preview(paths)}"
            )
    return issues


def _scaffold_marker_issues(public_leaves: list[tuple[str, str]]) -> list[str]:
    issues: list[str] = []
    for marker in _SCAFFOLD_MARKERS:
        paths = [path for path, text in public_leaves if marker in text]
        if paths:
            issues.append(f"greenfield public product content exposes scaffold marker `{marker}` at {_path_preview(paths)}")
    return issues


def _prompt_grounding_issues(proposal: Mapping[str, Any], *, prompt_terms: tuple[str, ...]) -> list[str]:
    issues: list[str] = []
    backlog = proposal.get("backlog")
    if isinstance(backlog, list):
        for index, row in enumerate(backlog, start=1):
            if not isinstance(row, Mapping):
                continue
            title = clean_text(row.get("title"))
            if title.casefold() in _STALE_GENERIC_TITLES:
                issues.append(f"backlog row {index} uses stale generic title `{title}`")
            if not _has_prompt_term(_grounding_text(row), prompt_terms):
                issues.append(
                    f"backlog row {index} `{title or '<untitled>'}` is not grounded in prompt-specific terms "
                    f"such as {_term_preview(prompt_terms)}"
                )
    components = proposal.get("components")
    if isinstance(components, list):
        for index, row in enumerate(components, start=1):
            if not isinstance(row, Mapping):
                continue
            label = clean_text(row.get("label"))
            if label.casefold() in {"operator workspace", "product model", "evidence harness"}:
                issues.append(f"component row {index} uses generic label `{label}` without the project noun")
            if not _has_prompt_term(_grounding_text(row), prompt_terms):
                issues.append(
                    f"component row {index} `{label or '<unlabeled>'}` is not grounded in prompt-specific terms "
                    f"such as {_term_preview(prompt_terms)}"
                )
    issues.extend(_top_level_grounding_issues(proposal, prompt_terms=prompt_terms))
    return issues


def _top_level_grounding_issues(proposal: Mapping[str, Any], *, prompt_terms: tuple[str, ...]) -> list[str]:
    checks = (
        ("project_brief", proposal.get("project_brief"), ("purpose", "project_outcome", "operating_principle")),
        ("project_intelligence", proposal.get("project_intelligence"), ("purpose", "coding_posture", "control_surface_summary")),
        ("program", proposal.get("program"), ("recommended_first_wave", "blueprint", "waves")),
        ("release_plan", proposal.get("release_plan"), ("label", "strategy", "milestones", "promotion_criteria")),
    )
    issues: list[str] = []
    for label, value, keys in checks:
        if not isinstance(value, Mapping):
            continue
        text = " ".join(str(nested or "") for key in keys for nested in text_values(value.get(key))).casefold()
        if text and not _has_prompt_term(text, prompt_terms):
            issues.append(
                f"proposal `{label}` is not grounded in prompt-specific terms such as {_term_preview(prompt_terms)}"
            )
    return issues


def _governance_prep_language_issues(proposal: Mapping[str, Any]) -> list[str]:
    issues: list[str] = []
    backlog = proposal.get("backlog")
    if not isinstance(backlog, list):
        return issues
    checked_fields = ("title", "problem", "customer", "opportunity", "product_view", "recommended_first_slice")
    for index, row in enumerate(backlog, start=1):
        if not isinstance(row, Mapping):
            continue
        text = " ".join(clean_text(row.get(field)) for field in checked_fields)
        for label, pattern in _GOVERNANCE_PREP_PHRASES:
            if pattern.search(text):
                issues.append(
                    f"backlog row {index} uses governance-prep phrase `{label}` where product/business language is required"
                )
    return issues


def _prompt_echo_issues(
    proposal: Mapping[str, Any],
    *,
    public_leaves: list[tuple[str, str]],
) -> list[str]:
    intent = proposal.get("intent")
    if not isinstance(intent, Mapping):
        return []
    raw_prompt = clean_text(intent.get("prompt"))
    raw_title = clean_text(intent.get("title"))
    issues: list[str] = []
    for label, value, max_hits in (("prompt", raw_prompt, 0), ("title", raw_title, 3)):
        needle = value.casefold()
        if len(needle) < 32:
            continue
        paths = [
            path
            for path, text in public_leaves
            if needle
            and needle in text.casefold()
            and not path.startswith("intent.")
            and _is_artifact_content_path(path)
        ]
        if len(paths) > max_hits:
            issues.append(
                f"greenfield public product content repeats the raw {label} instead of authoring natural project language at {_path_preview(paths)}"
            )
    return issues


def _is_artifact_content_path(path: str) -> bool:
    return path.startswith(("backlog.", "components.", "diagrams.", "program.", "release_plan."))


def _public_text_leaves(value: Any, *, path: tuple[str, ...] = ()) -> tuple[tuple[str, str], ...]:
    if isinstance(value, Mapping):
        rows: list[tuple[str, str]] = []
        for key, nested in value.items():
            key_text = str(key)
            if _is_excluded_public_key(key_text):
                continue
            rows.extend(_public_text_leaves(nested, path=(*path, key_text)))
        return tuple(rows)
    if isinstance(value, (list, tuple, set)):
        rows = []
        for index, nested in enumerate(value):
            rows.extend(_public_text_leaves(nested, path=(*path, str(index))))
        return tuple(rows)
    text = clean_text(value)
    return ((".".join(path) or "<root>", text),) if text else ()


def _is_excluded_public_key(key: str) -> bool:
    lowered = key.casefold()
    if lowered == "mermaid_source":
        return False
    return lowered in _EXCLUDED_PUBLIC_KEYS or lowered.endswith(_EXCLUDED_KEY_SUFFIXES)


def _grounding_text(row: Mapping[str, Any]) -> str:
    return " ".join(text_values(row)).casefold()


def _prompt_terms(proposal: Mapping[str, Any]) -> tuple[str, ...]:
    intent = proposal.get("intent")
    values: list[str] = []
    if isinstance(intent, Mapping):
        values.extend(
            clean_text(intent.get(key))
            for key in ("prompt", "title", "summary")
            if clean_text(intent.get(key))
        )
    return _meaningful_terms(" ".join(values))


def _meaningful_terms(text: str) -> tuple[str, ...]:
    seen: set[str] = set()
    terms: list[str] = []
    for raw in re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]*", text.casefold()):
        token = raw.strip("-_")
        if not token or token in _TERM_STOPWORDS:
            continue
        if len(token) < 3 and token not in _SHORT_DOMAIN_TERMS:
            continue
        normalized = _singular(token)
        if normalized in _TERM_STOPWORDS or normalized in seen:
            continue
        seen.add(normalized)
        terms.append(normalized)
    return tuple(terms[:12])


def _has_prompt_term(text: str, prompt_terms: tuple[str, ...]) -> bool:
    haystack = text.casefold()
    return any(_term_in_text(term, haystack) for term in prompt_terms)


def _term_in_text(term: str, haystack: str) -> bool:
    variants = {term, _singular(term)}
    if term.endswith("y"):
        variants.add(f"{term[:-1]}ies")
    if term.endswith("s"):
        variants.add(term[:-1])
    else:
        variants.add(f"{term}s")
    return any(re.search(rf"(?<![a-z0-9]){re.escape(variant)}(?![a-z0-9])", haystack) for variant in variants)


def _singular(token: str) -> str:
    if token.endswith("ies") and len(token) > 4:
        return f"{token[:-3]}y"
    if token.endswith("s") and len(token) > 3 and not token.endswith("ss"):
        return token[:-1]
    return token


def _path_preview(paths: list[str]) -> str:
    preview = ", ".join(paths[:3])
    if len(paths) > 3:
        preview = f"{preview}, +{len(paths) - 3} more"
    return preview


def _term_preview(terms: tuple[str, ...]) -> str:
    return ", ".join(terms[:5])


def _dedupe(issues: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for issue in issues:
        token = clean_text(issue)
        if not token or token in seen:
            continue
        seen.add(token)
        result.append(token)
    return result


__all__ = ["greenfield_quality_issues"]
