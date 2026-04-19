# Odylith Maintainer AGENTS

Scope: applies to maintainer-only paths under `odylith/maintainer/`.

## Purpose
- Keep Odylith product-maintainer release guidance, release skills, and release
  benchmark publishing rules separate from shared consumer-safe guidance.
- Keep end-to-end Odylith release process out of bundled consumer
  `agents-guidelines/` and `skills/`.

## Working Rule
- Use this subtree only in the Odylith product repo.
- Do not mirror files from this subtree into bundled consumer assets.
- Keep the product-repo lanes explicit:
  - pinned dogfood is the default proof posture for the shipped runtime
  - detached `source-local` is the explicit maintainer-only live-source
    execution posture
- Maintainer-only coding standards live in
  `agents-guidelines/CODING_STANDARDS.md`; treat that file as the single
  source for maintainer-side coding, testing, generated-artifact authoring,
  branch and write safety, refactor-first policy, release-surface source
  updates, benchmark harness changes, and coding validation expectations.
- Treat AI slop as a regression. In this product lane, use
  `../agents-guidelines/ANTI_SLOP_AND_DECOMPOSITION.md` together with
  `agents-guidelines/CODING_STANDARDS.md` to keep fake modularization,
  duplicate micro-helpers, mirrored host drift, and filler comments out of
  shipped code.
- For explicit deep anti-slop or decomposition passes in maintainer mode, use
  `skills/fail-closed-code-hygiene/` so the pass fails closed on remaining
  shims, duplicate helper clones, mirror drift, and missing proof.
- In detached `source-local` maintainer dev posture, touching a red-zone file
  (`2000+` LOC), a `1200+` LOC file that still grows, a host-mirror pair, or a
  known duplicate-helper cluster must be treated as an anti-slop pass, not as
  routine feature work. Use `skills/fail-closed-code-hygiene/`, extract a real
  owner, add enforcement tests, and rerun the full required proof surface
  before closeout.
- Treat touched `500+` or `900+` LOC giant functions the same way in detached
  `source-local` maintainer dev posture: do not keep phase-mixed render,
  payload, router, or score logic growing in place when the slice can take a
  same-change owner extraction. Do not hide the problem behind an alias wall;
  move it toward data prep, view model, and template/render owners or another
  equally real phase seam.
- Queued Radar items, case queues, and shell or Compass queue previews are not
  automatic implementation picks in the maintainer lane. Unless the user
  explicitly asks to work a queued item, do not start implementing it just
  because it is visible in a backlog or Odylith queue surface.
- Local maintainer release identity is also non-negotiable in this lane:
  authored maintainer work uses `freedom-research
  <freedom@freedompreetham.org>` for both author and committer config. If
  canonical release-history proof needs to survive platform merge machinery,
  keep the history gate focused on canonical maintainer authorship instead of
  widening local identity policy.
- Keep maintainer and dogfood progress updates task-first. Do not narrate
  startup, routing, packet-selection, or degraded-attempt history unless a
  literal command, a live blocker, or a runtime-lane distinction matters.
- Keep Odylith ambient by default during work. If a routing or governance fact
  materially changes the next move, weave it into the update first and reserve
  explicit `Odylith Insight:`, `Odylith History:`, or `Odylith Risks:` labels
  for rare high-signal moments.
- Treat live teaser, `**Odylith Observation**`, and `Odylith Proposal` as the
  intervention-engine fast path. Treat `Odylith Assist:` as the chatter-owned
  closeout so maintainer hooks do not drift into one slow, tangled narration
  stack.
- The `**Odylith Observation**` and `**Odylith Proposal**` experience is a
  maintainer-owned brand contract, not optional polish. Any maintainer change
  touching the intervention engine, Chatter, Compass, or host hooks must
  preserve the shipped labels, the one-confirmation proposal flow, and the
  human-feeling markdown UX across detached `source-local`, pinned dogfood,
  and the downstream consumer lane.
- Preserve the shipped shape as well as the words: Observation should look
  like `Odylith Assist`, which means one short labeled line. Proposal should
  be a short ruled block with the heading, a couple of lines, a few bullets,
  and the confirmation line.
- Maintain one stable intervention identity across teaser, Observation, and
  Proposal for the same session-local moment. Later hooks may add evidence or
  surface the first eligible Proposal, but they must not make the same moment
  feel like a fresh branded interruption.
- For Codex and Claude checkpoint hooks, keep the full Observation,
  Proposal, and Assist bundle in hidden developer context for continuity, but
  surface the earned Observation/Proposal beat visibly at the hook moment when
  the host renders hook output. If the host keeps hook output hidden, render
  the assistant-visible fallback Markdown in chat instead of claiming the
  engine is active. Stop is the fallback closeout lane, not the primary
  intervention moment.
- Hook `systemMessage` or `additionalContext` generation is not proof of
  chat-visible UX. The user-visible contract is satisfied only by rendered
  chat text or by a host channel that is proven visible in the active session.
  When in doubt, run `odylith codex visible-intervention` or `odylith claude
  visible-intervention` and show that Markdown directly.
- Make the interjection obvious immediately. Observation should tell the user
  why Odylith is stepping in without making them parse a card full of
  sections, and Proposal copy should sound like a crisp human recommendation
  rather than branded filler.
- Preserve the multiline markdown structure of Observation and Proposal blocks
  end to end. If a maintainer change flattens those sections into single-line
  summaries anywhere in the host or Compass path, treat that as a shipped UX
  regression and fix it before closeout.
- When maintainers show these surfaces to humans in docs, demos, reviews, or
  discussion, render them as Markdown or describe them in prose. Do not
  present them as fenced raw Markdown unless the task is specifically about
  debugging raw markdown text.
- Treat filler demo copy as a regression too. Mockups, screenshots, and sample
  payloads should use concrete governed meaning, not placeholder flourish.
- Treat templated or mechanical intervention copy as a product regression even
  when the facts are technically correct. The default shipped voice must stay
  friendly, delightful, soulful, insightful, simple, clear, accurate,
  precise, and above all human until a later release lands explicit
  voice-pack selection.
- Preview-only proposals remain unappliable until every action in the bundle
  has a safe CLI-backed apply lane. Maintainer changes must not reintroduce
  partial bundle apply just because one surface already has a helper.
- Preserve prompt memory across the full intervention lifecycle. Stop hooks,
  post-edit checkpoints, post-bash checkpoints, apply, and decline events must
  carry or recover the original prompt excerpt so later Odylith reasoning does
  not collapse into self-referential proposal summaries.
- At closeout, you may add at most one short `Odylith Assist:` line if it
  helps summarize what Odylith materially contributed. Prefer
  `**Odylith Assist:**` when Markdown formatting is available; otherwise use
  `Odylith Assist:`. Lead with the user win, link updated governance IDs inline
  when they were actually changed, and when no governed file moved, name the
  affected governance-contract IDs from bounded request or packet truth without
  calling them updated. Frame the edge against `odylith_off` or the broader
  unguided path when the evidence supports it. Keep it crisp, authentic, clear,
  simple, insightful, soulful, friendly, free-flowing, human, and factual. Use
  only concrete observed counts, measured deltas, or validation outcomes; if
  the evidence is thin or the user-facing delta is not clear, omit it.
- Treat Odylith-routed native delegation as the default execution path for
  substantive grounded maintainer work in both maintainer postures when the
  current host supports it. Codex is the currently validated native-spawn
  host; pinned dogfood and detached `source-local` maintainer dev still keep
  the slice local when Odylith says so or when another host has not yet
  proven native spawn.
- If a maintainer explicitly waives benchmark proof for one exact release
  version, stop any in-flight proof run, record the override in
  `odylith/runtime/source/release-maintainer-overrides.v1.json`, bind the
  blocker into Casebook plus the active workstream/plan and the impacted
  Registry specs, and describe that release as benchmark-advisory rather than
  benchmark-proved.
- Never game the eval.
- Never accept a benchmark improvement that gets faster or cheaper by becoming
  less accurate, less precise, or less recall-grounded.
- In benchmark publication and review framing, `odylith_off` means
  `raw_agent_baseline`; the repo-scan lane is a separate scaffold control.
- Treat benchmark softening, scenario cherry-picking, validator weakening,
  stale-report publication, or README claim inflation as a product failure, not
  as acceptable release polish.

## Routing
- Shared anti-slop and decomposition policy: `../agents-guidelines/ANTI_SLOP_AND_DECOMPOSITION.md`
- Maintainer coding standards: `agents-guidelines/CODING_STANDARDS.md`
- Release benchmark publishing: `agents-guidelines/RELEASE_BENCHMARKS.md`
- Canonical release order: `../MAINTAINER_RELEASE_RUNBOOK.md`

## Skills
- `../skills/odylith-code-hygiene-guard/`
- `skills/fail-closed-code-hygiene/`
- `skills/release-benchmark-publishing/`
