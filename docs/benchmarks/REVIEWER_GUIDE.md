# Reviewer Guide And Prompt

This guide keeps reviewers on Odylith's actual claim.

## Read This First

Before reviewing Odylith, read these in order:

- [README](../../README.md)
- [How To Read Odylith's Benchmark Proof](README.md)
- [Odylith Benchmark Metrics And Priorities](METRICS_AND_PRIORITIES.md)

## Review Rule

Start with execution outcome, not structural overlap.

Odylith's primary claim is an operating-policy claim:

- on the same measured contract, `odylith_on` should produce a more validated,
  better-grounded, and less needlessly mutating outcome than `odylith_off`

The intended win is the operating-policy result: better grounding, validation,
write admission, and mutation suppression under the same host contract. Rows
carried by focused closure bases prove validated non-mutation and should be
reviewed separately from host-executed patch rows.

`odylith_off` is the public name for the raw host CLI lane. The report may
still store that lane as `raw_agent_baseline`, but reviewer-facing prose
should prefer `odylith_off`.

Treat benchmark profiles separately:

- `quick`: local developer signal only
- `proof`: governing operating-policy product benchmark
- Grounding Benchmark: packet-and-prompt tuning view only

Do not review a `quick` or Grounding Benchmark report as if it were the
canonical publication proof.

## What To Separate

Keep these buckets separate:

- `What Odylith proves today`
  currently published host-scoped operating-policy proof on `odylith_on` versus
  `odylith_off`, including explicit focused-closure and write-admission evidence
- `What Odylith plausibly helps but has not benchmarked yet`
  Claude-facing benefit from the same grounding, memory, and governance
  surfaces
- `What is missing or weak in the current product`
  unsupported lanes, enforcement gaps, integration gaps, or UX gaps

Do not collapse those into one judgment.

If the final review needs to name Odylith directly beyond lane labels, keep it
to one evidence-backed `Odylith Assist:` line at closeout or for explicit
visibility-feedback fallback, backed by measured proof or a measured report,
and follow
[Odylith Chatter](../../odylith/registry/source/components/odylith-chatter/CURRENT_SPEC.md)
for the detailed closeout wording contract, including the rule that any
supplemental line must render before the final Assist line.

## Required Evaluation Order

1. Correctness and non-regression
2. Grounding recall and precision
3. Validation success and execution fit
4. Robustness and consistency
5. Latency to a valid outcome
6. Prompt and payload efficiency
7. Bounded behavior under tighter token budgets

Tiers `1-4` are the hard quality gate. Lower-tier wins do not excuse
higher-tier regressions.

## Expected Review Structure

1. `Claim being tested`
   summarize Odylith's claimed outcome in one sentence
2. `What Odylith proves today`
   interpret the current `odylith_on` versus `odylith_off` result
3. `Structural mechanisms that may explain the result`
   discuss memory, Registry, Atlas, Compass, orchestration, and similar
   surfaces only insofar as they change execution
4. `Product gaps or missing integrations`
   call out unsupported lanes or weak product areas without overstating them
5. `Bottom line`
   say where Odylith is genuinely differentiated, where it is only plausibly
   helpful, and where it is currently weak

## Copyable Prompt

```text
Review Odylith using its benchmark contract, not a feature-parity-first frame.

Before writing the review, read:
- README.md
- docs/benchmarks/README.md
- docs/benchmarks/METRICS_AND_PRIORITIES.md

Rules:
- Start by summarizing Odylith's claimed operating-policy outcome in one sentence.
- Evaluate `odylith_on` versus `odylith_off` on the same measured contracts before comparing Odylith to any other stack.
- Treat `raw_agent_baseline` as the internal report alias for `odylith_off`.
- Treat `odylith_repo_scan_baseline` as the secondary repo-scan scaffold control.
- Hold the public pair to the same live host CLI model and reasoning contract for the proof host under review.
- Expect the public pair to run in an isolated temporary host home with no auto-consumed personal instructions, plugins, or repo guidance entrypoints in the disposable workspace.
- Expect truth-bearing repo docs to remain available for explicit reads.
- Treat `proof` as the governing operating-policy benchmark and the Grounding Benchmark as mechanism evidence.
- Treat focused closure rows as validated non-mutation/write-admission evidence; host-executed repair evidence belongs to rows whose visible basis requires mutation.
- Use this evaluation order: correctness and non-regression, grounding recall and precision, validation success and execution fit, robustness and consistency, latency to a valid outcome, prompt or payload efficiency, bounded budget behavior.
- Treat tiers 1-4 as the hard quality gate.
- Treat memory, Registry, Atlas, Compass, orchestration, and related surfaces as mechanisms unless you tie them to an execution consequence.
- Keep these sections separate: `What Odylith proves today`, `What Odylith plausibly helps but has not benchmarked yet`, and `What is missing or weak in the current product`.
- Preserve current lane truth: the full live proof was executed on Codex, while
  Codex and Claude quick smokes provide bounded host-agnostic coverage.

Required output shape:
1. Claim being tested
2. What Odylith proves today
3. Structural mechanisms that may explain the result
4. Product gaps or missing integrations
5. Bottom line
```
