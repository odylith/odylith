"""High-variance greenfield post-confirm release matrix cases."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GreenfieldMatrixCase:
    name: str
    prompt: str
    required_terms: tuple[str, ...]
    confirmed_intent_markdown: str = ""

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
        GreenfieldMatrixCase(
            name="open source security embargo",
            prompt=(
                "Create a greenfield proposal for an open source security embargo room that receives vulnerability "
                "reports, coordinates maintainer triage, tracks affected package evidence, records disclosure "
                "approvals, and shows advisory readiness without sending public announcements in the first release."
            ),
            required_terms=("open", "source", "security", "embargo"),
        ),
        GreenfieldMatrixCase(
            name="sparse disclosure confirmation",
            prompt=(
                "Create a greenfield proposal for a cross-organization disclosure council that receives reports, "
                "coordinates review, records evidence custody, decides embargo status, and publishes release readiness proof."
            ),
            required_terms=("disclosure", "council", "evidence", "embargo"),
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

## Proof boundary
Evidence custody and embargo decision.
""".strip(),
        ),
        GreenfieldMatrixCase(
            name="quantum communication lab",
            prompt="Draft a greenfield proposal for a lab app where we are building quantum communication",
            required_terms=("quantum", "e91", "qber", "chsh"),
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


__all__ = ["GreenfieldMatrixCase", "default_cases"]
