"""Casebook linkage and release truth for the GitHub issue pipeline."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from odylith.runtime.governance import casebook_source_validation
from odylith.runtime.governance import release_planning_contract
from odylith.runtime.governance import sync_casebook_bug_index
from odylith.runtime.governance.github_issue_models import CasebookMatch
from odylith.runtime.governance.github_issue_models import DEFAULT_FIXED_VERSION
from odylith.runtime.governance.github_issue_models import GovernanceMutationPlan
from odylith.runtime.governance.github_issue_references import extract_issue_tokens
from odylith.runtime.governance.github_issue_references import format_issue_markdown_link
from odylith.runtime.governance.github_issue_references import format_issue_token
from odylith.runtime.governance.github_issue_references import normalize_version
from odylith.runtime.governance.github_issue_transport import GitHubPipelineError

_RELEASES_RELATIVE = Path("odylith/radar/source/releases/releases.v1.json")
_FIELD_RE = re.compile(r"^\s*-\s*(?P<name>[^:]+):\s*(?P<value>.*)$")
_WORD_RE = re.compile(r"[a-z0-9]{3,}")
_PLACEHOLDER_RE = re.compile(r"^(?:tbd|todo|unknown|n/?a|pending)(?:\b|[^A-Za-z0-9].*)?$", re.IGNORECASE)


@dataclass(frozen=True)
class CasebookRecord:
    path: Path
    fields: Mapping[str, str]

    @property
    def bug_id(self) -> str:
        return self.fields.get("Bug ID", "")


@dataclass(frozen=True)
class ReleaseInfo:
    release_id: str
    version: str
    tag: str
    status: str
    shipped_utc: str = ""
    closed_utc: str = ""


def iter_casebook_records(repo_root: Path) -> tuple[CasebookRecord, ...]:
    records: list[CasebookRecord] = []
    for path in casebook_source_validation.iter_casebook_bug_markdown_paths(repo_root=repo_root):
        fields = parse_casebook_fields(path.read_text(encoding="utf-8"))
        if fields:
            records.append(CasebookRecord(path=path, fields=fields))
    return tuple(records)


def parse_casebook_fields(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in text.splitlines():
        match = _FIELD_RE.match(line)
        if match:
            fields[match.group("name").strip()] = match.group("value").strip()
    return fields


def match_casebook_issue(*, repo_root: Path, issue: Mapping[str, object], repo: str) -> list[CasebookMatch]:
    issue_token = format_issue_token(repo=repo, number=int(issue["number"]))
    issue_words = set(_WORD_RE.findall(f"{issue.get('title', '')} {issue.get('body', '')}".lower()))
    matches: list[CasebookMatch] = []
    for record in iter_casebook_records(repo_root):
        rel_path = record.path.relative_to(repo_root).as_posix()
        fields = record.fields
        if issue_token in extract_issue_tokens(fields.get("GitHub Issue(s)", "")):
            matches.append(CasebookMatch(fields.get("Bug ID", ""), rel_path, fields.get("Status", ""), 1.0, "explicit_github_link"))
            continue
        record_words = set(_WORD_RE.findall(" ".join(fields.values()).lower()))
        overlap = len(issue_words & record_words) / max(len(issue_words), 1)
        if _looks_like_cb136_match(issue=issue, fields=fields):
            matches.append(CasebookMatch(fields.get("Bug ID", ""), rel_path, fields.get("Status", ""), 0.98, "install_data_loss_similarity"))
        elif overlap >= 0.18:
            matches.append(CasebookMatch(fields.get("Bug ID", ""), rel_path, fields.get("Status", ""), round(overlap, 3), "title_body_similarity"))
    ordered = sorted(matches, key=lambda match: match.score, reverse=True)
    high_confidence = [match for match in ordered if match.score >= 0.9]
    if high_confidence:
        return high_confidence
    return [match for match in ordered if match.score >= 0.25][:5]


def build_governance_plan(
    *,
    issue: Mapping[str, object],
    match: CasebookMatch | None,
    fixed_version: str,
) -> GovernanceMutationPlan:
    if match is None:
        return GovernanceMutationPlan(
            action="blocked",
            casebook_id="",
            casebook_path="",
            fields={},
            blocked_reason="No matching Casebook record found; capture or select a bug before applying governance.",
        )
    return GovernanceMutationPlan(
        action="update_casebook",
        casebook_id=match.bug_id,
        casebook_path=match.path,
        fields={
            "GitHub Issue(s)": format_issue_markdown_link(repo=str(issue["repo"]), number=int(issue["number"])),
            "GitHub Status": "fixed_pending_release",
            "Fixed In": fixed_version,
            "Public Response": "pending",
        },
    )


def apply_governance_plan(*, repo_root: Path, mutation: GovernanceMutationPlan) -> tuple[Path, ...]:
    """Apply a Casebook field mutation and restore the preimage on validation failure."""
    if mutation.action != "update_casebook" or not mutation.casebook_path:
        raise GitHubPipelineError(mutation.blocked_reason or "no Casebook mutation is available")
    path = (repo_root / mutation.casebook_path).resolve()
    if not path.is_file():
        raise GitHubPipelineError(f"Casebook record does not exist: {mutation.casebook_path}")
    preimage = path.read_text(encoding="utf-8")
    updated = set_casebook_fields(preimage, mutation.fields)
    if updated == preimage:
        return ()
    path.write_text(updated, encoding="utf-8")
    validation = casebook_source_validation.validate_casebook_sources(repo_root=repo_root)
    if not validation.passed:
        path.write_text(preimage, encoding="utf-8")
        first = validation.issues[0]
        raise GitHubPipelineError(
            "Casebook update failed validation and was rolled back: "
            + first.render(repo_root=validation.repo_root)
        )
    sync_casebook_bug_index.sync_casebook_bug_index(repo_root=repo_root, migrate_bug_ids=False)
    return (path,)


def set_casebook_fields(text: str, fields: Mapping[str, str]) -> str:
    lines = text.splitlines()
    replaced: set[str] = set()
    for index, line in enumerate(lines):
        match = _FIELD_RE.match(line)
        if not match:
            continue
        name = match.group("name").strip()
        if name in fields:
            lines[index] = f"- {name}: {fields[name]}"
            replaced.add(name)
    missing = [(name, value) for name, value in fields.items() if name not in replaced]
    if missing and lines and lines[-1].strip():
        lines.append("")
    for name, value in missing:
        lines.extend([f"- {name}: {value}", ""])
    return "\n".join(lines).rstrip() + "\n"


def resolve_release(*, repo_root: Path, release: str) -> ReleaseInfo:
    payload = json.loads((repo_root / _RELEASES_RELATIVE).read_text(encoding="utf-8"))
    selector = release_planning_contract.normalize_release_selector(release)
    selector_key = _release_selector_key(selector)
    aliases = payload.get("aliases", {}) if isinstance(payload, Mapping) else {}
    alias_release_id = ""
    for raw_alias, raw_release_id in aliases.items():
        if _release_selector_key(str(raw_alias or "")) == selector_key:
            alias_release_id = str(raw_release_id or "").strip()
            break
    matches: list[Mapping[str, object]] = []
    for item in payload.get("releases", []):
        if not isinstance(item, Mapping):
            continue
        release_id = str(item.get("release_id", "")).strip()
        version = str(item.get("version", "")).strip()
        tag = str(item.get("tag", "")).strip()
        name = str(item.get("name", "")).strip()
        tokens = {release_id, version, tag, name}
        if alias_release_id and release_id == alias_release_id:
            matches.append(item)
        elif selector_key and selector_key in {_release_selector_key(token) for token in tokens if token}:
            matches.append(item)
    unique_matches = {
        str(item.get("release_id", "")).strip(): item
        for item in matches
        if str(item.get("release_id", "")).strip()
    }
    if len(unique_matches) == 1:
        item = next(iter(unique_matches.values()))
        version = str(item.get("version", "") or DEFAULT_FIXED_VERSION)
        release_id = str(item.get("release_id", "")).strip()
        return ReleaseInfo(
            release_id=release_id,
            version=version,
            tag=str(item.get("tag", "") or f"v{version}"),
            status=str(item.get("status", "") or "unknown"),
            shipped_utc=str(item.get("shipped_utc", "") or ""),
            closed_utc=str(item.get("closed_utc", "") or ""),
        )
    if len(unique_matches) > 1:
        release_ids = ", ".join(sorted(unique_matches))
        raise GitHubPipelineError(f"ambiguous release selector `{release}` matches {release_ids}")
    if re.fullmatch(r"\d+\.\d+\.\d+", release):
        return ReleaseInfo(
            release_id=f"release-{release.replace('.', '-')}",
            version=release,
            tag=f"v{release}",
            status="unknown",
        )
    raise GitHubPipelineError(f"unknown release selector: {release}")


def _release_selector_key(value: str) -> str:
    return str(value or "").strip().casefold()


def linked_issues_for_release(*, repo_root: Path, repo: str, fixed_version: str) -> tuple[tuple[CasebookRecord, str], ...]:
    linked: list[tuple[CasebookRecord, str]] = []
    for record in iter_casebook_records(repo_root):
        if normalize_version(record.fields.get("Fixed In", "")) != normalize_version(fixed_version):
            continue
        for issue_token in extract_issue_tokens(record.fields.get("GitHub Issue(s)", "")):
            if issue_token.startswith(f"{repo}#"):
                linked.append((record, issue_token))
    return tuple(linked)


def has_validation_evidence(record: CasebookRecord) -> bool:
    verification = record.fields.get("Verification", "").strip()
    return bool(verification) and _PLACEHOLDER_RE.match(verification) is None


def _looks_like_cb136_match(*, issue: Mapping[str, object], fields: Mapping[str, str]) -> bool:
    issue_text = f"{issue.get('title', '')}\n{issue.get('body', '')}".lower()
    record_text = " ".join(fields.values()).lower()
    return (
        fields.get("Bug ID") == "CB-136"
        and "settings.json" in issue_text
        and "ssl" in issue_text
        and "settings.json" in record_text
    )
