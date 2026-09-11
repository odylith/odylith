"""Proposal ceilings change independently of model windows and commit-only time."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

from odylith.runtime.domain_intelligence import greenfield_create_transaction as transactions
from odylith.runtime.domain_intelligence import greenfield_model_profile_contract as profiles
from odylith.runtime.domain_intelligence import greenfield_preconfirm_engine as engine
from odylith.runtime.domain_intelligence import greenfield_proposals_cli as cli
from tests.unit.runtime.greenfield_authored_proposal_fixtures import approved_authored_quality_manifest_fixture


SCRIPTS_ROOT = Path(__file__).resolve().parents[3] / "scripts" / "release"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import greenfield_matrix_quality_scoring as scoring
from greenfield_matrix_quality_scoring import completion_issues, proposal_time_issues
from greenfield_matrix_types import GreenfieldArtifactCounts


TIERS = (("standard", 90.0), ("rescue", 120.0), ("deep", 150.0))
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
        budget_seconds=dict(TIERS)[tier], elapsed_seconds=elapsed,
    )
    receipt = manifest["model_authoring"]
    receipt["tier"] = tier
    for key, review in (("model_profile", False), ("candidate_review", True)):
        observed = receipt[key]["model_profile"] if review else receipt[key]
        observed.update(
            profile_id=profile.profile_id, authoring_tier=tier,
            model=profile.review_model if review else profile.model,
            reasoning_effort=profile.review_reasoning_effort if review else profile.reasoning_effort,
            effective_timeout_seconds=profile.review_timeout_seconds if review else profile.model_timeout_seconds,
        )
    return manifest


@pytest.mark.parametrize("tier,budget", TIERS)
def test_proposal_above_normal_target_but_below_ceiling_is_not_rejected(tier, budget):
    manifest = _manifest(tier, budget - 0.001)
    transactions.require_product_create_transaction_quality_approved(manifest)
    assert proposal_time_issues(manifest, proposal_seconds=budget - 0.001) == ()
    assert completion_issues(
        counts=GreenfieldArtifactCounts(), manifest=manifest,
        create_returncode=0, proposal_seconds=budget - 0.001, create_seconds=1.0,
    ) == ()


@pytest.mark.parametrize("tier,budget", TIERS)
@pytest.mark.parametrize("overrun", [0.0, 0.001])
def test_sealed_admission_and_release_scoring_reject_at_or_over_ceiling(tier, budget, overrun):
    manifest = _manifest(tier, budget + overrun)
    with pytest.raises(ValueError, match="quality manifest is not approved"):
        transactions.require_product_create_transaction_quality_approved(manifest)
    assert proposal_time_issues(manifest, proposal_seconds=budget + overrun)


@pytest.mark.parametrize("tier,budget", TIERS)
@pytest.mark.parametrize("overrun", [0.0, 0.001])
def test_expired_proposal_budget_stops_before_prewrite(monkeypatch, tier, budget, overrun):
    monkeypatch.setattr(engine, "sealed_authored_projection", lambda _: True)
    with pytest.raises(engine.GreenfieldPreconfirmEngineError) as exc:
        engine.run_greenfield_preconfirm_engine(
            proposal={}, release_selector="", repair_tier=tier,
            elapsed_before_start_seconds=budget + overrun, clock=lambda: 0.0,
            build_prewrite=lambda *_: pytest.fail("expired ceiling reached prewrite"),
        )
    assert exc.value.manifest["budget_seconds"] == budget
    assert exc.value.manifest["stop_reason"] == "time_budget_exhausted"


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


def test_scoring_does_not_coerce_matching_budget_string():
    manifest = approved_authored_quality_manifest_fixture()
    assert proposal_time_issues(manifest, proposal_seconds=1.0) == ()
    manifest["budget_seconds"] = str(manifest["budget_seconds"])
    assert proposal_time_issues(manifest, proposal_seconds=1.0)


@pytest.mark.parametrize("budget", [None, True, "90", 60, 120, float("nan"), float("inf"), 10 ** 1000])
def test_declared_budget_requires_exact_numeric_tier_binding(budget):
    manifest = _manifest("standard")
    manifest["budget_seconds"] = budget
    with pytest.raises(ValueError, match="quality manifest is not approved"):
        transactions.require_product_create_transaction_quality_approved(manifest)
    assert proposal_time_issues(manifest, proposal_seconds=1.0)


@pytest.mark.parametrize("tier,budget,profile_id", HISTORICAL_V12_PROFILES)
def test_old_v12_receipts_are_not_upgraded_or_mutated(tier, budget, profile_id):
    manifest = _manifest(tier)
    manifest["budget_seconds"] = budget
    receipt = manifest["model_authoring"]
    for observed in (receipt["model_profile"], receipt["candidate_review"]["model_profile"]):
        observed["profile_id"] = profile_id
    original = deepcopy(manifest)
    with pytest.raises(ValueError, match="quality manifest is not approved"):
        transactions.require_product_create_transaction_quality_approved(manifest)
    assert proposal_time_issues(manifest, proposal_seconds=1.0)
    assert manifest == original


@pytest.mark.parametrize("mutation", ["tier", "profile", "model_budget", "review_budget"])
def test_larger_outer_budget_does_not_relax_role_binding_or_model_caps(mutation):
    manifest = _manifest("standard", 80.0)
    receipt = manifest["model_authoring"]
    if mutation == "tier":
        manifest["repair_tier"] = "rescue"
    elif mutation == "profile":
        receipt["model_profile"]["profile_id"] = profiles.RESCUE_PROFILE_ID
    elif mutation == "model_budget":
        receipt["elapsed_seconds"] = 55.001
    else:
        receipt["candidate_review"]["model_profile"]["effective_timeout_seconds"] = 20.001
    with pytest.raises(ValueError, match="quality manifest is not approved"):
        transactions.require_product_create_transaction_quality_approved(manifest)


@pytest.mark.parametrize("command", ["propose", "apply", "compile-transaction"])
def test_help_distinguishes_proposal_ceilings_from_advisory_target(capsys, command):
    with pytest.raises(SystemExit) as exc:
        cli._parse_args([command, "--help"])
    assert exc.value.code == 0
    text = " ".join(capsys.readouterr().out.split())
    assert "under-90s" in text and "under-120s" in text and "under-150s" in text
    assert "60s" in text and "advisory" in text
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


@pytest.mark.parametrize("phase,ceiling", [("proposal", 90.0), ("commit-only create", 60.0)])
@pytest.mark.parametrize("overrun", [0.0, 0.001])
def test_real_quality_verdict_rejects_exact_or_exceeded_ceiling(monkeypatch, phase, ceiling, overrun):
    times = {"proposal_seconds" if phase == "proposal" else "create_seconds": ceiling + overrun}
    verdict = _quality_verdict(monkeypatch, **times)
    assert not verdict.passed, verdict.to_dict()
    assert len(verdict.issues) == 1 and verdict.issues[0].startswith(f"{phase} exceeded")
    assert verdict.scores["latency"] == 0
