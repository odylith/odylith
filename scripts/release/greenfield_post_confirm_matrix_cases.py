"""High-variance greenfield post-confirm release matrix cases."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GreenfieldMatrixCase:
    name: str
    prompt: str
    required_terms: tuple[str, ...]
    leakage_terms: tuple[str, ...] = ()
    confirmed_intent_markdown: str = ""
    case_id: str = ""
    tags: tuple[str, ...] = ()
    stressors: tuple[str, ...] = ()
    source_file: str = ""

    @property
    def slug(self) -> str:
        return "-".join(token for token in self.name.casefold().split() if token)


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
            leakage_terms=("flood shelter", "shelter capacity", "displaced residents"),
            stressors=("long-first-path", "multi-role-tribunal", "path-grant", "final-memory-pressure"),
        ),
        GreenfieldMatrixCase(
            name="pediatric agency practice",
            prompt=(
                "Create a greenfield proposal for a pediatric therapy agency practice workspace that coordinates "
                "referral intake, guardian consent, therapist assignment, care-plan readiness, visit evidence, "
                "and exception review for children served across multiple schools."
            ),
            required_terms=("pediatric", "therapy", "guardian", "care"),
            leakage_terms=("pediatric therapy", "guardian consent", "therapist assignment"),
            stressors=("modal-expert-lens", "multi-role-tribunal", "path-grant", "domain-depth-obligations"),
        ),
        GreenfieldMatrixCase(
            name="semiconductor lab custody",
            prompt=(
                "Create a greenfield proposal for a semiconductor reliability lab custody platform that receives "
                "wafer lot samples, records chamber exposure conditions, preserves chain-of-custody evidence, "
                "tracks failed stress runs, and prepares release readiness proof for engineering review."
            ),
            required_terms=("semiconductor", "wafer", "custody", "reliability"),
            leakage_terms=("semiconductor", "wafer lot", "chamber exposure"),
            stressors=("scientific-casing", "domain-depth-obligations", "registry-contract-pressure", "latency-pressure"),
        ),
        GreenfieldMatrixCase(
            name="port berth carbon tariff",
            prompt=(
                "Create a greenfield proposal for a port berth carbon tariff planner that lets port operations "
                "compare vessel schedules, berth windows, shore-power availability, emissions evidence, tariff "
                "exceptions, and operator signoff before publishing a daily berth plan."
            ),
            required_terms=("port", "berth", "tariff", "emissions"),
            leakage_terms=("port berth", "carbon tariff", "shore power", "emissions"),
            stressors=("long-first-path", "atlas-label-pressure", "path-grant", "modal-expert-lens"),
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
            leakage_terms=("security disclosure council", "embargo decisions", "public advisory"),
            stressors=("multi-role-tribunal", "final-memory-pressure", "modal-expert-lens", "path-grant"),
        ),
        GreenfieldMatrixCase(
            name="open source security embargo",
            prompt=(
                "Create a greenfield proposal for an open source security embargo room that receives vulnerability "
                "reports, coordinates maintainer triage, tracks affected package evidence, records disclosure "
                "approvals, and shows advisory readiness without sending public announcements in the first release."
            ),
            required_terms=("open", "source", "security", "embargo"),
            leakage_terms=("open source security embargo", "vulnerability reports", "advisory readiness"),
            stressors=("noun-verb-homonym", "multi-role-tribunal", "final-memory-pressure", "registry-contract-pressure"),
        ),
        GreenfieldMatrixCase(
            name="package supply chain exception desk",
            prompt=(
                "Create a greenfield proposal for a package supply chain exception desk that receives vulnerable "
                "dependency reports, tracks provenance and waiver evidence, coordinates package manager review, "
                "preserves release readiness proof, and blocks shipment until exceptions are approved."
            ),
            required_terms=("package", "dependency", "provenance", "waiver"),
            leakage_terms=("supply chain exception desk", "vulnerable dependency", "package manager review"),
            stressors=("noun-verb-homonym", "registry-contract-pressure", "path-grant", "domain-depth-obligations"),
        ),
        GreenfieldMatrixCase(
            name="credit union fair lending exception",
            prompt=(
                "Create a greenfield proposal for a credit union fair-lending exception review workspace that helps "
                "loan officers submit exception requests, preserves applicant consent and underwriting evidence, "
                "routes compliance review, records adverse-action rationale, and publishes portfolio readiness proof "
                "without automating final credit decisions in the first release."
            ),
            required_terms=("credit", "union", "lending", "underwriting"),
            leakage_terms=("credit union", "fair lending", "underwriting evidence"),
            stressors=("modal-expert-lens", "multi-role-tribunal", "final-memory-pressure", "domain-depth-obligations"),
        ),
        GreenfieldMatrixCase(
            name="apprenticeship credential readiness",
            prompt=(
                "Create a greenfield proposal for a regional apprenticeship credential readiness system that lets "
                "training coordinators register apprentices, map completed skills to employer requirements, track "
                "mentor signoff evidence, manage accommodation exceptions, and publish certification readiness for "
                "review by a workforce board."
            ),
            required_terms=("apprenticeship", "credential", "mentor", "certification"),
            leakage_terms=("apprenticeship", "credential readiness", "mentor signoff"),
            stressors=("multi-role-tribunal", "path-grant", "long-first-path", "registry-contract-pressure"),
        ),
        GreenfieldMatrixCase(
            name="film archive rights clearance",
            prompt=(
                "Create a greenfield proposal for an independent film archive rights-clearance workspace that helps "
                "curators ingest donated reels, track contributor agreements, flag disputed footage, preserve review "
                "evidence, and publish screening readiness without claiming automated legal clearance."
            ),
            required_terms=("film", "archive", "rights", "screening"),
            leakage_terms=("film archive", "rights clearance", "donated reels"),
            stressors=("modal-expert-lens", "final-memory-pressure", "domain-depth-obligations", "path-grant"),
        ),
        GreenfieldMatrixCase(
            name="developer incident runbook readiness",
            prompt=(
                "Create a greenfield proposal for a developer incident runbook readiness tool that lets engineering "
                "leads capture service incidents, map owners to mitigation steps, collect verification evidence, "
                "track follow-up exceptions, and publish release-readiness proof before the next deployment window."
            ),
            required_terms=("developer", "incident", "runbook", "deployment"),
            leakage_terms=("developer incident runbook", "mitigation steps", "deployment window"),
            stressors=("registry-contract-pressure", "latency-pressure", "final-memory-pressure", "atlas-label-pressure"),
        ),
        GreenfieldMatrixCase(
            name="assay drift prediction model",
            prompt="Draft a product-first greenfield proposal for building an assay drift prediction model.",
            required_terms=("assay", "drift", "prediction", "model"),
            leakage_terms=("assay drift", "prediction model", "assay drift prediction"),
            stressors=("scientific-casing", "domain-depth-obligations", "registry-contract-pressure", "latency-pressure"),
        ),
        GreenfieldMatrixCase(
            name="sparse disclosure confirmation",
            prompt=(
                "Create a greenfield proposal for a cross-organization disclosure council that receives reports, "
                "coordinates review, records evidence custody, decides embargo status, and publishes release readiness proof."
            ),
            required_terms=("disclosure", "council", "evidence", "embargo"),
            leakage_terms=("disclosure council", "embargo decision", "personalized notification delivery"),
            stressors=("final-memory-pressure", "multi-role-tribunal", "long-first-path", "modal-expert-lens"),
            confirmed_intent_markdown="""
# Product Intent Confirmation

## Title
Disclosure council

## Product story
External researchers and internal owners coordinate a disclosure review.

## State object
Report.

## First complete path
Reporter submits a report; owner reviews it; council publishes proof.

## Actors
Reporter, owner, council.

## Systems
Intake desk, review log.

## Assumptions
The first release records evidence only.

## Ambiguities
Notification delivery is not included.

## Non-goals
Personalized notification delivery is outside the first release.

## Proof boundary
Evidence custody and embargo decision.
""".strip(),
        ),
        GreenfieldMatrixCase(
            name="quantum communication lab",
            prompt="Draft a greenfield proposal for a lab app where we are building quantum communication",
            required_terms=("quantum", "e91", "qber", "chsh"),
            leakage_terms=(
                "quantum communication",
                "entangled photon",
                "coincidence counts",
                "bell inequality",
                "e91",
                "qber",
                "chsh",
            ),
            stressors=(
                "scientific-casing",
                "domain-depth-obligations",
                "long-first-path",
                "atlas-label-pressure",
                "registry-contract-pressure",
                "latency-pressure",
                "noun-verb-homonym",
            ),
            confirmed_intent_markdown="""
# Quantum Link Lab

## Product story
A lab application for a research team running entanglement-based quantum communication on real hardware. A researcher configures a run, launches it, and watches the link behave live: entangled pairs distributed, coincidence counts, the measured Bell/CHSH parameter, error rate (QBER), and sifted or final key bits. The headline question is whether the entanglement survived the channel well enough to certify a secure link, judged by the Bell-inequality violation.

## State object
A communication run: E91 parameters, measurement-basis configuration, bound source and station endpoints, live and final measurements, CHSH value, QBER, key length, status, and timestamped history for review and comparison.

## First complete path
A researcher opens the lab, defines a new E91 run, launches it against the hardware, watches coincidences and the live CHSH value stream in, and ends with a completed run that reports whether the Bell inequality was violated, the QBER, and the key established, saved and viewable alongside prior runs.

## Human actors
- Researcher - configures and launches E91 runs, reads live and historical results.
- Lab lead - reviews run history, compares configurations, judges link viability.
- Lab technician - manages source and station hardware setup, monitors active runs.

## External systems
- Entangled-photon source rig and its control interface.
- Two measurement stations and their control or readout interface.
- Coincidence-counting or time-tagging electronics.
- Shared clock or synchronization source across the stations.

## Internal product systems
- Run configuration and validation - supports E91 parameters, bases, and endpoints.
- Hardware control and run execution - drives the source and stations and sequences a run.
- Live telemetry stream - exposes coincidences, CHSH, and QBER while the run progresses.
- Security and verification logic - checks Bell-inequality verdicts and key sifting.
- Results store and run history - keeps saved runs, comparison, and review evidence.

## Critical assumptions
- The first release drives real lab hardware through an available control interface.
- E91 is the headline protocol and CHSH/Bell violation is the first security test.
- A run is owned by one researcher session at a time.
- Live telemetry and saved comparable run history are both required from day one.

## Ambiguities
- Is there a documented hardware control API, or does the app need a driver layer first?
- Are laser and detector safety interlocks in first release scope or externally handled?
- Does the first release operate one shared rig or select between multiple rigs?

## Proof boundary
The product is proven when a researcher can configure an E91 run, launch it on the real rig, watch coincidences and CHSH stream live, end with a saved run that reports the Bell verdict, QBER, and established key, then find that run in history and compare it. Formal security certification and hardware safety certification are outside this first proof.
""".strip(),
        ),
    )


def rescue_smoke_case() -> GreenfieldMatrixCase:
    """Return the internal auto-rescue release proof fixture."""

    return GreenfieldMatrixCase(
        name="rescue disclosure council",
        prompt=(
            "Create a greenfield proposal for a cross-organization disclosure council that receives external reports, "
            "coordinates review, records evidence custody, decides embargo status, and publishes release readiness proof "
            "without claiming personalized notification delivery in the first release."
        ),
        required_terms=("disclosure", "council", "embargo", "evidence"),
        leakage_terms=("disclosure council", "embargo status", "personalized notification delivery"),
        stressors=("final-memory-pressure", "multi-role-tribunal", "path-grant", "modal-expert-lens"),
    )


def historical_domain_leakage_sentinels() -> tuple[str, ...]:
    """Return historical consumer-domain sentinels for release leakage proof."""

    return (
        "anger management",
        "appointment",
        "booking",
        "digestive health",
        "fifa tracker",
        "quantum tunneling",
        "request says record is both a noun and a governed object",
        "request uses record as both a noun and a governed object",
        "request uses record as both a verb and a governed object",
        "request uses record both as an action and as a governed object",
        "wearable app",
        "workout",
    )


__all__ = [
    "GreenfieldMatrixCase",
    "default_cases",
    "historical_domain_leakage_sentinels",
    "rescue_smoke_case",
]
