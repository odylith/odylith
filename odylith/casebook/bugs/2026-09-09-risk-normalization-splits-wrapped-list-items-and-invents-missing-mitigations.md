- Bug ID: CB-335

- Frozen Checkpoint Verification (2026-09-09): The final frozen integrated source passes 5,002 runtime, 1,168 install and 340 browser checks (one fixture skip), with ten current-record desktop/mobile passes. The actual 95-plan audit reports zero byte or render changes, placeholder growth or non-idempotence; all 3,191 selected proof inputs stay unchanged. Earlier rejected formatter mechanisms remain historical evidence. Release qualification remains separate.

- Independent Final Review (2026-09-09): Twenty-six independently asserted cases pass, including five causal whole-section bypass controls, nine HTML/emphasis custody cases, five earlier list/literal/whitespace cases, one local-uncertainty case, two required-mitigation rejection cases and four exact-inventory reporting cases. No actionable finding remains in this bounded review. Source and test owners are terminal; wider regression and rendered readback still gate the stable checkpoint.

- Current Bounded Proof (2026-09-09): The 396-line source owner removes the physical-line renderer and whole-section ambiguity bypass. CommonMark ancestry and source positions preserve owned blocks, inline enclosures, hard breaks and literal whitespace; unresolved HTML is opaque only within its paragraph. Standard HTML void-element grammar allows proven labels after those elements. All 84 combined focused controls pass; 67 formatter/validator controls also pass under Markdown 4, independently of the main Markdown 3 environment. The actual 95-plan read-only audit produces no byte/render changes, placeholder growth or idempotency failures, and the CLI reports all 95 checked files. Final independent re-review and frozen broader proof remain pending; no additional plan writer or live Greenfield experiment has run.

- Section-bypass Rejection (2026-09-09): The inline-container candidate passes 61 focused controls but treats unresolved HTML, including valid void elements such as `<br>`, as a reason to preserve the entire risk section. Its equality-based validator then reports malformed unrelated top-level mitigation relationships as canonical. Preserving ambiguous source must not bypass independent records or silently erase validation coverage. Keep uncertainty local to the enclosing source span and apply actual HTML grammar at void-element boundaries; no domain vocabulary or example-specific exceptions are justified.

- Inline-container Review Finding (2026-09-09): Independent re-review closes the loose-list, code-span, hard-break and whitespace failures, with 48 focused controls passing, but finds a remaining P2 boundary defect. A checked risk containing `<code>the Mitigation: test</code>` or `<kbd>` is split inside the HTML element and invents a completed mitigation; splitting `*a risk Mitigation: a fix*` also destroys emphasis. Text-token eligibility alone does not prove an inline-container boundary. Preserve enclosed source and split only at proven container boundaries; add independent rendered-semantic controls before correction. Do not add tag-name regex exclusions. The formatter remains unqualified and no additional plan writer runs.

- Independent Review Rejection (2026-09-09): The CommonMark paragraph adapter still feeds a physical-line pending-entry renderer. A valid loose list, an owned second paragraph, or an owned fenced block flushes the parent risk and moves its real mitigation under a fabricated Unspecified risk. Inline-code `Mitigation:` text is also interpreted as a live label; global whitespace collapse alters inline code and hard breaks, while trimming opaque lines alters fenced examples. All three corruptions can be idempotent, so idempotency alone is not custody proof. Carry actual list ancestry and preserve source spans through the complete formatter; do not add blank-line or vocabulary exceptions. This finding rejects the candidate despite its 46 passing focused checks.

- Inventory Evidence Before Review: The previous canonical writer changed 30 of 95 plans only after a read-only comparison found identical words and CommonMark rendering apart from whitespace, with no added placeholders. Those finite examples do not establish general Markdown safety. The new review counterexamples are independent synthetic controls; no second plan writer is authorized until they and the actual inventory pass.

- Candidate Rejection (2026-09-09): The first indented-continuation iterator passes 32 focused controls but still corrupts valid lazy paragraph continuations and fenced source examples. A risk sentence wrapped without indentation gains invented TODO and Unspecified-risk rows; a fenced `- Risk:` example is changed into a real checked-list record. Extending block-start regex exclusions would preserve the failing physical-line abstraction. Replace that candidate with CommonMark block spans, keep literal examples opaque, and test the public normalization behavior before any plan writer runs. A whole-inventory dry-run also exposes pre-existing placeholder damage in completed plans; do not silently reconstruct historical meaning.

- Status: Open

- Created: 2026-09-09

- Severity: P1

- Reproducibility: Always

- Type: Tooling

- Description: The initial dry-run for newly covered dated active plans shows the risk normalizer flushing a Risk at its indented continuation line, inserting a TODO mitigation, then inventing an Unspecified risk for the actual following mitigation. This affects seven of ten initial proposed formatting rewrites, including the Greenfield plan. The initial damaging candidate was not applied; later finite-inventory and independent-review evidence is recorded above.

- Impact: Routine governed sync can detach mitigation ownership and replace complete authored risk relationships with invented placeholder records.

- Components Affected: odylith

- Environment(s): Detached source-local product proof checkout at b62b3f56 with the bounded CB-334 active-plan discovery correction.

- Detected By: Maintainer comparison of existing plan bytes against the normalizer return value before authorizing its CLI writer.

- Failure Signature: A wrapped Risk followed by an indented Mitigation gains TODO (add explicit mitigation) and Unspecified risk (legacy backfill) rows.

- Trigger Path: odylith governance normalize-plan-risk-mitigation; automatic risk normalization during odylith sync.

- Ownership: Plan risk/mitigation Markdown normalization.

- Timeline: Captured 2026-09-09 through `odylith bug capture`.

- Blast Radius: Active and completed plans with wrapped list-item paragraphs when selected for governance normalization.

- SLO/SLA Impact: Governance semantic fidelity and release evidence are compromised; no direct request latency change is demonstrated.

- Data Risk: Potential source-truth corruption. Thirty later canonical formatting changes passed the finite 95-plan comparison, but independent controls still reject the candidate. Preserve authored before-images and do not reconstruct historical unknown meaning.

- Security/Compliance: Safety and policy posture: risk-control provenance can be misrepresented; no demonstrated exploit, privacy leak or credential impact.

- Invariant Violated: Formatting must preserve complete authored risk and mitigation text, relationship ownership, and checkbox states without invented placeholder facts.

- Root Cause: Physical-line parsing flushes a pending risk before an indented continuation; subsequent mitigation text is then treated as orphaned.

- Solution: Preserve logical Markdown list-item structure before formatting and prove wrapped positive/negative, relationship and idempotency controls without adding domain vocabulary or regex cascades.

- Verification: Reproduce on independent wrapped risk and mitigation examples, inspect unchanged current-plan relationships, then run focused normalization and validation proof.

- Agent Guardrails: Do not run normalization writes on the 25-plan tree until the candidate diff contains no invented placeholders or detached mitigations; do not rewrite authored prose just to satisfy the flawed normalizer.

- Related Incidents/Bugs: CB-334; CB-303; B-142

- Code References: - src/odylith/runtime/governance/normalize_plan_risk_mitigation.py
