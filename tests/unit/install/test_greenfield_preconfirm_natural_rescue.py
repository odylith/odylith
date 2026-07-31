from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_ROOT = REPO_ROOT / "scripts" / "release"


def _module():
    spec = importlib.util.spec_from_file_location(
        "greenfield_preconfirm_matrix_natural_test",
        SCRIPTS_ROOT / "greenfield_preconfirm_matrix.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["greenfield_preconfirm_matrix_natural_test"] = module
    spec.loader.exec_module(module)
    return module


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
        program_records=0,
        project_brief_records=1,
        trace_nodes=12,
        trace_workstreams=4,
        rendered_surfaces=len(module.REQUIRED_RENDERED_SURFACES),
        rendered_surface_payloads=len(module.REQUIRED_RENDERED_SURFACES) * 2,
        atlas_rendered_assets=8,
        domain_term_hits=4,
        required_domain_terms=4,
        project_implementation_prompts=5,
    )


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
            scores={dimension: 10 for dimension in module.QUALITY_SCORE_DIMENSIONS},
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
        cli_create_seconds=66.0,
        counts=_full_counts(module),
        issues=(),
        manifest={"repair_tier": "rescue"},
        proof_scope="real_installed_structured_patch_plan_case",
        natural_rescue_quality_proven=True,
    )


def test_main_runs_natural_rescue_proof_when_requested(monkeypatch, tmp_path: Path, capsys) -> None:
    module = _module()
    dist_dir = tmp_path / "dist"
    _write(dist_dir / "install.sh", "#!/usr/bin/env bash\nexit 0\n")
    natural_kwargs: dict[str, object] = {}
    monkeypatch.setattr(module, "run_matrix", lambda **_kwargs: (_passing_matrix_result(module),))
    monkeypatch.setattr(module, "run_rescue_smoke", lambda **_kwargs: _passing_rescue_result(module))

    def fake_natural_rescue(**kwargs):  # noqa: ANN001
        natural_kwargs.update(kwargs)
        return _passing_natural_rescue_result(module)

    monkeypatch.setattr(module, "run_natural_rescue_proof", fake_natural_rescue)

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
            "--include-natural-rescue-proof",
            "--json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert natural_kwargs["dist_dir"] == dist_dir
    assert payload["proof_scope"]["natural_rescue_quality_proven"] is True
    assert payload["proof_scope"]["natural_rescue_path"] == "real_installed_structured_patch_plan_case"
    assert payload["natural_rescue_proof"]["status"] == "passed"
    assert payload["natural_rescue_proof"]["natural_rescue_quality_proven"] is True


def test_main_fails_when_requested_natural_rescue_proof_fails(monkeypatch, tmp_path: Path, capsys) -> None:
    module = _module()
    dist_dir = tmp_path / "dist"
    _write(dist_dir / "install.sh", "#!/usr/bin/env bash\nexit 0\n")
    monkeypatch.setattr(module, "run_matrix", lambda **_kwargs: (_passing_matrix_result(module),))
    monkeypatch.setattr(module, "run_rescue_smoke", lambda **_kwargs: _passing_rescue_result(module))
    monkeypatch.setattr(
        module,
        "run_natural_rescue_proof",
        lambda **_kwargs: module.GreenfieldRescueSmokeResult(
            status="failed",
            cli_create_seconds=91.0,
            counts=_full_counts(module),
            issues=("natural rescue proof did not record the structured patch provider",),
            manifest={},
            proof_scope="real_installed_structured_patch_plan_case",
            natural_rescue_quality_proven=False,
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
            "--proof-tier",
            "discovery",
            "--allow-skipped-browser-proof",
            "--include-natural-rescue-proof",
            "--json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert payload["status"] == "failed"
    assert payload["proof_scope"]["natural_rescue_quality_proven"] is False
    assert payload["natural_rescue_proof"]["issues"] == [
        "natural rescue proof did not record the structured patch provider"
    ]
