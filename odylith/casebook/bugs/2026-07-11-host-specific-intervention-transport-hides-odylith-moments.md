- Bug ID: CB-242

- Status: Open

- Created: 2026-07-11

- Severity: P1

- Reproducibility: Consistent

- Type: UX

- Description: The visible-intervention fallback can show diagnostic host/tool language, prompt eligibility is too keyword-bound for ordinary UX feedback, and the Codex stop continuation request is discarded before transport. This makes useful Odylith observations and assists inconsistent across Codex, Claude, and future hosts.

- Impact: Operators do not reliably see useful Odylith guidance and may see internal delivery language when they do.

- Components Affected: intervention-engine

- Environment(s): Product-repo maintainer source-local and installed host hook paths

- Detected By: Operator screenshot and adversarial code review

- Failure Signature: Codex visible fallback emits host-specific diagnostic prose; Claude has no equivalent automatic visible delivery; stop continuation flag is dropped.

- Trigger Path: Prompt submit, hook stop, and visible-intervention recovery workflows

- Ownership: Intervention Engine host-surface boundary

- Timeline: Captured 2026-07-11 through `odylith bug capture`.

- Blast Radius: All supported and future model hosts

- SLO/SLA Impact: Breaks the observable intervention UX contract and delays user decisions.

- Data Risk: No data loss; user-facing trust and clarity risk.

- Security/Compliance: No security impact.

- Invariant Violated: A shared, useful, host-neutral intervention plan must survive transport and never expose internal hook state.

- Root Cause: Presentation, eligibility, and transport policy are distributed across host adapters instead of sharing one visible-moment contract.

- Solution: Introduce a host-neutral visible-moment plan, preserve continuation delivery intent, broaden earned user-feedback eligibility, and prove cross-host rendered parity.

- Rollback/Forward Fix: Forward fix with regression and browser coverage; preserve silent success hooks where required.

- Verification: Cross-host exact Markdown parity, stop continuation transport, ordinary UX-feedback eligibility, and browser normal/empty/degraded scenarios.

- Prevention: Keep user-facing copy in a shared planner and restrict host adapters to transport metadata.

- Agent Guardrails: Never render host names, hooks, tools, or delivery ledger state in customer-facing intervention copy.

- Preflight Checks: Inspect intervention status and visible fallback before claiming chat-visible UX.

- GitHub Status: confirmed

- Public Response: pending

- Code References: - src/odylith/runtime/intervention_engine/visibility_broker.py
- src/odylith/runtime/intervention_engine/host_surface_runtime.py
- src/odylith/runtime/intervention_engine/prompt_signal_runtime.py
