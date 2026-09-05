from __future__ import annotations

from dataclasses import replace
import hashlib
import sys

from tests.greenfield_matrix_campaign_test_support import SCRIPTS_ROOT


if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from greenfield_matrix_corpus_provenance import GreenfieldCaseProvenance
from greenfield_matrix_campaign import MatrixCampaignConfig
from greenfield_matrix_campaign import campaign_summary
from greenfield_matrix_clarification import FOCUSED_FIRST_PATH_QUESTION
from greenfield_matrix_metamorphic import evaluate_metamorphic_outputs
from greenfield_matrix_types import GreenfieldArtifactCounts
from greenfield_matrix_types import GreenfieldMatrixResult
from greenfield_matrix_types import GreenfieldQualityVerdict
from greenfield_preconfirm_matrix_cases import GreenfieldMatrixCase
from greenfield_preconfirm_matrix_cases import case_evidence
from odylith.runtime.domain_intelligence.greenfield_atomic_fact_ledger import (
    append_atomic_source_spans,
    atomic_fact_ledger_hash,
    build_atomic_fact_ledger,
)
from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    AUTHORED_SEMANTICS_VERSION,
    authored_relation_set_sha256,
    combined_prompt_evidence_source,
)


HASH = "c" * 64
SOURCE_HASH = "d" * 64
SEMANTIC_DIGEST = "a" * 64
DESCRIPTION_FIRST_PATH = "An operator records one evidence decision and reviews the accepted result."
TOPIC_FIRST_PATH = "A reviewer logs one governed decision and inspects the approved outcome."

_FACTS_BY_CASE_ID: dict[str, dict[str, object]] = {
    "source-001-description": {
        "title": "Evidence Workspace",
        "product_story": "Evidence Workspace helps an operator review a governed evidence decision.",
        "state_object": "An evidence decision tracks its status and accepted result.",
        "first_path": DESCRIPTION_FIRST_PATH,
        "proof_boundary": "The first release proves one accepted evidence decision.",
        "human_actors": ["operator"],
    },
    "source-001-topic": {
        "title": "Evidence Workspace",
        "product_story": "The Evidence Workspace lets a reviewer inspect a controlled decision record.",
        "state_object": "The decision record preserves its state and approved outcome.",
        "first_path": TOPIC_FIRST_PATH,
        "proof_boundary": "Release one demonstrates one approved decision.",
        "human_actors": ["reviewer"],
    },
}

_EVENT_PARTS_BY_CASE_ID = {
    "source-001-description": ("operator", "records", "one evidence decision", "accepted result"),
    "source-001-topic": ("reviewer", "logs", "one governed decision", "approved outcome"),
}


def test_metamorphic_output_accepts_paraphrase_equivalent_typed_meaning() -> None:
    cases = _cases()

    assert DESCRIPTION_FIRST_PATH != TOPIC_FIRST_PATH

    evaluation = evaluate_metamorphic_outputs(
        cases=cases,
        results=tuple(_result(case) for case in cases),
        semantic_digests=_semantic_digests(cases),
    )

    assert evaluation["status"] == "passed"
    assert evaluation["complete_group_count"] == 1


def test_metamorphic_output_rejects_changed_readback_hash() -> None:
    cases = _cases()
    results = (_result(cases[0]), _result(cases[1], committed_hash="e" * 64))

    evaluation = evaluate_metamorphic_outputs(
        cases=cases,
        results=results,
        semantic_digests=_semantic_digests(cases),
    )

    assert evaluation["status"] == "failed"
    assert "changed the sealed transaction hash" in evaluation["issues"][0]


def test_metamorphic_output_rejects_typed_contradiction_despite_lexical_overlap() -> None:
    baseline, candidate = _cases()
    contradictory_path = "A reviewer never logs one governed decision or inspects the approved outcome."
    contradictory_facts = {**_facts(candidate), "first_path": contradictory_path}
    candidate = replace(candidate, prompt=_prompt_for_facts(contradictory_facts))
    results = (
        _result(baseline),
        _result(candidate, first_path=contradictory_path, atomic_polarity="prohibited"),
    )

    evaluation = evaluate_metamorphic_outputs(
        cases=(baseline, candidate),
        results=results,
        semantic_digests={baseline.case_id: SEMANTIC_DIGEST},
    )

    assert evaluation["status"] == "failed"
    assert any("lacks a verified normalized semantic digest" in issue for issue in evaluation["issues"])


def test_metamorphic_output_fails_closed_without_a_verified_semantic_digest() -> None:
    cases = _cases()

    evaluation = evaluate_metamorphic_outputs(
        cases=cases,
        results=tuple(_result(case) for case in cases),
        semantic_digests={cases[0].case_id: SEMANTIC_DIGEST},
    )

    assert evaluation["status"] == "failed"
    assert any("lacks a verified normalized semantic digest" in issue for issue in evaluation["issues"])


def test_metamorphic_output_rejects_same_topology_with_different_semantic_identities() -> None:
    baseline, candidate = _cases()

    evaluation = evaluate_metamorphic_outputs(
        cases=(baseline, candidate),
        results=(_result(baseline), _result(candidate)),
        semantic_digests={baseline.case_id: SEMANTIC_DIGEST, candidate.case_id: "b" * 64},
    )

    assert evaluation["status"] == "failed"
    assert any("changed frozen canonical semantic identities or relations" in issue for issue in evaluation["issues"])


def test_metamorphic_output_accepts_required_clarification_without_a_transaction() -> None:
    committed_case, clarification_case = _clarification_pair_cases()

    evaluation = evaluate_metamorphic_outputs(
        cases=(committed_case, clarification_case),
        results=(_result(committed_case), _clarification_result(clarification_case)),
    )

    assert evaluation["status"] == "passed"
    assert evaluation["complete_group_count"] == 1


def test_metamorphic_output_keeps_clarification_subprocess_as_diagnostic_evidence() -> None:
    committed_case, clarification_case = _clarification_pair_cases()

    evaluation = evaluate_metamorphic_outputs(
        cases=(committed_case, clarification_case),
        results=(
            _result(committed_case),
            _clarification_result(
                clarification_case,
                subprocess_attempts=("subprocess.Popen",),
            ),
        ),
    )

    assert evaluation["status"] == "passed"


def test_metamorphic_output_rejects_clarification_without_a_frozen_oracle() -> None:
    committed_case, clarification_case = _clarification_pair_cases()
    clarification_case = replace(
        clarification_case,
        expected_clarification_field="",
        expected_clarification_question="",
    )

    evaluation = evaluate_metamorphic_outputs(
        cases=(committed_case, clarification_case),
        results=(_result(committed_case), _clarification_result(clarification_case)),
    )

    assert evaluation["status"] == "failed"
    assert any("lacks frozen expected material fields" in issue for issue in evaluation["issues"])


def test_metamorphic_output_rejects_an_untyped_clarification_oracle() -> None:
    committed_case, clarification_case = _clarification_pair_cases()
    clarification_case = replace(
        clarification_case,
        expected_clarification_field="totally_unbounded_field",
    )

    evaluation = evaluate_metamorphic_outputs(
        cases=(committed_case, clarification_case),
        results=(
            _result(committed_case),
            _clarification_result(
                clarification_case,
                question="What is the totally unbounded field?",
                required_fields=("totally_unbounded_field",),
            ),
        ),
    )

    assert evaluation["status"] == "failed"
    assert any("unsupported material question field" in issue for issue in evaluation["issues"])


def test_metamorphic_output_rejects_clarification_that_stages_a_transaction() -> None:
    committed_case, clarification_case = _clarification_pair_cases()

    evaluation = evaluate_metamorphic_outputs(
        cases=(committed_case, clarification_case),
        results=(
            _result(committed_case),
            _clarification_result(clarification_case, staged_transaction_present=True),
        ),
    )

    assert evaluation["status"] == "failed"
    assert any("staged a transaction before clarification" in issue for issue in evaluation["issues"])


def test_metamorphic_output_rejects_noncanonical_clarification() -> None:
    committed_case, clarification_case = _clarification_pair_cases()

    evaluation = evaluate_metamorphic_outputs(
        cases=(committed_case, clarification_case),
        results=(
            _result(committed_case),
            _clarification_result(clarification_case, question="Choose the first task", required_fields=("target_user",)),
        ),
    )

    assert evaluation["status"] == "failed"
    assert any("did not ask its focused material question" in issue for issue in evaluation["issues"])
    assert any("changed its expected material fields" in issue for issue in evaluation["issues"])


def test_metamorphic_output_rejects_clarification_with_changed_record_count() -> None:
    committed_case, clarification_case = _clarification_pair_cases()

    evaluation = evaluate_metamorphic_outputs(
        cases=(committed_case, clarification_case),
        results=(
            _result(committed_case),
            _clarification_result(clarification_case, after_record_count=136),
        ),
    )

    assert evaluation["status"] == "failed"
    assert any("did not prove unchanged governed record counts" in issue for issue in evaluation["issues"])


def test_metamorphic_output_rejects_clarification_with_write_artifacts() -> None:
    committed_case, clarification_case = _clarification_pair_cases()

    evaluation = evaluate_metamorphic_outputs(
        cases=(committed_case, clarification_case),
        results=(
            _result(committed_case),
            _clarification_result(
                clarification_case,
                changed_records=("odylith/radar/source/workstreams.v1.json",),
                write_attempts=("open:odylith/radar/source/workstreams.v1.json",),
                preconfirm_dry_run=True,
                commit_manifest=True,
            ),
        ),
    )

    assert evaluation["status"] == "failed"
    assert any("changed governed records before clarification" in issue for issue in evaluation["issues"])
    assert any("attempted repository writes before clarification" in issue for issue in evaluation["issues"])
    assert any("created a dry-run receipt before clarification" in issue for issue in evaluation["issues"])
    assert any("produced a commit manifest before clarification" in issue for issue in evaluation["issues"])


def test_metamorphic_output_rejects_clarification_without_installed_write_audit() -> None:
    committed_case, clarification_case = _clarification_pair_cases()

    evaluation = evaluate_metamorphic_outputs(
        cases=(committed_case, clarification_case),
        results=(
            _result(committed_case),
            _clarification_result(clarification_case, write_audit_active=False, write_audit_error="trace unavailable"),
        ),
    )

    assert evaluation["status"] == "failed"
    assert any("did not activate the installed write audit" in issue for issue in evaluation["issues"])
    assert any("hit an installed write-audit error" in issue for issue in evaluation["issues"])


def test_metamorphic_output_is_pending_until_all_declared_variants_finish() -> None:
    cases = _cases()

    evaluation = evaluate_metamorphic_outputs(cases=cases, results=(_result(cases[0]),))

    assert evaluation["status"] == "pending"
    assert evaluation["pending_groups"] == ["source-001"]


def test_metamorphic_output_skips_single_member_group_after_filtered_replay() -> None:
    case = _cases()[0]

    evaluation = evaluate_metamorphic_outputs(cases=(case,), results=(_result(case),))

    assert evaluation["status"] == "passed"
    assert evaluation["skipped_groups"] == ["source-001"]
    assert evaluation["complete_group_count"] == 0


def test_campaign_summary_exposes_metamorphic_commit_hash_failure() -> None:
    cases = _cases()

    summary = campaign_summary(
        cases=cases,
        results=(_result(cases[0]), _result(cases[1], committed_hash="e" * 64)),
        config=MatrixCampaignConfig(proof_tier="release"),
        stopped_reason="",
    )

    assert summary["metamorphic_output"]["status"] == "failed"
    assert "changed the sealed transaction hash" in summary["metamorphic_output"]["issues"][0]


def _cases() -> tuple[GreenfieldMatrixCase, GreenfieldMatrixCase]:
    provenance = GreenfieldCaseProvenance(source_id="source-001", source_artifact_sha256=SOURCE_HASH)
    return (
        GreenfieldMatrixCase(
            case_id="source-001-description",
            name="description variant",
            prompt=_prompt_for_facts(_FACTS_BY_CASE_ID["source-001-description"]),
            required_terms=("evidence",),
            provenance=provenance,
            metamorphic_group="source-001",
            metamorphic_transform="description_evidence",
        ),
        GreenfieldMatrixCase(
            case_id="source-001-topic",
            name="topic variant",
            prompt=_prompt_for_facts(_FACTS_BY_CASE_ID["source-001-topic"]),
            required_terms=("evidence",),
            provenance=provenance,
            metamorphic_group="source-001",
            metamorphic_transform="topic_evidence",
        ),
    )


def _semantic_digests(cases: tuple[GreenfieldMatrixCase, ...]) -> dict[str, str]:
    return {case.case_id: SEMANTIC_DIGEST for case in cases}


def _clarification_pair_cases() -> tuple[GreenfieldMatrixCase, GreenfieldMatrixCase]:
    committed_case, topic_case = _cases()
    return committed_case, replace(
        topic_case,
        expectation="clarification_required",
        expected_clarification_field="first_path",
    )


def _result(
    case: GreenfieldMatrixCase,
    *,
    committed_hash: str = HASH,
    first_path: str | None = None,
    atomic_polarity: str = "affirmed",
) -> GreenfieldMatrixResult:
    facts = _facts(case)
    if first_path is not None:
        facts["first_path"] = first_path
    summary = {
        "write_transaction": {
            "commit_only": True,
            "prewrite_clean_before_commit": True,
            "product_create_transaction_hash": committed_hash,
        },
        "product_create_transaction": {"transaction_hash": committed_hash},
    }
    return GreenfieldMatrixResult(
        name=case.name,
        status="passed",
        create_seconds=1.0,
        counts=GreenfieldArtifactCounts(),
        quality=GreenfieldQualityVerdict(True, (), {}, {}, 10, ()),
        commit_manifest_summary=summary,
        evidence={
            "case": case_evidence(case),
            "preconfirm_dry_run": {
                "status": "compiled",
                "transaction_hash": HASH,
                "semantic_snapshot": _typed_semantic_snapshot(
                    case=case,
                    facts=facts,
                    atomic_polarity=atomic_polarity,
                ),
            },
        },
    )


def _typed_semantic_snapshot(
    *,
    case: GreenfieldMatrixCase,
    facts: dict[str, object],
    atomic_polarity: str,
) -> dict[str, object]:
    evidence = combined_prompt_evidence_source(
        prompt=case.prompt,
        edit_evidence=str(case.confirmed_intent_markdown or ""),
    )
    source_bytes = evidence.encode("utf-8")
    first_path = str(facts["first_path"])
    path_bytes = first_path.encode("utf-8")
    actor, action, target, visible_result = _EVENT_PARTS_BY_CASE_ID[case.case_id]
    event_start = source_bytes.index(path_bytes)
    state_object = str(facts["state_object"])
    state_bytes = state_object.encode("utf-8")
    state_start = source_bytes.index(state_bytes)
    relations = [
        {
            "order": 1,
            "source_start_byte": event_start,
            "source_end_byte": event_start + len(path_bytes),
            "event_start_byte": 0,
            "event_end_byte": len(path_bytes),
            "actor_kind": "human",
            "actor_quote": actor,
            "actor_is_carried": False,
            "actor_fact_path": "/human_actors/0",
            "actor_fact_quote": actor,
            "owner_system_path": "",
            "owner_system_quote": "",
            "event_quote": first_path,
            "action_verb_quote": action,
            "target_quote": target,
            "visible_result_quote": visible_result,
        }
    ]
    contexts = [
        {
            "context_kind": "state_object",
            "fact_path": "/state_object",
            "fact_quote": state_object,
            "source_start_byte": state_start,
            "source_end_byte": state_start + len(state_bytes),
            "first_path_event_order": 1,
        }
    ]
    components = [
        {
            "responsibility_path": "/first_path",
            "responsibility_quote": visible_result,
            "owner_system_path": "/title",
            "owner_system_quote": str(facts["title"]),
            "first_path_event_order": 1,
            "responsibility_source": "terminal_visible_result",
        }
    ]
    semantics = {
        "version": AUTHORED_SEMANTICS_VERSION,
        "first_path_relations": relations,
        "first_path_context_relations": contexts,
        "component_responsibility_relations": components,
    }
    atoms = _atomic_facts(
        facts=facts,
        source_bytes=source_bytes,
        event_source_start=event_start,
        action=action,
        polarity=atomic_polarity,
    )
    return {
        "facts": facts,
        "atomic_facts": atoms,
        "atomic_custody_sha256": atomic_fact_ledger_hash(atoms),
        "authored_semantics": semantics,
        "authored_relation_set_sha256": authored_relation_set_sha256(
            relations,
            components,
            first_path_context_relations=contexts,
        ),
    }


def _atomic_facts(
    *,
    facts: dict[str, object],
    source_bytes: bytes,
    event_source_start: int,
    action: str,
    polarity: str,
) -> list[dict[str, object]]:
    first_path = str(facts["first_path"])
    path_bytes = first_path.encode("utf-8")
    action_bytes = action.encode("utf-8")
    projection_start = path_bytes.index(action_bytes)
    source_start = event_source_start + projection_start
    claim = {
        "field": "first_path",
        "category": "actions",
        "polarity": polarity,
        "source_start_byte": source_start,
        "source_end_byte": source_start + len(action_bytes),
        "quote": action,
        "quote_sha256": hashlib.sha256(action_bytes).hexdigest(),
        "projection_path": "/first_path",
        "projection_start_byte": projection_start,
        "projection_end_byte": projection_start + len(action_bytes),
        "projection_value_sha256": hashlib.sha256(path_bytes).hexdigest(),
        "relation_order": 1,
        "relation_role": "action_verb_quote",
    }
    assert source_bytes[source_start : source_start + len(action_bytes)] == action_bytes
    spans: list[dict[str, object]] = []
    append_atomic_source_spans(spans, authored_atomic_claims=[claim])
    return build_atomic_fact_ledger(
        facts=facts,
        spans=spans,
        authored_atomic_claims=[claim],
    )


def _facts(case: GreenfieldMatrixCase) -> dict[str, object]:
    return dict(_FACTS_BY_CASE_ID[case.case_id])


def _prompt_for_facts(facts: dict[str, object]) -> str:
    return " ".join(
        str(facts[field])
        for field in ("title", "product_story", "state_object", "first_path", "proof_boundary")
    )


def _clarification_result(
    case: GreenfieldMatrixCase,
    *,
    question: str = FOCUSED_FIRST_PATH_QUESTION,
    required_fields: tuple[str, ...] = ("first_path",),
    staged_transaction_present: bool = False,
    before_record_count: int = 135,
    after_record_count: int = 135,
    changed_records: tuple[str, ...] = (),
    preconfirm_dry_run: bool = False,
    commit_manifest: bool = False,
    write_audit_active: bool = True,
    write_attempts: tuple[str, ...] = (),
    subprocess_attempts: tuple[str, ...] = (),
    write_audit_error: str = "",
) -> GreenfieldMatrixResult:
    evidence = {
        "case": case_evidence(case),
        "clarification": {
            "mode": "clarification_required",
            "question": question,
            "required_fields": list(required_fields),
            "returncode": 0,
        },
        "no_write": {
            "before_record_count": before_record_count,
            "after_record_count": after_record_count,
            "changed_records": list(changed_records),
            "staged_transaction_present": staged_transaction_present,
            "write_audit_active": write_audit_active,
            "write_attempts": list(write_attempts),
            "subprocess_attempts": list(subprocess_attempts),
            "write_audit_error": write_audit_error,
        },
    }
    if preconfirm_dry_run:
        evidence["preconfirm_dry_run"] = {"status": "compiled", "transaction_hash": HASH}
    return GreenfieldMatrixResult(
        name=case.name,
        status="passed",
        create_seconds=1.0,
        counts=GreenfieldArtifactCounts(),
        quality=GreenfieldQualityVerdict(True, (), {}, {}, 10, ()),
        commit_manifest_summary={"unexpected": "manifest"} if commit_manifest else {},
        evidence=evidence,
    )
