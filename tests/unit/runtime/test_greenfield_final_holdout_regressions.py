"""Disclosure guards for retired final-holdout evidence only."""

from __future__ import annotations

import json
from pathlib import Path


_FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "fixtures/greenfield-release-corpus"


def _retired_fixture(name: str) -> dict[str, object]:
    return json.loads((_FIXTURE_ROOT / name).read_text(encoding="utf-8"))


def test_failed_final_holdout_is_marked_disclosed_and_retired() -> None:
    payload = _retired_fixture("retired-ba25-final-holdout-regressions.v1.json")
    assert payload["version"] == "odylith.greenfield.retired-holdout-regression.v1"
    assert payload["disclosed"] is True
    assert len(payload["cases"]) == 24


def test_87e277_failed_holdout_is_marked_disclosed_and_retired() -> None:
    payload = _retired_fixture("retired-87e277-final-holdout-regressions.v1.json")
    assert payload["version"] == "odylith.greenfield.retired-holdout-regression.v1"
    assert payload["disclosed"] is True
    assert len(payload["cases"]) == 24
    assert len(payload["annotations"]) == 24


def test_cf410_failed_holdout_is_marked_disclosed_and_retired() -> None:
    payload = _retired_fixture("retired-cf410-final-holdout-regressions.v1.json")
    assert payload["version"] == "odylith.greenfield.retired-holdout-regression.v1"
    assert payload["disclosed"] is True
    assert payload["retired_from"]["holdout_sha256"] == (
        "2713e5b4cbd0abe0c7cc1e517c063c29ca3cdd029c2db5de764ecc8c03c9cfb5"
    )
    assert len(payload["cases"]) == 24
    assert len(payload["annotations"]) == 24


def test_1c54_failed_holdout_is_marked_disclosed_and_retired() -> None:
    payload = _retired_fixture("retired-1c54-final-holdout-regressions.v1.json")
    assert payload["version"] == "odylith.greenfield.retired-holdout-regression.v1"
    assert payload["disclosed"] is True
    assert payload["retired_from"] == {
        "product_revision": "1c54cb3403d482bdb72559aae5f9a52185cc242e",
        "holdout_sha256": "d48f7180bfd129a02609ac17289b1cf3233eeeba1f313a7aac16564e2a1a5a7e",
        "evaluation_manifest_sha256": "c1efaaf96b12e14c5c81387bd189797fafb1616f40e08680c5d82481d99df09c",
        "result_sha256": "8c6286bb28ccfa7c490d259861499ed8979863b20da4e9ccb6ded41156a6da90",
        "evaluated_on": "2026-08-09",
    }
    assert len(payload["cases"]) == 24
    assert len(payload["annotations"]) == 24
