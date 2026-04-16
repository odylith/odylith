# Briefs Voice Contract
Last updated: 2026-04-12


Last updated (UTC): 2026-04-12

## Purpose
Briefs Voice Contract is the governed narration contract for Compass standup
briefs and any future Odylith brief surface that needs factual, readable,
maintainer-friendly narration.

## Scope And Non-Goals
### Briefs Voice Contract owns
- The canonical Compass brief voice contract.
- The allowed brief source states: `provider`, exact `cache`, or explicit
  `unavailable`.
- The rule `LLM writes, local code thinks`.
- The provider-facing narration substrate contract: deterministic winner-fact
  selection, hard budgets, exact substrate fingerprinting, and prior-brief
  delta inputs.
- The one-bundle narration contract: global and verified scoped briefs for one
  runtime packet warm together, not through separate scope jobs.
- The provider-worthiness gate that decides whether a new provider pass is
  justified.
- The partial-salvage and subset-repair rules for bundle responses.
- The provider retry and diagnostics contract for narration attempts.
- The presentation rule that non-ready states must stay truthful, explicitly
  labeled, and must not impersonate a ready narrated brief for the selected
  scope or packet.
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
- The upstream evidence packet builders. Compass runtime owns those.
- The exact local ranking implementation details beyond the governed budgets,
  winner semantics, and reuse contract.
- Queue-row, Tribunal, or systemic-brief contracts.
- Renderer layout or typography.
- Silent fallback narration. If there is no provider brief and no exact
  validated cache entry, Compass must say `unavailable`. Cross-scope borrowing
  is allowed only when Compass labels it explicitly as temporary global live
  coverage while the selected scoped brief warms.

## Developer Mental Model
- The brief should sound like a thoughtful maintainer talking to a teammate.
- LLM writes. Local code thinks.
- Local code chooses and compresses the facts before the provider ever sees
  them.
- The provider should spend tokens on prose and judgment, not on re-reading a
  giant raw packet.
- Background brief warming must detect the active local host and stay on the
  bounded local ladder with `medium` reasoning only.
- Codex ladder for standup briefs:
  `gpt-5.3-codex-spark` -> `gpt-5.3-codex` -> `gpt-5.4-mini`.
- Claude ladder for standup briefs:
  `haiku` -> `sonnet`.
- Advance one rung only after a provider budget, rate-limit, or model-availability
  failure. Do not keep retrying the same exhausted cheap rung indefinitely.
- Friendly, calm, direct, simple, precise, and factual beats polished.
- Short plain sentences come first.
- Keep the prose free-flowing and human. Deterministic rules belong in
  evidence eligibility, cache identity, and rejection of known drift modes,
  not in sentence templates.
- Show judgment: what changed, why it matters, what is next, and what could
  still break.
- Celebrate real wins with restraint.
- When things are shaky, be steady and reassuring without hiding the truth.
- `Completed in this window` should speak only from concrete completed
  movement in the selected slice and window.
- `Current execution` should usually stay on one active lane and one concrete
  action, not widen into portfolio summary.
- `Next planned` should usually name the immediate next move from that same
  lane, not jump to a distant forcing-function backlog item.
- `Risks to watch` should name explicit blockers, freshness seams, or proof
  gaps instead of abstract execution commentary.
- If the evidence packet is thin, the brief should get shorter rather than
  broader.
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
- Exact cache identity now means exact `narration substrate` identity, not
  exact raw-packet identity. Non-winner packet churn must not force a cold
  miss.

## Runtime Contract
- Prompt owner:
  `src/odylith/runtime/surfaces/compass_standup_brief_narrator.py`
- Narration substrate owner:
  `src/odylith/runtime/surfaces/compass_standup_brief_substrate.py`
- Bundle orchestrator:
  `src/odylith/runtime/surfaces/compass_standup_brief_batch.py`
- Maintenance + retry owner:
  `src/odylith/runtime/surfaces/compass_standup_brief_maintenance.py`
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

### Narration substrate
- Every narrated entry is built from a deterministic local substrate, not the
  full fact packet.
- The substrate contains only:
  - top-ranked section winners
  - hard section and total budgets
  - compact storyline/self-host summary fields needed for prose
  - previous accepted brief snapshot for delta narration
  - stable evidence ids and stable fact keys
- Default budgets:
  - global window: top `8-12` facts total
  - scoped brief: top `3-4` facts total
- Exact cache replay keys off the substrate fingerprint, not unrelated packet
  noise.

### Delta narration
- Provider requests should update the prior accepted brief from deterministic
  deltas rather than regenerate from a raw packet every time.
- Each entry computes:
  - current substrate fingerprint
  - previous accepted substrate fingerprint
  - changed winner facts
  - dropped winner facts
  - unchanged kept facts
  - changed sections/storyline fields
- If the current substrate exactly matches a cached accepted brief, replay that
  cache directly.
- If the substrate changed but the winner story did not, skip provider
  generation and record that skip explicitly.
- If a fresh provider pass is needed, send one bundle request for the whole
  packet and allow one subset repair pass max.
- Partial salvage is mandatory. A malformed scoped entry must not poison valid
  sibling entries from the same bundle response.

### Provider-worthiness gate
- Do not call the provider when:
  - the substrate fingerprint matches exactly
  - only freshness wording or timestamp drift changed
  - only non-winner summary/count churn changed
  - the winning narrative facts did not materially move
- Call the provider when:
  - a winner fact was added, removed, or materially changed
  - a section winner changed enough to alter narration
  - a storyline consequence changed materially

### Provider diagnostics
- The brief runtime must not write a separate narration attempt recorder.
- Skip decisions stay on the explicit `unavailable` brief result for the
  affected entry.
- Provider failures stay in the maintained brief state as bounded diagnostics.
  Capacity, budget, and provider failures go to the slow retry lane;
  `invalid_batch` stays subset-only.

## Guardrails
- No deterministic or templated fallback narrator.
- No stock wrappers such as `Most of the work here was in`,
  `X and Y are still moving together`, `X is there because`,
  `The next move is`, or repeated `Over the last 48 hours` leads.
- No manager-speak or strategy-memo abstractions such as `forcing function`,
  `execution coherence`, `room to tighten`, `current immediate track`, or
  similar phrases that narrate posture instead of the actual work.
- No stagey metaphor or dashboard-wise abstractions such as `pressure point`,
  `center of gravity`, `muddy`, or `slippery`.
- No portfolio drift inside section bullets that are meant to orient the
  reader on one live lane.
- No even polished summary-card rhythm across the whole brief.
- No raw fact ids in prose.
- No raw-packet prompting on the normal provider path. Provider-facing payloads
  must consume the governed narration substrate.
- No cache carry-forward across non-exact fingerprints.
- No fuzzy truth matching or semantic cache replay across non-exact packets.
- Non-ready states must not masquerade as a finished narrated brief.
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
- Substrate builder, prompt, validator, cache epoch, diagnostics expectations,
  and tests when the brief contract changes.
- Compass spec, product-surface guidance, and skills when the brief source
  states change.
- Cache and runtime-snapshot reuse rules when any narration path changes.

## Validation Playbook
- `PYTHONPATH=src pytest tests/unit/runtime/test_compass_standup_brief_substrate.py -q`
- `PYTHONPATH=src pytest tests/unit/runtime/test_compass_standup_brief_batch.py tests/unit/runtime/test_compass_standup_brief_maintenance.py tests/unit/runtime/test_compass_standup_brief_narrator.py -q`
- `PYTHONPATH=src pytest tests/unit/runtime/test_compass_standup_brief_narrator.py -q`
- `PYTHONPATH=src pytest tests/unit/runtime/test_render_compass_dashboard.py tests/unit/runtime/test_compass_dashboard_shell.py tests/unit/runtime/test_compass_refresh_contract.py -q`
- `PYTHONPATH=src pytest tests/integration/runtime/test_surface_browser_deep.py -k 'compass and brief' -q`

## Requirements Trace
This section captures synchronized requirement and contract signals derived from component-linked timeline evidence.

<!-- registry-requirements:start -->
- No synchronized requirement or contract signals yet.
<!-- registry-requirements:end -->
## Feature History
- 2026-04-12: Tightened the governed brief voice again around founder feedback: deterministic rules now explicitly stop at evidence eligibility and drift rejection, while the prose itself stays free-flowing, one-lane, immediate, and human. `Current execution` now prefers one active lane plus one concrete action, `Next planned` now stays on the immediate next move, `Risks to watch` now names explicit seams instead of abstract coherence language, and thin packets are required to produce shorter briefs instead of broader summary prose. (Plan: [B-025](../../../odylith/radar/radar.html?view=plan&workstream=B-025))
- 2026-04-10: Re-architected Compass brief generation around deterministic narration substrates, exact substrate-fingerprint cache identity, delta bundle narration, provider-worthiness gating, partial salvage, provider diagnostics, and daemon-backed hot refresh reuse. (Plan: [B-025](../../../odylith/radar/radar.html?view=plan&workstream=B-025))
- 2026-04-10: Promoted the Compass brief voice, exact-cache replay rule, and explicit unavailable state into one governed component, removed deterministic fallback narration from the Compass brief runtime, and invalidated stale cache epochs so old stock prose cannot survive a contract change. (Plan: [B-025](../../../odylith/radar/radar.html?view=plan&workstream=B-025))
- 2026-04-10: Collapsed global and verified-scoped Compass warming into one packet-level narrated bundle so scope views keep live narration without reopening a second scoped provider queue. (Plan: [B-025](../../../odylith/radar/radar.html?view=plan&workstream=B-025))
