import json
from pathlib import Path

from odylith.runtime.governance import build_traceability_graph
from odylith.runtime.governance import traceability_freshness


def _release_events_path(repo_root: Path) -> Path:
    path = repo_root / "odylith" / "radar" / "source" / "releases" / "release-assignment-events.v1.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _write_graph_with_current_fingerprint(repo_root: Path, graph_path: Path) -> None:
    graph_path.parent.mkdir(parents=True, exist_ok=True)
    graph_path.write_text(
        json.dumps(
            {
                "version": "v1",
                "source_fingerprint": traceability_freshness.traceability_source_fingerprint(
                    repo_root=repo_root,
                ).as_dict(),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def test_traceability_graph_freshness_accepts_current_source_fingerprint(tmp_path: Path) -> None:
    _release_events_path(tmp_path).write_text(
        '{"event":"add","idea_id":"B-001","release_id":"release-0-1-14"}\n',
        encoding="utf-8",
    )
    graph_path = tmp_path / "odylith" / "radar" / "traceability-graph.v1.json"
    _write_graph_with_current_fingerprint(tmp_path, graph_path)

    assert traceability_freshness.traceability_graph_is_fresh(
        repo_root=tmp_path,
        graph_path=graph_path,
    )


def test_traceability_freshness_rebuilds_when_release_events_change(
    tmp_path: Path,
    monkeypatch,  # noqa: ANN001
) -> None:
    release_events = _release_events_path(tmp_path)
    release_events.write_text(
        '{"event":"add","idea_id":"B-001","release_id":"release-0-1-14"}\n',
        encoding="utf-8",
    )
    graph_path = tmp_path / "odylith" / "radar" / "traceability-graph.v1.json"
    _write_graph_with_current_fingerprint(tmp_path, graph_path)
    release_events.write_text(
        '{"event":"add","idea_id":"B-001","release_id":"release-0-1-15"}\n',
        encoding="utf-8",
    )
    calls: list[list[str]] = []

    def _fake_traceability_build(argv: list[str]) -> int:
        calls.append(list(argv))
        _write_graph_with_current_fingerprint(tmp_path, graph_path)
        return 0

    monkeypatch.setattr(build_traceability_graph, "main", _fake_traceability_build)

    assert traceability_freshness.ensure_traceability_graph_fresh(
        repo_root=tmp_path,
        graph_path=graph_path,
    )
    assert calls == [
        [
            "--repo-root",
            str(tmp_path.resolve()),
            "--output",
            "odylith/radar/traceability-graph.v1.json",
        ]
    ]
    assert traceability_freshness.traceability_graph_is_fresh(
        repo_root=tmp_path,
        graph_path=graph_path,
    )
