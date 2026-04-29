"""Classification, label, comment, and closeout policy for GitHub issues."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from odylith.runtime.governance.github_issue_casebook import CasebookRecord
from odylith.runtime.governance.github_issue_casebook import has_validation_evidence
from odylith.runtime.governance.github_issue_models import GitHubMutationPlan
from odylith.runtime.governance.github_issue_models import IssueClassification
from odylith.runtime.governance.github_issue_models import LabelCreationPlan
from odylith.runtime.governance.github_issue_models import ReleaseCloseoutItem
from odylith.runtime.governance.github_issue_references import dedupe

MANAGED_LABELS = {
    "bug": ("Something is not working as intended.", "d73a4a"),
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
class ClassificationRule:
    tokens: tuple[str, ...]
    evidence: str
    issue_type: str = ""
    severity: str = ""
    component: str = ""
    confidence: str = ""

    def matches(self, text: str) -> bool:
        return any(token in text for token in self.tokens)


_CLASSIFICATION_RULES = (
    ClassificationRule(
        tokens=("data loss", "destroy", "overwrote", "overwrite", "credentials"),
        severity="P0",
        issue_type="data-loss",
        evidence="User-owned settings or credentials can be overwritten or stranded.",
    ),
    ClassificationRule(
        tokens=("install", "installation", "partial"),
        issue_type="install",
        evidence="Failure occurs during install or partial install lifecycle.",
    ),
    ClassificationRule(
        tokens=("ssl", "certificate", "vpn", "intercept"),
        issue_type="trust",
        evidence="Enterprise SSL interception or trust-bootstrap failure is part of the trigger.",
    ),
    ClassificationRule(
        tokens=(".claude/settings.json", "claude code", ".codex", "hooks"),
        component="migration-runtime",
        confidence="high",
        evidence="Host AI settings and hook activation are migration-gated install surfaces.",
    ),
    ClassificationRule(
        tokens=("upgrade", "reinstall"),
        issue_type="upgrade",
        evidence="Failure reaches upgrade or reinstall lifecycle behavior.",
    ),
)


def normalize_issue(*, issue: Mapping[str, Any], repo: str) -> dict[str, Any]:
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


def classify_issue(issue: Mapping[str, Any]) -> IssueClassification:
    """Classify an issue using ordered additive rules.

    Rules may add evidence, issue types, severity, component ownership, or
    confidence. Later component/confidence rules intentionally refine earlier
    lifecycle rules, while label noise such as trust under a stronger
    data-loss/install signal is suppressed before the plan is serialized.
    """
    text = f"{issue.get('title', '')}\n{issue.get('body', '')}".lower()
    severity = "P2"
    component = "install"
    confidence = "medium"
    issue_types: list[str] = []
    evidence: list[str] = []
    for rule in _CLASSIFICATION_RULES:
        if not rule.matches(text):
            continue
        if rule.severity:
            severity = rule.severity
        if rule.issue_type:
            issue_types.append(rule.issue_type)
        if rule.component:
            component = rule.component
        if rule.confidence:
            confidence = rule.confidence
        evidence.append(rule.evidence)
    deduped_types = dedupe(issue_types) or ["ux"]
    if "data-loss" in deduped_types and "install" in deduped_types:
        deduped_types = [item for item in deduped_types if item != "trust"]
    return IssueClassification(
        severity=severity,
        issue_types=tuple(deduped_types),
        component=component,
        confidence=confidence,
        evidence_summary=tuple(evidence) or ("Issue needs maintainer classification.",),
    )


def build_github_plan(
    *,
    issue: Mapping[str, Any],
    classification: IssueClassification,
    casebook_id: str,
    fixed_version: str,
    existing_labels: Sequence[Mapping[str, Any]],
    governance_blocked_reason: str = "",
) -> GitHubMutationPlan:
    """Build public GitHub mutations, but block public apply without Casebook truth."""
    status_label = "status:fixed-pending-release" if casebook_id else "status:needs-repro"
    desired = [
        "bug",
        f"severity:{classification.severity}",
        *(f"type:{item}" for item in classification.issue_types),
        f"component:{classification.component}",
        status_label,
    ]
    if casebook_id:
        desired.insert(-1, f"release:{fixed_version}")
    desired = dedupe(desired)
    issue_labels = set(issue.get("labels", ()))
    existing_label_names = {str(label.get("name", "")) for label in existing_labels if isinstance(label, Mapping)}
    labels_to_create = tuple(
        LabelCreationPlan(name=name, description=MANAGED_LABELS[name][0], color=MANAGED_LABELS[name][1])
        for name in desired
        if name in MANAGED_LABELS and name not in existing_label_names and name not in issue_labels
    )
    labels_to_add = tuple(name for name in desired if name not in issue_labels)
    if not casebook_id:
        # Public issue responses must not claim confirmation or fixed-in status
        # until the internal Casebook record exists and is linked.
        return GitHubMutationPlan(
            labels_to_create=labels_to_create,
            labels_to_add=labels_to_add,
            comment_body="",
            close_decision="blocked",
            blocked_reason=governance_blocked_reason or "No Casebook record is linked yet.",
        )
    return GitHubMutationPlan(
        labels_to_create=labels_to_create,
        labels_to_add=labels_to_add,
        comment_body=render_triage_comment(casebook_id=casebook_id, fixed_version=fixed_version, evidence=issue.get("body", "")),
        close_decision="leave_open_until_release",
    )


def build_closeout_item(
    *,
    repo_root: Path,
    record: CasebookRecord,
    issue_token: str,
    issue_state: str,
    fixed_version: str,
    release_tag: str,
    public_release_available: bool,
) -> ReleaseCloseoutItem:
    """Decide one linked issue's release-closeout state."""
    severity = record.fields.get("Severity", "")
    github_status = record.fields.get("GitHub Status", "")
    public_response = record.fields.get("Public Response", "")
    validation_evidence = has_validation_evidence(record)
    if issue_state == "closed":
        eligibility = "already_closed"
        mutation = GitHubMutationPlan((), (), "", "already_closed")
    elif not github_status or not public_response:
        eligibility = "blocked"
        mutation = GitHubMutationPlan((), (), "", "blocked", "Linked fixed issue is missing GitHub Status or Public Response.")
    elif severity in {"P0", "P1"} and not validation_evidence:
        eligibility = "blocked"
        mutation = GitHubMutationPlan((), (), "", "blocked", "P0/P1 linked issues require validation evidence before closeout.")
    elif public_release_available and issue_state != "open":
        # A published release is not enough to close an issue if the pipeline
        # cannot prove that the target public issue is still open.
        eligibility = "blocked"
        mutation = GitHubMutationPlan((), (), "", "blocked", "Public release is available, but issue state could not be confirmed open.")
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


def render_triage_comment(*, casebook_id: str, fixed_version: str, evidence: str) -> str:
    validation = "Validation evidence is recorded in the linked Casebook record."
    if "settings.json" in evidence and "SSL" in evidence.upper():
        validation = (
            "Validation covers failed install before runtime activation, additive Claude/Codex settings merges, "
            "preimage preservation, invalid JSON refusal, and symlinked managed-asset refusal."
        )
    return (
        f"Confirmed. We captured this as {casebook_id} and fixed it on the `v{fixed_version}` branch.\n\n"
        f"{validation}\n\n"
        f"This issue stays open until v{fixed_version} is publicly released; release closeout will post the "
        "released-version note and close it after artifacts are available."
    )


def _author_login(value: Any) -> str:
    if isinstance(value, Mapping):
        return str(value.get("login", "")).strip()
    return str(value or "").strip()
