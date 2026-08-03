from __future__ import annotations

import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@pytest.fixture(autouse=True)
def _disable_desktop_browser_launches(monkeypatch: pytest.MonkeyPatch) -> None:
    """Automated tests may render dashboards but never open desktop browser tabs."""

    monkeypatch.setenv("ODYLITH_NO_BROWSER", "1")
