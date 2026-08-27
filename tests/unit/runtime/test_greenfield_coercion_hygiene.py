from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
DOMAIN_INTELLIGENCE = ROOT / "src/odylith/runtime/domain_intelligence"


def test_retired_project_intelligence_binding_authority_is_absent() -> None:
    assert not (DOMAIN_INTELLIGENCE / "project_intelligence_binding.py").exists()
