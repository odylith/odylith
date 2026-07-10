from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from odylith.runtime.domain_intelligence import greenfield_compiled_package_contract
from odylith.runtime.domain_intelligence import greenfield_prewrite_commit_result
from tests.unit.runtime.greenfield_proposal_fixtures import compiled_greenfield_package_fixture


def _valid_preview() -> dict[str, object]:
    return {
        "mode": "applied",
        "backlog": [],
        "components": [],
        "diagrams": [],
        "dashboard_refresh": {"status": "passed"},
        "completion_priority_quality_debt": [],
    }


@pytest.mark.parametrize("key", ("backlog", "components", "diagrams"))
def test_commit_result_preview_requires_every_text_report_collection(key: str) -> None:
    preview = _valid_preview()
    preview.pop(key)

    with pytest.raises(ValueError, match=rf"missing compiled {key} reporting data"):
        greenfield_prewrite_commit_result.require_greenfield_commit_result_preview(preview)


@pytest.mark.parametrize("key", ("backlog", "components", "diagrams"))
def test_commit_result_preview_rejects_non_list_text_report_collection(key: str) -> None:
    preview = _valid_preview()
    preview[key] = {}

    with pytest.raises(ValueError, match=rf"missing compiled {key} reporting data"):
        greenfield_prewrite_commit_result.require_greenfield_commit_result_preview(preview)


@pytest.mark.parametrize("key", ("backlog", "components", "diagrams"))
def test_compiled_package_rejects_incomplete_text_report_before_confirmation(
    tmp_path: Path,
    key: str,
) -> None:
    proposal = {
        "intent": {"title": "Receipt Contract Workspace"},
        "backlog": [{"title": "Prove the receipt contract"}],
        "components": [],
        "diagrams": [],
    }
    package = compiled_greenfield_package_fixture(proposal, repo_root=tmp_path)
    preview = dict(package.commit_result_preview or {})
    preview.pop(key)

    with pytest.raises(ValueError, match=rf"missing compiled {key} reporting data"):
        greenfield_compiled_package_contract.require_complete_compiled_greenfield_package(
            replace(package, commit_result_preview=preview),
            release_selector="0.0.1",
        )
