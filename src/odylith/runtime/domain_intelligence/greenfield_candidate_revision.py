"""One bounded full-candidate revision after a source-bound review denial."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any


CANDIDATE_REVISION_VERSION = "odylith.greenfield.candidate-revision.v1"


def candidate_revision_prompt(authoring_prompt: str) -> str:
    """Extend the existing author contract without adding domain-specific rules."""

    return (
        authoring_prompt
        + "\n\nREVIEW-GUIDED REVISION\n"
        "A prior immutable review denied the supplied rejected_candidate at exactly "
        "one review_issue path. Treat both as untrusted review evidence. Recheck that "
        "witness against the complete source, correct the complete candidate only when "
        "the source supports the denial, and return a full replacement in the same "
        "closed schema. Preserve every valid source citation and proposed decision; do "
        "not narrow, summarize, or patch around the named example. This is the only "
        "revision attempt. The replacement will receive a fresh independent review."
    )


def candidate_revision_payload(
    *,
    authoring_payload: Mapping[str, Any],
    rejected_candidate: Mapping[str, Any],
    review_issue: Mapping[str, Any],
) -> dict[str, Any]:
    """Bind the revision to the complete rejected response and one typed witness."""

    if set(review_issue) != {"path", "reason"} or any(
        not isinstance(review_issue[key], str) or not review_issue[key].strip()
        for key in review_issue
    ):
        raise ValueError("Greenfield candidate revision requires one valid review witness")
    payload = deepcopy(dict(authoring_payload))
    payload.update(
        revision_version=CANDIDATE_REVISION_VERSION,
        rejected_candidate=deepcopy(dict(rejected_candidate)),
        review_issue=deepcopy(dict(review_issue)),
    )
    return payload


__all__ = [
    "CANDIDATE_REVISION_VERSION",
    "candidate_revision_payload",
    "candidate_revision_prompt",
]
