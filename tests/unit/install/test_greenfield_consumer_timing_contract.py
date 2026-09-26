"""Advisory targets remain separate from operational and commit-only timeouts."""

from __future__ import annotations

import sys
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest

from odylith.runtime.domain_intelligence import (
    greenfield_create_transaction as transactions,
)
from odylith.runtime.domain_intelligence import (
    greenfield_model_profile_contract as profiles,
)
from odylith.runtime.domain_intelligence import greenfield_preconfirm_engine as engine
from odylith.runtime.domain_intelligence import greenfield_proposals_cli as cli
from tests.unit.runtime.greenfield_authored_proposal_fixtures import (
    approved_authored_quality_manifest_fixture,
)

SCRIPTS_ROOT = Path(__file__).resolve().parents[3] / "scripts" / "release"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import greenfield_matrix_quality_scoring as scoring
from greenfield_matrix_quality_scoring import completion_issues, proposal_time_issues
from greenfield_matrix_types import GreenfieldArtifactCounts

TIERS = (("standard", 90.0),)
HISTORICAL_V12_PROFILES = (
    ("standard", 60.0, "greenfield-standard-terra-low-complete-author-review-v12"),
    ("rescue", 90.0, "greenfield-rescue-terra-medium-complete-author-review-v12"),
    ("deep", 120.0, "greenfield-deep-sol-high-complete-author-review-v12"),
)
INVALID_DURATIONS = [None, True, False, "1", "90", -1, float("nan"), float("inf"), 10 ** 1000]


def _manifest(tier: str, elapsed: object = 1.0) -> dict:
    profile = profiles.get_greenfield_model_profile(profiles.model_profile_id_for_repair_tier(tier))
    manifest = approved_authored_quality_manifest_fixture(
        requested_repair_tier=tier, repair_tier=tier,
        target_seconds=dict(TIERS)[tier], operational_timeout_seconds=180.0,
        elapsed_seconds=elapsed,
    )
    receipt = manifest["model_authoring"]
    receipt["tier"] = tier
    elapsed_before = 0.0
    for key, model, effort in (
        ("participant_selection", profile.participant_model, profile.participant_reasoning_effort),
        ("remaining_candidate_authoring", profile.model, profile.reasoning_effort),
        ("candidate_review", profile.review_model, profile.review_reasoning_effort),
    ):
        role = receipt[key]
        observed = role["model_profile"]
        observed.update(
            profile_id=profile.profile_id, authoring_tier=tier,
            model=model, reasoning_effort=effort,
            effective_timeout_seconds=profile.model_timeout_seconds - elapsed_before,
        )
        elapsed_before += role["elapsed_seconds"]
    receipt["effective_model_window_seconds"] = profile.model_timeout_seconds
    return manifest


@pytest.mark.parametrize("tier,target", TIERS)
@pytest.mark.parametrize("offset", [-0.001, 0.0, 0.001])
def test_performance_target_boundary_is_advisory(tier, target, offset):
    elapsed = target + offset
    manifest = _manifest(tier, elapsed)
    transactions.require_product_create_transaction_quality_approved(manifest)
    assert proposal_time_issues(manifest, proposal_seconds=elapsed) == ()
    assert completion_issues(
        counts=GreenfieldArtifactCounts(), manifest=manifest,
        create_returncode=0, proposal_seconds=elapsed, create_seconds=1.0,
    ) == ()


@pytest.mark.parametrize("tier,target", TIERS)
@pytest.mark.parametrize("overrun", [0.0, 0.001])
def test_sealed_admission_and_release_scoring_reject_at_operational_timeout(tier, target, overrun):
    elapsed = 180.0 + overrun
    manifest = _manifest(tier, elapsed)
    with pytest.raises(ValueError, match="quality manifest is not approved"):
        transactions.require_product_create_transaction_quality_approved(manifest)
    assert proposal_time_issues(manifest, proposal_seconds=elapsed)


@pytest.mark.parametrize("tier,target", TIERS)
@pytest.mark.parametrize("overrun", [0.0, 0.001])
def test_expired_operational_timeout_stops_before_prewrite(monkeypatch, tier, target, overrun):
    monkeypatch.setattr(engine, "sealed_authored_projection", lambda _: True)
    with pytest.raises(engine.GreenfieldPreconfirmEngineError) as exc:
        engine.run_greenfield_preconfirm_engine(
            proposal={}, release_selector="", repair_tier=tier,
            elapsed_before_start_seconds=180.0 + overrun, clock=lambda: 0.0,
            build_prewrite=lambda *_: pytest.fail("expired ceiling reached prewrite"),
        )
    assert exc.value.manifest["target_seconds"] == target
    assert exc.value.manifest["operational_timeout_seconds"] == 180.0
    assert exc.value.manifest["stop_reason"] == "operational_timeout_exhausted"


@pytest.mark.parametrize("elapsed", INVALID_DURATIONS)
def test_sealed_quality_rejects_invalid_duration_with_matching_current_budget(elapsed):
    manifest = approved_authored_quality_manifest_fixture()
    transactions.require_product_create_transaction_quality_approved(manifest)
    manifest["elapsed_seconds"] = elapsed
    with pytest.raises(ValueError, match="quality manifest is not approved"):
        transactions.require_product_create_transaction_quality_approved(manifest)


@pytest.mark.parametrize("elapsed", [*INVALID_DURATIONS, 0])
def test_scoring_rejects_invalid_duration_with_matching_current_budget(elapsed):
    manifest = approved_authored_quality_manifest_fixture()
    assert proposal_time_issues(manifest, proposal_seconds=1.0) == ()
    assert proposal_time_issues(manifest, proposal_seconds=elapsed)


def test_scoring_does_not_coerce_matching_target_string():
    manifest = approved_authored_quality_manifest_fixture()
    assert proposal_time_issues(manifest, proposal_seconds=1.0) == ()
    manifest["target_seconds"] = str(manifest["target_seconds"])
    assert proposal_time_issues(manifest, proposal_seconds=1.0)


@pytest.mark.parametrize("target", [None, True, "90", 60, 120, float("nan"), float("inf"), 10 ** 1000])
def test_declared_target_requires_exact_numeric_tier_binding(target):
    manifest = _manifest("standard")
    manifest["target_seconds"] = target
    with pytest.raises(ValueError, match="quality manifest is not approved"):
        transactions.require_product_create_transaction_quality_approved(manifest)
    assert proposal_time_issues(manifest, proposal_seconds=1.0)


@pytest.mark.parametrize("tier,budget,profile_id", HISTORICAL_V12_PROFILES)
def test_old_v12_receipts_are_not_upgraded_or_mutated(tier, budget, profile_id):
    manifest = _manifest("standard")
    manifest["requested_repair_tier"] = tier
    manifest["repair_tier"] = tier
    manifest["target_seconds"] = budget
    receipt = manifest["model_authoring"]
    receipt["tier"] = tier
    for role in ("participant_selection", "remaining_candidate_authoring", "candidate_review"):
        receipt[role]["model_profile"]["profile_id"] = profile_id
    original = deepcopy(manifest)
    with pytest.raises(ValueError, match="quality manifest is not approved"):
        transactions.require_product_create_transaction_quality_approved(manifest)
    assert proposal_time_issues(manifest, proposal_seconds=1.0)
    assert manifest == original


@pytest.mark.parametrize(
    "mutation", ["tier", "participant_profile", "remainder_budget", "review_budget"]
)
def test_operational_timeout_does_not_relax_role_binding_or_model_caps(mutation):
    manifest = _manifest("standard", 80.0)
    receipt = manifest["model_authoring"]
    if mutation == "tier":
        manifest["repair_tier"] = "rescue"
    elif mutation == "participant_profile":
        receipt["participant_selection"]["model_profile"]["profile_id"] = profiles.RESCUE_PROFILE_ID
    elif mutation == "remainder_budget":
        receipt["remaining_candidate_authoring"]["model_profile"]["effective_timeout_seconds"] = 165.001
    else:
        receipt["candidate_review"]["model_profile"]["effective_timeout_seconds"] = 165.001
    with pytest.raises(ValueError, match="quality manifest is not approved"):
        transactions.require_product_create_transaction_quality_approved(manifest)


@pytest.mark.parametrize("command", ["propose", "apply", "compile-transaction"])
def test_help_distinguishes_performance_targets_from_operational_timeout(capsys, command):
    with pytest.raises(SystemExit) as exc:
        cli._parse_args([command, "--help"])
    assert exc.value.code == 0
    text = " ".join(capsys.readouterr().out.split())
    assert "90s" in text and "120s" in text and "150s" in text
    assert "Operational safety timeout: 180s" in text
    assert "Normal-case target: 90s" in text and "advisory" in text
    assert "under-60s profile" not in text


def test_commit_only_keeps_its_separate_sixty_second_cutoff():
    issues = completion_issues(
        counts=GreenfieldArtifactCounts(), manifest=_manifest("standard"),
        create_returncode=0, proposal_seconds=80.0, create_seconds=60.0,
    )
    assert issues == ("commit-only create exceeded 60s: 60.000s",)


@pytest.mark.parametrize("elapsed", [*INVALID_DURATIONS, 0])
def test_completion_rejects_invalid_commit_duration(elapsed):
    assert completion_issues(
        counts=GreenfieldArtifactCounts(), manifest=_manifest("standard"),
        create_returncode=0, proposal_seconds=80.0, create_seconds=elapsed,
    ) == ("commit-only create proof is missing a positive measured elapsed time",)


def _quality_verdict(monkeypatch, *, proposal_seconds=80.0, create_seconds=1.0):
    """Keep real custody/scoring; only the package audit returns synthetic empty findings."""

    monkeypatch.setattr(scoring, "package_evidence_findings", lambda _package: ())
    manifest = _manifest("standard")
    manifest["quality_lenses"] = {
        "status": "not_applicable", "lenses": {}, "reason": "typed_structural_validation",
    }
    summary = {
        "transaction_hash": "a" * 64,
        "product_facts_sha256": manifest["model_authoring"]["candidate_review"]["product_facts_sha256"],
        "repository_write_set_hash": "b" * 64,
    }
    manifest["product_create_transaction"] = summary
    manifest["write_transaction"].update(
        status="committed", commit_only=True,
        product_create_transaction_hash=summary["transaction_hash"],
        product_facts_sha256=summary["product_facts_sha256"],
        repository_write_set_hash=summary["repository_write_set_hash"],
    )
    gate = {"visible_actors": [
        {"stable_role": role, "visible_actor": role, "actor_source": "synthetic timing control",
         "responsibility": "Check the synthetic package"}
        for role in scoring.TRIBUNAL_STABLE_ROLES
    ]}
    return scoring.build_quality_verdict(
        create_payload={"commit_manifest": manifest, "product_create_transaction": summary,
                        "validation_gate": gate},
        package=SimpleNamespace(proposal={"projection_origin": scoring.AUTHORED_PROJECTION_ORIGIN},
                                accepted_project_preview={"validation_gate": gate}),
        counts=GreenfieldArtifactCounts(radar_workstreams=1, trace_nodes=1, trace_workstreams=1),
        create_returncode=0, proposal_seconds=proposal_seconds, create_seconds=create_seconds,
    )


@pytest.mark.parametrize("commit_seconds", [1, 1.0, 59.999])
def test_real_quality_verdict_accepts_positive_commit_below_sixty(monkeypatch, commit_seconds):
    verdict = _quality_verdict(monkeypatch, create_seconds=commit_seconds)
    assert verdict.passed, verdict.to_dict()
    assert verdict.issues == ()
    assert verdict.scores["latency"] == 10


@pytest.mark.parametrize("phase", ["proposal", "commit-only create"])
@pytest.mark.parametrize("elapsed", [*INVALID_DURATIONS, 0])
def test_real_quality_verdict_reports_invalid_observation_without_raising(monkeypatch, phase, elapsed):
    times = {"proposal_seconds" if phase == "proposal" else "create_seconds": elapsed}
    verdict = _quality_verdict(monkeypatch, **times)
    assert not verdict.passed, verdict.to_dict()
    assert verdict.issues == (f"{phase} proof is missing a positive measured elapsed time",)
    assert verdict.scores["latency"] == 0


@pytest.mark.parametrize("phase,ceiling", [("proposal", 180.0), ("commit-only create", 60.0)])
@pytest.mark.parametrize("overrun", [0.0, 0.001])
def test_real_quality_verdict_rejects_exact_or_exceeded_ceiling(monkeypatch, phase, ceiling, overrun):
    times = {"proposal_seconds" if phase == "proposal" else "create_seconds": ceiling + overrun}
    verdict = _quality_verdict(monkeypatch, **times)
    assert not verdict.passed, verdict.to_dict()
    assert len(verdict.issues) == 1 and verdict.issues[0].startswith(f"{phase} exceeded")
    assert verdict.scores["latency"] == 0
