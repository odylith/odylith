- Bug ID: CB-183

- Status: Open

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
