- Bug ID: CB-343

- Status: Open

- Created: 2026-09-23

- Severity: P2

- Reproducibility: Consistent

- Type: OperatorUX

- Description: Before this checkpoint, Greenfield could compile and commit governed artifacts while the next-step package omitted a direct Execution Engine snapshot and post-confirm output did not guarantee one explicit chat-visible Assist fallback. Delivery Intelligence was refreshed indirectly but its staged artifact freshness was not asserted by the Greenfield proof.

- Impact: Operators could receive a successful Greenfield package without a trustworthy execution handoff or visible intervention cue, forcing downstream reinterpretation and weakening end-to-end confidence.

- Components Affected: domain-intelligence-greenfield

- Environment(s): Odylith product repository source-local v0.1.15 on the consolidated target branch

- Detected By: Independent Greenfield integration audit and focused staged-package tests

- Failure Signature: next_steps_preview had no execution_engine_handoff; completion output had no Odylith Assist fallback; staged surface proof did not validate delivery_intelligence.v4.json

- Trigger Path: odylith greenfield propose -> pre-confirm package -> greenfield create --confirm

- Ownership: Greenfield Domain Intelligence, Execution Engine handoff, Delivery Intelligence proof, and Intervention visibility

- Timeline: Captured 2026-09-23 through `odylith bug capture`.

- Blast Radius: All host-model Greenfield proposal and confirmation flows across Codex, Claude, and CLI surfaces

- SLO/SLA Impact: Adds a bounded pre-confirm validation step and keeps 90/120/150 timing guidance visible; no post-confirm model work

- Data Risk: No source-data loss; risk was incomplete provenance and operator visibility

- Security/Compliance: No new security exposure; fail closed on invalid staged delivery artifact

- Invariant Violated: A successful Greenfield package must carry source-grounded execution and visible handoff evidence across governed surfaces

- Root Cause: Greenfield integration stopped at governed artifact publication and relied on indirect surface refresh and terminal navigation rather than explicit execution/intervention contracts.

- Solution: Project a typed Execution Engine snapshot into next_steps_preview, validate the real staged Delivery Intelligence artifact, and render one explicit Assist fallback after confirmation.

- Verification: Focused Greenfield handoff, staged surface proof, CLI, transaction, and host confirmation tests; broader non-holdout Greenfield suite and browser matrix.

- Prevention: Keep engine seams in the sealed package and require fresh staged artifact evidence before confirmation; preserve visible fallback when native hooks are unverified.

- Agent Guardrails: Do not claim automatic chat delivery from hook context alone; do not restore prose parsing or add a second intervention channel.

- Preflight Checks: Search existing Casebook records; run focused tests before full validation; preserve final holdout untouched.

- Regression Tests Added: tests/unit/runtime/test_greenfield_authored_completion_handoff.py; tests/unit/runtime/test_greenfield_surface_refresh_proof.py; tests/unit/runtime/test_greenfield_host_confirmation.py

- Version/Build: 0.1.15 source-local checkpoint 9d01b7aa3

- Config/Flags: No new flags; 90/120/150 remain timing guidance

- Current intervention qualification (2026-09-23): The clean-source Codex
  status probe reports `Activation: degraded` even though the current session
  has `12` confirmed-in-chat Odylith events; this proves assistant-visible
  fallback delivery, not native activation. The clean-source Claude probe also
  reports `Activation: degraded` with zero recorded or confirmed events. The
  full intervention claim gate therefore remains closed until a reloaded,
  trusted host session reports `Activation: ready` plus chat visibility. No
  second intervention channel or post-confirm write was added.

- Engine integration posture (2026-09-23): `odylith validate engine-integrity`
  passes `22/22` engine areas, `22/22` handshakes, and `0` findings. This
  proves the product-level inventory and source/command anchors are wired; it
  does not substitute for native host activation, installed positive semantic
  qualification, strong review, or final holdout evidence.

- Mechanism cleanup checkpoint (2026-09-23): The Greenfield text helper layer
  no longer carries its unreachable regex-based visible-result, proof-boundary,
  action-target, punctuation, and related grammar-repair family. The Atlas
  description path now preserves the source action relation instead of
  rewriting `to` into `for`; no replacement prose cascade was introduced.
  The focused Atlas/render/browser-adjacent checks pass `89`, and the complete
  Greenfield unit frontier passes `2,068`. This is a bounded removal of stale
  mechanism surface, not a release claim; native activation, installed
  positive semantic qualification, strong review, and the protected holdout
  remain open.

- Installed positive qualification attempt (2026-09-23): A clean `HEAD`
  archive of `0.1.15` was built, hosted-style assets were generated, and the
  fourteen-case full-install discovery matrix ran with the standard, rescue,
  and deep `90/120/150` profiles. All `14/14` cases completed but `14/14`
  were provider-gated before semantic authoring: thirteen returned
  `greenfield.model.authoring.returned.invalid.response.no.records.were.created`
  and one exercised the clarification contract without a successful write.
  Direct provider probes independently reproduced `credits_exhausted` for
  `gpt-5.6-sol` high and `gpt-5.6-luna` high. The temporary proof namespace
  cleaned successfully, no governed writes or holdout reads occurred, and no
  product-semantic conclusion is drawn from this run. Installed positive
  qualification, strong review, and final holdout gates remain open until
  model capacity is available.

- Installed capacity-restored discovery rerun (2026-09-24): The same clean
  `0.1.15` full-install archive was rerun after provider capacity recovered,
  covering all `14/14` non-holdout cases across the advisory `90/120/150`
  profiles. Thirteen cases reached commit-only publication with return code
  `0` and twelve carried a passed commit manifest; one clarification case and
  one quantum case remained no-write by contract. The matrix still reported
  `0/14` release-quality passes because this invocation was explicitly
  `proof-tier discovery`: retained private author/review evidence and browser
  proof were not requested, so the evaluator correctly withheld semantic
  scores. Temporary simulation roots cleaned, and the protected holdout was
  neither read nor run. This is evidence that provider capacity and the
  transaction path are live, not release qualification. The next gate is one
  bounded full-install `proof-tier release` run with retained evidence and
  browser proof; no product mechanism change is justified by this diagnostic.
  Evidence: `/tmp/odylith-greenfield-clean.PxI0Kb/installed-positive-rerun.json`.
