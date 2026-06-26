"""Construct one confirmed greenfield Radar backlog row."""

from __future__ import annotations

from typing import Any

from odylith.runtime.domain_intelligence import greenfield_confirmed_backlog_text_model as backlog_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import inline_list_sentence
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import normalize_connector_sequence
from odylith.runtime.domain_intelligence.greenfield_text import clean_text
from odylith.runtime.domain_intelligence.greenfield_workstream_intelligence import (
    build_workstream_domain_intelligence,
)


def build_backlog_row(
    *,
    label: str,
    title: str,
    problem: str,
    customer: str,
    opportunity: str,
    product_view: str,
    first_slice: str,
    metrics: list[str],
    component_focus: list[str],
    diagram_focus: list[str],
    dependencies: list[str],
    interfaces: list[str],
    validation: list[str],
    state_object: str,
    evidence_record: str,
    first_path: str,
    proof_boundary: str,
    human_actors: list[str],
    internal_systems: list[str],
    external_systems: list[str],
    non_goals: list[str],
    intelligence_actors: list[str] | None = None,
    workstream_type: str = "implementation",
) -> dict[str, Any]:
    clean_title = _row_text(title)
    clean_problem = _row_text(problem)
    clean_opportunity = _row_text(opportunity)
    clean_product_view = _row_text(product_view)
    clean_first_slice = _row_text(first_slice)
    clean_metrics = _metric_list_items(metrics)
    clean_dependencies = _row_texts(dependencies)
    clean_interfaces = _row_texts(interfaces)
    clean_validation = _row_texts(validation)
    return {
        "title": clean_title,
        "workstream_type": workstream_type,
        "problem": clean_problem,
        "customer": _row_text(customer),
        "opportunity": clean_opportunity,
        "product_view": clean_product_view,
        "success_metrics": clean_metrics,
        "priority": "P1",
        "sizing": "M",
        "complexity": "Medium",
        "recommended_first_slice": clean_first_slice,
        "component_focus": component_focus,
        "related_diagram_slugs": diagram_focus,
        "dependencies": clean_dependencies,
        "interfaces": clean_interfaces,
        "validation": clean_validation,
        "evidence_tier": "user_intent" if workstream_type == "program_parent" else "odylith_assumption",
        "rationale_lines": backlog_text.rationale_lines(
            label=label,
            title=clean_title,
            opportunity=clean_opportunity,
            first_slice=clean_first_slice,
            proof_boundary=proof_boundary,
            deferred_scope=non_goals,
        ),
        "domain_intelligence": build_workstream_domain_intelligence(
            label=label,
            row_title=clean_title,
            problem=clean_problem,
            opportunity=clean_opportunity,
            product_view=clean_product_view,
            first_slice=clean_first_slice,
            metrics=clean_metrics,
            dependencies=clean_dependencies,
            interfaces=clean_interfaces,
            validation=clean_validation,
            state_object=state_object,
            evidence_record=evidence_record,
            first_path=first_path,
            proof_boundary=proof_boundary,
            human_actors=intelligence_actors or human_actors,
            internal_systems=internal_systems,
            external_systems=external_systems,
            non_goals=non_goals,
        ),
    }


def first_success_metric_rows(values: list[str] | None) -> list[str]:
    return _metric_list_items((values or [])[:1])


def _metric_list_items(values: list[str]) -> list[str]:
    rows: list[str] = []
    for value in values:
        text = _metric_list_item(value)
        if text:
            rows.append(text)
    return rows


def _metric_list_item(value: str) -> str:
    return _row_text(inline_list_sentence(value))


def _row_text(value: str) -> str:
    return normalize_connector_sequence(clean_text(value)).strip()


def _row_texts(values: list[str]) -> list[str]:
    rows: list[str] = []
    for value in values:
        text = _row_text(value)
        if text:
            rows.append(text)
    return rows


__all__ = ["build_backlog_row", "first_success_metric_rows"]
