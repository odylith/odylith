- Bug ID: CB-242

- Current Session Visibility Evidence (2026-09-08): The operator again reports too few interventions while asking for the complete Greenfield-to-memory/execution journey. The original repository launcher reports static Activation ready but zero chat-confirmed events. An explicit visible-intervention fallback is rendered verbatim in the existing conversation; the subsequent status reports two confirmed events through assistant_chat_transcript. This proves manual recovery only, not automatic native delivery, useful ongoing cadence or a root cause for the original absence. No tracked files, host trust or authentication settings were changed in that repository. Session: 019ffcfa-f136-7080-a35d-1c9d6b6d8c79.

- Current Native Contract Check (2026-09-08): The corrected source-local status reader now reports activation degraded against that same actual repo and session: prompt, checkpoint and stop hooks are not recognized. The actual .codex/hooks.json remains the flat event document, while the pushed proof checkpoint uses the native hooks wrapper; CB-304 retains native evidence that the flat document is ignored. The actual launcher reports detached source-local, base_fallback memory and release ineligible. The same five manual/recovery events and two chat confirmations remain; no new automatic delivery was observed. This supersedes the older reader's static-ready claim, not its retained transcript evidence. Matching-runtime installed activation and a fresh/reloaded host session still need actual visible-delivery proof. Do not activate a mixed old-runtime/new-hook arrangement or treat manual acknowledgement as success. Read-only receipt: /private/tmp/odylith-session-resume-proof.45l4zG/intervention-current-session.md. Original tracked files and host trust/auth remain unchanged.

- Integration Acceptance (2026-09-08): Keep this record open until earned decision, risk and verified-result moments survive the actual host transport and are visible across resumed sessions. Registration readiness, hidden context, recorded events and manual acknowledgement copy cannot substitute for observed user value. Preserve the distinct Observation, Proposal and Assist roles; do not solve absence with repetitive diagnostics or unconditional chatter. CB-304 separately owns native confirmation transport and its timeout/receipt boundary.

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
