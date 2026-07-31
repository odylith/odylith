"""Quality scoring for installed greenfield matrix proof."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any

from greenfield_matrix_package_evidence import evidence_blocks_dimension
from greenfield_matrix_package_evidence import evidence_finding_messages
from greenfield_matrix_package_evidence import package_evidence_findings
from greenfield_matrix_types import GreenfieldArtifactCounts
from greenfield_matrix_types import GreenfieldQualityVerdict
from greenfield_surface_health import REQUIRED_RENDERED_SURFACES
from greenfield_surface_health import SURFACE_PAYLOAD_CONTRACTS
from odylith.runtime.artifact_quality.greenfield_package_quality import greenfield_rendered_package_quality_issues
from odylith.runtime.artifact_quality.greenfield_quality_lenses import build_greenfield_quality_lens_report
from odylith.runtime.common.value_coercion import mapping_copy
from odylith.runtime.domain_intelligence.artifact_tribunal_actors import tribunal_visible_actor_quality_issues
from odylith.runtime.domain_intelligence.greenfield_text import clean_text


PRECONFIRM_BUDGET_SECONDS = 60.0
QUALITY_SCORE_DIMENSIONS = (
    "completion",
    "latency",
    "semantic_manifest",
    "copy_semantic_clarity",
    "governance_depth",
    "traceability",
    "operator_usefulness",
    "implementation_prompts",
    "browser_surface_proof",
    "confirmation_ux",
    "product_manager",
    "architect",
    "engineer",
    "domain_expert",
)


def build_quality_verdict(
    *,
    create_payload: Mapping[str, Any],
    package: Any,
    counts: GreenfieldArtifactCounts,
    surface_issues: Sequence[str] = (),
    browser_surface_issues: Sequence[str] = (),
    browser_surface_proof_attempted: bool = True,
    browser_surface_proof_required: bool = True,
    confirmation_ux_issues: Sequence[str] = (),
    create_returncode: int,
    create_seconds: float,
    create_detail: str = "",
    external_issues: Sequence[str] = (),
) -> GreenfieldQualityVerdict:
    manifest = mapping_copy(create_payload.get("commit_manifest"))
    manifest_lenses = _manifest_lenses(manifest)
    package_lens_report = mapping_copy(build_greenfield_quality_lens_report(package)) if create_returncode == 0 else {}
    package_lenses = _package_lenses(package_lens_report)
    evidence_findings = tuple(package_evidence_findings(package)) if create_returncode == 0 else ()
    rendered_issues = _rendered_issues(
        create_returncode=create_returncode,
        package=package,
        package_lens_report=package_lens_report,
        evidence_findings=evidence_findings,
        create_payload=create_payload,
        surface_issues=surface_issues,
    )
    prompt_issues = tuple(issue for issue in rendered_issues if issue.startswith("Project implementation prompt "))
    issues = [
        *rendered_issues,
        *_browser_surface_proof_issues(
            create_returncode=create_returncode,
            browser_surface_proof_attempted=browser_surface_proof_attempted,
            browser_surface_proof_required=browser_surface_proof_required,
            browser_surface_issues=browser_surface_issues,
        ),
        *(str(issue).strip() for issue in confirmation_ux_issues if str(issue).strip()),
        *_create_failure_detail_issues(create_returncode=create_returncode, create_detail=create_detail),
        *_manifest_issues(
            manifest,
            product_create_transaction=mapping_copy(create_payload.get("product_create_transaction")),
        ),
        *completion_issues(counts=counts, create_returncode=create_returncode, create_seconds=create_seconds),
        *(str(issue).strip() for issue in external_issues if str(issue).strip()),
    ]
    lenses = _quality_lenses(
        manifest_lenses=manifest_lenses,
        package_lenses=package_lenses,
        evidence_findings=evidence_findings,
        counts=counts,
        manifest=manifest,
        create_returncode=create_returncode,
    )
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
        browser_surface_proof_attempted=browser_surface_proof_attempted,
        browser_surface_proof_required=browser_surface_proof_required,
        browser_surface_issues=browser_surface_issues,
        confirmation_ux_issues=confirmation_ux_issues,
    )
    final_score = _final_quality_score(
        scores=scores,
        manifest=manifest,
        create_returncode=create_returncode,
        rendered_issues=rendered_issues,
        prompt_issues=prompt_issues,
        external_issues=external_issues,
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
            external_issues=external_issues,
        ),
        score_basis=_score_basis(scores),
    )


def completion_issues(
    *,
    counts: GreenfieldArtifactCounts,
    create_returncode: int,
    create_seconds: float,
) -> tuple[str, ...]:
    issues: list[str] = []
    if create_returncode != 0:
        issues.append(f"commit-only create exited with code {create_returncode}")
    if create_seconds >= PRECONFIRM_BUDGET_SECONDS:
        issues.append(f"commit-only create exceeded {PRECONFIRM_BUDGET_SECONDS:.0f}s: {create_seconds:.3f}s")
    minimums = required_count_minimums()
    for label, value in _count_values(counts).items():
        if value < minimums[label]:
            issues.append(f"{label} incomplete: expected at least {minimums[label]}, found {value}")
    domain_term_minimum = required_domain_term_hits(counts)
    if counts.domain_term_hits < domain_term_minimum:
        issues.append(
            f"domain term coverage too low: expected at least {domain_term_minimum}, found {counts.domain_term_hits}"
        )
    return tuple(issues)


def command_excerpt(value: str, limit: int = 4000) -> str:
    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    return f"{text[:limit].rstrip()}...[truncated]"


def required_count_minimums() -> dict[str, int]:
    return {
        "Radar workstreams": 4,
        "Registry component specs": 3,
        "Atlas Mermaid sources": 4,
        "Compass records": 1,
        "release records": 1,
        "project brief records": 1,
        "trace nodes": 12,
        "trace workstreams": 4,
        "rendered surfaces": len(REQUIRED_RENDERED_SURFACES),
        "rendered surface payloads": len(SURFACE_PAYLOAD_CONTRACTS) * 2,
        "Atlas rendered diagram assets": 8,
        "Project implementation prompts": 5,
    }


def count_key(label: str) -> str:
    return {
        "Radar workstreams": "radar_workstreams",
        "Registry component specs": "registry_component_specs",
        "Atlas Mermaid sources": "atlas_mermaid_sources",
        "Compass records": "compass_records",
        "release records": "release_records",
        "project brief records": "project_brief_records",
        "trace nodes": "trace_nodes",
        "trace workstreams": "trace_workstreams",
        "rendered surfaces": "rendered_surfaces",
        "rendered surface payloads": "rendered_surface_payloads",
        "Atlas rendered diagram assets": "atlas_rendered_assets",
        "Project implementation prompts": "project_implementation_prompts",
    }.get(label, label)


def required_domain_term_hits(counts: GreenfieldArtifactCounts) -> int:
    declared_terms = int(counts.required_domain_terms or 0)
    if declared_terms > 0:
        return declared_terms
    return 3


def write_committed(manifest: Mapping[str, Any]) -> bool:
    return not write_transaction_custody_issues(manifest)


def write_transaction_custody_issues(
    manifest: Mapping[str, Any],
    *,
    product_create_transaction: Mapping[str, Any] | None = None,
) -> tuple[str, ...]:
    transaction = mapping_copy(manifest.get("write_transaction"))
    manifest_transaction = mapping_copy(manifest.get("product_create_transaction"))
    issues: list[str] = []
    if str(transaction.get("status", "")).strip() != "committed":
        issues.append("write transaction was not committed")
    if transaction.get("commit_only") is not True:
        issues.append("write transaction did not prove commit-only apply")
    if transaction.get("prewrite_clean_before_commit") is not True:
        issues.append("write transaction did not prove a clean prewrite package")
    if str(transaction.get("rollback_guard", "")).strip() != "enabled":
        issues.append("write transaction did not enable rollback")
    if not _is_sha256_digest(transaction.get("product_create_transaction_hash")):
        issues.append("write transaction is missing a valid ProductCreateTransaction hash")
    if not _is_sha256_digest(transaction.get("product_facts_sha256")):
        issues.append("write transaction is missing a valid Product Intent facts hash")
    if not _is_sha256_digest(transaction.get("repository_write_set_hash")):
        issues.append("write transaction is missing a valid repository write-set hash")
    issues.extend(
        _transaction_hash_match_issues(
            transaction=transaction,
            expected=manifest_transaction,
            source="manifest",
        )
    )
    if product_create_transaction is not None:
        issues.extend(
            _transaction_hash_match_issues(
                transaction=transaction,
                expected=product_create_transaction,
                source="create payload",
            )
        )
    return tuple(issues)


def _is_sha256_digest(value: Any) -> bool:
    digest = str(value or "").strip()
    return len(digest) == 64 and all(char in "0123456789abcdef" for char in digest)


def _transaction_hash_match_issues(
    *,
    transaction: Mapping[str, Any],
    expected: Mapping[str, Any],
    source: str,
) -> tuple[str, ...]:
    if not expected:
        return (f"{source} ProductCreateTransaction summary is missing",)
    issues: list[str] = []
    expected_transaction_hash = str(expected.get("transaction_hash", "")).strip()
    expected_product_facts_hash = str(expected.get("product_facts_sha256", "")).strip()
    expected_write_set_hash = str(expected.get("repository_write_set_hash", "")).strip()
    if not _is_sha256_digest(expected_transaction_hash):
        issues.append(f"{source} ProductCreateTransaction hash is invalid")
    elif str(transaction.get("product_create_transaction_hash", "")).strip() != expected_transaction_hash:
        issues.append(f"write transaction ProductCreateTransaction hash does not match the {source} summary")
    if not _is_sha256_digest(expected_product_facts_hash):
        issues.append(f"{source} Product Intent facts hash is invalid")
    elif str(transaction.get("product_facts_sha256", "")).strip() != expected_product_facts_hash:
        issues.append(f"write transaction Product Intent facts hash does not match the {source} summary")
    if not _is_sha256_digest(expected_write_set_hash):
        issues.append(f"{source} repository write-set hash is invalid")
    elif str(transaction.get("repository_write_set_hash", "")).strip() != expected_write_set_hash:
        issues.append(f"write transaction repository write-set hash does not match the {source} summary")
    return tuple(issues)


def elapsed_time_issues(manifest: Mapping[str, Any], *, budget_seconds: float) -> tuple[str, ...]:
    value = manifest.get("whole_project_elapsed_seconds")
    try:
        elapsed = float(value)
    except (TypeError, ValueError):
        return ("manifest is missing a positive measured elapsed time",)
    if not math.isfinite(elapsed) or elapsed <= 0.0:
        return ("manifest is missing a positive measured elapsed time",)
    if elapsed >= float(budget_seconds):
        return (f"manifest reports elapsed time outside the {float(budget_seconds):g}-second budget",)
    return ()


def _rendered_issues(
    *,
    create_returncode: int,
    package: Any,
    package_lens_report: Mapping[str, Any],
    evidence_findings: Sequence[Any],
    create_payload: Mapping[str, Any],
    surface_issues: Sequence[str],
) -> tuple[str, ...]:
    if create_returncode != 0:
        return ()
    return tuple(
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


def _quality_lenses(
    *,
    manifest_lenses: Mapping[str, Any],
    package_lenses: Mapping[str, Any],
    evidence_findings: Sequence[Any],
    counts: GreenfieldArtifactCounts,
    manifest: Mapping[str, Any],
    create_returncode: int,
) -> dict[str, bool]:
    return {
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
            and counts.release_records >= 1
            and create_returncode == 0
            and write_committed(manifest)
        ),
        "domain_expert": (
            _lens_passed(manifest_lenses, "domain_expert")
            and _lens_passed(package_lenses, "domain_expert")
            and not evidence_blocks_dimension(evidence_findings, "domain_expert")
            and counts.domain_term_hits >= required_domain_term_hits(counts)
        ),
    }


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
    browser_surface_proof_attempted: bool = True,
    browser_surface_proof_required: bool = True,
    browser_surface_issues: Sequence[str] = (),
    confirmation_ux_issues: Sequence[str] = (),
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
        "browser_surface_proof": _browser_surface_proof_score(
            create_returncode=create_returncode,
            browser_surface_proof_attempted=browser_surface_proof_attempted,
            browser_surface_proof_required=browser_surface_proof_required,
            browser_surface_issues=browser_surface_issues,
        ),
        "confirmation_ux": _confirmation_ux_score(
            create_returncode=create_returncode,
            confirmation_ux_issues=confirmation_ux_issues,
        ),
        "product_manager": 10 if lenses.get("product_manager") else 0,
        "architect": 10 if lenses.get("architect") else 0,
        "engineer": 10 if lenses.get("engineer") else 0,
        "domain_expert": 10 if lenses.get("domain_expert") else 0,
    }


def _completion_score(*, manifest: Mapping[str, Any], counts: GreenfieldArtifactCounts, create_returncode: int) -> int:
    if create_returncode != 0 or not write_committed(manifest):
        return 0
    ratio = _count_floor_ratio(counts, required_count_minimums())
    return 10 if ratio >= 1.0 else int(ratio * 8)


def _latency_score(*, create_returncode: int, create_seconds: float) -> int:
    if create_returncode != 0:
        return 0
    if create_seconds < PRECONFIRM_BUDGET_SECONDS:
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
    if create_returncode != 0 or not write_committed(manifest):
        return 0
    return max(0, 10 - (2 * len(tuple(rendered_issues))))


def _governance_depth_score(counts: GreenfieldArtifactCounts) -> int:
    ratio = _count_floor_ratio(counts, required_count_minimums())
    return 10 if ratio >= 1.0 else int(ratio * 10)


def _traceability_score(counts: GreenfieldArtifactCounts) -> int:
    minimums = {"trace nodes": 12, "trace workstreams": 4}
    values = {"trace nodes": counts.trace_nodes, "trace workstreams": counts.trace_workstreams}
    ratio = _count_floor_ratio(values, minimums)
    return 10 if ratio >= 1.0 else int(ratio * 10)


def _operator_usefulness_score(*, counts: GreenfieldArtifactCounts, create_returncode: int) -> int:
    if create_returncode != 0:
        return 0
    minimums = {
        "release records": 1,
        "project brief records": 1,
        "rendered surfaces": len(REQUIRED_RENDERED_SURFACES),
    }
    values = {
        "release records": counts.release_records,
        "project brief records": counts.project_brief_records,
        "rendered surfaces": counts.rendered_surfaces,
    }
    ratio = _count_floor_ratio(values, minimums)
    return 10 if ratio >= 1.0 else int(ratio * 10)


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
    external_issues: Sequence[str] = (),
) -> int:
    if create_returncode != 0 or not write_committed(manifest) or any(str(issue).strip() for issue in external_issues):
        return 0
    scored_dimensions = [
        int(scores.get(dimension, 0))
        for dimension in QUALITY_SCORE_DIMENSIONS
        if int(scores.get(dimension, 0)) >= 0
    ]
    score = min(scored_dimensions) if scored_dimensions else 0
    if rendered_issues:
        score = min(score, 6)
    if prompt_issues:
        score = min(score, 4)
    if _manifest_issues(manifest):
        score = min(score, 4)
    return max(0, min(10, score))


def _score_basis(scores: Mapping[str, int]) -> str:
    if int(scores.get("browser_surface_proof", 0)) < 0:
        return "volume_discovery_without_browser_surface_proof"
    return "release"


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
    external_issues: Sequence[str] = (),
) -> tuple[str, ...]:
    if create_returncode != 0 or not write_committed(manifest):
        return ("score forced to 0 because commit-only create did not commit governed records",)
    if any(str(issue).strip() for issue in external_issues):
        return ("score forced to 0 because commit readback differs from the sealed pre-confirm transaction",)
    explanations: list[str] = []
    if rendered_issues:
        explanations.append(f"copy/semantic artifact findings cap release score at 6; findings={len(tuple(rendered_issues))}")
    if prompt_issues:
        explanations.append(f"Project implementation prompt findings cap release score at 4; findings={len(tuple(prompt_issues))}")
    if _manifest_issues(manifest):
        explanations.append("manifest or transaction issues cap release score at 4")
    unscored_dimensions = [dimension for dimension, value in scores.items() if int(value) < 0]
    scored_values = [int(value) for value in scores.values() if int(value) >= 0]
    if score == 10 and scored_values and all(value == 10 for value in scored_values):
        if unscored_dimensions:
            explanations.append(
                "all scored release-quality dimensions scored 10; "
                f"unscored dimensions: {', '.join(unscored_dimensions)}"
            )
            explanations.append(
                "browser surface proof was not requested and is unscored; "
                "this is volume-discovery evidence, not complete browser release proof"
            )
        else:
            explanations.append("all brutal release-quality dimensions scored 10")
        explanations.extend(_passing_score_evidence(counts, prompt_issues, lenses))
        return tuple(explanations)
    weakest = [dimension for dimension, value in scores.items() if int(value) == score]
    if weakest:
        explanations.append(f"final score follows weakest dimension: {', '.join(weakest)}")
    return tuple(explanations)


def _passing_score_evidence(
    counts: GreenfieldArtifactCounts,
    prompt_issues: Sequence[str],
    lenses: Mapping[str, bool],
) -> tuple[str, ...]:
    passed_lenses = ", ".join(name for name, passed in lenses.items() if passed)
    return (
        "completion evidence: "
        f"{counts.radar_workstreams} Radar workstreams, "
        f"{counts.registry_component_specs} Registry specs, "
        f"{counts.atlas_mermaid_sources} Atlas diagrams, "
        f"{counts.project_brief_records} project brief records",
        "rendered-surface evidence: "
        f"{counts.rendered_surfaces} surfaces, "
        f"{counts.rendered_surface_payloads} payload assets, "
        f"{counts.atlas_rendered_assets} Atlas rendered assets",
        "traceability and prompt evidence: "
        f"{counts.trace_nodes} trace nodes, "
        f"{counts.trace_workstreams} trace workstreams, "
        f"{counts.project_implementation_prompts} Project implementation prompts, "
        f"{len(tuple(prompt_issues))} prompt findings",
        f"expert-lens evidence: {passed_lenses} passed",
    )


def _count_floor_ratio(values: GreenfieldArtifactCounts | Mapping[str, int], minimums: Mapping[str, int]) -> float:
    rows = values.to_dict() if isinstance(values, GreenfieldArtifactCounts) else dict(values)
    if not minimums:
        return 1.0
    ratios = []
    for label, minimum in minimums.items():
        if minimum <= 0:
            continue
        value = int(rows.get(count_key(label), rows.get(label, 0)) or 0)
        ratios.append(min(1.0, value / float(minimum)))
    return min(ratios) if ratios else 1.0


def _count_values(counts: GreenfieldArtifactCounts) -> dict[str, int]:
    return {
        "Radar workstreams": counts.radar_workstreams,
        "Registry component specs": counts.registry_component_specs,
        "Atlas Mermaid sources": counts.atlas_mermaid_sources,
        "Compass records": counts.compass_records,
        "release records": counts.release_records,
        "project brief records": counts.project_brief_records,
        "trace nodes": counts.trace_nodes,
        "trace workstreams": counts.trace_workstreams,
        "rendered surfaces": counts.rendered_surfaces,
        "rendered surface payloads": counts.rendered_surface_payloads,
        "Atlas rendered diagram assets": counts.atlas_rendered_assets,
        "Project implementation prompts": counts.project_implementation_prompts,
    }


def _manifest_issues(
    manifest: Mapping[str, Any],
    *,
    product_create_transaction: Mapping[str, Any] | None = None,
) -> tuple[str, ...]:
    if not manifest:
        return ("pre-confirm quality manifest missing",)
    issues: list[str] = []
    if str(manifest.get("status", "")).strip() != "passed":
        issues.append(f"pre-confirm quality manifest status is {manifest.get('status')!r}")
    if str(manifest.get("validation_status", "")).strip() != "passed":
        issues.append(f"pre-confirm validation status is {manifest.get('validation_status')!r}")
    if int(manifest.get("issue_count") or 0) != 0:
        issues.append(f"pre-confirm quality manifest has {manifest.get('issue_count')} issue(s)")
    issues.extend(
        f"commit-only {issue}"
        for issue in write_transaction_custody_issues(
            manifest,
            product_create_transaction=product_create_transaction,
        )
    )
    issues.extend(
        f"pre-confirm {issue}"
        for issue in elapsed_time_issues(manifest, budget_seconds=PRECONFIRM_BUDGET_SECONDS)
    )
    lens_report = mapping_copy(manifest.get("quality_lenses"))
    if str(lens_report.get("status", "")).strip() != "passed":
        issues.append("pre-confirm quality lens report did not pass")
    return tuple(issues)


def _validation_gate_actor_issues(*, create_payload: Mapping[str, Any], package: Any) -> tuple[str, ...]:
    create_gate = mapping_copy(create_payload.get("validation_gate"))
    accepted_gate = mapping_copy(mapping_copy(getattr(package, "accepted_project_preview", {})).get("validation_gate"))
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


def _browser_surface_proof_issues(
    *,
    create_returncode: int,
    browser_surface_proof_attempted: bool,
    browser_surface_proof_required: bool,
    browser_surface_issues: Sequence[str] = (),
) -> tuple[str, ...]:
    if create_returncode != 0:
        return ()
    issues = tuple(str(issue).strip() for issue in browser_surface_issues if str(issue).strip())
    if issues:
        return issues
    if browser_surface_proof_attempted or not browser_surface_proof_required:
        return ()
    return ("browser surface proof was not attempted; premium release scoring requires headless rendered-surface proof",)


def _browser_surface_proof_score(
    *,
    create_returncode: int,
    browser_surface_proof_attempted: bool,
    browser_surface_proof_required: bool,
    browser_surface_issues: Sequence[str] = (),
) -> int:
    if create_returncode != 0:
        return 0
    if browser_surface_issues:
        return 0
    if browser_surface_proof_attempted:
        return 10
    if not browser_surface_proof_required:
        return -1
    return 0


def _confirmation_ux_score(*, create_returncode: int, confirmation_ux_issues: Sequence[str]) -> int:
    """Score the visible decision rail and post-success routes as one hard contract."""

    if create_returncode != 0 or confirmation_ux_issues:
        return 0
    return 10


def _manifest_lenses(manifest: Mapping[str, Any]) -> Mapping[str, Any]:
    return mapping_copy(mapping_copy(manifest.get("quality_lenses")).get("lenses"))


def _package_lenses(package_lens_report: Mapping[str, Any]) -> Mapping[str, Any]:
    return mapping_copy(package_lens_report.get("lenses"))


def _package_lens_issues(package_lens_report: Mapping[str, Any]) -> tuple[str, ...]:
    if not package_lens_report:
        return ("independent package quality lens report missing",)
    issues = tuple(str(issue).strip() for issue in package_lens_report.get("issues", ()) if str(issue).strip())
    if issues:
        return issues
    if str(package_lens_report.get("status", "")).strip() != "passed":
        return ("independent package quality lens report did not pass",)
    return ()


def _lens_passed(lenses: Mapping[str, Any], name: str) -> bool:
    return str(mapping_copy(lenses.get(name)).get("status", "")).strip() == "passed"


def _create_failure_detail_issues(*, create_returncode: int, create_detail: str) -> tuple[str, ...]:
    if create_returncode == 0:
        return ()
    detail = command_excerpt(create_detail)
    return (f"commit-only create failure detail: {detail}",) if detail else ()


__all__ = [
    "PRECONFIRM_BUDGET_SECONDS",
    "QUALITY_SCORE_DIMENSIONS",
    "build_quality_verdict",
    "command_excerpt",
    "completion_issues",
    "count_key",
    "required_count_minimums",
    "required_domain_term_hits",
    "elapsed_time_issues",
    "write_committed",
    "write_transaction_custody_issues",
]
