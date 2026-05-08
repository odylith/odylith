"""Terminal closeout helpers for greenfield proposal commands."""

from __future__ import annotations

from typing import Any, Mapping


def print_apply_result(result: Mapping[str, Any], *, verb: str) -> None:
    print(f"odylith greenfield {verb} wrote confirmed proposal")
    tribunal = result.get("tribunal", {})
    if isinstance(tribunal, Mapping):
        print(f"- tribunal: {tribunal.get('status', 'unknown')}")
    print(f"- backlog: {len(result['backlog'])}")
    print(f"- components: {len(result['components'])}")
    print(f"- diagrams: {len(result['diagrams'])}")
    print("- validation already run: proposal schema, proposal Tribunal, governed backlog Tribunal, Atlas scaffold, surface refresh")
    program = result.get("program", {})
    if isinstance(program, Mapping) and bool(program.get("created")):
        print(f"- program: {program.get('umbrella_id')} ({len(program.get('waves', []))} waves)")
    release_target = result.get("release_target", {})
    if isinstance(release_target, Mapping) and str(release_target.get("release_id", "none")).strip() != "none":
        workstreams = release_target.get("workstream_ids", [])
        count = len(workstreams) if isinstance(workstreams, list) else 0
        print(f"- release: {release_target.get('release_id')} ({count} targeted workstreams)")
    _print_created_surfaces(result)
    next_steps = result.get("next_steps", {})
    if isinstance(next_steps, Mapping):
        _print_next_steps(next_steps)
    dashboard = result.get("dashboard_refresh", {})
    if isinstance(dashboard, Mapping):
        surfaces = ", ".join(str(item) for item in dashboard.get("surfaces", []))
        print(f"- dashboard: refreshed {surfaces}")
        print(f"- view: {dashboard.get('view')}")
        print("- reflected in: Compass current lane, Radar workstreams, Registry candidate specs, Atlas draft topology")


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
    print("- created governance files:")
    for label, values in (
        ("Radar", backlog_paths[:3]),
        ("Registry", spec_paths[:3]),
    ):
        for value in values:
            print(f"  - {label}: {value}")
    if len(backlog_paths) > 3:
        print(f"  - Radar: {len(backlog_paths) - 3} more workstream file(s)")
    if len(spec_paths) > 3:
        print(f"  - Registry: {len(spec_paths) - 3} more component spec(s)")
    if diagram_ids:
        print(f"  - Atlas: {', '.join(diagram_ids)} plus catalog/source render artifacts")


def _print_next_steps(next_steps: Mapping[str, Any]) -> None:
    start_id = str(next_steps.get("start_workstream_id", "")).strip()
    start_title = str(next_steps.get("start_workstream_title", "")).strip()
    first_wave = str(next_steps.get("first_wave", "")).strip()
    next_release = str(next_steps.get("release_selector", "")).strip()
    if start_id:
        print(f"- exact first coding workstream: {start_id} {start_title}".rstrip())
        print(f"- Radar deep link: odylith/radar/radar.html?view=plan&workstream={start_id}")
    if first_wave or next_release:
        lane = " | ".join(
            item
            for item in (f"wave {first_wave}" if first_wave else "", f"release {next_release}" if next_release else "")
            if item
        )
        print(f"- current implementation lane: {lane}")
    prompt = str(next_steps.get("implementation_prompt", "")).strip()
    if prompt:
        print(f"- next agent prompt: {prompt}")
    sequence = next_steps.get("operator_sequence", [])
    if isinstance(sequence, list) and sequence:
        print("- operator handoff:")
        for index, step in enumerate(sequence[:5], start=1):
            print(f"  {index}. {step}")
    gates = next_steps.get("validation_gates", [])
    if isinstance(gates, list) and gates:
        print("- expected implementation proof:")
        for gate in gates[:6]:
            print(f"  - {gate}")
    commands = next_steps.get("verification_commands", [])
    if isinstance(commands, list) and commands:
        print("- verify before next wave:")
        for command in commands[:6]:
            print(f"  - {command}")
