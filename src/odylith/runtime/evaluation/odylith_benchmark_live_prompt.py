from __future__ import annotations

import json
from typing import Any, Mapping, Sequence


def _normalize_mode(mode: str) -> str:
    token = str(mode or "").strip()
    if token == "odylith_off":
        return "raw_agent_baseline"
    return token


def _pretty_json(payload: Mapping[str, Any] | None) -> str:
    return json.dumps(dict(payload or {}), indent=2, sort_keys=True, ensure_ascii=False)


def _dedupe_strings(rows: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for raw in rows:
        token = str(raw or "").strip()
        if not token or token in seen:
            continue
        seen.add(token)
        ordered.append(token)
    return ordered


def _string_rows(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(token).strip() for token in value if str(token).strip()]


def _looks_like_code_or_test_path(path: str) -> bool:
    token = str(path or "").strip().lower()
    if not token:
        return False
    return token.endswith(".py") or token.startswith(("src/", "tests/"))


def _focus_starting_files(payload: Mapping[str, Any]) -> list[str]:
    payload_dict = dict(payload or {})
    context_packet = (
        dict(payload_dict.get("context_packet", {}))
        if isinstance(payload_dict.get("context_packet"), Mapping)
        else {}
    )
    anchors = dict(context_packet.get("anchors", {})) if isinstance(context_packet.get("anchors"), Mapping) else {}
    architecture_audit = (
        dict(payload_dict.get("architecture_audit", {}))
        if isinstance(payload_dict.get("architecture_audit"), Mapping)
        else {}
    )
    explicit_code_paths = [
        token
        for token in _string_rows(anchors.get("explicit_paths"))
        if _looks_like_code_or_test_path(token)
    ]
    return _dedupe_strings(
        [
            *_string_rows(payload_dict.get("changed_paths")),
            *_string_rows(payload_dict.get("implementation_anchors")),
            *_string_rows(anchors.get("changed_paths")),
            *explicit_code_paths,
            *_string_rows(architecture_audit.get("changed_paths")),
            *_string_rows(architecture_audit.get("implementation_anchors")),
        ]
    )


def _focus_supporting_docs(payload: Mapping[str, Any]) -> list[str]:
    payload_dict = dict(payload or {})
    context_packet = (
        dict(payload_dict.get("context_packet", {}))
        if isinstance(payload_dict.get("context_packet"), Mapping)
        else {}
    )
    retrieval_plan = (
        dict(context_packet.get("retrieval_plan", {}))
        if isinstance(context_packet.get("retrieval_plan"), Mapping)
        else {}
    )
    architecture_audit = (
        dict(payload_dict.get("architecture_audit", {}))
        if isinstance(payload_dict.get("architecture_audit"), Mapping)
        else {}
    )
    strict_boundary = bool(payload_dict.get("strict_boundary") or architecture_audit.get("strict_boundary"))
    if strict_boundary:
        return []
    docs_rows = _string_rows(payload_dict.get("docs"))
    relevant_docs = _string_rows(payload_dict.get("relevant_docs"))
    if docs_rows:
        return _dedupe_strings(
            [
                *docs_rows,
                *relevant_docs,
                *_string_rows(architecture_audit.get("required_reads")),
            ]
        )
    return _dedupe_strings(
        [
            *relevant_docs,
            *_string_rows(retrieval_plan.get("selected_docs")),
            *_string_rows(architecture_audit.get("required_reads")),
        ]
    )


def _focus_guidance_lines(payload: Mapping[str, Any]) -> list[str]:
    payload_dict = dict(payload or {})
    context_packet = (
        dict(payload_dict.get("context_packet", {}))
        if isinstance(payload_dict.get("context_packet"), Mapping)
        else {}
    )
    narrowing_guidance = (
        dict(payload_dict.get("narrowing_guidance", {}))
        if isinstance(payload_dict.get("narrowing_guidance"), Mapping)
        else {}
    )
    route = dict(context_packet.get("route", {})) if isinstance(context_packet.get("route"), Mapping) else {}
    architecture_audit = (
        dict(payload_dict.get("architecture_audit", {}))
        if isinstance(payload_dict.get("architecture_audit"), Mapping)
        else {}
    )
    lines: list[str] = []
    route_ready = bool(route.get("route_ready"))
    selection_state = str(context_packet.get("selection_state", "")).strip()
    full_scan_recommended = bool(
        payload_dict.get("full_scan_recommended")
        or context_packet.get("full_scan_recommended")
        or architecture_audit.get("full_scan_recommended")
    )
    has_starting_files = bool(_focus_starting_files(payload_dict))
    has_supporting_docs = bool(_focus_supporting_docs(payload_dict))
    has_implementation_anchors = bool(
        _string_rows(payload_dict.get("implementation_anchors"))
        or _string_rows(architecture_audit.get("implementation_anchors"))
    )
    strict_boundary = bool(payload_dict.get("strict_boundary") or architecture_audit.get("strict_boundary"))
    boundary_hints = _dedupe_strings(
        [
            *_string_rows(payload_dict.get("boundary_hints")),
            *_string_rows(architecture_audit.get("boundary_hints")),
        ]
    )
    if strict_boundary:
        lines.append(
            "This is a strict bounded slice. Work from the listed files first and do not open adjacent specs or implementation unless those files or the validator directly contradict each other."
        )
        lines.append(
            "Treat validator-only tests, generated artifacts, dashboards, and rendered outputs as out of scope unless they are already listed anchors or a focused contradiction points directly at them."
        )
        lines.append(
            "Even if Odylith marked the broader task as uncertain elsewhere, keep this slice local and fail closed before widening."
        )
    if route_ready and not full_scan_recommended:
        if selection_state.startswith("x:") or selection_state in {"explicit", "inferred_confident"}:
            lines.append(
                "Odylith considers this slice grounded. Treat the listed anchors as the working set unless they directly contradict the task or validator."
            )
        elif has_starting_files:
            lines.append(
                "Odylith considers this slice grounded. Start with the listed anchors and keep the task local unless they prove insufficient."
            )
        else:
            lines.append(
                "Odylith considers this slice grounded. Keep the task local and do not widen unless the first-pass reads fail."
            )
    elif full_scan_recommended and not strict_boundary:
        lines.append("Odylith did not fully ground this slice. Exhaust the listed anchors and docs before widening.")
    reason = str(narrowing_guidance.get("reason", "")).strip()
    if reason and not lines:
        lines.append(f"Odylith narrowing goal: {reason}")
    lines.extend(boundary_hints[:2])
    if has_supporting_docs:
        lines.append("Read only the listed supporting docs/contracts before looking elsewhere.")
    if has_implementation_anchors:
        lines.append("Read the listed implementation files before searching for code anywhere else.")
    if has_starting_files:
        lines.append("Treat references inside opened files as background, not as a reason to inspect every linked surface.")
    risk_tier = str(dict(architecture_audit.get("execution_hint", {})).get("risk_tier", "")).strip()
    if risk_tier:
        lines.append(f"This is a {risk_tier}-risk review. Finish the listed dossier before opening more files.")
    return _dedupe_strings(lines)


def odylith_focus_lines(prompt_payload: Mapping[str, Any] | None) -> list[str]:
    payload = dict(prompt_payload or {})
    changed_paths = _focus_starting_files(payload)
    docs = _focus_supporting_docs(payload)
    guidance_lines = _focus_guidance_lines(payload)
    lines: list[str] = []
    if changed_paths:
        lines.append("Odylith-selected starting files:")
        lines.extend(f"- {token}" for token in changed_paths[:8])
    if docs:
        if lines:
            lines.append("")
        lines.append("Odylith-selected supporting docs/contracts:")
        lines.extend(f"- {token}" for token in docs[:8])
    if guidance_lines:
        if lines:
            lines.append("")
        lines.extend(guidance_lines[:4])
    if lines:
        lines.append("Open the listed surfaces first.")
        lines.append(
            "Do not run broad repo-wide searches, listings, or scans unless those surfaces prove insufficient or contradictory."
        )
    return lines


def build_agent_prompt(
    *,
    scenario: Mapping[str, Any],
    mode: str,
    prompt_payload: Mapping[str, Any],
    validation_commands: Sequence[str] | None = None,
) -> str:
    normalized_mode = _normalize_mode(mode)
    allow_noop_completion = bool(scenario.get("allow_noop_completion"))
    task_lines = [
        "You are running a benchmark task in a disposable workspace for the Odylith product repository.",
        "Use local repo tools only.",
        "Return only JSON matching the required schema with no markdown fences.",
    ]
    if bool(scenario.get("needs_write")):
        if allow_noop_completion:
            task_lines.append(
                "Make the minimum file changes needed only if the grounded tree fails the task contract; a validator-backed no-op is valid when the current tree already satisfies it."
            )
        else:
            task_lines.append("Make the minimum file changes needed, then stop once the task is ready for the external validator.")
    else:
        task_lines.append("Do not edit files unless the task explicitly requires it.")
    task_lines.append("Keep the evidence cone tight and avoid broad repo scans when the listed anchors and docs suffice.")
    task_lines.append("")
    task_lines.append("Task:")
    task_lines.append(str(scenario.get("prompt", "")).strip())
    changed_paths = [str(token).strip() for token in scenario.get("changed_paths", []) if str(token).strip()]
    required_paths = _dedupe_strings(_string_rows(scenario.get("required_paths")))
    family = str(scenario.get("family", "")).strip()
    if changed_paths:
        task_lines.append("")
        if normalized_mode == "odylith_on":
            task_lines.append("Scenario contract anchors (reference only):")
        else:
            task_lines.append("Known starting anchors:")
        task_lines.extend(f"- {token}" for token in changed_paths)
        if normalized_mode == "odylith_on":
            task_lines.append(
                "These anchors define the benchmark contract. Use the Odylith grounding focus below as the approved first-pass read list when it is present."
            )
    contract_code_paths = [
        token for token in required_paths if token not in set(changed_paths) and _looks_like_code_or_test_path(token)
    ]
    if contract_code_paths:
        task_lines.append("")
        task_lines.append("Grounded contract files:")
        task_lines.extend(f"- {token}" for token in contract_code_paths[:3])
    acceptance = [str(token).strip() for token in scenario.get("acceptance_criteria", []) if str(token).strip()]
    if acceptance:
        task_lines.append("")
        task_lines.append("Acceptance criteria:")
        task_lines.extend(f"- {token}" for token in acceptance)
    focused_local_checks = [str(token).strip() for token in scenario.get("focused_local_checks", []) if str(token).strip()]
    if focused_local_checks:
        task_lines.append("")
        task_lines.append("Suggested first-pass local checks:")
        task_lines.extend(f"- {token}" for token in focused_local_checks)
        task_lines.append("Prefer these targeted checks before any broader local validator on this task.")
        if allow_noop_completion and str(scenario.get("family", "")).strip() in {"install_upgrade_runtime", "agent_activation"}:
            task_lines.append(
                "On this allow-no-op install slice, treat the listed focused checks as the approved first-pass proof path before opening broader runtime or guidance surfaces."
            )
        elif allow_noop_completion and str(scenario.get("family", "")).strip() == "daemon_security":
            task_lines.append(
                "On this allow-no-op daemon slice, treat the listed focused checks as the approved first-pass proof path before changing transport, auth-token, or shutdown code."
            )
    focused_local_check_results = _string_rows(prompt_payload.get("focused_local_check_results"))
    if focused_local_check_results:
        task_lines.append("")
        task_lines.append("Declared Odylith preflight evidence from the current workspace:")
        task_lines.extend(f"- {token}" for token in focused_local_check_results[:8])
        task_lines.append(
            "Treat these focused-check results as current workspace evidence. If they already prove the contract holds, prefer a no-file-change completion unless a grounded contradiction remains."
        )
        if family == "governed_surface_sync":
            task_lines.append(
                "These focused sync results already cover broader validator companions copied into the disposable workspace. Do not inspect or normalize pre-existing dirty Radar ideas, plan records, Registry specs, or Atlas artifacts unless a focused validator failure names them directly."
            )
    command_rows = [
        str(token).strip()
        for token in (validation_commands if validation_commands is not None else scenario.get("validation_commands", []))
        if str(token).strip()
    ]
    hidden_command_rows: list[str] = []
    visible_command_rows = list(command_rows)
    if allow_noop_completion and family == "release_publication":
        hidden_prefixes = (
            "odylith benchmark --repo-root .",
            "PYTHONPATH=src .venv/bin/python -m odylith.runtime.evaluation.odylith_benchmark_graphs",
        )
        visible_command_rows = [
            token
            for token in command_rows
            if not any(token.startswith(prefix) for prefix in hidden_prefixes)
        ]
        hidden_command_rows = [token for token in command_rows if token not in visible_command_rows]
        if not visible_command_rows:
            visible_command_rows = command_rows[:1]
            hidden_command_rows = command_rows[1:]
    if visible_command_rows:
        task_lines.append("")
        task_lines.append("Relevant validation commands:")
        task_lines.extend(f"- {token}" for token in visible_command_rows)
        task_lines.append("The benchmark harness will run these validation commands after your response.")
        if hidden_command_rows:
            task_lines.append(
                "The harness will also run broader publication validators after your response; keep first-pass diagnosis on the visible narrow checks and anchored publication surfaces unless a concrete contradiction remains."
            )
        task_lines.append(
            "Use focused local checks when needed to debug, but do not rerun the full listed validator unless it is necessary to diagnose a failure."
        )
        task_lines.append(
            "If a listed validator is already narrow, prefer running that exact validator over inventing a smaller subset."
        )
        task_lines.append(
            "Even if you run focused checks, your final step must still be a single schema-valid JSON message; do not stop after a command or prose note."
        )
        task_lines.append(
            "Do not treat every file named inside those validators as a required first-pass read; validator-only tests or generated artifacts are out of scope unless a listed anchor or focused contradiction points there."
        )
        if allow_noop_completion:
            task_lines.append(
                "If the grounded tree already satisfies the contract, treat a no-file-change completion as valid once the focused validator confirms it."
            )
            task_lines.append(
                "Do not run the full listed validator during first-pass diagnosis just to prove current truth on an allow-no-op task; prefer a narrower anchor-local check and leave the full validator to the harness unless a concrete contradiction remains."
            )
    if normalized_mode == "odylith_on":
        focus_payload = dict(prompt_payload or {})
        if changed_paths and not _focus_starting_files(focus_payload):
            focus_payload["changed_paths"] = _dedupe_strings(
                [
                    *_string_rows(focus_payload.get("changed_paths")),
                    *changed_paths,
                ]
            )
        focus_lines = odylith_focus_lines(focus_payload)
        task_lines.append("")
        task_lines.append("Odylith grounding focus:")
        if focus_lines:
            task_lines.extend(focus_lines)
        else:
            task_lines.append(_pretty_json(focus_payload))
        if _focus_supporting_docs(focus_payload):
            task_lines.append(
                "Treat the Odylith-selected supporting docs/contracts as read-only references and the only approved read-only expansion beyond the anchors unless a concrete contradiction appears."
            )
            if focused_local_check_results and family in {"install_upgrade_runtime", "agent_activation"}:
                task_lines.append(
                    "The listed supporting docs/contracts are already represented in the focused-check evidence; do not reopen them unless a grounded contradiction or validator failure points there directly."
                )
            else:
                task_lines.append("Read those listed docs/contracts before editing when they are present.")
        else:
            task_lines.append(
                "Treat the listed anchors and any explicit slice-bound acceptance criteria as a hard working boundary unless a concrete contradiction or validator failure forces one adjacent read."
            )
        task_lines.append("Treat the Odylith grounding focus as the approved first-pass read list.")
        task_lines.append(
            "This disposable workspace can still contain many unrelated repo files outside the grounded slice. Ignore them unless they are listed anchors, listed supporting docs/contracts, explicit required paths, or named by a focused validator failure."
        )
        if family == "governed_surface_sync":
            task_lines.append(
                "Do not use pre-existing dirty validator-companion files as a cue to widen this governed-surface task. Those files are background support for sync validation, not part of the writable slice."
            )
        task_lines.append(
            "Do not rewrite policy, guidance, or wording just to restate a contract the grounded anchors already establish."
        )
        if allow_noop_completion:
            task_lines.append(
                "If those grounded anchors already satisfy the task, prefer a validator-backed no-op over speculative rewrites."
            )
            task_lines.append(
                "A validator-backed no-op is fully acceptable for this task; do not invent a code change just because the slice is write-capable."
            )
        elif bool(scenario.get("needs_write")):
            task_lines.append(
                "This is a write-backed slice. Do not conclude with a no-file-change completion unless the task explicitly allows it."
            )
            task_lines.append(
                "If the grounded anchors expose a real gap, patch only the listed writable surfaces before widening anywhere else."
            )
        if visible_command_rows:
            task_lines.append(
                "Before editing, prefer the smallest targeted local check that can confirm whether the reported regression is already fixed."
            )
            if focused_local_checks and family in {"install_upgrade_runtime", "agent_activation"}:
                task_lines.append(
                    "If one of the listed focused install checks passes cleanly, do not widen into adjacent CLI, shell, dashboard, or routing surfaces unless the failure output points there directly."
                )
            elif focused_local_checks and family == "daemon_security":
                task_lines.append(
                    "If the focused daemon validator passes cleanly, do not rewrite auth-token persistence, socket transport, or stop-path logic unless a grounded contradiction remains."
                )
            if allow_noop_completion:
                task_lines.append(
                    "If that focused check passes and the grounded anchors already match the task contract, stop with no file changes."
                )
                if focused_local_checks and family == "validation_heavy_fix":
                    task_lines.append(
                        "If the focused benchmark check passes, treat that as current workspace truth and do not rewrite benchmark expectation literals or published-delta assertions unless the grounded runner code still contradicts the raw-baseline contract."
                    )
            elif bool(scenario.get("needs_write")):
                task_lines.append(
                    "If that focused check fails, keep the fix on the listed writable anchors and rerun the narrow validator before widening."
                )
        if family == "agent_activation":
            task_lines.append(
                "On agent-activation slices, if the focused install validators already pass on the grounded tree, stop with no file changes instead of rewriting install or AGENTS guidance wording."
            )
        elif family == "architecture":
            task_lines.append(
                "On architecture review slices, treat the listed anchors and listed supporting docs as the complete dossier unless an exact required path or concrete contradiction forces one adjacent read."
            )
            task_lines.append(
                "Once that bounded dossier supports the contract, stop and emit the schema-valid JSON response instead of reopening the same files for extra corroboration."
            )
            task_lines.append(
                "Do not inspect release runbooks, Atlas or other component specs, benchmark skills, or broader benchmark helper sources unless one of those exact files is an explicit required path or a concrete contradiction points there."
            )
        elif family == "browser_surface_reliability":
            task_lines.append(
                "On browser reliability slices, prefer the smallest source-of-truth repair on the listed renderer, onboarding, CLI, and browser-test anchors before adding new onboarding-state assertions."
            )
            task_lines.append(
                "If the contract is about the real rendered shell path, restore that path or remove test-only stubs first; do not broaden the browser contract with extra spotlight, reopen-pill, or onboarding-state checks unless the focused validator points there directly."
            )
            task_lines.append(
                "Do not inspect benchmark runner, prompt, or evaluation sources on browser slices unless they are listed anchors or a focused validator failure points there directly."
            )
            task_lines.append(
                "When browser tests already share a top-level real-render helper, preserve that helper and update it in place; do not delete it, shadow it, or replace it with one-off nested helpers that leave callers unresolved."
            )
            task_lines.append(
                "In temporary consumer-repo browser tests, keep shell setup on the existing fake sync or dashboard-refresh hooks; do not unmock or introduce live `sync_workstream_artifacts.main` calls just to prove the rendered-shell contract."
            )
            task_lines.append(
                "Treat install-state persistence and upgrade spotlight storage under `src/odylith/install/` as out of scope on browser slices unless the focused validator or a listed anchor points there directly."
            )
            task_lines.append(
                "Use the listed browser validators and shared real-render helpers for local proof. Do not invent ad hoc Python or shell probes that import `odylith.install.state` or other install persistence helpers just to inspect onboarding or spotlight state."
            )
            task_lines.append(
                "Ignore unrelated benchmark runner, prompt, reasoning, and benchmark-doc files that happen to exist elsewhere in the repo unless they are listed anchors or the focused browser validator cites them directly."
            )
        elif family == "install_upgrade_runtime":
            task_lines.append(
                "On install or rollback slices, keep the fix on manager, runtime, repair, and the focused install tests; do not widen into activation or policy wording when the grounded contract already holds."
            )
            task_lines.append(
                "Do not treat missing repo `AGENTS.md` or `CLAUDE.md` files or benchmark-managed pytest temp/cache paths during your own checks as product regressions on install slices; the harness restores stripped guidance before final validation."
            )
        elif family == "daemon_security":
            task_lines.append(
                "On daemon-security slices, if the focused daemon validator already passes on the grounded tree, stop with no file changes instead of rewriting auth-token persistence, socket transport, or daemon shutdown flow."
            )
        elif family == "merge_heavy_change":
            task_lines.append(
                "On merge-heavy bounded slices, if the listed router and governed-doc anchors already agree and the focused validator passes, finish successfully with no file changes."
            )
            task_lines.append(
                "Treat unrelated stale Registry, Atlas, or spec debt elsewhere in the repo as follow-up context, not as a blocker for this bounded no-op closeout."
            )
        elif family == "component_governance":
            task_lines.append(
                "On component-governance slices, keep the listed Registry entry, component spec, Mermaid source, and paired Atlas catalog or index artifacts synchronized as one bounded truth set."
            )
            task_lines.append(
                "If the listed component-governance validators already pass on that bounded truth set, stop with no file changes instead of restating the same contract through speculative Registry, Atlas, or benchmark-doc edits."
            )
            task_lines.append(
                "Do not close out after updating only the component spec or Mermaid source when a listed catalog or index artifact still needs the matching update."
            )
            task_lines.append(
                "If the required paths also list benchmark docs or maintainer guidance, treat those docs as part of the same bounded truth set when the focused validator still reports contract drift there; do not leave them as read-only support context."
            )
            task_lines.append(
                "Do not inspect benchmark runner code, graph generators, benchmark docs, or maintainer benchmark skills on this family unless they are explicit required paths or a focused validator failure cites them."
            )
            task_lines.append(
                "Do not edit `src/odylith/cli.py`, validator harness helpers, install or release runbooks, or broader benchmark publication infrastructure on this family unless one of those exact files is an explicit required path or the focused validator failure cites it directly."
            )
            task_lines.append(
                "If the validators fail because Atlas catalog references outside the bounded truth set are missing from the workspace, treat that as a bounded blocker to report, not a reason to mutate CLI or validator infrastructure."
            )
        elif family == "compass_brief_freshness":
            task_lines.append(
                "On Compass freshness slices, keep the writable boundary on the listed Compass runtime, brief narrator, focused tests, and the named Compass or product runtime surfaces."
            )
            task_lines.append(
                "If the listed Compass freshness validators already pass on that bounded runtime slice, stop with no file changes instead of speculative freshness or narration rewrites."
            )
            task_lines.append(
                "Do not widen into install, repair, or context-engine docs unless a listed anchor or focused validator failure points there directly."
            )
        elif family == "consumer_profile_compatibility":
            task_lines.append(
                "On consumer-profile compatibility slices, keep writes on the listed consumer-profile code and tests plus the named AGENTS and component-spec surfaces."
            )
            task_lines.append(
                "If the listed consumer-profile validator already passes on that bounded compatibility slice, stop with no file changes instead of rebinding truth roots or widening into broader Registry governance."
            )
            task_lines.append(
                "Do not widen into component inventory or broader Registry governance unless a listed anchor or focused validator failure points there directly."
            )
        elif family == "governed_surface_sync":
            task_lines.append(
                "On governed-surface sync slices, keep writes on the listed governance surface docs and the named Radar index only."
            )
            task_lines.append(
                "If the listed sync validators already pass on that bounded slice, stop with no file changes instead of widening into store code, runtime helpers, or broader governance cleanup."
            )
            task_lines.append(
                "Do not widen into Radar idea docs, plan records, Registry inventory, Atlas catalog artifacts, or broader governance maintenance drift unless a listed anchor or focused validator failure points there directly."
            )
        elif family == "cross_surface_governance_sync":
            task_lines.append(
                "On cross-surface governance sync slices, keep the writable boundary on the listed sync engine and paired backlog, plan, Registry, or Atlas surfaces."
            )
            task_lines.append(
                "If the focused sync validator passes on that bounded slice, do not turn unrelated pre-existing repo drift into a blocked closeout."
            )
            task_lines.append(
                "Treat rendered Radar or Compass HTML, backlog JS payloads, traceability JSON, and unrelated Radar idea notes as out of scope unless those exact files are listed required paths or the focused sync validator points there directly."
            )
        elif family == "release_publication":
            task_lines.append(
                "On benchmark publication slices, do not rerun the full benchmark proof lane yourself during first-pass diagnosis; rely on the listed narrow checks and stop with no file changes when the anchored publication surfaces already match."
            )
            task_lines.append(
                "If the copied artifacts, anchored benchmark tables, and release-proof docs already reflect the validated report, finish with no file changes instead of rewriting publication wording."
            )
            task_lines.append(
                "Use repo-relative paths only in commands, reads, and patch targets on publication slices; never use `/tmp` or other absolute workspace paths."
            )
            task_lines.append(
                "Treat graph command output paths and generated SVGs as validator-produced outputs, not manual patch targets; map any absolute output path back to the tracked repo-relative docs/benchmarks target before editing."
            )
            task_lines.append(
                "Unrelated dirty evaluation helpers under `src/odylith/runtime/evaluation/`, rendered shell pages such as `odylith/index.html` or `odylith/compass/compass.html`, and generated proof SVGs are out of scope unless they are explicit required paths or a focused validator failure cites them."
            )
        elif family == "validation_heavy_fix" and allow_noop_completion:
            task_lines.append(
                "On validation-heavy benchmark gate slices, if the focused runner validator already passes on the grounded tree, stop with no file changes instead of rewriting benchmark expectation literals or chasing cheaper-baseline optics."
            )
        task_lines.append(
            "Do not follow links or references from opened docs or skills unless that next file is needed to satisfy the task or validator."
        )
        task_lines.append("If you must widen, widen by one adjacent file at a time and stop as soon as the contradiction is resolved.")
    task_lines.append("")
    task_lines.append("Final response contract:")
    task_lines.append(
        '- Emit exactly one JSON object with keys: "status", "summary", "changed_files", "validation_commands_run", "validation_summary", "notes".'
    )
    task_lines.append("- Do not output markdown fences, prose, or a trailing explanation.")
    task_lines.append("- Always emit that JSON object even when blocked or failed.")
    task_lines.append(
        "Mark status as completed only if the task is actually finished. Use blocked when the workspace or validator contract prevents completion."
    )
    return "\n".join(task_lines).strip() + "\n"
