- Bug ID: CB-340

- Status: InProgress

- Current Source Proof (2026-09-10): Shared clipping and its call-site parameters are removed; selected highlight counts remain bounded. Authored summary now precedes optional body detail. The release-copy/loader/renderer/install-asset pack passes 128 controls. The spotlight stylesheet is a single adopted 240-line owner; the shell stylesheet shrinks from 2,530 to 2,303 lines, with unchanged frozen header hashes and cache-fingerprint coverage. All eight authored/bundled and explicit/body-fallback desktop/mobile browser cells pass in 13.26s. They preserve complete copy, reach the last highlight and notes link, and verify pointer Close, reopen and Escape on long authored copy. Independent final UI review accepts the bounded correction after 23 unit and eight browser controls with screenshot inspection. Full suites remain pending; built bbe31214 assets are still the earlier candidate.

- Governance Readback (2026-09-10): Eight real shared-shell desktop/mobile cells pass in 11.06s for both bugs and the Dashboard/Radar specs; all eight screenshots were inspected for complete copy and horizontal bounds. This is rendered-view proof only. The refresh command rendered its three selected surfaces but exited one during initial baseline activation with an after-image fingerprint mismatch for Registry and bundled assets; successful page rendering does not prove atomic publication. The separately blocked B-145 Radar index still requires reconciliation before its plan readback.

- Selection Follow-up (2026-09-10): The broader renderer contract has 32 passes and one failure after full-copy preservation: a single explicit highlight was padded with a body-derived detail before the authored summary. The old negative assertion had been hidden by character clipping. Prefer the supplied summary before optional body detail when filling the existing bounded bullet slots; preserve every selected item completely. No character-length-based selection or extra summary engine is warranted. Receipt: release-spotlight-render-contracts.xml in the retained proof root.

- Mobile Follow-up (2026-09-10): After removing shared clipping, both desktop cells pass and both mobile cells preserve the full highlight but cannot click Close: the Atlas toolbar tab intercepts the button. The retained mobile screenshot shows the tall release dialog extending behind the header. The spotlight must own a bounded, scrollable content region without shortening prose or changing the frozen header. The 2-failure/2-pass receipt is release-note-browser-after.xml; do not treat it as completed browser proof. The 2,530-line shell stylesheet needs a focused release-spotlight style owner if changed; no unrelated shell redesign is in scope.

- Rendered Failure (2026-09-10): All four authored/bundled desktop/mobile spotlight controls fail despite the nine source-note tests passing. Direct rendering reproduces the full highlight ending as `without creating Compass pr...`. The shared release-text normalizer slices characters and appends ellipsis; the presenter requests 180 characters, while authored loading and install fallback also request destructive character limits. Remove the operation and its call-site parameters across this shared owner, retaining selected-item limits and markup normalization. Do not shorten source copy to fit, weaken full-copy assertions, add punctuation repair rules, or infer rendered success from source-note equality. Receipt: /private/tmp/odylith-populated-predecessor-proof.0JeIRw/release-note-browser.xml.

- Focused Proof (2026-09-10): Two maintained controls fail on clean candidate copy: the obsolete apply lifecycle and an authored/bundled mismatch that retained wave-preservation wording only in the bundle. The affected release-note sections now describe complete pre-confirm compilation, exact CONFIRM/EDIT/REJECT, deterministic eligible-host commit and explicit recovery. Both copies match and all nine release-note tests pass. Evidence is retained in /private/tmp/odylith-populated-predecessor-proof.0JeIRw/release-note-before.xml and release-note-after.xml. Rendered readback, wider validation and independent acceptance remain pending; built bbe31214 assets retain the diagnosed old copy and are not relabeled as corrected.

- Created: 2026-09-10

- Severity: P1

- Reproducibility: Always

- Type: OperatorUX

- Description: The v0.1.15 authored release note and bundled mirror still promote Greenfield apply and refresh after apply. The current CLI disables apply and the authoritative runbook requires a complete sealed preview before commit-only CONFIRM.

- Impact: Operational risk: first-time users can follow an unavailable command or misunderstand CONFIRM as starting artifact generation, breaking the review-before-publication workflow.

- Components Affected: odylith

- Environment(s): Clean bbe31214 v0.1.15 full local candidate and corresponding authored release note.

- Detected By: Independent release-wide migration review against the current CLI and Greenfield runbook.

- Failure Signature: Release-note highlights advertise Greenfield apply while the CLI disables it; the note describes refresh after apply.

- Trigger Path: Consumer update spotlight and v0.1.15 release-note view.

- Ownership: Authored release-note content and managed bundle mirror; shared release-text normalization consumed by loading, installation and dashboard presentation.

- Timeline: Captured 2026-09-10 through `odylith bug capture`.

- Blast Radius: Candidate release-note readers and installed update spotlight surfaces.

- SLO/SLA Impact: Consumer guidance contradicts pre-confirm compilation; no new timing measurement.

- Data Risk: No observed data loss or publication; obsolete guidance obscures the reviewed write boundary.

- Security/Compliance: Operational risk is incorrect publication guidance. Confirmation authority must remain explicit; no demonstrated credential exposure.

- Invariant Violated: Consumer documentation must describe sealed preview and commit-only CONFIRM without post-confirm generation or repair.

- Root Cause: Historical release-note content outlived replacement of the apply mechanism.

- Solution: Rewrite affected authored lifecycle text and managed mirror from the supported command contract; verify rendered copy and preserve qualification limits.

- Verification: Verify actual CLI/runbook alignment, exact mirror equality, maintained release-note checks and real-shell desktop/mobile readback.

- Related Incidents/Bugs: B-145; B-142; CB-303.

- Code References: - odylith/runtime/source/release-notes/v0.1.15.md

- Runbook References: - docs/runbooks/odylith-greenfield.md
