from __future__ import annotations

import json
from pathlib import Path

from odylith.install.value_engine_migration import MIGRATION_ID
from odylith.install.value_engine_migration import VALUE_CORPUS_RELATIVE_PATH
from odylith.install.value_engine_migration import migrate_visible_intervention_value_engine


def test_value_engine_migration_removes_v010_signal_ranker_artifacts(tmp_path: Path) -> None:
    repo_root = tmp_path / "consumer"
    repo_root.mkdir()
    stale_source_paths = [
        repo_root / "odylith/runtime/source/intervention-signal-ranker-corpus.v1.json",
        repo_root / "odylith/runtime/source/intervention_signal_ranker_calibration.v1.json",
    ]
    for path in stale_source_paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('{"legacy": true}\n', encoding="utf-8")
    runtime_root = repo_root / ".odylith/runtime/versions/0.1.11"
    stale_runtime_path = (
        runtime_root
        / "lib/python3.12/site-packages/odylith/runtime/intervention_engine/signal_ranker.py"
    )
    stale_runtime_path.parent.mkdir(parents=True, exist_ok=True)
    stale_runtime_path.write_text("# legacy ranker\n", encoding="utf-8")
    stale_calibration_path = (
        stale_runtime_path.parent
        / "calibration/intervention_signal_ranker_calibration.v1.json"
    )
    stale_calibration_path.parent.mkdir(parents=True, exist_ok=True)
    stale_calibration_path.write_text('{"legacy": true}\n', encoding="utf-8")

    result = migrate_visible_intervention_value_engine(
        repo_root=repo_root,
        previous_version="0.1.10",
        target_version="0.1.11",
        runtime_root=runtime_root,
    )

    assert result.applied is True
    assert result.migration_id == MIGRATION_ID
    assert all(not path.exists() for path in stale_source_paths)
    assert not stale_runtime_path.exists()
    assert not stale_calibration_path.parent.exists()
    assert (repo_root / VALUE_CORPUS_RELATIVE_PATH).is_file()
    ledger_path = repo_root / result.ledger_path
    assert ledger_path.is_file()
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    assert ledger["backward_compatibility"] == "cut_hard"
    assert "odylith/runtime/source/intervention-signal-ranker-corpus.v1.json" in ledger["removed_paths"]


def test_value_engine_migration_skips_pre_v011_targets(tmp_path: Path) -> None:
    repo_root = tmp_path / "consumer"
    repo_root.mkdir()
    result = migrate_visible_intervention_value_engine(
        repo_root=repo_root,
        previous_version="0.1.9",
        target_version="0.1.10",
    )

    assert result.applied is False
    assert result.skipped_reason == "target_not_in_v0_1_11_migration_window"
    assert not (repo_root / VALUE_CORPUS_RELATIVE_PATH).exists()


def test_value_engine_migration_runs_for_unrecorded_v011_install(tmp_path: Path) -> None:
    repo_root = tmp_path / "consumer"
    repo_root.mkdir()

    result = migrate_visible_intervention_value_engine(
        repo_root=repo_root,
        previous_version="0.1.11",
        target_version="0.1.11",
    )

    assert result.applied is True
    assert (repo_root / result.ledger_path).is_file()
    assert (repo_root / VALUE_CORPUS_RELATIVE_PATH).is_file()


def test_value_engine_migration_is_idempotent_after_ledger_exists(tmp_path: Path) -> None:
    repo_root = tmp_path / "consumer"
    repo_root.mkdir()
    first = migrate_visible_intervention_value_engine(
        repo_root=repo_root,
        previous_version="0.1.10",
        target_version="0.1.11",
    )

    second = migrate_visible_intervention_value_engine(
        repo_root=repo_root,
        previous_version="0.1.11",
        target_version="0.1.11",
    )

    assert first.applied is True
    assert second.applied is False
    assert second.skipped_reason == "target_not_in_v0_1_11_migration_window"
