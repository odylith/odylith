"""Authored Greenfield-origin Project tab adapter."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    AUTHORED_PROJECTION_ORIGIN,
)
from odylith.runtime.project_intelligence.greenfield_authored_dashboard import (
    build_authored_greenfield_payload,
)


def proposal_from_sources(*, repo_root: Path, shell_payload: Mapping[str, Any]) -> dict[str, Any]:
    """Return an accepted Greenfield proposal from runtime payload or local truth."""

    from odylith.runtime.project_intelligence.greenfield_sources import _accepted_proposal
    from odylith.runtime.project_intelligence.greenfield_sources import _proposal_from_file

    for key in ("greenfield_proposal", "accepted_proposal", "proposal"):
        proposal = _accepted_proposal(shell_payload.get(key))
        if proposal:
            return proposal
    for path in (
        Path(repo_root) / "odylith" / "runtime" / "source" / "accepted-project.v1.json",
        Path(repo_root) / "odylith" / "runtime" / "source" / "greenfield-project.v1.json",
    ):
        proposal = _proposal_from_file(path)
        if proposal:
            return proposal
    return {}


def build_greenfield_payload(*, proposal: Mapping[str, Any], repo_root: Path) -> dict[str, Any]:
    """Compile the Project page only from the sealed authored projection."""

    if proposal.get("projection_origin") != AUTHORED_PROJECTION_ORIGIN:
        raise ValueError("Greenfield Project intelligence requires a sealed authored projection")
    return build_authored_greenfield_payload(proposal=proposal, repo_root=repo_root)
