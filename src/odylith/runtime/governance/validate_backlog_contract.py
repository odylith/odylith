"""Validate backlog contracts and backlog-to-plan linkage.

This checker is intentionally strict and fail-closed for consumer backlog
workflow artifacts.
"""

from __future__ import annotations

import argparse
import copy
import datetime as dt
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from odylith.runtime.common.consumer_profile import consumer_profile_path, truth_root_path
from odylith.runtime.governance import backlog_title_contract
from odylith.runtime.governance import execution_wave_contract
from odylith.runtime.governance import release_planning_contract
from odylith.runtime.context_engine import odylith_context_cache

_REQUIRED_METADATA: tuple[str, ...] = (
    "date",
    "priority",
    "commercial_value",
    "product_impact",
    "market_value",
    "impacted_parts",
    "sizing",
    "complexity",
    "ordering_score",
    "ordering_rationale",
)

_REQUIRED_SECTIONS: tuple[str, ...] = (
    "Problem",
    "Customer",
    "Opportunity",
    "Proposed Solution",
    "Scope",
    "Non-Goals",
    "Risks",
    "Dependencies",
    "Success Metrics",
    "Validation",
    "Rollout",
    "Why Now",
    "Product View",
    "Impacted Components",
    "Interface Changes",
    "Migration/Compatibility",
    "Test Strategy",
    "Open Questions",
)
_CORE_DETAIL_SECTION_TITLES: tuple[str, ...] = (
    "Problem",
    "Customer",
    "Opportunity",
    "Product View",
    "Success Metrics",
)
IDEA_SPEC_CACHE_VERSION = "v2-section-bodies"
_PLACEHOLDER_LIKE_TOKENS: frozenset[str] = frozenset(
    {
        "details",
        "details.",
        "tbd",
        "tbd.",
        "todo",
        "todo.",
        "n/a",
        "na",
        "none",
        "-",
    }
)
_MIN_CORE_DETAIL_WORDS = 6

_VALID_PRIORITIES: set[str] = {"P0", "P1", "P2", "P3"}
_VALID_SIZING: dict[str, int] = {"XS": 1, "S": 2, "M": 3, "L": 5, "XL": 8}
_VALID_COMPLEXITY: dict[str, int] = {"Low": 1, "Medium": 2, "High": 3, "VeryHigh": 5}
_VALID_STATUS: set[str] = {
    "queued",
    "planning",
    "implementation",
    "finished",
    "parked",
    "superseded",
}
_YES_NO: set[str] = {"yes", "no"}
_ACTIVE_STATUSES: set[str] = {"queued"}
_EXECUTION_STATUSES: set[str] = {"planning", "implementation"}
_PARKED_STATUSES: set[str] = {"parked"}
_FINISHED_STATUSES: set[str] = {"finished"}

_INDEX_COLS: tuple[str, ...] = (
    "rank",
    "idea_id",
    "title",
    "priority",
    "ordering_score",
    "commercial_value",
    "product_impact",
    "market_value",
    "sizing",
    "complexity",
    "status",
    "link",
)
_LEGACY_INDEX_COLS_WITH_LANES: tuple[str, ...] = (
    "rank",
    "idea_id",
    "title",
    "priority",
    "ordering_score",
    "commercial_value",
    "product_impact",
    "market_value",
    "sizing",
    "complexity",
    "impacted_lanes",
    "status",
    "link",
)
_LEGACY_METADATA_FIELDS: tuple[str, ...] = ("impacted_lanes",)

_PLAN_COLS: tuple[str, ...] = ("Plan", "Status", "Created", "Updated", "Backlog")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_SECTION_RE = re.compile(r"^##\s+(.+?)\s*$")
_LINK_RE = re.compile(r"^\[.+\]\((?P<target>[^)]+)\)$")
_IDEA_ID_RE = re.compile(r"^B-(?P<num>\d{3,})$")
_IDEA_FILE_RE = re.compile(r"^(?P<date>\d{4}-\d{2}-\d{2})-(?P<slug>[a-z0-9][a-z0-9-]*)$")
_REVIEW_DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
_UPDATE_STAMP_RE = re.compile(r"^Last updated \(UTC\):\s*(?P<date>\d{4}-\d{2}-\d{2})\s*$", re.M)
_STOPWORDS: set[str] = {"and", "for", "the", "with", "from", "into", "only", "global"}
_EXECUTION_SECTION_TITLES: tuple[str, ...] = (
    "In Planning/Implementation (Linked to `odylith/technical-plans/in-progress`)",
    "In Planning/Implementation (Linked to `odylith/technical-plans/in-progress` or an active parent wave)",
    "Promoted (In `odylith/technical-plans/in-progress`)",
)
_PARKED_SECTION_TITLE = "Parked (No Active Plan)"
_FINISHED_SECTION_TITLE = "Finished (Linked to `odylith/technical-plans/done`)"
_PARKED_PLAN_SECTION_TITLE = "Parked Plans"
_EXECUTION_STATUS_ORDER: dict[str, int] = {
    "implementation": 0,
    "planning": 1,
}
_LINEAGE_SINGLE_FIELDS: tuple[str, ...] = (
    "workstream_reopens",
    "workstream_reopened_by",
    "workstream_split_from",
    "workstream_merged_into",
)
_LINEAGE_MULTI_FIELDS: tuple[str, ...] = (
    "workstream_split_into",
    "workstream_merged_from",
)


@dataclass(frozen=True)
class IdeaSpec:
    path: Path
    metadata: dict[str, str]
    sections: set[str]
    section_bodies: dict[str, str]

    @property
    def idea_id(self) -> str:
        return self.metadata.get("idea_id", "").strip()

    @property
    def status(self) -> str:
        return self.metadata.get("status", "").strip()

    @property
    def founder_override(self) -> bool:
        return self.metadata.get("founder_override", "no").strip().lower() == "yes"


@dataclass
class ReorderRationaleSection:
    heading: str
    lines: list[str]

    def __iter__(self):  # pragma: no cover - compatibility shim for UI renderer
        return iter(self.lines)


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate backlog contracts")
    parser.add_argument("--repo-root", default=".", help="Repository root path")
    parser.add_argument("--ideas-root", default="odylith/radar/source/ideas", help="Backlog ideas root")
    parser.add_argument("--backlog-index", default="odylith/radar/source/INDEX.md", help="Backlog index path")
    parser.add_argument("--plan-index", default="odylith/technical-plans/INDEX.md", help="Plan index path")
    return parser.parse_args(argv)


def _resolve_repo_path(*, repo_root: Path, token: str) -> Path:
    raw = str(token or "").strip()
    path = Path(raw)
    if path.is_absolute():
        return path.resolve()
    return (repo_root / path).resolve()


def _infer_repo_root_from_path(path: Path) -> Path | None:
    target = Path(path).resolve()
    from odylith.runtime.governance import sync_session as governed_sync_session

    session = governed_sync_session.active_sync_session()
    if session is not None:
        session_root = session.repo_root_for_path(target)
        if session_root is not None:
            return session_root
    search_roots = [target, *target.parents]
    for candidate in search_roots:
        try:
            if consumer_profile_path(repo_root=candidate).is_file():
                return candidate
            radar_root = truth_root_path(repo_root=candidate, key="radar_source")
            plans_root = truth_root_path(repo_root=candidate, key="technical_plans")
            if (radar_root / "INDEX.md").is_file() and (plans_root / "INDEX.md").is_file():
                return candidate
        except OSError:
            continue
    return None


def _resolve_equivalent_repo_link(
    *,
    repo_root: Path,
    target: str,
    expected_path: Path,
) -> tuple[Path, bool]:
    """Resolve a backlog link against the current repo when possible.

    The canonical backlog contract now uses repo-relative links so clean
    checkouts stay portable across machines and CI workers. We still accept
    legacy absolute links when rebasing them through another detected repo root
    lands on the same expected repo-relative path in the current checkout.
    """

    repo_root_resolved = repo_root.resolve()
    expected_path_resolved = expected_path.resolve()
    raw_target = str(target or "").strip()
    path_token = Path(raw_target)
    if not path_token.is_absolute():
        link_path = (repo_root_resolved / path_token).resolve()
        try:
            link_path.relative_to(repo_root_resolved)
        except ValueError:
            return link_path, False
        return link_path, True

    link_path = path_token.resolve()
    try:
        link_path.relative_to(repo_root_resolved)
    except ValueError:
        pass
    else:
        return link_path, True

    linked_repo_root = _infer_repo_root_from_path(link_path)
    if linked_repo_root is None:
        return link_path, False

    try:
        relative_target = link_path.relative_to(linked_repo_root.resolve())
    except ValueError:
        return link_path, False

    rebased_path = (repo_root_resolved / relative_target).resolve()
    if rebased_path != expected_path_resolved:
        return link_path, False
    return rebased_path, True


def _repo_relative_cache_key(*, repo_root: Path, target: Path) -> str:
    try:
        return target.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return str(target.resolve())


def _idea_spec_payload(spec: IdeaSpec) -> dict[str, Any]:
    return {
        "metadata": dict(spec.metadata),
        "sections": sorted(spec.sections),
        "section_bodies": dict(spec.section_bodies),
    }


def _idea_spec_from_payload(*, path: Path, payload: Mapping[str, Any]) -> IdeaSpec:
    metadata_raw = payload.get("metadata", {})
    metadata = dict(metadata_raw) if isinstance(metadata_raw, Mapping) else {}
    sections_raw = payload.get("sections", [])
    sections = {
        str(token).strip()
        for token in sections_raw
        if str(token).strip()
    }
    section_bodies_raw = payload.get("section_bodies", {})
    section_bodies = (
        {
            str(key).strip(): str(value).strip()
            for key, value in section_bodies_raw.items()
            if str(key).strip()
        }
        if isinstance(section_bodies_raw, Mapping)
        else {}
    )
    return IdeaSpec(path=path, metadata=metadata, sections=sections, section_bodies=section_bodies)


def _idea_spec_signature_token(signature: Mapping[str, Any]) -> str:
    return ":".join(
        (
            "1" if bool(signature.get("exists")) else "0",
            str(signature.get("kind", "")).strip(),
            str(int(signature.get("size", 0) or 0)),
            str(int(signature.get("mtime_ns", 0) or 0)),
        )
    )


def default_section_boilerplate(title: str) -> dict[str, str]:
    plain_title = str(title).strip()
    return {
        "Problem": f"Odylith needs an explicit workstream for {plain_title} instead of leaving the slice implicit.",
        "Customer": "Odylith maintainers and operators who need this capability to exist as governed product truth.",
        "Opportunity": f"Bound {plain_title} as a queued workstream so implementation can attach to one clear source record.",
        "Proposed Solution": f"Create the workstream for {plain_title} and refine the exact implementation plan during execution.",
        "Scope": f"- Define and land the bounded work for {plain_title}.\n- Keep the first implementation wave narrow and test-backed.",
        "Non-Goals": "- Do not widen this queued workstream into unrelated product cleanup.",
        "Risks": "- The title may need refinement once the implementation owner confirms the exact boundary.",
        "Dependencies": "- No explicit dependency recorded yet; confirm related workstreams before implementation starts.",
        "Success Metrics": "- The workstream is specific enough to guide implementation and validation without further backlog surgery.",
        "Validation": "- Run focused validation for the touched paths once implementation begins.",
        "Rollout": "- Queue now, then bind a technical plan when the implementation wave starts.",
        "Why Now": "This slice is active enough that it should exist as explicit backlog truth now.",
        "Product View": "If the team is already acting as if this work exists, the backlog should say so explicitly.",
        "Impacted Components": "- `odylith`",
        "Interface Changes": "- None decided yet; record interface changes once implementation is scoped.",
        "Migration/Compatibility": "- No migration impact recorded yet.",
        "Test Strategy": "- Add targeted regression coverage when implementation begins.",
        "Open Questions": "- Which existing workstreams or component specs should this attach to first?",
    }


def _normalize_section_body_text(value: str) -> str:
    return "\n".join(line.rstrip() for line in str(value or "").strip().splitlines()).strip()


def _is_placeholder_like_section_body(value: str) -> bool:
    token = _normalize_section_body_text(value).casefold()
    return token in _PLACEHOLDER_LIKE_TOKENS


def _meaningful_word_count(value: str) -> int:
    return len(re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]*", _normalize_section_body_text(value)))


def core_detail_section_errors(
    *,
    title: str,
    sections: Mapping[str, str],
    path: Path,
) -> list[str]:
    errors: list[str] = []
    defaults = default_section_boilerplate(title)
    for section in _CORE_DETAIL_SECTION_TITLES:
        body = _normalize_section_body_text(str(sections.get(section, "")).strip())
        if not body:
            errors.append(f"{path}: core detail section `## {section}` must be non-empty")
            continue
        if _is_placeholder_like_section_body(body):
            errors.append(f"{path}: core detail section `## {section}` uses placeholder-like text")
            continue
        if _meaningful_word_count(body) < _MIN_CORE_DETAIL_WORDS:
            errors.append(
                f"{path}: core detail section `## {section}` must contain at least "
                f"{_MIN_CORE_DETAIL_WORDS} meaningful words"
            )
            continue
        if body == _normalize_section_body_text(defaults.get(section, "")):
            errors.append(f"{path}: core detail section `## {section}` still uses backlog-create boilerplate")
    return errors


def _parse_idea_spec_uncached(
    *,
    target: Path,
    repo_root: Path | None,
    signature: Mapping[str, Any],
) -> IdeaSpec:
    resolved_repo_root = Path(repo_root).resolve() if repo_root is not None else None
    if resolved_repo_root is not None:
        cache_file = odylith_context_cache.cache_path(
            repo_root=resolved_repo_root,
            namespace="backlog/idea-specs",
            key=_repo_relative_cache_key(repo_root=resolved_repo_root, target=target),
        )
        cached = odylith_context_cache.read_json_object(cache_file)
        cached_spec = cached.get("spec")
        if (
            cached.get("version") == IDEA_SPEC_CACHE_VERSION
            and cached.get("signature") == signature
            and isinstance(cached_spec, Mapping)
            and isinstance(cached_spec.get("section_bodies"), Mapping)
        ):
            return _idea_spec_from_payload(path=target, payload=cached_spec)

    metadata: dict[str, str] = {}
    sections: set[str] = set()
    section_bodies: dict[str, list[str]] = {}
    in_metadata = True
    current_section: str | None = None

    for raw_line in target.read_text(encoding="utf-8").splitlines():
        match = _SECTION_RE.match(raw_line)
        if match:
            in_metadata = False
            section_title = str(match.group(1)).strip()
            if section_title == "Founder POV":
                section_title = "Product View"
            sections.add(section_title)
            current_section = section_title
            section_bodies.setdefault(section_title, [])
            continue

        if not in_metadata:
            if current_section is not None:
                section_bodies.setdefault(current_section, []).append(raw_line)
            continue

        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip()

    spec = IdeaSpec(
        path=target,
        metadata=metadata,
        sections=sections,
        section_bodies={
            key: _normalize_section_body_text("\n".join(lines))
            for key, lines in section_bodies.items()
        },
    )
    if resolved_repo_root is not None:
        odylith_context_cache.write_json_if_changed(
            repo_root=resolved_repo_root,
            path=cache_file,
            payload={
                "version": IDEA_SPEC_CACHE_VERSION,
                "signature": signature,
                "spec": _idea_spec_payload(spec),
            },
            lock_key=str(cache_file),
        )
    return spec


def _parse_idea_spec(path: Path) -> IdeaSpec:
    target = path.resolve()
    from odylith.runtime.governance import sync_session as governed_sync_session

    session = governed_sync_session.active_sync_session()
    repo_root = session.repo_root_for_path(target) if session is not None else None
    if repo_root is None:
        repo_root = _infer_repo_root_from_path(target)
    signature = odylith_context_cache.path_signature(target)
    if session is not None and repo_root is not None and session.repo_root == repo_root:
        return session.get_or_compute(
            namespace="idea_spec",
            key=f"{target.as_posix()}\n{_idea_spec_signature_token(signature)}",
            builder=lambda: _parse_idea_spec_uncached(
                target=target,
                repo_root=repo_root,
                signature=signature,
            ),
        )
    return _parse_idea_spec_uncached(target=target, repo_root=repo_root, signature=signature)


def _parse_int_in_range(
    *,
    value: str,
    field: str,
    low: int,
    high: int,
    errors: list[str],
    path: Path,
) -> int | None:
    token = str(value or "").strip()
    if not token:
        errors.append(f"{path}: missing `{field}`")
        return None
    try:
        parsed = int(token)
    except ValueError:
        errors.append(f"{path}: `{field}` must be an integer, got `{token}`")
        return None
    if parsed < low or parsed > high:
        errors.append(f"{path}: `{field}` out of range [{low}, {high}], got `{parsed}`")
        return None
    return parsed


def _compute_score(metadata: dict[str, str], *, errors: list[str], path: Path) -> int | None:
    commercial = _parse_int_in_range(
        value=metadata.get("commercial_value", ""),
        field="commercial_value",
        low=1,
        high=5,
        errors=errors,
        path=path,
    )
    product = _parse_int_in_range(
        value=metadata.get("product_impact", ""),
        field="product_impact",
        low=1,
        high=5,
        errors=errors,
        path=path,
    )
    market = _parse_int_in_range(
        value=metadata.get("market_value", ""),
        field="market_value",
        low=1,
        high=5,
        errors=errors,
        path=path,
    )
    sizing = str(metadata.get("sizing", "")).strip()
    complexity = str(metadata.get("complexity", "")).strip()
    if sizing not in _VALID_SIZING:
        errors.append(f"{path}: `sizing` must be one of {sorted(_VALID_SIZING)}, got `{sizing}`")
        return None
    if complexity not in _VALID_COMPLEXITY:
        errors.append(
            f"{path}: `complexity` must be one of {sorted(_VALID_COMPLEXITY)}, got `{complexity}`"
        )
        return None
    if commercial is None or product is None or market is None:
        return None

    opportunity = (0.40 * commercial) + (0.35 * product) + (0.25 * market)
    execution_drag = (0.60 * _VALID_SIZING[sizing]) + (0.40 * _VALID_COMPLEXITY[complexity])
    raw_score = (opportunity / execution_drag) * 100
    rounded = int(raw_score + 0.5)
    return max(0, min(100, rounded))


def _collect_section_table(content: str, section_title: str) -> tuple[list[str], list[list[str]], str | None]:
    lines = content.splitlines()
    start = -1
    target = f"## {section_title}"
    for idx, line in enumerate(lines):
        if line.strip() == target:
            start = idx + 1
            break
    if start == -1:
        return [], [], f"missing section `{target}`"

    section_lines: list[str] = []
    for line in lines[start:]:
        if line.startswith("## "):
            break
        section_lines.append(line)

    rows: list[list[str]] = []
    for raw in section_lines:
        stripped = raw.strip()
        if not stripped.startswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.split("|")[1:-1]]
        if not cells:
            continue
        if all(re.fullmatch(r"-+", token or "") for token in cells):
            continue
        rows.append(cells)

    if not rows:
        return [], [], f"section `{target}` has no table rows"
    headers = rows[0]
    return headers, rows[1:], None


def _collect_first_available_section_table(
    *,
    content: str,
    section_titles: Sequence[str],
) -> tuple[str | None, list[str], list[list[str]], str | None]:
    first_error: str | None = None
    for section_title in section_titles:
        headers, rows, error = _collect_section_table(content, section_title)
        if error is None:
            return section_title, headers, rows, None
        if first_error is None:
            first_error = error
    return None, [], [], first_error


def _parse_link_target(cell: str) -> str | None:
    token = str(cell or "").strip()
    if not token:
        return None
    match = _LINK_RE.match(token)
    if not match:
        return None
    return str(match.group("target")).strip()


def _strip_inline_code(cell: str) -> str:
    token = str(cell or "").strip()
    if token.startswith("`") and token.endswith("`") and len(token) >= 2:
        return token[1:-1].strip()
    return token


def _normalize_title_tokens(title: str) -> set[str]:
    tokens = {
        token
        for token in re.findall(r"[a-z0-9]+", str(title or "").lower())
        if len(token) >= 3 and token not in _STOPWORDS
    }
    return tokens


def _jaccard_similarity(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)


def _extract_reorder_log_sections(
    content: str,
) -> tuple[dict[str, ReorderRationaleSection], list[str]]:
    errors: list[str] = []
    lines = content.splitlines()
    start = -1
    for idx, line in enumerate(lines):
        if line.strip() == "## Reorder Rationale Log":
            start = idx + 1
            break
    if start == -1:
        return {}, ["missing section `## Reorder Rationale Log`"]

    sections: dict[str, ReorderRationaleSection] = {}
    current_key: str | None = None
    for line in lines[start:]:
        if line.startswith("## "):
            break
        if line.startswith("### "):
            heading = line[4:].strip()
            key = heading.split(" ", 1)[0].strip()
            if not key:
                errors.append("reorder rationale entry has empty heading")
                current_key = None
                continue
            sections[key] = ReorderRationaleSection(heading=heading, lines=[])
            current_key = key
            continue
        if current_key is not None:
            sections[current_key].lines.append(line)
    return sections, errors


def _table_snapshot_payload(
    *,
    section_title: str,
    headers: Sequence[str],
    rows: Sequence[Sequence[str]],
    error: str | None,
) -> dict[str, Any]:
    return {
        "section_title": str(section_title),
        "headers": [str(cell) for cell in headers],
        "rows": [[str(cell) for cell in row] for row in rows],
        "error": str(error).strip() if error else "",
    }


def _table_snapshot_from_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    headers_raw = payload.get("headers", [])
    rows_raw = payload.get("rows", [])
    error_value = payload.get("error", "")
    error = ""
    if error_value not in (None, ""):
        error = str(error_value).strip()
    return {
        "section_title": str(payload.get("section_title", "")).strip(),
        "headers": [str(cell) for cell in headers_raw] if isinstance(headers_raw, list) else [],
        "rows": [
            [str(cell) for cell in row]
            for row in rows_raw
            if isinstance(row, list)
        ],
        "error": error,
    }


def _normalized_optional_text(value: Any) -> str:
    """Return a stable string for optional snapshot scalars.

    Cached section payloads may store missing errors as `None`. Treat that as an
    empty string instead of the literal `"None"` so cache rebuilds do not
    poison contract validation.
    """

    if value is None:
        return ""
    return str(value).strip()


def _read_cached_snapshot(
    *,
    path: Path,
    namespace: str,
) -> tuple[Path | None, dict[str, Any] | None]:
    repo_root = _infer_repo_root_from_path(path)
    if repo_root is None:
        return None, None
    cache_file = odylith_context_cache.cache_path(
        repo_root=repo_root,
        namespace=namespace,
        key=_repo_relative_cache_key(repo_root=repo_root, target=path),
    )
    cached = odylith_context_cache.read_json_object(cache_file)
    if cached.get("version") != "v1":
        return cache_file, None
    if cached.get("signature") != odylith_context_cache.path_signature(path):
        return cache_file, None
    snapshot = cached.get("snapshot")
    if not isinstance(snapshot, Mapping):
        return cache_file, None
    return cache_file, dict(snapshot)


def _write_cached_snapshot(
    *,
    path: Path,
    namespace: str,
    snapshot: Mapping[str, Any],
) -> None:
    repo_root = _infer_repo_root_from_path(path)
    if repo_root is None:
        return
    cache_file = odylith_context_cache.cache_path(
        repo_root=repo_root,
        namespace=namespace,
        key=_repo_relative_cache_key(repo_root=repo_root, target=path),
    )
    odylith_context_cache.write_json_if_changed(
        repo_root=repo_root,
        path=cache_file,
        payload={
            "version": "v1",
            "signature": odylith_context_cache.path_signature(path),
            "snapshot": dict(snapshot),
        },
        lock_key=str(cache_file),
    )


def _build_backlog_index_snapshot(backlog_index: Path) -> dict[str, Any]:
    content = backlog_index.read_text(encoding="utf-8")
    stamp_match = _UPDATE_STAMP_RE.search(content)
    updated_utc = str(stamp_match.group("date")).strip() if stamp_match is not None else ""
    active_headers, active_rows, active_err = _collect_section_table(content, "Ranked Active Backlog")
    (
        execution_section_title,
        execution_headers,
        execution_rows,
        execution_err,
    ) = _collect_first_available_section_table(
        content=content,
        section_titles=_EXECUTION_SECTION_TITLES,
    )
    finished_headers, finished_rows, finished_err = _collect_section_table(content, _FINISHED_SECTION_TITLE)
    parked_headers, parked_rows, parked_err = _collect_section_table(content, _PARKED_SECTION_TITLE)
    rationale_sections, rationale_errors = _extract_reorder_log_sections(content)
    return {
        "updated_utc": updated_utc,
        "active": _table_snapshot_payload(
            section_title="Ranked Active Backlog",
            headers=active_headers,
            rows=active_rows,
            error=active_err,
        ),
        "execution": _table_snapshot_payload(
            section_title=str(execution_section_title or _EXECUTION_SECTION_TITLES[0]),
            headers=execution_headers,
            rows=execution_rows,
            error=execution_err,
        ),
        "finished": _table_snapshot_payload(
            section_title=_FINISHED_SECTION_TITLE,
            headers=finished_headers,
            rows=finished_rows,
            error=finished_err,
        ),
        "parked": _table_snapshot_payload(
            section_title=_PARKED_SECTION_TITLE,
            headers=parked_headers,
            rows=parked_rows,
            error=parked_err,
        ),
        "reorder_sections": {
            key: {
                "heading": section.heading,
                "lines": list(section.lines),
            }
            for key, section in rationale_sections.items()
        },
        "reorder_errors": list(rationale_errors),
    }


def load_backlog_index_snapshot(backlog_index: Path) -> dict[str, Any]:
    """Return a cached parsed snapshot for `odylith/radar/source/INDEX.md`."""

    target = backlog_index.resolve()
    from odylith.runtime.governance import sync_session as governed_sync_session

    session = governed_sync_session.active_sync_session()
    if session is not None:
        repo_root = session.repo_root_for_path(target)
        if repo_root is not None:
            signature = odylith_context_cache.path_signature(target)
            snapshot = session.get_or_compute(
                namespace="backlog_index_snapshot",
                key=f"{target.as_posix()}\n{signature.get('mtime_ns', 0)}\n{signature.get('size', 0)}",
                builder=lambda: load_backlog_index_snapshot_uncached(target),
            )
            return copy.deepcopy(snapshot)
    return load_backlog_index_snapshot_uncached(target)


def load_backlog_index_snapshot_uncached(backlog_index: Path) -> dict[str, Any]:
    target = backlog_index.resolve()
    _cache_file, cached = _read_cached_snapshot(path=target, namespace="backlog/index")
    if cached is not None:
        return {
            "updated_utc": str(cached.get("updated_utc", "")).strip(),
            "active": _table_snapshot_from_payload(cached.get("active", {})) if isinstance(cached.get("active"), Mapping) else _table_snapshot_from_payload({}),
            "execution": _table_snapshot_from_payload(cached.get("execution", {})) if isinstance(cached.get("execution"), Mapping) else _table_snapshot_from_payload({}),
            "finished": _table_snapshot_from_payload(cached.get("finished", {})) if isinstance(cached.get("finished"), Mapping) else _table_snapshot_from_payload({}),
            "parked": _table_snapshot_from_payload(cached.get("parked", {})) if isinstance(cached.get("parked"), Mapping) else _table_snapshot_from_payload({}),
            "reorder_sections": {
                str(key): {
                    "heading": str(value.get("heading", "")).strip(),
                    "lines": [str(line) for line in value.get("lines", [])] if isinstance(value, Mapping) else [],
                }
                for key, value in cached.get("reorder_sections", {}).items()
            }
            if isinstance(cached.get("reorder_sections"), Mapping)
            else {},
            "reorder_errors": [
                str(item)
                for item in cached.get("reorder_errors", [])
            ]
            if isinstance(cached.get("reorder_errors"), list)
            else [],
        }

    snapshot = _build_backlog_index_snapshot(target)
    _write_cached_snapshot(path=target, namespace="backlog/index", snapshot=snapshot)
    return snapshot


def _build_plan_index_snapshot(plan_index: Path) -> dict[str, Any]:
    content = plan_index.read_text(encoding="utf-8")
    stamp_match = _UPDATE_STAMP_RE.search(content)
    updated_utc = str(stamp_match.group("date")).strip() if stamp_match is not None else ""
    active_headers, active_rows, active_err = _collect_section_table(content, "Active Plans")
    parked_headers, parked_rows, parked_err = _collect_section_table(content, _PARKED_PLAN_SECTION_TITLE)
    return {
        "updated_utc": updated_utc,
        "active": _table_snapshot_payload(
            section_title="Active Plans",
            headers=active_headers,
            rows=active_rows,
            error=active_err,
        ),
        "parked": _table_snapshot_payload(
            section_title=_PARKED_PLAN_SECTION_TITLE,
            headers=parked_headers,
            rows=parked_rows,
            error=parked_err,
        ),
    }


def load_plan_index_snapshot(plan_index: Path) -> dict[str, Any]:
    """Return a cached parsed snapshot for `odylith/technical-plans/INDEX.md`."""

    target = plan_index.resolve()
    from odylith.runtime.governance import sync_session as governed_sync_session

    session = governed_sync_session.active_sync_session()
    if session is not None:
        repo_root = session.repo_root_for_path(target)
        if repo_root is not None:
            signature = odylith_context_cache.path_signature(target)
            snapshot = session.get_or_compute(
                namespace="plan_index_snapshot",
                key=f"{target.as_posix()}\n{signature.get('mtime_ns', 0)}\n{signature.get('size', 0)}",
                builder=lambda: load_plan_index_snapshot_uncached(target),
            )
            return copy.deepcopy(snapshot)
    return load_plan_index_snapshot_uncached(target)


def load_plan_index_snapshot_uncached(plan_index: Path) -> dict[str, Any]:
    target = plan_index.resolve()
    _cache_file, cached = _read_cached_snapshot(path=target, namespace="odylith/technical-plans/index")
    if cached is not None:
        return {
            "updated_utc": str(cached.get("updated_utc", "")).strip(),
            "active": _table_snapshot_from_payload(cached.get("active", {})) if isinstance(cached.get("active"), Mapping) else _table_snapshot_from_payload({}),
            "parked": _table_snapshot_from_payload(cached.get("parked", {})) if isinstance(cached.get("parked"), Mapping) else _table_snapshot_from_payload({}),
        }

    snapshot = _build_plan_index_snapshot(target)
    _write_cached_snapshot(path=target, namespace="odylith/technical-plans/index", snapshot=snapshot)
    return snapshot


def rows_as_mapping(
    *,
    section: Mapping[str, Any],
    expected_headers: Sequence[str] | None = None,
) -> list[dict[str, str]]:
    """Return table rows as dictionaries when the section is structurally valid."""

    headers_raw = section.get("headers", [])
    rows_raw = section.get("rows", [])
    error = _normalized_optional_text(section.get("error", ""))
    if error:
        return []
    if not isinstance(headers_raw, list) or not isinstance(rows_raw, list):
        return []
    headers = [str(cell) for cell in headers_raw]
    if expected_headers is not None and tuple(headers) != tuple(expected_headers):
        return []
    mapped: list[dict[str, str]] = []
    for row in rows_raw:
        if not isinstance(row, list) or len(row) != len(headers):
            continue
        mapped.append(dict(zip(headers, [str(cell) for cell in row], strict=True)))
    return mapped


def _split_metadata_ids(raw: str) -> list[str]:
    values: list[str] = []
    for token in str(raw or "").replace(";", ",").split(","):
        normalized = token.strip().upper()
        if not normalized:
            continue
        values.append(normalized)
    return values


def _build_lineage_values(spec: IdeaSpec, field: str) -> list[str]:
    return _split_metadata_ids(spec.metadata.get(field, ""))


def _normalize_workstream_ref(raw: str) -> str:
    token = str(raw or "").strip().upper()
    if token in {"", "NONE", "-"}:
        return ""
    return token


def _build_topology_values(spec: IdeaSpec, field: str) -> list[str]:
    values: list[str] = []
    seen: set[str] = set()
    for token in _split_metadata_ids(spec.metadata.get(field, "")):
        normalized = _normalize_workstream_ref(token)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        values.append(normalized)
    return values


def _validate_topology_contract(*, ideas: dict[str, IdeaSpec]) -> list[str]:
    errors: list[str] = []
    idea_ids = set(ideas.keys())

    for idea_id, spec in sorted(ideas.items()):
        parent_values = _build_topology_values(spec, "workstream_parent")
        if len(parent_values) > 1:
            errors.append(
                f"{spec.path}: `workstream_parent` expects a single B-id, got `{','.join(parent_values)}`"
            )
            continue

        if parent_values:
            parent_id = parent_values[0]
            if not _IDEA_ID_RE.fullmatch(parent_id):
                errors.append(f"{spec.path}: `workstream_parent` must contain a valid B-id, got `{parent_id}`")
            elif parent_id == idea_id:
                errors.append(f"{spec.path}: `workstream_parent` cannot self-reference `{idea_id}`")
            elif parent_id not in idea_ids:
                errors.append(f"{spec.path}: `workstream_parent` references missing workstream `{parent_id}`")

        for child_id in _build_topology_values(spec, "workstream_children"):
            if not _IDEA_ID_RE.fullmatch(child_id):
                errors.append(f"{spec.path}: `workstream_children` contains invalid B-id `{child_id}`")
                continue
            if child_id == idea_id:
                errors.append(f"{spec.path}: `workstream_children` cannot self-reference `{idea_id}`")
                continue
            if child_id not in idea_ids:
                errors.append(f"{spec.path}: `workstream_children` references missing workstream `{child_id}`")

    for idea_id, spec in sorted(ideas.items()):
        parent_values = _build_topology_values(spec, "workstream_parent")
        if parent_values:
            parent_id = parent_values[0]
            parent = ideas.get(parent_id)
            if parent is not None and idea_id not in set(_build_topology_values(parent, "workstream_children")):
                errors.append(
                    f"{parent.path}: missing reciprocal `workstream_children` entry `{idea_id}` for `{idea_id}.workstream_parent={parent_id}`"
                )

        for child_id in _build_topology_values(spec, "workstream_children"):
            child = ideas.get(child_id)
            if child is None:
                continue
            reciprocal = _build_topology_values(child, "workstream_parent")
            if not reciprocal:
                errors.append(
                    f"{child.path}: missing reciprocal `workstream_parent: {idea_id}` for `{idea_id}.workstream_children`"
                )
            elif reciprocal[0] != idea_id:
                errors.append(
                    f"{child.path}: `workstream_parent` must be `{idea_id}` to match `{idea_id}.workstream_children`"
                )

    return errors


def _validate_lineage_contract(*, ideas: dict[str, IdeaSpec]) -> list[str]:
    errors: list[str] = []
    idea_ids = set(ideas.keys())

    for idea_id, spec in sorted(ideas.items()):
        for field in _LINEAGE_SINGLE_FIELDS:
            values = _build_lineage_values(spec, field)
            if len(values) > 1:
                errors.append(
                    f"{spec.path}: `{field}` expects a single B-id, got `{','.join(values)}`"
                )
                continue
            if not values:
                continue
            target = values[0]
            if not _IDEA_ID_RE.fullmatch(target):
                errors.append(f"{spec.path}: `{field}` must contain a valid B-id, got `{target}`")
                continue
            if target == idea_id:
                errors.append(f"{spec.path}: `{field}` cannot self-reference `{idea_id}`")
                continue
            if target not in idea_ids:
                errors.append(f"{spec.path}: `{field}` references missing workstream `{target}`")

        for field in _LINEAGE_MULTI_FIELDS:
            values = _build_lineage_values(spec, field)
            seen: set[str] = set()
            for target in values:
                if target in seen:
                    continue
                seen.add(target)
                if not _IDEA_ID_RE.fullmatch(target):
                    errors.append(f"{spec.path}: `{field}` contains invalid B-id `{target}`")
                    continue
                if target == idea_id:
                    errors.append(f"{spec.path}: `{field}` cannot self-reference `{idea_id}`")
                    continue
                if target not in idea_ids:
                    errors.append(f"{spec.path}: `{field}` references missing workstream `{target}`")

    # Reciprocal lineage checks.
    for idea_id, spec in sorted(ideas.items()):
        reopens = _build_lineage_values(spec, "workstream_reopens")
        if reopens:
            target_id = reopens[0]
            target = ideas.get(target_id)
            if target is not None:
                reciprocal = _build_lineage_values(target, "workstream_reopened_by")
                if reciprocal and reciprocal[0] != idea_id:
                    errors.append(
                        f"{target.path}: `workstream_reopened_by` must be `{idea_id}` to match `{idea_id}.workstream_reopens={target_id}`"
                    )
                if not reciprocal:
                    errors.append(
                        f"{target.path}: missing reciprocal `workstream_reopened_by: {idea_id}` for `{idea_id}.workstream_reopens`"
                    )

        reopened_by = _build_lineage_values(spec, "workstream_reopened_by")
        if reopened_by:
            source_id = reopened_by[0]
            source = ideas.get(source_id)
            if source is not None:
                reciprocal = _build_lineage_values(source, "workstream_reopens")
                if reciprocal and reciprocal[0] != idea_id:
                    errors.append(
                        f"{source.path}: `workstream_reopens` must be `{idea_id}` to match `{idea_id}.workstream_reopened_by={source_id}`"
                    )
                if not reciprocal:
                    errors.append(
                        f"{source.path}: missing reciprocal `workstream_reopens: {idea_id}` for `{idea_id}.workstream_reopened_by`"
                    )

        split_from = _build_lineage_values(spec, "workstream_split_from")
        if split_from:
            source_id = split_from[0]
            source = ideas.get(source_id)
            if source is not None:
                reciprocal = set(_build_lineage_values(source, "workstream_split_into"))
                if idea_id not in reciprocal:
                    errors.append(
                        f"{source.path}: missing reciprocal `workstream_split_into` entry `{idea_id}` for `{idea_id}.workstream_split_from={source_id}`"
                    )

        split_into = set(_build_lineage_values(spec, "workstream_split_into"))
        for child_id in sorted(split_into):
            child = ideas.get(child_id)
            if child is None:
                continue
            reciprocal = _build_lineage_values(child, "workstream_split_from")
            if not reciprocal:
                errors.append(
                    f"{child.path}: missing reciprocal `workstream_split_from: {idea_id}` for `{idea_id}.workstream_split_into`"
                )
            elif reciprocal[0] != idea_id:
                errors.append(
                    f"{child.path}: `workstream_split_from` must be `{idea_id}` to match `{idea_id}.workstream_split_into`"
                )

        merged_into = _build_lineage_values(spec, "workstream_merged_into")
        if merged_into:
            target_id = merged_into[0]
            target = ideas.get(target_id)
            if target is not None:
                reciprocal = set(_build_lineage_values(target, "workstream_merged_from"))
                if idea_id not in reciprocal:
                    errors.append(
                        f"{target.path}: missing reciprocal `workstream_merged_from` entry `{idea_id}` for `{idea_id}.workstream_merged_into={target_id}`"
                    )

        merged_from = set(_build_lineage_values(spec, "workstream_merged_from"))
        for source_id in sorted(merged_from):
            source = ideas.get(source_id)
            if source is None:
                continue
            reciprocal = _build_lineage_values(source, "workstream_merged_into")
            if not reciprocal:
                errors.append(
                    f"{source.path}: missing reciprocal `workstream_merged_into: {idea_id}` for `{idea_id}.workstream_merged_from`"
                )
            elif reciprocal[0] != idea_id:
                errors.append(
                    f"{source.path}: `workstream_merged_into` must be `{idea_id}` to match `{idea_id}.workstream_merged_from`"
                )

    # Cycle detection across directed lineage edges.
    edges: dict[str, set[str]] = {idea_id: set() for idea_id in idea_ids}
    for idea_id, spec in ideas.items():
        reopens = _build_lineage_values(spec, "workstream_reopens")
        if reopens:
            edges[idea_id].add(reopens[0])
        split_from = _build_lineage_values(spec, "workstream_split_from")
        if split_from:
            # Canonical directed split lineage: source -> child.
            edges.setdefault(split_from[0], set()).add(idea_id)
        merged_into = _build_lineage_values(spec, "workstream_merged_into")
        if merged_into:
            # Canonical directed merge lineage: source -> target.
            edges[idea_id].add(merged_into[0])

    visiting: set[str] = set()
    visited: set[str] = set()

    def _visit(node: str, stack: list[str]) -> None:
        if node in visited:
            return
        if node in visiting:
            cycle = stack[stack.index(node) :] + [node] if node in stack else stack + [node]
            errors.append(
                "lineage cycle detected: " + " -> ".join(cycle)
            )
            return
        visiting.add(node)
        stack.append(node)
        for nxt in sorted(edges.get(node, set())):
            if nxt in idea_ids:
                _visit(nxt, stack)
        stack.pop()
        visiting.remove(node)
        visited.add(node)

    for idea_id in sorted(idea_ids):
        _visit(idea_id, [])

    return errors


def _validate_idea_specs_uncached(
    idea_root: Path,
    repo_root: Path | None = None,
) -> tuple[dict[str, IdeaSpec], list[str]]:
    errors: list[str] = []
    if not idea_root.is_dir():
        return {}, [f"missing ideas root: {idea_root}"]

    resolved_repo_root = (
        Path(repo_root).resolve()
        if repo_root is not None
        else backlog_title_contract.infer_repo_root_from_ideas_root(idea_root)
    )
    ideas: dict[str, IdeaSpec] = {}
    for path in sorted(idea_root.rglob("*.md")):
        spec = _parse_idea_spec(path)

        for key in _REQUIRED_METADATA:
            if key not in spec.metadata or not str(spec.metadata.get(key, "")).strip():
                errors.append(f"{path}: missing required metadata `{key}`")
        for key in _LEGACY_METADATA_FIELDS:
            if key in spec.metadata:
                errors.append(
                    f"{path}: legacy metadata `{key}` is no longer supported in Radar; rerun `odylith sync --repo-root .` to migrate"
                )

        for section in _REQUIRED_SECTIONS:
            if section not in spec.sections:
                errors.append(f"{path}: missing required section `## {section}`")
        errors.extend(
            core_detail_section_errors(
                title=str(spec.metadata.get("title", "")).strip(),
                sections=spec.section_bodies,
                path=path,
            )
        )

        errors.extend(
            backlog_title_contract.validate_workstream_title(
                title=str(spec.metadata.get("title", "")).strip(),
                path=path,
                repo_root=resolved_repo_root,
            )
        )

        idea_id = spec.idea_id
        if not idea_id:
            errors.append(f"{path}: missing `idea_id`")
        elif idea_id in ideas:
            errors.append(f"{path}: duplicate idea_id `{idea_id}` also used in {ideas[idea_id].path}")
        else:
            ideas[idea_id] = spec

        id_match = _IDEA_ID_RE.fullmatch(idea_id)
        if not id_match:
            errors.append(
                f"{path}: `idea_id` must match short handle format `B-<numeric>` (for example `B-001`)"
            )

        date_token = str(spec.metadata.get("date", "")).strip()
        if not _DATE_RE.fullmatch(date_token):
            errors.append(f"{path}: `date` must use YYYY-MM-DD format")
        else:
            try:
                dt.date.fromisoformat(date_token)
            except ValueError:
                errors.append(f"{path}: `date` is not a valid calendar date `{date_token}`")

        file_match = _IDEA_FILE_RE.fullmatch(path.stem)
        if file_match is None:
            errors.append(
                f"{path}: filename must match `YYYY-MM-DD-<slug>.md` with lowercase slug"
            )
        else:
            file_date = str(file_match.group("date"))
            file_slug = str(file_match.group("slug"))
            if date_token and file_date != date_token:
                errors.append(
                    f"{path}: filename date `{file_date}` must match metadata date `{date_token}`"
                )
            month_dir = path.parent.name
            expected_month = file_date[:7]
            if month_dir != expected_month:
                errors.append(
                    f"{path}: month directory `{month_dir}` must match file date month `{expected_month}`"
                )

        priority = str(spec.metadata.get("priority", "")).strip()
        if priority and priority not in _VALID_PRIORITIES:
            errors.append(f"{path}: invalid `priority` `{priority}`")

        status = spec.status
        if status and status not in _VALID_STATUS:
            errors.append(f"{path}: invalid `status` `{status}`")

        founder_override = str(spec.metadata.get("founder_override", "no")).strip().lower()
        if founder_override not in _YES_NO:
            errors.append(f"{path}: `founder_override` must be one of {sorted(_YES_NO)}")

        execution_model = execution_wave_contract.execution_model_for_metadata(spec.metadata)
        if execution_model not in execution_wave_contract.VALID_EXECUTION_MODELS:
            errors.append(
                f"{path}: `{execution_wave_contract.EXECUTION_MODEL_FIELD}` must be one of "
                f"{sorted(execution_wave_contract.VALID_EXECUTION_MODELS)}, got `{execution_model}`"
            )

        declared_score = _parse_int_in_range(
            value=spec.metadata.get("ordering_score", ""),
            field="ordering_score",
            low=0,
            high=100,
            errors=errors,
            path=path,
        )
        computed_score = _compute_score(spec.metadata, errors=errors, path=path)
        if (
            declared_score is not None
            and computed_score is not None
            and declared_score != computed_score
            and founder_override != "yes"
        ):
            errors.append(
                f"{path}: `ordering_score` ({declared_score}) does not match formula ({computed_score})"
            )

    return ideas, errors


def _validate_idea_specs(
    idea_root: Path,
    repo_root: Path | None = None,
) -> tuple[dict[str, IdeaSpec], list[str]]:
    resolved_idea_root = Path(idea_root).resolve()
    resolved_repo_root = (
        Path(repo_root).resolve()
        if repo_root is not None
        else backlog_title_contract.infer_repo_root_from_ideas_root(resolved_idea_root)
    )
    from odylith.runtime.governance import sync_session as governed_sync_session

    session = governed_sync_session.active_sync_session()
    if session is not None and resolved_repo_root is not None and session.repo_root == resolved_repo_root:
        fingerprint = odylith_context_cache.fingerprint_tree(resolved_idea_root, glob="*.md")
        cached_ideas, cached_errors = session.get_or_compute(
            namespace="validate_idea_specs",
            key=f"{resolved_idea_root.as_posix()}\n{fingerprint}",
            builder=lambda: _validate_idea_specs_uncached(
                resolved_idea_root,
                repo_root=resolved_repo_root,
            ),
        )
        return dict(cached_ideas), list(cached_errors)
    return _validate_idea_specs_uncached(resolved_idea_root, repo_root=resolved_repo_root)


def _validate_promotion_links(*, ideas: dict[str, IdeaSpec], repo_root: Path) -> list[str]:
    errors: list[str] = []
    for spec in ideas.values():
        promoted_to_plan = str(spec.metadata.get("promoted_to_plan", "")).strip()
        status = spec.status
        if status in _EXECUTION_STATUSES:
            if not promoted_to_plan:
                errors.append(
                    f"{spec.path}: `{status}` idea missing `promoted_to_plan`"
                )
                continue
            target = _resolve_repo_path(repo_root=repo_root, token=promoted_to_plan)
            if not str(target).startswith(str(repo_root)):
                errors.append(
                    f"{spec.path}: `promoted_to_plan` must resolve inside repo root (`{promoted_to_plan}`)"
                )
                continue
            if not target.is_file():
                errors.append(
                    f"{spec.path}: `promoted_to_plan` target does not exist `{promoted_to_plan}`"
                )
                continue
            rel = target.relative_to(repo_root)
            if not str(rel).startswith("odylith/technical-plans/in-progress/"):
                errors.append(
                    f"{spec.path}: `{status}` `promoted_to_plan` must point under `odylith/technical-plans/in-progress/`, got `{promoted_to_plan}`"
                )
        elif status in _FINISHED_STATUSES:
            if not promoted_to_plan:
                errors.append(
                    f"{spec.path}: `finished` idea missing `promoted_to_plan`"
                )
                continue
            target = _resolve_repo_path(repo_root=repo_root, token=promoted_to_plan)
            if not str(target).startswith(str(repo_root)):
                errors.append(
                    f"{spec.path}: `promoted_to_plan` must resolve inside repo root (`{promoted_to_plan}`)"
                )
                continue
            if not target.is_file():
                errors.append(
                    f"{spec.path}: `promoted_to_plan` target does not exist `{promoted_to_plan}`"
                )
                continue
            rel = target.relative_to(repo_root)
            if not str(rel).startswith("odylith/technical-plans/done/"):
                errors.append(
                    f"{spec.path}: `finished` `promoted_to_plan` must point under `odylith/technical-plans/done/`, got `{promoted_to_plan}`"
                )
        elif promoted_to_plan:
            errors.append(
                f"{spec.path}: `{status}` idea must not set `promoted_to_plan` (`{promoted_to_plan}`)"
            )
    return errors


def _validate_backlog_index(
    *,
    backlog_index: Path,
    ideas: dict[str, IdeaSpec],
    repo_root: Path,
) -> tuple[set[str], set[str], set[str], set[str], dict[str, int], list[str]]:
    errors: list[str] = []
    if not backlog_index.is_file():
        return set(), set(), set(), set(), {}, [f"missing backlog index: {backlog_index}"]

    snapshot = load_backlog_index_snapshot(backlog_index)
    if not snapshot.get("updated_utc"):
        errors.append(f"{backlog_index}: missing `Last updated (UTC): YYYY-MM-DD` stamp")
    else:
        date_token = str(snapshot.get("updated_utc", "")).strip()
        try:
            dt.date.fromisoformat(date_token)
        except ValueError:
            errors.append(f"{backlog_index}: invalid update stamp date `{date_token}`")

    active_section = snapshot.get("active", {})
    execution_section = snapshot.get("execution", {})
    finished_section = snapshot.get("finished", {})
    parked_section = snapshot.get("parked", {})
    headers_active = list(active_section.get("headers", [])) if isinstance(active_section, Mapping) else []
    rows_active = list(active_section.get("rows", [])) if isinstance(active_section, Mapping) else []
    err_active = _normalized_optional_text(active_section.get("error", "")) if isinstance(active_section, Mapping) else ""
    headers_execution = list(execution_section.get("headers", [])) if isinstance(execution_section, Mapping) else []
    rows_execution = list(execution_section.get("rows", [])) if isinstance(execution_section, Mapping) else []
    err_execution = _normalized_optional_text(execution_section.get("error", "")) if isinstance(execution_section, Mapping) else ""
    headers_finished = list(finished_section.get("headers", [])) if isinstance(finished_section, Mapping) else []
    rows_finished = list(finished_section.get("rows", [])) if isinstance(finished_section, Mapping) else []
    err_finished = _normalized_optional_text(finished_section.get("error", "")) if isinstance(finished_section, Mapping) else ""
    headers_parked = list(parked_section.get("headers", [])) if isinstance(parked_section, Mapping) else []
    rows_parked = list(parked_section.get("rows", [])) if isinstance(parked_section, Mapping) else []
    err_parked = _normalized_optional_text(parked_section.get("error", "")) if isinstance(parked_section, Mapping) else ""
    parked_specs_present = any(spec.status in _PARKED_STATUSES for spec in ideas.values())

    if err_active:
        errors.append(f"{backlog_index}: {err_active}")
        rows_active = []
    if err_execution:
        errors.append(f"{backlog_index}: {err_execution}")
        rows_execution = []
    if err_finished:
        errors.append(f"{backlog_index}: {err_finished}")
        rows_finished = []
    if err_parked:
        if parked_specs_present or not str(err_parked).startswith("missing section"):
            errors.append(f"{backlog_index}: {err_parked}")
        rows_parked = []
    if headers_active and tuple(headers_active) != _INDEX_COLS:
        if tuple(headers_active) == _LEGACY_INDEX_COLS_WITH_LANES:
            errors.append(
                f"{backlog_index}: active table still uses legacy `impacted_lanes` column; rerun `odylith sync --repo-root .` to migrate"
            )
        else:
            errors.append(f"{backlog_index}: active table headers do not match contract")
    if headers_execution and tuple(headers_execution) != _INDEX_COLS:
        if tuple(headers_execution) == _LEGACY_INDEX_COLS_WITH_LANES:
            errors.append(
                f"{backlog_index}: execution table still uses legacy `impacted_lanes` column; rerun `odylith sync --repo-root .` to migrate"
            )
        else:
            errors.append(f"{backlog_index}: execution table headers do not match contract")
    if headers_finished and tuple(headers_finished) != _INDEX_COLS:
        if tuple(headers_finished) == _LEGACY_INDEX_COLS_WITH_LANES:
            errors.append(
                f"{backlog_index}: finished table still uses legacy `impacted_lanes` column; rerun `odylith sync --repo-root .` to migrate"
            )
        else:
            errors.append(f"{backlog_index}: finished table headers do not match contract")
    if headers_parked and tuple(headers_parked) != _INDEX_COLS:
        if tuple(headers_parked) == _LEGACY_INDEX_COLS_WITH_LANES:
            errors.append(
                f"{backlog_index}: parked table still uses legacy `impacted_lanes` column; rerun `odylith sync --repo-root .` to migrate"
            )
        else:
            errors.append(f"{backlog_index}: parked table headers do not match contract")

    seen_ids: set[str] = set()
    active_ids: set[str] = set()
    execution_ids: set[str] = set()
    parked_ids: set[str] = set()
    finished_ids: set[str] = set()
    active_ranks: dict[str, int] = {}

    prev_score: int | None = None
    prev_id: str | None = None
    prev_override = False
    expected_rank = 1

    for row in rows_active:
        if len(row) != len(_INDEX_COLS):
            errors.append(f"{backlog_index}: malformed active row with {len(row)} columns")
            continue
        payload = dict(zip(_INDEX_COLS, row, strict=True))

        rank_token = payload["rank"]
        try:
            rank = int(rank_token)
        except ValueError:
            errors.append(f"{backlog_index}: active row rank must be numeric, got `{rank_token}`")
            continue
        if rank != expected_rank:
            errors.append(
                f"{backlog_index}: active row rank sequence mismatch, expected {expected_rank}, got {rank}"
            )
        expected_rank += 1

        idea_id = payload["idea_id"].strip()
        if idea_id in seen_ids:
            errors.append(f"{backlog_index}: duplicate idea_id in index `{idea_id}`")
            continue
        seen_ids.add(idea_id)
        active_ids.add(idea_id)
        active_ranks[idea_id] = rank

        score = _parse_int_in_range(
            value=payload["ordering_score"],
            field=f"ordering_score ({idea_id})",
            low=0,
            high=100,
            errors=errors,
            path=backlog_index,
        )
        if score is not None and prev_score is not None and score > prev_score:
            delta = score - prev_score
            current_override = ideas.get(idea_id).founder_override if idea_id in ideas else False
            if delta >= 3 and not (current_override or prev_override):
                errors.append(
                    f"{backlog_index}: active ranking score inversion `{idea_id}`({score}) over "
                    f"`{prev_id}`({prev_score}) requires manual priority override or smaller delta"
                )
        if score is not None:
            prev_score = score
            prev_id = idea_id
            prev_override = ideas.get(idea_id).founder_override if idea_id in ideas else False

        status = payload["status"].strip()
        if status not in _ACTIVE_STATUSES:
            errors.append(
                f"{backlog_index}: active queue status must be one of {sorted(_ACTIVE_STATUSES)} (`{idea_id}`)"
            )

        _validate_row_against_idea(
            payload=payload,
            ideas=ideas,
            errors=errors,
            index_path=backlog_index,
            repo_root=repo_root,
        )

    execution_prev_status_rank: int | None = None
    execution_prev_status: str | None = None
    execution_prev_score: int | None = None
    execution_prev_id: str | None = None
    execution_prev_override = False
    for row in rows_execution:
        if len(row) != len(_INDEX_COLS):
            errors.append(f"{backlog_index}: malformed execution row with {len(row)} columns")
            continue
        payload = dict(zip(_INDEX_COLS, row, strict=True))
        if payload["rank"].strip() != "-":
            errors.append(
                f"{backlog_index}: execution row rank must be '-', got `{payload['rank'].strip()}`"
            )

        idea_id = payload["idea_id"].strip()
        if idea_id in seen_ids:
            errors.append(f"{backlog_index}: duplicate idea_id in index `{idea_id}`")
            continue
        seen_ids.add(idea_id)
        execution_ids.add(idea_id)
        current_override = ideas.get(idea_id).founder_override if idea_id in ideas else False

        normalized_status = payload["status"].strip().lower()
        if normalized_status not in _EXECUTION_STATUSES:
            errors.append(
                f"{backlog_index}: execution table status must be one of {sorted(_EXECUTION_STATUSES)} for `{idea_id}`"
            )

        score = _parse_int_in_range(
            value=payload["ordering_score"],
            field=f"ordering_score ({idea_id})",
            low=0,
            high=100,
            errors=errors,
            path=backlog_index,
        )
        if score is not None:
            status_rank = _EXECUTION_STATUS_ORDER.get(normalized_status, 99)
            if (
                execution_prev_status_rank is not None
                and status_rank < execution_prev_status_rank
                and not (current_override or execution_prev_override)
            ):
                errors.append(
                    f"{backlog_index}: execution ordering violation `{idea_id}`({normalized_status}) appears above "
                    f"higher-priority status sequence; required order is implementation before planning"
                )
            if (
                execution_prev_status_rank is not None
                and status_rank == execution_prev_status_rank
                and execution_prev_score is not None
                and score > execution_prev_score
                and not (current_override or execution_prev_override)
            ):
                errors.append(
                    f"{backlog_index}: execution ranking score inversion `{idea_id}`({score}) over "
                    f"`{execution_prev_id}`({execution_prev_score}) within status `{normalized_status}`; "
                    "execution rows must be sorted by highest score first within each status bucket"
                )
            execution_prev_status_rank = status_rank
            execution_prev_status = normalized_status
            execution_prev_score = score
            execution_prev_id = idea_id
            execution_prev_override = current_override

        _validate_row_against_idea(
            payload=payload,
            ideas=ideas,
            errors=errors,
            index_path=backlog_index,
            repo_root=repo_root,
        )

    for row in rows_finished:
        if len(row) != len(_INDEX_COLS):
            errors.append(f"{backlog_index}: malformed finished row with {len(row)} columns")
            continue
        payload = dict(zip(_INDEX_COLS, row, strict=True))
        if payload["rank"].strip() != "-":
            errors.append(
                f"{backlog_index}: finished row rank must be '-', got `{payload['rank'].strip()}`"
            )

        idea_id = payload["idea_id"].strip()
        if idea_id in seen_ids:
            errors.append(f"{backlog_index}: duplicate idea_id in index `{idea_id}`")
            continue
        seen_ids.add(idea_id)
        finished_ids.add(idea_id)

        if payload["status"].strip() not in _FINISHED_STATUSES:
            errors.append(
                f"{backlog_index}: finished table status must be one of {sorted(_FINISHED_STATUSES)} for `{idea_id}`"
            )

        _validate_row_against_idea(
            payload=payload,
            ideas=ideas,
            errors=errors,
            index_path=backlog_index,
            repo_root=repo_root,
        )

    for row in rows_parked:
        if len(row) != len(_INDEX_COLS):
            errors.append(f"{backlog_index}: malformed parked row with {len(row)} columns")
            continue
        payload = dict(zip(_INDEX_COLS, row, strict=True))
        if payload["rank"].strip() != "-":
            errors.append(
                f"{backlog_index}: parked row rank must be '-', got `{payload['rank'].strip()}`"
            )

        idea_id = payload["idea_id"].strip()
        if idea_id in seen_ids:
            errors.append(f"{backlog_index}: duplicate idea_id in index `{idea_id}`")
            continue
        seen_ids.add(idea_id)
        parked_ids.add(idea_id)

        if payload["status"].strip() not in _PARKED_STATUSES:
            errors.append(
                f"{backlog_index}: parked table status must be one of {sorted(_PARKED_STATUSES)} for `{idea_id}`"
            )

        _validate_row_against_idea(
            payload=payload,
            ideas=ideas,
            errors=errors,
            index_path=backlog_index,
            repo_root=repo_root,
        )

    all_idea_ids = set(ideas.keys())
    missing_in_index = sorted(all_idea_ids - seen_ids)
    if missing_in_index:
        errors.append(
            f"{backlog_index}: ideas missing from index: {', '.join(missing_in_index)}"
        )

    errors.extend(
        _validate_reorder_rationale_log(
            backlog_index=backlog_index,
            snapshot=snapshot,
            active_ids=active_ids,
            active_ranks=active_ranks,
            execution_ids=execution_ids,
            parked_ids=parked_ids,
            finished_ids=finished_ids,
            ideas=ideas,
        )
    )
    errors.extend(_validate_duplicate_risk(ideas=ideas, active_ids=active_ids))

    return active_ids, execution_ids, parked_ids, finished_ids, active_ranks, errors


def _validate_row_against_idea(
    *,
    payload: dict[str, str],
    ideas: dict[str, IdeaSpec],
    errors: list[str],
    index_path: Path,
    repo_root: Path,
) -> None:
    idea_id = payload["idea_id"].strip()
    spec = ideas.get(idea_id)
    if spec is None:
        errors.append(f"{index_path}: index references unknown idea_id `{idea_id}`")
        return

    comparisons = (
        ("title", payload["title"]),
        ("priority", payload["priority"]),
        ("ordering_score", payload["ordering_score"]),
        ("commercial_value", payload["commercial_value"]),
        ("product_impact", payload["product_impact"]),
        ("market_value", payload["market_value"]),
        ("sizing", payload["sizing"]),
        ("complexity", payload["complexity"]),
        ("status", payload["status"]),
    )
    for key, actual in comparisons:
        expected = str(spec.metadata.get(key, "")).strip()
        if str(actual).strip() != expected:
            errors.append(
                f"{index_path}: field mismatch for `{idea_id}` `{key}` index=`{actual}` idea=`{expected}`"
            )

    target = _parse_link_target(payload["link"])
    if target is None:
        errors.append(f"{index_path}: invalid markdown link for `{idea_id}` in `link` column")
        return
    link_path, resolves_inside_repo = _resolve_equivalent_repo_link(
        repo_root=repo_root,
        target=target,
        expected_path=spec.path.resolve(),
    )
    if not resolves_inside_repo:
        errors.append(f"{index_path}: link for `{idea_id}` must resolve under repo root")
    if link_path != spec.path.resolve():
        errors.append(
            f"{index_path}: link target mismatch for `{idea_id}` index=`{link_path}` idea=`{spec.path.resolve()}`"
        )


def _validate_plan_index(
    *,
    plan_index: Path,
    execution_ids: set[str],
    parked_ids: set[str],
    ideas: dict[str, IdeaSpec],
    repo_root: Path,
) -> list[str]:
    errors: list[str] = []
    if not plan_index.is_file():
        return [f"missing plan index: {plan_index}"]

    snapshot = load_plan_index_snapshot(plan_index)
    active_section = snapshot.get("active", {})
    parked_section = snapshot.get("parked", {})
    active_headers = list(active_section.get("headers", [])) if isinstance(active_section, Mapping) else []
    active_rows = list(active_section.get("rows", [])) if isinstance(active_section, Mapping) else []
    active_err = _normalized_optional_text(active_section.get("error", "")) if isinstance(active_section, Mapping) else ""
    if active_err:
        return [f"{plan_index}: {active_err}"]
    if tuple(active_headers) != _PLAN_COLS:
        errors.append(
            f"{plan_index}: active plans headers must match contract {list(_PLAN_COLS)}"
        )
        return errors

    parked_headers = list(parked_section.get("headers", [])) if isinstance(parked_section, Mapping) else []
    parked_rows = list(parked_section.get("rows", [])) if isinstance(parked_section, Mapping) else []
    parked_err = _normalized_optional_text(parked_section.get("error", "")) if isinstance(parked_section, Mapping) else ""
    parked_plan_files_present = any(truth_root_path(repo_root=repo_root, key="technical_plans").joinpath("parked").rglob("*.md"))
    if parked_err:
        if parked_plan_files_present or not str(parked_err).startswith("missing section"):
            errors.append(f"{plan_index}: {parked_err}")
        parked_rows = []
        parked_headers = []
    elif tuple(parked_headers) != _PLAN_COLS:
        errors.append(
            f"{plan_index}: parked plans headers must match contract {list(_PLAN_COLS)}"
        )
        return errors

    def _collect_plan_rows(
        *,
        rows: list[list[str]],
        section_title: str,
        expected_status: str,
        expected_prefix: str,
    ) -> dict[str, str]:
        mapping: dict[str, str] = {}
        for row in rows:
            if len(row) != len(_PLAN_COLS):
                errors.append(
                    f"{plan_index}: malformed {section_title.lower()} row with {len(row)} columns"
                )
                continue
            payload = dict(zip(_PLAN_COLS, row, strict=True))
            backlog_id = _strip_inline_code(payload["Backlog"])
            plan_path = _strip_inline_code(payload["Plan"])
            status = payload["Status"].strip()
            if status != expected_status:
                errors.append(
                    f"{plan_index}: `{section_title}` row for `{backlog_id or plan_path}` must use status `{expected_status}`, got `{status}`"
                )
            if not backlog_id or backlog_id == "-":
                errors.append(
                    f"{plan_index}: `{section_title}` row must bind a backlog id, got `{payload['Backlog']}`"
                )
                continue
            if backlog_id in mapping:
                errors.append(
                    f"{plan_index}: duplicate `{section_title}` row for backlog `{backlog_id}`"
                )
                continue
            if not plan_path.startswith(expected_prefix):
                errors.append(
                    f"{plan_index}: `{section_title}` row for `{backlog_id}` must point under `{expected_prefix}`, got `{plan_path}`"
                )
            resolved_plan_path = _resolve_repo_path(repo_root=repo_root, token=plan_path)
            if not resolved_plan_path.is_file():
                errors.append(
                    f"{plan_index}: `{section_title}` row for `{backlog_id}` points to missing plan `{plan_path}`"
                )
            mapping[backlog_id] = plan_path
        return mapping

    active_plans_by_backlog_id = _collect_plan_rows(
        rows=active_rows,
        section_title="Active Plans",
        expected_status="In progress",
        expected_prefix="odylith/technical-plans/in-progress/",
    )
    parked_plans_by_backlog_id = _collect_plan_rows(
        rows=parked_rows,
        section_title=_PARKED_PLAN_SECTION_TITLE,
        expected_status="Parked",
        expected_prefix="odylith/technical-plans/parked/",
    )

    for idea_id in sorted(execution_ids):
        spec = ideas.get(idea_id)
        if spec is None:
            continue
        expected_plan = str(spec.metadata.get("promoted_to_plan", "")).strip()
        mapped = active_plans_by_backlog_id.get(idea_id)
        if mapped is None:
            errors.append(
                f"{plan_index}: missing active plan row linked to execution backlog idea `{idea_id}`"
            )
            continue
        if mapped != expected_plan:
            errors.append(
                f"{plan_index}: execution idea `{idea_id}` points to `{expected_plan}` but index maps to `{mapped}`"
            )
    for backlog_id in sorted(parked_plans_by_backlog_id):
        spec = ideas.get(backlog_id)
        if spec is None:
            continue
        if spec.status not in _PARKED_STATUSES:
            errors.append(
                f"{plan_index}: parked plan row `{backlog_id}` must reference a parked backlog idea"
            )
    parked_root = truth_root_path(repo_root=repo_root, key="technical_plans") / "parked"
    for backlog_id in sorted(parked_ids):
        spec = ideas.get(backlog_id)
        if spec is None:
            continue
        candidate_paths = (
            sorted(parked_root.rglob(spec.path.name))
            if parked_root.is_dir()
            else []
        )
        if not candidate_paths:
            continue
        mapped = parked_plans_by_backlog_id.get(backlog_id)
        if mapped is None:
            errors.append(
                f"{plan_index}: parked backlog idea `{backlog_id}` is missing from `{_PARKED_PLAN_SECTION_TITLE}`"
            )
            continue
        expected_candidates = {
            candidate.relative_to(repo_root).as_posix()
            for candidate in candidate_paths
        }
        if mapped not in expected_candidates:
            errors.append(
                f"{plan_index}: parked backlog idea `{backlog_id}` maps to `{mapped}` but expected one of {sorted(expected_candidates)}"
            )
    return errors


def _validate_execution_status_sync(*, execution_ids: set[str], ideas: dict[str, IdeaSpec]) -> list[str]:
    errors: list[str] = []
    execution_specs = {idea_id for idea_id, spec in ideas.items() if spec.status in _EXECUTION_STATUSES}
    if execution_specs != execution_ids:
        missing = sorted(execution_specs - execution_ids)
        extra = sorted(execution_ids - execution_specs)
        if missing:
            errors.append(
                "odylith/radar/source/INDEX.md execution section missing planning/implementation ideas: "
                + ", ".join(missing)
            )
        if extra:
            errors.append(
                "odylith/radar/source/INDEX.md execution section includes non planning/implementation ideas: "
                + ", ".join(extra)
            )
    return errors


def _validate_parked_status_sync(*, parked_ids: set[str], ideas: dict[str, IdeaSpec]) -> list[str]:
    errors: list[str] = []
    parked_specs = {idea_id for idea_id, spec in ideas.items() if spec.status in _PARKED_STATUSES}
    if parked_specs != parked_ids:
        missing = sorted(parked_specs - parked_ids)
        extra = sorted(parked_ids - parked_specs)
        if missing:
            errors.append(
                "odylith/radar/source/INDEX.md parked section missing parked ideas: " + ", ".join(missing)
            )
        if extra:
            errors.append(
                "odylith/radar/source/INDEX.md parked section includes non-parked ideas: "
                + ", ".join(extra)
            )
    return errors


def _validate_reorder_rationale_log(
    *,
    backlog_index: Path,
    snapshot: Mapping[str, Any],
    active_ids: set[str],
    active_ranks: dict[str, int],
    execution_ids: set[str],
    parked_ids: set[str],
    finished_ids: set[str],
    ideas: dict[str, IdeaSpec],
) -> list[str]:
    errors: list[str] = []
    sections_payload = snapshot.get("reorder_sections", {})
    parse_errors_raw = snapshot.get("reorder_errors", [])
    parse_errors = [str(message) for message in parse_errors_raw] if isinstance(parse_errors_raw, list) else []
    errors.extend([f"{backlog_index}: {message}" for message in parse_errors])
    if parse_errors:
        return errors
    sections: dict[str, ReorderRationaleSection] = {}
    if isinstance(sections_payload, Mapping):
        for key, value in sections_payload.items():
            if not isinstance(value, Mapping):
                continue
            sections[str(key)] = ReorderRationaleSection(
                heading=str(value.get("heading", "")).strip(),
                lines=[str(line) for line in value.get("lines", [])] if isinstance(value.get("lines"), list) else [],
            )

    required_bullets = (
        "- why now:",
        "- expected outcome:",
        "- tradeoff:",
        "- deferred for now:",
        "- ranking basis:",
    )

    for idea_id in sorted(active_ids):
        if idea_id not in sections:
            errors.append(
                f"{backlog_index}: missing reorder rationale entry for active idea `{idea_id}`"
            )
            continue
        section = sections[idea_id]
        expected_rank = active_ranks.get(idea_id)
        expected_heading = (
            f"{idea_id} (rank {expected_rank})"
            if expected_rank is not None
            else f"{idea_id} (rank ?)"
        )
        if section.heading.strip() != expected_heading:
            errors.append(
                f"{backlog_index}: rationale heading for `{idea_id}` must be exactly "
                f"`### {expected_heading}`, found `### {section.heading.strip()}`"
            )
        section_text = "\n".join(section.lines).lower()
        for bullet in required_bullets:
            if bullet not in section_text:
                errors.append(
                    f"{backlog_index}: reorder rationale for `{idea_id}` missing `{bullet}`"
                )

    for idea_id, spec in sorted(ideas.items()):
        if not spec.founder_override:
            continue
        if (
            idea_id not in active_ids
            and idea_id not in execution_ids
            and idea_id not in parked_ids
            and idea_id not in finished_ids
        ):
            continue
        if idea_id not in sections:
            errors.append(
                f"{backlog_index}: priority override idea `{idea_id}` missing decision-basis entry"
            )
            continue
        section_text = "\n".join(sections[idea_id].lines)
        lowered = section_text.lower()
        if "- ranking basis:" not in lowered:
            errors.append(
                f"{backlog_index}: priority override idea `{idea_id}` missing `ranking basis` bullet"
            )
            continue
        if "no manual priority override" in lowered:
            errors.append(
                f"{backlog_index}: priority override idea `{idea_id}` has contradictory `no manual priority override` note"
            )
        if _REVIEW_DATE_RE.search(section_text) is None:
            errors.append(
                f"{backlog_index}: priority override idea `{idea_id}` must include review checkpoint date (YYYY-MM-DD)"
            )
    return errors


def _validate_duplicate_risk(*, ideas: dict[str, IdeaSpec], active_ids: set[str]) -> list[str]:
    errors: list[str] = []
    active_specs = [ideas[idea_id] for idea_id in sorted(active_ids) if idea_id in ideas]
    for idx, left in enumerate(active_specs):
        left_tokens = _normalize_title_tokens(left.metadata.get("title", ""))
        if len(left_tokens) < 4:
            continue
        for right in active_specs[idx + 1 :]:
            right_tokens = _normalize_title_tokens(right.metadata.get("title", ""))
            if len(right_tokens) < 4:
                continue
            similarity = _jaccard_similarity(left_tokens, right_tokens)
            if similarity < 0.85:
                continue
            errors.append(
                "possible duplicate active ideas: "
                f"`{left.idea_id}` <-> `{right.idea_id}` similarity={similarity:.2f}; "
                "merge or supersede explicitly"
            )
    return errors


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    repo_root = Path(args.repo_root).resolve()
    idea_root = _resolve_repo_path(repo_root=repo_root, token=args.ideas_root)
    backlog_index = _resolve_repo_path(repo_root=repo_root, token=args.backlog_index)
    plan_index = _resolve_repo_path(repo_root=repo_root, token=args.plan_index)

    errors: list[str] = []
    backlog_source_root = truth_root_path(repo_root=repo_root, key="radar_source")
    if not backlog_source_root.is_dir():
        errors.append(f"{repo_root}: missing `odylith/radar/source/` directory")

    ideas, idea_errors = _validate_idea_specs(idea_root, repo_root=repo_root)
    errors.extend(idea_errors)
    errors.extend(_validate_topology_contract(ideas=ideas))
    errors.extend(_validate_lineage_contract(ideas=ideas))
    errors.extend(_validate_promotion_links(ideas=ideas, repo_root=repo_root))
    _execution_programs, execution_program_errors = execution_wave_contract.collect_execution_programs(
        repo_root=repo_root,
        idea_specs=ideas,
    )
    errors.extend(execution_program_errors)

    active_ids, execution_ids, parked_ids, finished_ids, _active_ranks, backlog_errors = _validate_backlog_index(
        backlog_index=backlog_index,
        ideas=ideas,
        repo_root=repo_root,
    )
    del active_ids
    errors.extend(backlog_errors)
    errors.extend(_validate_execution_status_sync(execution_ids=execution_ids, ideas=ideas))
    errors.extend(_validate_parked_status_sync(parked_ids=parked_ids, ideas=ideas))
    errors.extend(
        _validate_plan_index(
            plan_index=plan_index,
            execution_ids=execution_ids,
            parked_ids=parked_ids,
            ideas=ideas,
            repo_root=repo_root,
        )
    )
    del finished_ids
    release_state, release_errors = release_planning_contract.validate_release_planning(
        repo_root=repo_root,
        idea_specs=ideas,
    )
    errors.extend(release_errors)

    if errors:
        print("backlog contract validation FAILED")
        for message in errors:
            print(f"- {message}")
        return 2

    print("backlog contract validation passed")
    print(f"- ideas validated: {len(ideas)}")
    print(f"- execution-linked ideas: {len(execution_ids)}")
    print(f"- parked ideas: {len(parked_ids)}")
    print(f"- releases: {len(release_state.releases_by_id)}")
    print(f"- active release targets: {len(release_state.active_release_by_workstream)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
