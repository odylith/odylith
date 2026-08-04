from __future__ import annotations

import importlib.util
import importlib
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from odylith.runtime.artifact_quality.greenfield_package_quality import greenfield_rendered_package_quality_issues
from odylith.runtime.domain_intelligence.greenfield_preconfirm_rescue_probe import (
    RESCUE_PROBE_ENV,
)
from odylith.runtime.domain_intelligence.greenfield_preconfirm_rescue_probe import (
    RESCUE_PROBE_TOKEN,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_ROOT = REPO_ROOT / "scripts" / "release"


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _module():
    return _load_module(SCRIPTS_ROOT / "greenfield_preconfirm_matrix.py", "greenfield_preconfirm_matrix")


def _stub_active_clarification_audit(monkeypatch: pytest.MonkeyPatch, module) -> None:
    class ActiveAudit:
        pass_fds: tuple[int, ...] = ()

        def environment(self) -> dict[str, str]:
            return {}

        def command(self, *, runtime_python: Path, arguments: tuple[str, ...]) -> tuple[str, ...]:
            _ = runtime_python
            return ("./.odylith/bin/odylith", *arguments)

        def finish(self) -> SimpleNamespace:
            return SimpleNamespace(
                active=True,
                write_attempts=(),
                subprocess_attempts=(),
                error="",
            )

    monkeypatch.setattr(module, "begin_installed_write_audit", lambda **_kwargs: ActiveAudit())


def _scoring_module():
    if str(SCRIPTS_ROOT) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_ROOT))
    return importlib.import_module("greenfield_matrix_quality_scoring")


def _package_evidence_module():
    if str(SCRIPTS_ROOT) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_ROOT))
    return importlib.import_module("greenfield_matrix_package_evidence")


def _governed_readback_module():
    if str(SCRIPTS_ROOT) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_ROOT))
    return importlib.import_module("greenfield_matrix_governed_readback")


def test_default_matrix_keeps_open_source_security_escape_replay() -> None:
    module = _module()

    cases = module.default_cases()

    assert len(cases) >= 10
    module._raise_for_ungrounded_required_terms(cases)  # noqa: SLF001
    assert module._term_present("displaced residents register for shelter", "resident")  # noqa: SLF001
    for name in (
        "credit union fair lending exception",
        "apprenticeship credential readiness",
        "film archive rights clearance",
        "developer incident runbook readiness",
    ):
        assert any(case.name == name for case in cases)
    escaped_case = next(case for case in cases if case.name == "open source security embargo")
    assert "open source security embargo room" in escaped_case.prompt
    assert "receives vulnerability reports" in escaped_case.prompt
    assert escaped_case.required_terms == ("open", "source", "security", "embargo")
    package_case = next(case for case in cases if case.name == "package supply chain exception desk")
    assert "receives vulnerable dependency reports" in package_case.prompt
    assert "tracks provenance and waiver evidence" in package_case.prompt
    assert package_case.required_terms == ("package", "dependency", "provenance", "waiver")
    sparse_case = next(case for case in cases if case.name == "sparse disclosure confirmation")
    sparse_prompt = sparse_case.prompt.casefold()
    assert "evidence custody" in sparse_prompt
    assert "personalized notification" in sparse_prompt
    assert "first release" in sparse_prompt
    assert sparse_case.required_terms == ("disclosure", "council", "evidence", "embargo")
    security_case = next(case for case in cases if case.name == "security disclosure council")
    assert security_case.expectation == "transaction_committed"
    assay_case = next(case for case in cases if case.name == "assay drift prediction model")
    assert assay_case.expectation == "clarification_required"
    quantum_case = next(case for case in cases if case.name == "quantum communication lab")
    quantum_prompt = quantum_case.prompt.casefold()
    assert "communication run" in quantum_prompt
    assert "chsh" in quantum_prompt
    assert "qber" in quantum_prompt
    assert quantum_case.required_terms == ("quantum", "e91", "qber", "chsh")
    assert "assay drift prediction model" in assay_case.prompt
    assert assay_case.required_terms == ("assay", "drift", "prediction", "model")


def test_run_matrix_scans_selected_case_vocabulary_before_simulation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _module()
    dist_dir = tmp_path / "dist"
    _write(dist_dir / "install.sh", "#!/usr/bin/env bash\n")
    captured_terms: list[tuple[str, ...]] = []

    def fake_scan_platform_custody(*, repo_root: Path, dist_dir: Path, terms: tuple[str, ...]):
        captured_terms.append(terms)
        return tuple(
            module.platform_domain_leakage.LeakageFinding(
                location="src/odylith/runtime/example.py",
                term=term,
                line=index,
            )
            for index, term in enumerate(terms, start=1)
        )

    monkeypatch.setattr(module.platform_domain_leakage, "scan_platform_custody", fake_scan_platform_custody)

    with pytest.raises(RuntimeError, match="selected greenfield matrix case vocabulary"):
        module.run_matrix(
            dist_dir=dist_dir,
            version="0.1.15",
            temp_parent=tmp_path,
            cases=(
                module.GreenfieldMatrixCase(
                    name="xenobot custody",
                    prompt="Create a greenfield proposal for xenobot culture.",
                    required_terms=("xenobot", "culture"),
                    leakage_terms=("xenobot culture",),
                ),
            ),
        )

    assert len(captured_terms) == 1
    assert "xenobot culture" in captured_terms[0]
    assert not any(path.name.startswith("odylith-greenfield-matrix-") for path in tmp_path.iterdir())


def test_matrix_preflight_replaces_platform_native_declared_sentinel_with_source_candidate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _module()
    dist_dir = tmp_path / "dist"
    _write(dist_dir / "install.sh", "#!/usr/bin/env bash\n")
    captured_terms: list[tuple[str, ...]] = []

    def fake_scan_platform_custody(*, repo_root: Path, dist_dir: Path, terms: tuple[str, ...]):
        captured_terms.append(terms)
        return (
            module.platform_domain_leakage.LeakageFinding(
                location="src/odylith/runtime/project_intelligence/greenfield_boundary_cards.py",
                term="calibration drift",
                line=221,
            ),
        )

    monkeypatch.setattr(module.platform_domain_leakage, "scan_platform_custody", fake_scan_platform_custody)
    case = module.GreenfieldMatrixCase(
        name="sepsis early warning calibration",
        prompt=(
            "Create a greenfield proposal for a sepsis early warning calibration workspace that compares "
            "vitals streams, lab results, model thresholds, calibration drift, false-positive reviews, "
            "clinician overrides, and fairness evidence before deployment readiness review."
        ),
        required_terms=("sepsis", "calibration", "false-positive", "clinician"),
        leakage_terms=("calibration drift",),
    )

    failures = module.matrix_preflight_failures(
        repo_root=module.REPO_ROOT,
        release_dir=dist_dir,
        cases=(case,),
        required_stressors=(),
        enforce_required_stressors=False,
    )

    assert failures == ()
    assert len(captured_terms) == 1
    assert "calibration drift" in captured_terms[0]
    assert "early warning calibration" in captured_terms[0]


def test_run_matrix_preflight_ignores_stale_declared_sentinels_without_source_grounding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _module()
    dist_dir = tmp_path / "dist"
    _write(dist_dir / "install.sh", "#!/usr/bin/env bash\n")
    captured_terms: list[tuple[str, ...]] = []

    def fake_scan_platform_custody(*, repo_root: Path, dist_dir: Path, terms: tuple[str, ...]):
        captured_terms.append(terms)
        return (
            module.platform_domain_leakage.LeakageFinding(
                location="src/odylith/runtime/example.py",
                term=terms[0],
                line=1,
            ),
        )

    monkeypatch.setattr(module.platform_domain_leakage, "scan_platform_custody", fake_scan_platform_custody)

    with pytest.raises(RuntimeError, match="selected greenfield matrix case vocabulary"):
        module.run_matrix(
            dist_dir=dist_dir,
            version="0.1.15",
            temp_parent=tmp_path,
            cases=(
                module.GreenfieldMatrixCase(
                    name="language archive",
                    prompt="Create a greenfield proposal for language archive dictionary review.",
                    required_terms=("language", "archive", "dictionary"),
                    leakage_terms=("dictionary review sentinel",),
                ),
            ),
        )

    assert len(captured_terms) == 1
    assert "dictionary review sentinel" not in captured_terms[0]
    assert "language archive dictionary" in captured_terms[0]
    assert not any(path.name.startswith("odylith-greenfield-matrix-") for path in tmp_path.iterdir())


def test_run_matrix_rejects_custom_cases_without_distinctive_leakage_terms(tmp_path: Path) -> None:
    module = _module()
    dist_dir = tmp_path / "dist"
    _write(dist_dir / "install.sh", "#!/usr/bin/env bash\n")

    with pytest.raises(RuntimeError, match="declare leakage_terms"):
        module.run_matrix(
            dist_dir=dist_dir,
            version="0.1.15",
            temp_parent=tmp_path,
            cases=(
                module.GreenfieldMatrixCase(
                    name="platform-native only",
                    prompt="Create a greenfield proposal for an agent tool permission tribunal.",
                    required_terms=("agent", "tool", "permission", "tribunal"),
                ),
            ),
        )

    assert not any(path.name.startswith("odylith-greenfield-matrix-") for path in tmp_path.iterdir())


def test_run_matrix_rejects_ungrounded_required_terms_before_simulation(tmp_path: Path) -> None:
    module = _module()
    dist_dir = tmp_path / "dist"
    _write(dist_dir / "install.sh", "#!/usr/bin/env bash\n")

    with pytest.raises(RuntimeError, match="required_terms must be grounded"):
        module.run_matrix(
            dist_dir=dist_dir,
            version="0.1.15",
            temp_parent=tmp_path,
            cases=(
                module.GreenfieldMatrixCase(
                    name="ungrounded anchor",
                    prompt="Create a greenfield proposal for protocol review.",
                    required_terms=("protocol", "trial"),
                    leakage_terms=("protocol review",),
                ),
            ),
        )

    assert not any(path.name.startswith("odylith-greenfield-matrix-") for path in tmp_path.iterdir())


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _passing_visible_actors() -> list[dict[str, str]]:
    return [
        {
            "stable_role": "beneficiary_advocate",
            "visible_actor": "Permit beneficiary advocate",
            "actor_source": "generated_role_projection",
        },
        {
            "stable_role": "domain_operator",
            "visible_actor": "Permit workflow operator",
            "actor_source": "generated_role_projection",
        },
        {
            "stable_role": "risk_owner",
            "visible_actor": "Permit risk reviewer",
            "actor_source": "generated_role_projection",
        },
        {
            "stable_role": "evidence_owner",
            "visible_actor": "Permit proof reviewer",
            "actor_source": "generated_role_projection",
        },
    ]


def _empty_package() -> SimpleNamespace:
    return SimpleNamespace(
        proposal={},
        backlog_result={"idea_files": {}, "backlog_index_text": ""},
        rendered_component_specs={},
        rendered_atlas_sources={},
        component_registry_preview=(),
        project_brief_preview={},
        project_brief_record_text="",
        accepted_project_preview={"validation_gate": {"visible_actors": _passing_visible_actors()}},
        source_launch_readback={},
        project_dashboard_preview={},
        compass_memory_preview={},
        governed_readback=_empty_governed_readback(),
        next_steps_preview={},
        program_result={},
        prewrite_safety_preview={},
        release_target_result={},
        release_assignment_result={},
        release_workstream_ids=(),
    )


def _substantive_project_brief() -> dict[str, object]:
    return {
        "purpose": "Coordinate permit readiness from submitted evidence through reviewable approval without bypassing human judgment.",
        "operating_principle": (
            "Keep every permit state transition tied to source evidence, reviewer ownership, blocked-path proof, "
            "and explicit release scope."
        ),
        "project_outcome": (
            "Release 0.0.1 proves one accepted permit path where intake, evidence review, decision rationale, "
            "and readiness proof stay connected."
        ),
        "blueprint_sections": [
            {
                "section": f"Blueprint section {index}",
                "must_capture": "The accepted actor, state change, evidence source, and release boundary.",
                "why_it_matters": "The implementation plan needs a concrete proof target before source work starts.",
            }
            for index in range(1, 5)
        ],
        "customization_options": [
            {
                "id": f"option-{index}",
                "decision": "Review depth",
                "recommended": "Keep the first release focused on one governed permit path.",
                "choices": ["single path", "expanded routing"],
                "impact": "Changes the amount of evidence and review routing required before coding.",
            }
            for index in range(1, 6)
        ],
        "customization_prompts": [
            "Prioritize reviewer evidence before adding additional notification channels.",
            "Keep the first release bounded to one permit path.",
            "Treat missing evidence as a blocked path requiring explanation.",
        ],
        "pre_coding_checkpoints": [
            {
                "checkpoint": f"Checkpoint {index}",
                "operator_question": "Is the accepted path still concrete and reviewable?",
                "done_when": "The workstream, component, diagram, and validation proof agree.",
            }
            for index in range(1, 5)
        ],
        "coding_readiness_gates": [
            "The first path has accepted actors, state changes, and visible result.",
            "The component boundary identifies source files and proof ownership.",
            "The validation plan covers valid input, missing input, and replay.",
            "The excluded scope remains explicit before implementation begins.",
        ],
        "host_independent_paths": [
            {
                "path": f"Path {index}",
                "command": "./.odylith/bin/odylith validate plan-workstream-binding --repo-root .",
                "works_in": "Codex, Claude Code, and installed consumer repositories.",
                "use_when": "Use it before claiming the governed package is ready for source work.",
            }
            for index in range(1, 4)
        ],
    }


def _substantive_project_brief_record_text() -> str:
    return """# Permit Readiness Workspace Project Brief

- schema: odylith.greenfield.project_brief.v1
- origin: greenfield
- accepted_at: prewrite
- release: 0.0.1
- workstreams: 4
- components: 3
- diagrams: 4

## Brief
- outcome: Release 0.0.1 proves one accepted permit path where intake, evidence review, decision rationale, and readiness proof stay connected.
- principle: Keep every permit state transition tied to source evidence, reviewer ownership, blocked-path proof, and explicit release scope.

## Project Design Board
- Blueprint section 1: The accepted actor, state change, evidence source, and release boundary.
- Blueprint section 2: The accepted actor, state change, evidence source, and release boundary.
- Blueprint section 3: The accepted actor, state change, evidence source, and release boundary.
- Blueprint section 4: The accepted actor, state change, evidence source, and release boundary.

## Governance Package
- choose before coding:
  - Review depth: Keep the first release focused on one governed permit path.
  - Evidence scope: Preserve source evidence before adding additional routing.
- customize by saying:
  - Prioritize reviewer evidence before adding additional notification channels.
  - Keep the first release bounded to one permit path.
  - Treat missing evidence as a blocked path requiring explanation.
- coding readiness gates:
  - The first path has accepted actors, state changes, and visible result.
  - The component boundary identifies source files and proof ownership.
  - The validation plan covers valid input, missing input, and replay.
  - The excluded scope remains explicit before implementation begins.
"""


def _substantive_workstream_text(title: str) -> str:
    return f"""# {title}

## Problem
Permit staff need one reliable path from submitted evidence to a reviewable readiness decision.

## Customer
Review coordinators, permit operators, and evidence owners who must explain blocked or accepted permit states.

## Opportunity
Connect intake, evidence review, decision rationale, and release proof before implementation expands.

## Product View
The product helps an operator open the accepted permit path, review evidence, block missing inputs, and publish readiness proof.

## Success Metrics
- A valid permit request reaches a reviewable readiness decision with evidence, owner, and explanation.
- A missing evidence request stops before release movement and shows the recovery path.

## Validation
- Prove valid input, missing input, replay evidence, and source-boundary traceability before release.
"""


def _substantive_registry_spec(label: str) -> str:
    return f"""# {label}

> Planned from user intent. Source boundary: src/app/{label.casefold().replace(' ', '-')}. Trace links for {label}: workstreams B-001.

{label} owns one permit state transition, source evidence, reviewer explanation, and blocked-path recovery.

Successful path evidence for {label}: accepted permit input, reviewer decision, visible readiness result, and persisted explanation.
Blocked input evidence for {label}: missing or malformed evidence stops before a trusted result and records recovery guidance.
Replay evidence for {label}: actor, input facts, status, explanation, and proof trail remain reviewable.
"""


def _substantive_prompt(position: int, label: str) -> dict[str, str]:
    step_ids = {
        1: "choose_language",
        2: "create_plan",
        3: "build_slice",
        4: "prove_behavior",
        5: "refresh_governance",
    }
    base = {
        "step_id": step_ids.get(position, ""),
        "label": label,
        "when": "Use after accepting the governed permit readiness direction.",
        "position": str(position),
    }
    if position == 1:
        base.update(
            {
                "prompt": (
                    "From the accepted product direction, choose the runtime, test tool, source layout, and first "
                    "implementation boundary for the permit readiness path before writing source code."
                ),
                "result": "Runtime, test command, and source boundary are explicit.",
                "stop": "Stop if runtime or test proof cannot be named.",
            }
        )
    elif position == 2:
        base.update(
            {
                "prompt": (
                    "Plan the accepted first-release work item with source boundary, target files, proof gates for "
                    "reviewing permit evidence, validation commands, and excluded scope before implementation."
                ),
                "result": "A governed target and proof plan are ready.",
                "stop": "Stop if the plan omits source boundary, proof, validation, or excluded scope.",
            }
        )
    elif position == 3:
        base.update(
            {
                "prompt": (
                    "Implement the accepted first-release work item only in target files, build only the permit "
                    "readiness slice, add input validation, return a structured result, and preserve risk and excluded scope."
                ),
                "result": "Implemented behavior is bounded to the governed target.",
                "stop": "Stop if work expands outside the slice or loses structured proof.",
            }
        )
    elif position == 4:
        base.update(
            {
                "prompt": (
                    "Prove the accepted first-release work item with valid input, missing evidence, validation "
                    "commands, replay evidence, source-boundary traceability, visible result inspection, and "
                    "reviewer explanation before any release claim."
                ),
                "result": "Validation evidence covers accepted and blocked paths.",
                "stop": "Stop if validation fails or missing-input proof is absent.",
            }
        )
    else:
        base.update(
            {
                "prompt": (
                    "Refresh governed records for the accepted first-release work item after implemented behavior "
                    "passes validation, then link source proof, workstream evidence, component ownership, and "
                    "operator readiness back to the project artifacts."
                ),
                "result": "Governed records reflect implemented behavior and validation proof.",
                "stop": "Stop before claiming release readiness if governed records and source proof disagree.",
            }
        )
    return base


def _substantive_project_payload() -> dict[str, object]:
    return {
        "projection": {"origin": "accepted greenfield project"},
        "host_handoff_prompts": [
            _substantive_prompt(index, label)
            for index, label in enumerate(
                (
                    "Choose runtime and test harness",
                    "Create first implementation plan",
                    "Build smallest runnable slice",
                    "Prove accepted and blocked paths",
                    "Refresh governed records",
                ),
                start=1,
            )
        ],
    }


def _empty_governed_readback() -> SimpleNamespace:
    return SimpleNamespace(
        release_catalogs={},
        release_events={},
        program_records={},
        compass_records={},
        surface_payloads={},
    )


def _substantive_governed_readback() -> SimpleNamespace:
    return SimpleNamespace(
        release_catalogs={
            "odylith/radar/source/releases/releases.v1.json": {
                "version": "v1",
                "releases": [
                    {"release_id": "release-0-0-1", "version": "0.0.1", "status": "active"},
                ],
            }
        },
        release_events={
            "odylith/radar/source/releases/release-assignment-events.v1.jsonl": (
                {
                    "action": "add",
                    "recorded_at": "2026-06-30T12:00:00Z",
                    "release_id": "release-0-0-1",
                    "workstream_id": "B-001",
                },
            )
        },
        program_records={},
        compass_records={
            "odylith/compass/runtime/current.v1.json": {
                "version": "v1",
                "generated_utc": "2026-06-30T12:00:00Z",
                "sources": {"backlog_index": "odylith/radar/source/INDEX.md"},
            }
        },
        surface_payloads={
            "radar": {"entries": [{"id": f"B-00{index}"} for index in range(1, 5)]},
            "registry": {"components": [{"id": f"C{index}"} for index in range(1, 4)]},
            "atlas": {"diagrams": [{"id": f"D{index}"} for index in range(1, 5)]},
            "compass": {
                "runtime_json_href": "runtime/current.v1.json?v=1",
                "source_truth_href": "../compass-source-truth.v1.json?v=1",
            },
            "casebook": {"bugs": [], "counts": {"total": 0}},
            "tooling": {
                "radar_href": "radar/radar.html?v=1",
                "registry_href": "registry/registry.html?v=1",
                "atlas_href": "atlas/atlas.html?v=1",
                "compass_href": "compass/compass.html?v=1",
                "casebook_href": "casebook/casebook.html?v=1",
                "project_intelligence": _substantive_project_payload(),
                "surface_runtime_status": {"status": "ready"},
            },
        },
    )


def _substantive_package() -> SimpleNamespace:
    project_brief = _substantive_project_brief()
    source_launch = {
        "start_workstream_id": "B-001",
        "implementation_prompt": "Start B-001 from the accepted permit readiness model and prove valid, missing, replay, and source-boundary evidence.",
        "verification_commands": ["pytest tests/unit/test_permit.py", "./.odylith/bin/odylith validate plan-workstream-binding --repo-root ."],
        "coding_readiness_gates": [
            "Semantic contract accepted.",
            "Release boundary accepted.",
            "Proof commands identified.",
            "Excluded scope preserved.",
        ],
    }
    proposal = {
        "write_policy": "confirmed_intent_before_confirmed_create",
        "intent": {
            "reasoning_mode": "odylith_confirmed_governed_proposal",
            "title": "Permit Readiness Workspace",
            "state_object": "A permit request records submitted evidence, reviewer decision, blocked inputs, and readiness status.",
        },
        "semantic_model": {
            "first_path_contract": {
                "capability": "An operator submits permit evidence, reviewer checks it, and readiness proof is published.",
                "visible_result": "Permit readiness proof with reviewer decision and blocked-path evidence.",
                "events": [{"action": "submit"}, {"action": "review"}, {"action": "publish"}],
            },
            "domain_ontology": {
                "state_object": "Permit request",
                "proof_boundary": "Readiness proof is valid only when evidence, reviewer decision, and blocked-path replay are visible.",
                "internal_systems": [
                    "Permit Intake Register",
                    "Evidence Review Ledger",
                    "Readiness Proof Publisher",
                ],
                "external_systems": ["Municipal permit filing portal"],
            },
        },
        "backlog": [
            {
                "title": f"Permit readiness slice {index}",
                "success_metrics": [
                    "Accepted permit evidence reaches a reviewer decision with visible readiness proof.",
                    "Missing permit evidence stops before release movement and records recovery guidance.",
                ],
            }
            for index in range(1, 5)
        ],
        "components": [
            {"component_id": "permit-intake-register", "label": "Permit Intake Register Service", "release_scope": "first_path_required"},
            {"component_id": "evidence-review-ledger", "label": "Evidence Review Ledger Service", "release_scope": "first_path_required"},
            {"component_id": "readiness-proof-publisher", "label": "Readiness Proof Publisher", "release_scope": "first_path_required"},
        ],
        "diagrams": [{"title": f"Permit readiness diagram {index}"} for index in range(1, 5)],
        "assumptions": [
            {"tier": "user_intent", "statement": "Human reviewers keep final permit judgment."},
            {"tier": "user_intent", "statement": "Missing evidence blocks readiness until recovery is recorded."},
        ],
        "open_questions": [{"question": "Which permit evidence source is authoritative for the first release?"}],
        "project_brief": project_brief,
    }
    return SimpleNamespace(
        proposal=proposal,
        backlog_result={
            "idea_files": {f"B-00{index}.md": _substantive_workstream_text(f"Permit readiness slice {index}") for index in range(1, 5)},
            "backlog_index_text": "# Backlog Index\n\nB-001 through B-004 cover the accepted permit readiness path.\n",
            "validation_gate": {"status": "passed"},
        },
        rendered_component_specs={
            "Permit Intake Register Service": _substantive_registry_spec("Permit Intake Register Service"),
            "Evidence Review Ledger Service": _substantive_registry_spec("Evidence Review Ledger Service"),
            "Readiness Proof Publisher": _substantive_registry_spec("Readiness Proof Publisher"),
        },
        rendered_atlas_sources={
            f"permit-readiness-{index}.mmd": (
                "flowchart TD\n"
                '  intake["Permit intake"] --> review["Evidence review"]\n'
                '  review --> proof["Readiness proof"]\n'
            )
            for index in range(1, 5)
        },
        component_registry_preview=(
            {"component_id": "permit-intake-register", "validation_gate": {"status": "passed"}},
            {"component_id": "evidence-review-ledger", "validation_gate": {"status": "passed"}},
            {"component_id": "readiness-proof-publisher", "validation_gate": {"status": "passed"}},
        ),
        project_brief_preview=project_brief,
        project_brief_record_text=_substantive_project_brief_record_text(),
        accepted_project_preview={
            "validation_gate": {"visible_actors": _passing_visible_actors()},
            "source_launch": source_launch,
        },
        source_launch_readback=source_launch,
        project_dashboard_preview=_substantive_project_payload(),
        compass_memory_preview={},
        governed_readback=_substantive_governed_readback(),
        next_steps_preview={
            "start_workstream_id": "B-001",
            "implementation_prompt": "Start B-001 from the accepted permit readiness model and prove valid, missing, replay, and source-boundary evidence.",
            "verification_commands": ["pytest tests/unit/test_permit.py", "./.odylith/bin/odylith validate plan-workstream-binding --repo-root ."],
            "coding_readiness_gates": [
                "Semantic contract accepted.",
                "Release boundary accepted.",
                "Proof commands identified.",
                "Excluded scope preserved.",
            ],
            "operator_sequence": ["Review the project brief.", "Open B-001.", "Author the first technical plan."],
        },
        program_result={},
        prewrite_safety_preview={
            "status": "passed",
            "checks": {
                "validation_gate_passed": True,
                "release_target_dry_run": True,
                "release_assignment_dry_run": True,
            },
        },
        release_target_result={},
        release_assignment_result={},
        release_workstream_ids=("B-001",),
    )


def _full_counts(module) -> object:
    return module.GreenfieldArtifactCounts(
        radar_workstreams=4,
        registry_component_specs=3,
        atlas_mermaid_sources=4,
        compass_records=1,
        release_records=1,
        program_records=0,
        project_brief_records=1,
        trace_nodes=12,
        trace_workstreams=4,
        rendered_surfaces=len(module.REQUIRED_RENDERED_SURFACES),
        rendered_surface_payloads=len(_scoring_module().SURFACE_PAYLOAD_CONTRACTS) * 2,
        atlas_rendered_assets=8,
        domain_term_hits=3,
        project_implementation_prompts=5,
    )


def _passing_write_transaction() -> dict[str, object]:
    return {
        "status": "committed",
        "commit_only": True,
        "prewrite_clean_before_commit": True,
        "rollback_guard": "enabled",
        "product_create_transaction_hash": "a" * 64,
        "product_facts_sha256": "c" * 64,
        "repository_write_set_hash": "b" * 64,
    }


def _passing_transaction_summary() -> dict[str, object]:
    return {
        "transaction_hash": "a" * 64,
        "product_facts_sha256": "c" * 64,
        "repository_write_set_hash": "b" * 64,
    }


def _passing_manifest() -> dict[str, object]:
    return {
        "status": "passed",
        "validation_status": "passed",
        "issue_count": 0,
        "whole_project_elapsed_seconds": 20.0,
        "write_transaction": _passing_write_transaction(),
        "product_create_transaction": _passing_transaction_summary(),
        "quality_lenses": {
            "status": "passed",
            "lenses": {
                "product_manager": {"status": "passed"},
                "architect": {"status": "passed"},
                "engineer": {"status": "passed"},
                "domain_expert": {"status": "passed"},
            },
        },
    }


def _passing_create_payload() -> dict[str, object]:
    return {
        "commit_manifest": _passing_manifest(),
        "product_create_transaction": _passing_transaction_summary(),
        "validation_gate": {"visible_actors": _passing_visible_actors()},
        "post_confirm_navigation": {
            "project": "odylith/index.html?tab=project",
            "radar": "odylith/index.html?tab=radar",
            "registry": "odylith/index.html?tab=registry",
            "atlas": "odylith/index.html?tab=atlas",
            "compass": "odylith/index.html?tab=compass&date=live",
        },
    }


def _passing_create_payload_for_repo(repo_root: Path) -> dict[str, object]:
    payload = _passing_create_payload()
    transaction_hash = str(_passing_transaction_summary()["transaction_hash"])
    dashboard = (
        repo_root
        / ".odylith/runtime/greenfield/generations"
        / transaction_hash
        / "repository/odylith/index.html"
    ).resolve()
    compatibility_dashboard = (repo_root / "odylith/index.html").resolve()
    _write(dashboard, "<!doctype html><title>Reviewed generation</title>\n")
    _write(compatibility_dashboard, "<!doctype html><title>Current project</title>\n")
    navigation = dict(payload["post_confirm_navigation"])
    navigation.update(
        {
            "dashboard_path": str(dashboard),
            "project_url": f"{dashboard.as_uri()}?tab=project",
            "view_status": "reviewed_generation",
            "compatibility_dashboard_path": str(compatibility_dashboard),
            "generation_transaction_hash": transaction_hash,
        }
    )
    payload["post_confirm_navigation"] = navigation
    return payload


def _create_payload_with_manifest(manifest: dict[str, object]) -> dict[str, object]:
    return {
        "commit_manifest": manifest,
        "product_create_transaction": _passing_transaction_summary(),
    }


def _proposed_transaction_payload() -> dict[str, object]:
    transaction_hash = "a" * 64
    transaction_file = (
        f".odylith/runtime/greenfield/pending/{transaction_hash}/product-create-transaction.v1.json"
    )
    return {
        "mode": "product_create_transaction",
        "product_create_transaction": {"transaction_hash": transaction_hash},
        "transaction_file": transaction_file,
        "confirmation": {
            "command_rule": "Use exactly one hash-bound command: CONFIRM, EDIT, or REJECT.",
            "post_confirm_contract": (
                "CONFIRM commits only this hash-bound transaction; commit-only create verifies the hash, "
                "compiler receipt, and repo preconditions, writes only sealed bytes under the rollback "
                "guard, validates readback, and reports success or environment/IO failure."
            ),
            "choices": [
                {
                    "command": f"CONFIRM {transaction_hash}",
                    "description": "Commit this exact validated package now.",
                    "commit_command": (
                        "odylith greenfield create --repo-root . "
                        f"--transaction-file {transaction_file} --transaction-hash {transaction_hash} --confirm"
                    ),
                },
                {
                    "command": f"EDIT {transaction_hash} <corrections>",
                    "description": "Do not commit. Treat corrections as new evidence and rebuild the package.",
                },
                {
                    "command": f"REJECT {transaction_hash}",
                    "description": "Stop. No governed records are written.",
                },
            ],
        },
    }


def _write_compiled_transaction(repo_root: Path, proposal: dict[str, object]) -> None:
    transaction_file = repo_root / str(proposal["transaction_file"])
    transaction_hash = str(dict(proposal["product_create_transaction"])["transaction_hash"])
    transaction = {
        "transaction_hash": transaction_hash,
        "quality_manifest": {"status": "passed", "validation_status": "passed"},
        "proposal": {
            "intent": {
                "product_story": "Standard Project helps an operator complete one governed task.",
                "state_object": "A project record tracks task evidence and accepted status.",
                "first_path": "An operator submits one task and reviews the accepted result.",
                "proof_boundary": "The first release proves one accepted task with readback.",
                "human_actors": ["Operator: submits and reviews the task."],
            }
        },
        "intent_authority": {
            "product_facts_sha256": "c" * 64,
            "material_fields": {
                "first_path": {
                    "custody_state": "accepted_fact",
                    "entailment_relationship": "direct_product_claim",
                }
            },
        },
    }
    encoded = json.dumps(transaction, sort_keys=True).encode("utf-8")
    transaction_file.parent.mkdir(parents=True, exist_ok=True)
    transaction_file.write_bytes(encoded)
    compiler_receipt = {
        "transaction_hash": transaction_hash,
        "transaction_file_sha256": hashlib.sha256(encoded).hexdigest(),
    }
    transaction_file.with_name(transaction_file.name + ".compiler-receipt.v1.json").write_text(
        json.dumps(compiler_receipt, sort_keys=True),
        encoding="utf-8",
    )


def _clarification_payload() -> dict[str, object]:
    return {
        "mode": "clarification_required",
        "clarification": {
            "question": "What is the first complete task the product should help a person finish, and what result should they see?",
            "required_fields": ["first_path"],
        },
    }


def _passing_package_lens_report() -> dict[str, object]:
    return {
        "version": "greenfield-quality-lenses-v1",
        "status": "passed",
        "issues": [],
        "lenses": {
            "product_manager": {"status": "passed", "checks": []},
            "architect": {"status": "passed", "checks": []},
            "engineer": {"status": "passed", "checks": []},
            "domain_expert": {"status": "passed", "checks": []},
        },
    }


def test_collect_artifact_package_carries_prewrite_safety_evidence(tmp_path: Path) -> None:
    module = _module()

    package = module.collect_artifact_package(
        repo_root=tmp_path,
        create_payload={
            "prewrite_safety": {
                "status": "passed",
                "checks": {
                    "validation_gate_passed": True,
                    "release_target_dry_run": True,
                    "release_assignment_dry_run": True,
                },
            }
        },
    )

    assert package.prewrite_safety_preview["status"] == "passed"
    assert package.prewrite_safety_preview["checks"]["validation_gate_passed"] is True


def _passing_matrix_result(module) -> object:
    return module.GreenfieldMatrixResult(
        name="matrix case",
        status="passed",
        create_seconds=18.0,
        counts=_full_counts(module),
        quality=module.GreenfieldQualityVerdict(
            passed=True,
            issues=(),
            lenses={lens: True for lens in ("product_manager", "architect", "engineer", "domain_expert")},
            scores={dimension: 10 for dimension in module.QUALITY_SCORE_DIMENSIONS},  # noqa: SLF001
            score=10,
            score_explanation=("all brutal release-quality dimensions scored 10",),
        ),
        browser_surface_proof_attempted=True,
    )


def _passing_rescue_result(module) -> object:
    return module.GreenfieldRescueSmokeResult(
        status="passed",
        cli_create_seconds=44.0,
        counts=_full_counts(module),
        issues=(),
        manifest={"repair_tier": "rescue"},
    )


def _passing_natural_rescue_result(module) -> object:
    return module.GreenfieldRescueSmokeResult(
        status="passed",
        cli_create_seconds=64.0,
        counts=_full_counts(module),
        issues=(),
        manifest={"repair_tier": "rescue"},
        proof_scope="real_installed_structured_patch_plan_and_provider_failure_cases",
        natural_rescue_quality_proven=True,
        provider_failure_fallback_proven=True,
        provider_failure_observation={"proven": True},
    )


def test_standard_matrix_create_does_not_receive_internal_rescue_probe_env(monkeypatch, tmp_path: Path) -> None:
    module = _module()
    create_envs: list[dict[str, str]] = []
    monkeypatch.setattr(module, "collect_artifact_package", lambda **_kwargs: _substantive_package())
    monkeypatch.setattr(module, "collect_artifact_counts", lambda **_kwargs: _full_counts(module))
    monkeypatch.setattr(_scoring_module(), "greenfield_rendered_package_quality_issues", lambda _package: [])
    monkeypatch.setattr(_scoring_module(), "build_greenfield_quality_lens_report", lambda _package: _passing_package_lens_report())
    monkeypatch.setattr(module, "rendered_surface_health_issues", lambda **_kwargs: ())
    monkeypatch.setattr(module, "browser_surface_proof_issues", lambda **_kwargs: ())

    def fake_run(*, cwd, env, command, timeout):  # noqa: ANN001
        if "propose" in command:
            proposal = _proposed_transaction_payload()
            _write_compiled_transaction(cwd, proposal)
            return subprocess.CompletedProcess(command, 0, json.dumps(proposal), "")
        if "create" in command:
            create_envs.append(dict(env))
            payload = _passing_create_payload_for_repo(cwd)
            return subprocess.CompletedProcess(command, 0, json.dumps(payload), "")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(module, "_run", fake_run)

    result = module._run_case(  # noqa: SLF001
        case=module.GreenfieldMatrixCase(
            name="standard custody",
            prompt="Create a standard greenfield project.",
            required_terms=("standard", "project"),
        ),
            repo_root=tmp_path / "standard-repo",
            install_script=tmp_path / "install.sh",
            base_url="http://127.0.0.1:8123",
            version="0.1.15",
            include_browser_proof=True,
        )

    assert result.status == "passed"
    assert len(create_envs) == 1
    assert RESCUE_PROBE_ENV not in create_envs[0]


def test_standard_matrix_propose_compiles_before_hash_bound_create_without_rescue_probe(monkeypatch, tmp_path: Path) -> None:
    module = _module()
    commands: list[list[str]] = []
    create_envs: list[dict[str, str]] = []
    monkeypatch.setattr(module, "collect_artifact_package", lambda **_kwargs: _substantive_package())
    monkeypatch.setattr(module, "collect_artifact_counts", lambda **_kwargs: _full_counts(module))
    monkeypatch.setattr(_scoring_module(), "greenfield_rendered_package_quality_issues", lambda _package: [])
    monkeypatch.setattr(_scoring_module(), "build_greenfield_quality_lens_report", lambda _package: _passing_package_lens_report())
    monkeypatch.setattr(module, "rendered_surface_health_issues", lambda **_kwargs: ())
    monkeypatch.setattr(module, "browser_surface_proof_issues", lambda **_kwargs: ())

    def fake_run(*, cwd, env, command, timeout):  # noqa: ANN001
        commands.append(list(command))
        if "propose" in command:
            proposal = _proposed_transaction_payload()
            _write_compiled_transaction(cwd, proposal)
            return subprocess.CompletedProcess(command, 0, json.dumps(proposal), "")
        if "create" in command:
            create_envs.append(dict(env))
            payload = _passing_create_payload_for_repo(cwd)
            return subprocess.CompletedProcess(command, 0, json.dumps(payload), "")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(module, "_run", fake_run)

    result = module._run_case(  # noqa: SLF001
        case=module.GreenfieldMatrixCase(
            name="sparse standard",
            prompt="Create a sparse project whose report preserves its first-path evidence.",
            required_terms=("sparse", "project"),
        ),
            repo_root=tmp_path / "standard-repo",
            install_script=tmp_path / "install.sh",
            base_url="http://127.0.0.1:8123",
            version="0.1.15",
            include_browser_proof=True,
        )

    assert result.status == "passed"
    propose_index = next(index for index, command in enumerate(commands) if "propose" in command)
    create_index = next(index for index, command in enumerate(commands) if "create" in command)
    assert propose_index < create_index
    assert all("compile-transaction" not in command for command in commands)
    assert all("--intent-file" not in command for command in commands)
    create_command = commands[create_index]
    assert "--transaction-file" in create_command
    assert "--transaction-hash" in create_command
    assert "--confirm" in create_command
    assert "--prompt" not in create_command
    assert len(create_envs) == 1
    assert RESCUE_PROBE_ENV not in create_envs[0]
    assert result.evidence["preconfirm_dry_run"]["status"] == "compiled"
    assert result.evidence["preconfirm_dry_run"]["transaction_hash"] == "a" * 64


def test_explicit_clarification_expectation_passes_without_create_or_records(
    monkeypatch, tmp_path: Path
) -> None:
    module = _module()
    _stub_active_clarification_audit(monkeypatch, module)
    commands: list[list[str]] = []
    repo_root = tmp_path / "clarification-repo"

    def fake_run(*, cwd, env, command, timeout):  # noqa: ANN001
        commands.append(list(command))
        if "propose" in command:
            return subprocess.CompletedProcess(command, 0, json.dumps(_clarification_payload()), "")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(module, "_run", fake_run)

    result = module._run_case(  # noqa: SLF001
        case=module.GreenfieldMatrixCase(
            name="ambiguous cell therapy",
            prompt="Create a cell therapy proposal with several possible operating paths.",
            required_terms=("cell", "therapy"),
            expectation="clarification_required",
        ),
        repo_root=repo_root,
        install_script=tmp_path / "install.sh",
        base_url="http://127.0.0.1:8123",
        version="0.1.15",
    )

    assert result.status == "passed"
    assert result.quality.passed is True
    assert result.quality.score_basis == "clarification_required_no_write_contract"
    assert result.create_returncode == 0
    assert sum("propose" in command for command in commands) == 1
    assert not any(command[1:3] == ["greenfield", "create"] for command in commands)
    assert result.evidence["case"]["expectation"] == "clarification_required"
    assert result.evidence["clarification"] == {
        "mode": "clarification_required",
        "question": "What is the first complete task the product should help a person finish, and what result should they see?",
        "required_fields": ["first_path"],
        "returncode": 0,
    }
    assert result.evidence["no_write"]["changed_records"] == []
    assert result.evidence["no_write"]["staged_transaction_present"] is False
    assert result.evidence["no_write"]["write_audit_active"] is True
    assert result.evidence["no_write"]["write_attempts"] == []
    assert result.evidence["no_write"]["subprocess_attempts"] == []
    assert result.evidence["no_write"]["write_audit_error"] == ""
    assert not (repo_root / ".odylith/runtime/greenfield/pending").exists()
    assert not (repo_root / "odylith").exists()


def test_explicit_clarification_expectation_rejects_staged_transaction_record(
    monkeypatch, tmp_path: Path
) -> None:
    module = _module()
    _stub_active_clarification_audit(monkeypatch, module)
    commands: list[list[str]] = []
    repo_root = tmp_path / "clarification-repo"

    def fake_run(*, cwd, env, command, timeout):  # noqa: ANN001
        commands.append(list(command))
        if "propose" in command:
            _write(
                cwd
                / ".odylith/runtime/greenfield/pending"
                / ("a" * 64)
                / "product-create-transaction.v1.json",
                "unexpected staged transaction\n",
            )
            return subprocess.CompletedProcess(command, 0, json.dumps(_clarification_payload()), "")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(module, "_run", fake_run)

    result = module._run_case(  # noqa: SLF001
        case=module.GreenfieldMatrixCase(
            name="ambiguous cell therapy",
            prompt="Create a cell therapy proposal with several possible operating paths.",
            required_terms=("cell", "therapy"),
            expectation="clarification_required",
        ),
        repo_root=repo_root,
        install_script=tmp_path / "install.sh",
        base_url="http://127.0.0.1:8123",
        version="0.1.15",
    )

    assert result.status == "failed"
    assert result.quality.passed is False
    assert "clarification proposal created a staged transaction record" in result.quality.issues
    assert not any(command[1:3] == ["greenfield", "create"] for command in commands)


def test_explicit_clarification_expectation_rejects_extra_payload_fields(monkeypatch, tmp_path: Path) -> None:
    module = _module()
    _stub_active_clarification_audit(monkeypatch, module)

    def fake_run(*, cwd, env, command, timeout):  # noqa: ANN001
        if "propose" in command:
            payload = _clarification_payload()
            payload["intent_hypothesis"] = {"title": "must not leak"}
            return subprocess.CompletedProcess(command, 0, json.dumps(payload), "")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(module, "_run", fake_run)

    result = module._run_case(  # noqa: SLF001
        case=module.GreenfieldMatrixCase(
            name="ambiguous cell therapy",
            prompt="Create a cell therapy proposal with several possible operating paths.",
            required_terms=("cell", "therapy"),
            expectation="clarification_required",
        ),
        repo_root=tmp_path / "clarification-repo",
        install_script=tmp_path / "install.sh",
        base_url="http://127.0.0.1:8123",
        version="0.1.15",
    )

    assert result.status == "failed"
    assert "clarification proposal must contain only mode and clarification" in result.quality.issues


def test_explicit_clarification_expectation_rejects_reply_instruction_inside_question(monkeypatch, tmp_path: Path) -> None:
    module = _module()
    _stub_active_clarification_audit(monkeypatch, module)

    def fake_run(*, cwd, env, command, timeout):  # noqa: ANN001
        if "propose" in command:
            payload = _clarification_payload()
            payload["clarification"]["question"] = (
                "What is the first complete path a site coordinator follows? One sentence is enough."
            )
            return subprocess.CompletedProcess(command, 0, json.dumps(payload), "")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(module, "_run", fake_run)

    result = module._run_case(  # noqa: SLF001
        case=module.GreenfieldMatrixCase(
            name="ambiguous cell therapy",
            prompt="Create a cell therapy proposal with several possible operating paths.",
            required_terms=("cell", "therapy"),
            expectation="clarification_required",
        ),
        repo_root=tmp_path / "clarification-repo",
        install_script=tmp_path / "install.sh",
        base_url="http://127.0.0.1:8123",
        version="0.1.15",
    )

    assert result.status == "failed"
    assert "clarification payload must ask one focused question about the expected material fields" in result.quality.issues


def test_explicit_clarification_expectation_rejects_persisted_write_attempt(monkeypatch, tmp_path: Path) -> None:
    module = _module()
    _stub_active_clarification_audit(monkeypatch, module)
    repo_root = tmp_path / "clarification-repo"

    def fake_run(*, cwd, env, command, timeout):  # noqa: ANN001
        if "propose" in command:
            _write(cwd / "odylith/radar/source/workstreams.v1.json", "must not persist\n")
            return subprocess.CompletedProcess(command, 0, json.dumps(_clarification_payload()), "")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(module, "_run", fake_run)

    result = module._run_case(  # noqa: SLF001
        case=module.GreenfieldMatrixCase(
            name="ambiguous cell therapy",
            prompt="Create a cell therapy proposal with several possible operating paths.",
            required_terms=("cell", "therapy"),
            expectation="clarification_required",
        ),
        repo_root=repo_root,
        install_script=tmp_path / "install.sh",
        base_url="http://127.0.0.1:8123",
        version="0.1.15",
    )

    assert result.status == "failed"
    assert any("created or changed governed or staged records" in issue for issue in result.quality.issues)
    assert result.evidence["no_write"]["write_audit_active"] is True
    assert (repo_root / "odylith/radar/source/workstreams.v1.json").exists()


def test_explicit_clarification_expectation_requires_an_active_installed_write_audit(
    monkeypatch, tmp_path: Path
) -> None:
    module = _module()
    repo_root = tmp_path / "clarification-repo"
    _write(repo_root / ".odylith/bin/odylith", "#!/usr/bin/env bash\n")
    runtime_python = repo_root / ".odylith/runtime/current/bin/python"
    runtime_python.parent.mkdir(parents=True, exist_ok=True)
    runtime_python.symlink_to(sys.executable)

    def fake_run(*, cwd, env, command, timeout, pass_fds):  # noqa: ANN001
        assert pass_fds
        if "propose" in command:
            return subprocess.CompletedProcess(command, 0, json.dumps(_clarification_payload()), "")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(module, "_run", fake_run)

    result = module._run_case(  # noqa: SLF001
        case=module.GreenfieldMatrixCase(
            name="ambiguous cell therapy",
            prompt="Create a cell therapy proposal with several possible operating paths.",
            required_terms=("cell", "therapy"),
            expectation="clarification_required",
        ),
        repo_root=repo_root,
        install_script=tmp_path / "install.sh",
        base_url="http://127.0.0.1:8123",
        version="0.1.15",
        skip_install=True,
        require_write_audit=True,
    )

    assert result.status == "failed"
    assert "clarification proposal did not activate the installed write audit" in result.quality.issues
    assert result.evidence["no_write"]["write_audit_active"] is False
    assert result.evidence["no_write"]["write_audit_error"] == "installed write audit did not activate"


def test_explicit_clarification_expectation_cannot_opt_out_of_the_write_audit(tmp_path: Path) -> None:
    module = _module()
    repo_root = tmp_path / "clarification-repo"
    _write(repo_root / ".odylith/bin/odylith", "#!/usr/bin/env bash\n")

    with pytest.raises(ValueError, match="require the installed write audit"):
        module._run_case(  # noqa: SLF001
            case=module.GreenfieldMatrixCase(
                name="ambiguous cell therapy",
                prompt="Create a cell therapy proposal with several possible operating paths.",
                required_terms=("cell", "therapy"),
                expectation="clarification_required",
            ),
            repo_root=repo_root,
            install_script=tmp_path / "install.sh",
            base_url="http://127.0.0.1:8123",
            version="0.1.15",
            skip_install=True,
            require_write_audit=False,
        )


def test_release_proof_accepts_expected_clarification_cases(monkeypatch, tmp_path: Path) -> None:
    module = _module()
    dist_dir = tmp_path / "dist"
    _write(dist_dir / "install.sh", "#!/usr/bin/env bash\n")
    case = module.GreenfieldMatrixCase(
        name="ambiguous cell therapy",
        prompt="Create a cell therapy proposal with several possible operating paths.",
        required_terms=("cell", "therapy"),
        leakage_terms=("cell therapy",),
        expectation="clarification_required",
    )

    class Server:
        def shutdown(self) -> None:
            return None

        def server_close(self) -> None:
            return None

    policy_calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        module,
        "_raise_for_invalid_campaign_policy",
        lambda **kwargs: policy_calls.append(kwargs),
    )
    monkeypatch.setattr(module, "matrix_preflight_failures", lambda **_kwargs: ())
    monkeypatch.setattr(module, "_platform_baseline_required_terms", lambda **_kwargs: ())
    monkeypatch.setattr(module, "_serve_directory", lambda _release_dir: (Server(), "http://127.0.0.1:8123"))
    monkeypatch.setattr(module, "_with_case_platform_leakage_issues", lambda **kwargs: kwargs["result"])
    monkeypatch.setattr(module, "_cleanup_repo_before_next", lambda _repo_root: None)
    audit_flags: list[bool] = []

    def fake_run_case(**kwargs):  # noqa: ANN003
        audit_flags.append(kwargs["require_write_audit"])
        return _passing_matrix_result(module)

    monkeypatch.setattr(module, "_run_case", fake_run_case)

    results = module.run_matrix(
        dist_dir=dist_dir,
        version="0.1.15",
        temp_parent=tmp_path,
        cases=(case,),
        include_browser_proof=True,
        proof_tier="release",
    )

    assert len(results) == 1
    assert results[0].status == "passed"
    assert policy_calls and policy_calls[0]["config"].proof_tier == "release"
    assert audit_flags == [True]


def test_source_evidence_custody_rejects_raw_multiword_excerpt() -> None:
    module = _module()
    case = module.GreenfieldMatrixCase(
        name="source evidence custody",
        prompt="Create a product with an explicit user path.",
        required_terms=("product",),
        provenance=SimpleNamespace(
            corpus_tier="source_provenanced",
            source_excerpt="A private benchmark phrase must remain evidence only.",
        ),
    )

    issues = module._source_evidence_content_custody_issues(  # noqa: SLF001
        case=case,
        generated_text="The product repeats a private benchmark phrase must remain evidence only.",
    )

    assert issues == ("source evidence text leaked into product artifacts",)


def test_unannotated_clarification_stays_a_failed_transaction_expectation(monkeypatch, tmp_path: Path) -> None:
    module = _module()
    commands: list[list[str]] = []

    def fake_run(*, cwd, env, command, timeout):  # noqa: ANN001
        commands.append(list(command))
        if "propose" in command:
            return subprocess.CompletedProcess(command, 0, json.dumps(_clarification_payload()), "")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(module, "_run", fake_run)

    result = module._run_case(  # noqa: SLF001
        case=module.GreenfieldMatrixCase(
            name="unannotated ambiguity",
            prompt="Create a cell therapy proposal with several possible operating paths.",
            required_terms=("cell", "therapy"),
        ),
        repo_root=tmp_path / "transaction-repo",
        install_script=tmp_path / "install.sh",
        base_url="http://127.0.0.1:8123",
        version="0.1.15",
    )

    assert result.status == "failed"
    assert result.quality.passed is False
    assert result.create_returncode == 2
    assert result.failure_detail == "greenfield proposal requires a material clarification before compiling a transaction"
    assert json.loads(result.create_stdout_excerpt)["mode"] == "clarification_required"
    assert not any(command[1:3] == ["greenfield", "create"] for command in commands)


def test_rescue_smoke_create_receives_internal_probe_env(monkeypatch, tmp_path: Path) -> None:
    module = _module()
    create_envs: list[dict[str, str]] = []
    monkeypatch.setattr(module, "collect_artifact_package", lambda **_kwargs: _empty_package())
    monkeypatch.setattr(module, "collect_artifact_counts", lambda **_kwargs: _full_counts(module))
    monkeypatch.setattr(_scoring_module(), "greenfield_rendered_package_quality_issues", lambda _package: [])
    monkeypatch.setattr(_scoring_module(), "build_greenfield_quality_lens_report", lambda _package: _passing_package_lens_report())
    monkeypatch.setattr(module, "rendered_surface_health_issues", lambda **_kwargs: ())

    def fake_run(*, cwd, env, command, timeout):  # noqa: ANN001
        if "propose" in command:
            proposal = _proposed_transaction_payload()
            _write_compiled_transaction(cwd, proposal)
            return subprocess.CompletedProcess(command, 0, json.dumps(proposal), "")
        if "create" in command:
            create_envs.append(dict(env))
            manifest = _passing_manifest()
            manifest.update(
                {
                    "requested_repair_tier": "auto",
                    "repair_tier": "rescue",
                    "rescue_activated": True,
                    "budget_seconds": 90.0,
                    "passes": 2,
                    "repaired_issue_codes": ["preconfirm_rescue_probe"],
                }
            )
            payload = {"commit_manifest": manifest}
            return subprocess.CompletedProcess(command, 0, json.dumps(payload), "")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(module, "_run", fake_run)

    result = module._run_rescue_smoke_case(  # noqa: SLF001
        repo_root=tmp_path / "rescue-repo",
        install_script=tmp_path / "install.sh",
        base_url="http://127.0.0.1:8123",
        version="0.1.15",
    )

    assert result.status == "passed"
    assert len(create_envs) == 1
    assert create_envs[0][RESCUE_PROBE_ENV] == RESCUE_PROBE_TOKEN


def test_collect_artifact_package_excludes_guidance_from_radar_workstreams(tmp_path: Path) -> None:
    module = _module()
    _write(tmp_path / "odylith/radar/source/AGENTS.md", "Guidance that is not a generated workstream and may end with of.\n")
    _write(
        tmp_path / "odylith/radar/source/CLAUDE.md",
        "Companion host guidance that is not a generated workstream and mentions claudeonly.\n",
    )
    _write(
        tmp_path / "odylith/radar/source/ideas/B-001.md",
        "# Flood shelter intake\n\nCity staff register residents and prepare placement readiness evidence.\n",
    )
    _write(tmp_path / "odylith/radar/source/INDEX.md", "# Backlog Index\n\nRelease 0.0.1 includes B-001.\n")
    _write(
        tmp_path / "odylith/registry/source/components/intake/CURRENT_SPEC.md",
        "# Intake Service\n\nOwns resident intake, consent evidence, and placement readiness state.\n",
    )
    _write(tmp_path / "odylith/atlas/source/intake-flow.mmd", "flowchart TD\n  A[Resident intake] --> B[Placement readiness]\n")
    _write(
        tmp_path / "odylith/radar/traceability-graph.v1.json",
        json.dumps({"nodes": [{"id": str(index)} for index in range(12)], "workstreams": ["B-001", "B-002", "B-003", "B-004"]}),
    )
    _write(
        tmp_path / "odylith/radar/source/releases/releases.v1.json",
        json.dumps(
            {
                "version": "v1",
                "releases": [{"release_id": "release-0-0-1", "version": "0.0.1", "status": "active"}],
            }
        ),
    )
    _write(
        tmp_path / "odylith/radar/source/programs/B-001.execution-waves.v1.json",
        json.dumps(
            {
                "umbrella_id": "B-001",
                "waves": [
                    {
                        "wave_id": "W1",
                        "label": "First path",
                        "summary": "Prove the first governed path.",
                        "primary_workstreams": ["B-001"],
                    }
                ],
            }
        ),
    )
    _write(tmp_path / "odylith/runtime/source/accepted-project.v1.json", "{}\n")
    for surface in module.REQUIRED_RENDERED_SURFACES:
        _write(tmp_path / surface, "<html>ready</html>\n")
    _write(
        tmp_path / "odylith/compass/runtime/current.v1.json",
        json.dumps(
            {
                "version": "v1",
                "generated_utc": "2026-06-30T12:00:00Z",
                "sources": {"backlog_index": "odylith/radar/source/INDEX.md"},
            }
        ),
    )

    package = module.collect_artifact_package(repo_root=tmp_path, create_payload={})
    counts = module.collect_artifact_counts(
        repo_root=tmp_path,
        package=package,
        required_terms=("flood", "shelter", "resident", "placement", "claudeonly"),
    )

    assert "odylith/radar/source/AGENTS.md" not in package.backlog_result["idea_files"]
    assert "odylith/radar/source/CLAUDE.md" not in package.backlog_result["idea_files"]
    assert counts.radar_workstreams == 1
    assert counts.registry_component_specs == 1
    assert counts.atlas_mermaid_sources == 1
    assert counts.compass_records == 1
    assert counts.rendered_surfaces == len(module.REQUIRED_RENDERED_SURFACES)
    assert counts.domain_term_hits == 4


def test_collect_artifact_package_infers_release_workstream_ids_from_radar_readback(tmp_path: Path) -> None:
    module = _module()
    _write(
        tmp_path / "odylith/radar/source/ideas/B-123.md",
        "# First governed slice\n\n## Problem\nOperators need a governed path.\n",
    )
    _write(tmp_path / "odylith/radar/traceability-graph.v1.json", json.dumps({"nodes": [], "workstreams": []}))

    package = module.collect_artifact_package(repo_root=tmp_path, create_payload={})

    assert package.release_workstream_ids == ("B-123",)


def test_collect_artifact_counts_does_not_count_compass_shell_assets_as_records(tmp_path: Path) -> None:
    module = _module()
    package = _empty_package()
    _write(tmp_path / "odylith/compass/compass.html", "<html>Compass shell</html>\n")
    _write(tmp_path / "odylith/compass/compass-payload.v1.js", "window.__ODYLITH_COMPASS__ = {}\n")
    _write(tmp_path / "odylith/radar/traceability-graph.v1.json", json.dumps({"nodes": [], "workstreams": []}))

    shell_only = module.collect_artifact_counts(repo_root=tmp_path, package=package, required_terms=())
    assert shell_only.compass_records == 0

    _write(
        tmp_path / "odylith/compass/runtime/current.v1.json",
        json.dumps(
            {
                "version": "v1",
                "generated_utc": "2026-06-30T12:00:00Z",
                "sources": {"backlog_index": "odylith/radar/source/INDEX.md"},
            }
        ),
    )
    package = module.collect_artifact_package(repo_root=tmp_path, create_payload={})
    with_record = module.collect_artifact_counts(repo_root=tmp_path, package=package, required_terms=())
    assert with_record.compass_records == 1


def test_collect_artifact_counts_require_typed_release_and_compass_readback(tmp_path: Path) -> None:
    module = _module()
    package = _empty_package()
    _write(tmp_path / "odylith/radar/source/releases/AGENTS.md", "# Release guidance\n")
    _write(tmp_path / "odylith/radar/source/releases/releases.v1.json", "{}\n")
    _write(tmp_path / "odylith/radar/source/releases/release-assignment-events.v1.jsonl", '{"action":"add"}\n')
    _write(tmp_path / "odylith/compass/runtime/current.v1.json", "{}\n")
    _write(tmp_path / "odylith/radar/traceability-graph.v1.json", json.dumps({"nodes": [], "workstreams": []}))

    stale_counts = module.collect_artifact_counts(repo_root=tmp_path, package=package, required_terms=())

    assert stale_counts.release_records == 0
    assert stale_counts.program_records == 0
    assert stale_counts.compass_records == 0

    _write(
        tmp_path / "odylith/radar/source/releases/releases.v1.json",
        json.dumps(
            {
                "version": "v1",
                "releases": [{"release_id": "release-0-0-1", "version": "0.0.1", "status": "active"}],
            }
        ),
    )
    _write(
        tmp_path / "odylith/radar/source/releases/release-assignment-events.v1.jsonl",
        json.dumps(
            {
                "action": "add",
                "recorded_at": "2026-06-30T12:00:00Z",
                "release_id": "release-0-0-1",
                "workstream_id": "B-001",
            }
        )
        + "\n",
    )
    _write(
        tmp_path / "odylith/compass/runtime/current.v1.json",
        json.dumps({"version": "v1", "generated_utc": "2026-06-30T12:00:00Z", "sources": {}}),
    )
    package = module.collect_artifact_package(repo_root=tmp_path, create_payload={})
    valid_counts = module.collect_artifact_counts(repo_root=tmp_path, package=package, required_terms=())

    assert valid_counts.release_records == 2
    assert valid_counts.program_records == 0
    assert valid_counts.compass_records == 1


def test_collect_artifact_counts_excludes_runtime_custody_from_domain_terms(tmp_path: Path) -> None:
    module = _module()
    package = _empty_package()
    package.accepted_project_preview = {
        "source_launch": {
            "implementation_prompt": "Runtime-only zephyr lattice attestation evidence should not count."
        }
    }
    _write(tmp_path / "odylith/radar/traceability-graph.v1.json", json.dumps({"nodes": [], "workstreams": []}))

    counts = module.collect_artifact_counts(
        repo_root=tmp_path,
        package=package,
        required_terms=("zephyr", "lattice", "attestation"),
    )

    assert counts.domain_term_hits == 0


def test_source_evidence_custody_rejects_raw_identifier_in_product_artifacts() -> None:
    module = _module()
    source_case = SimpleNamespace(
        provenance=SimpleNamespace(corpus_tier="source_provenanced"),
        leakage_terms=("owner/evidence-repo",),
    )
    synthetic_case = SimpleNamespace(
        provenance=SimpleNamespace(corpus_tier="synthetic_regression"),
        leakage_terms=("owner/evidence-repo",),
    )

    assert module._source_evidence_custody_issues(  # noqa: SLF001
        case=source_case,
        generated_text="Owner evidence repo appears in the project brief.",
    ) == ("source evidence identifier leaked into product artifacts: `owner/evidence-repo`",)
    assert module._source_evidence_custody_issues(  # noqa: SLF001
        case=synthetic_case,
        generated_text="Owner evidence repo appears in the project brief.",
    ) == ()


def test_source_provenanced_candidates_detect_source_prose_after_identifier_redaction() -> None:
    module = _module()
    case = module.GreenfieldMatrixCase(
        name="accessibility source case",
        prompt=(
            "Create an accessibility product. An accessibility operator reviews one evidence item, "
            "records a decision, and verifies the visible outcome. Source repository: leongersen/noUiSlider. "
            "Source evidence: noUiSlider is a lightweight, ARIA-accessible JavaScript range slider. "
            "It also fits wonderfully in responsive designs and has no dependencies."
        ),
        required_terms=("accessibility",),
        leakage_terms=("leongersen/noUiSlider",),
        provenance=type(module.default_cases()[0].provenance)(corpus_tier="source_provenanced"),
    )

    terms = module._case_generated_leakage_terms(  # noqa: SLF001
        case=case,
        generated_text="The product description promises responsive designs for every review.",
    )

    assert "responsive designs" in terms
    assert "visible outcome" not in terms


def test_release_source_fixture_does_not_treat_first_path_copy_as_platform_leakage() -> None:
    module = _module()
    source_cases = module.load_case_file(
        REPO_ROOT / "tests/fixtures/greenfield-release-corpus/greenfield-release-source-provenanced.v3.json"
    )
    case = next(case for case in source_cases if case.case_id == "release-accessibility-001-description")

    typed_product_terms = module._case_generated_leakage_terms(  # noqa: SLF001
        case=case,
        generated_text="The product shows the visible outcome to reviewers.",
    )
    source_prose_terms = module._case_generated_leakage_terms(  # noqa: SLF001
        case=case,
        generated_text="Completely unstyled UI components remain in the product brief.",
    )

    assert typed_product_terms == ()
    assert "completely unstyled" in source_prose_terms


def test_run_case_fails_when_source_evidence_identifier_reaches_product_artifacts(
    monkeypatch,
    tmp_path: Path,
) -> None:
    module = _module()
    monkeypatch.setattr(module, "collect_artifact_package", lambda **_kwargs: _substantive_package())
    monkeypatch.setattr(module, "collect_artifact_counts", lambda **_kwargs: _full_counts(module))
    monkeypatch.setattr(module, "_generated_text", lambda **_kwargs: "owner/evidence-repo")
    monkeypatch.setattr(_scoring_module(), "greenfield_rendered_package_quality_issues", lambda _package: [])
    monkeypatch.setattr(_scoring_module(), "build_greenfield_quality_lens_report", lambda _package: _passing_package_lens_report())
    monkeypatch.setattr(module, "rendered_surface_health_issues", lambda **_kwargs: ())

    def fake_run(*, cwd, env, command, timeout):  # noqa: ANN001
        if "propose" in command:
            proposal = _proposed_transaction_payload()
            _write_compiled_transaction(cwd, proposal)
            return subprocess.CompletedProcess(command, 0, json.dumps(proposal), "")
        if "create" in command:
            return subprocess.CompletedProcess(command, 0, json.dumps(_passing_create_payload()), "")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(module, "_run", fake_run)

    result = module._run_case(  # noqa: SLF001
        case=module.GreenfieldMatrixCase(
            name="source custody",
            prompt="Create an accessibility project from untrusted source evidence.",
            required_terms=("accessibility",),
            leakage_terms=("owner/evidence-repo",),
            provenance=type(module.default_cases()[0].provenance)(corpus_tier="source_provenanced"),
        ),
        repo_root=tmp_path / "source-custody-repo",
        install_script=tmp_path / "install.sh",
        base_url="http://127.0.0.1:8123",
        version="0.1.15",
    )

    assert result.status == "failed"
    assert "source evidence identifier leaked into product artifacts: `owner/evidence-repo`" in result.quality.issues


def test_release_policy_rejects_missing_commit_recovery_proof() -> None:
    module = _module()
    config = SimpleNamespace(proof_tier="release", stop_after_failures=0, stop_after_cluster_failures=0)

    with pytest.raises(RuntimeError, match="must include installed commit recovery proof"):
        module._raise_for_invalid_campaign_policy(  # noqa: SLF001
            config=config,
            install_mode="full",
            include_browser_proof=True,
            include_rescue_smoke=True,
            include_natural_rescue_proof=True,
            include_commit_recovery_proof=False,
            allow_skipped_browser_proof=False,
        )


def test_release_policy_rejects_omitted_semantic_proof() -> None:
    module = _module()
    config = SimpleNamespace(proof_tier="release", stop_after_failures=0, stop_after_cluster_failures=0)

    with pytest.raises(RuntimeError, match="requires blinded semantic annotations"):
        module._raise_for_invalid_campaign_policy(  # noqa: SLF001
            config=config,
            install_mode="full",
            include_browser_proof=True,
            include_rescue_smoke=True,
            include_natural_rescue_proof=True,
            include_commit_recovery_proof=True,
            allow_skipped_browser_proof=False,
        )


def test_collect_artifact_counts_uses_token_aware_domain_terms(tmp_path: Path) -> None:
    module = _module()
    package = _empty_package()
    package.project_brief_record_text = "Portfolio readiness remains visible for review."
    _write(tmp_path / "odylith/radar/traceability-graph.v1.json", json.dumps({"nodes": [], "workstreams": []}))

    counts = module.collect_artifact_counts(repo_root=tmp_path, package=package, required_terms=("port",))

    assert counts.domain_term_hits == 0


def test_project_brief_record_count_excludes_runtime_custody_files(tmp_path: Path) -> None:
    module = _module()
    package = _empty_package()
    _write(tmp_path / "odylith/runtime/source/accepted-project.v1.json", "{}\n")
    _write(tmp_path / "odylith/radar/traceability-graph.v1.json", json.dumps({"nodes": [], "workstreams": []}))

    counts = module.collect_artifact_counts(repo_root=tmp_path, package=package, required_terms=())

    assert counts.project_brief_records == 0


def test_project_brief_record_count_requires_persisted_brief_source(tmp_path: Path) -> None:
    module = _module()
    package = _empty_package()
    package.project_brief_preview = _substantive_project_brief()
    _write(tmp_path / "odylith/radar/traceability-graph.v1.json", json.dumps({"nodes": [], "workstreams": []}))

    preview_only = module.collect_artifact_counts(repo_root=tmp_path, package=package, required_terms=())
    assert preview_only.project_brief_records == 0

    _write(tmp_path / "odylith/runtime/source/project-brief.v1.md", _substantive_project_brief_record_text())
    persisted = module.collect_artifact_counts(repo_root=tmp_path, package=package, required_terms=())
    assert persisted.project_brief_records == 1


def test_collect_artifact_package_keeps_project_brief_markdown_boundaries(tmp_path: Path) -> None:
    module = _module()
    project_brief = """# Film Festival Accessibility Screening Planner Project Brief

## Project Design Board
- First path: Programmers can publish accessible screening readiness
  - Why: A narrow first path keeps the first release testable and prevents broad platform drift.
"""
    _write(tmp_path / "odylith/runtime/source/project-brief.v1.md", project_brief)

    package = module.collect_artifact_package(repo_root=tmp_path, create_payload={})

    assert package.project_brief_record_text == project_brief
    assert not any(
        "coordinated modal grammar drift" in issue
        for issue in greenfield_rendered_package_quality_issues(package)
    )


def test_package_evidence_rejects_preview_only_project_brief() -> None:
    module = _module()
    package = _substantive_package()
    package.project_brief_record_text = ""

    findings = _package_evidence_module().package_evidence_findings(package)

    assert any("persisted project brief readback" in finding.message for finding in findings)


def test_package_evidence_prefers_accepted_source_launch_readback() -> None:
    module = _module()
    package = _substantive_package()
    package.next_steps_preview = {}
    package.source_launch_readback = dict(package.accepted_project_preview["source_launch"])

    findings = _package_evidence_module().package_evidence_findings(package)

    assert not any("accepted source-launch readback" in finding.message for finding in findings)
    assert not any("operator next steps" in finding.message for finding in findings)


def test_package_evidence_rejects_preview_only_source_launch() -> None:
    module = _module()
    package = _substantive_package()
    package.source_launch_readback = {}
    package.next_steps_preview = {
        "start_workstream_id": "B-001",
        "implementation_prompt": "Start B-001 from the accepted model.",
        "verification_commands": ["pytest", "./.odylith/bin/odylith validate plan-workstream-binding --repo-root ."],
        "coding_readiness_gates": ["One", "Two", "Three", "Four"],
    }

    findings = _package_evidence_module().package_evidence_findings(package)

    assert any("persisted accepted source-launch readback" in finding.message for finding in findings)


def test_package_evidence_rejects_stale_release_unexpected_program_and_surface_readback() -> None:
    module = _module()
    package = _substantive_package()
    stale = _substantive_governed_readback()
    stale.release_events = {
        "odylith/radar/source/releases/release-assignment-events.v1.jsonl": (
            {
                "action": "add",
                "recorded_at": "2026-06-30T12:00:00Z",
                "release_id": "release-0-0-1",
                "workstream_id": "B-999",
            },
        )
    }
    stale.program_records = {
        "odylith/radar/source/programs/B-999.execution-waves.v1.json": {
            "umbrella_id": "B-999",
            "waves": [
                {
                    "wave_id": "W1",
                    "label": "Unrelated path",
                    "summary": "This record belongs to another workstream.",
                    "primary_workstreams": ["B-999"],
                }
            ],
        }
    }
    stale.surface_payloads = {
        key: value for key, value in stale.surface_payloads.items() if key not in {"registry", "casebook"}
    }
    package.governed_readback = stale

    findings = _package_evidence_module().package_evidence_findings(package)
    messages = [finding.message for finding in findings]

    assert any("release assignment events do not cover workstream(s): B-001" in message for message in messages)
    assert any("Greenfield commit created unexpected Compass program record(s)" in message for message in messages)
    assert any("registry surface payload readback is missing or invalid" in message for message in messages)
    assert any("casebook surface payload readback is missing or invalid" in message for message in messages)


def test_governed_readback_rejects_malformed_program_artifacts(tmp_path: Path) -> None:
    relative = "odylith/radar/source/programs/B-001.execution-waves.v1.json"
    _write(tmp_path / relative, "{not valid JSON\n")

    module = _governed_readback_module()
    readback = module.collect_governed_readback(tmp_path)

    assert relative in readback.program_records
    assert ("engineer", "Greenfield commit created unexpected Compass program record(s)") in module.governed_readback_findings(readback)


def test_domain_readback_excludes_accepted_project_source_launch_runtime_text() -> None:
    module = _module()
    package = _empty_package()
    package.proposal = {
        "intent": {"state_object": "Zephyr lattice attestation queue"},
        "semantic_model": {
            "first_path_contract": {
                "capability": "Review zephyr lattice attestation evidence",
                "visible_result": "Zephyr lattice attestation readiness",
            },
            "domain_ontology": {
                "proof_boundary": "Zephyr lattice attestation proof stays reviewer-owned.",
                "external_systems": ["Zephyr lattice source"],
                "internal_systems": ["Attestation queue"],
            },
        },
    }
    package.accepted_project_preview = {
        "source_launch": {
            "implementation_prompt": "Zephyr lattice attestation evidence appears only inside runtime custody."
        },
        "validation_gate": {"visible_actors": _passing_visible_actors()},
    }

    findings = _package_evidence_module().package_evidence_findings(package)

    assert any(
        finding.dimension == "domain_expert" and "independent domain readback carried" in finding.message
        for finding in findings
    )


def test_domain_readback_requires_semantic_terms_on_each_major_surface() -> None:
    module = _module()
    package = _substantive_package()
    package.proposal["intent"]["state_object"] = "Zephyr lattice attestation queue."
    semantic = package.proposal["semantic_model"]
    semantic["first_path_contract"].update({"capability": "Review zephyr lattice attestation evidence", "visible_result": "Zephyr lattice attestation readiness"})
    semantic["domain_ontology"].update({"proof_boundary": "Zephyr lattice attestation proof is visible.", "internal_systems": ["Zephyr lattice attestation ledger"], "external_systems": ["Zephyr lattice source"]})
    package.backlog_result["idea_files"] = {
        key: f"{text}\nZephyr lattice attestation readiness stays reviewable.\n" for key, text in package.backlog_result["idea_files"].items()
    }
    package.rendered_atlas_sources = {
        key: 'flowchart TD\n  A["Zephyr lattice attestation"] --> B["Attestation readiness"]\n' for key in package.rendered_atlas_sources
    }
    package.project_dashboard_preview["host_handoff_prompts"] = [
        {**row, "prompt": f"{row['prompt']} Zephyr lattice attestation readiness."} for row in package.project_dashboard_preview["host_handoff_prompts"]
    ]
    generic_spec = "# Generic Component\n\nSource boundary and Trace links are present. Successful path evidence, Blocked input evidence, and Replay evidence are present. " + "Ownership keeps operators aligned with controls, logs, recovery, routing, status, and audit notes. " * 8
    package.rendered_component_specs = {key: generic_spec for key in package.rendered_component_specs}

    findings = _package_evidence_module().package_evidence_findings(package)

    assert any("semantic terms on Registry" in finding.message for finding in findings)


def test_collect_artifact_package_prefers_accepted_project_proposal_over_create_payload(tmp_path: Path) -> None:
    module = _module()
    _write(
        tmp_path / "odylith/runtime/source/accepted-project.v1.json",
        json.dumps(
            {
                "proposal": {
                    "intent": {"title": "Neonatal Transfer Coordination"},
                    "components": [
                        {
                            "component_id": "neonatal-transfer-intake-register",
                            "label": "Neonatal Transfer Intake Register Service",
                        }
                    ],
                }
            }
        )
        + "\n",
    )
    package = module.collect_artifact_package(
        repo_root=tmp_path,
        create_payload={"proposal": {"intent": {"title": "Uncommitted proposal"}, "components": []}},
    )

    assert package.proposal["intent"]["title"] == "Neonatal Transfer Coordination"
    assert package.proposal["components"][0]["label"] == "Neonatal Transfer Intake Register Service"


def test_collect_artifact_package_reads_project_prompts_from_persisted_tooling_payload(tmp_path: Path) -> None:
    module = _module()
    project_payload = _substantive_project_payload()
    project_payload["host_handoff_prompts"] = [
        {**row, "label": f"Persisted {index}", "prompt": f"Persisted prompt {index} binds source proof and governed workstream."}
        for index, row in enumerate(project_payload["host_handoff_prompts"], start=1)
    ]
    _write(
        tmp_path / "odylith/runtime/source/accepted-project.v1.json",
        json.dumps({"proposal": _substantive_package().proposal, "source_launch": {"start_workstream_id": "B-001"}})
        + "\n",
    )
    _write(
        tmp_path / "odylith/tooling-payload.v1.js",
        f'window["__ODYLITH_TOOLING_DATA__"] = {json.dumps({"project_intelligence": project_payload}, sort_keys=True)};\n',
    )

    package = module.collect_artifact_package(repo_root=tmp_path, create_payload={})

    prompts = package.project_dashboard_preview["host_handoff_prompts"]
    assert len(prompts) == 5
    assert prompts[0]["label"] == "Persisted 1"
    assert "Persisted prompt 5" in prompts[4]["prompt"]


def test_tooling_payload_reader_ignores_leading_js_braces_before_assignment(tmp_path: Path) -> None:
    module = _module()
    project_payload = _substantive_project_payload()
    _write(
        tmp_path / "odylith/tooling-payload.v1.js",
        "/* preamble { not the payload } */\n"
        f'window["__ODYLITH_TOOLING_DATA__"] = {json.dumps({"project_intelligence": project_payload}, sort_keys=True)};\n',
    )

    payload = module._read_tooling_payload(tmp_path)  # noqa: SLF001

    assert len(payload["project_intelligence"]["host_handoff_prompts"]) == 5


def test_tooling_payload_reader_resolves_simple_named_object_binding(tmp_path: Path) -> None:
    module = _module()
    project_payload = _substantive_project_payload()
    _write(
        tmp_path / "odylith/tooling-payload.v1.js",
        "const payload = "
        + json.dumps({"project_intelligence": project_payload}, sort_keys=True)
        + ';\nwindow["__ODYLITH_TOOLING_DATA__"] = payload;\n',
    )

    payload = module._read_tooling_payload(tmp_path)  # noqa: SLF001

    assert len(payload["project_intelligence"]["host_handoff_prompts"]) == 5


def test_matrix_preflight_failure_flushes_structured_incremental_telemetry(tmp_path: Path) -> None:
    module = _module()
    dist = tmp_path / "dist"
    dist.mkdir()
    _write(dist / "install.sh", "#!/usr/bin/env bash\nexit 0\n")
    output_json = tmp_path / "matrix.json"
    telemetry_jsonl = tmp_path / "matrix.jsonl"
    case = module.GreenfieldMatrixCase(
        name="preflight source case",
        prompt="Create a greenfield proposal for source case review.",
        required_terms=("missingterm",),
        leakage_terms=("source case sentinel",),
        stressors=("modal-expert-lens",),
    )

    results = module.run_matrix(
        dist_dir=dist,
        version="0.1.15",
        temp_parent=tmp_path,
        cases=(case,),
        telemetry_jsonl=telemetry_jsonl,
        incremental_output_json=output_json,
        proof_tier="discovery",
    )

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    events = [json.loads(line)["event"] for line in telemetry_jsonl.read_text(encoding="utf-8").splitlines()]

    assert results[0].status == "preflight_failed"
    assert payload["status"] == "failed"
    assert payload["campaign"]["completed_case_count"] == 1
    assert events[:2] == ["run_started", "preflight_failed"]
    assert "case_completed" in events
    assert "required terms are not grounded" in results[0].failure_detail


def test_browser_runtime_preflight_fails_before_final_holdout_claim(tmp_path: Path, monkeypatch) -> None:
    module = _module()
    dist = tmp_path / "dist"
    dist.mkdir()
    _write(dist / "install.sh", "#!/usr/bin/env bash\nexit 0\n")
    claimed = False

    def claim() -> None:
        nonlocal claimed
        claimed = True

    monkeypatch.setattr(
        module,
        "browser_runtime_preflight_issues",
        lambda: ("Playwright is unavailable for browser surface proof: ModuleNotFoundError",),
    )

    results = module.run_matrix(
        dist_dir=dist,
        version="0.1.15",
        temp_parent=tmp_path,
        cases=(module.default_cases()[0],),
        include_browser_proof=True,
        telemetry_jsonl=tmp_path / "matrix.jsonl",
        incremental_output_json=tmp_path / "matrix.json",
        proof_tier="discovery",
        before_product_execution=claim,
    )

    assert claimed is False
    assert len(results) == 1
    assert results[0].status == "preflight_failed"
    assert "Playwright is unavailable" in results[0].failure_detail


def test_package_evidence_rejects_missing_persisted_project_prompt_payload() -> None:
    module = _module()
    package = _substantive_package()
    package.project_dashboard_preview = {}

    findings = _package_evidence_module().package_evidence_findings(package)

    assert any("accepted Project readback does not expose five source-launch prompts" in finding.message for finding in findings)


def test_generated_leakage_terms_use_declared_sentinels_without_source_phrase_padding(tmp_path: Path) -> None:
    module = _module()
    package = _substantive_package()
    package.project_brief_record_text += "\nWafer lot and wafer xenobot attestation remain visible for review."
    case = module.GreenfieldMatrixCase(
        name="wafer xenobot",
        prompt="Create a proposal for wafer xenobot attestation with wafer lot and missing lattice phrase sentinels.",
        required_terms=("xenobot", "wafer", "attestation"),
        leakage_terms=("wafer lot", "missing lattice phrase"),
    )

    terms = module._case_generated_leakage_terms(  # noqa: SLF001
        case=case,
        generated_text=module._generated_text(repo_root=tmp_path, package=package),  # noqa: SLF001
    )

    assert "wafer lot" in terms
    assert "missing lattice phrase" not in terms
    assert "wafer xenobot attestation" not in terms
    assert "xenobot" not in terms
    assert "wafer" not in terms


def test_generated_leakage_terms_ignore_required_quality_anchors(tmp_path: Path) -> None:
    module = _module()
    package = _substantive_package()
    package.project_brief_record_text += "\nXenobot readiness remains visible for review."
    case = module.GreenfieldMatrixCase(
        name="protocol artifact sample",
        prompt="Create a proposal for protocol artifact sample review.",
        required_terms=("protocol", "artifact", "sample", "xenobot"),
        leakage_terms=("missing lattice phrase",),
    )

    terms = module._case_generated_leakage_terms(  # noqa: SLF001
        case=case,
        generated_text=module._generated_text(repo_root=tmp_path, package=package),  # noqa: SLF001
    )

    assert "protocol" not in terms
    assert "artifact" not in terms
    assert "sample" not in terms
    assert "xenobot" not in terms


def test_generated_leakage_terms_suppress_required_anchors_already_native_to_platform(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _module()
    package = _substantive_package()
    package.project_brief_record_text += "\nEstimate projection disputes stay visible for review."
    case = module.GreenfieldMatrixCase(
        name="estimate dispute",
        prompt="Create a proposal for estimate projection dispute review.",
        required_terms=("estimate", "projection"),
    )
    captured_terms: list[tuple[str, ...]] = []

    def fake_scan_platform_custody(*, repo_root: Path, dist_dir: Path, terms: tuple[str, ...]):
        captured_terms.append(terms)
        return tuple(
            module.platform_domain_leakage.LeakageFinding(
                location="src/odylith/runtime/common/cache_budget_policy.py",
                term=term,
                line=index,
            )
            for index, term in enumerate(terms, start=1)
        )

    monkeypatch.setattr(module.platform_domain_leakage, "scan_platform_custody", fake_scan_platform_custody)

    platform_baseline_terms = module._platform_baseline_required_terms(  # noqa: SLF001
        repo_root=module.REPO_ROOT,
        release_dir=tmp_path,
        cases=(case,),
    )
    terms = module._case_generated_leakage_terms(  # noqa: SLF001
        case=case,
        generated_text=module._generated_text(repo_root=tmp_path, package=package),  # noqa: SLF001
        platform_baseline_terms=platform_baseline_terms,
    )

    assert len(captured_terms) == 1
    assert "estimate projection" in captured_terms[0]
    assert "estimate projection" in platform_baseline_terms
    assert "estimate" not in terms
    assert "projection" not in terms


def test_generated_leakage_terms_fall_back_when_case_has_no_declared_sentinels(tmp_path: Path) -> None:
    module = _module()
    package = _substantive_package()
    package.project_brief_record_text += "\nXenobot culture readiness remains visible for review."
    case = module.GreenfieldMatrixCase(
        name="xenobot culture fallback",
        prompt="Create a proposal for xenobot culture review.",
        required_terms=("xenobot",),
    )

    terms = module._case_generated_leakage_terms(  # noqa: SLF001
        case=case,
        generated_text=module._generated_text(repo_root=tmp_path, package=package),  # noqa: SLF001
    )

    assert "xenobot culture" in terms
    assert "xenobot" not in terms


def test_platform_leakage_proof_summary_reports_cumulative_terms_and_issues() -> None:
    module = _module()
    result = _passing_matrix_result(module)
    result = module.GreenfieldMatrixResult(
        **{
            **result.to_dict(),
            "counts": result.counts,
            "quality": result.quality,
            "browser_surface_issues": tuple(result.browser_surface_issues),
            "platform_leakage_terms": ("zephyr attestation", "permit"),
            "platform_leakage_issues": ("platform domain leakage after generated artifact readback: src/x.py:1 leaked `permit`",),
        }
    )

    proof = module._platform_leakage_proof_summary((result,))  # noqa: SLF001

    assert proof["status"] == "failed"
    assert proof["term_count"] == 2
    assert "zephyr attestation" in proof["terms"]
    assert proof["issues"] == [
        "platform domain leakage after generated artifact readback: src/x.py:1 leaked `permit`"
    ]


def test_generated_leakage_scan_runs_once_for_result_union(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _module()
    first = _passing_matrix_result(module)
    first = module.GreenfieldMatrixResult(
        name="first",
        status=first.status,
        create_seconds=first.create_seconds,
        counts=first.counts,
        quality=first.quality,
        browser_surface_proof_attempted=True,
        platform_leakage_terms=("zephyr",),
    )
    second = _passing_matrix_result(module)
    second = module.GreenfieldMatrixResult(
        name="second",
        status=second.status,
        create_seconds=second.create_seconds,
        counts=second.counts,
        quality=second.quality,
        browser_surface_proof_attempted=True,
        platform_leakage_terms=("lattice",),
    )
    captured_terms: list[tuple[str, ...]] = []

    def fake_scan_platform_custody(*, repo_root: Path, dist_dir: Path, terms: tuple[str, ...]):
        captured_terms.append(terms)
        return (
            module.platform_domain_leakage.LeakageFinding(
                location="scripts/release/example.py",
                term="zephyr",
                line=7,
            ),
        )

    monkeypatch.setattr(module.platform_domain_leakage, "scan_platform_custody", fake_scan_platform_custody)

    results = module._with_platform_leakage_issues(  # noqa: SLF001
        repo_root=module.REPO_ROOT,
        results=(first, second),
        release_dir=tmp_path,
    )

    assert captured_terms == [("lattice", "zephyr")]
    assert results[0].status == "failed"
    assert results[0].quality.score == 0
    assert results[0].platform_leakage_issues == (
        "platform domain leakage after generated artifact readback: scripts/release/example.py:7 leaked `zephyr`",
    )
    assert results[1].status == "passed"
    assert results[1].platform_leakage_issues == ()


def test_matrix_result_serializes_retained_case_evidence() -> None:
    module = _module()
    result = _passing_matrix_result(module)
    result = module.GreenfieldMatrixResult(
        name=result.name,
        status=result.status,
        create_seconds=result.create_seconds,
        counts=result.counts,
        quality=result.quality,
        evidence={"case": {"id": "science-001"}, "artifacts": [{"sha256": "abc"}]},
    )

    payload = result.to_dict()

    assert payload["evidence"]["case"]["id"] == "science-001"
    assert payload["evidence"]["artifacts"][0]["sha256"] == "abc"


def test_case_file_loads_variance_metadata(tmp_path: Path) -> None:
    module = _module()
    case_file = tmp_path / "cases.json"
    case_file.write_text(
        json.dumps(
            {
                "cases": [
                    {
                        "case_id": "science-001",
                        "name": "rare assay workflow",
                        "prompt": "Create a proposal for rare assay workflow.",
                        "required_terms": ["assay"],
                        "leakage_terms": ["rare assay"],
                        "expectation": "clarification_required",
                        "tags": ["science", "regulated"],
                        "stressors": ["thin prompt", "specialized vocabulary"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    case = module.load_case_file(case_file)[0]

    assert case.case_id == "science-001"
    assert case.expectation == "clarification_required"
    assert case.tags == ("science", "regulated")
    assert case.stressors == ("thin prompt", "specialized vocabulary")
    assert case.source_file == str(case_file.resolve())


def test_case_file_rejects_duplicate_case_ids(tmp_path: Path) -> None:
    module = _module()
    case_file = tmp_path / "duplicate-cases.json"
    row = {
        "case_id": "duplicate-001",
        "name": "permit workflow",
        "prompt": "Create a proposal for a permit workflow.",
        "required_terms": ["permit"],
        "leakage_terms": ["permit workflow"],
    }
    case_file.write_text(json.dumps({"cases": [row, {**row, "name": "second permit workflow"}]}), encoding="utf-8")

    with pytest.raises(RuntimeError, match="duplicate case IDs: duplicate-001"):
        module.load_case_file(case_file)


def test_case_evidence_manifest_retains_artifact_hashes_and_grounding(tmp_path: Path) -> None:
    module = _module()
    install_script = tmp_path / "install.sh"
    _write(install_script, "#!/usr/bin/env bash\nexit 0\n")
    case = module.GreenfieldMatrixCase(
        name="permit readiness evidence",
        prompt="Create a permit readiness workspace.",
        required_terms=("permit", "readiness"),
        leakage_terms=("permit readiness",),
        case_id="permit-001",
        tags=("civic",),
        stressors=("evidence retention",),
    )
    quality = _passing_matrix_result(module).quality

    evidence = module._case_evidence_manifest(  # noqa: SLF001
        case=case,
        repo_root=tmp_path,
        package=_substantive_package(),
        create_payload=_passing_create_payload(),
        quality=quality,
        install_script=install_script,
        version="0.1.15",
        install_mode="seeded",
        browser_surface_proof_attempted=False,
        browser_surface_proof_required=False,
        browser_surface_issues=(),
    )

    assert evidence["case"]["id"] == "permit-001"
    assert len(evidence["case"]["prompt_sha256"]) == 64
    assert evidence["release"]["install_mode"] == "seeded"
    assert len(evidence["release"]["install_script_sha256"]) == 64
    assert evidence["artifacts"]
    assert all(len(artifact["sha256"]) == 64 for artifact in evidence["artifacts"])
    grounding = {row["term"]: row for row in evidence["required_term_grounding"]}
    assert grounding["permit"]["present"] is True
    assert grounding["readiness"]["present"] is True
    assert evidence["browser_surface_proof"]["required"] is False


def test_case_evidence_manifest_splits_scored_grounding_from_runtime_only_terms(tmp_path: Path) -> None:
    module = _module()
    install_script = tmp_path / "install.sh"
    _write(install_script, "#!/usr/bin/env bash\nexit 0\n")
    package = _substantive_package()
    package.accepted_project_preview = {"runtimeonly": "runtimeonly term remains only in accepted runtime state"}
    case = module.GreenfieldMatrixCase(
        name="runtime only term split",
        prompt="Create a permit readiness workspace with runtimeonly runtime evidence.",
        required_terms=("permit", "runtimeonly"),
        leakage_terms=("permit readiness",),
    )

    evidence = module._case_evidence_manifest(  # noqa: SLF001
        case=case,
        repo_root=tmp_path,
        package=package,
        create_payload=_passing_create_payload(),
        quality=_passing_matrix_result(module).quality,
        install_script=install_script,
        version="0.1.15",
        install_mode="seeded",
        browser_surface_proof_attempted=False,
        browser_surface_proof_required=False,
        browser_surface_issues=(),
    )

    all_grounding = {row["term"]: row for row in evidence["required_term_grounding"]}
    scored_grounding = {row["term"]: row for row in evidence["required_term_scored_grounding"]}

    assert all_grounding["runtimeonly"]["present"] is True
    assert all_grounding["runtimeonly"]["surfaces"] == ["Accepted project"]
    assert scored_grounding["runtimeonly"]["present"] is False
    assert any(
        "required term `runtimeonly` appears only outside scored generated artifacts" in row
        for row in evidence["required_term_distribution_findings"]
    )


def test_seeded_clone_reuses_runtime_without_copying_seed_git(tmp_path: Path) -> None:
    module = _module()
    seed = tmp_path / "seed"
    clone = tmp_path / "clone"
    _write(seed / ".odylith/bin/odylith", "#!/usr/bin/env bash\n")
    _write(seed / ".odylith/runtime/versions/0.1.15/bin/python", "#!/usr/bin/env bash\n")
    _write(seed / ".odylith/runtime/versions/0.1.15/runtime-metadata.json", "{}\n")
    _write(seed / "odylith/radar/source/B-001.md", "# Workstream\n")
    _write(seed / ".git/seed-marker", "do not copy\n")

    module._clone_seed_repo(seed_repo=seed, repo_root=clone, version="0.1.15")  # noqa: SLF001

    assert (clone / ".odylith/bin/odylith").is_file()
    assert (clone / "odylith/radar/source/B-001.md").read_text(encoding="utf-8") == "# Workstream\n"
    assert (clone / ".odylith/runtime/versions/0.1.15").is_symlink()
    assert (clone / ".odylith/runtime/versions/0.1.15").resolve() == (
        seed / ".odylith/runtime/versions/0.1.15"
    ).resolve()
    assert (clone / ".odylith/runtime/current").is_symlink()
    assert not (clone / ".git/seed-marker").exists()


def test_invalid_greenfield_matrix_install_mode_is_rejected() -> None:
    module = _module()

    with pytest.raises(RuntimeError, match="install mode"):
        module._validated_install_mode("partial")  # noqa: SLF001


def test_greenfield_create_times_only_hash_bound_commit_phase(monkeypatch, tmp_path: Path) -> None:
    module = _module()
    clock = {"seconds": 0.0}
    transaction_payload = _proposed_transaction_payload()
    _write_compiled_transaction(tmp_path, transaction_payload)
    proposed = SimpleNamespace(
        returncode=0,
        stdout=json.dumps(transaction_payload),
        stderr="",
    )
    created = SimpleNamespace(returncode=0, stdout="{}", stderr="")

    def fake_run(*, command, **_kwargs):
        if "propose" in command:
            clock["seconds"] += 69.0
            return proposed
        clock["seconds"] += 0.2
        return created

    monkeypatch.setattr(module, "_run", fake_run)
    monkeypatch.setattr(module.time, "perf_counter", lambda: clock["seconds"])
    transaction_evidence = importlib.import_module("greenfield_matrix_transaction_evidence")
    monkeypatch.setattr(transaction_evidence.time, "perf_counter", lambda: clock["seconds"])

    response, create_seconds = module._run_compiled_greenfield_create(  # noqa: SLF001
        repo_root=tmp_path,
        env={},
        prompt="Create a concise project.",
        timeout=120,
    )

    assert response is created
    assert create_seconds == 0.2


def test_greenfield_create_rejects_an_unexpected_proposal_mode_without_running_create(monkeypatch, tmp_path: Path) -> None:
    module = _module()
    stale_transaction = tmp_path / ".odylith/runtime/greenfield/product-create-transaction.v1.json"
    stale_transaction.parent.mkdir(parents=True)
    stale_transaction.write_text('{"transaction_hash":"stale"}\n', encoding="utf-8")
    proposed = SimpleNamespace(
        returncode=0,
        stdout=json.dumps(
            {
                "mode": "unexpected_success_mode",
                "product_create_transaction": {"transaction_hash": "stale"},
            }
        ),
        stderr="",
    )
    commands: list[list[str]] = []

    def fake_run(*, command, **_kwargs):  # noqa: ANN001
        commands.append(command)
        return proposed

    monkeypatch.setattr(module, "_run", fake_run)

    response, create_seconds = module._run_compiled_greenfield_create(  # noqa: SLF001
        repo_root=tmp_path,
        env={},
        prompt="Create a concise project.",
        timeout=120,
    )

    assert response.returncode == 2
    assert json.loads(response.stdout)["mode"] == "error"
    assert create_seconds == 0.0
    assert len(commands) == 1
    assert commands[0][1:3] == ["greenfield", "propose"]


def test_greenfield_create_retains_material_clarification_payload(monkeypatch, tmp_path: Path) -> None:
    module = _module()
    proposed = SimpleNamespace(
        returncode=0,
        stdout=json.dumps(
            {
                "mode": "clarification_required",
                "clarification": {
                    "question": "What is the first complete task the product should help a person finish?",
                    "required_fields": ["first_path"],
                },
            }
        ),
        stderr="",
    )

    monkeypatch.setattr(module, "_run", lambda **_kwargs: proposed)

    response, create_seconds = module._run_compiled_greenfield_create(  # noqa: SLF001
        repo_root=tmp_path,
        env={},
        prompt="Create a product with several possible operating paths.",
        timeout=120,
    )

    assert response.returncode == 2
    assert json.loads(response.stdout) == json.loads(proposed.stdout)
    assert response.stderr == "greenfield proposal requires a material clarification before compiling a transaction"
    assert create_seconds == 0.0


def test_quality_verdict_fails_closed_without_manifest_or_complete_artifacts() -> None:
    module = _module()

    verdict = module.build_quality_verdict(
        create_payload={},
        package=_empty_package(),
        counts=module.GreenfieldArtifactCounts(),
        create_returncode=0,
        create_seconds=61.0,
    )

    assert not verdict.passed
    assert verdict.score == 0
    assert verdict.scores["completion"] == 0
    assert "pre-confirm quality manifest missing" in verdict.issues
    assert "commit-only create exceeded 60s: 61.000s" in verdict.issues
    assert all(passed is False for passed in verdict.lenses.values())


def test_quality_verdict_retains_commit_only_failure_detail() -> None:
    module = _module()

    verdict = module.build_quality_verdict(
        create_payload={},
        package=_empty_package(),
        counts=module.GreenfieldArtifactCounts(),
        create_returncode=2,
        create_seconds=14.0,
        create_detail="greenfield pre-confirm completion failed with 1 issue: repeated canonical projection",
    )

    assert not verdict.passed
    assert (
        "commit-only create failure detail: greenfield pre-confirm completion failed with 1 issue: "
        "repeated canonical projection"
    ) in verdict.issues


def test_matrix_result_json_carries_bounded_failure_evidence() -> None:
    module = _module()

    result = module.GreenfieldMatrixResult(
        name="failed case",
        status="failed",
        create_seconds=14.0,
        counts=module.GreenfieldArtifactCounts(),
        quality=module.GreenfieldQualityVerdict(
            passed=False,
            issues=("commit-only create exited with code 2",),
            lenses={lens: False for lens in ("product_manager", "architect", "engineer", "domain_expert")},
            scores={dimension: 0 for dimension in module.QUALITY_SCORE_DIMENSIONS},  # noqa: SLF001
            score=0,
            score_explanation=("score forced to 0 because commit-only create did not commit governed records",),
        ),
        create_returncode=2,
        failure_detail="typed blocker",
        create_stdout_excerpt='{"error":"typed blocker"}',
        create_stderr_excerpt="",
    )

    payload = result.to_dict()

    assert payload["failure_detail"] == "typed blocker"
    assert payload["create_stdout_excerpt"] == '{"error":"typed blocker"}'


def test_matrix_result_json_keeps_passed_case_failure_evidence_empty() -> None:
    module = _module()

    payload = _passing_matrix_result(module).to_dict()

    assert payload["failure_detail"] == ""
    assert payload["create_stdout_excerpt"] == ""
    assert payload["create_stderr_excerpt"] == ""


def test_quality_verdict_requires_committed_write_transaction() -> None:
    module = _module()
    manifest = _passing_manifest()
    manifest["write_transaction"] = {"status": "not_started"}

    verdict = module.build_quality_verdict(
        create_payload=_create_payload_with_manifest(manifest),
        package=_empty_package(),
        counts=_full_counts(module),
        create_returncode=0,
        create_seconds=20.0,
    )

    assert not verdict.passed
    assert verdict.score == 0
    assert "commit-only write transaction was not committed" in verdict.issues
    assert verdict.lenses["engineer"] is False


@pytest.mark.parametrize(
    ("field", "value", "expected_issue"),
    (
        ("commit_only", False, "commit-only write transaction did not prove commit-only apply"),
        (
            "prewrite_clean_before_commit",
            False,
            "commit-only write transaction did not prove a clean prewrite package",
        ),
        ("rollback_guard", "disabled", "commit-only write transaction did not enable rollback"),
        (
            "product_create_transaction_hash",
            "",
            "commit-only write transaction is missing a valid ProductCreateTransaction hash",
        ),
        (
            "repository_write_set_hash",
            "",
            "commit-only write transaction is missing a valid repository write-set hash",
        ),
        (
            "product_create_transaction_hash",
            "c" * 64,
            "commit-only write transaction ProductCreateTransaction hash does not match the manifest summary",
        ),
        (
            "repository_write_set_hash",
            "d" * 64,
            "commit-only write transaction repository write-set hash does not match the manifest summary",
        ),
    ),
)
def test_quality_verdict_requires_commit_only_transaction_custody(
    field: str,
    value: object,
    expected_issue: str,
) -> None:
    module = _module()
    manifest = _passing_manifest()
    write_transaction = manifest["write_transaction"]
    assert isinstance(write_transaction, dict)
    write_transaction[field] = value

    verdict = module.build_quality_verdict(
        create_payload=_create_payload_with_manifest(manifest),
        package=_empty_package(),
        counts=_full_counts(module),
        create_returncode=0,
        create_seconds=20.0,
    )

    assert not verdict.passed
    assert expected_issue in verdict.issues


def test_quality_verdict_rejects_create_payload_transaction_hash_mismatch() -> None:
    module = _module()
    manifest = _passing_manifest()
    create_payload = _create_payload_with_manifest(manifest)
    transaction_summary = create_payload["product_create_transaction"]
    assert isinstance(transaction_summary, dict)
    transaction_summary["transaction_hash"] = "c" * 64

    verdict = module.build_quality_verdict(
        create_payload=create_payload,
        package=_empty_package(),
        counts=_full_counts(module),
        create_returncode=0,
        create_seconds=20.0,
    )

    assert not verdict.passed
    assert (
        "commit-only write transaction ProductCreateTransaction hash does not match the create payload summary"
        in verdict.issues
    )


@pytest.mark.parametrize("elapsed", (None, 0.0, -0.1, "not-a-number"))
def test_quality_verdict_requires_positive_measured_preconfirm_time(elapsed: object) -> None:
    module = _module()
    manifest = _passing_manifest()
    manifest["whole_project_elapsed_seconds"] = elapsed

    verdict = module.build_quality_verdict(
        create_payload=_create_payload_with_manifest(manifest),
        package=_empty_package(),
        counts=_full_counts(module),
        create_returncode=0,
        create_seconds=20.0,
    )

    assert not verdict.passed
    assert "pre-confirm manifest is missing a positive measured elapsed time" in verdict.issues


def test_quality_verdict_rejects_self_reported_manifest_without_package_readback(monkeypatch) -> None:
    module = _module()
    monkeypatch.setattr(_scoring_module(), "greenfield_rendered_package_quality_issues", lambda package: [])

    verdict = module.build_quality_verdict(
        create_payload=_passing_create_payload(),
        package=_empty_package(),
        counts=_full_counts(module),
        create_returncode=0,
        create_seconds=20.0,
    )

    assert not verdict.passed
    assert verdict.score == 0
    assert any(issue.startswith("quality lens product_manager") for issue in verdict.issues)
    assert all(passed is False for passed in verdict.lenses.values())


def test_quality_verdict_scores_premium_only_when_every_dimension_is_clean(monkeypatch) -> None:
    module = _module()
    monkeypatch.setattr(_scoring_module(), "greenfield_rendered_package_quality_issues", lambda package: [])
    monkeypatch.setattr(_scoring_module(), "build_greenfield_quality_lens_report", lambda _package: _passing_package_lens_report())

    verdict = module.build_quality_verdict(
        create_payload=_passing_create_payload(),
        package=_substantive_package(),
        counts=_full_counts(module),
        create_returncode=0,
        create_seconds=20.0,
    )

    assert verdict.passed
    assert verdict.score == 10
    assert all(score == 10 for score in verdict.scores.values())
    assert "all brutal release-quality dimensions scored 10" in verdict.score_explanation


def test_quality_verdict_rejects_scientific_package_missing_evidence_obligations(monkeypatch) -> None:
    module = _module()
    monkeypatch.setattr(_scoring_module(), "greenfield_rendered_package_quality_issues", lambda package: [])
    monkeypatch.setattr(_scoring_module(), "build_greenfield_quality_lens_report", lambda _package: _passing_package_lens_report())
    package = _substantive_package()
    package.proposal["semantic_model"]["evaluation_semantics"] = {
        "schema_version": "odylith.greenfield.evaluation_semantics.v1",
        "focus": "Assay Drift Prediction Model",
    }

    verdict = module.build_quality_verdict(
        create_payload=_passing_create_payload(),
        package=package,
        counts=_full_counts(module),
        create_returncode=0,
        create_seconds=20.0,
    )

    assert not verdict.passed
    assert verdict.scores["domain_expert"] == 0
    assert any("scientific/evaluation readback missing evidence obligation" in issue for issue in verdict.issues)


def test_quality_verdict_accepts_scientific_package_with_paraphrased_ir_evidence(monkeypatch) -> None:
    module = _module()
    monkeypatch.setattr(_scoring_module(), "greenfield_rendered_package_quality_issues", lambda package: [])
    monkeypatch.setattr(_scoring_module(), "build_greenfield_quality_lens_report", lambda _package: _passing_package_lens_report())
    package = _substantive_package()
    package.proposal["semantic_model"]["evaluation_semantics"] = {
        "schema_version": "odylith.greenfield.evaluation_semantics.v1",
        "focus": "Assay Drift Prediction Model",
        "method_or_protocol": "solver release identifier and analysis configuration used for the accepted run",
        "reference_or_baseline": "control-run comparator and expected range reviewed with the result",
        "uncertainty_or_tolerance": "error interval and acceptable range visible beside the result",
        "reproducibility": "identical source inputs, context, parameter set, and rerun ledger can regenerate the accepted result",
    }
    package.rendered_component_specs["Evidence Review Ledger Service"] += (
        "\n\nScientific review proof: the accepted run records the solver release identifier, "
        "analysis configuration, control-run comparator, expected range, error interval, "
        "acceptable range, identical source inputs, context, parameter set, and rerun ledger."
    )
    package.project_dashboard_preview["host_handoff_prompts"][0]["prompt"] += (
        " Preserve the solver release identifier, control-run comparator, error interval, "
        "acceptable range, parameter set, and rerun ledger in the governed implementation prompt."
    )

    verdict = module.build_quality_verdict(
        create_payload=_passing_create_payload(),
        package=package,
        counts=_full_counts(module),
        create_returncode=0,
        create_seconds=20.0,
    )

    assert verdict.passed
    assert verdict.score == 10
    assert verdict.scores["domain_expert"] == 10


def test_quality_verdict_rejects_scientific_package_with_evidence_concentrated_in_one_spec(monkeypatch) -> None:
    module = _module()
    monkeypatch.setattr(_scoring_module(), "greenfield_rendered_package_quality_issues", lambda package: [])
    monkeypatch.setattr(_scoring_module(), "build_greenfield_quality_lens_report", lambda _package: _passing_package_lens_report())
    package = _substantive_package()
    package.proposal["semantic_model"]["evaluation_semantics"] = {
        "schema_version": "odylith.greenfield.evaluation_semantics.v1",
        "focus": "Assay Drift Prediction Model",
        "method_or_protocol": "solver release identifier and analysis configuration used for the accepted run",
        "reference_or_baseline": "control-run comparator and expected range reviewed with the result",
        "uncertainty_or_tolerance": "error interval and acceptable range visible beside the result",
        "reproducibility": "identical source inputs, context, parameter set, and rerun ledger can regenerate the accepted result",
    }
    package.rendered_component_specs["Evidence Review Ledger Service"] += (
        "\n\nScientific review proof: the accepted run records the solver release identifier, "
        "analysis configuration, control-run comparator, expected range, error interval, "
        "acceptable range, identical source inputs, context, parameter set, and rerun ledger."
    )

    verdict = module.build_quality_verdict(
        create_payload=_passing_create_payload(),
        package=package,
        counts=_full_counts(module),
        create_returncode=0,
        create_seconds=20.0,
    )

    assert not verdict.passed
    assert verdict.scores["domain_expert"] == 0
    assert any("concentrates method, baseline, uncertainty, and reproducibility evidence" in issue for issue in verdict.issues)


def test_quality_verdict_rejects_unattempted_browser_surface_proof(monkeypatch) -> None:
    module = _module()
    monkeypatch.setattr(_scoring_module(), "greenfield_rendered_package_quality_issues", lambda package: [])
    monkeypatch.setattr(_scoring_module(), "build_greenfield_quality_lens_report", lambda _package: _passing_package_lens_report())

    verdict = module.build_quality_verdict(
        create_payload=_passing_create_payload(),
        package=_substantive_package(),
        counts=_full_counts(module),
        browser_surface_proof_attempted=False,
        create_returncode=0,
        create_seconds=20.0,
    )

    assert not verdict.passed
    assert verdict.score == 0
    assert verdict.scores["browser_surface_proof"] == 0
    assert verdict.scores["copy_semantic_clarity"] == 10
    assert "browser surface proof was not attempted; premium release scoring requires headless rendered-surface proof" in verdict.issues


def test_quality_verdict_rejects_missing_confirmation_or_success_navigation(monkeypatch) -> None:
    module = _module()
    monkeypatch.setattr(_scoring_module(), "greenfield_rendered_package_quality_issues", lambda package: [])
    monkeypatch.setattr(_scoring_module(), "build_greenfield_quality_lens_report", lambda _package: _passing_package_lens_report())

    verdict = module.build_quality_verdict(
        create_payload=_passing_create_payload(),
        package=_substantive_package(),
        counts=_full_counts(module),
        confirmation_ux_issues=("REJECT does not clearly promise no governed writes",),
        create_returncode=0,
        create_seconds=20.0,
    )

    assert not verdict.passed
    assert verdict.score == 0
    assert verdict.scores["confirmation_ux"] == 0
    assert "REJECT does not clearly promise no governed writes" in verdict.issues


def test_quality_verdict_allows_unattempted_browser_proof_for_volume_discovery(monkeypatch) -> None:
    module = _module()
    monkeypatch.setattr(_scoring_module(), "greenfield_rendered_package_quality_issues", lambda package: [])
    monkeypatch.setattr(_scoring_module(), "build_greenfield_quality_lens_report", lambda _package: _passing_package_lens_report())

    verdict = module.build_quality_verdict(
        create_payload=_passing_create_payload(),
        package=_substantive_package(),
        counts=_full_counts(module),
        browser_surface_proof_attempted=False,
        browser_surface_proof_required=False,
        create_returncode=0,
        create_seconds=20.0,
    )

    assert verdict.passed
    assert verdict.score == 10
    assert verdict.scores["browser_surface_proof"] == -1
    assert verdict.score_basis == "volume_discovery_without_browser_surface_proof"
    assert any("browser surface proof was not requested and is unscored" in line for line in verdict.score_explanation)
    assert "all brutal release-quality dimensions scored 10" not in verdict.score_explanation
    assert "browser surface proof was not attempted; premium release scoring requires headless rendered-surface proof" not in verdict.issues


def test_quality_verdict_rejects_failed_browser_surface_proof(monkeypatch) -> None:
    module = _module()
    monkeypatch.setattr(_scoring_module(), "greenfield_rendered_package_quality_issues", lambda package: [])
    monkeypatch.setattr(_scoring_module(), "build_greenfield_quality_lens_report", lambda _package: _passing_package_lens_report())

    verdict = module.build_quality_verdict(
        create_payload=_passing_create_payload(),
        package=_substantive_package(),
        counts=_full_counts(module),
        browser_surface_proof_attempted=True,
        browser_surface_proof_required=True,
        browser_surface_issues=("browser surface Radar rendered blank main content",),
        create_returncode=0,
        create_seconds=20.0,
    )

    assert not verdict.passed
    assert verdict.score == 0
    assert verdict.scores["browser_surface_proof"] == 0
    assert "browser surface Radar rendered blank main content" in verdict.issues


def test_quality_verdict_rejects_count_only_package_even_when_lenses_are_stubbed(monkeypatch) -> None:
    module = _module()
    monkeypatch.setattr(_scoring_module(), "greenfield_rendered_package_quality_issues", lambda package: [])
    monkeypatch.setattr(_scoring_module(), "build_greenfield_quality_lens_report", lambda _package: _passing_package_lens_report())

    verdict = module.build_quality_verdict(
        create_payload=_passing_create_payload(),
        package=_empty_package(),
        counts=_full_counts(module),
        create_returncode=0,
        create_seconds=20.0,
    )

    assert not verdict.passed
    assert verdict.score < 10
    assert verdict.scores["governance_depth"] == 0
    assert verdict.scores["operator_usefulness"] == 0
    assert verdict.scores["implementation_prompts"] == 0
    assert any("independent package evidence missing persisted project brief readback" in issue for issue in verdict.issues)
    assert any("independent Radar readback has only 0 workstream" in issue for issue in verdict.issues)


def test_quality_verdict_rejects_dry_run_only_prewrite_safety(monkeypatch) -> None:
    module = _module()
    monkeypatch.setattr(_scoring_module(), "greenfield_rendered_package_quality_issues", lambda package: [])
    monkeypatch.setattr(_scoring_module(), "build_greenfield_quality_lens_report", lambda _package: _passing_package_lens_report())
    package = _substantive_package()
    package.prewrite_safety_preview = {}

    verdict = module.build_quality_verdict(
        create_payload=_passing_create_payload(),
        package=package,
        counts=_full_counts(module),
        create_returncode=0,
        create_seconds=20.0,
    )

    assert not verdict.passed
    assert verdict.scores["engineer"] == 0
    assert "independent package evidence missing explicit prewrite safety checks" in verdict.issues


def test_quality_verdict_rejects_stub_atlas_diagrams(monkeypatch) -> None:
    module = _module()
    monkeypatch.setattr(_scoring_module(), "greenfield_rendered_package_quality_issues", lambda package: [])
    monkeypatch.setattr(_scoring_module(), "build_greenfield_quality_lens_report", lambda _package: _passing_package_lens_report())
    package = _substantive_package()
    package.rendered_atlas_sources = {f"stub-{index}.mmd": "flowchart TD\n  A[Placeholder]\n" for index in range(1, 5)}

    verdict = module.build_quality_verdict(
        create_payload=_passing_create_payload(),
        package=package,
        counts=_full_counts(module),
        create_returncode=0,
        create_seconds=20.0,
    )

    assert not verdict.passed
    assert verdict.scores["architect"] == 0
    assert any("has no visible topology edge" in issue for issue in verdict.issues)


def test_quality_verdict_rejects_collapsed_tribunal_judgment_roles(monkeypatch) -> None:
    module = _module()
    monkeypatch.setattr(_scoring_module(), "greenfield_rendered_package_quality_issues", lambda package: [])
    monkeypatch.setattr(_scoring_module(), "build_greenfield_quality_lens_report", lambda _package: _passing_package_lens_report())
    payload = _passing_create_payload()
    payload["validation_gate"] = {
        "visible_actors": [
            {
                "stable_role": role,
                "visible_actor": "Cross-Boundary Evidence Workspace proof reviewer",
            }
            for role in ("beneficiary_advocate", "domain_operator", "risk_owner", "evidence_owner")
        ]
    }

    verdict = module.build_quality_verdict(
        create_payload=payload,
        package=_empty_package(),
        counts=_full_counts(module),
        create_returncode=0,
        create_seconds=20.0,
    )

    assert not verdict.passed
    assert verdict.score < 10
    assert verdict.scores["copy_semantic_clarity"] < 10
    assert any("collapse distinct judgment roles" in issue for issue in verdict.issues)


def test_quality_verdict_rejects_persisted_actor_readback_drift(monkeypatch) -> None:
    module = _module()
    monkeypatch.setattr(_scoring_module(), "greenfield_rendered_package_quality_issues", lambda package: [])
    monkeypatch.setattr(_scoring_module(), "build_greenfield_quality_lens_report", lambda _package: _passing_package_lens_report())
    package = _empty_package()
    package.accepted_project_preview = {
        "validation_gate": {
            "visible_actors": [
                {
                    "stable_role": role,
                    "visible_actor": "Cross-Boundary Evidence Workspace proof reviewer",
                    "actor_source": "generated_role_projection",
                }
                for role in ("beneficiary_advocate", "domain_operator", "risk_owner", "evidence_owner")
            ]
        }
    }

    verdict = module.build_quality_verdict(
        create_payload=_passing_create_payload(),
        package=package,
        counts=_full_counts(module),
        create_returncode=0,
        create_seconds=20.0,
    )

    assert not verdict.passed
    assert verdict.score < 10
    assert any("accepted-project readback" in issue and "collapse distinct judgment roles" in issue for issue in verdict.issues)
    assert any("drifted from create payload" in issue for issue in verdict.issues)


def test_quality_verdict_requires_create_payload_actor_evidence(monkeypatch) -> None:
    module = _module()
    monkeypatch.setattr(_scoring_module(), "greenfield_rendered_package_quality_issues", lambda package: [])
    monkeypatch.setattr(_scoring_module(), "build_greenfield_quality_lens_report", lambda _package: _passing_package_lens_report())
    payload = _passing_create_payload()
    payload["validation_gate"] = {}

    verdict = module.build_quality_verdict(
        create_payload=payload,
        package=_empty_package(),
        counts=_full_counts(module),
        create_returncode=0,
        create_seconds=20.0,
    )

    assert not verdict.passed
    assert verdict.score < 10
    assert "create payload validation gate visible actors missing" in verdict.issues


def test_quality_verdict_caps_score_when_rendered_artifacts_have_copy_findings(monkeypatch) -> None:
    module = _module()
    monkeypatch.setattr(
        _scoring_module(),
        "greenfield_rendered_package_quality_issues",
        lambda package: ["Radar workstream has clipped copy", "Registry spec repeats generic copy"],
    )
    monkeypatch.setattr(_scoring_module(), "build_greenfield_quality_lens_report", lambda _package: _passing_package_lens_report())

    verdict = module.build_quality_verdict(
        create_payload=_passing_create_payload(),
        package=_substantive_package(),
        counts=_full_counts(module),
        create_returncode=0,
        create_seconds=20.0,
    )

    assert not verdict.passed
    assert verdict.score == 6
    assert verdict.scores["copy_semantic_clarity"] == 6
    assert any("cap release score at 6" in explanation for explanation in verdict.score_explanation)


def test_quality_verdict_rejects_project_implementation_prompt_findings(monkeypatch) -> None:
    module = _module()
    monkeypatch.setattr(
        _scoring_module(),
        "greenfield_rendered_package_quality_issues",
        lambda package: ["Project implementation prompt `Build smallest runnable slice` does not bind implementation to a governed workstream"],
    )
    monkeypatch.setattr(_scoring_module(), "build_greenfield_quality_lens_report", lambda _package: _passing_package_lens_report())

    verdict = module.build_quality_verdict(
        create_payload=_passing_create_payload(),
        package=_empty_package(),
        counts=_full_counts(module),
        create_returncode=0,
        create_seconds=20.0,
    )

    assert not verdict.passed
    assert verdict.score == 0
    assert verdict.scores["implementation_prompts"] == 0
    assert any("Project implementation prompt findings cap release score at 4" in explanation for explanation in verdict.score_explanation)


def test_rescue_cli_issues_allow_committed_rescue_under_90s(monkeypatch) -> None:
    module = _module()
    manifest = _passing_manifest()
    manifest.update(
        {
            "requested_repair_tier": "auto",
            "repair_tier": "rescue",
            "rescue_activated": True,
            "budget_seconds": 90.0,
            "whole_project_elapsed_seconds": 74.5,
            "passes": 2,
            "repaired_issue_codes": ["preconfirm_rescue_probe"],
        }
    )
    monkeypatch.setattr(module, "greenfield_rendered_package_quality_issues", lambda package: [])

    issues = module.rescue_cli_issues(
        manifest=manifest,
        package=_empty_package(),
        counts=_full_counts(module),
        count_minimums=_scoring_module().required_count_minimums(),  # noqa: SLF001
        count_key=_scoring_module().count_key,  # noqa: SLF001
        write_transaction_issues=_scoring_module().write_transaction_custody_issues,  # noqa: SLF001
        as_mapping=module._as_mapping,  # noqa: SLF001
        package_quality_issues=module.greenfield_rendered_package_quality_issues,
        create_returncode=0,
        create_seconds=74.5,
        detail="",
        expected_requested_tier="auto",
    )

    assert issues == ()


def test_rescue_cli_issues_report_specific_commit_only_custody_failure() -> None:
    module = _module()
    manifest = _passing_manifest()
    manifest.update(
        {
            "requested_repair_tier": "auto",
            "repair_tier": "rescue",
            "rescue_activated": True,
            "budget_seconds": 90.0,
            "whole_project_elapsed_seconds": 74.5,
            "passes": 2,
            "repaired_issue_codes": ["preconfirm_rescue_probe"],
        }
    )
    write_transaction = manifest["write_transaction"]
    assert isinstance(write_transaction, dict)
    write_transaction["commit_only"] = False

    issues = module.rescue_cli_issues(
        manifest=manifest,
        package=_empty_package(),
        counts=_full_counts(module),
        count_minimums=_scoring_module().required_count_minimums(),  # noqa: SLF001
        count_key=_scoring_module().count_key,  # noqa: SLF001
        write_transaction_issues=_scoring_module().write_transaction_custody_issues,  # noqa: SLF001
        as_mapping=module._as_mapping,  # noqa: SLF001
        package_quality_issues=lambda _package: [],
        create_returncode=0,
        create_seconds=74.5,
        detail="",
        expected_requested_tier="auto",
    )

    assert "auto-rescue write transaction did not prove commit-only apply" in issues
    assert "auto-rescue write transaction was not committed" not in issues


def test_rescue_cli_issues_require_auto_escalation() -> None:
    module = _module()

    issues = module.rescue_cli_issues(
        manifest={
            "status": "passed",
            "validation_status": "passed",
            "requested_repair_tier": "auto",
            "repair_tier": "standard",
            "rescue_activated": False,
            "budget_seconds": 60.0,
            "passes": 1,
            "issue_count": 0,
            "repaired_issue_codes": [],
            "write_transaction": _passing_write_transaction(),
            "whole_project_elapsed_seconds": 30.0,
            "quality_lenses": {"status": "passed"},
        },
        package=_empty_package(),
        counts=_full_counts(module),
        count_minimums=_scoring_module().required_count_minimums(),  # noqa: SLF001
        count_key=_scoring_module().count_key,  # noqa: SLF001
        write_transaction_issues=_scoring_module().write_transaction_custody_issues,  # noqa: SLF001
        as_mapping=module._as_mapping,  # noqa: SLF001
        package_quality_issues=lambda _package: [],
        create_returncode=0,
        create_seconds=30.0,
        detail="",
        expected_requested_tier="auto",
    )

    assert "auto-rescue manifest active tier is 'standard'" in issues
    assert "auto-rescue manifest did not mark rescue_activated" in issues
    assert "auto-rescue manifest did not record a repair pass after the injected typed failure" in issues
    assert "auto-rescue manifest did not record repaired issue `preconfirm_rescue_probe`" in issues


def test_quality_verdict_requires_all_case_domain_terms() -> None:
    module = _module()
    counts = module.GreenfieldArtifactCounts(
        radar_workstreams=4,
        registry_component_specs=3,
        atlas_mermaid_sources=4,
        compass_records=1,
        release_records=1,
        program_records=0,
        project_brief_records=1,
        trace_nodes=12,
        trace_workstreams=4,
        rendered_surfaces=len(module.REQUIRED_RENDERED_SURFACES),
        rendered_surface_payloads=len(_scoring_module().SURFACE_PAYLOAD_CONTRACTS) * 2,
        atlas_rendered_assets=8,
        domain_term_hits=3,
        required_domain_terms=4,
        project_implementation_prompts=5,
    )
    quality = module.build_quality_verdict(
        create_payload=_passing_create_payload(),
        package=_substantive_package(),
        counts=counts,
        create_returncode=0,
        create_seconds=20.0,
    )

    assert not quality.passed
    assert quality.scores["domain_expert"] == 0
    assert "domain term coverage too low: expected at least 4, found 3" in quality.issues


def test_quality_verdict_accepts_sparse_case_when_all_declared_domain_terms_survive(monkeypatch) -> None:
    module = _module()
    monkeypatch.setattr(_scoring_module(), "greenfield_rendered_package_quality_issues", lambda package: [])
    monkeypatch.setattr(_scoring_module(), "build_greenfield_quality_lens_report", lambda _package: _passing_package_lens_report())
    counts = module.GreenfieldArtifactCounts(
        radar_workstreams=4,
        registry_component_specs=3,
        atlas_mermaid_sources=4,
        compass_records=1,
        release_records=1,
        program_records=0,
        project_brief_records=1,
        trace_nodes=12,
        trace_workstreams=4,
        rendered_surfaces=len(module.REQUIRED_RENDERED_SURFACES),
        rendered_surface_payloads=len(_scoring_module().SURFACE_PAYLOAD_CONTRACTS) * 2,
        atlas_rendered_assets=8,
        domain_term_hits=2,
        required_domain_terms=2,
        project_implementation_prompts=5,
    )
    quality = module.build_quality_verdict(
        create_payload=_passing_create_payload(),
        package=_substantive_package(),
        counts=counts,
        create_returncode=0,
        create_seconds=20.0,
    )

    assert quality.passed
    assert quality.scores["domain_expert"] == 10
    assert "domain term coverage too low: expected at least 3, found 2" not in quality.issues


def test_rendered_surface_health_requires_payload_assets_and_shell_contract(tmp_path: Path) -> None:
    module = _module()
    for relative, assets in _scoring_module().SURFACE_PAYLOAD_CONTRACTS.items():
        body = "\n".join(f'<script src="{asset}?v=123"></script>' for asset in assets)
        _write(tmp_path / relative, f"<!doctype html><html><head>{body}</head><body>ready</body></html>")
        for asset in assets:
            _write(tmp_path / Path(relative).parent / asset, "window.__payload = true;\n")
    shell_payload = {
        payload_key: f"{expected_href}?v=123"
        for _tab, (_frame_id, payload_key, expected_href) in module.INDEX_SHELL_TAB_CONTRACTS.items()
    }
    shell_payload["project_intelligence"] = _substantive_project_payload()
    _write(
        tmp_path / "odylith/tooling-payload.v1.js",
        f'window["__ODYLITH_TOOLING_DATA__"] = {json.dumps(shell_payload, sort_keys=True)};\n',
    )
    tab_markup = "\n".join(
        [
            '<button type="button" data-tab="project" role="tab">project</button>',
            *(
                f'<button type="button" data-tab="{tab}" role="tab">{tab}</button>'
                for tab in module.INDEX_SHELL_TAB_CONTRACTS
            ),
        ]
    )
    frame_markup = "\n".join(
        f'<iframe id="{frame_id}"></iframe>'
        for frame_id, _payload_key, _expected_href in module.INDEX_SHELL_TAB_CONTRACTS.values()
    )
    _write(
        tmp_path / "odylith/index.html",
        "\n".join(
            (
                '<script id="toolingDashboardData" src="tooling-payload.v1.js?v=123"></script>',
                '<script src="tooling-app.v1.js?v=123"></script>',
                tab_markup,
                frame_markup,
            )
        ),
    )
    _write(tmp_path / "odylith/atlas/source/sample-flow.mmd", "flowchart TD\n  A[Start] --> B[Done]\n")
    _write(tmp_path / "odylith/atlas/source/sample-flow.svg", "<svg></svg>\n")
    _write(tmp_path / "odylith/atlas/source/sample-flow.png", "png bytes\n")

    assert module.rendered_surface_health_issues(repo_root=tmp_path) == ()

    (tmp_path / "odylith/radar/radar.html").write_text(
        (
            '<script src="stale/backlog-app.v1.js"></script>\n'
            '<script src="backlog-payload.v1.js"></script>\n'
        ),
        encoding="utf-8",
    )
    (tmp_path / "odylith/tooling-payload.v1.js").write_text(
        f"window.__WRONG_TOOLING_DATA__ = {json.dumps(shell_payload, sort_keys=True)};\n",
        encoding="utf-8",
    )
    (tmp_path / "odylith/registry/registry-payload.v1.js").unlink()
    (tmp_path / "odylith/atlas/source/sample-flow.png").unlink()
    (tmp_path / "odylith/index.html").write_text(
        "\n".join(
            (
                '<script id="toolingDashboardData" src="tooling-payload.v1.js?v=123"></script>',
                '<script src="tooling-app.v1.js?v=123"></script>',
                '<img src="surfaces/brand/lockup/odylith-lockup-horizontal.svg" alt="Odylith" />',
                '<button type="button" data-tab="radar" role="tab">radar</button>',
                '<iframe id="frame-radar"></iframe>',
            )
        ),
        encoding="utf-8",
    )

    issues = module.rendered_surface_health_issues(repo_root=tmp_path)

    assert "rendered surface odylith/radar/radar.html does not load backlog-app.v1.js" in issues
    assert (
        "rendered surface odylith/index.html references missing local asset "
        "surfaces/brand/lockup/odylith-lockup-horizontal.svg"
    ) in issues
    assert "rendered surface payload odylith/registry/registry-payload.v1.js is missing or empty" in issues
    assert "Atlas diagram odylith/atlas/source/sample-flow.mmd is missing rendered png output" in issues
    assert "odylith/index.html shell payload is missing or invalid" in issues
    assert "odylith/index.html is missing shell tab registry" in issues
    assert "odylith/index.html is missing shell frame frame-registry" in issues


def test_quality_verdict_rejects_surface_health_findings(monkeypatch) -> None:
    module = _module()
    monkeypatch.setattr(_scoring_module(), "greenfield_rendered_package_quality_issues", lambda _package: [])
    monkeypatch.setattr(_scoring_module(), "build_greenfield_quality_lens_report", lambda _package: _passing_package_lens_report())

    verdict = module.build_quality_verdict(
        create_payload=_passing_create_payload(),
        package=_substantive_package(),
        counts=_full_counts(module),
        surface_issues=("rendered surface odylith/radar/radar.html does not load backlog-payload.v1.js",),
        create_returncode=0,
        create_seconds=20.0,
    )

    assert not verdict.passed
    assert verdict.score == 6
    assert verdict.scores["copy_semantic_clarity"] == 8
    assert "rendered surface odylith/radar/radar.html does not load backlog-payload.v1.js" in verdict.issues


def test_main_defaults_to_labeled_discovery_when_browser_proof_is_not_requested(monkeypatch, tmp_path: Path, capsys) -> None:
    module = _module()
    dist_dir = tmp_path / "dist"
    _write(dist_dir / "install.sh", "#!/usr/bin/env bash\nexit 0\n")
    monkeypatch.setattr(
        module,
        "run_matrix",
        lambda **_kwargs: (_passing_matrix_result(module),),
    )
    monkeypatch.setattr(module, "run_rescue_smoke", lambda **_kwargs: _passing_rescue_result(module))

    exit_code = module.main(
        [
            "--dist-dir",
            str(dist_dir),
            "--version",
            "0.1.15",
            "--temp-parent",
            str(tmp_path),
            "--json",
            "--output-json",
            str(tmp_path / "matrix-proof.json"),
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["status"] == "discovery-passed"
    assert payload["corpus_provenance"]["claim_class"] == "synthetic-discovery"
    assert (tmp_path / "matrix-proof.json").is_file()


def test_main_rejects_an_unsealed_release_root_before_loading_case_files(monkeypatch, tmp_path: Path) -> None:
    module = _module()
    case_file = tmp_path / "release-cases.json"
    audit_file = tmp_path / "release-audit.json"
    annotations_file = tmp_path / "final-holdout.json"
    evaluation_manifest = tmp_path / "evaluation-splits.json"

    def fail_if_loaded(*_args, **_kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("release evidence was loaded before snapshot validation")

    monkeypatch.setattr(module, "_load_cli_case_files", fail_if_loaded)

    with pytest.raises(RuntimeError, match="sealed input is missing or unsafe"):
        module.main(
            [
                "--dist-dir",
                str(tmp_path / "dist"),
                "--version",
                "0.1.15",
                "--temp-parent",
                str(tmp_path),
                "--proof-tier",
                "release",
                "--case-file",
                str(case_file),
                "--release-audit-file",
                str(audit_file),
                "--release-audit-repo-root",
                str(tmp_path),
                "--sealed-release-input-root",
                str(tmp_path),
                "--semantic-annotations-file",
                str(annotations_file),
                "--evaluation-split-manifest",
                str(evaluation_manifest),
            ]
        )


def test_main_allows_skipped_browser_surface_proof_for_volume_discovery(monkeypatch, tmp_path: Path, capsys) -> None:
    module = _module()
    dist_dir = tmp_path / "dist"
    _write(dist_dir / "install.sh", "#!/usr/bin/env bash\nexit 0\n")
    monkeypatch.setattr(module, "run_matrix", lambda **_kwargs: (_passing_matrix_result(module),))
    monkeypatch.setattr(module, "run_rescue_smoke", lambda **_kwargs: _passing_rescue_result(module))

    exit_code = module.main(
        [
            "--dist-dir",
            str(dist_dir),
            "--version",
            "0.1.15",
            "--temp-parent",
            str(tmp_path),
            "--proof-tier",
            "discovery",
            "--allow-skipped-browser-proof",
            "--json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["status"] == "discovery-passed"
    assert payload["browser_surface_proof"]["status"] == "skipped"


def test_main_runs_browser_surface_proof_when_requested(monkeypatch, tmp_path: Path, capsys) -> None:
    module = _module()
    dist_dir = tmp_path / "dist"
    _write(dist_dir / "install.sh", "#!/usr/bin/env bash\nexit 0\n")
    matrix_kwargs: dict[str, object] = {}

    def fake_run_matrix(**kwargs):  # noqa: ANN001
        matrix_kwargs.update(kwargs)
        return (_passing_matrix_result(module),)

    monkeypatch.setattr(module, "run_matrix", fake_run_matrix)
    monkeypatch.setattr(module, "run_rescue_smoke", lambda **_kwargs: _passing_rescue_result(module))
    monkeypatch.setattr(
        module,
        "run_natural_rescue_proof",
        lambda **_kwargs: _passing_natural_rescue_result(module),
    )

    exit_code = module.main(
        [
            "--dist-dir",
            str(dist_dir),
            "--version",
            "0.1.15",
            "--temp-parent",
            str(tmp_path),
            "--include-browser-proof",
            "--include-natural-rescue-proof",
            "--json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["status"] == "discovery-passed"
    assert matrix_kwargs["include_browser_proof"] is True
    assert payload["proof_scope"]["browser_surface_proof"] == "per_case_headless_generated_surface_state_matrix"
    assert payload["browser_surface_proof"]["status"] == "passed"
    assert payload["browser_surface_proof"]["case_count"] == 1


def test_main_fails_when_requested_browser_surface_proof_fails(monkeypatch, tmp_path: Path, capsys) -> None:
    module = _module()
    dist_dir = tmp_path / "dist"
    _write(dist_dir / "install.sh", "#!/usr/bin/env bash\nexit 0\n")
    failing_result = module.GreenfieldMatrixResult(
        name="matrix case",
        status="passed",
        create_seconds=18.0,
        counts=_full_counts(module),
        quality=module.GreenfieldQualityVerdict(
            passed=True,
            issues=(),
            lenses={lens: True for lens in ("product_manager", "architect", "engineer", "domain_expert")},
            scores={dimension: 10 for dimension in module.QUALITY_SCORE_DIMENSIONS},  # noqa: SLF001
            score=10,
            score_explanation=("all brutal release-quality dimensions scored 10",),
        ),
        browser_surface_issues=("browser surface casebook failed routed render",),
        browser_surface_proof_attempted=True,
    )
    monkeypatch.setattr(module, "run_matrix", lambda **_kwargs: (failing_result,))
    monkeypatch.setattr(module, "run_rescue_smoke", lambda **_kwargs: _passing_rescue_result(module))
    monkeypatch.setattr(
        module,
        "run_natural_rescue_proof",
        lambda **_kwargs: _passing_natural_rescue_result(module),
    )

    exit_code = module.main(
        [
            "--dist-dir",
            str(dist_dir),
            "--version",
            "0.1.15",
            "--temp-parent",
            str(tmp_path),
            "--include-browser-proof",
            "--include-natural-rescue-proof",
            "--json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert payload["status"] == "failed"
    assert payload["browser_surface_proof"]["issues"] == [
        "matrix case: browser surface casebook failed routed render"
    ]


def test_browser_surface_proof_summary_marks_unattempted_case_as_skipped() -> None:
    module = _module()
    result = module.GreenfieldMatrixResult(
        name="failed create case",
        status="failed",
        create_seconds=3.0,
        counts=module.GreenfieldArtifactCounts(),
        quality=module.GreenfieldQualityVerdict(
            passed=False,
            issues=("commit-only create exited with code 2",),
            lenses={lens: False for lens in ("product_manager", "architect", "engineer", "domain_expert")},
            scores={dimension: 0 for dimension in module.QUALITY_SCORE_DIMENSIONS},  # noqa: SLF001
            score=0,
            score_explanation=("completion scored 0/10",),
        ),
        create_returncode=2,
    )

    summary = module.browser_proof_summary((result,), include_browser_proof=True)

    assert summary["status"] == "failed"
    assert summary["cases"] == [
        {
            "name": "failed create case",
            "status": "skipped",
            "attempted": False,
            "issues": ["browser proof skipped because commit-only create did not pass"],
        }
    ]
