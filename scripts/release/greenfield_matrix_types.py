"""Serializable result models for greenfield release matrix proof."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class GreenfieldArtifactCounts:
    radar_workstreams: int = 0
    registry_component_specs: int = 0
    atlas_mermaid_sources: int = 0
    compass_records: int = 0
    release_records: int = 0
    program_records: int = 0
    project_brief_records: int = 0
    trace_nodes: int = 0
    trace_workstreams: int = 0
    rendered_surfaces: int = 0
    rendered_surface_payloads: int = 0
    atlas_rendered_assets: int = 0
    domain_term_hits: int = 0
    required_domain_terms: int = 0
    project_implementation_prompts: int = 0

    def to_dict(self) -> dict[str, int]:
        return asdict(self)


@dataclass(frozen=True)
class GreenfieldQualityVerdict:
    passed: bool
    issues: tuple[str, ...]
    lenses: Mapping[str, bool]
    scores: Mapping[str, int]
    score: int
    score_explanation: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "issues": list(self.issues),
            "lenses": dict(self.lenses),
            "scores": dict(self.scores),
            "score": self.score,
            "score_explanation": list(self.score_explanation),
        }


@dataclass(frozen=True)
class GreenfieldMatrixResult:
    name: str
    status: str
    create_seconds: float
    counts: GreenfieldArtifactCounts
    quality: GreenfieldQualityVerdict
    browser_surface_issues: tuple[str, ...] = ()
    browser_surface_proof_attempted: bool = False
    create_returncode: int = 0
    failure_detail: str = ""
    create_stdout_excerpt: str = ""
    create_stderr_excerpt: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "create_seconds": self.create_seconds,
            "create_returncode": self.create_returncode,
            "counts": self.counts.to_dict(),
            "quality": self.quality.to_dict(),
            "browser_surface_issues": list(self.browser_surface_issues),
            "browser_surface_proof_attempted": self.browser_surface_proof_attempted,
            "failure_detail": self.failure_detail,
            "create_stdout_excerpt": self.create_stdout_excerpt,
            "create_stderr_excerpt": self.create_stderr_excerpt,
        }


@dataclass(frozen=True)
class GreenfieldRescueSmokeResult:
    status: str
    cli_create_seconds: float
    counts: GreenfieldArtifactCounts
    issues: tuple[str, ...]
    manifest: Mapping[str, Any]
    proof_scope: str = "synthetic_typed_probe_wiring_only"
    natural_rescue_quality_proven: bool = False
    create_returncode: int = 0

    @property
    def passed(self) -> bool:
        return self.status == "passed" and not self.issues

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "cli_create_seconds": self.cli_create_seconds,
            "create_returncode": self.create_returncode,
            "counts": self.counts.to_dict(),
            "issues": list(self.issues),
            "manifest": dict(self.manifest),
            "proof_scope": self.proof_scope,
            "natural_rescue_quality_proven": self.natural_rescue_quality_proven,
        }


__all__ = [
    "GreenfieldArtifactCounts",
    "GreenfieldMatrixResult",
    "GreenfieldQualityVerdict",
    "GreenfieldRescueSmokeResult",
]
