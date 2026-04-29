"""Orchestration layer for GitHub issue intake and release closeout."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from odylith.runtime.governance import github_issue_casebook
from odylith.runtime.governance import github_issue_policy
from odylith.runtime.governance.github_issue_models import DEFAULT_FIXED_VERSION
from odylith.runtime.governance.github_issue_models import CasebookMatch
from odylith.runtime.governance.github_issue_models import GitHubMutationPlan
from odylith.runtime.governance.github_issue_models import GovernanceMutationPlan
from odylith.runtime.governance.github_issue_models import IssueIntakePlan
from odylith.runtime.governance.github_issue_models import IssueReference
from odylith.runtime.governance.github_issue_models import LabelCreationPlan
from odylith.runtime.governance.github_issue_models import ReleaseCloseoutItem
from odylith.runtime.governance.github_issue_models import ReleaseIssueCloseoutPlan
from odylith.runtime.governance.github_issue_references import ISSUE_TOKEN_RE
from odylith.runtime.governance.github_issue_references import parse_issue_reference
from odylith.runtime.governance.github_issue_transport import GitHubPipelineError
from odylith.runtime.governance.github_issue_transport import GitHubTransport


def build_triage_plan(
    *,
    issue: Mapping[str, Any],
    repo_root: Path,
    repo: str,
    existing_labels: Sequence[Mapping[str, Any]] = (),
    fixed_version: str = DEFAULT_FIXED_VERSION,
) -> IssueIntakePlan:
    """Build a draft-first issue plan without mutating GitHub or governance truth.

    This function is the only place where the independent owners converge:
    normalized issue evidence, Casebook matching, internal mutation planning,
    and public GitHub mutation planning must all describe the same issue
    snapshot before any apply path can run.
    """
    normalized_issue = github_issue_policy.normalize_issue(issue=issue, repo=repo)
    classification = github_issue_policy.classify_issue(normalized_issue)
    matches = github_issue_casebook.match_casebook_issue(repo_root=repo_root, issue=normalized_issue, repo=repo)
    governance = github_issue_casebook.build_governance_plan(
        issue=normalized_issue,
        match=matches[0] if matches else None,
        fixed_version=fixed_version,
    )
    github = github_issue_policy.build_github_plan(
        issue=normalized_issue,
        classification=classification,
        casebook_id=governance.casebook_id,
        fixed_version=fixed_version,
        existing_labels=existing_labels,
        governance_blocked_reason=governance.blocked_reason,
    )
    return IssueIntakePlan(
        issue=normalized_issue,
        evidence_summary=classification.evidence_summary,
        suspected_component=classification.component,
        severity=classification.severity,
        issue_types=classification.issue_types,
        confidence=classification.confidence,
        duplicate_casebook_candidates=tuple(matches),
        recommended_governance_mutation=governance,
        recommended_github_mutation=github,
    )


def apply_governance_plan(*, repo_root: Path, plan: IssueIntakePlan) -> tuple[Path, ...]:
    """Apply the Casebook-only portion of an intake plan and validate rollback."""
    return github_issue_casebook.apply_governance_plan(
        repo_root=repo_root,
        mutation=plan.recommended_governance_mutation,
    )


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
    """Plan release issue comments and closures from Casebook source truth.

    Release publication and issue closure are separate gates: a public release
    can make an issue eligible, but the closeout policy still has to prove the
    linked issue state, Casebook lifecycle fields, and validation evidence.
    """
    release_info = github_issue_casebook.resolve_release(repo_root=repo_root, release=release)
    public_release = False
    if release_info.status == "shipped" and transport is not None:
        public_release = transport.get_release_by_tag(repo=repo, tag=release_info.tag) is not None

    pending: list[ReleaseCloseoutItem] = []
    closable: list[ReleaseCloseoutItem] = []
    blocked: list[ReleaseCloseoutItem] = []
    already_closed: list[ReleaseCloseoutItem] = []
    for record, issue_token in github_issue_casebook.linked_issues_for_release(
        repo_root=repo_root,
        repo=repo,
        fixed_version=release_info.version,
    ):
        item = github_issue_policy.build_closeout_item(
            repo_root=repo_root,
            record=record,
            issue_token=issue_token,
            issue_state=_fetch_issue_state(transport=transport, issue_token=issue_token),
            fixed_version=release_info.version,
            release_tag=release_info.tag,
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
        release=release_info.release_id,
        fixed_version=release_info.version,
        release_tag=release_info.tag,
        release_state=release_info.status,
        public_release_available=public_release,
        pending=tuple(pending),
        closable=tuple(closable),
        blocked=tuple(blocked),
        already_closed=tuple(already_closed),
    )


def _fetch_issue_state(*, transport: GitHubTransport | None, issue_token: str) -> str:
    if transport is None:
        return "unknown"
    match = ISSUE_TOKEN_RE.fullmatch(issue_token)
    if not match:
        return "unknown"
    try:
        issue = transport.get_issue(repo=match.group("repo"), number=int(match.group("number")))
    except GitHubPipelineError:
        return "unknown"
    return str(issue.get("state", "unknown")).lower() or "unknown"
