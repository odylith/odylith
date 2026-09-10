"""Exercise support ownership through the real projection collector and selector."""

from __future__ import annotations

from contextlib import closing
from copy import deepcopy
from itertools import permutations
import json
from pathlib import Path
import sqlite3

import pytest

from odylith.runtime.context_engine import odylith_context_engine_store as store


WORKSTREAMS = ("B-101", "B-102", "B-103")


@pytest.fixture
def projection(tmp_path: Path):
    with closing(sqlite3.connect(":memory:")) as connection:
        connection.row_factory = lambda cursor, row: {
            column[0]: value for column, value in zip(cursor.description, row)
        }
        connection.executescript(
            """
            CREATE TABLE workstreams (
                idea_id TEXT, title TEXT, status TEXT, source_path TEXT,
                section TEXT, priority TEXT, promoted_to_plan TEXT,
                idea_file TEXT, metadata_json TEXT
            );
            CREATE TABLE traceability_edges (
                source_id TEXT, target_kind TEXT, target_id TEXT, relation TEXT
            );
            CREATE TABLE components (component_id TEXT, workstreams_json TEXT);
            """
        )
        yield connection, tmp_path
        store.clear_runtime_process_caches(repo_root=tmp_path)


def _workstreams(connection, owners=WORKSTREAMS):
    connection.executemany(
        "INSERT INTO workstreams VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (
                owner, f"Workstream {owner}", "implementation",
                f"odylith/radar/source/ideas/{owner}.md", "active", "P1", "",
                f"odylith/radar/source/ideas/{owner}.md", "{}",
            )
            for owner in owners
        ],
    )


def _references(connection, refs):
    connection.executemany(
        "INSERT INTO traceability_edges VALUES (?, ?, ?, 'support')", refs
    )


def _topology(connection, kind):
    components = []
    diagrams = []
    if kind in {"components", "both"}:
        components = ["shared-component", "extra-component"]
        connection.executemany(
            "INSERT INTO components VALUES (?, ?)",
            [
                (components[0], json.dumps(WORKSTREAMS[:2])),
                (components[1], json.dumps(WORKSTREAMS[:1])),
            ],
        )
    if kind in {"diagrams", "both"}:
        diagrams = ["shared-diagram", "extra-diagram", "another-diagram"]
        connection.executemany(
            "INSERT INTO traceability_edges VALUES (?, 'diagram', ?, 'related_diagram_ids')",
            [
                ("B-101", diagrams[0]), ("B-102", diagrams[0]),
                ("B-101", diagrams[1]), ("B-101", diagrams[2]),
            ],
        )
    return components, diagrams


def _collect(projection, paths, *, components=(), diagrams=()):
    connection, repo_root = projection
    return store._collect_impacted_workstreams(
        connection, repo_root=repo_root, changed_paths=paths,
        component_ids=components, diagram_ids=diagrams,
    )


@pytest.mark.parametrize("path", ["docs/runbooks/operations.md", "docs/renamed-guide.md"])
@pytest.mark.parametrize("kind", ["runbook", "doc"])
@pytest.mark.parametrize("topology", ["components", "diagrams", "both"])
@pytest.mark.parametrize("owners", list(permutations(WORKSTREAMS)))
@pytest.mark.parametrize("duplicate", [False, True])
def test_shared_support_cannot_gain_an_owner_from_topology(
    projection, path, kind, topology, owners, duplicate,
):
    connection, _ = projection
    _workstreams(connection, owners)
    refs = [(owner, kind, path) for owner in owners]
    _references(connection, refs + ([(owners[0], kind, f"./{path}")] * 3 if duplicate else []))
    components, diagrams = _topology(connection, topology)

    candidates = _collect(projection, [path], components=components, diagrams=diagrams)
    selection = store._workstream_selection(connection=connection, candidates=candidates)

    assert selection["state"] == "ambiguous", selection
    assert selection["selected_workstream"] == {}
    assert selection["strong_candidate_count"] == 0
    assert {row["entity_id"] for row in candidates} == set(WORKSTREAMS)
    for row in candidates:
        evidence = row["evidence"]
        assert evidence["matched_paths"] == [path]
        assert evidence["counters"] == {f"trace_{kind}_exact": 1}
        assert evidence["broad_only"] is True
        assert evidence["broad_shared_signal_count"] == 1
    assert candidates[0]["evidence"]["matched_components"] == components
    assert candidates[0]["evidence"]["matched_diagrams"] == diagrams
    assert _collect(projection, [path], components=components, diagrams=diagrams) == candidates


@pytest.mark.parametrize("match", ["exact", "watch"])
def test_shared_support_is_shared_across_reference_types(projection, match):
    connection, _ = projection
    _workstreams(connection)
    target = "docs/operations" if match == "watch" else "docs/operations/guide.md"
    changed = "docs/operations/guide.md"
    _references(connection, [("B-101", "doc", target), ("B-102", "runbook", target)])
    components, diagrams = _topology(connection, "both")

    candidates = _collect(projection, [changed], components=components, diagrams=diagrams)
    selection = store._workstream_selection(connection=connection, candidates=candidates)

    assert selection["state"] == "ambiguous"
    assert selection["selected_workstream"] == {}
    assert candidates[0]["evidence"]["broad_only"] is True


def test_typed_shared_support_does_not_inherit_implementation_strength(projection):
    connection, _ = projection
    _workstreams(connection)
    path = "src/odylith/bundle/assets/docs/operations.md"
    _references(connection, [(owner, "doc", path) for owner in WORKSTREAMS])
    components, diagrams = _topology(connection, "both")
    candidates = _collect(projection, [path], components=components, diagrams=diagrams)

    selection = store._workstream_selection(connection=connection, candidates=candidates)

    assert selection["state"] == "ambiguous"
    assert selection["strong_candidate_count"] == 0
    assert selection["selected_workstream"] == {}


def test_explicit_owner_remains_available_for_shared_support(projection):
    connection, _ = projection
    _workstreams(connection)
    path = "docs/runbooks/operations.md"
    _references(connection, [(owner, "runbook", path) for owner in WORKSTREAMS])
    components, diagrams = _topology(connection, "both")
    candidates = _collect(projection, [path], components=components, diagrams=diagrams)

    selection = store._workstream_selection(
        connection=connection, candidates=candidates, explicit_workstream="B-102",
    )

    assert selection["state"] == "explicit"
    assert selection["selected_workstream"]["entity_id"] == "B-102"
    assert selection["selected_workstream"]["evidence"]["matched_paths"] == [path]


@pytest.mark.parametrize("path, kind", [
    ("src/odylith/runtime/sample.py", "code"),
    ("contracts/sample.json", "code"),
    ("odylith/radar/source/ideas/B-102.md", "direct"),
])
def test_real_ownership_wins_alongside_shared_support(projection, path, kind):
    connection, _ = projection
    _workstreams(connection)
    shared = "docs/runbooks/operations.md"
    _references(connection, [(owner, "runbook", shared) for owner in WORKSTREAMS])
    if kind != "direct":
        _references(connection, [("B-102", kind, path)])
    components, diagrams = _topology(connection, "both")
    candidates = _collect(projection, [shared, path], components=components, diagrams=diagrams)

    selection = store._workstream_selection(connection=connection, candidates=candidates)

    assert selection["state"] == "inferred_confident"
    assert selection["selected_workstream"]["entity_id"] == "B-102"
    assert selection["selected_workstream"]["evidence"]["strong_signal_count"] > 0
    assert set(selection["selected_workstream"]["evidence"]["matched_paths"]) == {path, shared}


@pytest.mark.parametrize("kind", ["doc", "runbook"])
def test_dedicated_documentation_ownership_is_not_globally_weakened(projection, kind):
    connection, _ = projection
    _workstreams(connection)
    path = "docs/runbooks/dedicated-slice.md"
    _references(connection, [
        ("B-101", kind, path), ("B-101", kind, f"./{path}"),
        ("B-999", kind, path),
    ])
    components, _ = _topology(connection, "components")
    candidates = _collect(projection, [path], components=components)

    selection = store._workstream_selection(connection=connection, candidates=candidates)

    assert selection["state"] == "inferred_confident"
    assert selection["selected_workstream"]["entity_id"] == "B-101"
    assert candidates[0]["evidence"]["broad_only"] is False
    assert candidates[0]["evidence"]["broad_shared_signal_count"] == 0


@pytest.mark.parametrize("shared", [False, True])
def test_memory_confirmation_retains_the_current_ownership_boundary(projection, shared):
    connection, _ = projection
    _workstreams(connection)
    path = "docs/runbooks/operations.md"
    _references(connection, [(owner, "runbook", path) for owner in (WORKSTREAMS if shared else WORKSTREAMS[:1])])
    candidates = _collect(projection, [path])

    selection = store._workstream_selection(
        connection=connection, candidates=candidates,
        judgment_hint={"workstream_id": "B-101", "confidence": "high"},
    )

    if shared:
        assert selection["state"] == "ambiguous"
        assert selection["selected_workstream"] == {}
        assert selection["ambiguity_class"] == "low_signal"
    else:
        assert selection["state"] == "inferred_confident"
        assert selection["ambiguity_class"] == "judgment_memory_confirmed"
        assert selection["selected_workstream"]["entity_id"] == "B-101"


@pytest.mark.parametrize("targets", [
    ("docs/neutral", "docs/neutral/guide.md", "docs/neutral/guide.md"),
    ("docs/neutral", "docs/neutral", "docs/neutral/guide.md"),
    ("docs", "docs/neutral", "docs/neutral/guide.md"),
])
@pytest.mark.parametrize("owners", list(permutations(WORKSTREAMS)))
@pytest.mark.parametrize("remembered", [False, True])
def test_overlapping_support_references_share_each_changed_path(
    projection, targets, owners, remembered,
):
    connection, _ = projection
    _workstreams(connection, owners)
    refs = dict(zip(WORKSTREAMS, zip(("doc", "doc", "runbook"), targets)))
    _references(connection, [(owner, *refs[owner]) for owner in owners])
    _references(connection, [("B-101", "doc", f"./{targets[0]}")])
    connection.execute("INSERT INTO components VALUES ('component-0', ?)", (json.dumps(["B-101"]),))
    path = "docs/neutral/guide.md"

    candidates = _collect(projection, [path], components=["component-0"])
    selection = store._workstream_selection(
        connection=connection, candidates=candidates,
        judgment_hint={"workstream_id": "B-101", "confidence": "high"} if remembered else None,
    )

    assert selection["state"] == "ambiguous", selection
    assert selection["selected_workstream"] == {}
    assert selection["strong_candidate_count"] == 0
    assert {row["entity_id"] for row in candidates} == set(WORKSTREAMS)
    for row in candidates:
        assert row["evidence"]["matched_paths"] == [path]
        assert row["evidence"]["broad_only"] is True
        assert row["evidence"]["broad_shared_signal_count"] == 1
        assert row["evidence"]["non_shared_signal_count"] == 0
    assert _collect(projection, [path], components=["component-0"]) == candidates


def test_support_sharedness_is_local_to_each_changed_path_and_cache_request(projection):
    connection, _ = projection
    _workstreams(connection)
    shared = "docs/neutral/shared.md"
    dedicated = "docs/neutral/dedicated.md"
    _references(connection, [
        ("B-101", "doc", "docs/neutral"),
        ("B-102", "doc", shared),
        ("B-103", "runbook", shared),
    ])
    connection.execute("INSERT INTO components VALUES ('component-0', ?)", (json.dumps(["B-101"]),))
    for paths in ([shared], [dedicated], [shared, dedicated], [dedicated, shared], [shared], [dedicated]):
        candidates = _collect(projection, paths, components=["component-0"])
        owner = next(row for row in candidates if row["entity_id"] == "B-101")
        evidence = owner["evidence"]
        assert evidence["broad_shared_signal_count"] == int(shared in paths)
        assert evidence["non_shared_signal_count"] == int(dedicated in paths)
        assert set(evidence["matched_paths"]) == set(paths)
        selection = store._workstream_selection(connection=connection, candidates=candidates)
        if dedicated in paths:
            assert selection["state"] == "inferred_confident"
            assert selection["selected_workstream"]["entity_id"] == "B-101"
        else:
            assert selection["state"] == "ambiguous"
            assert selection["selected_workstream"] == {}


@pytest.mark.parametrize("other", ["docs/other", "docs/owned-adjacent"])
def test_unrelated_watched_subtrees_do_not_share_ownership(projection, other):
    connection, _ = projection
    _workstreams(connection)
    _references(connection, [
        ("B-101", "doc", "docs/owned"),
        ("B-102", "doc", other),
        ("B-103", "runbook", f"{other}/guide.md"),
    ])
    connection.execute("INSERT INTO components VALUES ('component-0', ?)", (json.dumps(["B-101"]),))
    owned = "docs/owned/guide.md"
    candidates = _collect(projection, [owned, f"{other}/guide.md"], components=["component-0"])
    evidence = next(row for row in candidates if row["entity_id"] == "B-101")["evidence"]

    assert evidence["broad_only"] is False
    assert evidence["broad_shared_signal_count"] == 0
    assert evidence["matched_paths"] == [owned]
    selection = store._workstream_selection(connection=connection, candidates=candidates)
    assert selection["state"] == "inferred_confident"
    assert selection["selected_workstream"]["entity_id"] == "B-101"


@pytest.mark.parametrize("path, kind", [
    ("src/odylith/runtime/sample.py", "code"),
    ("contracts/sample.json", "code"),
    ("docs/neutral/guide.md", "code"),
    ("odylith/radar/source/ideas/B-102.md", "direct"),
])
def test_exact_authority_survives_overlapping_support_on_the_same_path(projection, path, kind):
    connection, _ = projection
    _workstreams(connection)
    _references(connection, [
        ("B-101", "doc", str(Path(path).parent)),
        ("B-103", "runbook", path),
    ])
    if kind != "direct":
        _references(connection, [("B-102", kind, path)])
    components, diagrams = _topology(connection, "both")
    candidates = _collect(projection, [path], components=components, diagrams=diagrams)

    selection = store._workstream_selection(connection=connection, candidates=candidates)

    assert selection["state"] == "inferred_confident"
    assert selection["selected_workstream"]["entity_id"] == "B-102"
    assert selection["selected_workstream"]["evidence"]["strong_signal_count"] > 0
    explicit = store._workstream_selection(
        connection=connection, candidates=candidates, explicit_workstream="B-101",
    )
    assert explicit["state"] == "explicit"
    assert explicit["selected_workstream"]["entity_id"] == "B-101"


@pytest.mark.parametrize("trace_kind", ["trace_doc", "trace_code", "trace_runbook", "", "  "])
def test_path_evidence_preserves_typed_order_defaults_and_cached_rows(projection, monkeypatch, trace_kind):
    connection, _ = projection
    _workstreams(connection, ["B-101"])
    direct = "odylith/radar/source/ideas/B-101.md"
    traced = "docs/neutral/guide.md"
    _references(connection, [("B-101", "doc", traced)])
    cached_rows = store._cached_projection_rows
    add_evidence = store._add_workstream_path_evidence
    snapshots = {}
    events = []

    def projection_rows(**kwargs):
        rows = cached_rows(**kwargs)
        name = kwargs["cache_name"]
        if name in {"workstream_direct_match_rows", "workstream_traceability_match_rows"}:
            if name not in snapshots:
                snapshots[name] = deepcopy(rows)
            assert rows == snapshots[name]
        if name == "workstream_traceability_match_rows":
            return [{**row, "source_kind": trace_kind} for row in rows]
        return rows

    def record_evidence(candidate, **kwargs):
        events.append((kwargs["source_kind"], kwargs["changed_path"], kwargs["match_type"]))
        add_evidence(candidate, **kwargs)

    monkeypatch.setattr(store, "_cached_projection_rows", projection_rows)
    monkeypatch.setattr(store, "_add_workstream_path_evidence", record_evidence)
    results = []
    for _ in range(2):
        events.clear()
        candidates = _collect(projection, [traced, direct])
        assert events == [("direct", direct, "exact"), (trace_kind.strip() or "trace_doc", traced, "exact")]
        assert candidates[0]["evidence"]["matched_paths"] == [direct, traced]
        results.append(candidates)
    assert results[0] == results[1]
    assert all("source_kind" not in row for row in snapshots["workstream_direct_match_rows"])
