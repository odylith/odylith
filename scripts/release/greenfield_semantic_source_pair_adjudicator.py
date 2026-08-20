"""Adjudicate existing source hypotheses without reauthoring either graph."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
import json
from pathlib import Path
from typing import Any

from greenfield_semantic_authoring_wave import admit_partitioned_candidate
from greenfield_semantic_release_support import canonical_sha256, mapping
from greenfield_semantic_standard_path_experiment import case_prompt
from greenfield_semantic_structured_host import run_structured_host
from odylith.runtime.domain_intelligence.greenfield_semantic_final_adjudication import (
    clarification_from_source_ambiguity,
    settle_independently_confirmed_discarded_materiality_refs,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_graph_contract import (
    SEMANTIC_CLARIFICATION_FIELDS,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_layered_authoring import (
    SEMANTIC_PARTITIONED_AUTHOR_VERSION,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_parallel_materiality import (
    canonical_parallel_materiality_decision,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_source_citations import (
    require_semantic_source_refs,
    semantic_evidence_block_catalog,
    semantic_source_ref_schema,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_source_hypothesis_comparison import (
    admit_source_only_authority,
    independent_source_materiality_observation,
    independently_confirmed_discarded_refs,
    source_candidate_discarded_refs,
)


SOURCE_PAIR_ADJUDICATION_VERSION = (
    "odylith.greenfield.semantic-source-pair-adjudication.v3"
)
MATERIALITY_PAIR_ADJUDICATION_VERSION = (
    "odylith.greenfield.semantic-materiality-pair-adjudication.v1"
)


def run_source_pair_adjudication(
    *,
    corpus_path: Path,
    case_id: str,
    critic: Mapping[str, Any],
    source_receipt: Mapping[str, Any],
    host_profile: str,
    model: str,
    reasoning_effort: str,
    budget_seconds: int,
) -> dict[str, Any]:
    """Choose one existing source hypothesis or one material clarification."""

    prompt_text = case_prompt(corpus_path=corpus_path, case_id=case_id)
    evidence_sources = {"operator_prompt": prompt_text, "operator_edit": ""}
    decision = _settled_pair_materiality_decision(
        mapping(critic.get("decision"), "materiality hypothesis"),
        source_receipt=source_receipt,
        evidence_sources=evidence_sources,
    )
    if source_receipt.get("source_pair_dispute") == "materiality":
        return _run_materiality_pair_adjudication(
            case_id=case_id,
            prompt_text=prompt_text,
            evidence_sources=evidence_sources,
            decision=decision,
            source_receipt=source_receipt,
            host_profile=host_profile,
            model=model,
            reasoning_effort=reasoning_effort,
            budget_seconds=budget_seconds,
        )
    candidates = _admissible_sources(
        source_receipt,
        decision=decision,
        evidence_sources=evidence_sources,
    )
    if not candidates:
        raise ValueError(
            "neither existing source hypothesis is admissible; fresh graph authorship "
            "is forbidden in rescue"
        )
    schema = _source_pair_schema(candidate_names=tuple(candidates))
    prompt = _source_pair_prompt(
        prompt_text=prompt_text,
        materiality_decision=decision,
        candidates=candidates,
        evidence_catalog=semantic_evidence_block_catalog(evidence_sources),
        budget_seconds=budget_seconds,
    )
    raw, usage, wall_ms = run_structured_host(
        schema=schema,
        prompt=prompt,
        model=model,
        reasoning_effort=reasoning_effort,
        budget_seconds=budget_seconds,
        temporary_prefix="odylith-source-pair-adjudicator-",
        host_profile=host_profile,
    )
    result = _mapping(raw, "source-pair adjudication")
    _exact_keys(
        result,
        {"version", "source_selection", "clarification"},
        "source-pair adjudication",
    )
    if result.get("version") != SOURCE_PAIR_ADJUDICATION_VERSION:
        raise ValueError("source-pair adjudication uses an unsupported version")
    selection = str(result.get("source_selection") or "")
    clarification = _mapping(
        result.get("clarification"), "source-pair clarification"
    )
    if selection == "clarification_required":
        fields = _text_rows(clarification.get("fields"), "clarification fields")
        question = str(clarification.get("question") or "").strip()
        refs = require_semantic_source_refs(
            clarification.get("source_refs"),
            evidence_sources=evidence_sources,
            allow_empty=False,
        )
        if len(fields) != 1 or not refs or not question:
            raise ValueError("source-pair clarification is not one material question")
        final_decision = clarification_from_source_ambiguity(
            decision,
            ambiguity={
                "materiality_field": fields[0],
                "question": question,
                "source_refs": refs,
            },
        )
        return _receipt(
            case_id=case_id,
            host_profile=host_profile,
            model=model,
            reasoning_effort=reasoning_effort,
            budget_seconds=budget_seconds,
            wall_ms=wall_ms,
            usage=usage,
            decision=final_decision,
            source_status="not_applicable",
            candidate=None,
            compiled_author_output=None,
            discarded_source_refs=[],
        )
    if selection not in candidates:
        raise ValueError("source-pair adjudication selects an unknown hypothesis")
    if (
        clarification.get("question")
        or clarification.get("fields")
        or clarification.get("source_refs")
    ):
        raise ValueError("source-pair selection carries an unused clarification")
    selected = candidates[selection]
    admitted = selected["admitted"]
    return _receipt(
        case_id=case_id,
        host_profile=host_profile,
        model=model,
        reasoning_effort=reasoning_effort,
        budget_seconds=budget_seconds,
        wall_ms=wall_ms,
        usage=usage,
        decision=decision,
        source_status="approved",
        candidate={
            "source": selected["compiled_source"],
            "completion": mapping(admitted.get("completion"), "admitted completion"),
        },
        compiled_author_output=selected["compiled_author_output"],
        discarded_source_refs=source_candidate_discarded_refs(admitted),
        source_candidate_rejections=selected["source_candidate_rejections"],
    )


def _run_materiality_pair_adjudication(
    *, case_id: str, prompt_text: str, evidence_sources: Mapping[str, str],
    decision: Mapping[str, Any], source_receipt: Mapping[str, Any],
    host_profile: str, model: str, reasoning_effort: str, budget_seconds: int,
) -> dict[str, Any]:
    candidates = _raw_hypothesis_candidates(source_receipt)
    observed = independent_source_materiality_observation(
        [row["candidate"] for row in candidates], decision=decision
    )
    recorded = source_receipt.get("materiality_observation")
    if observed is None or not isinstance(recorded, Mapping) or dict(recorded) != observed:
        raise ValueError("materiality handoff changes its typed source observation")
    raw, usage, wall_ms = run_structured_host(
        schema=_materiality_pair_schema(observation=observed),
        prompt=_materiality_pair_prompt(
            prompt_text=prompt_text,
            materiality_decision=decision,
            observation=observed,
            candidates=candidates,
            evidence_catalog=semantic_evidence_block_catalog(evidence_sources),
            budget_seconds=budget_seconds,
        ),
        model=model,
        reasoning_effort=reasoning_effort,
        budget_seconds=budget_seconds,
        temporary_prefix="odylith-materiality-pair-adjudicator-",
        host_profile=host_profile,
    )
    result = _mapping(raw, "materiality-pair adjudication")
    _exact_keys(
        result,
        {"version", "decision", "clarification"},
        "materiality-pair adjudication",
    )
    if result.get("version") != MATERIALITY_PAIR_ADJUDICATION_VERSION:
        raise ValueError("materiality-pair adjudication uses an unsupported version")
    final_name = str(result.get("decision") or "")
    clarification = _mapping(
        result.get("clarification"), "materiality-pair clarification"
    )
    fields = _text_rows(clarification.get("fields"), "clarification fields")
    question = str(clarification.get("question") or "").strip()
    raw_refs = clarification.get("source_refs")
    if final_name == "clarification_required":
        refs = require_semantic_source_refs(
            raw_refs, evidence_sources=evidence_sources, allow_empty=False
        )
        if (
            fields != [observed["materiality_field"]]
            or not question
            or not refs
        ):
            raise ValueError("materiality-pair clarification changes the challenged field")
        final_decision = clarification_from_source_ambiguity(
            decision,
            ambiguity={
                "materiality_field": fields[0],
                "question": question,
                "source_refs": refs,
            },
        )
        return _receipt(
            case_id=case_id,
            host_profile=host_profile,
            model=model,
            reasoning_effort=reasoning_effort,
            budget_seconds=budget_seconds,
            wall_ms=wall_ms,
            usage=usage,
            decision=final_decision,
            source_status="not_applicable",
            candidate=None,
            compiled_author_output=None,
            discarded_source_refs=[],
        )
    if final_name != "authorize_graph":
        raise ValueError("materiality-pair adjudication has an unsupported decision")
    if question or fields or raw_refs not in ([], None):
        raise ValueError("materiality-pair authorization carries a clarification")
    authorized = _authorized_materiality_decision(decision)
    return _admit_existing_candidate(
        candidates,
        case_id=case_id,
        prompt_text=prompt_text,
        decision=authorized,
        host_profile=host_profile,
        model=model,
        reasoning_effort=reasoning_effort,
        budget_seconds=budget_seconds,
        wall_ms=wall_ms,
        usage=usage,
    )


def _admit_existing_candidate(
    candidates: Sequence[Mapping[str, Any]],
    *, case_id: str, prompt_text: str, decision: Mapping[str, Any],
    host_profile: str, model: str, reasoning_effort: str,
    budget_seconds: int, wall_ms: int, usage: Mapping[str, Any],
) -> dict[str, Any]:
    failures: list[str] = []
    for row in sorted(
        candidates,
        key=lambda candidate: int(candidate.get("run_index") != 1),
    ):
        candidate = _mapping(row.get("candidate"), "existing partitioned candidate")
        try:
            admitted, compiled_source, rejections, author_output = (
                admit_partitioned_candidate(
                    candidate,
                    decision=decision,
                    prompt_text=prompt_text,
                    host_profile=host_profile,
                )
            )
        except ValueError as error:
            failures.append(str(error))
            continue
        return _receipt(
            case_id=case_id,
            host_profile=host_profile,
            model=model,
            reasoning_effort=reasoning_effort,
            budget_seconds=budget_seconds,
            wall_ms=wall_ms,
            usage=usage,
            decision=decision,
            source_status="approved",
            candidate={
                "source": compiled_source,
                "completion": mapping(
                    admitted.get("completion"), "admitted completion"
                ),
            },
            compiled_author_output=author_output,
            discarded_source_refs=source_candidate_discarded_refs(admitted),
            source_candidate_rejections=rejections,
        )
    raise ValueError(
        "; ".join(failures) or "no existing typed hypothesis is admissible"
    )


def _authorized_materiality_decision(
    decision: Mapping[str, Any],
) -> dict[str, Any]:
    result = deepcopy(dict(decision))
    result["outcome"] = {
        "decision": "authorize_graph",
        "clarification": {
            "field": "",
            "question": "",
            "source_refs": [],
            "alternatives": [],
        },
    }
    canonical_parallel_materiality_decision(result)
    return result


def _raw_hypothesis_candidates(
    source_receipt: Mapping[str, Any],
) -> list[dict[str, Any]]:
    rows = source_receipt.get("hypothesis_candidates")
    if not isinstance(rows, list) or len(rows) != 2:
        raise ValueError("materiality handoff lacks two exact source hypotheses")
    result: list[dict[str, Any]] = []
    for raw in rows:
        row = _mapping(raw, "materiality source hypothesis")
        if row.get("hypothesis_mode") not in {"full_graph", "source_only"}:
            raise ValueError("materiality handoff changes a source hypothesis identity")
        _mapping(row.get("candidate"), "materiality source candidate")
        result.append(row)
    if {str(row["hypothesis_mode"]) for row in result} != {
        "full_graph", "source_only"
    }:
        raise ValueError("materiality handoff duplicates a source hypothesis")
    return result


def _admissible_sources(
    source_receipt: Mapping[str, Any], *, decision: Mapping[str, Any],
    evidence_sources: Mapping[str, str],
) -> dict[str, dict[str, Any]]:
    rows = source_receipt.get("hypothesis_candidates")
    if not isinstance(rows, list) or len(rows) not in {1, 2}:
        raise ValueError("source handoff lacks one or two exact hypotheses")
    result: dict[str, dict[str, Any]] = {}
    for raw in rows:
        row = _mapping(raw, "source hypothesis candidate")
        name = str(row.get("hypothesis_mode") or "")
        candidate = _mapping(row.get("candidate"), "partitioned source candidate")
        try:
            partitioned_source, _ = admit_source_only_authority(
                candidate,
                decision=decision,
                evidence_sources=evidence_sources,
            )
            admitted, compiled_source, rejections, author_output = (
                admit_partitioned_candidate(
                    {
                        "version": SEMANTIC_PARTITIONED_AUTHOR_VERSION,
                        "source": partitioned_source,
                        "completion": _mapping(
                            candidate.get("completion"),
                            "partitioned source candidate completion",
                        ),
                    },
                    decision=decision,
                    prompt_text=str(evidence_sources["operator_prompt"]),
                    host_profile=str(source_receipt.get("host_profile") or ""),
                )
            )
        except ValueError:
            continue
        result[name] = {
            "compiled_source": compiled_source,
            "admitted": admitted,
            "compiled_author_output": author_output,
            "source_candidate_rejections": rejections,
        }
    if not set(result).issubset({"full_graph", "source_only"}):
        raise ValueError("source-pair handoff contains an unknown source hypothesis")
    return result


def _settled_pair_materiality_decision(
    decision: Mapping[str, Any], *, source_receipt: Mapping[str, Any],
    evidence_sources: Mapping[str, str],
) -> dict[str, Any]:
    rows = source_receipt.get("hypothesis_candidates")
    if not isinstance(rows, list) or len(rows) not in {1, 2}:
        raise ValueError("source handoff lacks one or two exact hypotheses")
    candidates = [
        _mapping(_mapping(row, "source hypothesis candidate").get("candidate"),
                 "partitioned source candidate")
        for row in rows
    ]
    if len(candidates) == 1:
        return dict(decision)
    confirmed = independently_confirmed_discarded_refs(
        source_candidate_discarded_refs(candidates[0]),
        source_candidate_discarded_refs(candidates[1]),
        evidence_sources=evidence_sources,
    )
    if not confirmed:
        return dict(decision)
    return settle_independently_confirmed_discarded_materiality_refs(
        decision,
        discarded_source_refs=confirmed,
        evidence_sources=evidence_sources,
    )


def _materiality_pair_schema(
    *, observation: Mapping[str, Any]
) -> dict[str, Any]:
    clarification = {
        "type": "object",
        "additionalProperties": False,
        "required": ["question", "fields", "source_refs"],
        "properties": {
            "question": {"type": "string", "maxLength": 600},
            "fields": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": list(SEMANTIC_CLARIFICATION_FIELDS),
                },
                "maxItems": 1,
            },
            "source_refs": {
                "type": "array",
                "items": semantic_source_ref_schema(),
                "maxItems": 8,
            },
        },
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["version", "decision", "clarification"],
        "properties": {
            "version": {
                "type": "string", "enum": [MATERIALITY_PAIR_ADJUDICATION_VERSION]
            },
            "decision": {
                "type": "string",
                "enum": (
                    ["clarification_required"]
                    if observation.get("status")
                    == "critic_authorization_disputed"
                    else ["authorize_graph", "clarification_required"]
                ),
            },
            "clarification": clarification,
        },
    }


def _materiality_pair_prompt(
    *, prompt_text: str, materiality_decision: Mapping[str, Any],
    observation: Mapping[str, Any], candidates: Sequence[Mapping[str, Any]],
    evidence_catalog: Mapping[str, Mapping[str, Any]], budget_seconds: int,
) -> str:
    contract = {
        "deadline": {"stage_seconds": budget_seconds, "retries": 0},
        "authority": (
            "Adjudicate one critic/source disagreement from the original evidence and "
            "two independently authored typed source graphs. Return authorize_graph only "
            "when the challenged field is materially settled without inventing meaning; "
            "otherwise return exactly one necessary clarification. Do not author, merge, "
            "or repair a graph."
        ),
        "typed_source_observation": dict(observation),
        "initial_materiality_decision": materiality_decision,
        "source_hypotheses": {
            str(row["hypothesis_mode"]): _mapping(
                _mapping(row.get("candidate"), "materiality source candidate").get(
                    "source"
                ),
                "materiality source graph",
            )
            for row in candidates
        },
        "evidence_blocks": {
            key: {"source_id": row["source_id"], "quote": row["quote"]}
            for key, row in evidence_catalog.items()
        },
        "invariants": [
            "typed source presence is comparison evidence, not automatic authority",
            "a clarification cites exact operator evidence and asks one material question",
            "authorization carries an empty clarification",
            "no graph authorship, regex, fuzzy matching, token heuristics, retry, or repair",
        ],
    }
    return (
        "Act as the bounded materiality disagreement adjudicator. Use no tools or files. "
        "Return only the typed decision object."
        f"\nOPERATOR_PROMPT\n{prompt_text}"
        "\nCONTRACT\n"
        + json.dumps(contract, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    )


def _source_pair_schema(*, candidate_names: Sequence[str]) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["version", "source_selection", "clarification"],
        "properties": {
            "version": {
                "type": "string", "enum": [SOURCE_PAIR_ADJUDICATION_VERSION]
            },
            "source_selection": {
                "type": "string",
                "enum": [*candidate_names, "clarification_required"],
            },
            "clarification": {
                "type": "object",
                "additionalProperties": False,
                "required": ["question", "fields", "source_refs"],
                "properties": {
                    "question": {"type": "string", "maxLength": 600},
                    "fields": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": list(SEMANTIC_CLARIFICATION_FIELDS),
                        },
                        "maxItems": 1,
                    },
                    "source_refs": {
                        "type": "array",
                        "items": semantic_source_ref_schema(),
                        "maxItems": 8,
                    },
                },
            },
        },
    }


def _source_pair_prompt(
    *, prompt_text: str, materiality_decision: Mapping[str, Any],
    candidates: Mapping[str, Mapping[str, Any]],
    evidence_catalog: Mapping[str, Mapping[str, Any]], budget_seconds: int,
) -> str:
    selection_rule = (
        "Select the sole admitted source hypothesis unless the original operator "
        "evidence requires one material clarification; never clarify for an "
        "implementation, presentation, or styling choice."
        if len(candidates) == 1
        else (
            "Select one hypothesis unchanged when it preserves the complete supported "
            "meaning; otherwise ask exactly one material question."
        )
    )
    contract = {
        "deadline": {"stage_seconds": budget_seconds, "retries": 0},
        "authority": (
            "Adjudicate the admitted source hypotheses against the operator evidence. "
            + selection_rule
            + " If selecting, reuse that already validated candidate unchanged. Never "
            "author, merge, repair, or rewrite a graph."
        ),
        "candidate_sources": {
            name: row["compiled_source"] for name, row in candidates.items()
        },
        "evidence_blocks": {
            key: {"source_id": row["source_id"], "quote": row["quote"]}
            for key, row in evidence_catalog.items()
        },
        "materiality_decision": materiality_decision,
        "invariants": [
            "source selection is whole-hypothesis selection, never field-level merging",
            "clarification is reserved for a material source disagreement",
            "the selected candidate has already passed source and graph validation",
            "selection reuses existing candidate bytes without completion authorship",
            "no regex, fuzzy matching, token heuristics, retries, or validator repair",
        ],
    }
    return (
        "Act as the bounded final source-pair adjudicator. Use no tools or files. Return "
        "only the typed adjudication object."
        f"\nOPERATOR_PROMPT\n{prompt_text}"
        "\nCONTRACT\n"
        + json.dumps(contract, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    )


def _receipt(
    *, case_id: str, host_profile: str, model: str, reasoning_effort: str,
    budget_seconds: int, wall_ms: int, usage: Mapping[str, Any],
    decision: Mapping[str, Any], source_status: str,
    candidate: Mapping[str, Any] | None,
    compiled_author_output: Mapping[str, Any] | None,
    discarded_source_refs: Sequence[Mapping[str, Any]],
    source_candidate_rejections: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    payload = {
        "materiality_decision": decision,
        "source_status": source_status,
        "candidate": candidate,
    }
    return {
        "stage": "final_graph_adjudication",
        "case_id": case_id,
        "host_profile": host_profile,
        "model": model,
        "reasoning_effort": reasoning_effort,
        "model_budget_seconds": budget_seconds,
        "wall_ms": wall_ms,
        "usage": dict(usage),
        "model_call_count": 1,
        "materiality_decision": deepcopy(dict(decision)),
        "source_status": source_status,
        "findings": [],
        "discarded_source_refs": [dict(row) for row in discarded_source_refs],
        "source_candidate_rejections": [
            dict(row) for row in source_candidate_rejections
        ],
        "candidate": deepcopy(dict(candidate)) if candidate is not None else None,
        "compiled_author_output": (
            deepcopy(dict(compiled_author_output))
            if compiled_author_output is not None
            else None
        ),
        "validation_status": "passed",
        "validation_error": "",
        "adjudicator_run_id": (
            "standard:clarification-author:"
            if source_status == "not_applicable"
            else "standard:partitioned-graph-author:"
        ) + canonical_sha256(payload),
    }


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be a JSON object")
    return dict(value)


def _text_rows(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(row, str) for row in value):
        raise ValueError(f"{label} must be a string array")
    return list(value)


def _exact_keys(value: Mapping[str, Any], keys: set[str], label: str) -> None:
    if set(value) != keys:
        raise ValueError(f"{label} has unsupported or missing fields")


__all__ = [
    "MATERIALITY_PAIR_ADJUDICATION_VERSION",
    "SOURCE_PAIR_ADJUDICATION_VERSION",
    "run_source_pair_adjudication",
]
