from __future__ import annotations

import json
from pathlib import Path
import re

import pytest

from odylith.runtime.artifact_quality.greenfield_package_quality import greenfield_rendered_package_quality_issues
from odylith.runtime.domain_intelligence import greenfield_apply_prewrite
from odylith.runtime.domain_intelligence import greenfield_apply_write
from odylith.runtime.domain_intelligence import greenfield_proposals
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent import parse_confirmed_intent_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_project_brief import _first_path_readiness_summary
from odylith.runtime.domain_intelligence.greenfield_first_path_clauses import first_path_capability_phrase
from odylith.runtime.domain_intelligence.greenfield_preconfirm_completion import GreenfieldCompletionPackage
from odylith.runtime.domain_intelligence.greenfield_preconfirm_completion import build_greenfield_package_report
from odylith.runtime.domain_intelligence.greenfield_proposals import build_greenfield_proposal
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import generated_semantic_slop_issues
from odylith.runtime.domain_intelligence.proposal_tribunal import run_greenfield_tribunal
from odylith.runtime.project_intelligence.intent_confirmation import build_product_intent_confirmation
from odylith.runtime.project_intelligence.intent_confirmation import format_product_intent_confirmation_text
from tests.unit.runtime.greenfield_proposal_fixtures import confirmed_intent_with_authority
from tests.unit.runtime.greenfield_proposal_fixtures import confirmed_mapping_with_authority
from tests.unit.runtime.greenfield_proposal_fixtures import stub_preconfirm_surface_refresh


_ARBORCELL_PROMPT = (
    "Draft a product-first greenfield proposal for generating electricity from a tree using natural chlorophyl "
    "process. Think hard and make this innovative :)"
)

_ARBORCELL_CONFIRMED_INTENT = """# Product Intent Confirmation: ArborCell

## Product story

ArborCell is a living-tree energy interface for research labs that turns a tree's normal photosynthesis cycle into trace usable electricity without harming the tree. The product does not plug into chlorophyll directly. Instead, sunlight drives chlorophyll in the leaves, the tree sends some carbon-rich compounds into the root zone, and a bioelectrochemical root collar harvests electrons released by soil microbes as they metabolize those compounds.

The first product targets controlled lab prototypes using both a young sapling and a bonsai-scale tree. Its first useful workload is one sensor reading per hour, powered by stored trace energy from the living root system.

## State object

A Tree Energy Session tracks prototype type, tree species, pot or soil context, light exposure, soil moisture, temperature, electrode geometry, microbial maturity, voltage, current, stored capacitor energy, hourly sensor duty cycle, tree-health signals, and excluded claims. It also records that this release is a research-lab proof and not a claim of household, vehicle, or grid-scale power.

## First complete path

A research lab installs a non-invasive root-zone energy collar on a living sapling and a bonsai-scale tree. Each collar uses a porous anode in the oxygen-poor root zone, an oxygen-facing cathode, a low-leakage energy harvester, and a small storage capacitor. The system waits for the microbial biofilm to mature, measures power across light and dark cycles, and proves it can deliver one sensor reading per hour while showing that both trees remain healthy.

## Human actors

- Research founder: needs a credible first prototype and falsifiable proof boundary
- Lab researcher: configures experiments, compares sapling and bonsai-scale runs, and reviews measurement quality
- Field or lab technician: installs collars, checks soil, swaps sensors, and avoids root damage
- Reviewer or grant evaluator: needs clear evidence, limits, and repeatable measurements

## External systems

- Living sapling and bonsai-scale tree
- Rhizosphere microbiome around each tree's roots
- Sunlight or controlled grow lights
- Water, soil chemistry, oxygen gradients, and seasonal or chamber conditions
- Environmental sensor package for one reading per hour
- Lab measurement tools for current, voltage, impedance, stored energy, and plant health

## Internal product systems

- Root-halo electrode module: soft, modular, non-invasive anode and cathode layout for sapling and bonsai-scale containers
- Biofilm maturity tracker: separates startup noise from stable energy production
- Chlorophyll-to-root energy model: links light, photosynthesis proxy, root exudate availability, and measured output
- Energy budget controller: stores trace energy and schedules one sensor reading per hour only when enough charge exists
- Comparative prototype dashboard: shows sapling and bonsai-scale performance side by side
- Tree health guard: blocks successful-power claims if either tree is stressed
- Proof ledger: keeps raw measurements, calibration notes, units, tolerances, baselines, and failed runs

## Critical assumptions

- The first viable product is a research-lab self-powered sensing platform, not a general electricity generator
- The first prototype compares one sapling and one bonsai-scale tree under controlled conditions
- The most honest mechanism is photosynthesis-fed root microbial electricity, not direct chlorophyll extraction from the tree
- One sensor reading per hour is the first useful energy workload
- Non-invasive design matters more than peak output
- Release 0.0.1 proves repeatability in controlled lab conditions before expanding to species libraries, outdoor deployments, or customer pilots

## Ambiguities

- Which sapling species and bonsai-scale tree species should be used first
- Whether grow lights, natural daylight, or both define the first light regime
- How much biological intervention is allowed: native microbes only, inoculated electroactive microbes, or engineered biology excluded
- Required tree-health evidence: visual inspection, chlorophyll fluorescence, growth rate, soil respiration, or simpler proxies
- Whether the hourly sensor reading should measure tree health, soil moisture, temperature, voltage/current, or a combined packet

## Proof boundary

Release 0.0.1 succeeds when ArborCell repeatedly harvests measurable current from both a living sapling root system and a bonsai-scale tree root system, stores it, and powers one defined sensor reading per hour under documented research-lab conditions. The proof must include units, baselines without the tree, dark-cycle behavior, soil-only controls, uncertainty, and tree-health checks. It must not claim scalable household, vehicle, or grid power unless later evidence supports that.

## Next step

Confirmed: expand this accepted Product Intent Confirmation into the governed proposal contract for release 0.0.1, writing records only if validation and Tribunal gates pass.
"""


def _intent_from_prompt(prompt: str) -> dict[str, object]:
    text = f"""
Product Intent Confirmation needed

Original user intent
{prompt}
"""
    return confirmed_intent_with_authority(text, prompt=prompt, source_format="operator_prompt")


def _visible_confirmation_intent(prompt: str) -> dict[str, object]:
    confirmation = build_product_intent_confirmation(
        prompt=prompt,
        title="greenfield simulation",
        repo_name="greenfield-simulation",
        observed_source={},
    )
    return confirmed_intent_with_authority(
        format_product_intent_confirmation_text(confirmation),
        prompt=prompt,
        source_format="operator_prompt",
    )


@pytest.fixture(autouse=True)
def _preconfirm_surface_fixture(monkeypatch: pytest.MonkeyPatch) -> None:
    stub_preconfirm_surface_refresh(monkeypatch)


def _proposal_and_prewrite(tmp_path: Path, prompt: str):
    tmp_path.mkdir(parents=True, exist_ok=True)
    proposal = build_greenfield_proposal(
        repo_root=tmp_path,
        prompt=prompt,
        release_selector="0.0.1",
        confirmed_intent=_visible_confirmation_intent(prompt),
        require_completion_ready=False,
    )
    tribunal = run_greenfield_tribunal(proposal, release_selector="0.0.1")
    prewrite = greenfield_apply_prewrite.build_prewrite_completion_package(
        root=tmp_path,
        proposal=proposal,
        release_selector="0.0.1",
        backlog_args=greenfield_proposals._backlog_apply_args(proposal, release_selector="0.0.1"),
        validation_gate=tribunal.to_dict(),
        release_assignment_note=greenfield_apply_write.release_assignment_note(selector="0.0.1"),
    )
    return proposal, prewrite


def test_arborcell_setup_details_do_not_become_confirmed_action_truth() -> None:
    intent = parse_confirmed_intent_text(_ARBORCELL_CONFIRMED_INTENT, prompt=_ARBORCELL_PROMPT)
    first_path = str(intent["first_path"])
    capability = first_path_capability_phrase(first_path, max_fragments=8, limit=360)
    readiness = _first_path_readiness_summary(
        first_path,
        fallback="",
        proof_boundary=str(intent["proof_boundary"]),
        visible_result="",
        limit=520,
    )

    assert "Lab measurement tools for current, voltage, impedance, stored energy, and plant health" in intent["external_systems"]
    assert all("current Lab measurement tools for" not in value for value in intent["external_systems"])
    assert "measure power across light and dark cycles" in capability
    assert "one sensor reading per hour" in capability
    assert "measure power across light and dark cycles" in readiness
    assert "one sensor reading per hour" in readiness
    assert "Each collar uses" not in capability
    assert "Each collar uses" not in readiness
    assert "review the oxygen-poor root zone" not in capability
    assert "review the oxygen-poor root zone" not in readiness


def test_wedding_context_phrase_does_not_become_the_first_path_actor(tmp_path: Path) -> None:
    prompt = (
        "Make a wedding weekend guide for guests traveling to a small town with limited taxis, a rehearsal dinner, "
        "and an accessibility request. A guest RSVPs with a dietary choice, reserves a shuttle seat, notes a hearing "
        "loop need, and saves the ceremony location. The couple sees headcounts, the shuttle coordinator assigns "
        "departure groups, and the venue contact confirms that the hearing loop has been tested before guests arrive."
    )

    proposal, prewrite = _proposal_and_prewrite(tmp_path, prompt)
    rendered = json.dumps(
        {
            "intent": proposal["intent"],
            "backlog": proposal["backlog"],
            "package": prewrite.package.backlog_result,
        },
        sort_keys=True,
        default=str,
    )

    assert str(proposal["intent"]["first_path"]).startswith("A guest RSVPs")
    assert proposal["semantic_model"]["first_path_contract"]["actor"] == "Guest"
    for term in ("limited taxis", "rehearsal dinner", "accessibility request"):
        assert term in proposal["intent"]["evidence_requirements"]
        assert term in rendered.casefold()
    assert "Guests Traveling to a" not in rendered
    assert "guests traveling to a small town" not in rendered.casefold()
    assert ", handles missing or invalid input" not in str(proposal["intent"]["proof_boundary"])
    assert "It explains missing or invalid input" in str(proposal["intent"]["proof_boundary"])
    assert greenfield_rendered_package_quality_issues(prewrite.package) == ()


def test_on_call_role_context_is_preserved_in_the_compiled_package(tmp_path: Path) -> None:
    prompt = (
        "Create a focused incident-operations workspace for on-call engineers handing an active service incident to "
        "the next shift. Each handoff records incident timeline, current customer impact, mitigation owner, and "
        "unresolved decision. The first release boundary is shift handoff for a single incident with an acknowledgement "
        "trail; paging, automated remediation, and status-page publication remain outside the initial product."
    )

    proposal, prewrite = _proposal_and_prewrite(tmp_path, prompt)
    rendered = "\n".join(
        [
            *prewrite.package.backlog_result["idea_files"].values(),
            *prewrite.package.rendered_component_specs.values(),
            *prewrite.package.rendered_atlas_sources.values(),
            prewrite.package.project_brief_record_text,
        ]
    ).casefold()

    assert proposal["intent"]["human_actors"][0].startswith("On-call Engineers:")
    assert str(proposal["intent"]["first_path"]).casefold().startswith("on-call engineers can record incident timeline")
    for term in ("on-call engineers", "incident timeline", "customer impact", "acknowledgement trail"):
        assert term in rendered
    assert greenfield_rendered_package_quality_issues(prewrite.package) == ()


@pytest.mark.parametrize(
    ("prompt", "required_terms"),
    (
        (
            "A mining company needs to allocate one critical haul-truck hydraulic pump between two sites after both "
            "report failures. The maintenance planner verifies the part number, the reliability engineer compares "
            "failure analysis, and the site superintendent approves the transport priority. Keep the serialized pump, "
            "equipment downtime, warranty status, and transfer authorization distinct.",
            ("hydraulic pump", "part number", "failure analysis", "transfer authorization"),
        ),
        (
            "A proteomics team is transferring a DIA mass spectrometry method between two laboratories. The product "
            "must capture peptide library version, retention-time alignment, iRT standards, instrument tuning, false "
            "discovery rate, and replicate precision. Method owners need to know whether differences in collision energy "
            "or column lot prevent a comparable method transfer.",
            ("DIA", "iRT standards", "false discovery rate", "collision energy"),
        ),
    ),
)
def test_direct_product_need_recovery_preserves_domain_contract(
    tmp_path: Path,
    prompt: str,
    required_terms: tuple[str, ...],
) -> None:
    proposal, prewrite = _proposal_and_prewrite(tmp_path, prompt)
    rendered = "\n".join(
        [
            *prewrite.package.backlog_result["idea_files"].values(),
            *prewrite.package.rendered_component_specs.values(),
            *prewrite.package.rendered_atlas_sources.values(),
            prewrite.package.project_brief_record_text,
        ]
    ).casefold()

    assert proposal["intent"]["title"] != "Recovered Product Workspace"
    assert "representative user" not in str(proposal["intent"]["first_path"]).casefold()
    for term in required_terms:
        assert term.casefold() in rendered
    assert greenfield_rendered_package_quality_issues(prewrite.package) == ()


def test_generic_setup_sentences_do_not_project_as_review_actions() -> None:
    first_path = (
        "A records team opens a reconciliation run. "
        "Each gateway uses a buffer, retry ledger, and checksum cache. "
        "The service validates records, publishes a signed result, and proves it delivers one export per hour."
    )
    capability = first_path_capability_phrase(first_path, max_fragments=8, limit=320)
    readiness = _first_path_readiness_summary(
        first_path,
        fallback="",
        proof_boundary="The first proof succeeds when one export is delivered with replay evidence.",
        visible_result="",
        limit=420,
    )

    assert capability == "open a reconciliation run"
    assert "validate records" in readiness
    assert "signed result" in readiness
    assert "one export per hour" in readiness
    assert "Each gateway uses" not in capability
    assert "review a buffer" not in capability
    assert "Each gateway uses" not in readiness
    assert "review a buffer" not in readiness


def test_arborcell_preconfirm_package_does_not_repeat_setup_or_malformed_copy(tmp_path: Path) -> None:
    intent = parse_confirmed_intent_text(_ARBORCELL_CONFIRMED_INTENT, prompt=_ARBORCELL_PROMPT)
    proposal = build_greenfield_proposal(
        repo_root=tmp_path,
        prompt=_ARBORCELL_PROMPT,
        release_selector="0.0.1",
        confirmed_intent=confirmed_mapping_with_authority(intent),
    )
    tribunal = run_greenfield_tribunal(proposal, release_selector="0.0.1")
    prewrite = greenfield_apply_prewrite.build_prewrite_completion_package(
        root=tmp_path,
        proposal=proposal,
        release_selector="0.0.1",
        backlog_args=greenfield_proposals._backlog_apply_args(proposal, release_selector="0.0.1"),
        validation_gate=tribunal.to_dict(),
        release_assignment_note=greenfield_apply_write.release_assignment_note(selector="0.0.1"),
    )
    report = build_greenfield_package_report(prewrite.package)
    public_payload = json.dumps(
        {
            "backlog": prewrite.package.backlog_result.get("idea_files"),
            "registry": prewrite.package.rendered_component_specs,
            "atlas": prewrite.package.rendered_atlas_sources,
            "brief": prewrite.package.project_brief_preview,
            "next_steps": prewrite.package.next_steps_preview,
        },
        sort_keys=True,
        default=str,
    )

    assert tribunal.passed, tribunal.issues
    assert report.issues == ()
    assert greenfield_rendered_package_quality_issues(prewrite.package) == ()
    assert "Each collar uses a porous anode in the oxygen-poor root zone, and an oxygen-facing cathode" not in public_payload
    assert "current Lab measurement tools for" not in public_payload
    assert "proven it" not in public_payload
    assert "review the oxygen-poor root zone" not in public_payload


def test_confirmed_actor_labels_drop_dangling_action_fragments(tmp_path: Path) -> None:
    prompt = (
        "Create a greenfield product for a decision coach that lets a user describe a difficult choice, "
        "compare options against stated values, record tradeoffs, and choose one next action with review evidence."
    )

    proposal = build_greenfield_proposal(
        repo_root=tmp_path,
        prompt=prompt,
        release_selector="0.0.1",
        confirmed_intent=_intent_from_prompt(prompt),
    )
    encoded = json.dumps(proposal, sort_keys=True)
    actor_text = json.dumps(
        [row.get("customer") for row in proposal.get("backlog", []) if isinstance(row, dict)],
        sort_keys=True,
    )

    assert generated_semantic_slop_issues(proposal, root="proposal") == []
    assert "Choose One Next Action with" not in encoded
    assert not re.search(r"\b(?:and|for|from|the|to|when|while|with)\.?(?:\"|$)", actor_text)


def test_repaired_interfaces_do_not_repeat_generic_next_step_copy(tmp_path: Path) -> None:
    prompt = (
        "Create a greenfield product for public agency response teams to collect resident reports, triage urgency, "
        "coordinate owner follow-up, and publish a clear status explanation with proof of action."
    )

    proposal = build_greenfield_proposal(
        repo_root=tmp_path,
        prompt=prompt,
        release_selector="0.0.1",
        confirmed_intent=_intent_from_prompt(prompt),
        require_completion_ready=False,
    )
    interfaces = [
        item
        for row in proposal.get("backlog", [])
        if isinstance(row, dict)
        for item in row.get("interfaces", [])
        if isinstance(item, str)
    ]
    package = GreenfieldCompletionPackage(
        proposal=proposal,
        accepted_project_preview={"proposal": proposal},
    )
    handoffs = [item for item in interfaces if " hands off " in item]

    assert "The next product step receives" not in json.dumps(proposal, sort_keys=True)
    assert handoffs
    assert len(handoffs) == len(set(handoffs))
    assert not any("repeats a noncanonical sentence" in issue for issue in greenfield_rendered_package_quality_issues(package))


def test_distributed_agent_confirmation_preserves_actor_and_component_boundaries(tmp_path: Path) -> None:
    prompt = (
        "Create a greenfield product for platform operators who submit distributed agent jobs, "
        "track assigned worker progress, collect execution evidence, surface blockers, and publish "
        "a final run record with reviewer approval."
    )

    proposal, prewrite = _proposal_and_prewrite(tmp_path, prompt)
    encoded = json.dumps(proposal, sort_keys=True)
    component_labels = [
        str(row.get("label", "")).strip()
        for row in proposal.get("components", [])
        if isinstance(row, dict) and str(row.get("label", "")).strip()
    ]
    report = build_greenfield_package_report(prewrite.package)

    assert "Publish a Final" not in encoded
    assert "can run record with reviewer approval" not in encoded.casefold()
    assert "reviewer run record with reviewer approval" not in encoded.casefold()
    assert any("Platform Operators" in row for row in proposal["intent"]["human_actors"])
    assert len(component_labels) >= 3
    assert len(component_labels) == len(set(component_labels))
    assert len(prewrite.package.rendered_component_specs or {}) == len(component_labels)
    assert report.issues == ()


def test_relative_actor_confirmation_does_not_promote_outcome_terms_to_people(tmp_path: Path) -> None:
    prompt = (
        "Create a greenfield product for community sports organizers who schedule FIFA-style neighborhood "
        "tournaments, register teams, assign referees, publish fixtures, record match results, and show "
        "standings with dispute review."
    )

    proposal, prewrite = _proposal_and_prewrite(tmp_path, prompt)
    public_payload = json.dumps(
        {
            "intent": proposal.get("intent"),
            "backlog": proposal.get("backlog"),
            "next_steps": prewrite.package.next_steps_preview,
        },
        sort_keys=True,
    )
    actors = [str(row) for row in proposal["intent"]["human_actors"]]
    actor_labels = [row.split(":", 1)[0] for row in actors]
    report = build_greenfield_package_report(prewrite.package)

    assert any(label == "Community Sports Organizers" for label in actor_labels)
    assert "Dispute" not in actor_labels
    assert "can who" not in public_payload.casefold()
    assert "to who" not in public_payload.casefold()
    assert report.issues == ()
    assert greenfield_rendered_package_quality_issues(prewrite.package) == ()


def test_sparse_model_lab_notebook_preconfirm_package_stays_clean(tmp_path: Path) -> None:
    prompt = "model lab notebook"

    proposal, prewrite = _proposal_and_prewrite(tmp_path, prompt)
    actor_labels = [str(row).split(":", 1)[0] for row in proposal["intent"]["human_actors"]]
    public_payload = json.dumps(
        {
            "intent": proposal.get("intent"),
            "project_brief": prewrite.package.project_brief_preview,
            "next_steps": prewrite.package.next_steps_preview,
        },
        sort_keys=True,
    )
    report = build_greenfield_package_report(prewrite.package)

    assert actor_labels == ["Representative User"]
    assert "Records" not in actor_labels
    assert "Sees" not in actor_labels
    assert "people and teams: Teams" not in public_payload
    assert "teams Teams" not in public_payload
    assert "Preserve this accepted first path:" in public_payload
    assert report.issues == ()
    assert greenfield_rendered_package_quality_issues(prewrite.package) == ()


def test_security_disclosure_council_object_list_projection_stays_canonical(tmp_path: Path) -> None:
    prompt = (
        "Create a greenfield proposal for a multi-party security disclosure council that coordinates "
        "external vulnerability reports, affected partner review, embargo decisions, evidence custody, "
        "legal signoff, and public advisory release readiness without personalized notification campaigns "
        "in the first release."
    )

    proposal, prewrite = _proposal_and_prewrite(tmp_path, prompt)
    report = build_greenfield_package_report(prewrite.package)
    rendered = json.dumps(
        {
            "proposal": proposal,
            "project_brief": prewrite.package.project_brief_preview,
            "next_steps": prewrite.package.next_steps_preview,
            "accepted_project": prewrite.package.accepted_project_preview,
        },
        sort_keys=True,
        default=str,
    )

    assert "affected partner review" in rendered.casefold()
    assert "embargo decisions" in rendered.casefold()
    assert "personalized notification campaigns" in rendered.casefold()
    assert "reports, affected." not in json.dumps(
        proposal["project_brief"]["coding_readiness_gates"],
        sort_keys=True,
    )
    assert report.issues == ()
    assert greenfield_rendered_package_quality_issues(prewrite.package) == ()


def test_health_followup_recovery_keeps_adjectival_result_terms_out_of_actors(tmp_path: Path) -> None:
    prompt = (
        "Create a greenfield product for digestive health patients who log meals, symptoms, medications, "
        "and bowel patterns, then prepare a clinician-ready follow-up summary with safety escalation notes."
    )

    intent = _visible_confirmation_intent(prompt)
    proposal, prewrite = _proposal_and_prewrite(tmp_path, prompt)
    actor_labels = [str(row).split(":", 1)[0] for row in proposal["intent"]["human_actors"]]
    system_rows = [str(row) for row in intent["internal_systems"]]

    assert intent["title"] == "Digestive Health Patients Workspace"
    assert actor_labels == ["Digestive Health Patients"]
    assert "Clinician Ready Follow Up Summary" not in actor_labels
    assert len(system_rows) >= 3
    assert not any("Recovered Product" in row or "— keeps Safety" in row for row in system_rows)
    rendered_package = json.dumps(
        {
            "backlog": prewrite.package.backlog_result.get("idea_files"),
            "next_steps": prewrite.package.next_steps_preview,
        },
        sort_keys=True,
    )
    assert "provide what the product needs, leaves enough context" not in rendered_package
    assert "provides what the product needs" not in rendered_package
    assert "the product keeps enough context for follow-up" not in rendered_package
    assert "the product preserves the saved context" in rendered_package
    assert build_greenfield_package_report(prewrite.package).issues == ()


def test_wearable_health_visible_result_quotes_survive_preconfirm_package(tmp_path: Path) -> None:
    prompt = (
        "captures exhaustive metrics from a wearable and shows insight about metabolic age, chronic illness, "
        "athletic capabilities, biological age, and related health signals"
    )
    confirmed_intent = parse_confirmed_intent_text(
        """
Metabolic Health Companion — Product Intent Confirmation

Product story
A health insight app connects to a wearable, gathers biometric, activity, sleep, recovery, and lifestyle signals, and turns them into understandable longitudinal insight. The product helps a person see how their body appears to be aging, recovering, training, and adapting over time, while clearly separating wellness insight from medical diagnosis.

State object
A personal health profile contains raw wearable readings, device provenance, user context, baselines, trends, derived estimates, confidence levels, consent settings, and safety flags.

First complete path
A user connects a wearable, completes basic health and goal context, grants consent for selected data streams, and sees an initial dashboard after enough data is available. The first useful experience should show baseline trends, recovery and exertion patterns, estimated metabolic and biological age indicators, athletic capability markers, and clear "what changed" insights without making diagnosis claims.

Human actors
- Wearable User — tracks personal health, longevity, recovery, or performance.
- Athlete or Highly Active User Optimizing Training Load and Capability — optimizes training load and capability.
- Person Managing Chronic Illness Risk — wants early signals and trend awareness.

External systems
- Wearable devices and health platforms such as Apple Health, Garmin, Oura, WHOOP, Fitbit, or similar sources.
- Lab, nutrition, medication, symptom, and training-log data sources.
- Clinical and scientific reference material used to explain metric meaning and limits.
- Identity, consent, notification, and secure storage providers.

Internal product systems
- Data Ingestion and Normalization Across Wearable Vendors and Metric Units — receives wearable data and preserves provenance.
- Personal Baseline and Trend Engine — computes stable baselines and trend changes.
- Derived Health Insight Engine — produces explainable metabolic, biological-age, recovery, and capability estimates.
- Explainability Layer Showing Inputs, Confidence, Missing Data, and Trend Drivers — explains why a result changed.
- Consent, Privacy, Retention, Audit, and Export System — manages consent, retention, sharing, export, and audit evidence.
- Safety Review Layer — prevents unsupported diagnosis, urgent-risk ambiguity, or overconfident recommendations.

Critical assumptions
- The app is a wellness and insight product first, not a standalone diagnostic medical device.
- Derived scores must show confidence, source data, and limitations.
- Users control which data is collected, retained, shared, and deleted.

Ambiguities
- Initial wearable platform priority.
- Whether lab tests, nutrition, medications, and symptoms are required in the first path.
- Regulatory posture if chronic illness insights become diagnostic, treatment-guiding, or clinician-facing.

Proof boundary
The first proof should demonstrate that the app can ingest real wearable data, preserve provenance and consent, compute stable personal baselines, show derived estimates with uncertainty, and produce clear trend explanations. It should not claim to diagnose chronic illness, determine biological age as fact, or prescribe treatment without a separate clinical validation and regulatory plan.
""",
        prompt=prompt,
    )
    proposal = build_greenfield_proposal(
        repo_root=tmp_path,
        prompt=prompt,
        release_selector="0.0.1",
        confirmed_intent=confirmed_mapping_with_authority(confirmed_intent),
    )
    tribunal = run_greenfield_tribunal(proposal, release_selector="0.0.1")
    prewrite = greenfield_apply_prewrite.build_prewrite_completion_package(
        root=tmp_path,
        proposal=proposal,
        release_selector="0.0.1",
        backlog_args=greenfield_proposals._backlog_apply_args(proposal, release_selector="0.0.1"),
        validation_gate=tribunal.to_dict(),
        release_assignment_note=greenfield_apply_write.release_assignment_note(selector="0.0.1"),
    )
    public_payload = json.dumps(
        {
            "proposal": proposal,
            "backlog": prewrite.package.backlog_result.get("idea_files"),
            "registry": prewrite.package.rendered_component_specs,
            "atlas": prewrite.package.rendered_atlas_sources,
            "brief": prewrite.package.project_brief_preview,
            "next_steps": prewrite.package.next_steps_preview,
        },
        sort_keys=True,
        default=str,
    )
    first_path = proposal["semantic_model"]["first_path_contract"]
    report = build_greenfield_package_report(prewrite.package)

    assert tribunal.passed, tribunal.issues
    assert first_path["visible_result"] == 'Clear "what changed" insights without making diagnosis claims'
    assert "baseline trends" not in first_path["visible_result"].casefold()
    assert "athletic capability markers" not in first_path["visible_result"].casefold()
    assert re.search(r"\bgrant(?:ing)? consent\b", first_path["capability"])
    assert "grants consent" not in first_path["capability"]
    assert 'clear "what.' not in public_payload
    assert "clear 'what<br" not in public_payload
    assert "clear 'what.\"" not in public_payload
    assert "Launches launches" not in public_payload
    assert "high Check" not in public_payload
    assert "assumptions={" not in public_payload
    assert "open_questions={" not in public_payload
    assert report.issues == ()
    assert greenfield_rendered_package_quality_issues(prewrite.package) == ()
    assert generated_semantic_slop_issues(proposal, root="proposal") == []


def test_autonomous_warehouse_state_review_terms_do_not_become_actors(tmp_path: Path) -> None:
    prompt = (
        "Draft a greenfield proposal for an autonomous warehouse safety state console. "
        "The product monitor robot near-miss reports, sensor confidence, aisle lockdown decisions, "
        "maintenance agent handoffs. Operator override records and release readiness must be reviewable "
        "before any autonomous movement authority expands."
    )

    proposal, prewrite = _proposal_and_prewrite(tmp_path, prompt)
    actor_labels = [str(row).split(":", 1)[0] for row in proposal["intent"]["human_actors"]]
    rendered = json.dumps(
        {
            "intent": proposal["intent"],
            "backlog": proposal["backlog"],
            "brief": prewrite.package.project_brief_preview,
            "next_steps": prewrite.package.next_steps_preview,
        },
        sort_keys=True,
        default=str,
    )

    assert actor_labels == ["Autonomous Warehouse Operator"]
    assert "Release Readiness" not in actor_labels
    assert "Operator Override Records" not in " ".join(actor_labels)
    assert "a autonomous" not in rendered.casefold()
    assert "can reports" not in rendered.casefold()
    assert "operator override records and release readiness" in rendered.casefold()
    assert generated_semantic_slop_issues(proposal, root="proposal") == []
    assert build_greenfield_package_report(prewrite.package).issues == ()


def test_federated_agent_release_clause_stays_modal_safe(tmp_path: Path) -> None:
    prompt = (
        "Draft a greenfield proposal for a federated agent incident command ledger. "
        "Human operators assign investigation cases, review model-generated hypotheses, record state changes, "
        "route cross-team claims, maintain audit evidence, and decide what can be released to partners "
        "after legal approval."
    )

    proposal, prewrite = _proposal_and_prewrite(tmp_path, prompt)
    rendered = json.dumps(
        {
            "intent": proposal["intent"],
            "backlog": proposal["backlog"],
            "brief": prewrite.package.project_brief_preview,
            "next_steps": prewrite.package.next_steps_preview,
        },
        sort_keys=True,
        default=str,
    )
    actor_labels = [str(row).split(":", 1)[0] for row in proposal["intent"]["human_actors"]]

    assert actor_labels == ["Human Operators"]
    assert "what can be released to partners after legal approval" in rendered.casefold()
    assert "what bes released" not in rendered.casefold()
    assert generated_semantic_slop_issues(proposal, root="proposal") == []
    assert build_greenfield_package_report(prewrite.package).issues == ()


def test_spacecraft_recovery_state_tail_does_not_become_actor_or_clipped_copy(tmp_path: Path) -> None:
    prompt = (
        "Create a greenfield proposal for a spacecraft anomaly triage board that helps mission controllers "
        "compare telemetry claims, fault hypotheses, simulation evidence, command risk, operator approvals, "
        "and recovery state before a corrective procedure is released."
    )

    proposal, prewrite = _proposal_and_prewrite(tmp_path, prompt)
    actor_labels = [str(row).split(":", 1)[0] for row in proposal["intent"]["human_actors"]]
    rendered = json.dumps(
        {
            "intent": proposal["intent"],
            "backlog": proposal["backlog"],
            "brief": prewrite.package.project_brief_preview,
            "next_steps": prewrite.package.next_steps_preview,
        },
        sort_keys=True,
        default=str,
    )

    assert actor_labels == ["Mission Controllers"]
    assert "Recovery State Before a Corrective Procedure" not in rendered
    assert "State Before a" not in rendered
    assert "clipped article phrase" not in "\n".join(greenfield_rendered_package_quality_issues(prewrite.package))
    assert generated_semantic_slop_issues(proposal, root="proposal") == []
    assert build_greenfield_package_report(prewrite.package).issues == ()


def test_scientific_lab_state_predicate_does_not_poison_post_confirm_artifacts(tmp_path: Path) -> None:
    intent = parse_confirmed_intent_text(
        """
# Quantum Tunneling Lab

## Product story
A virtual physics lab helps learners run and understand one-dimensional quantum tunneling experiments without physical equipment.

## State object
A lab session contains the selected experiment, particle properties, barrier shape, energy settings, solver settings, visualization state, measured outputs, notes, and saved results.

## First complete path
A physics learner opens a preset electron tunneling experiment, adjusts barrier height and width, runs the simulation, watches the wave packet interact with the barrier, and saves a short lab result with the chosen parameters and observations.

## Human actors
- Physics learner exploring tunneling behavior.
- Instructor assigning or reviewing lab scenarios.

## Internal product systems
- Experiment workspace.
- Units and parameter validation.
- Quantum solver for one-dimensional tunneling.
- Visualization layer for wave function, potential barrier, and probability outputs.
- Results and notes store.
- Benchmark fixtures for known analytic cases.

## External systems
- Browser runtime for the first version.
- Export target for saved lab reports.

## Critical assumptions
- This is a digital simulation lab, not control software for physical lab equipment.
- The first version focuses on one-dimensional tunneling through rectangular barriers.
- Outputs must be reproducible and checked against known formulas or trusted fixtures.

## Ambiguities
- Whether the target audience is high school, undergraduate physics, or research-oriented users.
- Whether the first version should be web-only or also support local/offline use.

## Proof boundary
The first proof is a working one-dimensional quantum tunneling lab for a rectangular barrier. It should run deterministic sample experiments, show transmission and reflection behavior, preserve units clearly, and match expected analytic or benchmark results within stated tolerances.
""",
        prompt="Draft a greenfield proposal for a quantum tunneling lab.",
    )

    proposal = build_greenfield_proposal(
        repo_root=tmp_path,
        prompt="Draft a greenfield proposal for a quantum tunneling lab.",
        release_selector="0.0.1",
        confirmed_intent=confirmed_mapping_with_authority(intent),
        require_completion_ready=False,
    )
    tribunal = run_greenfield_tribunal(proposal, release_selector="0.0.1")
    prewrite = greenfield_apply_prewrite.build_prewrite_completion_package(
        root=tmp_path,
        proposal=proposal,
        release_selector="0.0.1",
        backlog_args=greenfield_proposals._backlog_apply_args(proposal, release_selector="0.0.1"),
        validation_gate=tribunal.to_dict(),
        release_assignment_note=greenfield_apply_write.release_assignment_note(selector="0.0.1"),
    )
    report = build_greenfield_package_report(prewrite.package)
    rendered = json.dumps(
        {
            "proposal": proposal,
            "project_brief": prewrite.package.project_brief_preview,
            "next_steps": prewrite.package.next_steps_preview,
            "registry": prewrite.package.rendered_component_specs,
            "radar": prewrite.package.backlog_result,
        },
        default=str,
        sort_keys=True,
    )
    registry_rendered = json.dumps(prewrite.package.rendered_component_specs, default=str, sort_keys=True)
    actor_labels = [str(row).split(":", 1)[0] for row in proposal["intent"]["human_actors"]]

    assert report.issues == ()
    assert proposal["semantic_model"]["domain_ontology"]["state_object"] == "Lab Session"
    assert "Lab Session Contains" not in rendered
    assert "openning" not in rendered
    assert "open a preset electron tunneling experiment, adjusts" not in rendered
    assert "done when Done when" not in rendered
    assert "related proof context" not in rendered
    assert "related scope context" not in rendered
    assert not re.search(r"\band\s+or\b", rendered)
    assert not re.search(r"\band\s+and\b", rendered)
    assert "sent, received, declined, and scheduled" not in rendered
    assert "understand one-dimensional quantum tunneling" not in registry_rendered
    assert "Run the simulation" not in actor_labels
    assert "Watch the wave packet interact with the barrier" not in actor_labels
    first_metrics = proposal["backlog"][0]["success_metrics"]
    assert first_metrics[0] == (
        "The first release proves the first path: open a preset electron tunneling experiment, "
        "adjust barrier height and width, run the simulation, watch the wave packet interact with the barrier, "
        "and save a short lab result with the chosen parameters and observations"
    )
    assert not any(metric == "adjust barrier height and width" for metric in first_metrics)
    assert ";" not in first_metrics[0]
    actor_section = next(
        row["must_capture"]
        for row in proposal["project_brief"]["blueprint_sections"]
        if row["section"] == "Actors and systems"
    )
    first_user_option = proposal["project_brief"]["customization_options"][0]["recommended"]
    assert actor_section.startswith("Actors include Physics Learner and Instructor.")
    assert first_user_option == "Confirm who participates in the first path: Physics Learner and Instructor."


def test_gene_expression_confirmed_intent_finishes_without_repeated_result_atlas_copy(tmp_path: Path) -> None:
    prompt = "Draft a product-first greenfield proposal for building an AI-model that simulates gene expression prediction."
    intent = parse_confirmed_intent_text(
        """
# Gene Expression Simulation Model - Product Intent Confirmation

Product story
Gene Expression Simulation Model helps researchers run and review gene expression prediction experiments with a bounded first release.

State object
A gene expression simulation run tracks input dataset, organism or cell type, selected genes or features, perturbation or condition, model version, predicted expression outputs, uncertainty or confidence, comparison evidence, run status, and review notes.

First complete path
A researcher uploads or selects an expression dataset, defines the biological context and prediction target, runs the simulation, reviews predicted expression values against baseline or held-out truth with uncertainty, and saves the result as a reviewable experiment.

Human actors
- Researcher: runs and reviews prediction experiments.
- Scientific reviewer: checks assumptions, uncertainty, and comparison evidence.

External systems
- Public or lab-owned gene expression datasets.
- Reference genome or annotation sources.
- Compute environment for training and inference.
- Optional model artifact storage or experiment tracking system.

Internal product systems
- Dataset Intake Register.
- Model Execution Record.
- Results Review Workspace.
- Experiment Proof Ledger.

Critical assumptions
- Release 0.0.1 proves one bounded prediction workflow before broader automation.

Ambiguities
- Exact organism, model family, reference baseline, and tolerance thresholds can be refined after the first proof path is accepted.

Proof boundary
Release 0.0.1 succeeds when a researcher can run one gene expression prediction, review inputs, model version, predicted outputs, uncertainty, baseline comparison, and reopen the saved run. It must not claim biological truth or broader model performance beyond the accepted evidence.
""",
        prompt=prompt,
    )
    proposal = build_greenfield_proposal(
        repo_root=tmp_path,
        prompt=prompt,
        release_selector="0.0.1",
        confirmed_intent=confirmed_mapping_with_authority(intent),
        require_completion_ready=False,
    )
    tribunal = run_greenfield_tribunal(proposal, release_selector="0.0.1")
    prewrite = greenfield_apply_prewrite.build_prewrite_completion_package(
        root=tmp_path,
        proposal=proposal,
        release_selector="0.0.1",
        backlog_args=greenfield_proposals._backlog_apply_args(proposal, release_selector="0.0.1"),
        validation_gate=tribunal.to_dict(),
        release_assignment_note=greenfield_apply_write.release_assignment_note(selector="0.0.1"),
    )
    report = build_greenfield_package_report(prewrite.package)
    atlas = json.dumps(prewrite.package.rendered_atlas_sources, sort_keys=True)
    rendered = json.dumps(
        {
            "proposal": proposal,
            "radar": prewrite.package.backlog_result,
            "registry": prewrite.package.rendered_component_specs,
            "atlas": prewrite.package.rendered_atlas_sources,
            "brief": prewrite.package.project_brief_preview,
        },
        default=str,
        sort_keys=True,
    )

    assert tribunal.passed, tribunal.issues
    assert proposal["semantic_model"]["first_path_contract"]["visible_result"] == "Saved reviewable experiment"
    assert proposal["semantic_model"]["evaluation_semantics"]["focus"] == "Gene Expression Simulation Model"
    assert "Proof result<br/>Saved reviewable experiment" in atlas
    assert "Visible result<br/>Saved reviewable experiment" in atlas
    assert "Upload or select an expression<br/>dataset" in atlas
    assert "Define the biological context<br/>and prediction target" in atlas
    assert "Run the simulation" in atlas
    assert "Uploads or select" not in atlas
    assert "result result" not in atlas.casefold()
    rendered_lower = rendered.casefold()
    for term in ("baseline", "comparison", "uncertainty", "tolerance", "method", "model version", "reproducibility"):
        assert term in rendered_lower
    for bad_phrase in (
        "weak inputs are or selects",
        "expression decide result",
        "ledger public lab-owned gene",
        "the weak inputs are or",
    ):
        assert bad_phrase not in rendered_lower
    assert report.issues == ()
    assert greenfield_rendered_package_quality_issues(prewrite.package) == ()


def test_review_and_adjustment_prompts_avoid_generic_handoff_and_recommendation_drift(tmp_path: Path) -> None:
    tenant_prompt = (
        "Create a greenfield product for tenant aid coordinators who intake housing requests, verify "
        "eligibility documents, match residents to assistance programs, track case blockers, and prepare "
        "approval packets for supervisor review."
    )
    warehouse_prompt = (
        "Create a greenfield product for warehouse shift leads who reconcile inventory exceptions, compare "
        "scanner counts against expected stock, assign cycle-count follow-up, and publish an auditable "
        "adjustment decision."
    )

    tenant_proposal, tenant_prewrite = _proposal_and_prewrite(tmp_path / "tenant", tenant_prompt)
    warehouse_proposal, warehouse_prewrite = _proposal_and_prewrite(tmp_path / "warehouse", warehouse_prompt)
    tenant_payload = json.dumps(
        {"proposal": tenant_proposal, "next_steps": tenant_prewrite.package.next_steps_preview},
        sort_keys=True,
    ).casefold()
    warehouse_payload = json.dumps(
        {"proposal": warehouse_proposal, "next_steps": warehouse_prewrite.package.next_steps_preview},
        sort_keys=True,
    ).casefold()
    tenant_actor_labels = [str(row).split(":", 1)[0] for row in tenant_proposal["intent"]["human_actors"]]

    assert "downstream actor" not in tenant_payload
    assert "Packets for Supervisor" not in tenant_actor_labels
    assert "recommendation" not in warehouse_payload
    assert build_greenfield_package_report(tenant_prewrite.package).issues == ()
    assert build_greenfield_package_report(warehouse_prewrite.package).issues == ()


def test_wearable_quote_prompt_keeps_radar_inline_labels_sentence_safe(tmp_path: Path) -> None:
    prompt = (
        'Create a greenfield product for wearable-informed lab recovery teams that can ingest motion sensor recovery entries, '
        'therapist consent notes, and adverse symptom check-ins, then show clear "what changed" insights, access-safe escalation tasks, '
        "and a release evidence report without making medical diagnosis or personalized treatment claims."
    )

    proposal, prewrite = _proposal_and_prewrite(tmp_path / "wearable", prompt)
    report = build_greenfield_package_report(prewrite.package)
    rendered = json.dumps(
        {
            "proposal": proposal,
            "radar": prewrite.package.backlog_result,
            "project_brief": prewrite.package.project_brief_preview,
        },
        default=str,
        sort_keys=True,
    )

    assert report.issues == ()
    assert "first path, What Changed" not in rendered
    assert "can can ingest" not in rendered
    assert "clear what changed insights" in rendered.casefold()


def test_use_to_relative_prompt_does_not_leak_compact_mixed_action_memory(tmp_path: Path) -> None:
    prompt = (
        "Create a greenfield product for kitchen robot controllers that home cooks use to choose recipes, "
        "adjust portions, and start cooking runs."
    )

    proposal, prewrite = _proposal_and_prewrite(tmp_path / "kitchen", prompt)
    report = build_greenfield_package_report(prewrite.package)
    rendered = json.dumps(
        {
            "proposal": proposal,
            "radar": prewrite.package.backlog_result,
            "accepted_project": prewrite.package.accepted_project_preview,
        },
        default=str,
        sort_keys=True,
    ).casefold()

    assert proposal["intent"]["first_path"].startswith("Home cooks choose recipes")
    assert "use to choose" not in rendered
    assert "review to choose" not in rendered
    assert report.issues == ()


def test_computer_vision_defect_result_slot_rerenders_confirmed_artifacts(tmp_path: Path) -> None:
    prompt = (
        "Create a greenfield proposal for a computer vision defect adjudication system that tracks image sensor "
        "calibration, labeled defect classes, model confidence, reviewer overrides, production lot disposition, "
        "and traceable proof."
    )

    proposal, prewrite = _proposal_and_prewrite(tmp_path / "computer-vision", prompt)
    report = build_greenfield_package_report(prewrite.package)
    rendered_atlas = json.dumps(prewrite.package.rendered_atlas_sources, sort_keys=True)
    rendered_public_artifacts = json.dumps(
        {
            "backlog": proposal["backlog"],
            "project_brief": prewrite.package.project_brief_preview,
            "next_steps": prewrite.package.next_steps_preview,
            "atlas": prewrite.package.rendered_atlas_sources,
        },
        default=str,
        sort_keys=True,
    ).casefold()
    accepted_project_intelligence = json.dumps(
        prewrite.package.accepted_project_preview["proposal"]["project_intelligence"],
        default=str,
        sort_keys=True,
    ).casefold()

    assert report.issues == ()
    assert greenfield_rendered_package_quality_issues(prewrite.package) == ()
    assert proposal["semantic_model"]["first_path_contract"]["visible_result"] == (
        "the computer vision defect adjudication result"
    )
    assert "Proof result<br/>the computer vision defect<br/>adjudication result" in rendered_atlas
    assert "Visible result<br/>the computer vision defect<br/>adjudication result" in rendered_atlas
    assert "result result" not in rendered_public_artifacts
    assert "the computer vision defect adjudication result, handles" not in rendered_public_artifacts
    assert "the computer vision defect adjudication result, handles" not in accepted_project_intelligence
    assert "and keeps replayable evidence for review and keeping" not in rendered_public_artifacts
    assert "handles missing or invalid input with a clear blocker, and keeps" not in rendered_atlas.casefold()
