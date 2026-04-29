"""GitHub issue intake, governance mapping, and release closeout planning."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from odylith.runtime.governance import casebook_source_validation
from odylith.runtime.governance import sync_casebook_bug_index
from odylith.runtime.governance.github_issue_transport import GitHubPipelineError
from odylith.runtime.governance.github_issue_transport import GitHubTransport

_CASEBOOK_BUGS_RELATIVE = Path("odylith/casebook/bugs")
_RELEASES_RELATIVE = Path("odylith/radar/source/releases/releases.v1.json")
_ISSUE_URL_RE = re.compile(r"^https://github\.com/(?P<repo>[^/]+/[^/]+)/issues/(?P<number>\d+)(?:[/?#].*)?$")
_ISSUE_TOKEN_RE = re.compile(r"(?P<repo>[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)#(?P<number>\d+)")
_FIELD_RE = re.compile(r"^\s*-\s*(?P<name>[^:]+):\s*(?P<value>.*)$")
_WORD_RE = re.compile(r"[a-z0-9]{3,}")
_PLACEHOLDER_RE = re.compile(r"^(?:tbd|todo|unknown|n/?a|pending)(?:\b|[^A-Za-z0-9].*)?$", re.IGNORECASE)
_DEFAULT_REPO = "odylith/odylith"
_DEFAULT_RELEASE = "0.1.12"
_MANAGED_LABELS = {
    "severity:P0": ("Critical data loss, environment breakage, or release-blocking bug.", "b60205"),
    "severity:P1": ("High-severity product bug.", "d93f0b"),
    "severity:P2": ("Normal priority product bug.", "fbca04"),
    "type:data-loss": ("Bug can destroy, overwrite, or strand user-owned data/config.", "7f1d1d"),
    "type:install": ("Install, bootstrap, or first-run lifecycle issue.", "0052cc"),
    "type:upgrade": ("Upgrade or reinstall lifecycle issue.", "1d76db"),
    "type:trust": ("Trust bootstrap, signature, certificate, or verification issue.", "5319e7"),
    "type:ux": ("Operator experience, clarity, or adoption-friction issue.", "c2e0c6"),
    "component:migration-runtime": ("Owned by the migration-runtime component.", "0e8a16"),
    "component:install": ("Owned by install lifecycle code.", "0e8a16"),
    "release:0.1.12": ("Tracked for the v0.1.12 release lane.", "bfdadc"),
    "status:confirmed": ("Maintainers have confirmed this issue.", "ededed"),
    "status:needs-repro": ("Needs reproduction evidence before implementation.", "ededed"),
    "status:fixed-pending-release": ("Fixed on a branch but not yet publicly released.", "ededed"),
    "status:fixed-released": ("Fix is publicly released.", "ededed"),
}

@dataclass(frozen=True)
class IssueReference:
    repo: str
    number: int

    def as_dict(self) -> dict[str, Any]:
        return {"repo": self.repo, "number": self.number}


@dataclass(frozen=True)
class LabelCreationPlan:
    name: str
    description: str
    color: str

    def as_dict(self) -> dict[str, str]:
        return {"name": self.name, "description": self.description, "color": self.color}


@dataclass(frozen=True)
class CasebookMatch:
    bug_id: str
    path: str
    status: str
    score: float
    reason: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "bug_id": self.bug_id,
            "path": self.path,
            "status": self.status,
            "score": self.score,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class GovernanceMutationPlan:
    action: str
    casebook_id: str
    casebook_path: str
    fields: Mapping[str, str]
    blocked_reason: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "casebook_id": self.casebook_id,
            "casebook_path": self.casebook_path,
            "fields": dict(self.fields),
            "blocked_reason": self.blocked_reason,
        }


@dataclass(frozen=True)
class GitHubMutationPlan:
    labels_to_create: tuple[LabelCreationPlan, ...]
    labels_to_add: tuple[str, ...]
    comment_body: str
    close_decision: str
    blocked_reason: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "labels_to_create": [label.as_dict() for label in self.labels_to_create],
            "labels_to_add": list(self.labels_to_add),
            "comment_body": self.comment_body,
            "close_decision": self.close_decision,
            "blocked_reason": self.blocked_reason,
        }


@dataclass(frozen=True)
class IssueIntakePlan:
    issue: Mapping[str, Any]
    evidence_summary: tuple[str, ...]
    suspected_component: str
    severity: str
    issue_types: tuple[str, ...]
    confidence: str
    duplicate_casebook_candidates: tuple[CasebookMatch, ...]
    recommended_governance_mutation: GovernanceMutationPlan
    recommended_github_mutation: GitHubMutationPlan

    def as_dict(self) -> dict[str, Any]:
        return {
            "issue": dict(self.issue),
            "evidence_summary": list(self.evidence_summary),
            "suspected_component": self.suspected_component,
            "severity": self.severity,
            "type": list(self.issue_types),
            "confidence": self.confidence,
            "duplicate_casebook_candidates": [
                candidate.as_dict() for candidate in self.duplicate_casebook_candidates
            ],
            "recommended_governance_mutation": self.recommended_governance_mutation.as_dict(),
            "recommended_github_mutation": self.recommended_github_mutation.as_dict(),
        }


@dataclass(frozen=True)
class ReleaseCloseoutItem:
    issue: str
    issue_state: str
    casebook_id: str
    casebook_path: str
    severity: str
    github_status: str
    public_response: str
    validation_evidence: bool
    close_eligibility: str
    github_mutation: GitHubMutationPlan

    def as_dict(self) -> dict[str, Any]:
        return {
            "issue": self.issue,
            "issue_state": self.issue_state,
            "casebook_id": self.casebook_id,
            "casebook_path": self.casebook_path,
            "severity": self.severity,
            "github_status": self.github_status,
            "public_response": self.public_response,
            "validation_evidence": self.validation_evidence,
            "close_eligibility": self.close_eligibility,
            "github_mutation": self.github_mutation.as_dict(),
        }


@dataclass(frozen=True)
class ReleaseIssueCloseoutPlan:
    release: str
    fixed_version: str
    release_tag: str
    release_state: str
    public_release_available: bool
    pending: tuple[ReleaseCloseoutItem, ...]
    closable: tuple[ReleaseCloseoutItem, ...]
    blocked: tuple[ReleaseCloseoutItem, ...]
    already_closed: tuple[ReleaseCloseoutItem, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "release": self.release,
            "fixed_version": self.fixed_version,
            "release_tag": self.release_tag,
            "release_state": self.release_state,
            "public_release_available": self.public_release_available,
            "pending": [item.as_dict() for item in self.pending],
            "closable": [item.as_dict() for item in self.closable],
            "blocked": [item.as_dict() for item in self.blocked],
            "already_closed": [item.as_dict() for item in self.already_closed],
        }

def parse_issue_reference(reference: str, *, default_repo: str = _DEFAULT_REPO) -> IssueReference:
    token = str(reference or "").strip()
    if not token:
        raise ValueError("issue reference is required")
    url_match = _ISSUE_URL_RE.match(token)
    if url_match:
        return IssueReference(repo=url_match.group("repo"), number=int(url_match.group("number")))
    shorthand_match = _ISSUE_TOKEN_RE.fullmatch(token)
    if shorthand_match:
        return IssueReference(repo=shorthand_match.group("repo"), number=int(shorthand_match.group("number")))
    if token.isdigit():
        if not default_repo:
            raise ValueError("numeric issue references require --repo")
        return IssueReference(repo=default_repo, number=int(token))
    raise ValueError(f"unsupported GitHub issue reference: {reference}")


def build_triage_plan(
    *,
    issue: Mapping[str, Any],
    repo_root: Path,
    repo: str,
    existing_labels: Sequence[Mapping[str, Any]] = (),
    fixed_version: str = _DEFAULT_RELEASE,
) -> IssueIntakePlan:
    """Build a draft-first issue intake plan from fetched issue metadata."""
    normalized_issue = _normalize_issue(issue=issue, repo=repo)
    severity, issue_types, component, confidence, evidence = _classify_issue(normalized_issue)
    matches = _match_casebook_issue(repo_root=repo_root, issue=normalized_issue, repo=repo)
    governance = _build_governance_plan(
        repo_root=repo_root,
        issue=normalized_issue,
        match=matches[0] if matches else None,
        fixed_version=fixed_version,
    )
    github = _build_github_plan(
        issue=normalized_issue,
        severity=severity,
        issue_types=issue_types,
        component=component,
        casebook_id=governance.casebook_id,
        fixed_version=fixed_version,
        existing_labels=existing_labels,
    )
    return IssueIntakePlan(
        issue=normalized_issue,
        evidence_summary=tuple(evidence),
        suspected_component=component,
        severity=severity,
        issue_types=tuple(issue_types),
        confidence=confidence,
        duplicate_casebook_candidates=tuple(matches),
        recommended_governance_mutation=governance,
        recommended_github_mutation=github,
    )


def apply_governance_plan(*, repo_root: Path, plan: IssueIntakePlan) -> tuple[Path, ...]:
    """Apply the Casebook-only portion of an issue intake plan."""
    mutation = plan.recommended_governance_mutation
    if mutation.action != "update_casebook" or not mutation.casebook_path:
        raise GitHubPipelineError(mutation.blocked_reason or "no Casebook mutation is available")
    path = (repo_root / mutation.casebook_path).resolve()
    if not path.is_file():
        raise GitHubPipelineError(f"Casebook record does not exist: {mutation.casebook_path}")
    preimage = path.read_text(encoding="utf-8")
    updated = _set_casebook_fields(preimage, mutation.fields)
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


def apply_github_plan(*, repo: str, issue_number: int, plan: GitHubMutationPlan, transport: GitHubTransport) -> None:
    """Apply public GitHub mutations after the caller supplied --apply-github."""
    if plan.blocked_reason:
        raise GitHubPipelineError(plan.blocked_reason)
    for label in plan.labels_to_create:
        transport.create_label(repo=repo, name=label.name, description=label.description, color=label.color)
    if plan.labels_to_add:
        transport.add_labels(repo=repo, number=issue_number, labels=plan.labels_to_add)
    if plan.comment_body:
        transport.comment_issue(repo=repo, number=issue_number, body=plan.comment_body)
    if plan.close_decision == "close":
        transport.close_issue(repo=repo, number=issue_number)


def build_release_closeout_plan(
    *,
    repo_root: Path,
    release: str,
    repo: str,
    transport: GitHubTransport | None = None,
) -> ReleaseIssueCloseoutPlan:
    """Build a release issue closeout plan from Casebook source truth."""
    release_info = _resolve_release(repo_root=repo_root, release=release)
    fixed_version = release_info["version"]
    release_tag = release_info["tag"]
    release_state = release_info["status"]
    public_release = False
    if release_state == "shipped" and transport is not None:
        public_release = transport.get_release_by_tag(repo=repo, tag=release_tag) is not None

    pending: list[ReleaseCloseoutItem] = []
    closable: list[ReleaseCloseoutItem] = []
    blocked: list[ReleaseCloseoutItem] = []
    already_closed: list[ReleaseCloseoutItem] = []
    for record in _iter_casebook_records(repo_root):
        if _normalize_version(record.fields.get("Fixed In", "")) != _normalize_version(fixed_version):
            continue
        issues = _extract_issue_tokens(record.fields.get("GitHub Issue(s)", ""))
        for issue_token in issues:
            if not issue_token.startswith(f"{repo}#"):
                continue
            issue_state = _fetch_issue_state(transport=transport, issue_token=issue_token)
            item = _build_closeout_item(
                repo_root=repo_root,
                record=record,
                issue_token=issue_token,
                issue_state=issue_state,
                fixed_version=fixed_version,
                release_tag=release_tag,
                public_release_available=public_release,
            )
            if item.close_eligibility == "blocked":
                blocked.append(item)
            elif item.close_eligibility == "closable":
                closable.append(item)
            elif item.close_eligibility == "already_closed":
                already_closed.append(item)
            else:
                pending.append(item)
    return ReleaseIssueCloseoutPlan(
        release=release_info["release_id"],
        fixed_version=fixed_version,
        release_tag=release_tag,
        release_state=release_state,
        public_release_available=public_release,
        pending=tuple(pending),
        closable=tuple(closable),
        blocked=tuple(blocked),
        already_closed=tuple(already_closed),
    )


def _normalize_issue(*, issue: Mapping[str, Any], repo: str) -> dict[str, Any]:
    labels = issue.get("labels", [])
    label_names = [str(label.get("name", "")) for label in labels if isinstance(label, Mapping)]
    return {
        "repo": repo,
        "number": int(issue.get("number", 0)),
        "title": str(issue.get("title", "")).strip(),
        "state": str(issue.get("state", "")).strip().lower() or "open",
        "url": str(issue.get("html_url", "") or issue.get("url", "")).strip()
        or f"https://github.com/{repo}/issues/{issue.get('number')}",
        "author": _author_login(issue.get("author") or issue.get("user")),
        "created_at": str(issue.get("createdAt", issue.get("created_at", ""))),
        "updated_at": str(issue.get("updatedAt", issue.get("updated_at", ""))),
        "body": str(issue.get("body", "")).strip(),
        "labels": tuple(sorted(name for name in label_names if name)),
    }


def _author_login(value: Any) -> str:
    if isinstance(value, Mapping):
        return str(value.get("login", "")).strip()
    return str(value or "").strip()


def _classify_issue(issue: Mapping[str, Any]) -> tuple[str, list[str], str, str, list[str]]:
    text = f"{issue.get('title', '')}\n{issue.get('body', '')}".lower()
    issue_types: list[str] = []
    evidence: list[str] = []
    severity = "P2"
    component = "install"
    confidence = "medium"
    if any(token in text for token in ("data loss", "destroy", "overwrote", "overwrite", "credentials")):
        severity = "P0"
        issue_types.append("data-loss")
        evidence.append("User-owned settings or credentials can be overwritten or stranded.")
    if any(token in text for token in ("install", "installation", "partial")):
        issue_types.append("install")
        evidence.append("Failure occurs during install or partial install lifecycle.")
    has_trust_trigger = any(token in text for token in ("ssl", "certificate", "vpn", "intercept"))
    if has_trust_trigger:
        issue_types.append("trust")
        evidence.append("Enterprise SSL interception or trust-bootstrap failure is part of the trigger.")
    if any(token in text for token in (".claude/settings.json", "claude code", ".codex", "hooks")):
        component = "migration-runtime"
        confidence = "high"
        evidence.append("Host AI settings and hook activation are migration-gated install surfaces.")
    if "upgrade" in text or "reinstall" in text:
        issue_types.append("upgrade")
    if not issue_types:
        issue_types.append("ux")
    deduped_types = _dedupe(issue_types)
    if "data-loss" in deduped_types and "install" in deduped_types:
        deduped_types = [item for item in deduped_types if item != "trust"]
    return severity, deduped_types, component, confidence, evidence or ["Issue needs maintainer classification."]


def _build_governance_plan(
    *,
    repo_root: Path,
    issue: Mapping[str, Any],
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
            "GitHub Issue(s)": f"{issue['repo']}#{issue['number']}",
            "GitHub Status": "fixed_pending_release",
            "Fixed In": fixed_version,
            "Public Response": "pending",
        },
    )


def _build_github_plan(
    *,
    issue: Mapping[str, Any],
    severity: str,
    issue_types: Sequence[str],
    component: str,
    casebook_id: str,
    fixed_version: str,
    existing_labels: Sequence[Mapping[str, Any]],
) -> GitHubMutationPlan:
    desired = ["bug", f"severity:{severity}", *(f"type:{item}" for item in issue_types), f"component:{component}"]
    desired.extend([f"release:{fixed_version}", "status:fixed-pending-release"])
    desired = _dedupe(desired)
    existing_label_names = {str(label.get("name", "")) for label in existing_labels if isinstance(label, Mapping)}
    issue_labels = set(issue.get("labels", ()))
    labels_to_create = tuple(
        LabelCreationPlan(name=name, description=_MANAGED_LABELS[name][0], color=_MANAGED_LABELS[name][1])
        for name in desired
        if name != "bug" and name in _MANAGED_LABELS and name not in existing_label_names
    )
    labels_to_add = tuple(name for name in desired if name not in issue_labels)
    comment = _render_triage_comment(
        casebook_id=casebook_id,
        fixed_version=fixed_version,
        evidence=issue.get("body", ""),
    )
    return GitHubMutationPlan(
        labels_to_create=labels_to_create,
        labels_to_add=labels_to_add,
        comment_body=comment,
        close_decision="leave_open_until_release",
    )


def _render_triage_comment(*, casebook_id: str, fixed_version: str, evidence: str) -> str:
    casebook = casebook_id or "a Casebook bug"
    validation = "Validation evidence is recorded in the linked Casebook record."
    if "settings.json" in evidence and "SSL" in evidence.upper():
        validation = (
            "Validation covers failed install before runtime activation, additive Claude/Codex settings merges, "
            "preimage preservation, invalid JSON refusal, and symlinked managed-asset refusal."
        )
    return (
        "Confirmed. We captured this as "
        f"{casebook} and fixed it on the `v{fixed_version}` branch.\n\n"
        f"{validation}\n\n"
        f"This issue stays open until v{fixed_version} is publicly released; release closeout will post the "
        "released-version note and close it after artifacts are available."
    )


@dataclass(frozen=True)
class _CasebookRecord:
    path: Path
    fields: Mapping[str, str]

    @property
    def bug_id(self) -> str:
        return self.fields.get("Bug ID", "")


def _iter_casebook_records(repo_root: Path) -> tuple[_CasebookRecord, ...]:
    records: list[_CasebookRecord] = []
    for path in casebook_source_validation.iter_casebook_bug_markdown_paths(repo_root=repo_root):
        fields = _parse_casebook_fields(path.read_text(encoding="utf-8"))
        if fields:
            records.append(_CasebookRecord(path=path, fields=fields))
    return tuple(records)


def _parse_casebook_fields(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in text.splitlines():
        match = _FIELD_RE.match(line)
        if match:
            fields[match.group("name").strip()] = match.group("value").strip()
    return fields


def _match_casebook_issue(*, repo_root: Path, issue: Mapping[str, Any], repo: str) -> list[CasebookMatch]:
    issue_token = f"{repo}#{issue['number']}"
    issue_words = set(_WORD_RE.findall(f"{issue.get('title', '')} {issue.get('body', '')}".lower()))
    matches: list[CasebookMatch] = []
    for record in _iter_casebook_records(repo_root):
        rel_path = record.path.relative_to(repo_root).as_posix()
        fields = record.fields
        if issue_token in fields.get("GitHub Issue(s)", ""):
            matches.append(CasebookMatch(fields.get("Bug ID", ""), rel_path, fields.get("Status", ""), 1.0, "explicit_github_link"))
            continue
        record_text = " ".join(fields.values()).lower()
        record_words = set(_WORD_RE.findall(record_text))
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


def _looks_like_cb136_match(*, issue: Mapping[str, Any], fields: Mapping[str, str]) -> bool:
    issue_text = f"{issue.get('title', '')}\n{issue.get('body', '')}".lower()
    record_text = " ".join(fields.values()).lower()
    return (
        fields.get("Bug ID") == "CB-136"
        and "settings.json" in issue_text
        and "ssl" in issue_text
        and "settings.json" in record_text
    )


def _set_casebook_fields(text: str, fields: Mapping[str, str]) -> str:
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


def _resolve_release(*, repo_root: Path, release: str) -> dict[str, str]:
    payload = json.loads((repo_root / _RELEASES_RELATIVE).read_text(encoding="utf-8"))
    aliases = payload.get("aliases", {}) if isinstance(payload, Mapping) else {}
    release_id = str(aliases.get(release, release))
    for item in payload.get("releases", []):
        if isinstance(item, Mapping) and str(item.get("release_id", "")) == release_id:
            return {
                "release_id": release_id,
                "version": str(item.get("version", "") or _DEFAULT_RELEASE),
                "tag": str(item.get("tag", "") or f"v{item.get('version', _DEFAULT_RELEASE)}"),
                "status": str(item.get("status", "") or "unknown"),
            }
    if re.fullmatch(r"\d+\.\d+\.\d+", release):
        return {"release_id": f"release-{release.replace('.', '-')}", "version": release, "tag": f"v{release}", "status": "unknown"}
    raise GitHubPipelineError(f"unknown release selector: {release}")


def _build_closeout_item(
    *,
    repo_root: Path,
    record: _CasebookRecord,
    issue_token: str,
    issue_state: str,
    fixed_version: str,
    release_tag: str,
    public_release_available: bool,
) -> ReleaseCloseoutItem:
    severity = record.fields.get("Severity", "")
    validation_evidence = bool(record.fields.get("Verification", "").strip()) and not _PLACEHOLDER_RE.match(
        record.fields.get("Verification", "")
    )
    github_status = record.fields.get("GitHub Status", "")
    public_response = record.fields.get("Public Response", "")
    if issue_state == "closed":
        eligibility = "already_closed"
        mutation = GitHubMutationPlan((), (), "", "already_closed")
    elif not github_status or not public_response:
        eligibility = "blocked"
        mutation = GitHubMutationPlan((), (), "", "blocked", "Linked fixed issue is missing GitHub Status or Public Response.")
    elif severity in {"P0", "P1"} and not validation_evidence:
        eligibility = "blocked"
        mutation = GitHubMutationPlan((), (), "", "blocked", "P0/P1 linked issues require validation evidence before closeout.")
    elif public_release_available:
        eligibility = "closable"
        mutation = GitHubMutationPlan(
            labels_to_create=(),
            labels_to_add=("status:fixed-released",),
            comment_body=f"Released in `{release_tag}`. Closing this because the fixed version is now publicly available.",
            close_decision="close",
        )
    else:
        eligibility = "pending_release"
        mutation = GitHubMutationPlan(
            labels_to_create=(),
            labels_to_add=("status:fixed-pending-release",),
            comment_body=f"Fixed for `v{fixed_version}` and pending public release. This will close after release artifacts are available.",
            close_decision="leave_open_until_release",
        )
    return ReleaseCloseoutItem(
        issue=issue_token,
        issue_state=issue_state,
        casebook_id=record.bug_id,
        casebook_path=record.path.relative_to(repo_root).as_posix(),
        severity=severity,
        github_status=github_status,
        public_response=public_response,
        validation_evidence=validation_evidence,
        close_eligibility=eligibility,
        github_mutation=mutation,
    )


def _extract_issue_tokens(value: str) -> tuple[str, ...]:
    return tuple(f"{match.group('repo')}#{match.group('number')}" for match in _ISSUE_TOKEN_RE.finditer(value or ""))


def _fetch_issue_state(*, transport: GitHubTransport | None, issue_token: str) -> str:
    if transport is None:
        return "unknown"
    match = _ISSUE_TOKEN_RE.fullmatch(issue_token)
    if not match:
        return "unknown"
    try:
        issue = transport.get_issue(repo=match.group("repo"), number=int(match.group("number")))
    except Exception:
        return "unknown"
    return str(issue.get("state", "unknown")).lower() or "unknown"


def _normalize_version(value: str) -> str:
    return str(value or "").strip().lstrip("v")


def _dedupe(values: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result
