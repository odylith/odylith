"""Own source-verified run choices and their exact canonical projection.

The inventory chooses meaning and the existing source-only verifier judges it.
This owner checks structure and source custody, then maps those choices without
selecting a branch, result, performer, or execution order itself.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_event_ordering import (
    validate_first_run, validate_source_precedence,
)
from odylith.runtime.domain_intelligence.greenfield_model_source_citations import (
    canonical_citation_from_host_selection, resolve_source_citation,
)
from odylith.runtime.domain_intelligence.greenfield_model_outcomes import GreenfieldModelAuthoringError
from odylith.runtime.domain_intelligence.greenfield_intent_fact_values import TERMINAL_RESULT_FACT_FIELDS
from odylith.runtime.domain_intelligence.greenfield_operating_envelope import (
    MAX_AUTHORED_FIELD_VALUE_CHARS, MAX_AUTHORED_LIST_ITEMS,
)

SOURCE_RUN_PLAN_LEDGER_VERSION = "odylith.greenfield.source-duty-ledger.v13"
PREVIOUS_SOURCE_RUN_PLAN_LEDGER_VERSION = "odylith.greenfield.source-duty-ledger.v12"
_ACTION_SECTIONS = ("first_path_actions", "supporting_human_actions", "system_duties")
_RUN_JUDGMENTS = ("membership", "order", "completeness")
_RESULT_JUDGMENTS = ("proof_boundary", "result_fact", "producing_duty", "result_custody")
SOURCE_RUN_VERIFIER_TASK = (
    "Judge the existing source_precedence, first_run and terminal together against the complete "
    "authority source. Return source_plan decisions, separately from each duty's ordinary decision. "
    "Every precedence row must express a source-required ordering between those exact duties, "
    "supported by its exact constraint_ref; retain every such material relation. first_run.membership "
    "must affirm exactly the required complete run, including required discrete system consequences "
    "and transitive prerequisites, without moving first_path_actions or changing performer roles. "
    "Exclude disconnected optional work, recovery alternatives and recurring invariants. order must "
    "affirm the complete proposed sequence is source-supported and preserves declared path order. "
    "completeness must affirm the run reaches the requested result and omits no required work, "
    "including work required after the visible result. terminal.proof_boundary must affirm its own citation "
    "is the existing source-supported proof-boundary witness, not an arbitrary clause repurposed as "
    "proof. result_fact must affirm the selected fact's existing typed field meaning independently "
    "of proof: first_path, product_story, opportunity, product_view, success_metrics or proof_boundary. "
    "producing_duty must affirm the exact duty produces the requested result; result_custody "
    "must affirm the exact result_quote/local occurrence and source meaning. A producer is not "
    "selected by largest ID, array tail or graph sink. Preserve atomic release/recheck meaning. "
    "Source-wide completeness also covers this plan and every required system consequence. Use no "
    "or uncertain for unsupported, missing or ambiguous choices. This is the same source-only "
    "verifier pass; do not author a candidate or a replacement plan."
)


def source_run_plan_schema(citation: Mapping[str, Any]) -> dict[str, Any]:
    """Reuse inline citations for the three moved source-plan concepts."""
    duty_id = {"type": "string", "minLength": 1, "maxLength": 200}
    edge = {"before_duty_id": duty_id, "after_duty_id": duty_id,
            "constraint_ref": deepcopy(dict(citation))}
    run = {"duty_ids": {"type": "array", "minItems": 1, "maxItems": 32, "items": duty_id}}
    path_fact = {"field": {"type": "string", "maxLength": 32, "enum": ["first_path"]}, "duty_id": duty_id}
    other_fact = {"field": {"type": "string", "maxLength": 32, "enum": [field for field in TERMINAL_RESULT_FACT_FIELDS if field != "first_path"]},
                  "source_ref": deepcopy(dict(citation))}
    result_fact = {"anyOf": [{"type": "object", "additionalProperties": False,
                              "required": list(fields), "properties": fields}
                             for fields in (path_fact, other_fact)]}
    terminal = {
        "duty_id": duty_id, "proof_boundary": deepcopy(dict(citation)), "result_fact": result_fact,
        "result_quote": {"type": "string", "minLength": 1, "maxLength": MAX_AUTHORED_FIELD_VALUE_CHARS},
        "result_occurrence": {"type": "integer", "minimum": 1, "maximum": MAX_AUTHORED_FIELD_VALUE_CHARS},
    }
    return {
        "source_precedence": {"type": "array", "maxItems": 64, "items": {
            "type": "object", "additionalProperties": False, "required": list(edge), "properties": edge}},
        "first_run": {"type": "object", "additionalProperties": False,
                      "required": list(run), "properties": run},
        "terminal": {"anyOf": [{"type": "object", "additionalProperties": False,
                                "required": list(terminal), "properties": terminal}, {"type": "null"}]},
    }


def source_run_decisions_schema(ledger: Mapping[str, Any]) -> dict[str, Any]:
    """Bind affirmative judgments to each exact compiler-addressed source choice."""
    verdict = {"type": "string", "enum": ["yes", "no", "uncertain"]}
    tables = {
        "source_precedence": {str(i): verdict for i in range(len(ledger["source_precedence"]))},
        "first_run": {key: verdict for key in _RUN_JUDGMENTS},
        "terminal": {key: verdict for key in _RESULT_JUDGMENTS},
    }
    return {"type": "object", "additionalProperties": False, "required": list(tables),
            "properties": {name: {"type": "object", "additionalProperties": False,
                                   "required": list(rows), "properties": rows}
                           for name, rows in tables.items()}}


def require_source_run_decisions(value: Any, ledger: Mapping[str, Any]) -> None:
    """A missing, uncertain or negative plan judgment never reaches the candidate."""
    schema = source_run_decisions_schema(ledger)
    if not isinstance(value, Mapping) or set(value) != set(schema["required"]):
        raise ValueError("source plan decisions are incomplete or unexpected")
    for name, table_schema in schema["properties"].items():
        table = value[name]
        if (not isinstance(table, Mapping) or set(table) != set(table_schema["required"])
                or any(type(verdict) is not str or verdict != "yes" for verdict in table.values())):
            raise ValueError(f"source plan {name} decision is not affirmative")


def _canonical_ref(evidence: bytes, value: Any) -> tuple[dict[str, Any], tuple[int, int]]:
    if not isinstance(value, Mapping) or set(value) != {"quote", "context"}:
        raise ValueError("source plan citation fields are invalid")
    if any(not isinstance(v, str) or not v.strip() or len(v) > MAX_AUTHORED_FIELD_VALUE_CHARS
           for v in value.values()):
        raise ValueError("source plan citation is empty or exceeds its bound")
    try:
        canonical = canonical_citation_from_host_selection(evidence, value)
        quote, start = resolve_source_citation(evidence, canonical)
    except GreenfieldModelAuthoringError as exc:
        raise ValueError("source plan citation is absent or ambiguous") from exc
    return canonical, (start, start + len(quote.encode("utf-8")))


def project_source_run_plan(ledger: Mapping[str, Any], *, evidence_text: str) -> dict[str, Any]:
    """Validate exact source choices and map duty IDs to existing canonical IDs."""
    if ledger.get("version") not in {SOURCE_RUN_PLAN_LEDGER_VERSION, PREVIOUS_SOURCE_RUN_PLAN_LEDGER_VERSION}:
        raise ValueError("source run projection requires its exact ledger version")
    if ledger["status"] == "clarification_required":
        if ledger["source_precedence"] or ledger["first_run"] != {"duty_ids": []} or ledger["terminal"] is not None:
            raise ValueError("clarification must carry no source plan")
        return {}
    evidence = evidence_text.encode("utf-8")
    actions = [row for section in _ACTION_SECTIONS for row in ledger[section]]
    by_id = {row["id"]: order for order, row in enumerate(actions, 1)}
    if len(by_id) != len(actions) or not 1 <= len(actions) <= 32:
        raise ValueError("source plan action identities are invalid")
    run = ledger["first_run"]
    if not isinstance(run, Mapping) or set(run) != {"duty_ids"}:
        raise ValueError("source plan first run fields are invalid")
    ids = run["duty_ids"]
    if (not isinstance(ids, list) or not 1 <= len(ids) <= 32
            or any(type(key) is not str or key not in by_id for key in ids) or len(set(ids)) != len(ids)):
        raise ValueError("source plan first run must name unique known action duties")
    declared = [row["id"] for row in ledger["first_path_actions"]]
    if [key for key in ids if key in declared] != declared:
        raise ValueError("source plan first run must preserve declared workflow order")
    raw_edges = ledger["source_precedence"]
    if not isinstance(raw_edges, list) or len(raw_edges) > 64:
        raise ValueError("source plan precedence exceeds its bound")
    constraints: list[dict[str, Any]] = []
    constraint_spans: list[tuple[int, int]] = []
    edges = []
    for raw in raw_edges:
        if not isinstance(raw, Mapping) or set(raw) != {"before_duty_id", "after_duty_id", "constraint_ref"}:
            raise ValueError("source plan precedence fields are invalid")
        if any(type(raw[k]) is not str or raw[k] not in by_id for k in ("before_duty_id", "after_duty_id")):
            raise ValueError("source plan precedence references an unknown duty")
        ref, span = _canonical_ref(evidence, raw["constraint_ref"])
        if span not in constraint_spans:
            constraints.append(ref)
            constraint_spans.append(span)
        edges.append({"before_event": by_id[raw["before_duty_id"]],
                      "after_event": by_id[raw["after_duty_id"]],
                      "constraint_index": constraint_spans.index(span) + 1})
    if len(constraints) > MAX_AUTHORED_LIST_ITEMS:
        raise ValueError("source plan constraints exceed the existing fact bound")
    terminal = ledger["terminal"]
    if not isinstance(terminal, Mapping) or set(terminal) != {"duty_id", "proof_boundary", "result_fact", "result_quote", "result_occurrence"}:
        raise ValueError("source plan requires exact terminal custody")
    if type(terminal["duty_id"]) is not str or terminal["duty_id"] not in by_id:
        raise ValueError("source plan terminal has an unknown producing duty")
    proof, proof_span = _canonical_ref(evidence, terminal["proof_boundary"])
    carrier = terminal["result_fact"]
    if not isinstance(carrier, Mapping) or carrier.get("field") not in TERMINAL_RESULT_FACT_FIELDS:
        raise ValueError("source plan terminal result fact field is invalid")
    field = carrier["field"]
    if field == "first_path":
        if set(carrier) != {"field", "duty_id"} or carrier["duty_id"] not in declared:
            raise ValueError("source plan terminal fact requires a declared first-path duty")
        row = declared.index(carrier["duty_id"]) + 1
        result_fact, fact_span = _canonical_ref(evidence, ledger["first_path_actions"][row - 1]["event_ref"])
    else:
        if set(carrier) != {"field", "source_ref"}:
            raise ValueError("source plan terminal fact citation fields are invalid")
        row = 1
        result_fact, fact_span = _canonical_ref(evidence, carrier["source_ref"])
        if field == "proof_boundary" and fact_span != proof_span:
            raise ValueError("terminal proof-boundary carrier must be the exact independent proof fact")
    result, occurrence = terminal["result_quote"], terminal["result_occurrence"]
    if (not isinstance(result, str) or not result.strip() or len(result) > MAX_AUTHORED_FIELD_VALUE_CHARS
            or type(occurrence) is not int or not 1 <= occurrence <= MAX_AUTHORED_FIELD_VALUE_CHARS):
        raise ValueError("source plan terminal selection is invalid")
    haystack, needle = result_fact["quote"].encode("utf-8"), result.encode("utf-8")
    starts, cursor = [], 0
    while (found := haystack.find(needle, cursor)) >= 0:
        starts.append(found)
        cursor = found + 1
    if occurrence > len(starts):
        raise ValueError("source plan terminal result occurrence is outside its exact fact")
    result_order = by_id[terminal["duty_id"]]
    event_orders = list(by_id.values())
    validate_source_precedence(edges, event_orders=event_orders,
                               operational_constraints=[ref["quote"] for ref in constraints])
    run_orders = [by_id[key] for key in ids]
    recurring = [by_id[row["id"]] for row in ledger["system_duties"]
                 if row["execution_kind"] == "recurring_invariant"]
    validate_first_run({"event_orders": run_orders, "rationale": "Verified source run."},
                       event_orders=event_orders, source_precedence=edges,
                       result_event_order=result_order, recurring_event_orders=recurring)
    spans = [("operational_constraints", index, ref["quote"], span)
             for index, (ref, span) in enumerate(zip(constraints, constraint_spans), 1)]
    spans.append(("proof_boundary", 1, proof["quote"], proof_span))
    if field != "proof_boundary":
        spans.append((field, row, result_fact["quote"], fact_span))
    reference_spans = [_canonical_ref(evidence, control)[1] for control in (
        {"quote": row["quote"], "context": row["context"]} for row in ledger["evidence_controls"]
        if row["handling"] == "reference_context")]
    if ledger["version"] == PREVIOUS_SOURCE_RUN_PLAN_LEDGER_VERSION and any(start < right and left < end for _, _, _, (start, end) in spans
           for left, right in reference_spans):
        raise ValueError("source plan overlaps reference-only context")
    return {"source_precedence": edges, "event_orders": run_orders,
            "terminal": {"result_fact": {"field": field, "row": row},
                         "result_quote": result, "result_occurrence": occurrence,
                         "event_order": result_order},
            "proof_boundary": proof, "operational_constraints": constraints,
            "result_fact": result_fact,
            "fact_spans": spans,
            "result_span": (fact_span[0] + starts[occurrence - 1],
                            fact_span[0] + starts[occurrence - 1] + len(needle))}


def source_run_candidate_first_run(ledger: Mapping[str, Any], result: Mapping[str, Any],
                                    *, evidence_text: str) -> dict[str, Any]:
    """Keep native rationale while refusing duplicate source-plan authorship."""
    design = result.get("provisional_design")
    facts = result.get("facts")
    if ("terminal" in result or "source_precedence" in result or not isinstance(facts, Mapping)
            or "proof_boundary" in facts or not isinstance(design, Mapping)
            or not isinstance(design.get("first_run"), Mapping)
            or set(design["first_run"]) != {"rationale"}):
        raise ValueError("candidate must not author the source-owned complete run or result")
    return {"rationale": design["first_run"]["rationale"],
            "event_orders": project_source_run_plan(ledger, evidence_text=evidence_text)["event_orders"]}


def compile_source_run_candidate(ledger: Mapping[str, Any], result: Mapping[str, Any],
                                 *, evidence_text: str) -> dict[str, Any]:
    """Insert source-owned choices; reject redundant candidate authorship."""
    first_run = source_run_candidate_first_run(ledger, result, evidence_text=evidence_text)
    plan = project_source_run_plan(ledger, evidence_text=evidence_text)
    facts = result["facts"]
    compiled = deepcopy(dict(result))
    constraints = deepcopy(plan["operational_constraints"])
    raw = facts.get("operational_constraints")
    if not isinstance(raw, list):
        raise ValueError("candidate operational constraints must be an array")
    for ref in raw:
        canonical, _ = _canonical_ref(evidence_text.encode("utf-8"), ref)
        if canonical not in constraints:
            constraints.append(canonical)
    if len(constraints) > MAX_AUTHORED_LIST_ITEMS:
        raise ValueError("source and candidate constraints exceed the existing fact bound")
    compiled["facts"]["operational_constraints"] = constraints
    compiled["facts"]["proof_boundary"] = deepcopy(plan["proof_boundary"])
    field = plan["terminal"]["result_fact"]["field"]
    if field in {"product_story", "opportunity", "product_view"}:
        if field not in facts or facts[field] is not None:
            raise ValueError("candidate must explicitly abstain from its source-owned terminal singleton")
        compiled["facts"][field] = deepcopy(plan["result_fact"])
    elif field == "success_metrics":
        raw_metrics = facts.get(field)
        if not isinstance(raw_metrics, list):
            raise ValueError("candidate success metrics must be an array")
        metrics = [deepcopy(plan["result_fact"])]
        for ref in raw_metrics:
            canonical, _ = _canonical_ref(evidence_text.encode("utf-8"), ref)
            if canonical not in metrics:
                metrics.append(canonical)
        if len(metrics) > MAX_AUTHORED_LIST_ITEMS:
            raise ValueError("source and candidate success metrics exceed the existing fact bound")
        compiled["facts"][field] = metrics
    if field != "product_story" and facts.get("product_story") is None:
        raise ValueError("unreserved candidate product_story requires its original source citation")
    compiled["source_precedence"] = deepcopy(plan["source_precedence"])
    compiled["terminal"] = deepcopy(plan["terminal"])
    compiled["provisional_design"]["first_run"] = first_run
    return compiled


def require_source_run_projection(ledger: Mapping[str, Any], *, evidence_text: str,
                                  facts: Mapping[str, Any], source_precedence: Any,
                                  first_run: Mapping[str, Any], terminal: Any = None,
                                  relations: Sequence[Mapping[str, Any]] | None = None,
                                  canonical_facts: bool = False) -> None:
    """Revalidate the same fixed source choices at canonical and passive boundaries."""
    plan = project_source_run_plan(ledger, evidence_text=evidence_text)
    constraints = facts.get("operational_constraints", [])
    prefix = plan["operational_constraints"]
    proof = plan["proof_boundary"]
    if not canonical_facts:
        prefix = [ref["quote"] for ref in prefix]
        proof = proof["quote"]
    if (list(source_precedence) != plan["source_precedence"]
            or first_run.get("event_orders") != plan["event_orders"]
            or facts.get("proof_boundary") != proof or not isinstance(constraints, (list, tuple))
            or list(constraints[:len(prefix)]) != prefix):
        raise ValueError("canonical complete run differs from its verified source plan")
    field = plan["terminal"]["result_fact"]["field"]
    expected = plan["result_fact"] if canonical_facts else plan["result_fact"]["quote"]
    if field == "success_metrics":
        metrics = facts.get(field)
        if not isinstance(metrics, (list, tuple)) or not metrics or metrics[0] != expected:
            raise ValueError("canonical terminal success metric differs from its verified prefix")
    elif field in {"product_story", "opportunity", "product_view"} and facts.get(field) != expected:
        raise ValueError("canonical terminal singleton differs from its verified source fact")
    if relations is None:
        if terminal != plan["terminal"]:
            raise ValueError("canonical terminal differs from its verified source plan")
    else:
        visible = [(row["order"], row["visible_result_quote"]) for row in relations if row["visible_result_quote"]]
        if visible != [(plan["terminal"]["event_order"], plan["terminal"]["result_quote"])]:
            raise ValueError("canonical result producer differs from its verified source plan")


def require_source_run_fact_custody(ledger: Mapping[str, Any], *, evidence_text: str,
                                   source_spans: Sequence[Mapping[str, Any]]) -> None:
    """Equal labels at other addresses cannot replace compiler-owned plan facts."""
    plan = project_source_run_plan(ledger, evidence_text=evidence_text)
    for field, row, quote, (start, end) in plan["fact_spans"]:
        matches = [span for span in source_spans if span.get("section_key") == field
                   and span.get("row_index") == row and span.get("classification") == "product_claim"]
        if len(matches) != 1 or any(matches[0].get(key) != value for key, value in (
                ("text", quote), ("source_start_byte", start), ("source_end_byte", end))):
            raise ValueError("source plan fact differs from its exact verified source address")


def require_source_run_atomic_custody(ledger: Mapping[str, Any], *, evidence_text: str,
                                     atomic_facts: Sequence[Mapping[str, Any]]) -> None:
    """A rehashed passive seal retains each source fact and selected result address."""
    plan = project_source_run_plan(ledger, evidence_text=evidence_text)
    for field, row, quote, (start, end) in plan["fact_spans"]:
        if field == "first_path":
            continue  # Existing action custody verifies this normalized fact independently.
        path = f"/{field}/{row - 1}" if field in {"operational_constraints", "success_metrics"} else f"/{field}"
        if not any(atom.get("normalized_value") == quote
                   and any(link.get("path") == path and link.get("relation_order") == 0
                           for link in atom.get("projection_links", ()))
                   and any(ref.get("source_start_byte") == start and ref.get("source_end_byte") == end
                           for ref in atom.get("source_span_refs", ())) for atom in atomic_facts):
            raise ValueError("sealed source plan fact lost its exact source address")
    start, end = plan["result_span"]
    if not any(atom.get("normalized_value") == plan["terminal"]["result_quote"]
               and any(link.get("relation_order") == plan["terminal"]["event_order"]
                       and link.get("relation_role") == "visible_result_quote"
                       for link in atom.get("projection_links", ()))
               and any(ref.get("source_start_byte") == start and ref.get("source_end_byte") == end
                       for ref in atom.get("source_span_refs", ())) for atom in atomic_facts):
        raise ValueError("sealed source result lost its exact selected source address")
