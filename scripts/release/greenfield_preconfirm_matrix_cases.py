"""High-variance Greenfield transaction-matrix cases."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
import hashlib

from greenfield_matrix_corpus_provenance import case_provenance_summary

from greenfield_matrix_corpus_provenance import GreenfieldCaseProvenance
from greenfield_matrix_input_axes import DEFAULT_INPUT_STYLE


DEFAULT_CASE_EXPECTATION = "transaction_committed"
CLARIFICATION_REQUIRED_EXPECTATION = "clarification_required"
VALID_CASE_EXPECTATIONS = frozenset(
    {
        DEFAULT_CASE_EXPECTATION,
        CLARIFICATION_REQUIRED_EXPECTATION,
    }
)


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
    provenance: GreenfieldCaseProvenance = field(default_factory=GreenfieldCaseProvenance)
    expectation: str = DEFAULT_CASE_EXPECTATION
    input_style: str = DEFAULT_INPUT_STYLE
    input_style_declared: bool = False
    metamorphic_group: str = ""
    metamorphic_transform: str = ""
    expected_question_fields: tuple[str, ...] = ()

    @property
    def slug(self) -> str:
        return "-".join(token for token in self.name.casefold().split() if token)


def case_expectation(case: GreenfieldMatrixCase) -> str:
    return str(getattr(case, "expectation", "") or DEFAULT_CASE_EXPECTATION).strip().casefold()


def case_evidence(case: GreenfieldMatrixCase) -> dict[str, object]:
    """Return non-sensitive case identity evidence for matrix proof records."""

    evidence: dict[str, object] = {
        "id": str(getattr(case, "case_id", "") or case.slug),
        "name": case.name,
        "slug": case.slug,
        "source_file": str(getattr(case, "source_file", "") or ""),
        "expectation": case_expectation(case),
        "tags": list(getattr(case, "tags", ()) or ()),
        "stressors": list(getattr(case, "stressors", ()) or ()),
        "prompt_sha256": hashlib.sha256(str(case.prompt or "").encode("utf-8")).hexdigest(),
        "required_terms": list(case.required_terms),
        "leakage_terms": list(getattr(case, "leakage_terms", ()) or ()),
        "provenance": case_provenance_summary(getattr(case, "provenance", None)),
    }
    confirmed_intent = str(getattr(case, "confirmed_intent_markdown", "") or "").strip()
    if confirmed_intent:
        evidence["confirmed_intent_sha256"] = hashlib.sha256(confirmed_intent.encode("utf-8")).hexdigest()
    expected_question_fields = tuple(getattr(case, "expected_question_fields", ()) or ())
    if expected_question_fields:
        evidence["expected_question_fields"] = list(expected_question_fields)
    return evidence


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
            expectation=CLARIFICATION_REQUIRED_EXPECTATION,
        ),
        GreenfieldMatrixCase(
            name="sparse disclosure confirmation",
            prompt=(
                "Create a greenfield proposal for a cross-organization disclosure council that receives reports, "
                "coordinates review, records evidence custody, decides embargo status, and publishes first release "
                "readiness proof without personalized notification delivery."
            ),
            required_terms=("disclosure", "council", "evidence", "embargo"),
            leakage_terms=("disclosure council", "embargo decision", "personalized notification delivery"),
            stressors=("final-memory-pressure", "multi-role-tribunal", "long-first-path", "modal-expert-lens"),
        ),
        GreenfieldMatrixCase(
            name="quantum communication lab",
            prompt=(
                "Draft a greenfield proposal for a lab app where researchers configure and launch an E91 quantum "
                "communication run on real hardware, observe live coincidence counts, Bell inequality checks, CHSH, "
                "QBER, and established key bits, then compare the saved run against prior results."
            ),
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
    "CLARIFICATION_REQUIRED_EXPECTATION",
    "DEFAULT_CASE_EXPECTATION",
    "GreenfieldMatrixCase",
    "GreenfieldCaseProvenance",
    "VALID_CASE_EXPECTATIONS",
    "case_expectation",
    "default_cases",
    "historical_domain_leakage_sentinels",
    "rescue_smoke_case",
]
