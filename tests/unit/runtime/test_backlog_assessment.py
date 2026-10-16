"""Unknown Radar assessments survive source, index, and Context Engine boundaries."""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest

from odylith.runtime.context_engine import odylith_context_engine_projection_compiler_runtime as compiler
from odylith.runtime.context_engine import odylith_context_engine_store as store
from odylith.runtime.governance import backlog_assessment as assessment
from odylith.runtime.governance import backlog_authoring as author
from odylith.runtime.governance import legacy_backlog_normalization as normalization
from odylith.runtime.governance import reconcile_plan_workstream_binding as binding
from odylith.runtime.governance import validate_backlog_contract as gate
from odylith.runtime.memory import odylith_projection_snapshot as snapshot
from test_backlog_authoring import _grounded_backlog_args, _seed_backlog_repo


def _args(**overrides):
    args = author._parse_args(["--title", "Public counter triage", *_grounded_backlog_args()])
    for field, value in overrides.items():
        setattr(args, field, value)
    return args


def _create_unknown(root: Path):
    index = _seed_backlog_repo(root)
    args = _args(**assessment.UNASSESSED_BACKLOG_METADATA)
    result = author.create_queued_backlog_items(
        repo_root=root, backlog_index_path=index,
        ideas_root=root / "odylith/radar/source/ideas",
        titles=["Public counter triage", "Resident request routing"], args=args,
    )
    index.write_text(result["backlog_index_text"], encoding="utf-8")
    for filename, content in result["idea_files"].items():
        Path(filename).write_text(content, encoding="utf-8")
    return index, result


def test_actual_authoring_index_validation_preserves_unknown_and_sequence(tmp_path):
    index, result = _create_unknown(tmp_path)
    assert [row["ordering_score"] for row in result["created"]] == [None, None]
    ideas, errors = gate._validate_idea_specs(tmp_path / "odylith/radar/source/ideas", repo_root=tmp_path)
    assert errors == []
    assert gate._validate_backlog_index(backlog_index=index, ideas=ideas, repo_root=tmp_path)[-1] == []
    rows = gate.rows_as_mapping(section=gate.load_backlog_index_snapshot(index)["active"], expected_headers=gate._INDEX_COLS)
    assert [row["idea_id"] for row in rows] == ["B-101", "B-102", "B-103"]
    for idea_id in ("B-102", "B-103"):
        for field, value in assessment.UNASSESSED_BACKLOG_METADATA.items():
            assert ideas[idea_id].metadata[field] == assessment.markdown_value(value)
    assert "score-based rank" not in result["idea_files"][result["created"][0]["idea_path"]]


@pytest.mark.parametrize("field", list(assessment.UNASSESSED_BACKLOG_METADATA))
def test_unassessed_metadata_cannot_omit_any_contract_field(field):
    metadata = {key: assessment.markdown_value(value) for key, value in assessment.UNASSESSED_BACKLOG_METADATA.items()}
    metadata.pop(field)
    errors = []
    assessment.validate_assessment(metadata, errors=errors, path=Path("record.md"))
    assert errors


@pytest.mark.parametrize("field,value", [
    ("commercial_value", 3), ("product_impact", 4), ("market_value", 3),
    ("ordering_score", 0), ("priority", "P1"), ("sizing", "M"),
    ("complexity", "Medium"), ("confidence", "medium"),
    ("assessment_status", "assessed"), ("assessment_provenance", "model_assessed"),
    ("founder_override", True),
])
def test_authoring_rejects_partial_or_falsely_assessed_unknowns(field, value):
    args = _args(**{**assessment.UNASSESSED_BACKLOG_METADATA, field: value})
    with pytest.raises(ValueError):
        author._build_metadata(idea_id="B-001", title="Public counter triage", today=dt.date(2026, 10, 4), args=args)


@pytest.mark.parametrize("score,override,valid", [(None, False, True), (89, False, False), (89, True, True), (0, True, True), (101, True, False)])
def test_assessed_formula_range_and_manual_override(score, override, valid):
    args = _args(ordering_score=score, founder_override=override)
    if not valid:
        with pytest.raises(ValueError):
            assessment.author_assessment(args)
        return
    metadata = assessment.author_assessment(args)
    assert metadata["ordering_score"] == str(100 if score is None else score)
    errors = []
    assessment.validate_assessment(metadata, errors=errors, path=Path("record.md"))
    assert errors == []


def test_index_rejects_fabricated_zero_for_unknown(tmp_path):
    index, result = _create_unknown(tmp_path)
    text = index.read_text().replace("| unassessed | unassessed | unassessed | unassessed | unassessed |", "| unassessed | 0 | unassessed | unassessed | unassessed |", 1)
    index.write_text(text)
    ideas, _ = gate._validate_idea_specs(tmp_path / "odylith/radar/source/ideas", repo_root=tmp_path)
    errors = gate._validate_backlog_index(backlog_index=index, ideas=ideas, repo_root=tmp_path)[-1]
    assert any("unassessed index score" in error for error in errors)


def test_legacy_rationale_normalization_preserves_absent_assessment():
    lines = normalization._normalized_rationale_lines(
        idea_id="B-001", title="Public counter triage", existing_lines=[],
        founder_override=False, today=dt.date(2026, 10, 4), require_ordering=True,
        ordering_score=None,
    )
    assert lines == ["- ranking basis: assessment pending; no numeric ranking assigned."]


def test_execution_rewrite_accepts_unknown_without_score_or_priority(tmp_path):
    index, _ = _create_unknown(tmp_path)
    rows = gate.rows_as_mapping(section=gate.load_backlog_index_snapshot(index)["active"], expected_headers=gate._INDEX_COLS)
    for row in rows:
        row["status"] = "planning"
        row["rank"] = "-"
    binding._rewrite_execution_section(index, execution_rows=rows, today=dt.date(2026, 10, 4))
    execution = gate.rows_as_mapping(section=gate.load_backlog_index_snapshot(index)["execution"], expected_headers=gate._INDEX_COLS)
    assert [row["ordering_score"] for row in execution] == ["100", "unassessed", "unassessed"]


def test_real_context_compiler_and_retrieval_preserve_unknown(tmp_path, monkeypatch):
    _create_unknown(tmp_path)
    compiler.warm_projections(repo_root=tmp_path, force=True, scope="full")
    rows = snapshot.load_snapshot(repo_root=tmp_path)["tables"]["workstreams"]
    assert {row["idea_id"]: row["ordering_score"] for row in rows} == {"B-101": 100, "B-102": None, "B-103": None}
    detail = store.load_backlog_detail(repo_root=tmp_path, workstream_id="B-102")
    assert detail["assessment_status"] == "unassessed"
    assert detail["assessment_provenance"] == "greenfield_provisional_design"
    for field in assessment.NUMERIC_FIELDS:
        assert detail[field] is None
        assert detail["metadata"][field] is None
    listed = store.load_backlog_rows(repo_root=tmp_path)
    unknown = next(row for row in listed["active"] if row["idea_id"] == "B-102")
    assert unknown["ordering_score"] is None
    from odylith.runtime.context_engine import odylith_context_engine_projection_backlog_runtime as projection
    monkeypatch.setattr(projection, "_warm_runtime", lambda **kwargs: False)
    fallback = projection.load_backlog_rows(repo_root=tmp_path)
    fallback_unknown = next(row for row in fallback["active"] if row["idea_id"] == "B-102")
    for field in (*assessment.NUMERIC_FIELDS, "assessment_status", "assessment_provenance"):
        assert fallback_unknown[field] == unknown[field]


def test_out_of_range_override_refuses_before_governed_writes(tmp_path):
    _seed_backlog_repo(tmp_path)
    truth = tmp_path / "odylith"
    before = {path: path.read_bytes() for path in truth.rglob("*") if path.is_file()}
    assert author.main([
        "--repo-root", str(tmp_path), "--title", "Out of range assessment",
        *_grounded_backlog_args(), "--founder-override", "--override-review-date", "2026-10-04",
        "--ordering-score", "101",
    ]) == 2
    after = {path: path.read_bytes() for path in truth.rglob("*") if path.is_file()}
    assert after == before


def test_context_source_fallback_preserves_unknown(tmp_path, monkeypatch):
    from odylith.runtime.context_engine import odylith_context_engine_projection_backlog_runtime as projection
    _create_unknown(tmp_path)
    monkeypatch.setattr(projection, "_warm_runtime", lambda **kwargs: False)
    listed = projection.load_backlog_rows(repo_root=tmp_path)
    unknown = next(row for row in listed["active"] if row["idea_id"] == "B-102")
    for field in assessment.NUMERIC_FIELDS:
        assert unknown[field] is None
    assert unknown["assessment_status"] == "unassessed"
    assert unknown["assessment_provenance"] == "greenfield_provisional_design"
    monkeypatch.setattr(store, "_runtime_backlog_detail", lambda **kwargs: None)
    detail = store.load_backlog_detail(repo_root=tmp_path, workstream_id="B-102")
    for field in assessment.NUMERIC_FIELDS:
        assert detail[field] is None
    assert detail["assessment_provenance"] == "greenfield_provisional_design"


def test_successor_preserves_unassessed_provenance(tmp_path):
    _, result = _create_unknown(tmp_path)
    source, sections = author._parse_metadata_and_sections(Path(result["created"][0]["idea_path"]))
    metadata = binding._build_successor_metadata(
        source_metadata=source, source_id="B-102", successor_id="B-104",
        plan_path="odylith/technical-plans/in-progress/continuation.md", today=dt.date(2026, 10, 4),
    )
    rendered = binding._render_idea_text(metadata=metadata, sections=sections)
    assert "assessment_status: unassessed" in rendered
    assert "assessment_provenance: greenfield_provisional_design" in rendered
    assert "ordering_score: unassessed" in rendered
    errors = []
    assessment.validate_assessment(metadata, errors=errors, path=Path("successor.md"))
    assert errors == []


@pytest.mark.parametrize("score", [None, "unassessed"])
def test_compact_packet_keeps_unknown_state_and_null_without_expanding_metadata(score):
    from odylith.runtime.context_engine import odylith_context_engine_hot_path_packet_finalize_runtime as packets
    source = {**assessment.UNASSESSED_BACKLOG_METADATA, "ordering_score": score, "title": "Not part of compact metadata"}
    compact = packets._compact_workstream_metadata_for_packet(source)
    assert compact == {
        "priority": "unassessed", "ordering_score": None,
        "assessment_status": "unassessed", "assessment_provenance": "greenfield_provisional_design",
    }
    assert packets._compact_workstream_metadata_for_packet({"priority": "P1", "ordering_score": 0}) == {
        "priority": "P1", "ordering_score": "0",
    }


@pytest.mark.parametrize("same_status,first_override,expected_inversion", [
    (True, False, True), (False, False, False), (True, True, False),
])
def test_execution_numeric_order_survives_intervening_unknown(tmp_path, same_status, first_override, expected_inversion):
    index, result = _create_unknown(tmp_path)
    ideas, _ = gate._validate_idea_specs(tmp_path / "odylith/radar/source/ideas", repo_root=tmp_path)
    base = dict(ideas["B-101"].metadata)
    for idea_id, score in (("B-101", "50"), ("B-103", "100")):
        metadata = ideas[idea_id].metadata
        title = metadata["title"]
        metadata.update(base)
        metadata.update(idea_id=idea_id, title=title, ordering_score=score)
        metadata.pop("assessment_status", None)
        metadata.pop("assessment_provenance", None)
    ideas["B-101"].metadata["founder_override"] = "yes" if first_override else "no"
    rows = []
    for idea_id, spec in ideas.items():
        spec.metadata["status"] = "implementation" if idea_id == "B-101" and not same_status else "planning"
        row = {field: spec.metadata.get(field, "") for field in gate._INDEX_COLS}
        row.update(rank="-", link=f"[record]({spec.path.relative_to(tmp_path)})")
        rows.append(row)
    rows.sort(key=lambda row: row["idea_id"])
    text = result["backlog_index_text"]
    header = "| " + " | ".join(gate._INDEX_COLS) + " |\n"
    separator = "| " + " | ".join("---" for _ in gate._INDEX_COLS) + " |\n"
    execution = header + separator + "\n".join("| " + " | ".join(row[field] for field in gate._INDEX_COLS) + " |" for row in rows) + "\n\n"
    start = text.index("## Ranked Active Backlog")
    end = text.index("## Finished")
    text = text[:start] + "## Ranked Active Backlog\n\n" + header + separator + "\n## In Planning/Implementation (Linked to `odylith/technical-plans/in-progress`)\n\n" + execution + text[end:]
    index.write_text(text)
    errors = gate._validate_backlog_index(backlog_index=index, ideas=ideas, repo_root=tmp_path)[-1]
    assert any("execution ranking score inversion `B-103`(100) over `B-101`(50)" in error for error in errors) is expected_inversion
