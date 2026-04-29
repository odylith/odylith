"""Serializable contracts for GitHub issue intake and closeout."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

DEFAULT_FIXED_VERSION = "0.1.12"
DEFAULT_GITHUB_REPO = "odylith/odylith"


@dataclass(frozen=True)
class IssueReference:
    """A normalized GitHub issue pointer used before any network call."""

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
class IssueClassification:
    severity: str
    issue_types: tuple[str, ...]
    component: str
    confidence: str
    evidence_summary: tuple[str, ...]


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
