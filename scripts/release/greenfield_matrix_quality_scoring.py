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
from odylith.runtime.common.value_coercion import mapping_copy
from odylith.runtime.domain_intelligence.artifact_tribunal_actors import (
    TRIBUNAL_STABLE_ROLES,
    tribunal_visible_actor_quality_issues,
)
from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    AUTHORED_PROJECTION_ORIGIN,
)
from odylith.runtime.domain_intelligence.greenfield_model_intent_authoring import (
    MAX_GREENFIELD_SEMANTIC_CALLS,
)
from odylith.runtime.domain_intelligence.greenfield_text import clean_text
from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import (
    get_greenfield_model_profile,
    model_profile_id_for_repair_tier,
)


PRECONFIRM_BUDGET_SECONDS = 60.0
UNSCORED_QUALITY_SCORE = -1
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
INDEPENDENT_SEMANTIC_LENS_DIMENSIONS = (
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
    proposal_seconds: float,
    create_seconds: float,
    create_detail: str = "",
    external_issues: Sequence[str] = (),
) -> GreenfieldQualityVerdict:
    manifest = mapping_copy(create_payload.get("commit_manifest"))
    manifest_lenses = _manifest_lenses(manifest)
    evidence_findings = tuple(package_evidence_findings(package)) if create_returncode == 0 else ()
    rendered_issues = _rendered_issues(
        create_returncode=create_returncode,
        package=package,
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
        *completion_issues(
            counts=counts,
            manifest=manifest,
            create_returncode=create_returncode,
            proposal_seconds=proposal_seconds,
            create_seconds=create_seconds,
        ),
        *(str(issue).strip() for issue in external_issues if str(issue).strip()),
    ]
    lenses = _quality_lenses(
        manifest_lenses=manifest_lenses,
        evidence_findings=evidence_findings,
        counts=counts,
        manifest=manifest,
        create_returncode=create_returncode,
    )
    issues.extend(_quality_lens_issues(manifest_lenses=manifest_lenses, lenses=lenses))
    scores = _quality_scores(
        manifest=manifest,
        counts=counts,
        create_returncode=create_returncode,
        proposal_seconds=proposal_seconds,
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
    unscored_dimensions = _automated_unscored_dimensions(scores)
    if unscored_dimensions:
        issues.append(
            "release-quality evidence is unproven for unscored dimension(s): "
            + ", ".join(unscored_dimensions)
        )
    unique_issues = tuple(dict.fromkeys(issue for issue in issues if str(issue).strip()))
    final_score = _final_quality_score(
        scores=scores,
        manifest=manifest,
        create_returncode=create_returncode,
        rendered_issues=rendered_issues,
        prompt_issues=prompt_issues,
        external_issues=external_issues,
    )
    return GreenfieldQualityVerdict(
        passed=not unique_issues and final_score == 10,
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
    manifest: Mapping[str, Any],
    create_returncode: int,
    proposal_seconds: float,
    create_seconds: float,
) -> tuple[str, ...]:
    issues: list[str] = []
    if create_returncode != 0:
        issues.append(f"commit-only create exited with code {create_returncode}")
    if create_seconds >= PRECONFIRM_BUDGET_SECONDS:
        issues.append(f"commit-only create exceeded {PRECONFIRM_BUDGET_SECONDS:.0f}s: {create_seconds:.3f}s")
    issues.extend(proposal_time_issues(manifest, proposal_seconds=proposal_seconds))
    return tuple(issues)


def command_excerpt(value: str, limit: int = 4000) -> str:
    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    return f"{text[:limit].rstrip()}...[truncated]"


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


def proposal_time_issues(manifest: Mapping[str, Any], *, proposal_seconds: float) -> tuple[str, ...]:
    budget_seconds = _sealed_tier_budget_seconds(manifest)
    if budget_seconds is None:
        return ("proposal manifest does not declare an approved 60/90/120 repair-tier budget",)
    try:
        elapsed = float(proposal_seconds)
    except (TypeError, ValueError):
        return ("proposal proof is missing a positive measured elapsed time",)
    if not math.isfinite(elapsed) or elapsed <= 0.0:
        return ("proposal proof is missing a positive measured elapsed time",)
    if elapsed >= budget_seconds:
        return (f"proposal exceeded its sealed {budget_seconds:g}-second tier budget: {elapsed:.3f}s",)
    return ()


def _rendered_issues(
    *,
    create_returncode: int,
    package: Any,
    evidence_findings: Sequence[Any],
    create_payload: Mapping[str, Any],
    surface_issues: Sequence[str],
) -> tuple[str, ...]:
    if create_returncode != 0:
        return ()
    return tuple(
        dict.fromkeys(
            (
                *tuple(evidence_finding_messages(evidence_findings)),
                *tuple(_validation_gate_actor_issues(create_payload=create_payload, package=package)),
                *tuple(str(issue).strip() for issue in surface_issues if str(issue).strip()),
            )
        )
    )


def _quality_lenses(
    *,
    manifest_lenses: Mapping[str, Any],
    evidence_findings: Sequence[Any],
    counts: GreenfieldArtifactCounts,
    manifest: Mapping[str, Any],
    create_returncode: int,
) -> dict[str, bool]:
    del counts
    return {
        "product_manager": (
            _lens_passed(manifest_lenses, "product_manager")
            and not evidence_blocks_dimension(evidence_findings, "product_manager")
        ),
        "architect": (
            _lens_passed(manifest_lenses, "architect")
            and not evidence_blocks_dimension(evidence_findings, "architect")
        ),
        "engineer": (
            _lens_passed(manifest_lenses, "engineer")
            and not evidence_blocks_dimension(evidence_findings, "engineer")
            and create_returncode == 0
            and write_committed(manifest)
        ),
        "domain_expert": (
            _lens_passed(manifest_lenses, "domain_expert")
            and not evidence_blocks_dimension(evidence_findings, "domain_expert")
        ),
    }


def _quality_scores(
    *,
    manifest: Mapping[str, Any],
    counts: GreenfieldArtifactCounts,
    create_returncode: int,
    proposal_seconds: float,
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
    package_evidence_measured = create_returncode == 0
    return {
        "completion": _completion_score(
            manifest=manifest,
            create_returncode=create_returncode,
            evidence_findings=evidence_findings,
            evidence_measured=package_evidence_measured,
        ),
        "latency": _latency_score(
            manifest=manifest,
            create_returncode=create_returncode,
            proposal_seconds=proposal_seconds,
            create_seconds=create_seconds,
        ),
        "semantic_manifest": _semantic_manifest_score(manifest),
        "copy_semantic_clarity": _copy_semantic_clarity_score(
            manifest=manifest,
            create_returncode=create_returncode,
            rendered_issues=rendered_issues,
        ),
        "governance_depth": _evidence_backed_dimension_score(
            dimension="governance_depth",
            create_returncode=create_returncode,
            evidence_findings=evidence_findings,
            evidence_measured=package_evidence_measured,
        ),
        "traceability": _traceability_score(
            counts=counts,
            create_returncode=create_returncode,
        ),
        "operator_usefulness": _evidence_backed_dimension_score(
            dimension="operator_usefulness",
            create_returncode=create_returncode,
            evidence_findings=evidence_findings,
            evidence_measured=package_evidence_measured,
        ),
        "implementation_prompts": _implementation_prompt_score(
            create_returncode=create_returncode,
            prompt_issues=prompt_issues,
            evidence_findings=evidence_findings,
            evidence_measured=package_evidence_measured,
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
        **{
            lens: _independent_lens_score(
                manifest_lenses=_manifest_lenses(manifest),
                lens=lens,
                passed=bool(lenses.get(lens)),
            )
            for lens in INDEPENDENT_SEMANTIC_LENS_DIMENSIONS
        },
    }


def _completion_score(
    *,
    manifest: Mapping[str, Any],
    create_returncode: int,
    evidence_findings: Sequence[Any],
    evidence_measured: bool,
) -> int:
    if create_returncode != 0 or not write_committed(manifest):
        return 0
    return _evidence_backed_dimension_score(
        dimension="completion",
        create_returncode=create_returncode,
        evidence_findings=evidence_findings,
        evidence_measured=evidence_measured,
    )


def _latency_score(
    *,
    manifest: Mapping[str, Any],
    create_returncode: int,
    proposal_seconds: float,
    create_seconds: float,
) -> int:
    if create_returncode != 0:
        return 0
    if create_seconds < PRECONFIRM_BUDGET_SECONDS and not proposal_time_issues(
        manifest,
        proposal_seconds=proposal_seconds,
    ):
        return 10
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


def _evidence_backed_dimension_score(
    *,
    dimension: str,
    create_returncode: int,
    evidence_findings: Sequence[Any],
    evidence_measured: bool,
) -> int:
    if create_returncode != 0:
        return 0
    if not evidence_measured:
        return UNSCORED_QUALITY_SCORE
    return 0 if evidence_blocks_dimension(evidence_findings, dimension) else 10


def _traceability_score(*, counts: GreenfieldArtifactCounts, create_returncode: int) -> int:
    if create_returncode != 0:
        return 0
    if counts.trace_nodes == 0 and counts.trace_workstreams == 0:
        return UNSCORED_QUALITY_SCORE
    if (
        counts.radar_workstreams <= 0
        or counts.trace_nodes < counts.trace_workstreams
        or counts.trace_workstreams != counts.radar_workstreams
    ):
        return 0
    return 10


def _implementation_prompt_score(
    *,
    create_returncode: int,
    prompt_issues: Sequence[str],
    evidence_findings: Sequence[Any] = (),
    evidence_measured: bool,
) -> int:
    if create_returncode != 0 or prompt_issues:
        return 0
    return _evidence_backed_dimension_score(
        dimension="implementation_prompts",
        create_returncode=create_returncode,
        evidence_findings=evidence_findings,
        evidence_measured=evidence_measured,
    )


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
    if _automated_unscored_dimensions(scores):
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
    unscored_dimensions = _unscored_dimensions(scores)
    if any(dimension in unscored_dimensions for dimension in INDEPENDENT_SEMANTIC_LENS_DIMENSIONS):
        return "automated_contract_independent_semantic_review_required"
    if unscored_dimensions == ("browser_surface_proof",):
        return "volume_discovery_without_browser_surface_proof"
    if unscored_dimensions:
        return "release_quality_unproven"
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
    automated_unscored_dimensions = _automated_unscored_dimensions(scores)
    if automated_unscored_dimensions:
        explanations.append(
            "release-quality score is unproven because positive evidence is missing for: "
            + ", ".join(automated_unscored_dimensions)
        )
        return tuple(explanations)
    independent_unscored_dimensions = tuple(
        dimension
        for dimension in INDEPENDENT_SEMANTIC_LENS_DIMENSIONS
        if int(scores.get(dimension, UNSCORED_QUALITY_SCORE)) < 0
    )
    if independent_unscored_dimensions:
        explanations.append(
            "automated contract passed; independent semantic review remains required for: "
            + ", ".join(independent_unscored_dimensions)
        )
        explanations.extend(_passing_score_evidence(counts, prompt_issues, lenses))
        return tuple(explanations)
    scored_values = [int(value) for value in scores.values() if int(value) >= 0]
    if score == 10 and scored_values and all(value == 10 for value in scored_values):
        explanations.append("all automated and independently evidenced dimensions scored 10")
        explanations.extend(_passing_score_evidence(counts, prompt_issues, lenses))
        return tuple(explanations)
    weakest = [dimension for dimension, value in scores.items() if int(value) == score]
    if weakest:
        explanations.append(f"final score follows weakest dimension: {', '.join(weakest)}")
    return tuple(explanations)


def _unscored_dimensions(scores: Mapping[str, int]) -> tuple[str, ...]:
    return tuple(
        dimension
        for dimension in QUALITY_SCORE_DIMENSIONS
        if int(scores.get(dimension, UNSCORED_QUALITY_SCORE)) < 0
    )


def _automated_unscored_dimensions(scores: Mapping[str, int]) -> tuple[str, ...]:
    """Return gaps owned by the automated per-case contract."""

    return tuple(
        dimension
        for dimension in _unscored_dimensions(scores)
        if dimension not in INDEPENDENT_SEMANTIC_LENS_DIMENSIONS
    )


def _lens_evidence_claimed(lenses: Mapping[str, Any], name: str) -> bool:
    status = str(mapping_copy(lenses.get(name)).get("status", "")).strip().casefold()
    return status not in {"", "not_applicable", "unproven"}


def _independent_lens_score(
    *,
    manifest_lenses: Mapping[str, Any],
    lens: str,
    passed: bool,
) -> int:
    if not _lens_evidence_claimed(manifest_lenses, lens):
        return UNSCORED_QUALITY_SCORE
    return 10 if passed else 0


def _quality_lens_issues(
    *,
    manifest_lenses: Mapping[str, Any],
    lenses: Mapping[str, bool],
) -> tuple[str, ...]:
    return tuple(
        f"{lens} release-matrix lens failed"
        for lens, passed in lenses.items()
        if _lens_evidence_claimed(manifest_lenses, lens) and not passed
    )


def _passing_score_evidence(
    counts: GreenfieldArtifactCounts,
    prompt_issues: Sequence[str],
    lenses: Mapping[str, bool],
) -> tuple[str, ...]:
    passed_lenses = ", ".join(name for name, passed in lenses.items() if passed)
    evidence = [
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
    ]
    if passed_lenses:
        evidence.append(f"expert-lens evidence: {passed_lenses} passed")
    return tuple(evidence)


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
    tier_budget_seconds = _sealed_tier_budget_seconds(manifest)
    if tier_budget_seconds is None:
        issues.append("pre-confirm manifest does not declare an approved 60/90/120 repair-tier budget")
    lens_report = mapping_copy(manifest.get("quality_lenses"))
    if (
        str(lens_report.get("status", "")).strip() != "passed"
        and not _typed_structural_validation_passed(manifest)
    ):
        issues.append("pre-confirm quality lens report did not pass")
    return tuple(issues)


def _sealed_tier_budget_seconds(manifest: Mapping[str, Any]) -> float | None:
    requested_tier = str(manifest.get("requested_repair_tier", "")).strip()
    active_tier = str(manifest.get("repair_tier", "")).strip()
    try:
        selected_profile = get_greenfield_model_profile(
            model_profile_id_for_repair_tier(requested_tier)
        )
        declared = float(manifest.get("budget_seconds"))
    except (TypeError, ValueError):
        return None
    if active_tier != selected_profile.repair_tier:
        return None
    expected = selected_profile.consumer_budget_seconds
    return expected if declared == expected else None


def _validation_gate_actor_issues(*, create_payload: Mapping[str, Any], package: Any) -> tuple[str, ...]:
    create_gate = mapping_copy(create_payload.get("validation_gate"))
    accepted_gate = mapping_copy(mapping_copy(getattr(package, "accepted_project_preview", {})).get("validation_gate"))
    sources = (
        ("create payload", create_gate),
        ("accepted-project readback", accepted_gate),
    )
    issues: list[str] = []
    source_labels: dict[str, dict[str, str]] = {}
    proposal = mapping_copy(getattr(package, "proposal", {}))
    authored_projection = proposal.get("projection_origin") == AUTHORED_PROJECTION_ORIGIN
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
        actor_issues = (
            _authored_visible_actor_quality_issues(rows)
            if authored_projection
            else tribunal_visible_actor_quality_issues(rows)
        )
        issues.extend(f"{source_name} {issue}" for issue in actor_issues)
    if source_labels.get("create payload") and source_labels.get("accepted-project readback"):
        if source_labels["create payload"] != source_labels["accepted-project readback"]:
            issues.append("accepted-project validation gate visible actors drifted from create payload")
    return tuple(dict.fromkeys(issue for issue in issues if str(issue).strip()))


def _authored_visible_actor_quality_issues(
    visible_actors: Sequence[Mapping[str, Any]],
) -> tuple[str, ...]:
    """Validate the closed authored role contract without parsing actor labels."""

    roles = [str(row.get("stable_role") or "").strip() for row in visible_actors]
    issues: list[str] = []
    for role in TRIBUNAL_STABLE_ROLES:
        matching = [row for row in visible_actors if str(row.get("stable_role") or "").strip() == role]
        if not matching:
            issues.append(f"Tribunal visible actor missing for {role}")
            continue
        if len(matching) > 1:
            issues.append(f"Tribunal visible actor duplicated for {role}")
            continue
        row = matching[0]
        for field in ("visible_actor", "actor_source", "responsibility"):
            if not clean_text(row.get(field)):
                issues.append(f"Tribunal visible actor for {role} is missing {field}")
    unexpected = sorted(set(roles) - set(TRIBUNAL_STABLE_ROLES))
    if unexpected:
        issues.append("Tribunal visible actors contain unsupported roles: " + ", ".join(unexpected))
    return tuple(issues)


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


def _lens_passed(lenses: Mapping[str, Any], name: str) -> bool:
    return str(mapping_copy(lenses.get(name)).get("status", "")).strip() == "passed"


def _typed_structural_validation_passed(manifest: Mapping[str, Any]) -> bool:
    """Authenticate the authored route's explicit replacement for prose lenses."""

    lens_report = mapping_copy(manifest.get("quality_lenses"))
    semantic_compiler = mapping_copy(manifest.get("semantic_compiler"))
    model_authoring = mapping_copy(manifest.get("model_authoring"))
    semantic_model_call_count = model_authoring.get("semantic_model_call_count")
    return (
        str(manifest.get("status", "")).strip() == "passed"
        and str(manifest.get("validation_status", "")).strip() == "passed"
        and int(manifest.get("issue_count") or 0) == 0
        and str(lens_report.get("status", "")).strip() == "not_applicable"
        and str(lens_report.get("reason", "")).strip() == "typed_structural_validation"
        and str(semantic_compiler.get("status", "")).strip() == "passed"
        and str(semantic_compiler.get("version", "")).strip()
        == "odylith.greenfield.authored-semantic-validation.v3"
        and str(semantic_compiler.get("semantic_owner", "")).strip()
        == "validated_model_authored_intent"
        and semantic_compiler.get("post_authoring_interpretation_calls") == 0
        and type(semantic_model_call_count) is int
        and 1 <= semantic_model_call_count <= MAX_GREENFIELD_SEMANTIC_CALLS
    )


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
    "proposal_time_issues",
    "write_committed",
    "write_transaction_custody_issues",
]
