"""Extracted narration presentation remains part of the worker's source epoch."""

from pathlib import Path

import pytest

from odylith.runtime.surfaces import compass_standup_brief_maintenance as maintenance


@pytest.mark.parametrize("module", ["compass_standup_brief_narrator.py", "compass_standup_brief_status.py"])
def test_narration_presentation_source_change_invalidates_worker_epoch(tmp_path: Path, module: str) -> None:
    source = tmp_path / "src" / "odylith" / "runtime" / "surfaces" / module
    source.parent.mkdir(parents=True)
    source.write_text("# Prior narration presentation\n", encoding="utf-8")
    prior = maintenance._worker_epoch(repo_root=tmp_path)
    source.write_text("# Updated narration presentation and availability copy\n", encoding="utf-8")

    assert maintenance._worker_epoch(repo_root=tmp_path) != prior
