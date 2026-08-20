"""Project concise governance narratives from accepted Semantic Intent facts."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


_MAX_NARRATIVE_FACTS = 8
_MAX_NARRATIVE_CANDIDATES = 8
_MAX_SUMMARY_ROWS = 3


def project_semantic_narratives(
    facts: Mapping[str, Sequence[Mapping[str, Any]]],
    relations: Mapping[str, Sequence[Mapping[str, Any]]],
) -> list[dict[str, Any]]:
    """Return source-custodied narrative views without prose interpretation."""

    identities = _rows(facts, "identities")
    actors = _rows(facts, "actors")
    steps = _rows(facts, "workflow_steps")
    states = _rows(facts, "state_objects")
    outputs = _rows(facts, "visible_outputs")
    dependencies = _rows(facts, "external_systems")
    constraints = _rows(facts, "operational_constraints")
    non_goals = _rows(facts, "non_goals")
    index = {
        str(row["fact_id"]): row
        for rows in facts.values()
        for row in rows
    }
    producer_steps = _relation_subjects(relations, "produces", index=index)
    change_steps = _relation_subjects(relations, "changes", index=index)

    result = [
        _product_story(identities, actors, steps, outputs),
        _problem(actors, steps, constraints),
        _customer(identities, actors, steps),
        _opportunity(identities, steps, outputs),
        _product_view(
            identities, outputs, states, dependencies, constraints, non_goals
        ),
        _proof_boundary(outputs, states, constraints, non_goals),
    ]
    metrics = _success_metrics(
        steps,
        states,
        outputs,
        producer_steps=producer_steps,
        change_steps=change_steps,
    )
    evidence = _evidence_requirements(
        states,
        outputs,
        producer_steps=producer_steps,
        change_steps=change_steps,
    )
    return [*result, *metrics, *evidence]


def _product_story(
    identities: Sequence[Mapping[str, Any]],
    actors: Sequence[Mapping[str, Any]],
    steps: Sequence[Mapping[str, Any]],
    outputs: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    scope = _scope(
        steps=steps[:_MAX_SUMMARY_ROWS],
        outputs=outputs[:2],
        identity=identities[:1],
        actors=actors[:2],
    )
    identity = _labels(scope["identity"], fallback="the product")
    participants = _labels(scope["actors"], fallback="the product")
    actions = _actions(scope["steps"])
    text = f"For {participants}, the first path in {identity} is to {actions}."
    if scope["outputs"]:
        text += f" The path makes {_result_subject(scope['outputs'])} visible."
    return _narrative("product_story", 0, text, scope)


def _problem(
    actors: Sequence[Mapping[str, Any]],
    steps: Sequence[Mapping[str, Any]],
    constraints: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    scope = _scope(
        steps=steps[:2],
        constraints=constraints[:2],
        actors=actors[:2],
    )
    participants = _labels(scope["actors"])
    if len(scope["actors"]) == 1:
        text = (
            f"The declared role, {participants}, needs a governed path to "
            f"{_actions(scope['steps'])}."
        )
    elif scope["actors"]:
        text = (
            f"The declared participants, {participants}, need a governed path to "
            f"{_actions(scope['steps'])}."
        )
    else:
        text = f"The product must provide a governed path to {_actions(scope['steps'])}."
    if scope["constraints"]:
        text += f" The path must respect {_labels(scope['constraints'])}."
    return _narrative("problem", 0, text, scope)


def _customer(
    identities: Sequence[Mapping[str, Any]],
    actors: Sequence[Mapping[str, Any]],
    steps: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    if actors:
        scope = _scope(actors=actors[:4])
        participants = _quoted_labels(scope["actors"])
        text = (
            f"The declared participant is {participants}."
            if len(scope["actors"]) == 1
            else f"The declared participants are {participants}."
        )
    else:
        scope = _scope(identity=identities[:1], steps=steps[:1])
        text = (
            "No human participant is declared; the first path is owned by the "
            "product or its systems."
        )
    return _narrative("customer", 0, text, scope)


def _opportunity(
    identities: Sequence[Mapping[str, Any]],
    steps: Sequence[Mapping[str, Any]],
    outputs: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    scope = _scope(
        outputs=outputs[:2], steps=steps[:1], identity=identities[:1]
    )
    identity = _labels(scope["identity"], fallback="the product")
    if scope["steps"]:
        text = (
            f"The opportunity for {identity} is to support the source-backed action "
            f"“{_actions(scope['steps'])}” and make "
            f"{_result_subject(scope['outputs'])} visible."
        )
    else:
        text = (
            f"The opportunity for {identity} is to make "
            f"{_result_subject(scope['outputs'])} visible."
        )
    return _narrative("opportunity", 0, text, scope)


def _product_view(
    identities: Sequence[Mapping[str, Any]],
    outputs: Sequence[Mapping[str, Any]],
    states: Sequence[Mapping[str, Any]],
    dependencies: Sequence[Mapping[str, Any]],
    constraints: Sequence[Mapping[str, Any]],
    non_goals: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    scope = _scope(
        outputs=outputs[:2],
        identity=identities[:1],
        states=states[:1],
        dependencies=dependencies[:1],
        constraints=constraints[:1],
        non_goals=non_goals[:1],
    )
    identity = _labels(scope["identity"], fallback="the declared product")
    text = (
        f"The product view for {identity} includes the first-path workflow and "
        f"{_labels(scope['outputs'])}."
    )
    if scope["states"]:
        text += f" Its durable state is {_labels(scope['states'])}."
    if scope["dependencies"]:
        text += f" Its explicit dependency is {_labels(scope['dependencies'])}."
    if scope["constraints"]:
        text += f" Its operating constraint is {_labels(scope['constraints'])}."
    if scope["non_goals"]:
        text += f" It excludes {_labels(scope['non_goals'])}."
    return _narrative("product_view", 0, text, scope)


def _proof_boundary(
    outputs: Sequence[Mapping[str, Any]],
    states: Sequence[Mapping[str, Any]],
    constraints: Sequence[Mapping[str, Any]],
    non_goals: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    scope = _scope(
        outputs=outputs[:2],
        states=states[:2],
        constraints=constraints[:2],
        non_goals=non_goals[:2],
    )
    clauses = [f"visibility of {_result_subject(scope['outputs'])}"]
    transitions = _transitions(scope["states"])
    if transitions:
        clauses.append(transitions)
    if scope["constraints"]:
        clauses.append(f"compliance with {_labels(scope['constraints'])}")
    text = f"Release evidence must show {_join(clauses)}."
    if scope["non_goals"]:
        text += f" It must also show that {_labels(scope['non_goals'])} remains excluded."
    return _narrative("proof_boundary", 0, text, scope)


def _success_metrics(
    steps: Sequence[Mapping[str, Any]],
    states: Sequence[Mapping[str, Any]],
    outputs: Sequence[Mapping[str, Any]],
    *,
    producer_steps: Mapping[str, Mapping[str, Any]],
    change_steps: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for output in outputs[:4]:
        step = producer_steps.get(str(output["fact_id"]))
        scope = _scope(output=(output,), step=(step,) if step else ())
        if scope["step"]:
            text = (
                f"When {_step_completion(scope['step'])}, the path makes "
                f"{_result_subject(scope['output'])} visible."
            )
        else:
            text = f"The path makes {_result_subject(scope['output'])} visible."
        result.append(_narrative("success_metric", len(result), text, scope))
    for state in states[:4]:
        transition = state.get("transition")
        if not isinstance(transition, Mapping):
            continue
        step = change_steps.get(str(state["fact_id"]))
        scope = _scope(state=(state,), step=(step,) if step else ())
        if scope["step"]:
            text = (
                f"When {_step_completion(scope['step'])}, {_state_subject(scope['state'])} changes "
                f"from {transition['from_state']} to {transition['to_state']}."
            )
        else:
            subject = _state_subject(scope["state"])
            text = (
                f"{subject[:1].upper()}{subject[1:]} changes from "
                f"{transition['from_state']} to {transition['to_state']}."
            )
        result.append(_narrative("success_metric", len(result), text, scope))
    for step in steps:
        if len(result) >= 2:
            break
        scope = _scope(step=(step,))
        result.append(
            _narrative(
                "success_metric",
                len(result),
                f"The first path completes {_quoted_labels(scope['step'])}.",
                scope,
            )
        )
    if len(result) < 2:
        raise ValueError("Semantic narrative projection lacks two observable checks")
    return result


def _evidence_requirements(
    states: Sequence[Mapping[str, Any]],
    outputs: Sequence[Mapping[str, Any]],
    *,
    producer_steps: Mapping[str, Mapping[str, Any]],
    change_steps: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for output in outputs[:4]:
        step = producer_steps.get(str(output["fact_id"]))
        scope = _scope(output=(output,), step=(step,) if step else ())
        if scope["step"]:
            text = (
                f"Evidence must show that {_step_subject(scope['step'])} produced "
                f"{_result_subject(scope['output'])}."
            )
        else:
            text = f"Evidence must show {_result_subject(scope['output'])}."
        result.append(
            _narrative("evidence_requirement", len(result), text, scope)
        )
    for state in states[:4]:
        transition = state.get("transition")
        if not isinstance(transition, Mapping):
            continue
        step = change_steps.get(str(state["fact_id"]))
        scope = _scope(state=(state,), step=(step,) if step else ())
        text = (
            f"Evidence must show {_state_subject(scope['state'])} changing from "
            f"{transition['from_state']} to {transition['to_state']}"
        )
        result.append(
            _narrative("evidence_requirement", len(result), text + ".", scope)
        )
    return result


def _scope(**groups: Sequence[Mapping[str, Any] | None]) -> dict[str, list[Mapping[str, Any]]]:
    accepted: dict[str, list[Mapping[str, Any]]] = {name: [] for name in groups}
    candidate_ids: set[str] = set()
    fact_ids: set[str] = set()
    for name, rows in groups.items():
        for raw in rows:
            if raw is None:
                continue
            row = raw
            row_candidates = {str(value) for value in row.get("candidate_ids", ())}
            fact_id = str(row.get("fact_id") or "")
            if (
                not fact_id
                or fact_id in fact_ids
                or len(fact_ids) >= _MAX_NARRATIVE_FACTS
                or len(candidate_ids | row_candidates) > _MAX_NARRATIVE_CANDIDATES
            ):
                continue
            accepted[name].append(row)
            fact_ids.add(fact_id)
            candidate_ids.update(row_candidates)
    return accepted


def _narrative(
    field: str,
    order: int,
    text: str,
    scope: Mapping[str, Sequence[Mapping[str, Any]]],
) -> dict[str, Any]:
    rows = [row for values in scope.values() for row in values]
    fact_ids = list(dict.fromkeys(str(row["fact_id"]) for row in rows))
    candidate_ids = list(
        dict.fromkeys(
            str(candidate_id)
            for row in rows
            for candidate_id in row.get("candidate_ids", ())
        )
    )
    if not fact_ids or not candidate_ids:
        raise ValueError("Semantic narrative projection lacks source custody")
    return {
        "field": field,
        "order": order,
        "text": text,
        "fact_ids": fact_ids,
        "candidate_ids": candidate_ids,
    }


def _relation_subjects(
    relations: Mapping[str, Sequence[Mapping[str, Any]]],
    kind: str,
    *,
    index: Mapping[str, Mapping[str, Any]],
) -> dict[str, Mapping[str, Any]]:
    result: dict[str, Mapping[str, Any]] = {}
    for relation in relations.get(kind, ()):
        subject = index.get(str(relation.get("subject_id") or ""))
        object_id = str(relation.get("object_id") or "")
        if subject is not None and object_id and object_id not in result:
            result[object_id] = subject
    return result


def _rows(
    facts: Mapping[str, Sequence[Mapping[str, Any]]], name: str
) -> list[Mapping[str, Any]]:
    return list(facts.get(name, ()))


def _attribute(row: Mapping[str, Any], name: str) -> str:
    for attribute in row.get("attributes", ()):
        if isinstance(attribute, Mapping) and attribute.get("name") == name:
            return str(attribute.get("value") or "").strip()
    return ""


def _labels(rows: Sequence[Mapping[str, Any]], *, fallback: str = "") -> str:
    labels = [_fragment(str(row.get("label") or "")) for row in rows]
    return _join([label for label in labels if label]) or fallback


def _actions(rows: Sequence[Mapping[str, Any]]) -> str:
    actions = [
        _fragment(_attribute(row, "action") or str(row.get("label") or ""))
        for row in rows
    ]
    return "; then ".join(action for action in actions if action)


def _quoted_labels(rows: Sequence[Mapping[str, Any]]) -> str:
    return _join(
        [f"“{label}”" for label in (_fragment(str(row.get("label") or "")) for row in rows) if label]
    )


def _step_subject(rows: Sequence[Mapping[str, Any]]) -> str:
    labels = _quoted_labels(rows)
    return f"the {labels} step" if len(rows) == 1 else f"the {labels} steps"


def _step_completion(rows: Sequence[Mapping[str, Any]]) -> str:
    subject = _step_subject(rows)
    return f"{subject} completes" if len(rows) == 1 else f"{subject} complete"


def _result_subject(rows: Sequence[Mapping[str, Any]]) -> str:
    noun = "result" if len(rows) == 1 else "results"
    return f"the {_quoted_labels(rows)} {noun}"


def _state_subject(rows: Sequence[Mapping[str, Any]]) -> str:
    noun = "state" if len(rows) == 1 else "states"
    return f"the {_quoted_labels(rows)} {noun}"


def _transitions(rows: Sequence[Mapping[str, Any]]) -> str:
    values = []
    for row in rows:
        transition = row.get("transition")
        if isinstance(transition, Mapping):
            values.append(
                f"{_fragment(str(row.get('label') or 'state'))} changing from "
                f"{transition['from_state']} to {transition['to_state']}"
            )
    return _join(values)


def _join(values: Sequence[str]) -> str:
    items = [value for value in values if value]
    if len(items) < 2:
        return items[0] if items else ""
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return f"{', '.join(items[:-1])}, and {items[-1]}"


def _fragment(value: str) -> str:
    result = " ".join(value.strip().split())
    while result.endswith((".", "!", "?")):
        result = result[:-1].rstrip()
    return result


__all__ = ["project_semantic_narratives"]
