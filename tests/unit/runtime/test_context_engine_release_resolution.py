from __future__ import annotations

import json
from pathlib import Path

from odylith.runtime.context_engine import odylith_context_engine_projection_runtime
from odylith.runtime.context_engine import odylith_context_engine_store as store


class _Cursor:
    def __init__(self, *, rows: list[dict[str, object]] | None = None, row: dict[str, object] | None = None) -> None:
        self._rows = list(rows or [])
        self._row = row

    def fetchall(self) -> list[dict[str, object]]:
        return list(self._rows)

    def fetchone(self) -> dict[str, object] | None:
        return self._row


class _ReleaseConnection:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self._rows = list(rows)

    def execute(self, sql: str, _params: tuple[object, ...] = ()) -> _Cursor:
        normalized = " ".join(sql.split())
        if "FROM releases" in normalized:
            return _Cursor(rows=self._rows)
        return _Cursor()


class _MixedConnection:
    def __init__(
        self,
        *,
        releases: list[dict[str, object]] | None = None,
        workstreams: list[dict[str, object]] | None = None,
    ) -> None:
        self._releases = list(releases or [])
        self._workstreams = list(workstreams or [])

    def execute(self, sql: str, _params: tuple[object, ...] = ()) -> _Cursor:
        normalized = " ".join(sql.split())
        if "FROM releases" in normalized:
            return _Cursor(rows=self._releases)
        if "FROM workstreams" in normalized:
            return _Cursor(rows=self._workstreams)
        if "FROM components" in normalized or "FROM plans" in normalized:
            return _Cursor(rows=[])
        return _Cursor()


def _release_row(*, release_id: str, alias: str, version: str, tag: str, effective_name: str) -> dict[str, object]:
    return {
        "release_id": release_id,
        "display_label": effective_name,
        "status": "active",
        "source_path": "odylith/radar/source/releases/releases.v1.json",
        "version": version,
        "tag": tag,
        "effective_name": effective_name,
        "aliases_json": json.dumps([alias]),
        "active_workstreams_json": json.dumps(["B-101"]),
        "metadata_json": json.dumps({"release_id": release_id}),
    }


def _workstream_row(*, idea_id: str, title: str, active_release_aliases: list[str], active_release_version: str) -> dict[str, object]:
    return {
        "idea_id": idea_id,
        "title": title,
        "status": "implementation",
        "source_path": f"odylith/radar/source/ideas/{idea_id.lower()}.md",
        "section": "execution",
        "priority": "P1",
        "promoted_to_plan": "",
        "idea_file": f"{idea_id.lower()}.md",
        "metadata_json": json.dumps(
            {
                "active_release_aliases": active_release_aliases,
                "active_release_version": active_release_version,
            }
        ),
    }


def test_entity_by_kind_id_resolves_release_by_alias_version_tag_and_name() -> None:
    connection = _ReleaseConnection(
        [_release_row(release_id="release-0-1-11", alias="current", version="0.1.11", tag="v0.1.11", effective_name="Launch Title")]
    )

    for selector in ("current", "current release", "release:release-0-1-11", "0.1.11", "v0.1.11", "Launch Title"):
        entity = store._entity_by_kind_id(connection, kind="release", entity_id=selector)  # noqa: SLF001
        assert entity is not None
        assert entity["kind"] == "release"
        assert entity["entity_id"] == "release-0-1-11"


def test_resolve_context_entity_prefers_release_aliases_before_runtime_search(tmp_path: Path, monkeypatch) -> None:
    connection = _ReleaseConnection(
        [_release_row(release_id="release-next", alias="next", version="0.1.12", tag="v0.1.12", effective_name="Next Cut")]
    )

    monkeypatch.setattr(
        store,
        "search_entities_payload",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("release alias resolution should not search")),
    )

    entity, matches, lookup = store._resolve_context_entity(  # noqa: SLF001
        connection,
        repo_root=tmp_path,
        ref="next release",
        kind=None,
    )

    assert entity is not None
    assert matches == []
    assert entity["kind"] == "release"
    assert entity["entity_id"] == "release-next"
    assert lookup["resolution_mode"] == "release_alias"


def test_resolve_context_entity_prefers_release_alias_before_workstream_alias(tmp_path: Path) -> None:
    connection = _MixedConnection(
        releases=[
            _release_row(
                release_id="release-0-1-11",
                alias="current",
                version="0.1.11",
                tag="v0.1.11",
                effective_name="Launch Title",
            )
        ],
        workstreams=[
            _workstream_row(
                idea_id="B-047",
                title="Tribunal Default Diagnosis Triggers",
                active_release_aliases=["current"],
                active_release_version="0.1.11",
            )
        ],
    )

    entity, matches, lookup = store._resolve_context_entity(  # noqa: SLF001
        connection,
        repo_root=tmp_path,
        ref="current",
        kind=None,
    )

    assert matches == []
    assert entity is not None
    assert entity["kind"] == "release"
    assert entity["entity_id"] == "release-0-1-11"
    assert lookup["resolution_mode"] == "release_alias"


def test_resolve_context_entity_prefers_release_version_before_workstream_release_metadata(tmp_path: Path) -> None:
    connection = _MixedConnection(
        releases=[
            _release_row(
                release_id="release-0-1-11",
                alias="current",
                version="0.1.11",
                tag="v0.1.11",
                effective_name="Launch Title",
            )
        ],
        workstreams=[
            _workstream_row(
                idea_id="B-047",
                title="Tribunal Default Diagnosis Triggers",
                active_release_aliases=["current"],
                active_release_version="0.1.11",
            )
        ],
    )

    entity, matches, lookup = store._resolve_context_entity(  # noqa: SLF001
        connection,
        repo_root=tmp_path,
        ref="0.1.11",
        kind=None,
    )

    assert matches == []
    assert entity is not None
    assert entity["kind"] == "release"
    assert entity["entity_id"] == "release-0-1-11"
    assert lookup["resolution_mode"] == "release_alias"


def test_load_release_projection_reads_live_release_source_even_when_traceability_graph_is_stale(tmp_path: Path) -> None:
    ideas_root = tmp_path / "odylith" / "radar" / "source" / "ideas" / "2026-04"
    ideas_root.mkdir(parents=True, exist_ok=True)
    ideas_root.joinpath("2026-04-09-b-067.md").write_text(
        (
            "status: finished\n\n"
            "idea_id: B-067\n\n"
            "title: Old target\n\n"
            "date: 2026-04-09\n\n"
            "priority: P1\n\n"
            "commercial_value: 4\n\n"
            "product_impact: 4\n\n"
            "market_value: 4\n\n"
            "impacted_parts: release truth\n\n"
            "sizing: S\n\n"
            "complexity: Medium\n\n"
            "ordering_score: 100\n\n"
            "ordering_rationale: test fixture\n\n"
            "confidence: high\n\n"
            "founder_override: no\n\n"
            "promoted_to_plan:\n\n"
            "execution_model: standard\n\n"
            "workstream_type: standalone\n\n"
            "workstream_parent:\n\n"
            "workstream_children:\n\n"
            "workstream_depends_on:\n\n"
            "workstream_blocks:\n\n"
            "related_diagram_ids:\n\n"
            "workstream_reopens:\n\n"
            "workstream_reopened_by:\n\n"
            "workstream_split_from:\n\n"
            "workstream_split_into:\n\n"
            "workstream_merged_into:\n\n"
            "workstream_merged_from:\n\n"
            "supersedes:\n\n"
            "superseded_by:\n\n"
            "## Problem\nGrounded fixture coverage for problem in this synthetic workstream.\n"
        ),
        encoding="utf-8",
    )
    ideas_root.joinpath("2026-04-09-b-068.md").write_text(
        ideas_root.joinpath("2026-04-09-b-067.md").read_text(encoding="utf-8").replace("B-067", "B-068").replace("Old target", "New target").replace("finished", "implementation", 1),
        encoding="utf-8",
    )

    releases_root = tmp_path / "odylith" / "radar" / "source" / "releases"
    releases_root.mkdir(parents=True, exist_ok=True)
    (releases_root / "releases.v1.json").write_text(
        json.dumps(
            {
                "version": "v1",
                "updated_utc": "2026-04-09T16:00:00Z",
                "aliases": {"current": "release-0-1-11"},
                "releases": [
                    {
                        "release_id": "release-0-1-11",
                        "status": "active",
                        "version": "0.1.11",
                        "tag": "v0.1.11",
                        "name": "",
                        "notes": "",
                        "created_utc": "2026-04-08",
                        "shipped_utc": "",
                        "closed_utc": "",
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (releases_root / "release-assignment-events.v1.jsonl").write_text(
        "\n".join(
            [
                json.dumps({"action": "add", "release_id": "release-0-1-11", "workstream_id": "B-067", "recorded_at": "2026-04-09T01:00:00Z"}),
                json.dumps({"action": "add", "release_id": "release-0-1-11", "workstream_id": "B-068", "recorded_at": "2026-04-09T02:00:00Z"}),
                json.dumps({"action": "remove", "release_id": "release-0-1-11", "workstream_id": "B-067", "recorded_at": "2026-04-09T03:00:00Z"}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    traceability_path = tmp_path / "odylith" / "radar" / "traceability-graph.v1.json"
    traceability_path.parent.mkdir(parents=True, exist_ok=True)
    traceability_path.write_text(
        json.dumps(
            {
                "releases": [
                    {
                        "release_id": "release-0-1-11",
                        "display_label": "0.1.11",
                        "active_workstreams": ["B-067"],
                        "completed_workstreams": [],
                        "aliases": ["current"],
                    }
                ],
                "release_aliases": {"current": {"release_id": "release-0-1-11"}},
                "current_release": {
                    "release_id": "release-0-1-11",
                    "display_label": "0.1.11",
                    "active_workstreams": ["B-067"],
                    "completed_workstreams": [],
                    "aliases": ["current"],
                },
                "next_release": {},
                "release_summary": {"active_assignment_count": 1},
                "workstreams": [],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    projection = odylith_context_engine_projection_runtime._load_release_projection(repo_root=tmp_path)  # noqa: SLF001

    assert projection["current_release"]["active_workstreams"] == ["B-068"]
    assert projection["current_release"]["completed_workstreams"] == ["B-067"]
    release_row = projection["releases"][0]
    assert json.loads(release_row["active_workstreams_json"]) == ["B-068"]
    assert projection["workstreams"]["B-067"]["release_history_summary"] == "Removed from 0.1.11"
