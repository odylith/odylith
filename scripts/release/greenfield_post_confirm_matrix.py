"""Run installed greenfield post-confirm simulations against a local release."""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time
import uuid
from types import SimpleNamespace
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from local_release_smoke import _cleanup_smoke_temp_root, _local_release_env, _serve_directory  # noqa: E402
from greenfield_rescue_smoke import POST_CONFIRM_RESCUE_BUDGET_SECONDS  # noqa: E402
from greenfield_rescue_smoke import installed_auto_rescue_env  # noqa: E402
from greenfield_rescue_smoke import rescue_cli_issues  # noqa: E402
from greenfield_browser_proof_summary import browser_proof_summary  # noqa: E402
from greenfield_browser_surface_proof import BROWSER_SURFACE_PROOF_SCOPE, browser_surface_proof_issues  # noqa: E402
from greenfield_surface_health import INDEX_SHELL_TAB_CONTRACTS  # noqa: E402
from greenfield_surface_health import REQUIRED_RENDERED_SURFACES  # noqa: E402
from greenfield_surface_health import SURFACE_PAYLOAD_CONTRACTS  # noqa: E402
from greenfield_surface_health import atlas_rendered_asset_count  # noqa: E402
from greenfield_surface_health import rendered_surface_health_issues  # noqa: E402
from greenfield_surface_health import rendered_surface_payload_count  # noqa: E402
from greenfield_post_confirm_matrix_cases import GreenfieldMatrixCase  # noqa: E402
from greenfield_post_confirm_matrix_cases import default_cases  # noqa: E402
from greenfield_process import run_command_with_group_timeout as _run  # noqa: E402
from greenfield_matrix_types import GreenfieldArtifactCounts  # noqa: E402
from greenfield_matrix_types import GreenfieldMatrixResult  # noqa: E402
from greenfield_matrix_types import GreenfieldQualityVerdict  # noqa: E402
from greenfield_matrix_types import GreenfieldRescueSmokeResult  # noqa: E402
from greenfield_matrix_package_evidence import evidence_blocks_dimension  # noqa: E402
from greenfield_matrix_package_evidence import evidence_finding_messages  # noqa: E402
from greenfield_matrix_package_evidence import package_evidence_findings  # noqa: E402
import platform_domain_leakage_check as platform_domain_leakage  # noqa: E402
from odylith.runtime.domain_intelligence.artifact_tribunal_actors import (  # noqa: E402
    tribunal_visible_actor_quality_issues,
)
from odylith.runtime.domain_intelligence.greenfield_text import clean_text  # noqa: E402
from odylith.runtime.domain_intelligence.greenfield_text import text_values  # noqa: E402
from odylith.runtime.artifact_quality.greenfield_package_quality import (  # noqa: E402
    greenfield_rendered_package_quality_issues,
)
from odylith.runtime.artifact_quality.greenfield_quality_lenses import (  # noqa: E402
    build_greenfield_quality_lens_report,
)


POST_CONFIRM_BUDGET_SECONDS = 60.0
COMMAND_TIMEOUT_SECONDS = 300
QUALITY_MATRIX_VERSION = "greenfield-post-confirm-installed-matrix-v1"
REPO_ROOT = Path(__file__).resolve().parents[2]
NON_ARTIFACT_MARKDOWN_FILES = {"AGENTS.md", "CLAUDE.md", "INDEX.md", "README.md"}


def run_matrix(
    *,
    dist_dir: Path,
    version: str,
    temp_parent: Path,
    cases: Sequence[GreenfieldMatrixCase] = (),
    include_browser_proof: bool = False,
) -> tuple[GreenfieldMatrixResult, ...]:
    """Run the real installed greenfield create path for each matrix case."""

    selected_cases = tuple(cases) or default_cases()
    release_dir = Path(dist_dir).expanduser().resolve()
    install_script = release_dir / "install.sh"
    if not install_script.is_file():
        raise FileNotFoundError(f"missing local release install script: {install_script}")
    _raise_for_platform_domain_leakage(release_dir, selected_cases)
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
                include_browser_proof=include_browser_proof,
            )
            results.append(result)
            _cleanup_repo_before_next(repo_root)
    finally:
        server.shutdown()
        server.server_close()
        _cleanup_run_root(run_root)
    return tuple(results)


def _raise_for_platform_domain_leakage(release_dir: Path, cases: Sequence[GreenfieldMatrixCase]) -> None:
    missing_cases = platform_domain_leakage.cases_missing_leakage_terms(cases)
    if missing_cases:
        names = ", ".join(missing_cases)
        raise RuntimeError(
            "platform domain leakage check cannot prove selected greenfield matrix case vocabulary; "
            f"declare leakage_terms for: {names}"
        )
    terms = platform_domain_leakage.domain_leakage_terms(cases, include_historical=False)
    if not terms:
        return
    findings = platform_domain_leakage.scan_platform_custody(
        repo_root=REPO_ROOT,
        dist_dir=release_dir,
        terms=terms,
    )
    if not findings:
        return
    preview = "\n".join(
        f"- {finding.location}:{finding.line}: leaked `{finding.term}`" for finding in findings[:20]
    )
    remaining = len(findings) - 20
    suffix = f"\n- ... {remaining} additional finding(s)" if remaining > 0 else ""
    raise RuntimeError(
        "platform domain leakage check failed for selected greenfield matrix case vocabulary\n"
        f"{preview}{suffix}"
    )


def run_rescue_smoke(
    *,
    dist_dir: Path,
    version: str,
    temp_parent: Path,
) -> GreenfieldRescueSmokeResult:
    """Prove installed rescue-tier writes and auto-rescue engine escalation."""

    release_dir = Path(dist_dir).expanduser().resolve()
    install_script = release_dir / "install.sh"
    if not install_script.is_file():
        raise FileNotFoundError(f"missing local release install script: {install_script}")
    run_root = Path(temp_parent).expanduser().resolve() / f"odylith-greenfield-rescue-{uuid.uuid4().hex[:8]}"
    run_root.mkdir(parents=True, exist_ok=False)
    server, base_url = _serve_directory(release_dir)
    try:
        repo_root = run_root / f"odylith-sim-rescue-{uuid.uuid4().hex[:8]}"
        result = _run_rescue_smoke_case(
            repo_root=repo_root,
            install_script=install_script,
            base_url=base_url,
            version=version,
        )
        _cleanup_repo_before_next(repo_root)
        return result
    finally:
        server.shutdown()
        server.server_close()
        _cleanup_run_root(run_root)


def _run_case(
    *,
    case: GreenfieldMatrixCase,
    repo_root: Path,
    install_script: Path,
    base_url: str,
    version: str,
    include_browser_proof: bool = False,
) -> GreenfieldMatrixResult:
    repo_root.mkdir(parents=True)
    env = _local_release_env(base_url=base_url, version=version)
    _run(cwd=repo_root, env=env, command=["git", "init"], timeout=60)
    install = _run(cwd=repo_root, env=env, command=["bash", str(install_script)], timeout=COMMAND_TIMEOUT_SECONDS)
    if install.returncode != 0:
        return _failed_case(case, repo_root, "install_failed", install.returncode, install.stderr or install.stdout)
    confirmed_intent = str(case.confirmed_intent_markdown or "").strip()
    if not confirmed_intent:
        propose = _run(
            cwd=repo_root,
            env=env,
            command=["./.odylith/bin/odylith", "greenfield", "propose", "--repo-root", ".", "--prompt", case.prompt],
            timeout=120,
        )
        if propose.returncode != 0:
            return _failed_case(case, repo_root, "propose_failed", propose.returncode, propose.stderr or propose.stdout)
        confirmed_intent = propose.stdout
    intent_path = repo_root / ".odylith/runtime/greenfield/confirmed-intent.md"
    intent_path.parent.mkdir(parents=True, exist_ok=True)
    intent_path.write_text(confirmed_intent, encoding="utf-8")
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
    surface_issues = rendered_surface_health_issues(repo_root=repo_root)
    leakage_terms = _case_generated_leakage_terms(case=case, repo_root=repo_root, package=package)
    leakage_issues = _case_platform_leakage_issues(
        terms=leakage_terms,
        release_dir=install_script.parent,
    )
    browser_surface_proof_attempted = bool(include_browser_proof and create.returncode == 0)
    browser_surface_issues = (
        browser_surface_proof_issues(repo_root=repo_root) if browser_surface_proof_attempted else ()
    )
    quality = build_quality_verdict(
        create_payload=payload,
        package=package,
        counts=counts,
        surface_issues=(*surface_issues, *browser_surface_issues, *leakage_issues),
        create_returncode=create.returncode,
        create_seconds=create_seconds,
        create_detail=create.stderr or create.stdout,
    )
    return GreenfieldMatrixResult(
        name=case.name,
        status="passed" if quality.passed else "failed",
        create_seconds=create_seconds,
        counts=counts,
        quality=quality,
        browser_surface_issues=browser_surface_issues,
        browser_surface_proof_attempted=browser_surface_proof_attempted,
        create_returncode=create.returncode,
        failure_detail=_command_excerpt(create.stderr or create.stdout) if create.returncode else "",
        create_stdout_excerpt=_command_excerpt(create.stdout) if create.returncode else "",
        create_stderr_excerpt=_command_excerpt(create.stderr) if create.returncode else "",
        platform_leakage_terms=leakage_terms,
        platform_leakage_issues=leakage_issues,
    )


def _run_rescue_smoke_case(
    *,
    repo_root: Path,
    install_script: Path,
    base_url: str,
    version: str,
) -> GreenfieldRescueSmokeResult:
    case = GreenfieldMatrixCase(
        name="rescue disclosure council",
        prompt=(
            "Create a greenfield proposal for a cross-organization disclosure council that receives external reports, "
            "coordinates review, records evidence custody, decides embargo status, and publishes release readiness proof "
            "without claiming personalized notification delivery in the first release."
        ),
        required_terms=("disclosure", "council", "embargo", "evidence"),
        leakage_terms=("disclosure council", "embargo status", "personalized notification delivery"),
    )
    repo_root.mkdir(parents=True)
    env = _local_release_env(base_url=base_url, version=version)
    _run(cwd=repo_root, env=env, command=["git", "init"], timeout=60)
    install = _run(cwd=repo_root, env=env, command=["bash", str(install_script)], timeout=COMMAND_TIMEOUT_SECONDS)
    if install.returncode != 0:
        return _rescue_smoke_result(
            create_payload={},
            counts=GreenfieldArtifactCounts(),
            issues=(f"install_failed: {(install.stderr or install.stdout).strip()[:800]}",),
            create_returncode=install.returncode,
        )
    propose = _run(
        cwd=repo_root,
        env=env,
        command=["./.odylith/bin/odylith", "greenfield", "propose", "--repo-root", ".", "--prompt", case.prompt],
        timeout=120,
    )
    if propose.returncode != 0:
        return _rescue_smoke_result(
            create_payload={},
            counts=GreenfieldArtifactCounts(),
            issues=(f"propose_failed: {(propose.stderr or propose.stdout).strip()[:800]}",),
            create_returncode=propose.returncode,
        )
    intent_path = repo_root / ".odylith/runtime/greenfield/confirmed-intent.md"
    intent_path.parent.mkdir(parents=True, exist_ok=True)
    intent_path.write_text(propose.stdout, encoding="utf-8")
    started = time.perf_counter()
    create = _run(
        cwd=repo_root,
        env=installed_auto_rescue_env(env),
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
            "--repair-tier",
            "auto",
            "--json",
        ],
        timeout=150,
    )
    create_seconds = round(time.perf_counter() - started, 3)
    payload = _parse_json_object(create.stdout)
    package = collect_artifact_package(repo_root=repo_root, create_payload=payload)
    counts = collect_artifact_counts(repo_root=repo_root, package=package, required_terms=case.required_terms)
    surface_issues = rendered_surface_health_issues(repo_root=repo_root)
    issues = list(
        rescue_cli_issues(
            manifest=_as_mapping(payload.get("post_confirm_quality_manifest")),
            package=package,
            counts=counts,
            count_minimums=_required_count_minimums(),
            count_key=_count_key,
            write_committed=_write_committed,
            as_mapping=_as_mapping,
            package_quality_issues=greenfield_rendered_package_quality_issues,
            create_returncode=create.returncode,
            create_seconds=create_seconds,
            detail=create.stderr or create.stdout,
            expected_requested_tier="auto",
        )
    )
    issues.extend(surface_issues)
    return _rescue_smoke_result(
        create_payload=payload,
        counts=counts,
        issues=tuple(issues),
        create_returncode=create.returncode,
        cli_create_seconds=create_seconds,
    )


def _rescue_smoke_result(
    *,
    create_payload: Mapping[str, Any],
    counts: GreenfieldArtifactCounts,
    issues: Sequence[str],
    create_returncode: int,
    cli_create_seconds: float = 0.0,
) -> GreenfieldRescueSmokeResult:
    cleaned_issues = tuple(dict.fromkeys(issue for issue in issues if str(issue).strip()))
    return GreenfieldRescueSmokeResult(
        status="passed" if not cleaned_issues else "failed",
        cli_create_seconds=cli_create_seconds,
        counts=counts,
        issues=cleaned_issues,
        manifest=_as_mapping(create_payload.get("post_confirm_quality_manifest")),
        create_returncode=create_returncode,
    )
def collect_artifact_package(*, repo_root: Path, create_payload: Mapping[str, Any]) -> Any:
    """Collect generated records in the shape understood by artifact quality gates."""

    accepted_project = _read_json_mapping(repo_root / "odylith/runtime/source/accepted-project.v1.json")
    confirmed_intent = _read_json_mapping(repo_root / ".odylith/runtime/greenfield/confirmed-intent.json")
    proposal = _as_mapping(accepted_project.get("proposal")) or _as_mapping(create_payload.get("proposal")) or confirmed_intent
    source_launch_readback = _as_mapping(accepted_project.get("source_launch"))
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
        project_brief_record_text=_read_text(repo_root / "odylith/runtime/source/project-brief.v1.md"),
        accepted_project_preview=accepted_project,
        source_launch_readback=source_launch_readback,
        project_dashboard_preview=_read_project_dashboard_payload(repo_root),
        compass_memory_preview=_as_mapping(_as_mapping(create_payload.get("memory")).get("event")),
        next_steps_preview=_as_mapping(create_payload.get("next_steps")),
        backlog_result=backlog_result,
        program_result=_as_mapping(create_payload.get("program")),
        prewrite_safety_preview=_as_mapping(create_payload.get("prewrite_safety")),
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
        rendered_surface_payloads=rendered_surface_payload_count(repo_root),
        atlas_rendered_assets=atlas_rendered_asset_count(repo_root),
        domain_term_hits=sum(1 for term in required_terms if term.casefold() in rendered_text),
        required_domain_terms=len(tuple(dict.fromkeys(term.casefold() for term in required_terms if str(term).strip()))),
        project_implementation_prompts=len(
            _mapping_rows(_as_mapping(getattr(package, "project_dashboard_preview", None)).get("host_handoff_prompts"))
        ),
    )

def build_quality_verdict(
    *,
    create_payload: Mapping[str, Any],
    package: Any,
    counts: GreenfieldArtifactCounts,
    surface_issues: Sequence[str] = (),
    create_returncode: int,
    create_seconds: float,
    create_detail: str = "",
) -> GreenfieldQualityVerdict:
    manifest = _as_mapping(create_payload.get("post_confirm_quality_manifest"))
    manifest_lenses = _manifest_lenses(manifest)
    package_lens_report = _as_mapping(build_greenfield_quality_lens_report(package)) if create_returncode == 0 else {}
    package_lenses = _package_lenses(package_lens_report)
    evidence_findings = tuple(package_evidence_findings(package)) if create_returncode == 0 else ()
    rendered_issues = (
        tuple(
            dict.fromkeys(
                (
                    *tuple(greenfield_rendered_package_quality_issues(package)),
                    *tuple(_package_lens_issues(package_lens_report)),
                    *tuple(evidence_finding_messages(evidence_findings)),
                    *tuple(_validation_gate_actor_issues(create_payload=create_payload, package=package)),
                    *tuple(str(issue).strip() for issue in surface_issues if str(issue).strip()),
                )
            )
        )
        if create_returncode == 0
        else ()
    )
    prompt_issues = tuple(issue for issue in rendered_issues if issue.startswith("Project implementation prompt "))
    issues = [
        *rendered_issues,
        *_create_failure_detail_issues(create_returncode=create_returncode, create_detail=create_detail),
        *_manifest_issues(manifest),
        *_completion_issues(counts=counts, create_returncode=create_returncode, create_seconds=create_seconds),
    ]
    lenses = {
        "product_manager": (
            _lens_passed(manifest_lenses, "product_manager")
            and _lens_passed(package_lenses, "product_manager")
            and not evidence_blocks_dimension(evidence_findings, "product_manager")
            and counts.radar_workstreams >= 4
            and counts.release_records >= 1
            and counts.project_brief_records >= 1
        ),
        "architect": (
            _lens_passed(manifest_lenses, "architect")
            and _lens_passed(package_lenses, "architect")
            and not evidence_blocks_dimension(evidence_findings, "architect")
            and counts.registry_component_specs >= 3
            and counts.atlas_mermaid_sources >= 4
            and counts.trace_nodes >= 12
            and counts.trace_workstreams >= 4
        ),
        "engineer": (
            _lens_passed(manifest_lenses, "engineer")
            and _lens_passed(package_lenses, "engineer")
            and not evidence_blocks_dimension(evidence_findings, "engineer")
            and counts.registry_component_specs >= 3
            and counts.program_records >= 1
            and create_returncode == 0
            and _write_committed(manifest)
        ),
        "domain_expert": (
            _lens_passed(manifest_lenses, "domain_expert")
            and _lens_passed(package_lenses, "domain_expert")
            and not evidence_blocks_dimension(evidence_findings, "domain_expert")
            and counts.domain_term_hits >= _required_domain_term_hits(counts)
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
        prompt_issues=prompt_issues,
        lenses=lenses,
        evidence_findings=evidence_findings,
    )
    final_score = _final_quality_score(
        scores=scores,
        manifest=manifest,
        create_returncode=create_returncode,
        rendered_issues=rendered_issues,
        prompt_issues=prompt_issues,
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
            counts=counts,
            rendered_issues=rendered_issues,
            prompt_issues=prompt_issues,
            manifest=manifest,
            create_returncode=create_returncode,
            lenses=lenses,
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
        failure_detail=_command_excerpt(detail),
    )


def _cleanup_repo_before_next(repo_root: Path) -> None:
    _cleanup_smoke_temp_root(repo_root)
    if repo_root.exists():
        shutil.rmtree(repo_root, ignore_errors=True)
    if repo_root.exists():
        raise RuntimeError(f"temporary greenfield simulation repo was not removed: {repo_root}")


def _cleanup_run_root(run_root: Path) -> None:
    _cleanup_smoke_temp_root(run_root)
    if run_root.exists():
        shutil.rmtree(run_root, ignore_errors=True)
    if run_root.exists():
        raise RuntimeError(f"temporary greenfield matrix root was not removed: {run_root}")


def _read_radar_workstreams(repo_root: Path) -> dict[str, str]:
    source = repo_root / "odylith/radar/source"
    if not source.is_dir():
        return {}
    records: dict[str, str] = {}
    for path in sorted(source.rglob("*.md")):
        if path.name in NON_ARTIFACT_MARKDOWN_FILES:
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
    text = _read_text(repo_root / "odylith/runtime/source/project-brief.v1.md")
    if not text:
        text = str(getattr(package, "project_brief_record_text", "") or "")
    required_markers = ("## Brief", "## Project Design Board", "## Governance Package")
    return 1 if text and all(marker in text for marker in required_markers) else 0


def _generated_text(*, repo_root: Path, package: Any) -> str:
    del repo_root
    chunks: list[str] = []
    chunks.extend(_as_mapping(package.backlog_result.get("idea_files")).values())
    chunks.append(str(package.backlog_result.get("backlog_index_text") or ""))
    chunks.extend(_as_mapping(package.rendered_component_specs).values())
    chunks.extend(_as_mapping(package.rendered_atlas_sources).values())
    chunks.append(str(getattr(package, "project_brief_record_text", "") or ""))
    chunks.extend(text_values(getattr(package, "source_launch_readback", None)))
    for row in _mapping_rows(_as_mapping(getattr(package, "project_dashboard_preview", None)).get("host_handoff_prompts")):
        chunks.extend(text_values(row))
    return "\n".join(str(item) for item in chunks).casefold()


def _case_generated_leakage_terms(*, case: GreenfieldMatrixCase, repo_root: Path, package: Any) -> tuple[str, ...]:
    generated_text = _generated_text(repo_root=repo_root, package=package)
    candidate_terms = platform_domain_leakage.case_leakage_terms(case)
    return tuple(term for term in candidate_terms if _term_present(generated_text, term))


def _case_platform_leakage_issues(*, terms: Sequence[str], release_dir: Path) -> tuple[str, ...]:
    checked_terms = tuple(dict.fromkeys(str(term).strip() for term in terms if str(term).strip()))
    if not checked_terms:
        return ()
    findings = platform_domain_leakage.scan_platform_custody(
        repo_root=REPO_ROOT,
        dist_dir=release_dir,
        terms=checked_terms,
    )
    return tuple(
        f"platform domain leakage after generated artifact readback: {finding.location}:{finding.line} leaked `{finding.term}`"
        for finding in findings
    )


def _term_present(text: str, term: str) -> bool:
    text_tokens = _tokenize(text)
    term_tokens = _tokenize(term)
    if not text_tokens or not term_tokens or len(term_tokens) > len(text_tokens):
        return False
    width = len(term_tokens)
    return any(text_tokens[index : index + width] == term_tokens for index in range(len(text_tokens) - width + 1))


def _tokenize(text: str) -> tuple[str, ...]:
    tokens: list[str] = []
    current: list[str] = []
    for char in str(text or "").casefold():
        if char.isalnum():
            current.append(char)
        elif current:
            tokens.append("".join(current))
            current = []
    if current:
        tokens.append("".join(current))
    return tuple(tokens)


def _read_project_dashboard_payload(repo_root: Path) -> Mapping[str, Any]:
    shell_payload = _read_tooling_payload(repo_root)
    project = shell_payload.get("project_intelligence")
    return project if isinstance(project, Mapping) else {}


def _read_tooling_payload(repo_root: Path) -> Mapping[str, Any]:
    payload_path = repo_root / "odylith/tooling-payload.v1.js"
    text = _read_text(payload_path).strip()
    if not text or "__ODYLITH_TOOLING_DATA__" not in text:
        return {}
    json_start = text.find("{")
    if json_start < 0:
        return {}
    try:
        payload, _end = json.JSONDecoder().raw_decode(text[json_start:])
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, Mapping) else {}


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
        "rendered surface payloads": counts.rendered_surface_payloads,
        "Atlas rendered diagram assets": counts.atlas_rendered_assets,
        "Project implementation prompts": counts.project_implementation_prompts,
    }
    minimums = _required_count_minimums()
    for label, value in required_counts.items():
        if value < minimums[label]:
            issues.append(f"{label} incomplete: expected at least {minimums[label]}, found {value}")
    domain_term_minimum = _required_domain_term_hits(counts)
    if counts.domain_term_hits < domain_term_minimum:
        issues.append(
            f"domain term coverage too low: expected at least {domain_term_minimum}, found {counts.domain_term_hits}"
        )
    return tuple(issues)


def _create_failure_detail_issues(*, create_returncode: int, create_detail: str) -> tuple[str, ...]:
    if create_returncode == 0:
        return ()
    detail = _command_excerpt(create_detail)
    return (f"post-confirm create failure detail: {detail}",) if detail else ()


def _command_excerpt(value: str, limit: int = 4000) -> str:
    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    return f"{text[:limit].rstrip()}...[truncated]"


_QUALITY_SCORE_DIMENSIONS = (
    "completion",
    "latency",
    "semantic_manifest",
    "copy_semantic_clarity",
    "governance_depth",
    "traceability",
    "operator_usefulness",
    "implementation_prompts",
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
    prompt_issues: Sequence[str],
    lenses: Mapping[str, bool],
    evidence_findings: Sequence[Any] = (),
) -> dict[str, int]:
    return {
        "completion": (
            0
            if evidence_blocks_dimension(evidence_findings, "completion")
            else _completion_score(manifest=manifest, counts=counts, create_returncode=create_returncode)
        ),
        "latency": _latency_score(create_returncode=create_returncode, create_seconds=create_seconds),
        "semantic_manifest": _semantic_manifest_score(manifest),
        "copy_semantic_clarity": _copy_semantic_clarity_score(
            manifest=manifest,
            create_returncode=create_returncode,
            rendered_issues=rendered_issues,
        ),
        "governance_depth": (
            0 if evidence_blocks_dimension(evidence_findings, "governance_depth") else _governance_depth_score(counts)
        ),
        "traceability": _traceability_score(counts),
        "operator_usefulness": (
            0
            if evidence_blocks_dimension(evidence_findings, "operator_usefulness")
            else _operator_usefulness_score(counts=counts, create_returncode=create_returncode)
        ),
        "implementation_prompts": _implementation_prompt_score(
            counts=counts,
            create_returncode=create_returncode,
            prompt_issues=prompt_issues,
            evidence_findings=evidence_findings,
        ),
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


def _implementation_prompt_score(
    *,
    counts: GreenfieldArtifactCounts,
    create_returncode: int,
    prompt_issues: Sequence[str],
    evidence_findings: Sequence[Any] = (),
) -> int:
    if create_returncode != 0 or prompt_issues or evidence_blocks_dimension(evidence_findings, "implementation_prompts"):
        return 0
    return 10 if counts.project_implementation_prompts >= 5 else 0


def _final_quality_score(
    *,
    scores: Mapping[str, int],
    manifest: Mapping[str, Any],
    create_returncode: int,
    rendered_issues: Sequence[str],
    prompt_issues: Sequence[str],
) -> int:
    if create_returncode != 0 or not _write_committed(manifest):
        return 0
    score = min(int(scores.get(dimension, 0)) for dimension in _QUALITY_SCORE_DIMENSIONS)
    if rendered_issues:
        score = min(score, 6)
    if prompt_issues:
        score = min(score, 4)
    if _manifest_issues(manifest):
        score = min(score, 4)
    return max(0, min(10, score))


def _score_explanation(
    *,
    score: int,
    scores: Mapping[str, int],
    counts: GreenfieldArtifactCounts,
    rendered_issues: Sequence[str],
    prompt_issues: Sequence[str],
    manifest: Mapping[str, Any],
    create_returncode: int,
    lenses: Mapping[str, bool],
) -> tuple[str, ...]:
    if create_returncode != 0 or not _write_committed(manifest):
        return ("score forced to 0 because post-confirm did not commit governed records",)
    explanations: list[str] = []
    if rendered_issues:
        explanations.append(f"copy/semantic artifact findings cap release score at 6; findings={len(tuple(rendered_issues))}")
    if prompt_issues:
        explanations.append(f"Project implementation prompt findings cap release score at 4; findings={len(tuple(prompt_issues))}")
    if _manifest_issues(manifest):
        explanations.append("manifest or transaction issues cap release score at 4")
    if score == 10 and all(int(value) == 10 for value in scores.values()):
        explanations.append("all brutal release-quality dimensions scored 10")
        explanations.append(
            "completion evidence: "
            f"{counts.radar_workstreams} Radar workstreams, "
            f"{counts.registry_component_specs} Registry specs, "
            f"{counts.atlas_mermaid_sources} Atlas diagrams, "
            f"{counts.project_brief_records} project brief records"
        )
        explanations.append(
            "rendered-surface evidence: "
            f"{counts.rendered_surfaces} surfaces, "
            f"{counts.rendered_surface_payloads} payload assets, "
            f"{counts.atlas_rendered_assets} Atlas rendered assets"
        )
        explanations.append(
            "traceability and prompt evidence: "
            f"{counts.trace_nodes} trace nodes, "
            f"{counts.trace_workstreams} trace workstreams, "
            f"{counts.project_implementation_prompts} Project implementation prompts, "
            f"{len(tuple(prompt_issues))} prompt findings"
        )
        passed_lenses = ", ".join(name for name, passed in lenses.items() if passed)
        explanations.append(f"expert-lens evidence: {passed_lenses} passed")
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
        "rendered surface payloads": len(SURFACE_PAYLOAD_CONTRACTS) * 2,
        "Atlas rendered diagram assets": 8,
        "Project implementation prompts": 5,
    }


def _required_domain_term_hits(counts: GreenfieldArtifactCounts) -> int:
    return max(3, int(counts.required_domain_terms or 0))


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
        "rendered surface payloads": "rendered_surface_payloads",
        "Atlas rendered diagram assets": "atlas_rendered_assets",
        "Project implementation prompts": "project_implementation_prompts",
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


def _validation_gate_actor_issues(*, create_payload: Mapping[str, Any], package: Any) -> tuple[str, ...]:
    create_gate = _as_mapping(create_payload.get("validation_gate"))
    accepted_gate = _as_mapping(_as_mapping(getattr(package, "accepted_project_preview", {})).get("validation_gate"))
    sources = (
        ("create payload", create_gate),
        ("accepted-project readback", accepted_gate),
    )
    issues: list[str] = []
    source_labels: dict[str, dict[str, str]] = {}
    for source_name, validation_gate in sources:
        visible_actors = validation_gate.get("visible_actors")
        if not isinstance(visible_actors, Sequence) or isinstance(visible_actors, (str, bytes)):
            issues.append(f"{source_name} validation gate visible actors missing")
            continue
        rows = tuple(row for row in visible_actors if isinstance(row, Mapping))
        source_labels[source_name] = {
            str(row.get("stable_role", "")).strip(): clean_text(row.get("visible_actor", "")).strip()
            for row in rows
            if str(row.get("stable_role", "")).strip()
        }
        issues.extend(f"{source_name} {issue}" for issue in tribunal_visible_actor_quality_issues(rows))
    if source_labels.get("create payload") and source_labels.get("accepted-project readback"):
        if source_labels["create payload"] != source_labels["accepted-project readback"]:
            issues.append("accepted-project validation gate visible actors drifted from create payload")
    return tuple(dict.fromkeys(issue for issue in issues if str(issue).strip()))


def _manifest_lenses(manifest: Mapping[str, Any]) -> Mapping[str, Any]:
    return _as_mapping(_as_mapping(manifest.get("quality_lenses")).get("lenses"))


def _package_lenses(package_lens_report: Mapping[str, Any]) -> Mapping[str, Any]:
    return _as_mapping(package_lens_report.get("lenses"))


def _package_lens_issues(package_lens_report: Mapping[str, Any]) -> tuple[str, ...]:
    if not package_lens_report:
        return ("independent package quality lens report missing",)
    issues = tuple(
        str(issue).strip()
        for issue in package_lens_report.get("issues", ())
        if str(issue).strip()
    )
    if issues:
        return issues
    if str(package_lens_report.get("status", "")).strip() != "passed":
        return ("independent package quality lens report did not pass",)
    return ()


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


def _print_rescue_summary(rescue: GreenfieldRescueSmokeResult | None) -> None:
    if rescue is None:
        return
    print(
        " - rescue smoke ({scope}): {status}, cli_auto_rescue={cli:.3f}s, issues={issues}, "
        "radar={radar}, registry={registry}, atlas={atlas}, trace_nodes={trace_nodes}".format(
            scope=rescue.proof_scope,
            status=rescue.status,
            cli=rescue.cli_create_seconds,
            issues=len(rescue.issues),
            radar=rescue.counts.radar_workstreams,
            registry=rescue.counts.registry_component_specs,
            atlas=rescue.counts.atlas_mermaid_sources,
            trace_nodes=rescue.counts.trace_nodes,
        )
    )
    for issue in rescue.issues:
        print(f"   issue: {issue}")


def _platform_leakage_proof_summary(results: Sequence[GreenfieldMatrixResult]) -> dict[str, Any]:
    terms = sorted(
        {
            str(term).strip()
            for result in results
            for term in result.platform_leakage_terms
            if str(term).strip()
        }
    )
    issues = tuple(
        dict.fromkeys(
            issue
            for result in results
            for issue in result.platform_leakage_issues
            if str(issue).strip()
        )
    )
    return {
        "status": "passed" if not issues else "failed",
        "scope": "generated_artifact_readback_terms_against_platform_source_and_dist",
        "term_count": len(terms),
        "terms": terms,
        "issues": list(issues),
    }


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run installed greenfield post-confirm release simulations.")
    parser.add_argument("--dist-dir", required=True, help="Local release asset directory containing install.sh.")
    parser.add_argument("--version", default=_version_from_pyproject())
    parser.add_argument("--temp-parent", default=str(_default_temp_parent()))
    parser.add_argument(
        "--include-rescue-smoke",
        action="store_true",
        default=True,
        help="Prove installed CLI auto-rescue governed writes. Enabled by default.",
    )
    parser.add_argument(
        "--skip-rescue-smoke",
        action="store_false",
        dest="include_rescue_smoke",
        help="Skip rescue smoke for local debugging only; this is not release proof.",
    )
    parser.add_argument(
        "--include-browser-proof",
        action="store_true",
        help="Run headless generated browser state proof against every generated matrix repo.",
    )
    parser.add_argument(
        "--allow-skipped-browser-proof",
        action="store_true",
        help="Allow omitted browser proof for local debugging only; this is not release proof.",
    )
    parser.add_argument("--json", action="store_true", dest="json_output")
    parser.add_argument(
        "--output-json",
        default="",
        help="Optional path where the full matrix proof payload should be persisted.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    results = run_matrix(
        dist_dir=Path(args.dist_dir),
        version=str(args.version),
        temp_parent=Path(args.temp_parent),
        include_browser_proof=bool(args.include_browser_proof),
    )
    rescue = (
        run_rescue_smoke(
            dist_dir=Path(args.dist_dir),
            version=str(args.version),
            temp_parent=Path(args.temp_parent),
        )
        if bool(args.include_rescue_smoke)
        else None
    )
    browser_proof = browser_proof_summary(results, include_browser_proof=bool(args.include_browser_proof))
    platform_leakage_proof = _platform_leakage_proof_summary(results)
    browser_status = str(browser_proof.get("status") or "").strip()
    browser_passed = browser_status == "passed" or (
        browser_status == "skipped" and bool(args.allow_skipped_browser_proof)
    )
    platform_leakage_passed = str(platform_leakage_proof.get("status") or "").strip() == "passed"
    passed = (
        all(result.quality.passed for result in results)
        and (rescue is None or rescue.passed)
        and browser_passed
        and platform_leakage_passed
    )
    payload = {
        "version": QUALITY_MATRIX_VERSION,
        "status": "passed" if passed else "failed",
        "proof_scope": {
            "standard_path": "real_installed_greenfield_post_confirm_quality_matrix",
            "rescue_path": "synthetic_typed_probe_wiring_only",
            "natural_rescue_quality_proven": False,
            "browser_surface_proof": (
                BROWSER_SURFACE_PROOF_SCOPE if bool(args.include_browser_proof) else "not_requested"
            ),
        },
        "results": [result.to_dict() for result in results],
        "browser_surface_proof": browser_proof,
        "platform_domain_leakage_proof": platform_leakage_proof,
    }
    if rescue is not None:
        payload["rescue_smoke"] = rescue.to_dict()
    if str(args.output_json or "").strip():
        output_path = Path(str(args.output_json)).expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.json_output:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        _print_human_summary(results)
        _print_rescue_summary(rescue)
    return 0 if payload["status"] == "passed" else 1
if __name__ == "__main__":
    raise SystemExit(main())
