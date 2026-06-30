from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


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
    if str(SCRIPTS_ROOT) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_ROOT))
    return _load_module(SCRIPTS_ROOT / "greenfield_post_confirm_matrix.py", "greenfield_post_confirm_matrix")


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


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
        rendered_surface_payloads=12,
        atlas_rendered_assets=8,
        domain_term_hits=3,
        project_implementation_prompts=5,
    )


def _passing_quality(module) -> object:
    return module.GreenfieldQualityVerdict(
        passed=True,
        issues=(),
        lenses={lens: True for lens in ("product_manager", "architect", "engineer", "domain_expert")},
        scores={dimension: 10 for dimension in module.QUALITY_SCORE_DIMENSIONS},
        score=10,
        score_explanation=("all brutal release-quality dimensions scored 10",),
    )


def _passing_matrix_result(module, *, manifest_summary: dict[str, object] | None = None) -> object:
    return module.GreenfieldMatrixResult(
        name="matrix case",
        status="passed",
        create_seconds=18.0,
        counts=_full_counts(module),
        quality=_passing_quality(module),
        browser_surface_proof_attempted=True,
        post_confirm_manifest_summary=manifest_summary or {},
    )


def _passing_rescue_result(module) -> object:
    return module.GreenfieldRescueSmokeResult(
        status="passed",
        cli_create_seconds=44.0,
        counts=_full_counts(module),
        issues=(),
        manifest={"repair_tier": "rescue"},
    )


def test_case_file_loader_preserves_confirmed_intent_markdown(tmp_path: Path) -> None:
    module = _module()
    case_file = tmp_path / "cases.json"
    confirmed = "# Product Intent Confirmation\n\n## State object\nA review record.\n"
    case_file.write_text(
        json.dumps(
            {
                "cases": [
                    {
                        "name": "language archive review",
                        "prompt": "Create a greenfield proposal for language archive review.",
                        "required_terms": ["language", "archive", "review"],
                        "leakage_terms": ["language archive review"],
                        "confirmed_intent_markdown": confirmed,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    cases = module.load_case_file(case_file)

    assert len(cases) == 1
    assert cases[0].name == "language archive review"
    assert cases[0].required_terms == ("language", "archive", "review")
    assert cases[0].leakage_terms == ("language archive review",)
    assert cases[0].confirmed_intent_markdown == confirmed.strip()


def test_main_uses_external_case_files_instead_of_default_catalog(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys,
) -> None:
    module = _module()
    dist_dir = tmp_path / "dist"
    _write(dist_dir / "install.sh", "#!/usr/bin/env bash\nexit 0\n")
    case_file = tmp_path / "fresh-cases.json"
    case_file.write_text(
        json.dumps(
            [
                {
                    "name": "museum conservation queue",
                    "prompt": "Create a greenfield proposal for museum conservation queue review.",
                    "required_terms": ["museum", "conservation", "queue"],
                    "leakage_terms": ["museum conservation queue"],
                }
            ]
        ),
        encoding="utf-8",
    )
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
            "--case-file",
            str(case_file),
            "--include-browser-proof",
            "--json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["status"] == "passed"
    assert payload["temp_cleanup_proof"]["status"] == "passed"
    cases = matrix_kwargs["cases"]
    assert len(cases) == 1
    assert cases[0].name == "museum conservation queue"
    assert cases[0].leakage_terms == ("museum conservation queue",)


def test_case_file_rejects_missing_leakage_terms_before_simulation(tmp_path: Path) -> None:
    module = _module()
    dist_dir = tmp_path / "dist"
    _write(dist_dir / "install.sh", "#!/usr/bin/env bash\n")
    case_file = tmp_path / "cases.json"
    case_file.write_text(
        json.dumps(
            {
                "cases": [
                    {
                        "name": "weak case",
                        "prompt": "Create a greenfield proposal for weak case review.",
                        "required_terms": ["weak", "case"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="must define leakage_terms"):
        module.main(
            [
                "--dist-dir",
                str(dist_dir),
                "--version",
                "0.1.15",
                "--temp-parent",
                str(tmp_path),
                "--case-file",
                str(case_file),
            ]
        )

    assert not any(path.name.startswith("odylith-greenfield-matrix-") for path in tmp_path.iterdir())


def test_main_fails_when_temp_cleanup_proof_finds_leftover_repo(monkeypatch, tmp_path: Path, capsys) -> None:
    module = _module()
    dist_dir = tmp_path / "dist"
    _write(dist_dir / "install.sh", "#!/usr/bin/env bash\nexit 0\n")
    (tmp_path / "odylith-greenfield-matrix-leftover").mkdir()
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
            "--include-browser-proof",
            "--json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert payload["status"] == "failed"
    assert payload["temp_cleanup_proof"]["status"] == "failed"
    assert str(tmp_path / "odylith-greenfield-matrix-leftover") in payload["temp_cleanup_proof"]["remaining_paths"]


def test_natural_rescue_quality_requires_provider_backed_non_probe_case() -> None:
    module = _module()
    synthetic = _passing_matrix_result(
        module,
        manifest_summary={
            "status": "passed",
            "validation_status": "passed",
            "repair_tier": "rescue",
            "rescue_activated": True,
            "repaired_issue_codes": ["post_confirm_rescue_probe"],
            "tribunal_patch_plan_status": "planned",
            "tribunal_patch_plan_operation_count": 1,
            "tribunal_patch_plan_provider": "codex-cli",
        },
    )
    natural = _passing_matrix_result(
        module,
        manifest_summary={
            "status": "passed",
            "validation_status": "passed",
            "repair_tier": "rescue",
            "rescue_activated": True,
            "repaired_issue_codes": ["semantic_alignment"],
            "tribunal_patch_plan_status": "planned",
            "tribunal_patch_plan_operation_count": 1,
            "tribunal_patch_plan_provider": "codex-cli",
        },
    )

    assert module.natural_rescue_quality_proven((synthetic,)) is False
    assert module.natural_rescue_quality_proven((natural,)) is True
