from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from odylith.runtime.domain_intelligence.greenfield_post_confirm_rescue_probe import (
    RESCUE_PROBE_ENV,
)
from odylith.runtime.domain_intelligence.greenfield_post_confirm_rescue_probe import (
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
    return _load_module(SCRIPTS_ROOT / "greenfield_post_confirm_matrix.py", "greenfield_post_confirm_matrix")


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
    assert "## State object\nReport." in sparse_case.confirmed_intent_markdown
    assert "## Proof boundary\nEvidence custody and embargo decision." in sparse_case.confirmed_intent_markdown
    assert sparse_case.required_terms == ("disclosure", "council", "evidence", "embargo")
    quantum_case = next(case for case in cases if case.name == "quantum communication lab")
    assert "## State object\nA communication run" in quantum_case.confirmed_intent_markdown
    assert "CHSH" in quantum_case.confirmed_intent_markdown
    assert "QBER" in quantum_case.confirmed_intent_markdown
    assert quantum_case.required_terms == ("quantum", "e91", "qber", "chsh")


def test_run_matrix_scans_selected_case_vocabulary_before_simulation(
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
                term="xenobot",
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
                    name="xenobot custody",
                    prompt="Create a greenfield proposal for xenobot agent custody.",
                    required_terms=("xenobot", "agent"),
                ),
            ),
        )

    assert len(captured_terms) == 1
    assert "xenobot" in captured_terms[0]
    assert "xenobot custody" in captured_terms[0]
    assert not any(path.name.startswith("odylith-greenfield-matrix-") for path in tmp_path.iterdir())


def test_run_matrix_preflight_supplements_declared_sentinels_with_case_vocabulary(
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
    assert "dictionary review sentinel" in captured_terms[0]
    assert "language" in captured_terms[0]
    assert "language archive" in captured_terms[0]
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
        program_result={"dry_run": "true"},
        prewrite_safety_preview={
            "status": "passed",
            "checks": {
                "program_dry_run": True,
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
        program_records=1,
        project_brief_records=1,
        trace_nodes=12,
        trace_workstreams=4,
        rendered_surfaces=len(module.REQUIRED_RENDERED_SURFACES),
        rendered_surface_payloads=len(module.SURFACE_PAYLOAD_CONTRACTS) * 2,
        atlas_rendered_assets=8,
        domain_term_hits=3,
        project_implementation_prompts=5,
    )


def _passing_manifest() -> dict[str, object]:
    return {
        "status": "passed",
        "validation_status": "passed",
        "issue_count": 0,
        "whole_project_elapsed_seconds": 20.0,
        "write_transaction": {"status": "committed"},
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
        "post_confirm_quality_manifest": _passing_manifest(),
        "validation_gate": {"visible_actors": _passing_visible_actors()},
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
                    "program_dry_run": True,
                    "validation_gate_passed": True,
                    "release_target_dry_run": True,
                    "release_assignment_dry_run": True,
                },
            }
        },
    )

    assert package.prewrite_safety_preview["status"] == "passed"
    assert package.prewrite_safety_preview["checks"]["program_dry_run"] is True


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
            scores={dimension: 10 for dimension in module._QUALITY_SCORE_DIMENSIONS},  # noqa: SLF001
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


def test_standard_matrix_create_does_not_receive_internal_rescue_probe_env(monkeypatch, tmp_path: Path) -> None:
    module = _module()
    create_envs: list[dict[str, str]] = []
    monkeypatch.setattr(module, "collect_artifact_package", lambda **_kwargs: _substantive_package())
    monkeypatch.setattr(module, "collect_artifact_counts", lambda **_kwargs: _full_counts(module))
    monkeypatch.setattr(module, "greenfield_rendered_package_quality_issues", lambda _package: [])
    monkeypatch.setattr(module, "build_greenfield_quality_lens_report", lambda _package: _passing_package_lens_report())
    monkeypatch.setattr(module, "rendered_surface_health_issues", lambda **_kwargs: ())

    def fake_run(*, cwd, env, command, timeout):  # noqa: ANN001
        if "create" in command:
            create_envs.append(dict(env))
            payload = _passing_create_payload()
            return subprocess.CompletedProcess(command, 0, json.dumps(payload), "")
        if "propose" in command:
            return subprocess.CompletedProcess(command, 0, "Visible product intent\n", "")
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
    )

    assert result.status == "passed"
    assert len(create_envs) == 1
    assert RESCUE_PROBE_ENV not in create_envs[0]


def test_standard_matrix_override_intent_skips_propose_without_rescue_probe(monkeypatch, tmp_path: Path) -> None:
    module = _module()
    commands: list[list[str]] = []
    create_envs: list[dict[str, str]] = []
    monkeypatch.setattr(module, "collect_artifact_package", lambda **_kwargs: _substantive_package())
    monkeypatch.setattr(module, "collect_artifact_counts", lambda **_kwargs: _full_counts(module))
    monkeypatch.setattr(module, "greenfield_rendered_package_quality_issues", lambda _package: [])
    monkeypatch.setattr(module, "build_greenfield_quality_lens_report", lambda _package: _passing_package_lens_report())
    monkeypatch.setattr(module, "rendered_surface_health_issues", lambda **_kwargs: ())

    def fake_run(*, cwd, env, command, timeout):  # noqa: ANN001
        commands.append(list(command))
        if "create" in command:
            create_envs.append(dict(env))
            payload = _passing_create_payload()
            return subprocess.CompletedProcess(command, 0, json.dumps(payload), "")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(module, "_run", fake_run)

    result = module._run_case(  # noqa: SLF001
        case=module.GreenfieldMatrixCase(
            name="sparse standard",
            prompt="Create a sparse confirmed project.",
            required_terms=("sparse", "project"),
            confirmed_intent_markdown="# Product Intent Confirmation\n\n## State object\nReport.\n",
        ),
        repo_root=tmp_path / "standard-repo",
        install_script=tmp_path / "install.sh",
        base_url="http://127.0.0.1:8123",
        version="0.1.15",
    )

    intent_text = (tmp_path / "standard-repo/.odylith/runtime/greenfield/confirmed-intent.md").read_text(
        encoding="utf-8"
    )
    assert result.status == "passed"
    assert "## State object\nReport." in intent_text
    assert all("propose" not in command for command in commands)
    assert len(create_envs) == 1
    assert RESCUE_PROBE_ENV not in create_envs[0]


def test_rescue_smoke_create_receives_internal_probe_env(monkeypatch, tmp_path: Path) -> None:
    module = _module()
    create_envs: list[dict[str, str]] = []
    monkeypatch.setattr(module, "collect_artifact_package", lambda **_kwargs: _empty_package())
    monkeypatch.setattr(module, "collect_artifact_counts", lambda **_kwargs: _full_counts(module))
    monkeypatch.setattr(module, "greenfield_rendered_package_quality_issues", lambda _package: [])
    monkeypatch.setattr(module, "build_greenfield_quality_lens_report", lambda _package: _passing_package_lens_report())
    monkeypatch.setattr(module, "rendered_surface_health_issues", lambda **_kwargs: ())

    def fake_run(*, cwd, env, command, timeout):  # noqa: ANN001
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
                    "repaired_issue_codes": ["post_confirm_rescue_probe"],
                }
            )
            payload = {"post_confirm_quality_manifest": manifest}
            return subprocess.CompletedProcess(command, 0, json.dumps(payload), "")
        if "propose" in command:
            return subprocess.CompletedProcess(command, 0, "Visible product intent\n", "")
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
    _write(tmp_path / "odylith/radar/source/releases/releases.v1.json", "{}\n")
    _write(tmp_path / "odylith/radar/source/programs/B-001.execution-waves.v1.json", "{}\n")
    _write(tmp_path / "odylith/runtime/source/accepted-project.v1.json", "{}\n")
    _write(
        tmp_path / ".odylith/runtime/greenfield/confirmed-intent.json",
        json.dumps({"project_brief": {"project_outcome": "Residents reach shelter placements with consent evidence."}}),
    )
    for surface in module.REQUIRED_RENDERED_SURFACES:
        _write(tmp_path / surface, "<html>ready</html>\n")
    _write(tmp_path / "odylith/compass/runtime/current.v1.json", "{}\n")

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
    assert counts.rendered_surfaces == len(module.REQUIRED_RENDERED_SURFACES)
    assert counts.domain_term_hits == 4


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
    _write(tmp_path / ".odylith/runtime/greenfield/confirmed-intent.json", "{}\n")
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


def test_package_evidence_rejects_preview_only_project_brief() -> None:
    module = _module()
    package = _substantive_package()
    package.project_brief_record_text = ""

    findings = module.package_evidence_findings(package)

    assert any("persisted project brief readback" in finding.message for finding in findings)


def test_package_evidence_prefers_accepted_source_launch_readback() -> None:
    module = _module()
    package = _substantive_package()
    package.next_steps_preview = {}
    package.source_launch_readback = dict(package.accepted_project_preview["source_launch"])

    findings = module.package_evidence_findings(package)

    assert not any("accepted source-launch readback" in finding.message for finding in findings)
    assert not any("operator next steps" in finding.message for finding in findings)


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

    findings = module.package_evidence_findings(package)

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

    findings = module.package_evidence_findings(package)

    assert any("semantic terms on Registry" in finding.message for finding in findings)


def test_collect_artifact_package_prefers_accepted_project_proposal_over_confirmed_intent(tmp_path: Path) -> None:
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
    _write(
        tmp_path / ".odylith/runtime/greenfield/confirmed-intent.json",
        json.dumps({"intent": {"title": "Confirmed intent only"}, "components": []}) + "\n",
    )

    package = module.collect_artifact_package(repo_root=tmp_path, create_payload={})

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


def test_package_evidence_rejects_missing_persisted_project_prompt_payload() -> None:
    module = _module()
    package = _substantive_package()
    package.project_dashboard_preview = {}

    findings = module.package_evidence_findings(package)

    assert any("accepted Project readback does not expose five source-launch prompts" in finding.message for finding in findings)


def test_generated_leakage_terms_supplement_declared_sentinels_with_distinctive_anchors(tmp_path: Path) -> None:
    module = _module()
    package = _substantive_package()
    package.project_brief_record_text += "\nWafer lot xenobot readiness remains visible for review."
    case = module.GreenfieldMatrixCase(
        name="wafer xenobot",
        prompt="Create a proposal for wafer xenobot attestation.",
        required_terms=("xenobot", "wafer", "attestation"),
        leakage_terms=("wafer lot", "missing lattice phrase"),
    )

    terms = module._case_generated_leakage_terms(  # noqa: SLF001
        case=case,
        generated_text=module._generated_text(repo_root=tmp_path, package=package),  # noqa: SLF001
    )

    assert "wafer lot" in terms
    assert "missing lattice phrase" not in terms
    assert "xenobot" in terms
    assert "wafer" in terms


def test_generated_leakage_terms_suppress_generic_required_anchors(tmp_path: Path) -> None:
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
    assert "xenobot" in terms


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
        leakage_terms=("missing lattice phrase",),
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
    assert "estimate" in captured_terms[0]
    assert "projection" in captured_terms[0]
    assert "estimate projection" in captured_terms[0]
    assert "estimate" in platform_baseline_terms
    assert "projection" in platform_baseline_terms
    assert "estimate projection" in platform_baseline_terms
    assert "estimate" not in terms
    assert "projection" not in terms


def test_generated_leakage_terms_fall_back_when_case_has_no_declared_sentinels(tmp_path: Path) -> None:
    module = _module()
    package = _substantive_package()
    package.project_brief_record_text += "\nXenobot readiness remains visible for review."
    case = module.GreenfieldMatrixCase(
        name="xenobot fallback",
        prompt="Create a proposal for xenobot review.",
        required_terms=("xenobot",),
    )

    terms = module._case_generated_leakage_terms(  # noqa: SLF001
        case=case,
        generated_text=module._generated_text(repo_root=tmp_path, package=package),  # noqa: SLF001
    )

    assert "xenobot" in terms


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
    assert "post-confirm quality manifest missing" in verdict.issues
    assert "post-confirm create exceeded 60s: 61.000s" in verdict.issues
    assert all(passed is False for passed in verdict.lenses.values())


def test_quality_verdict_retains_post_confirm_failure_detail() -> None:
    module = _module()

    verdict = module.build_quality_verdict(
        create_payload={},
        package=_empty_package(),
        counts=module.GreenfieldArtifactCounts(),
        create_returncode=2,
        create_seconds=14.0,
        create_detail="greenfield post-confirm completion failed with 1 issue: repeated canonical projection",
    )

    assert not verdict.passed
    assert (
        "post-confirm create failure detail: greenfield post-confirm completion failed with 1 issue: "
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
            issues=("post-confirm create exited with code 2",),
            lenses={lens: False for lens in ("product_manager", "architect", "engineer", "domain_expert")},
            scores={dimension: 0 for dimension in module._QUALITY_SCORE_DIMENSIONS},  # noqa: SLF001
            score=0,
            score_explanation=("score forced to 0 because post-confirm did not commit governed records",),
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
        create_payload={"post_confirm_quality_manifest": manifest},
        package=_empty_package(),
        counts=_full_counts(module),
        create_returncode=0,
        create_seconds=20.0,
    )

    assert not verdict.passed
    assert verdict.score == 0
    assert "post-confirm write transaction was not committed" in verdict.issues
    assert verdict.lenses["engineer"] is False


def test_quality_verdict_rejects_self_reported_manifest_without_package_readback(monkeypatch) -> None:
    module = _module()
    monkeypatch.setattr(module, "greenfield_rendered_package_quality_issues", lambda package: [])

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
    monkeypatch.setattr(module, "greenfield_rendered_package_quality_issues", lambda package: [])
    monkeypatch.setattr(module, "build_greenfield_quality_lens_report", lambda _package: _passing_package_lens_report())

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


def test_quality_verdict_rejects_count_only_package_even_when_lenses_are_stubbed(monkeypatch) -> None:
    module = _module()
    monkeypatch.setattr(module, "greenfield_rendered_package_quality_issues", lambda package: [])
    monkeypatch.setattr(module, "build_greenfield_quality_lens_report", lambda _package: _passing_package_lens_report())

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
    monkeypatch.setattr(module, "greenfield_rendered_package_quality_issues", lambda package: [])
    monkeypatch.setattr(module, "build_greenfield_quality_lens_report", lambda _package: _passing_package_lens_report())
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
    monkeypatch.setattr(module, "greenfield_rendered_package_quality_issues", lambda package: [])
    monkeypatch.setattr(module, "build_greenfield_quality_lens_report", lambda _package: _passing_package_lens_report())
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
    monkeypatch.setattr(module, "greenfield_rendered_package_quality_issues", lambda package: [])
    monkeypatch.setattr(module, "build_greenfield_quality_lens_report", lambda _package: _passing_package_lens_report())
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
    monkeypatch.setattr(module, "greenfield_rendered_package_quality_issues", lambda package: [])
    monkeypatch.setattr(module, "build_greenfield_quality_lens_report", lambda _package: _passing_package_lens_report())
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
    monkeypatch.setattr(module, "greenfield_rendered_package_quality_issues", lambda package: [])
    monkeypatch.setattr(module, "build_greenfield_quality_lens_report", lambda _package: _passing_package_lens_report())
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
        module,
        "greenfield_rendered_package_quality_issues",
        lambda package: ["Radar workstream has clipped copy", "Registry spec repeats generic copy"],
    )
    monkeypatch.setattr(module, "build_greenfield_quality_lens_report", lambda _package: _passing_package_lens_report())

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
        module,
        "greenfield_rendered_package_quality_issues",
        lambda package: ["Project implementation prompt `Build smallest runnable slice` does not bind implementation to a governed workstream"],
    )
    monkeypatch.setattr(module, "build_greenfield_quality_lens_report", lambda _package: _passing_package_lens_report())

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
            "repaired_issue_codes": ["post_confirm_rescue_probe"],
        }
    )
    monkeypatch.setattr(module, "greenfield_rendered_package_quality_issues", lambda package: [])

    issues = module.rescue_cli_issues(
        manifest=manifest,
        package=_empty_package(),
        counts=_full_counts(module),
        count_minimums=module._required_count_minimums(),  # noqa: SLF001
        count_key=module._count_key,  # noqa: SLF001
        write_committed=module._write_committed,  # noqa: SLF001
        as_mapping=module._as_mapping,  # noqa: SLF001
        package_quality_issues=module.greenfield_rendered_package_quality_issues,
        create_returncode=0,
        create_seconds=74.5,
        detail="",
        expected_requested_tier="auto",
    )

    assert issues == ()


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
            "write_transaction": {"status": "committed"},
            "whole_project_elapsed_seconds": 30.0,
            "quality_lenses": {"status": "passed"},
        },
        package=_empty_package(),
        counts=_full_counts(module),
        count_minimums=module._required_count_minimums(),  # noqa: SLF001
        count_key=module._count_key,  # noqa: SLF001
        write_committed=module._write_committed,  # noqa: SLF001
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
    assert "auto-rescue manifest did not record the typed rescue probe repair" in issues


def test_quality_verdict_requires_all_case_domain_terms() -> None:
    module = _module()
    counts = module.GreenfieldArtifactCounts(
        radar_workstreams=4,
        registry_component_specs=3,
        atlas_mermaid_sources=4,
        compass_records=1,
        release_records=1,
        program_records=1,
        project_brief_records=1,
        trace_nodes=12,
        trace_workstreams=4,
        rendered_surfaces=len(module.REQUIRED_RENDERED_SURFACES),
        rendered_surface_payloads=len(module.SURFACE_PAYLOAD_CONTRACTS) * 2,
        atlas_rendered_assets=8,
        domain_term_hits=3,
        required_domain_terms=4,
        project_implementation_prompts=5,
    )
    quality = module.build_quality_verdict(
        create_payload=_passing_create_payload(),
        package=_empty_package(),
        counts=counts,
        create_returncode=0,
        create_seconds=20.0,
    )

    assert not quality.passed
    assert quality.scores["domain_expert"] == 0
    assert "domain term coverage too low: expected at least 4, found 3" in quality.issues


def test_rendered_surface_health_requires_payload_assets_and_shell_contract(tmp_path: Path) -> None:
    module = _module()
    for relative, assets in module.SURFACE_PAYLOAD_CONTRACTS.items():
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
    monkeypatch.setattr(module, "greenfield_rendered_package_quality_issues", lambda _package: [])
    monkeypatch.setattr(module, "build_greenfield_quality_lens_report", lambda _package: _passing_package_lens_report())

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


def test_main_requires_browser_surface_proof_by_default(monkeypatch, tmp_path: Path, capsys) -> None:
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
    persisted = json.loads((tmp_path / "matrix-proof.json").read_text(encoding="utf-8"))

    assert exit_code == 1
    assert payload["status"] == "failed"
    assert payload == persisted
    assert payload["proof_scope"]["standard_path"] == "real_installed_greenfield_post_confirm_quality_matrix"
    assert payload["proof_scope"]["rescue_path"] == "synthetic_typed_probe_wiring_only"
    assert payload["proof_scope"]["natural_rescue_quality_proven"] is False
    assert payload["rescue_smoke"]["status"] == "passed"
    assert payload["rescue_smoke"]["proof_scope"] == "synthetic_typed_probe_wiring_only"
    assert payload["rescue_smoke"]["natural_rescue_quality_proven"] is False
    assert "engine_manifest" not in payload["rescue_smoke"]
    assert payload["browser_surface_proof"]["status"] == "skipped"


def test_main_allows_skipped_browser_surface_proof_only_for_debug(monkeypatch, tmp_path: Path, capsys) -> None:
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
            "--allow-skipped-browser-proof",
            "--json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["status"] == "passed"
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

    exit_code = module.main(
        [
            "--dist-dir",
            str(dist_dir),
            "--version",
            "0.1.15",
            "--temp-parent",
            str(tmp_path),
            "--include-browser-proof",
            "--json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["status"] == "passed"
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
            scores={dimension: 10 for dimension in module._QUALITY_SCORE_DIMENSIONS},  # noqa: SLF001
            score=10,
            score_explanation=("all brutal release-quality dimensions scored 10",),
        ),
        browser_surface_issues=("browser surface casebook failed routed render",),
        browser_surface_proof_attempted=True,
    )
    monkeypatch.setattr(module, "run_matrix", lambda **_kwargs: (failing_result,))
    monkeypatch.setattr(module, "run_rescue_smoke", lambda **_kwargs: _passing_rescue_result(module))

    exit_code = module.main(
        [
            "--dist-dir",
            str(dist_dir),
            "--version",
            "0.1.15",
            "--temp-parent",
            str(tmp_path),
            "--include-browser-proof",
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
            issues=("post-confirm create exited with code 2",),
            lenses={lens: False for lens in ("product_manager", "architect", "engineer", "domain_expert")},
            scores={dimension: 0 for dimension in module._QUALITY_SCORE_DIMENSIONS},  # noqa: SLF001
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
            "issues": ["browser proof skipped because post-confirm create did not pass"],
        }
    ]
