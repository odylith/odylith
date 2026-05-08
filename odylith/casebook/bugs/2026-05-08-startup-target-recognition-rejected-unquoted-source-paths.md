- Bug ID: CB-183

- Status: FixedPendingRelease

- Created: 2026-05-08

- Severity: P2

- Reproducibility: High

- Type: Product

- Description: Startup target recognition rejected unquoted source paths

- Impact: Host agents can see a false needs-target startup result even when the operator or visible UI names concrete source files, causing noisy negative commentary and unnecessary fallback work.

- Components Affected: context-engine

- Environment(s): Odylith product repo maintainer source path, 2026-05-08 startup bootstrap.

- Detected By: Operator report after Codex surfaced a negative startup narrowing message despite concrete file names.

- Failure Signature: odylith start --intent 'fix src/...' returned lane narrowing, status needs target, reason Need one code path, while JSON target_resolution already had writable candidate file targets.

- Trigger Path: PYTHONPATH=src python3 -m odylith.cli start --repo-root . --intent 'fix src/odylith/runtime/governance/component_authoring.py and src/odylith/runtime/context_engine/odylith_context_engine_packet_session_runtime.py'

- Ownership: Context Engine startup path scope, raw path extraction, narrowing guidance, and host startup summary.

- Timeline: Captured 2026-05-08 through `odylith bug capture`.

- Blast Radius: Codex and Claude startup grounding, host-visible progress summaries, and any turn that names unquoted src paths through intent, visible text, or surface context.

- SLO/SLA Impact: First-turn grounding can waste time and reduce trust by forcing a bogus narrowing loop instead of admitting the supplied file target.

- Data Risk: No data-loss risk; runtime packet state and generated startup summaries can misrepresent the actual target resolution.

- Security/Compliance: No direct security exposure; compliance posture is operator-trust and auditability of startup routing decisions.

- Invariant Violated: Concrete repo file paths in intent, visible text, or surface context must satisfy startup target narrowing and must not produce a user-visible needs-target message.

- Solution: Startup intent path anchoring now accepts unquoted existing paths and planned new files under trusted repo roots with source/config/doc/test suffixes. Successful bootstrap output prints a compact `target` line, while untrusted planned suffixes remain rejected.

- Rollback/Forward Fix: Forward fix only; reverting would restore false needs-target startup results for planned new source files.

- Verification: Existing unquoted source-path repro returns bootstrap with two writable targets and no needs-target status. Planned new-file intent for `src/odylith/runtime/context_engine/new_startup_probe.py` returns bootstrap and prints the recognized target.

- Prevention: Keep startup path-intake tests covering existing unquoted paths, planned new trusted paths, untrusted suffix rejection, narrowing suppression for actionable targets, and CLI target-summary output.

- Regression Tests Added: tests/unit/runtime/test_context_grounding_hardening.py::test_session_scope_accepts_unquoted_src_anchor_paths
- tests/unit/runtime/test_context_engine_intent_anchors.py::test_session_scope_accepts_planned_new_src_file_anchor_paths
- tests/unit/runtime/test_context_engine_intent_anchors.py::test_session_scope_rejects_untrusted_planned_path_extensions
- tests/unit/test_cli.py::test_start_bootstrap_lane_prints_recognized_target

- GitHub Status: fixed_pending_release

- Fixed In: 0.1.15

- Public Response: pending

- Code References: - src/odylith/runtime/context_engine/odylith_context_engine_hot_path_scope_runtime.py
- src/odylith/runtime/context_engine/odylith_context_engine_intent_anchor_runtime.py
- src/odylith/cli.py
