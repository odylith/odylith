"""Run installed greenfield post-confirm simulations against a local release."""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from dataclasses import asdict
from dataclasses import dataclass
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from types import SimpleNamespace
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from local_release_smoke import _cleanup_smoke_temp_root  # noqa: E402
from local_release_smoke import _local_release_env  # noqa: E402
from local_release_smoke import _serve_directory  # noqa: E402
from odylith.runtime.artifact_quality.greenfield_package_quality import (  # noqa: E402
    greenfield_rendered_package_quality_issues,
)


POST_CONFIRM_BUDGET_SECONDS = 60.0
COMMAND_TIMEOUT_SECONDS = 300
QUALITY_MATRIX_VERSION = "greenfield-post-confirm-installed-matrix-v1"
REPO_ROOT = Path(__file__).resolve().parents[2]
GENERATED_TEXT_SUFFIXES = {".html", ".js", ".json", ".jsonl", ".md", ".mmd"}
RADAR_WORKSTREAM_SKIP_FILES = {"AGENTS.md", "INDEX.md", "README.md"}
REQUIRED_RENDERED_SURFACES = (
    "odylith/radar/radar.html",
    "odylith/registry/registry.html",
    "odylith/atlas/atlas.html",
    "odylith/compass/compass.html",
    "odylith/index.html",
)


@dataclass(frozen=True)
class GreenfieldMatrixCase:
    name: str
    prompt: str
    required_terms: tuple[str, ...]

    @property
    def slug(self) -> str:
        return "-".join(token for token in self.name.casefold().split() if token)


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
    domain_term_hits: int = 0

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
    create_returncode: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "create_seconds": self.create_seconds,
            "create_returncode": self.create_returncode,
            "counts": self.counts.to_dict(),
            "quality": self.quality.to_dict(),
        }


def default_cases() -> tuple[GreenfieldMatrixCase, ...]:
    """Return the high-variance release matrix used for greenfield proof."""

    return (
        GreenfieldMatrixCase(
            name="flood shelter intake",
            prompt=(
                "Create a greenfield proposal for a flood shelter intake system that helps city staff register "
                "displaced residents, match household needs to shelter capacity, track medical and accessibility "
                "constraints, preserve consent evidence, and produce a daily placement readiness report."
            ),
            required_terms=("flood", "shelter", "resident", "placement"),
        ),
        GreenfieldMatrixCase(
            name="pediatric agency practice",
            prompt=(
                "Create a greenfield proposal for a pediatric therapy agency practice workspace that coordinates "
                "referral intake, guardian consent, therapist assignment, care-plan readiness, visit evidence, "
                "and exception review for children served across multiple schools."
            ),
            required_terms=("pediatric", "therapy", "guardian", "care"),
        ),
        GreenfieldMatrixCase(
            name="semiconductor lab custody",
            prompt=(
                "Create a greenfield proposal for a semiconductor reliability lab custody platform that receives "
                "wafer lot samples, records chamber exposure conditions, preserves chain-of-custody evidence, "
                "tracks failed stress runs, and prepares release readiness proof for engineering review."
            ),
            required_terms=("semiconductor", "wafer", "custody", "reliability"),
        ),
        GreenfieldMatrixCase(
            name="port berth carbon tariff",
            prompt=(
                "Create a greenfield proposal for a port berth carbon tariff planner that lets port operations "
                "compare vessel schedules, berth windows, shore-power availability, emissions evidence, tariff "
                "exceptions, and operator signoff before publishing a daily berth plan."
            ),
            required_terms=("port", "berth", "tariff", "emissions"),
        ),
        GreenfieldMatrixCase(
            name="security disclosure council",
            prompt=(
                "Create a greenfield proposal for a multi-party security disclosure council that coordinates "
                "external vulnerability reports, affected partner review, embargo decisions, evidence custody, "
                "legal signoff, and public advisory release readiness without personalized notification campaigns "
                "in the first release."
            ),
            required_terms=("security", "disclosure", "embargo", "evidence"),
        ),
    )


def run_matrix(
    *,
    dist_dir: Path,
    version: str,
    temp_parent: Path,
    cases: Sequence[GreenfieldMatrixCase] = (),
) -> tuple[GreenfieldMatrixResult, ...]:
    """Run the real installed greenfield create path for each matrix case."""

    selected_cases = tuple(cases) or default_cases()
    release_dir = Path(dist_dir).expanduser().resolve()
    install_script = release_dir / "install.sh"
    if not install_script.is_file():
        raise FileNotFoundError(f"missing local release install script: {install_script}")
    run_root = Path(temp_parent).expanduser().resolve() / f"odylith-greenfield-matrix-{uuid.uuid4().hex[:8]}"
    run_root.mkdir(parents=True, exist_ok=False)
    server, base_url = _serve_directory(release_dir)
    results: list[GreenfieldMatrixResult] = []
    try:
        for case in selected_cases:
            repo_root = run_root / f"odylith-sim-{case.slug}-{uuid.uuid4().hex[:8]}"
            result = _run_case(
                case=case,
                repo_root=repo_root,
                install_script=install_script,
                base_url=base_url,
                version=version,
            )
            results.append(result)
            _cleanup_repo_before_next(repo_root)
    finally:
        server.shutdown()
        server.server_close()
        _cleanup_smoke_temp_root(run_root)
    return tuple(results)


def _run_case(
    *,
    case: GreenfieldMatrixCase,
    repo_root: Path,
    install_script: Path,
    base_url: str,
    version: str,
) -> GreenfieldMatrixResult:
    repo_root.mkdir(parents=True)
    env = _local_release_env(base_url=base_url, version=version)
    _run(cwd=repo_root, env=env, command=["git", "init"], timeout=60)
    install = _run(cwd=repo_root, env=env, command=["bash", str(install_script)], timeout=COMMAND_TIMEOUT_SECONDS)
    if install.returncode != 0:
        return _failed_case(case, repo_root, "install_failed", install.returncode, install.stderr or install.stdout)
    propose = _run(
        cwd=repo_root,
        env=env,
        command=["./.odylith/bin/odylith", "greenfield", "propose", "--repo-root", ".", "--prompt", case.prompt],
        timeout=120,
    )
    if propose.returncode != 0:
        return _failed_case(case, repo_root, "propose_failed", propose.returncode, propose.stderr or propose.stdout)
    intent_path = repo_root / ".odylith/runtime/greenfield/confirmed-intent.md"
    intent_path.parent.mkdir(parents=True, exist_ok=True)
    intent_path.write_text(propose.stdout, encoding="utf-8")
    started = time.perf_counter()
    create = _run(
        cwd=repo_root,
        env=env,
        command=[
            "./.odylith/bin/odylith",
            "greenfield",
            "create",
            "--repo-root",
            ".",
            "--prompt",
            case.prompt,
            "--intent-file",
            ".odylith/runtime/greenfield/confirmed-intent.md",
            "--confirm",
            "--release",
            "0.0.1",
            "--json",
        ],
        timeout=120,
    )
    create_seconds = round(time.perf_counter() - started, 3)
    payload = _parse_json_object(create.stdout)
    package = collect_artifact_package(repo_root=repo_root, create_payload=payload)
    counts = collect_artifact_counts(repo_root=repo_root, package=package, required_terms=case.required_terms)
    quality = build_quality_verdict(
        create_payload=payload,
        package=package,
        counts=counts,
        create_returncode=create.returncode,
        create_seconds=create_seconds,
    )
    return GreenfieldMatrixResult(
        name=case.name,
        status="passed" if quality.passed else "failed",
        create_seconds=create_seconds,
        counts=counts,
        quality=quality,
        create_returncode=create.returncode,
    )


def collect_artifact_package(*, repo_root: Path, create_payload: Mapping[str, Any]) -> Any:
    """Collect generated records in the shape understood by artifact quality gates."""

    accepted_project = _read_json_mapping(repo_root / "odylith/runtime/source/accepted-project.v1.json")
    confirmed_intent = _read_json_mapping(repo_root / ".odylith/runtime/greenfield/confirmed-intent.json")
    proposal = _as_mapping(accepted_project.get("proposal")) or _as_mapping(create_payload.get("proposal")) or confirmed_intent
    backlog_result = {
        "idea_files": _read_radar_workstreams(repo_root),
        "backlog_index_text": _read_text(repo_root / "odylith/radar/source/INDEX.md"),
        "validation_gate": _as_mapping(create_payload.get("validation_gate")),
    }
    return SimpleNamespace(
        proposal=proposal,
        release_selector="0.0.1",
        rendered_component_specs=_read_component_specs(repo_root),
        rendered_atlas_sources=_read_atlas_sources(repo_root),
        component_registry_preview=tuple(_mapping_rows(create_payload.get("components"))),
        project_brief_preview=_as_mapping(proposal.get("project_brief")) if isinstance(proposal, Mapping) else {},
        accepted_project_preview=accepted_project,
        compass_memory_preview=_as_mapping(_as_mapping(create_payload.get("memory")).get("event")),
        next_steps_preview=_as_mapping(create_payload.get("next_steps")),
        backlog_result=backlog_result,
        program_result=_as_mapping(create_payload.get("program")),
        release_target_result=_as_mapping(create_payload.get("release_bootstrap")),
        release_assignment_result=_as_mapping(create_payload.get("release_target")),
        release_workstream_ids=tuple(_release_workstream_ids(create_payload)),
    )


def collect_artifact_counts(
    *,
    repo_root: Path,
    package: Any,
    required_terms: Sequence[str],
) -> GreenfieldArtifactCounts:
    trace = _read_json_mapping(repo_root / "odylith/radar/traceability-graph.v1.json")
    rendered_text = _generated_text(repo_root=repo_root, package=package)
    return GreenfieldArtifactCounts(
        radar_workstreams=len(_as_mapping(package.backlog_result.get("idea_files"))),
        registry_component_specs=len(_as_mapping(package.rendered_component_specs)),
        atlas_mermaid_sources=len(_as_mapping(package.rendered_atlas_sources)),
        compass_records=_count_existing_files(repo_root / "odylith/compass", {".html", ".js", ".json", ".jsonl", ".md"}),
        release_records=_count_existing_files(repo_root / "odylith/radar/source/releases", {".json", ".jsonl", ".md"}),
        program_records=_count_existing_files(repo_root / "odylith/radar/source/programs", {".json", ".md"}),
        project_brief_records=_project_brief_record_count(repo_root=repo_root, package=package),
        trace_nodes=len(trace.get("nodes") or []) if isinstance(trace.get("nodes"), list) else 0,
        trace_workstreams=len(trace.get("workstreams") or []) if isinstance(trace.get("workstreams"), list) else 0,
        rendered_surfaces=sum(1 for path in REQUIRED_RENDERED_SURFACES if _nonempty(repo_root / path)),
        domain_term_hits=sum(1 for term in required_terms if term.casefold() in rendered_text),
    )


def build_quality_verdict(
    *,
    create_payload: Mapping[str, Any],
    package: Any,
    counts: GreenfieldArtifactCounts,
    create_returncode: int,
    create_seconds: float,
) -> GreenfieldQualityVerdict:
    manifest = _as_mapping(create_payload.get("post_confirm_quality_manifest"))
    manifest_lenses = _manifest_lenses(manifest)
    rendered_issues = tuple(greenfield_rendered_package_quality_issues(package)) if create_returncode == 0 else ()
    issues = [
        *rendered_issues,
        *_manifest_issues(manifest),
        *_completion_issues(counts=counts, create_returncode=create_returncode, create_seconds=create_seconds),
    ]
    lenses = {
        "product_manager": (
            _lens_passed(manifest_lenses, "product_manager")
            and counts.radar_workstreams >= 4
            and counts.release_records >= 1
            and counts.project_brief_records >= 1
        ),
        "architect": (
            _lens_passed(manifest_lenses, "architect")
            and counts.registry_component_specs >= 3
            and counts.atlas_mermaid_sources >= 4
            and counts.trace_nodes >= 12
            and counts.trace_workstreams >= 4
        ),
        "engineer": (
            _lens_passed(manifest_lenses, "engineer")
            and counts.registry_component_specs >= 3
            and counts.program_records >= 1
            and create_returncode == 0
            and _write_committed(manifest)
        ),
        "domain_expert": (
            _lens_passed(manifest_lenses, "domain_expert")
            and counts.domain_term_hits >= 3
        ),
    }
    for lens, passed in lenses.items():
        if not passed:
            issues.append(f"{lens} release-matrix lens failed")
    unique_issues = tuple(dict.fromkeys(issue for issue in issues if str(issue).strip()))
    scores = _quality_scores(
        manifest=manifest,
        counts=counts,
        create_returncode=create_returncode,
        create_seconds=create_seconds,
        rendered_issues=rendered_issues,
        lenses=lenses,
    )
    final_score = _final_quality_score(
        scores=scores,
        manifest=manifest,
        create_returncode=create_returncode,
        rendered_issues=rendered_issues,
    )
    return GreenfieldQualityVerdict(
        passed=not unique_issues and all(lenses.values()) and final_score == 10,
        issues=unique_issues,
        lenses=lenses,
        scores=scores,
        score=final_score,
        score_explanation=_score_explanation(
            score=final_score,
            scores=scores,
            rendered_issues=rendered_issues,
            manifest=manifest,
            create_returncode=create_returncode,
        ),
    )


def _failed_case(
    case: GreenfieldMatrixCase,
    repo_root: Path,
    status: str,
    returncode: int,
    detail: str,
) -> GreenfieldMatrixResult:
    package = collect_artifact_package(repo_root=repo_root, create_payload={})
    counts = collect_artifact_counts(repo_root=repo_root, package=package, required_terms=case.required_terms)
    quality = GreenfieldQualityVerdict(
        passed=False,
        issues=(f"{status}: {detail.strip()[:800]}",),
        lenses={lens: False for lens in ("product_manager", "architect", "engineer", "domain_expert")},
        scores={dimension: 0 for dimension in _QUALITY_SCORE_DIMENSIONS},
        score=0,
        score_explanation=("post-confirm did not complete a governed write transaction",),
    )
    return GreenfieldMatrixResult(
        name=case.name,
        status=status,
        create_seconds=0.0,
        counts=counts,
        quality=quality,
        create_returncode=returncode,
    )


def _run(
    *,
    cwd: Path,
    env: Mapping[str, str],
    command: list[str],
    timeout: float,
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            cwd=str(cwd),
            env=dict(env),
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout.decode("utf-8", errors="replace") if isinstance(exc.stdout, bytes) else str(exc.stdout or "")
        stderr = exc.stderr.decode("utf-8", errors="replace") if isinstance(exc.stderr, bytes) else str(exc.stderr or "")
        return subprocess.CompletedProcess(command, 124, stdout=stdout, stderr=stderr)


def _cleanup_repo_before_next(repo_root: Path) -> None:
    _cleanup_smoke_temp_root(repo_root)
    if repo_root.exists():
        shutil.rmtree(repo_root, ignore_errors=True)
    if repo_root.exists():
        raise RuntimeError(f"temporary greenfield simulation repo was not removed: {repo_root}")


def _read_radar_workstreams(repo_root: Path) -> dict[str, str]:
    source = repo_root / "odylith/radar/source"
    if not source.is_dir():
        return {}
    records: dict[str, str] = {}
    for path in sorted(source.rglob("*.md")):
        if path.name in RADAR_WORKSTREAM_SKIP_FILES:
            continue
        records[str(path.relative_to(repo_root))] = _read_text(path)
    return records


def _read_component_specs(repo_root: Path) -> dict[str, str]:
    source = repo_root / "odylith/registry/source/components"
    if not source.is_dir():
        return {}
    specs: dict[str, str] = {}
    for path in sorted(source.rglob("CURRENT_SPEC.md")):
        specs[str(path.relative_to(repo_root))] = _read_text(path)
    return specs


def _read_atlas_sources(repo_root: Path) -> dict[str, str]:
    source = repo_root / "odylith/atlas/source"
    if not source.is_dir():
        return {}
    return {
        str(path.relative_to(repo_root)): _read_text(path)
        for path in sorted(source.glob("*.mmd"))
    }


def _project_brief_record_count(*, repo_root: Path, package: Any) -> int:
    count = 0
    if _as_mapping(getattr(package, "project_brief_preview", None)):
        count += 1
    if _nonempty(repo_root / "odylith/runtime/source/accepted-project.v1.json"):
        count += 1
    if _nonempty(repo_root / ".odylith/runtime/greenfield/confirmed-intent.json"):
        count += 1
    return count


def _generated_text(*, repo_root: Path, package: Any) -> str:
    chunks: list[str] = []
    chunks.extend(_as_mapping(package.backlog_result.get("idea_files")).values())
    chunks.append(str(package.backlog_result.get("backlog_index_text") or ""))
    chunks.extend(_as_mapping(package.rendered_component_specs).values())
    chunks.extend(_as_mapping(package.rendered_atlas_sources).values())
    for path in (repo_root / "odylith").rglob("*") if (repo_root / "odylith").exists() else ():
        if path.is_file() and path.suffix in GENERATED_TEXT_SUFFIXES and path.name != "AGENTS.md":
            chunks.append(_read_text(path))
    return "\n".join(str(item) for item in chunks).casefold()


def _completion_issues(
    *,
    counts: GreenfieldArtifactCounts,
    create_returncode: int,
    create_seconds: float,
) -> tuple[str, ...]:
    issues: list[str] = []
    if create_returncode != 0:
        issues.append(f"post-confirm create exited with code {create_returncode}")
    if create_seconds >= POST_CONFIRM_BUDGET_SECONDS:
        issues.append(f"post-confirm create exceeded {POST_CONFIRM_BUDGET_SECONDS:.0f}s: {create_seconds:.3f}s")
    required_counts = {
        "Radar workstreams": counts.radar_workstreams,
        "Registry component specs": counts.registry_component_specs,
        "Atlas Mermaid sources": counts.atlas_mermaid_sources,
        "Compass records": counts.compass_records,
        "release records": counts.release_records,
        "program records": counts.program_records,
        "project brief records": counts.project_brief_records,
        "trace nodes": counts.trace_nodes,
        "trace workstreams": counts.trace_workstreams,
        "rendered surfaces": counts.rendered_surfaces,
    }
    minimums = _required_count_minimums()
    for label, value in required_counts.items():
        if value < minimums[label]:
            issues.append(f"{label} incomplete: expected at least {minimums[label]}, found {value}")
    if counts.domain_term_hits < 3:
        issues.append(f"domain term coverage too low: expected at least 3, found {counts.domain_term_hits}")
    return tuple(issues)


_QUALITY_SCORE_DIMENSIONS = (
    "completion",
    "latency",
    "semantic_manifest",
    "copy_semantic_clarity",
    "governance_depth",
    "traceability",
    "operator_usefulness",
    "product_manager",
    "architect",
    "engineer",
    "domain_expert",
)


def _quality_scores(
    *,
    manifest: Mapping[str, Any],
    counts: GreenfieldArtifactCounts,
    create_returncode: int,
    create_seconds: float,
    rendered_issues: Sequence[str],
    lenses: Mapping[str, bool],
) -> dict[str, int]:
    return {
        "completion": _completion_score(manifest=manifest, counts=counts, create_returncode=create_returncode),
        "latency": _latency_score(create_returncode=create_returncode, create_seconds=create_seconds),
        "semantic_manifest": _semantic_manifest_score(manifest),
        "copy_semantic_clarity": _copy_semantic_clarity_score(
            manifest=manifest,
            create_returncode=create_returncode,
            rendered_issues=rendered_issues,
        ),
        "governance_depth": _governance_depth_score(counts),
        "traceability": _traceability_score(counts),
        "operator_usefulness": _operator_usefulness_score(counts=counts, create_returncode=create_returncode),
        "product_manager": 10 if lenses.get("product_manager") else 0,
        "architect": 10 if lenses.get("architect") else 0,
        "engineer": 10 if lenses.get("engineer") else 0,
        "domain_expert": 10 if lenses.get("domain_expert") else 0,
    }


def _completion_score(*, manifest: Mapping[str, Any], counts: GreenfieldArtifactCounts, create_returncode: int) -> int:
    if create_returncode != 0 or not _write_committed(manifest):
        return 0
    return 10 if _count_floor_ratio(counts, _required_count_minimums()) >= 1.0 else int(_count_floor_ratio(counts, _required_count_minimums()) * 8)


def _latency_score(*, create_returncode: int, create_seconds: float) -> int:
    if create_returncode != 0:
        return 0
    if create_seconds < POST_CONFIRM_BUDGET_SECONDS:
        return 10
    if create_seconds < 90.0:
        return 6
    if create_seconds < 120.0:
        return 3
    return 0


def _semantic_manifest_score(manifest: Mapping[str, Any]) -> int:
    if not manifest:
        return 0
    return 10 if not _manifest_issues(manifest) else 0


def _copy_semantic_clarity_score(
    *,
    manifest: Mapping[str, Any],
    create_returncode: int,
    rendered_issues: Sequence[str],
) -> int:
    if create_returncode != 0 or not _write_committed(manifest):
        return 0
    return max(0, 10 - (2 * len(tuple(rendered_issues))))


def _governance_depth_score(counts: GreenfieldArtifactCounts) -> int:
    return 10 if _count_floor_ratio(counts, _required_count_minimums()) >= 1.0 else int(_count_floor_ratio(counts, _required_count_minimums()) * 10)


def _traceability_score(counts: GreenfieldArtifactCounts) -> int:
    minimums = {"trace nodes": 12, "trace workstreams": 4}
    values = {"trace nodes": counts.trace_nodes, "trace workstreams": counts.trace_workstreams}
    return 10 if _count_floor_ratio(values, minimums) >= 1.0 else int(_count_floor_ratio(values, minimums) * 10)


def _operator_usefulness_score(*, counts: GreenfieldArtifactCounts, create_returncode: int) -> int:
    if create_returncode != 0:
        return 0
    minimums = {
        "release records": 1,
        "program records": 1,
        "project brief records": 1,
        "rendered surfaces": len(REQUIRED_RENDERED_SURFACES),
    }
    values = {
        "release records": counts.release_records,
        "program records": counts.program_records,
        "project brief records": counts.project_brief_records,
        "rendered surfaces": counts.rendered_surfaces,
    }
    return 10 if _count_floor_ratio(values, minimums) >= 1.0 else int(_count_floor_ratio(values, minimums) * 10)


def _final_quality_score(
    *,
    scores: Mapping[str, int],
    manifest: Mapping[str, Any],
    create_returncode: int,
    rendered_issues: Sequence[str],
) -> int:
    if create_returncode != 0 or not _write_committed(manifest):
        return 0
    score = min(int(scores.get(dimension, 0)) for dimension in _QUALITY_SCORE_DIMENSIONS)
    if rendered_issues:
        score = min(score, 6)
    if _manifest_issues(manifest):
        score = min(score, 4)
    return max(0, min(10, score))


def _score_explanation(
    *,
    score: int,
    scores: Mapping[str, int],
    rendered_issues: Sequence[str],
    manifest: Mapping[str, Any],
    create_returncode: int,
) -> tuple[str, ...]:
    if create_returncode != 0 or not _write_committed(manifest):
        return ("score forced to 0 because post-confirm did not commit governed records",)
    explanations: list[str] = []
    if rendered_issues:
        explanations.append(f"copy/semantic artifact findings cap release score at 6; findings={len(tuple(rendered_issues))}")
    if _manifest_issues(manifest):
        explanations.append("manifest or transaction issues cap release score at 4")
    if score == 10 and all(int(value) == 10 for value in scores.values()):
        explanations.append("all brutal release-quality dimensions scored 10")
        return tuple(explanations)
    weakest = [dimension for dimension, value in scores.items() if int(value) == score]
    if weakest:
        explanations.append(f"final score follows weakest dimension: {', '.join(weakest)}")
    return tuple(explanations)


def _required_count_minimums() -> dict[str, int]:
    return {
        "Radar workstreams": 4,
        "Registry component specs": 3,
        "Atlas Mermaid sources": 4,
        "Compass records": 1,
        "release records": 1,
        "program records": 1,
        "project brief records": 1,
        "trace nodes": 12,
        "trace workstreams": 4,
        "rendered surfaces": len(REQUIRED_RENDERED_SURFACES),
    }


def _count_floor_ratio(values: GreenfieldArtifactCounts | Mapping[str, int], minimums: Mapping[str, int]) -> float:
    rows = values.to_dict() if isinstance(values, GreenfieldArtifactCounts) else dict(values)
    if not minimums:
        return 1.0
    ratios = []
    for label, minimum in minimums.items():
        if minimum <= 0:
            continue
        value = int(rows.get(_count_key(label), rows.get(label, 0)) or 0)
        ratios.append(min(1.0, value / float(minimum)))
    return min(ratios) if ratios else 1.0


def _count_key(label: str) -> str:
    return {
        "Radar workstreams": "radar_workstreams",
        "Registry component specs": "registry_component_specs",
        "Atlas Mermaid sources": "atlas_mermaid_sources",
        "Compass records": "compass_records",
        "release records": "release_records",
        "program records": "program_records",
        "project brief records": "project_brief_records",
        "trace nodes": "trace_nodes",
        "trace workstreams": "trace_workstreams",
        "rendered surfaces": "rendered_surfaces",
    }.get(label, label)


def _manifest_issues(manifest: Mapping[str, Any]) -> tuple[str, ...]:
    if not manifest:
        return ("post-confirm quality manifest missing",)
    issues: list[str] = []
    if str(manifest.get("status", "")).strip() != "passed":
        issues.append(f"post-confirm quality manifest status is {manifest.get('status')!r}")
    if str(manifest.get("validation_status", "")).strip() != "passed":
        issues.append(f"post-confirm validation status is {manifest.get('validation_status')!r}")
    if int(manifest.get("issue_count") or 0) != 0:
        issues.append(f"post-confirm quality manifest has {manifest.get('issue_count')} issue(s)")
    if not _write_committed(manifest):
        issues.append("post-confirm write transaction was not committed")
    if float(manifest.get("whole_project_elapsed_seconds") or 0.0) >= POST_CONFIRM_BUDGET_SECONDS:
        issues.append("post-confirm manifest reports elapsed time outside the standard budget")
    lens_report = _as_mapping(manifest.get("quality_lenses"))
    if str(lens_report.get("status", "")).strip() != "passed":
        issues.append("post-confirm quality lens report did not pass")
    return tuple(issues)


def _manifest_lenses(manifest: Mapping[str, Any]) -> Mapping[str, Any]:
    return _as_mapping(_as_mapping(manifest.get("quality_lenses")).get("lenses"))


def _lens_passed(lenses: Mapping[str, Any], name: str) -> bool:
    return str(_as_mapping(lenses.get(name)).get("status", "")).strip() == "passed"


def _write_committed(manifest: Mapping[str, Any]) -> bool:
    return str(_as_mapping(manifest.get("write_transaction")).get("status", "")).strip() == "committed"


def _release_workstream_ids(payload: Mapping[str, Any]) -> tuple[str, ...]:
    release_target = _as_mapping(payload.get("release_target"))
    workstreams: list[str] = []
    for event in _mapping_rows(release_target.get("events")):
        token = str(event.get("workstream_id", "")).strip()
        if token:
            workstreams.append(token)
    return tuple(dict.fromkeys(workstreams))


def _count_existing_files(root: Path, suffixes: set[str]) -> int:
    if not root.exists():
        return 0
    return sum(1 for path in root.rglob("*") if path.is_file() and path.suffix in suffixes and path.stat().st_size > 0)


def _nonempty(path: Path) -> bool:
    return path.is_file() and path.stat().st_size > 0


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(errors="replace")
    except FileNotFoundError:
        return ""


def _read_json_mapping(path: Path) -> Mapping[str, Any]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, Mapping) else {}


def _parse_json_object(value: str) -> Mapping[str, Any]:
    try:
        payload = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, Mapping) else {}


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _mapping_rows(value: Any) -> tuple[Mapping[str, Any], ...]:
    return tuple(row for row in value if isinstance(row, Mapping)) if isinstance(value, Sequence) and not isinstance(value, (str, bytes)) else ()


def _version_from_pyproject() -> str:
    text = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.startswith("version = "):
            return line.split("=", 1)[1].strip().strip('"')
    return "0.1.15"


def _default_temp_parent() -> Path:
    mock = Path("/Users/freedom/mock")
    if mock.is_dir():
        return mock
    return Path(tempfile.gettempdir())


def _print_human_summary(results: Sequence[GreenfieldMatrixResult]) -> None:
    print(f"greenfield post-confirm installed matrix: {QUALITY_MATRIX_VERSION}")
    for result in results:
        print(
            " - {name}: {status}, score={score}/10, {seconds:.3f}s, issues={issues}, "
            "radar={radar}, registry={registry}, atlas={atlas}, trace_nodes={trace_nodes}".format(
                name=result.name,
                status=result.status,
                score=result.quality.score,
                seconds=result.create_seconds,
                issues=len(result.quality.issues),
                radar=result.counts.radar_workstreams,
                registry=result.counts.registry_component_specs,
                atlas=result.counts.atlas_mermaid_sources,
                trace_nodes=result.counts.trace_nodes,
            )
        )
        if result.quality.issues:
            for issue in result.quality.issues:
                print(f"   issue: {issue}")
        for explanation in result.quality.score_explanation:
            print(f"   score: {explanation}")


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run installed greenfield post-confirm release simulations.")
    parser.add_argument("--dist-dir", required=True, help="Local release asset directory containing install.sh.")
    parser.add_argument("--version", default=_version_from_pyproject())
    parser.add_argument("--temp-parent", default=str(_default_temp_parent()))
    parser.add_argument("--json", action="store_true", dest="json_output")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    results = run_matrix(
        dist_dir=Path(args.dist_dir),
        version=str(args.version),
        temp_parent=Path(args.temp_parent),
    )
    payload = {
        "version": QUALITY_MATRIX_VERSION,
        "status": "passed" if all(result.quality.passed for result in results) else "failed",
        "results": [result.to_dict() for result in results],
    }
    if args.json_output:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        _print_human_summary(results)
    return 0 if payload["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
