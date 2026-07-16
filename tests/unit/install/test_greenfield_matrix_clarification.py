from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


SCRIPTS_ROOT = Path(__file__).resolve().parents[3] / "scripts" / "release"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from greenfield_matrix_clarification import clarification_quality_verdict


def _matrix_module():
    spec = importlib.util.spec_from_file_location(
        "greenfield_preconfirm_matrix_clarification_test",
        SCRIPTS_ROOT / "greenfield_preconfirm_matrix.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_clarification_quality_verdict_preserves_one_complete_summary_line() -> None:
    verdict = clarification_quality_verdict(())

    assert verdict.score_explanation == (
        "clarification-required pre-confirm contract verified without a transaction or governed write",
    )


def test_matrix_summary_renders_the_clarification_verdict_once(capsys) -> None:  # noqa: ANN001
    module = _matrix_module()
    explanation = "clarification-required pre-confirm contract verified without a transaction or governed write"
    result = module.GreenfieldMatrixResult(
        name="cell therapy clarification",
        status="passed",
        create_seconds=0.0,
        counts=module.GreenfieldArtifactCounts(),
        quality=clarification_quality_verdict(()),
    )

    module._print_human_summary((result,))  # noqa: SLF001

    output = capsys.readouterr().out
    assert output.count(f"   score: {explanation}") == 1
    assert "\n   score: c\n" not in output
