from __future__ import annotations

import json
from pathlib import Path

from odylith.install.consumer_runtime_repair import repair_stale_consumer_intervention_noise


def _write_jsonl(path: Path, events: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(event, sort_keys=True) for event in events) + "\n",
        encoding="utf-8",
    )


def test_repair_stale_consumer_intervention_noise_removes_product_visibility_events(tmp_path: Path) -> None:
    stream_path = tmp_path / "odylith" / "compass" / "runtime" / "agent-stream.v1.jsonl"
    _write_jsonl(
        stream_path,
        [
            {
                "host_family": "claude",
                "kind": "ambient_signal",
                "summary": (
                    "Odylith History: Casebook already remembers CB-122. "
                    "Why it matters: This conversation is touching a previously captured failure lane."
                ),
            },
            {
                "host_family": "claude",
                "kind": "intervention_card",
                "summary": "Odylith is ready to speak, but this chat has not shown the Odylith moment yet.",
                "workstreams": ["B-096"],
            },
            {
                "host_family": "claude",
                "kind": "workspace_activity",
                "summary": "Recent workspace activity across tracked paths: src/app.py",
            },
        ],
    )

    result = repair_stale_consumer_intervention_noise(repo_root=tmp_path, consumer_repo=True)

    remaining = stream_path.read_text(encoding="utf-8")
    assert result.changed is True
    assert result.removed_events == 2
    assert result.repaired_streams == ("odylith/compass/runtime/agent-stream.v1.jsonl",)
    assert "CB-122" not in remaining
    assert "B-096" not in remaining
    assert "Recent workspace activity" in remaining


def test_repair_stale_consumer_intervention_noise_preserves_local_matching_records(tmp_path: Path) -> None:
    workstream_path = tmp_path / "odylith" / "radar" / "source" / "ideas" / "B-096.md"
    bug_path = tmp_path / "odylith" / "casebook" / "bugs" / "CB-122.md"
    workstream_path.parent.mkdir(parents=True, exist_ok=True)
    bug_path.parent.mkdir(parents=True, exist_ok=True)
    workstream_path.write_text("idea_id: B-096\n\n## Problem\nLocal workstream.\n", encoding="utf-8")
    bug_path.write_text("- Bug ID: CB-122\n\n- Description: Local bug.\n", encoding="utf-8")
    stream_path = tmp_path / "odylith" / "compass" / "runtime" / "agent-stream.v1.jsonl"
    _write_jsonl(
        stream_path,
        [
            {
                "host_family": "claude",
                "kind": "workspace_activity",
                "summary": "Updated local B-096 and CB-122 records.",
            }
        ],
    )
    before = stream_path.read_text(encoding="utf-8")

    result = repair_stale_consumer_intervention_noise(repo_root=tmp_path, consumer_repo=True)

    assert result.changed is False
    assert stream_path.read_text(encoding="utf-8") == before


def test_repair_stale_consumer_intervention_noise_scans_agent_and_legacy_codex_streams(
    tmp_path: Path,
) -> None:
    agent_stream = tmp_path / "odylith" / "compass" / "runtime" / "agent-stream.v1.jsonl"
    codex_stream = tmp_path / "odylith" / "compass" / "runtime" / "codex-stream.v1.jsonl"
    stale_event = {
        "host_family": "claude",
        "kind": "intervention_card",
        "summary": "Odylith is ready to speak, but this chat has not shown the Odylith moment yet.",
        "workstreams": ["B-096"],
    }
    kept_event = {
        "host_family": "codex",
        "kind": "workspace_activity",
        "summary": "Recent workspace activity across tracked paths: src/app.py",
    }
    _write_jsonl(agent_stream, [stale_event, kept_event])
    _write_jsonl(codex_stream, [stale_event, kept_event])

    result = repair_stale_consumer_intervention_noise(repo_root=tmp_path, consumer_repo=True)

    assert result.changed is True
    assert result.removed_events == 2
    assert result.repaired_streams == (
        "odylith/compass/runtime/agent-stream.v1.jsonl",
        "odylith/compass/runtime/codex-stream.v1.jsonl",
    )
    assert "B-096" not in agent_stream.read_text(encoding="utf-8")
    assert "B-096" not in codex_stream.read_text(encoding="utf-8")
    assert "Recent workspace activity" in agent_stream.read_text(encoding="utf-8")
    assert "Recent workspace activity" in codex_stream.read_text(encoding="utf-8")


def test_repair_stale_consumer_intervention_noise_skips_product_repo(tmp_path: Path) -> None:
    stream_path = tmp_path / "odylith" / "compass" / "runtime" / "agent-stream.v1.jsonl"
    _write_jsonl(
        stream_path,
        [
            {
                "host_family": "claude",
                "kind": "intervention_card",
                "summary": "Odylith is ready to speak, but this chat has not shown the Odylith moment yet.",
                "workstreams": ["B-096"],
            }
        ],
    )
    before = stream_path.read_text(encoding="utf-8")

    result = repair_stale_consumer_intervention_noise(repo_root=tmp_path, consumer_repo=False)

    assert result.changed is False
    assert result.skipped_reason == "not a consumer repo"
    assert stream_path.read_text(encoding="utf-8") == before
