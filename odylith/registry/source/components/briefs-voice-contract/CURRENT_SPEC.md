# Briefs Voice Contract
Last updated: 2026-04-10


Last updated (UTC): 2026-04-10

## Purpose
Briefs Voice Contract is the governed narration contract for Compass standup
briefs and any future Odylith brief surface that needs factual, readable,
maintainer-friendly narration.

## Scope And Non-Goals
### Briefs Voice Contract owns
- The canonical Compass brief voice contract.
- The allowed brief source states: `provider`, exact `cache`, or explicit
  `unavailable`.
- The presentation rule that only real `provider` or exact `cache` briefs get
  the full standup-brief stage; non-ready states stay compact, truthful, and
  clearly labeled.
- Cache-epoch rotation when the brief contract changes.
- The writing rules that keep briefs simple, precise, friendly, human, and
  factual.
- The rejection rules for stock framing, workstream roll calls, stagey
  metaphor, and portable summary prose.
- The scenario guidance for quiet celebration, calm reassurance, slow windows,
  and risk callouts.
- The shared guidance and skill reminders that keep agents from drifting the
  contract back into templated narration.

### Briefs Voice Contract does not own
- Fact selection, ranking, or packet assembly. Compass runtime owns that.
- Queue-row, Tribunal, or systemic-brief contracts.
- Renderer layout or typography.
- Silent fallback narration. If there is no provider brief and no exact
  validated cache entry, Compass must say `unavailable`. Cross-scope borrowing
  is allowed only when Compass labels it explicitly as temporary global live
  coverage while the selected scoped brief warms.

## Developer Mental Model
- The brief should sound like a thoughtful maintainer talking to a teammate.
- Friendly, calm, direct, simple, precise, and factual beats polished.
- Short plain sentences come first.
- Show judgment: what changed, why it matters, what is next, and what could
  still break.
- Celebrate real wins with restraint.
- When things are shaky, be steady and reassuring without hiding the truth.
- Do not force workstream coverage into prose. Name only the lanes that help
  the reader understand the window.
- If a bullet could fit any repo, it is too generic.
- If the cited facts disappear and the bullet still sounds fine, it is too
  generic.
- One contract means one narration system. Provider writes the brief, exact
  cache may replay it, and Compass fails closed otherwise except for the
  explicitly disclosed scoped-warming case above.
- Global and scoped Compass narration should be authored together for one
  runtime packet. Scoped narration is part of the same narrated bundle as the
  matching global windows, not a second provider workflow.

## Runtime Contract
- Prompt owner:
  `src/odylith/runtime/surfaces/compass_standup_brief_narrator.py`
- Voice validator:
  `src/odylith/runtime/surfaces/compass_standup_brief_voice_validation.py`
- Primary consumer:
  [Compass](../compass/CURRENT_SPEC.md)

### Brief source states
- `provider`
  Fresh AI-authored brief validated against the current fact packet.
- `cache`
  Exact-fingerprint replay of a previously validated brief for the same fact
  packet.
- `unavailable`
  Explicit fail-closed state when neither of the above exists.
- One packet change should trigger one narrated bundle request in the normal
  path, with one repair pass max. Independent scope-by-scope provider fanout
  is out of contract.

## Guardrails
- No deterministic or templated fallback narrator.
- No stock wrappers such as `Most of the work here was in`,
  `X and Y are still moving together`, `X is there because`,
  `The next move is`, or repeated `Over the last 48 hours` leads.
- No stagey metaphor or dashboard-wise abstractions such as `pressure point`,
  `center of gravity`, `muddy`, or `slippery`.
- No even polished summary-card rhythm across the whole brief.
- No raw fact ids in prose.
- No cache carry-forward across non-exact fingerprints.
- No full-brief visual treatment for non-ready states. Warming, failed,
  budget-limited, or unavailable states must not masquerade as a finished
  narrated brief.
- Voice-contract changes must rotate the cache/schema epoch and invalidate
  stale runtime-snapshot prose.
- Whole-window coverage facts are evidence, not a mandatory bullet.

## Scenario Handling
- Meaningful landing:
  Quiet celebration is welcome when something real closed or got firmer.
- Shaky but improving:
  Briefs may offer a calm anchor such as `Small but real reassurance`, but only
  when a concrete reassuring fact exists.
- Slow window:
  Say little moved. Do not fake momentum.
- Rising risk:
  Name the seam to watch and the human consequence if it drifts.

## What To Change Together
- Prompt, validator, cache epoch, and tests when the brief contract changes.
- Compass spec, product-surface guidance, and skills when the brief source
  states change.
- Cache and runtime-snapshot reuse rules when any narration path changes.

## Validation Playbook
- `PYTHONPATH=src pytest tests/unit/runtime/test_compass_standup_brief_narrator.py -q`
- `PYTHONPATH=src pytest tests/unit/runtime/test_render_compass_dashboard.py tests/unit/runtime/test_compass_dashboard_shell.py tests/unit/runtime/test_compass_refresh_contract.py -q`
- `PYTHONPATH=src pytest tests/integration/runtime/test_surface_browser_deep.py -k 'compass and brief' -q`

## Requirements Trace
This section captures synchronized requirement and contract signals derived from component-linked timeline evidence.

<!-- registry-requirements:start -->
- No synchronized requirement or contract signals yet.
<!-- registry-requirements:end -->
## Feature History
- 2026-04-10: Promoted the Compass brief voice, exact-cache replay rule, and explicit unavailable state into one governed component, removed deterministic fallback narration from the Compass brief runtime, and invalidated stale cache epochs so old stock prose cannot survive a contract change. (Plan: [B-025](../../../odylith/radar/radar.html?view=plan&workstream=B-025))
- 2026-04-10: Collapsed global and verified-scoped Compass warming into one packet-level narrated bundle so scope views keep live narration without reopening a second scoped provider queue. (Plan: [B-025](../../../odylith/radar/radar.html?view=plan&workstream=B-025))
- 2026-04-10: Tightened the presentation contract so only ready live briefs keep the full standup card. Non-ready states now stay compact, truthful, retry-aware, and copy-safe instead of impersonating a finished brief. (Plan: [B-025](../../../odylith/radar/radar.html?view=plan&workstream=B-025))
