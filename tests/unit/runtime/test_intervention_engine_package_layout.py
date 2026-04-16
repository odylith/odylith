from __future__ import annotations

import importlib
from pathlib import Path

import pytest

from odylith.runtime.intervention_engine import claim_runtime
from odylith.runtime.intervention_engine import continuity_runtime
from odylith.runtime.intervention_engine import conversation_runtime
from odylith.runtime.intervention_engine import delivery_ledger
from odylith.runtime.intervention_engine import delivery_runtime


def test_conversation_signaling_modules_live_under_intervention_engine() -> None:
    repo_root = Path(__file__).resolve().parents[3]

    assert (repo_root / "src" / "odylith" / "runtime" / "intervention_engine" / "conversation_runtime.py").is_file()
    assert (repo_root / "src" / "odylith" / "runtime" / "intervention_engine" / "delivery_runtime.py").is_file()
    assert (repo_root / "src" / "odylith" / "runtime" / "intervention_engine" / "delivery_ledger.py").is_file()
    assert (repo_root / "src" / "odylith" / "runtime" / "intervention_engine" / "claim_runtime.py").is_file()
    assert (repo_root / "src" / "odylith" / "runtime" / "intervention_engine" / "continuity_runtime.py").is_file()

    assert not (repo_root / "src" / "odylith" / "runtime" / "orchestration" / "odylith_chatter_runtime.py").exists()
    assert not (repo_root / "src" / "odylith" / "runtime" / "orchestration" / "odylith_chatter_delivery_runtime.py").exists()
    assert not (repo_root / "src" / "odylith" / "runtime" / "orchestration" / "chatter_claim_runtime.py").exists()

    assert "runtime/intervention_engine/conversation_runtime.py" in Path(conversation_runtime.__file__).as_posix()
    assert "runtime/intervention_engine/delivery_runtime.py" in Path(delivery_runtime.__file__).as_posix()
    assert "runtime/intervention_engine/delivery_ledger.py" in Path(delivery_ledger.__file__).as_posix()
    assert "runtime/intervention_engine/claim_runtime.py" in Path(claim_runtime.__file__).as_posix()
    assert "runtime/intervention_engine/continuity_runtime.py" in Path(continuity_runtime.__file__).as_posix()


@pytest.mark.parametrize(
    "module_name",
    [
        "odylith.runtime.orchestration.odylith_chatter_runtime",
        "odylith.runtime.orchestration.odylith_chatter_delivery_runtime",
        "odylith.runtime.orchestration.chatter_claim_runtime",
    ],
)
def test_legacy_orchestration_signaling_modules_are_not_importable(module_name: str) -> None:
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module(module_name)
