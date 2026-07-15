from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_ROOT = REPO_ROOT / "scripts" / "release"


def _module():
    spec = importlib.util.spec_from_file_location(
        "greenfield_preconfirm_release_provenance_test",
        SCRIPTS_ROOT / "greenfield_preconfirm_matrix.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_case_file(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "cases": [
                    {
                        "case_id": "synthetic-001",
                        "name": "synthetic evidence review",
                        "prompt": "Create a proposal for synthetic evidence review.",
                        "required_terms": ["synthetic"],
                        "leakage_terms": ["synthetic evidence"],
                        "stressors": ["modal-expert-lens"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )


def test_release_cli_rejects_synthetic_case_file_before_any_installed_run(tmp_path: Path, monkeypatch) -> None:
    module = _module()
    case_file = tmp_path / "synthetic.json"
    _write_case_file(case_file)
    calls: list[object] = []
    monkeypatch.setattr(module, "run_matrix", lambda **kwargs: calls.append(kwargs))

    with pytest.raises(RuntimeError, match="source-provenanced cases"):
        module.main(
            [
                "--dist-dir",
                str(tmp_path / "dist"),
                "--version",
                "0.1.15",
                "--temp-parent",
                str(tmp_path / "temp"),
                "--case-file",
                str(case_file),
                "--proof-tier",
                "release",
                "--include-browser-proof",
                "--include-natural-rescue-proof",
            ]
        )

    assert calls == []


def test_direct_release_matrix_api_reapplies_policy_before_reading_dist(tmp_path: Path) -> None:
    module = _module()
    case = module.GreenfieldMatrixCase(
        name="synthetic evidence review",
        prompt="Create a proposal for synthetic evidence review.",
        required_terms=("synthetic",),
        leakage_terms=("synthetic evidence",),
    )

    with pytest.raises(RuntimeError) as error:
        module.run_matrix(
            dist_dir=tmp_path / "missing-dist",
            version="0.1.15",
            temp_parent=tmp_path / "temp",
            cases=(case,),
            proof_tier="release",
            install_mode="seeded",
            include_browser_proof=False,
            stop_after_failures=1,
        )

    message = str(error.value)
    assert "release proof must use full install mode" in message
    assert "release proof must include browser proof" in message
    assert "release proof cannot stop after a failure threshold" in message
    assert "source-provenanced cases" in message


def test_case_evidence_omits_absent_edit_hash_and_uses_campaign_field_name() -> None:
    module = _module()
    case = module.GreenfieldMatrixCase(
        name="evidence naming",
        prompt="Create a proposal for evidence naming.",
        required_terms=("evidence",),
        leakage_terms=("evidence naming",),
    )

    no_edit = module._case_evidence(case)  # noqa: SLF001
    with_edit = module._case_evidence(
        module.GreenfieldMatrixCase(
            name=case.name,
            prompt=case.prompt,
            required_terms=case.required_terms,
            leakage_terms=case.leakage_terms,
            confirmed_intent_markdown="Accepted intent records the evidence naming boundary.",
        )
    )  # noqa: SLF001

    assert "edit_evidence_sha256" not in no_edit
    assert "confirmed_intent_sha256" not in no_edit
    assert len(with_edit["confirmed_intent_sha256"]) == 64
