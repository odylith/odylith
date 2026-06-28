from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

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
    sparse_case = next(case for case in cases if case.name == "sparse disclosure confirmation")
    assert "## State object\nReport." in sparse_case.confirmed_intent_markdown
    assert "## Proof boundary\nEvidence custody and embargo decision." in sparse_case.confirmed_intent_markdown
    assert sparse_case.required_terms == ("disclosure", "council", "evidence", "embargo")
    quantum_case = next(case for case in cases if case.name == "quantum communication lab")
    assert "## State object\nA communication run" in quantum_case.confirmed_intent_markdown
    assert "CHSH" in quantum_case.confirmed_intent_markdown
    assert "QBER" in quantum_case.confirmed_intent_markdown
    assert quantum_case.required_terms == ("quantum", "e91", "qber", "chsh")


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _empty_package() -> SimpleNamespace:
    return SimpleNamespace(
        proposal={},
        backlog_result={"idea_files": {}, "backlog_index_text": ""},
        rendered_component_specs={},
        rendered_atlas_sources={},
        component_registry_preview=(),
        project_brief_preview={},
        accepted_project_preview={},
        project_dashboard_preview={},
        compass_memory_preview={},
        next_steps_preview={},
        program_result={},
        release_target_result={},
        release_assignment_result={},
        release_workstream_ids=(),
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


def test_standard_matrix_create_does_not_receive_internal_rescue_probe_env(monkeypatch, tmp_path: Path) -> None:
    module = _module()
    create_envs: list[dict[str, str]] = []
    monkeypatch.setattr(module, "collect_artifact_package", lambda **_kwargs: _empty_package())
    monkeypatch.setattr(module, "collect_artifact_counts", lambda **_kwargs: _full_counts(module))
    monkeypatch.setattr(module, "greenfield_rendered_package_quality_issues", lambda _package: [])

    def fake_run(*, cwd, env, command, timeout):  # noqa: ANN001
        if "create" in command:
            create_envs.append(dict(env))
            payload = {"post_confirm_quality_manifest": _passing_manifest()}
            return module.subprocess.CompletedProcess(command, 0, json.dumps(payload), "")
        if "propose" in command:
            return module.subprocess.CompletedProcess(command, 0, "Visible product intent\n", "")
        return module.subprocess.CompletedProcess(command, 0, "", "")

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
    monkeypatch.setattr(module, "collect_artifact_package", lambda **_kwargs: _empty_package())
    monkeypatch.setattr(module, "collect_artifact_counts", lambda **_kwargs: _full_counts(module))
    monkeypatch.setattr(module, "greenfield_rendered_package_quality_issues", lambda _package: [])

    def fake_run(*, cwd, env, command, timeout):  # noqa: ANN001
        commands.append(list(command))
        if "create" in command:
            create_envs.append(dict(env))
            payload = {"post_confirm_quality_manifest": _passing_manifest()}
            return module.subprocess.CompletedProcess(command, 0, json.dumps(payload), "")
        return module.subprocess.CompletedProcess(command, 0, "", "")

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
            return module.subprocess.CompletedProcess(command, 0, json.dumps(payload), "")
        if "propose" in command:
            return module.subprocess.CompletedProcess(command, 0, "Visible product intent\n", "")
        return module.subprocess.CompletedProcess(command, 0, "", "")

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
        required_terms=("flood", "shelter", "resident", "placement"),
    )

    assert "odylith/radar/source/AGENTS.md" not in package.backlog_result["idea_files"]
    assert counts.radar_workstreams == 1
    assert counts.registry_component_specs == 1
    assert counts.atlas_mermaid_sources == 1
    assert counts.rendered_surfaces == len(module.REQUIRED_RENDERED_SURFACES)
    assert counts.domain_term_hits == 4


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


def test_quality_verdict_scores_premium_only_when_every_dimension_is_clean(monkeypatch) -> None:
    module = _module()
    monkeypatch.setattr(module, "greenfield_rendered_package_quality_issues", lambda package: [])

    verdict = module.build_quality_verdict(
        create_payload={"post_confirm_quality_manifest": _passing_manifest()},
        package=_empty_package(),
        counts=_full_counts(module),
        create_returncode=0,
        create_seconds=20.0,
    )

    assert verdict.passed
    assert verdict.score == 10
    assert all(score == 10 for score in verdict.scores.values())
    assert "all brutal release-quality dimensions scored 10" in verdict.score_explanation


def test_quality_verdict_caps_score_when_rendered_artifacts_have_copy_findings(monkeypatch) -> None:
    module = _module()
    monkeypatch.setattr(
        module,
        "greenfield_rendered_package_quality_issues",
        lambda package: ["Radar workstream has clipped copy", "Registry spec repeats generic copy"],
    )

    verdict = module.build_quality_verdict(
        create_payload={"post_confirm_quality_manifest": _passing_manifest()},
        package=_empty_package(),
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

    verdict = module.build_quality_verdict(
        create_payload={"post_confirm_quality_manifest": _passing_manifest()},
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
        domain_term_hits=3,
        required_domain_terms=4,
        project_implementation_prompts=5,
    )
    quality = module.build_quality_verdict(
        create_payload={"post_confirm_quality_manifest": _passing_manifest()},
        package=_empty_package(),
        counts=counts,
        create_returncode=0,
        create_seconds=20.0,
    )

    assert not quality.passed
    assert quality.scores["domain_expert"] == 0
    assert "domain term coverage too low: expected at least 4, found 3" in quality.issues


def test_main_includes_rescue_smoke_by_default(monkeypatch, tmp_path: Path, capsys) -> None:
    module = _module()
    dist_dir = tmp_path / "dist"
    _write(dist_dir / "install.sh", "#!/usr/bin/env bash\nexit 0\n")
    monkeypatch.setattr(
        module,
        "run_matrix",
        lambda **_kwargs: (
            module.GreenfieldMatrixResult(
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
            ),
        ),
    )
    monkeypatch.setattr(
        module,
        "run_rescue_smoke",
        lambda **_kwargs: module.GreenfieldRescueSmokeResult(
            status="passed",
            cli_create_seconds=44.0,
            counts=_full_counts(module),
            issues=(),
            manifest={"repair_tier": "rescue"},
        ),
    )

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

    assert exit_code == 0
    assert payload["status"] == "passed"
    assert payload == persisted
    assert payload["proof_scope"]["standard_path"] == "real_installed_greenfield_post_confirm_quality_matrix"
    assert payload["proof_scope"]["rescue_path"] == "synthetic_typed_probe_wiring_only"
    assert payload["proof_scope"]["natural_rescue_quality_proven"] is False
    assert payload["rescue_smoke"]["status"] == "passed"
    assert payload["rescue_smoke"]["proof_scope"] == "synthetic_typed_probe_wiring_only"
    assert payload["rescue_smoke"]["natural_rescue_quality_proven"] is False
    assert "engine_manifest" not in payload["rescue_smoke"]
