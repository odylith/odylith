from __future__ import annotations

import copy
import datetime as dt
import hashlib
import json
import os
from pathlib import Path

import pytest

from odylith.runtime.common import derivation_provenance
from odylith.runtime.context_engine import judgment_memory_records as judgment
from odylith.runtime.context_engine import memory_record_policy as policy
from odylith.runtime.context_engine import odylith_context_engine_store as store
from odylith.runtime.context_engine import tooling_context_retrieval as retrieval
from odylith.runtime.context_engine import tooling_context_packet_builder as packet_builder
from odylith.runtime.context_engine import tooling_context_budgeting as budgeting
from odylith.runtime.context_engine import odylith_context_engine_projection_compiler_runtime as compiler
from odylith.runtime.context_engine import odylith_context_engine_projection_search_runtime as search
from odylith.runtime.memory import odylith_memory_backend as backend
from odylith.runtime.memory import odylith_projection_bundle as bundle
from odylith.runtime.memory import odylith_projection_snapshot as snapshot
from odylith.runtime.memory import tooling_memory_contracts as contracts

NOW = dt.datetime(2026, 10, 4, 12, tzinfo=dt.timezone.utc)
FRESH = "2026-10-04T11:00:00Z"


def provenance(root: Path, *, generation: int = 0) -> dict:
    return derivation_provenance.build_derivation_provenance(
        repo_root=root, projection_scope="reasoning", projection_fingerprint="a" * 64,
        sync_generation=generation, code_version="b" * 64,
    )


def record(root: Path, *, role="current_truth", validity="current", date=FRESH, **values) -> dict:
    return policy.record(
        values, role=role, validity=validity,
        source_ref="odylith/registry/source/components/service/CURRENT_SPEC.md",
        source_fingerprint="c" * 64, confirmed_utc=date, provenance=provenance(root),
    )


def starter(root: Path, *, metadata="", confirmed=FRESH) -> tuple[dict, dict]:
    source_ref = "odylith/radar/source/ideas/2026-10/service.md"
    path = root / source_ref
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("idea_id: B-001\nstatus: planning\n" + metadata + "\n# Service\n")
    memory = judgment.source_record(
        store=store, root=root, source_ref=source_ref, role="current_truth",
        observed_utc=FRESH, provenance=provenance(root),
    )
    memory["confirmed_utc"] = confirmed
    row = {"path": "src/service", "workstream_id": "B-001", "status": "current", "confirmed_utc": confirmed, "memory_record": memory}
    state = {"odylith_compiler": {"provenance": provenance(root)}}
    return row, state


def write_hint(root: Path, row: dict, state: dict) -> None:
    path = store.judgment_memory_path(repo_root=root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"starter_slice": row}))
    store.write_runtime_state(repo_root=root, payload=state)


@pytest.mark.parametrize("validity", ["superseded", "refuted", "rejected", "unknown"])
def test_invalid_history_cannot_outscore_an_old_active_constraint(tmp_path, validity):
    current = record(tmp_path, date="2020-01-01T00:00:00Z", constraint="proof_required")
    historical = record(tmp_path, role="historical_learning", validity=validity)
    ranked = policy.rank_records([
        {"entity_id": "recent_failed_path", "score": 10000, "memory_record": historical},
        {"entity_id": "active_constraint", "score": 1, "memory_record": current},
    ], now=NOW)
    assert ranked[0]["entity_id"] == "active_constraint"
    assert ranked[0]["memory_usefulness"]["current_authority"] is True
    assert ranked[0]["memory_usefulness"]["decay_factor"] == 1
    assert ranked[1]["memory_usefulness"]["use"] == "historical_learning"
    assert policy.assess(historical, now=NOW)["current_authority"] is False


def test_legacy_record_and_conflicting_current_claims_remain_unknown(tmp_path):
    assert policy.assess({"role": "current_truth", "validity": "current"})["current_authority"] is False
    rows = [
        {"score": 20, "memory_record": record(tmp_path, claim_key="review_owner", claim_value=value)}
        for value in ("reviewer", "publisher")
    ]
    ranked = policy.rank_records(rows, now=NOW)
    assert all(row["memory_usefulness"]["current_authority"] is False for row in ranked)
    assert all(row["memory_usefulness"]["reason"] == "contradictory_current_claims" for row in ranked)


def test_decay_only_ranks_within_learning_and_retains_failed_mechanism(tmp_path):
    recent = record(tmp_path, role="historical_learning", date=FRESH)
    old = record(tmp_path, role="historical_learning", date="2020-01-01T00:00:00Z", validity="refuted")
    ranked = policy.rank_records([
        {"entity_id": "old_failure", "score": 100, "memory_record": old},
        {"entity_id": "recent_failure", "score": 100, "memory_record": recent},
    ], now=NOW)
    assert [row["entity_id"] for row in ranked] == ["recent_failure", "old_failure"]
    assert ranked[1]["memory_usefulness"]["use"] == "historical_learning"
    assert ranked[1]["memory_usefulness"]["score"] > 0


@pytest.mark.parametrize("field,value", [("projection_fingerprint", "d" * 64), ("sync_generation", 1)])
def test_hint_refuses_changed_derivation_provenance(tmp_path, monkeypatch, field, value):
    row, state = starter(tmp_path, confirmed=dt.datetime.now(dt.timezone.utc).isoformat())
    state["odylith_compiler"]["provenance"][field] = value
    write_hint(tmp_path, row, state)
    assert store._load_judgment_workstream_hint(repo_root=tmp_path, changed_paths=["src/service/app.py"]) == {}


@pytest.mark.parametrize("metadata", ["superseded_by: B-002\n", "memory_validity: refuted\n", "memory_validity: rejected\n"])
def test_hint_refuses_explicit_source_invalidation(tmp_path, metadata):
    row, state = starter(tmp_path, metadata=metadata, confirmed=dt.datetime.now(dt.timezone.utc).isoformat())
    write_hint(tmp_path, row, state)
    assert store._load_judgment_workstream_hint(repo_root=tmp_path, changed_paths=["src/service/app.py"]) == {}


def test_current_hint_survives_warm_reads_but_refuses_changed_source(tmp_path, monkeypatch):
    row, state = starter(tmp_path, confirmed=dt.datetime.now(dt.timezone.utc).isoformat())
    write_hint(tmp_path, row, state)
    first = store._load_judgment_workstream_hint(repo_root=tmp_path, changed_paths=["src/service/app.py"])
    assert first["memory_admission"] == "current_source_confirmed"
    assert first["workstream_id"] == "B-001"
    source = tmp_path / row["memory_record"]["source_ref"]
    original = Path.read_bytes
    reads = []

    def counted(path):
        if path == source:
            reads.append(path)
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", counted)
    assert store._load_judgment_workstream_hint(repo_root=tmp_path, changed_paths=["src/service/app.py"]) == first
    assert reads == []
    source.write_text(source.read_text() + "\nChanged source contract.\n")
    assert store._load_judgment_workstream_hint(repo_root=tmp_path, changed_paths=["src/service/app.py"]) == {}
    assert len(reads) == 1


def test_rebuild_does_not_reconfirm_old_evidence_or_change_its_generation(tmp_path):
    old, state = starter(tmp_path)
    previous = {**old, "first_seen_utc": FRESH, "last_seen_utc": FRESH}
    state["odylith_compiler"]["provenance"]["sync_generation"] = 1
    rebuilt = judgment.build_starter(
        store=store, root=tmp_path, current={}, previous=previous,
        rows=[], packets=[{"workstream": "B-001", "changed_paths": ["src/service/app.py"], "bootstrapped_at": FRESH}],
        sessions=[], observed_utc="2026-10-05T11:00:00Z", runtime_state=state,
    )
    assert rebuilt["confirmed_utc"] == FRESH
    assert rebuilt["last_seen_utc"] == FRESH
    assert rebuilt["observed_utc"] == "2026-10-05T11:00:00Z"
    assert rebuilt["memory_record"]["provenance"]["sync_generation"] == 0


def test_new_slice_cannot_inherit_previous_workstream(tmp_path):
    old, state = starter(tmp_path)
    rebuilt = judgment.build_starter(
        store=store, root=tmp_path, current={"path": "src/different"}, previous=old,
        rows=[], packets=[], sessions=[], observed_utc=FRESH, runtime_state=state,
    )
    assert rebuilt["workstream_id"] == ""
    assert rebuilt["confirmed_utc"] == ""
    assert rebuilt["memory_record"]["validity"] == "unknown"


def test_legacy_hint_does_not_promote_low_signal_selection(tmp_path):
    write_hint(tmp_path, {"path": "src/service", "workstream_id": "B-001", "status": "established"}, {})
    assert store._load_judgment_workstream_hint(repo_root=tmp_path, changed_paths=["src/service/app.py"]) == {}
    candidate = {"entity_id": "B-001", "evidence": {"score": 1, "strong_signal_count": 1, "matched_paths": ["src/service/app.py"], "counters": {"direct_exact": 1}}}
    selected = store._workstream_selection(connection=None, candidates=[candidate], judgment_hint={"workstream_id": "B-001", "confidence": "high"})
    assert selected["state"] == "ambiguous"


def test_source_record_snapshot_retrieval_and_compact_transport_agree(tmp_path):
    source = tmp_path / "odylith/registry/source/components/service/CURRENT_SPEC.md"
    source.parent.mkdir(parents=True)
    body = "# Service\n\nPublication requires a completed review.\n"
    source.write_text(body)
    tables = {
        "components": [{"component_id": "service", "name": "Service", "status": "active", "owner": "product", "spec_ref": source.relative_to(tmp_path).as_posix(), "aliases_json": "[]", "workstreams_json": "[]", "diagrams_json": "[]", "metadata_json": json.dumps({"spec_last_updated": "2020-01-01"})}],
        "component_specs": [{"component_id": "service", "markdown": body}],
    }
    policy.annotate_projection_tables(tables, provenance=provenance(tmp_path), observed_utc=FRESH)
    payload = snapshot.write_snapshot(repo_root=tmp_path, projection_fingerprint="a" * 64, projection_scope="reasoning", input_fingerprint="input", tables=tables, projection_state={}, updated_projections=["components"], provenance=provenance(tmp_path))
    connection = store._ProjectionConnection(repo_root=tmp_path, snapshot=snapshot.load_snapshot(repo_root=tmp_path))
    entity = store._entity_by_kind_id(connection, kind="component", entity_id="service")
    retrieved = store._projection_exact_search_results(connection, repo_root=tmp_path, query="service", kinds=["component"], limit=4)
    expected = tables["components"][0]["memory_record"]
    assert entity["memory_record"] == retrieved[0]["memory_record"] == expected
    assert expected["source_fingerprint"] == hashlib.sha256(body.encode()).hexdigest()
    assert policy.assess(expected, expected_provenance=payload["provenance"], now=NOW)["current_authority"] is True
    direct = backend.build_backend_materialization_inputs_from_projection_tables(tables=tables)
    connected = backend.build_backend_materialization_inputs(connection=connection)
    assert direct["documents"] == connected["documents"]
    assert json.loads(direct["documents"][0]["provenance_json"])["memory_record"] == expected
    compact = contracts._compact_component_rows([entity], limit=1)
    assert compact[0]["memory_record"]["source_fingerprint"] == expected["source_fingerprint"]
    assert compact[0]["memory_record"]["provenance"]["sync_generation"] == 0


def test_real_indexed_and_compiler_memory_contract_parity(tmp_path):
    assert backend.backend_dependencies_available(), "Declared memory backend test dependencies must be installed"
    tables = {"workstreams": [
        {"idea_id": "B-001", "title": "Avoid TTL stale source reuse", "source_path": "odylith/radar/source/ideas/2026-10/failure.md", "search_body": "A failed TTL mechanism hides source fingerprint drift.", "metadata_json": "{}", "section": "finished"},
    ]}
    policy.annotate_projection_tables(tables, provenance=provenance(tmp_path), observed_utc=FRESH)
    inputs = backend.build_backend_materialization_inputs_from_projection_tables(tables=tables)
    bundle.write_bundle(repo_root=tmp_path, documents=inputs["documents"], edges=[], projection_fingerprint="a" * 64, projection_scope="reasoning", input_fingerprint=inputs["input_fingerprint"], provenance=provenance(tmp_path))
    result = backend.materialize_local_backend(repo_root=tmp_path, projection_fingerprint="a" * 64, projection_scope="reasoning", provenance=provenance(tmp_path))
    assert result["ready"] is True
    exact = backend.exact_lookup(repo_root=tmp_path, query="B-001", limit=1)
    sparse = backend.sparse_search(repo_root=tmp_path, query="fingerprint", limit=1)
    assert exact[0]["memory_record"] == sparse[0]["memory_record"] == tables["workstreams"][0]["memory_record"]
    assert sparse[0]["memory_usefulness"]["use"] == "historical_learning"


def test_guidance_authority_precedes_high_scoring_rejected_learning(tmp_path):
    current = record(tmp_path, date="2020-01-01")
    old = record(tmp_path, role="historical_learning", validity="rejected")
    catalog = {"chunks": [
        {"chunk_id": "failed-path", "title": "Rejected TTL reuse", "canonical_source": "odylith/agents-guidelines/failed.md", "note_kind": "tooling_policy", "path_refs": ["src/service/app.py"], "memory_record": old},
        {"chunk_id": "active-policy", "title": "Fingerprint must match", "canonical_source": current["source_ref"], "note_kind": "guardrail", "task_families": ["implementation"], "memory_record": current},
    ]}
    selected = retrieval.selected_guidance_chunks({}, guidance_catalog=catalog, changed_paths=["src/service/app.py"], family_hint="implementation")
    assert selected[0]["chunk_id"] == "active-policy"
    assert selected[1]["actionability"]["actionable"] is False
    brief = retrieval.compact_guidance_brief(selected)
    compact, _ = contracts._compact_guidance_source_rows(brief, limit=2)
    assert compact[0]["memory_record"]["validity"] == "current"
    assert compact[1]["memory_record"]["validity"] == "rejected"
    assert compact[1]["memory_record"]["role"] == "historical_learning"


def test_sensitive_record_source_is_not_compacted(tmp_path):
    row = {"memory_record": record(tmp_path)}
    row["memory_record"]["source_ref"] = "src/odylith/private_key.py"
    assert contracts._compact_memory_record(row) == {}


@pytest.mark.parametrize("invalid", ["wrong_generation", "invalid_version"])
def test_inadmissible_current_claim_cannot_poison_valid_current_claim(tmp_path, invalid):
    current = record(tmp_path, claim_key="approval_owner", claim_value="reviewer")
    copied = record(tmp_path, claim_key="approval_owner", claim_value="publisher")
    if invalid == "wrong_generation":
        copied["provenance"]["sync_generation"] = 9
    else:
        copied["version"] = "unsupported.v0"
    selected = backend._rank_rows_with_query_match(
        rows=[
            {"kind": "workstream", "entity_id": "copied", "title": "approval", "score": 1000, "provenance_json": json.dumps({"memory_record": copied})},
            {"kind": "workstream", "entity_id": "current", "title": "approval", "score": 1, "provenance_json": json.dumps({"memory_record": current})},
        ], query="approval", limit=1, exact=False, expected_provenance=provenance(tmp_path),
    )
    assert selected[0]["entity_id"] == "current"
    assert selected[0]["memory_usefulness"]["reason"] == "current_source"


def test_independent_current_evidence_survives_memory_only_bootstrap_recursion(tmp_path):
    previous, state = starter(tmp_path)
    rows = [{"idea_id": "B-001", "section": "active", "link": f"[source]({previous['memory_record']['source_ref']})"}]
    packet = {
        "workstream": "B-001", "changed_paths": ["src/service/app.py"],
        "selection_state": "inferred_confident", "selection_ambiguity_class": "resolved",
        "bootstrapped_at": "2026-10-04T12:00:00Z",
    }
    accepted = judgment.build_starter(
        store=store, root=tmp_path, current=previous, previous=previous, rows=rows,
        packets=[packet], sessions=[], observed_utc="2026-10-04T12:01:00Z", runtime_state=state,
    )
    assert accepted["confirmed_utc"] == packet["bootstrapped_at"]
    assert policy.assess(accepted["memory_record"], expected_provenance=provenance(tmp_path))["current_authority"]
    selected = store._workstream_selection(
        connection=None, candidates=[{
            "entity_id": "B-001", "path": previous["memory_record"]["source_ref"],
            "evidence": {"score": 1, "strong_signal_count": 1, "matched_paths": ["src/service/app.py"], "counters": {"direct_exact": 1}},
        }], judgment_hint={
            "workstream_id": "B-001", "memory_admission": "current_source_confirmed",
            "memory_record": accepted["memory_record"],
        },
    )
    assert selected["state"] == "inferred_confident"
    assert selected["ambiguity_class"] == "judgment_memory_confirmed"
    packet.update(selection_ambiguity_class=selected["ambiguity_class"], bootstrapped_at="2026-10-05T12:00:00Z")
    carried = judgment.build_starter(
        store=store, root=tmp_path, current=previous, previous=accepted, rows=rows,
        packets=[packet], sessions=[], observed_utc=packet["bootstrapped_at"], runtime_state=state,
    )
    assert carried["confirmed_utc"] == accepted["confirmed_utc"]
    assert carried["memory_record"]["source_fingerprint"] == accepted["memory_record"]["source_fingerprint"]


def test_session_observation_cannot_renew_confirmation_and_legacy_is_unknown(tmp_path, monkeypatch):
    first_stamp = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    confirmed = first_stamp.isoformat().replace("+00:00", "Z")
    observed = (first_stamp + dt.timedelta(minutes=1)).isoformat().replace("+00:00", "Z")
    monkeypatch.setattr(store, "_utc_now", lambda: confirmed)
    kwargs = dict(
        repo_root=tmp_path, session_id="memory-test", workstream="B-001",
        touched_paths=[], explicit_paths=[], repo_dirty_paths=[], analysis_paths=[],
        generated_surfaces=[], intent="Build service", claimed_paths=["src/service"],
    )
    accepted = store.register_session_state(**kwargs, selection_state="inferred_confident", selection_ambiguity_class="resolved")
    assert accepted["evidence_confirmed_utc"] == confirmed
    monkeypatch.setattr(store, "_utc_now", lambda: observed)
    carried = store.register_session_state(**kwargs, selection_state="inferred_confident", selection_ambiguity_class="judgment_memory_confirmed")
    assert carried["updated_utc"] == observed
    assert carried["evidence_confirmed_utc"] == accepted["evidence_confirmed_utc"]
    legacy = store.register_session_state(**{**kwargs, "session_id": "legacy"})
    assert legacy["evidence_confirmed_utc"] == ""


def test_actual_compiler_backend_and_fallback_keep_active_constraints_before_history(tmp_path, monkeypatch):
    sources = {
        "current": "odylith/radar/source/ideas/2026-10/current.md",
        "history": "odylith/radar/source/ideas/2026-10/history.md",
        "plan": "odylith/technical-plans/in-progress/2026-10/current.md",
        "bug": "odylith/casebook/bugs/current.md",
    }
    for key, ref in sources.items():
        path = tmp_path / ref
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"idea_id: {'B-001' if key == 'current' else 'B-002'}\nupdated: {'2020-01-01' if key != 'history' else '2026-10-04'}\n# Approval\nReview must precede publication.\n")
    backlog = {
        "active": [{"idea_id": "B-001", "title": "Approval", "status": "planning", "link": f"[current]({sources['current']})"}],
        "finished": [{"idea_id": "B-002", "title": "Approval", "status": "finished", "link": f"[history]({sources['history']})"}],
    }
    monkeypatch.setattr(compiler, "_projection_names_for_scope", lambda scope: ("workstreams", "plans", "bugs"))
    monkeypatch.setattr(compiler, "_load_backlog_projection", lambda **kwargs: backlog)
    monkeypatch.setattr(compiler, "_load_plan_projection", lambda **kwargs: {"active": [{"Plan": sources["plan"], "Status": "in-progress", "Updated": "2020-01-01"}]})
    monkeypatch.setattr(compiler, "_load_bug_projection", lambda **kwargs: [{"Bug ID": "CB-001", "Title": "Approval", "Status": "Open", "Link": f"[bug]({sources['bug']})", "Date": "2020-01-01"}])
    built = search.warm_projections(repo_root=tmp_path, scope="reasoning", force=True)
    assert built["odylith_memory_backend"]["ready"], built["odylith_memory_backend"]
    rows = snapshot.load_snapshot(repo_root=tmp_path)["tables"]
    assert rows["workstreams"][0]["memory_record"]["role"] == "current_truth"
    assert rows["workstreams"][1]["memory_record"]["role"] == "historical_learning"
    assert rows["plans"][0]["memory_record"]["role"] == rows["bugs"][0]["memory_record"]["role"] == "current_truth"
    indexed = store.search_entities_payload(repo_root=tmp_path, query="Approval", kinds=["workstream"], limit=1)
    assert indexed["results"][0]["entity_id"] == "B-001"
    monkeypatch.setattr(backend, "backend_dependencies_available", lambda: False)
    monkeypatch.setattr(search, "_local_backend_match_for_requested_scope", lambda **kwargs: (False, "reasoning", built["projection_fingerprint"]))
    fallback = store.search_entities_payload(repo_root=tmp_path, query="Approval", kinds=["workstream"], limit=1)
    assert fallback["results"][0]["entity_id"] == "B-001"
    assert fallback["results"][0]["memory_record"] == indexed["results"][0]["memory_record"]
    compact = contracts._compact_memory_record(fallback["results"][0])
    assert compact["memory_record"]["provenance"] == fallback["results"][0]["memory_record"]["provenance"]
    assert policy.assess(compact["memory_record"], expected_provenance=built["odylith_compiler"]["provenance"])["current_authority"]
    assert compact["memory_usefulness"]["reason"] == "current_source"
    first_fingerprint = built["projection_fingerprint"]
    monkeypatch.setattr(compiler, "compiler_code_version", lambda: "d" * 64)
    assert search.projection_input_fingerprint(repo_root=tmp_path, scope="reasoning") != first_fingerprint
    assert search._warm_runtime_can_reuse_snapshot(repo_root=tmp_path, scope="reasoning", requested_fingerprint=first_fingerprint) is False
    rebuilt = search.warm_projections(repo_root=tmp_path, scope="reasoning")
    assert rebuilt["updated_projections"]
    assert snapshot.load_snapshot(repo_root=tmp_path)["tables"]["workstreams"][0]["memory_record"]["provenance"]["code_version"] == "d" * 64
    reused = search.warm_projections(repo_root=tmp_path, scope="reasoning")
    assert reused["updated_projections"] == []
    monkeypatch.setattr(derivation_provenance, "active_sync_generation", lambda **kwargs: (1, True, "new-evidence"))
    assert search._warm_runtime_can_reuse_snapshot(repo_root=tmp_path, scope="reasoning", requested_fingerprint=rebuilt["projection_fingerprint"]) is False
    assert search._warm_runtime(repo_root=tmp_path, runtime_mode="auto", reason="current_generation", scope="reasoning")
    assert snapshot.load_snapshot(repo_root=tmp_path)["provenance"]["sync_generation"] == 1
    monkeypatch.setattr(search, "warm_projections", lambda **kwargs: pytest.fail("unchanged generation must reuse ready memory"))
    assert search._warm_runtime(repo_root=tmp_path, runtime_mode="auto", reason="same_generation", scope="reasoning")


def test_unsupported_nested_metadata_does_not_get_upgraded_to_current_truth(tmp_path):
    copied = record(tmp_path)
    copied["version"] = "unsupported.v0"
    rebuilt = policy.record({"memory_record": copied}, provenance=provenance(tmp_path))
    assert rebuilt["role"] == "observation"
    assert rebuilt["validity"] == "unknown"


@pytest.mark.parametrize("replacement", ["status: finished", "idea_id: B-002"])
def test_exact_source_change_with_restored_mtime_invalidates_hint_and_parsed_header(tmp_path, monkeypatch, replacement):
    row, state = starter(tmp_path, confirmed=dt.datetime.now(dt.timezone.utc).isoformat())
    write_hint(tmp_path, row, state)
    changed_paths = ["src/service/app.py"]
    assert store._load_judgment_workstream_hint(repo_root=tmp_path, changed_paths=changed_paths)
    source = tmp_path / row["memory_record"]["source_ref"]
    before = source.stat()
    original = source.read_text()
    target = "status: planning" if replacement.startswith("status:") else "idea_id: B-001"
    changed = original.replace(target, replacement)
    assert len(changed.encode()) == len(original.encode())
    source.write_text(changed)
    os.utime(source, ns=(before.st_atime_ns, before.st_mtime_ns))
    after = source.stat()
    assert (after.st_size, after.st_mtime_ns) == (before.st_size, before.st_mtime_ns)
    assert after.st_ctime_ns != before.st_ctime_ns
    assert store._load_judgment_workstream_hint(repo_root=tmp_path, changed_paths=changed_paths) == {}
    # Even a newly observed SHA cannot turn the stale cached owner/lifecycle into current evidence.
    refreshed = judgment.source_record(
        store=store, root=tmp_path, source_ref=row["memory_record"]["source_ref"], role="current_truth",
        observed_utc=FRESH, provenance=provenance(tmp_path),
    )
    assert refreshed["source_fingerprint"] == hashlib.sha256(changed.encode()).hexdigest()
    refreshed["confirmed_utc"] = row["memory_record"]["confirmed_utc"]
    write_hint(tmp_path, {**row, "memory_record": refreshed}, state)
    assert store._load_judgment_workstream_hint(repo_root=tmp_path, changed_paths=changed_paths) == {}


@pytest.mark.parametrize("invalid", ["generation", "historical", "refuted", "unknown", "legacy"])
def test_final_guidance_admission_owns_instruction_actionability_and_compact_packet(tmp_path, invalid):
    memory = record(tmp_path)
    expected = provenance(tmp_path)
    if invalid == "generation":
        expected["sync_generation"] = 1
    elif invalid == "historical":
        memory["role"] = "historical_learning"
    elif invalid == "legacy":
        memory.pop("version")
    else:
        memory["validity"] = invalid
    catalog = {"chunks": [{
        "chunk_id": "source-guidance", "note_kind": "guardrail", "title": "Review first",
        "canonical_source": memory["source_ref"], "memory_record": memory,
        "path_refs": ["src/service/app.py"], "risk_class": "release_safety",
    }]}
    selected = retrieval.selected_guidance_chunks(
        {}, guidance_catalog=catalog, changed_paths=["src/service/app.py"], expected_provenance=expected,
    )
    row = selected[0]
    assert row["memory_usefulness"]["current_authority"] is False
    assert row["actionability"]["actionable"] is False
    assert row["actionability"]["direct"] is False
    assert row["actionability"]["signals"] == ["read_source"]
    assert row["actionability"]["read_path"] == memory["source_ref"]
    brief = retrieval.compact_guidance_brief(selected)
    compact, _ = contracts._compact_guidance_source_rows(brief, limit=1)
    assert compact[0].get("actionable", False) is False
    assert compact[0].get("direct", False) is False
    assert compact[0]["memory_usefulness"]["current_authority"] is False
    assert compact[0]["read_path"] == memory["source_ref"]


def test_current_guidance_keeps_instruction_signals_after_final_admission(tmp_path):
    memory = record(tmp_path)
    catalog = {"chunks": [{
        "chunk_id": "current-guidance", "note_kind": "guardrail", "title": "Review first",
        "canonical_source": memory["source_ref"], "memory_record": memory,
        "path_refs": ["src/service/app.py"],
    }]}
    selected = retrieval.selected_guidance_chunks(
        {}, guidance_catalog=catalog, changed_paths=["src/service/app.py"], expected_provenance=provenance(tmp_path),
    )
    assert selected[0]["memory_usefulness"]["current_authority"] is True
    assert selected[0]["actionability"]["actionable"] is True
    assert "follow_matched_path" in selected[0]["actionability"]["signals"]
    assert "guardrail" in selected[0]["actionability"]["signals"]


def test_actual_aggregate_packet_budget_retains_admitted_memory_metadata_at_existing_row_caps(tmp_path):
    expected = provenance(tmp_path)
    bundle.write_bundle(
        repo_root=tmp_path, documents=[], edges=[], projection_fingerprint="a" * 64,
        projection_scope="reasoning", input_fingerprint="aggregate-control", provenance=expected,
    )
    source_records = {}

    def source_record(ref):
        body = "# Current review constraint\nReview must precede publication.\n"
        path = tmp_path / ref
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body)
        memory = policy.record(
            role="current_truth", validity="current", source_ref=ref,
            source_fingerprint=hashlib.sha256(body.encode()).hexdigest(),
            evidence_utc="2020-01-01", provenance=expected,
        )
        source_records[ref] = memory
        return memory

    # Existing selection cap is eight guidance rows; warm components/workstreams each cap at four.
    catalog = {"chunks": [
        {"chunk_id": f"review-{index}", "note_kind": "guardrail", "title": f"Review constraint {index}",
         "canonical_source": f"odylith/agents-guidelines/review-{index}.md",
         "memory_record": source_record(f"odylith/agents-guidelines/review-{index}.md"),
         "path_refs": ["src/service/app.py"]}
        for index in range(8)
    ]}
    workstreams = [
        {"entity_id": f"B-{index + 1:03d}", "title": f"Service delivery {index}", "status": "implementation",
         "path": f"odylith/radar/source/ideas/2026-10/service-{index}.md",
         "memory_record": source_record(f"odylith/radar/source/ideas/2026-10/service-{index}.md")}
        for index in range(4)
    ]
    components = [
        {"entity_id": f"service-{index}", "title": f"Service {index}",
         "path": f"odylith/registry/source/components/service-{index}/CURRENT_SPEC.md",
         "memory_record": source_record(f"odylith/registry/source/components/service-{index}/CURRENT_SPEC.md")}
        for index in range(4)
    ]
    selection = {"state": "inferred_confident", "ambiguity_class": "resolved", "selected_workstream": workstreams[0]}
    packet = packet_builder.finalize_packet(
        repo_root=tmp_path, packet_kind="bootstrap_session", packet_state="compact",
        payload={"candidate_workstreams": workstreams, "components": components, "changed_paths": ["src/service/app.py"]},
        changed_paths=["src/service/app.py"], explicit_paths=[], shared_only_input=False,
        selection_state="inferred_confident", workstream_selection=selection,
        candidate_workstreams=workstreams, components=components, diagrams=[],
        docs=[row["path"] for row in components], recommended_commands=["odylith validate plan-all"],
        recommended_tests=[], engineering_notes={}, miss_recovery={},
        full_scan_recommended=False, full_scan_reason="", guidance_catalog=catalog,
        delivery_profile="full",
    )
    budget = budgeting.packet_budget(packet_kind="bootstrap_session", packet_state="compact")
    serialized_bytes = len(json.dumps(packet, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode())
    assert serialized_bytes <= budget["max_bytes"]
    assert packet["packet_metrics"]["within_budget"] is True

    def mappings(value):
        if isinstance(value, dict):
            yield value
            for child in value.values():
                yield from mappings(child)
        elif isinstance(value, list):
            for child in value:
                yield from mappings(child)

    retained = [row for row in mappings(packet) if isinstance(row.get("memory_record"), dict)]
    assert len(retained) >= 3
    retained_sources = {row["memory_record"]["source_ref"] for row in retained}
    assert workstreams[0]["path"] in retained_sources
    current_guidance = [row for row in retained if row.get("chunk_id") and row.get("actionability", {}).get("actionable")]
    assert current_guidance
    for row in retained:
        memory = row["memory_record"]
        assert memory["source_fingerprint"] == source_records[memory["source_ref"]]["source_fingerprint"]
        assert memory["provenance"] == expected
        assert policy.assess(memory, expected_provenance=expected)["current_authority"] is True
    print(json.dumps({
        "aggregate_packet_bytes": serialized_bytes, "existing_max_bytes": budget["max_bytes"],
        "retained_metadata_rows": len(retained), "retained_distinct_sources": len(retained_sources),
        "retained_current_actionable_guidance_rows": len(current_guidance),
        "budget_truncation": packet.get("truncation", {}).get("packet_budget", {}),
    }, sort_keys=True))
