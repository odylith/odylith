"""Terminal closeout helpers for greenfield proposal commands."""

from __future__ import annotations

from typing import Any, Mapping


def print_apply_result(result: Mapping[str, Any], *, verb: str) -> None:
    print(f"odylith greenfield {verb} wrote confirmed proposal")
    validation_gate = result.get("validation_gate") or result.get("tribunal", {})
    if isinstance(validation_gate, Mapping):
        print(f"- validation gate: {validation_gate.get('status', 'unknown')}")
    print(f"- backlog: {len(result['backlog'])}")
    print(f"- components: {len(result['components'])}")
    print(f"- diagrams: {len(result['diagrams'])}")
    print("- validation already run: proposal schema, product-quality gate, backlog checks, architecture scaffold, dashboard refresh attempt")
    program = result.get("program", {})
    if isinstance(program, Mapping) and bool(program.get("created")):
        print(f"- program: {program.get('umbrella_id')} ({len(program.get('waves', []))} waves)")
    release_target = result.get("release_target", {})
    if isinstance(release_target, Mapping) and str(release_target.get("release_id", "none")).strip() != "none":
        workstreams = release_target.get("workstream_ids", [])
        count = len(workstreams) if isinstance(workstreams, list) else 0
        print(f"- release: {release_target.get('release_id')} ({count} targeted workstreams)")
    _print_completion_quality_debt(result)
    _print_created_surfaces(result)
    next_steps = result.get("next_steps", {})
    if isinstance(next_steps, Mapping):
        _print_next_steps(next_steps)
    dashboard = result.get("dashboard_refresh", {})
    if isinstance(dashboard, Mapping):
        surfaces = ", ".join(str(item) for item in dashboard.get("surfaces", []))
        if dashboard.get("status") == "warning":
            print(f"- dashboard: refresh warning for {surfaces}")
            warning = str(dashboard.get("warning", "")).strip()
            if warning:
                print(f"- dashboard warning: {warning}")
        else:
            print(f"- dashboard: refreshed {surfaces}")
        print(f"- view: {dashboard.get('view')}")
        print("- reflected in: progress lane, workstreams, candidate component specs, and draft architecture topology")


def _print_completion_quality_debt(result: Mapping[str, Any]) -> None:
    debt = result.get("completion_priority_quality_debt")
    if not isinstance(debt, list) or not debt:
        return
    print(f"- quality debt: {len(debt)} non-critical projection issue(s) recorded after governed write")
    for item in debt[:3]:
        print(f"  - {item}")
    if len(debt) > 3:
        print(f"  - {len(debt) - 3} more quality debt item(s)")


def _print_created_surfaces(result: Mapping[str, Any]) -> None:
    backlog_paths = [
        str(row.get("idea_path", "")).strip()
        for row in result.get("backlog", [])
        if isinstance(row, Mapping) and str(row.get("idea_path", "")).strip()
    ]
    spec_paths = [
        str(row.get("spec_path", "")).strip()
        for row in result.get("components", [])
        if isinstance(row, Mapping) and str(row.get("spec_path", "")).strip()
    ]
    diagram_ids = [str(item).strip() for item in result.get("diagrams", []) if str(item).strip()]
    if not backlog_paths and not spec_paths and not diagram_ids:
        return
    print("- created project files:")
    for label, values in (
        ("workstream", backlog_paths[:3]),
        ("component spec", spec_paths[:3]),
    ):
        for value in values:
            print(f"  - {label}: {value}")
    if len(backlog_paths) > 3:
        print(f"  - workstream: {len(backlog_paths) - 3} more workstream file(s)")
    if len(spec_paths) > 3:
        print(f"  - component spec: {len(spec_paths) - 3} more component spec(s)")
    if diagram_ids:
        print(f"  - architecture: {', '.join(diagram_ids)} plus catalog/source render artifacts")


def _print_next_steps(next_steps: Mapping[str, Any]) -> None:
    project_id = str(next_steps.get("project_workstream_id", "")).strip()
    project_title = str(next_steps.get("project_workstream_title", "")).strip()
    start_id = str(next_steps.get("start_workstream_id", "")).strip()
    start_title = str(next_steps.get("start_workstream_title", "")).strip()
    first_wave = str(next_steps.get("first_wave", "")).strip()
    next_release = str(next_steps.get("release_selector", "")).strip()
    project_prompt = str(next_steps.get("project_first_prompt", "")).strip()
    if project_id:
        print(f"- project-first workstream: {project_id} {project_title}".rstrip())
        print("- project story: odylith/index.html?tab=project")
        print(f"- workstream detail: odylith/radar/radar.html?view=plan&workstream={project_id}")
        print("- project gate: review direction choices and readiness gates before opening a technical plan; do not edit source from this closeout")
    if project_prompt:
        print(f"- next project prompt: {project_prompt}")
    if start_id:
        print(f"- future first implementation lane after gates: {start_id} {start_title}".rstrip())
        print(f"- child lane: odylith/radar/radar.html?view=plan&workstream={start_id}")
    if first_wave or next_release:
        lane = " | ".join(
            item
            for item in (f"wave {first_wave}" if first_wave else "", f"release {next_release}" if next_release else "")
            if item
        )
        print(f"- current project lane: {lane}")
    choices = next_steps.get("customization_options", [])
    if isinstance(choices, list) and choices:
        print("- choose before coding:")
        for choice in choices[:8]:
            print(f"  - {choice}")
    readiness_gates = next_steps.get("coding_readiness_gates", [])
    if isinstance(readiness_gates, list) and readiness_gates:
        print("- coding readiness gates:")
        for gate in readiness_gates[:6]:
            print(f"  - {gate}")
    prompt = str(next_steps.get("implementation_prompt", "")).strip()
    if prompt:
        print(f"- post-gate implementation prompt: {prompt}")
    sequence = next_steps.get("operator_sequence", [])
    if isinstance(sequence, list) and sequence:
        print("- operator handoff:")
        for index, step in enumerate(sequence[:5], start=1):
            print(f"  {index}. {step}")
    gates = next_steps.get("validation_gates", [])
    if isinstance(gates, list) and gates:
        print("- proof to name in the child plan:")
        for gate in gates[:6]:
            print(f"  - {gate}")
    commands = next_steps.get("verification_commands", [])
    if isinstance(commands, list) and commands:
        print("- after implementation, verify before next wave:")
        for command in commands[:6]:
            print(f"  - {command}")
