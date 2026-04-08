from __future__ import annotations

import importlib
from pathlib import Path

import pytest

from odylith.runtime.reasoning import odylith_reasoning
from odylith.runtime.reasoning import remediator
from odylith.runtime.reasoning import tribunal_engine

_REASONING_MODULE_NAMES = (
    "odylith_reasoning",
    "tribunal_engine",
    "remediator",
)


def test_reasoning_modules_live_under_reasoning_package() -> None:
    repo_root = Path(__file__).resolve().parents[3]

    assert (repo_root / "src" / "odylith" / "runtime" / "reasoning" / "odylith_reasoning.py").is_file()
    assert (repo_root / "src" / "odylith" / "runtime" / "reasoning" / "tribunal_engine.py").is_file()
    assert (repo_root / "src" / "odylith" / "runtime" / "reasoning" / "remediator.py").is_file()
    assert not (repo_root / "src" / "odylith" / "runtime" / "evaluation" / "odylith_reasoning.py").exists()
    assert not (repo_root / "src" / "odylith" / "runtime" / "evaluation" / "tribunal_engine.py").exists()
    assert not (repo_root / "src" / "odylith" / "runtime" / "evaluation" / "remediator.py").exists()
    assert "runtime/reasoning/odylith_reasoning.py" in str(Path(odylith_reasoning.__file__).as_posix())
    assert "runtime/reasoning/tribunal_engine.py" in str(Path(tribunal_engine.__file__).as_posix())
    assert "runtime/reasoning/remediator.py" in str(Path(remediator.__file__).as_posix())


@pytest.mark.parametrize(
    "module_name",
    [
        "odylith.runtime.evaluation.odylith_reasoning",
        "odylith.runtime.evaluation.tribunal_engine",
        "odylith.runtime.evaluation.remediator",
    ],
)
def test_legacy_evaluation_reasoning_modules_are_not_importable(module_name: str) -> None:
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module(module_name)


def test_reasoning_path_move_updates_sync_governance_inputs() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    atlas_catalog = repo_root / "odylith" / "atlas" / "source" / "catalog" / "diagrams.v1.json"
    delivery_intelligence = repo_root / "odylith" / "runtime" / "delivery_intelligence.v4.json"

    atlas_text = atlas_catalog.read_text(encoding="utf-8")
    delivery_text = delivery_intelligence.read_text(encoding="utf-8")

    for module_name in _REASONING_MODULE_NAMES:
        old_path = f"src/odylith/runtime/evaluation/{module_name}.py"
        new_path = f"src/odylith/runtime/reasoning/{module_name}.py"

        assert old_path not in atlas_text
        assert new_path in atlas_text
        assert old_path not in delivery_text

    assert "src/odylith/runtime/reasoning/tribunal_engine.py" in delivery_text
    assert "src/odylith/runtime/reasoning/remediator.py" in delivery_text
