- Bug ID: CB-046

- Status: Open

- Created: 2026-04-02

- Severity: P0

- Reproducibility: High

- Type: Product

- Description: The live proof support-doc selector could overvalue generic
  guidance surfaces such as `AGENTS.md` and `agents-guidelines/*` when their
  path tokens overlapped a changed filename, even if the truthful slice was an
  install, closeout, or other subsystem task with more relevant contracts or
  runbooks available.

- Impact: `odylith_on` could enter the live run with the wrong supporting
  docs, widen into adjacent governance or orchestration surfaces, and pay
  extra token and time tax without improving recall, validation, or fit. On
  strict bounded slices, the same payload could still inherit a contradictory
  “Odylith did not fully ground this slice” widening cue.

- Components Affected: `src/odylith/runtime/evaluation/odylith_benchmark_prompt_payloads.py`,
  `src/odylith/runtime/evaluation/odylith_benchmark_live_prompt.py`,
  proof support-doc ranking, bounded-slice widening contract.

- Environment(s): Odylith product repo maintainer mode, detached
  `source-local`, live weak-family proof reruns on install, closeout, and
  governance-heavy scenarios.

- Root Cause: Support-doc ranking primarily optimized for generic document
  strength and simple token overlap. Tokens like `agents` from
  `src/odylith/install/agents.py` falsely made `AGENTS.md` and
  `agents-guidelines/*` look relevant, while strict bounded slices could still
  inherit `full_scan_recommended` language from broader packet state.

- Solution: Rank support docs by slice relevance before generic doc strength,
  keep component specs as the only generic fallback when stronger relevant
  docs exist, and suppress widening guidance on strict bounded slices even if
  the broader packet was uncertain.

- Verification: Added regression coverage proving that install-oriented slices
  now prefer the install and upgrade runbook over generic guidance docs, and
  that strict bounded focus lines no longer tell Codex to widen because of
  inherited `full_scan_recommended` state.

- Prevention: Live proof doc selection must optimize for truthful
  task-locality, not just for globally “strong” governance surfaces. Generic
  guidance is only helpful when it is also slice-relevant.

- Detected By: Targeted weak-family proof rerun comparison plus direct prompt
  payload inspection for `install-time-agent-activation-contract` and bounded
  closeout slices.

- Failure Signature: Live prompt payloads on install slices include
  `AGENTS.md`, `agents-guidelines/*`, or unrelated skills while omitting the
  install runbook; strict bounded prompts can simultaneously say “keep this
  slice bounded” and “Odylith did not fully ground this slice.”

- Trigger Path: `odylith benchmark --repo-root . --profile proof` through
  `supplement_live_prompt_payload(...)`, `select_live_prompt_support_docs(...)`,
  and `odylith_focus_lines(...)`.

- Ownership: Benchmark proof support-doc selection and bounded-slice prompt
  discipline.

- Timeline: After the clean-room fairness bugs were fixed, the next remaining
  proof misses were increasingly last-mile grounding problems: the right files
  were being found internally, but the live proof handoff could still carry
  the wrong surrounding docs and contradictory widening language.

- Blast Radius: Proof precision, hallucinated-surface rate, token efficiency,
  time to valid outcome, and trust that `odylith_on` is being evaluated on the
  same truthful slice it grounded internally.

- SLO/SLA Impact: Maintainers can burn time on memory or ML ideas when the
  immediate loss is still deterministic selector quality.

- Data Risk: Low direct data risk, high benchmark-integrity risk.

- Security/Compliance: None directly; this is a slice-selection and prompt
  discipline defect.

- Invariant Violated: Odylith's proof handoff must prefer the most
  slice-relevant supporting contracts and must not tell a strict bounded slice
  to widen because of unrelated broader packet uncertainty.

- Workaround: Manual prompt inspection and bespoke reruns. Not acceptable as a
  release benchmark process.

- Rollback/Forward Fix: Forward fix only.

- Agent Guardrails: Do not suppress this by deleting useful install or release
  docs, and do not weaken `odylith_off`. Improve relevance ranking for
  `odylith_on` instead.

- Preflight Checks: Inspect changed paths, live prompt docs, bounded-slice
  focus lines, and family-level hallucination deltas together before changing
  support-doc selection again.

- Regression Tests Added:
  `test_select_live_prompt_support_docs_prefers_slice_relevant_docs_over_generic_guidance`,
  `test_supplement_live_prompt_payload_keeps_agents_guidance_docs_when_impact_report_surfaces_them`,
  `test_odylith_focus_lines_do_not_recommend_widening_for_strict_boundary`

- Monitoring Updates: Treat unexpected generic guidance docs in install or
  closeout proof prompts as a selector regression even if packet recall
  remains high.

- Residual Risk: Medium until the fresh weak-family proof rerun shows a real
  live precision and fit gain on the affected cases.

- Related Incidents/Bugs:
  `2026-04-02-benchmark-live-prompt-surfaced-routing-metadata-instead-of-concrete-focus.md`,
  `2026-04-01-benchmark-live-prompt-drops-selected-docs-before-codex-handoff.md`,
  `2026-04-02-benchmark-warm-cold-proof-instability-flips-narrow-slice-winners.md`

- Version/Build: `v0.1.7` benchmark support-doc relevance and bounded-slice
  hardening wave on 2026-04-02.

- Config/Flags: `odylith benchmark --repo-root . --profile proof`,
  `ODYLITH_REASONING_MODEL=gpt-5.4`,
  `ODYLITH_REASONING_CODEX_REASONING_EFFORT=medium`

- Customer Comms: Do not interpret generic guidance spillover in a proof prompt
  as Odylith memory strength. If the slice is install or closeout, the live
  prompt should look like install or closeout.

- Code References: `src/odylith/runtime/evaluation/odylith_benchmark_prompt_payloads.py`,
  `src/odylith/runtime/evaluation/odylith_benchmark_live_prompt.py`,
  `tests/unit/runtime/test_odylith_benchmark_prompt_payloads.py`,
  `tests/unit/runtime/test_odylith_benchmark_live_execution.py`

- Runbook References: `odylith/registry/source/components/benchmark/CURRENT_SPEC.md`,
  `odylith/maintainer/agents-guidelines/RELEASE_BENCHMARKS.md`

- Fix Commit/PR: Pending.
