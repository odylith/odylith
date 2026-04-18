# Odylith Agent Operating Character

Use this skill when adaptive Agent Operating Character, credit-safe hard laws,
learning-spine signals, or benchmark-proved pressure behavior need validation
or implementation.

## Default Flow
- Run `./.odylith/bin/odylith character status --repo-root .` to inspect the
  local hard-law, stance, benchmark, lane, and credit posture.
- Put a proposed move in a file and run
  `./.odylith/bin/odylith character check --repo-root . --intent-file <path>`
  before acting on ambiguous, risky, proof-sensitive, delegation-sensitive, or
  public-claim-sensitive work.
- Run `./.odylith/bin/odylith validate agent-operating-character --repo-root .`
  for deterministic proof. Add `--case-id <id>` for a focused case and `--json`
  for machine-readable proof.
- For benchmark proof, use the existing benchmark lane:
  `./.odylith/bin/odylith benchmark --profile quick --family agent_operating_character --no-write-report --json`.
- Keep Guidance Behavior as the first deterministic pressure-family lane under
  this layer: `./.odylith/bin/odylith validate guidance-behavior --repo-root .`
  and `./.odylith/bin/odylith benchmark --profile quick --family guidance_behavior`.

## Rules
- Character checks are local deterministic computation. They must not call
  Codex, Claude, provider APIs, subagents, full validation, benchmark execution,
  broad scans, or projection expansion on the hot path.
- Codex and Claude are first-class host families for the shared contract across
  dev, pinned dogfood, and consumer lanes. Host-specific surfaces may differ
  (`routed_spawn` for Codex, Task-tool subagents for Claude), but the hard-law,
  stance, budget, and benchmark decisions must stay byte-compatible in meaning.
- Host model names are adapter metadata, not Character decision engines. Passing
  a Codex or Claude model alias still resolves to the same local family
  contract and must not spend model credits.
- Modern host model aliases such as GPT/Codex variants and Claude/Sonnet/Opus
  variants must normalize to the shared Codex or Claude family contract; model
  names are never evidence that model credits may be spent.
- Hard laws stay deterministic: CLI-first governed truth, fresh proof for
  completion claims, visible-intervention proof, queue non-adoption, bounded
  delegation, benchmark proof for public claims, consumer-lane mutation guard,
  and explicit model-credit authorization.
- Hard-law recovery actions, recovery cues, visible-intervention eligibility,
  and block/defer decisions come from the shared Character contract. Do not
  recreate law lists in host guidance, Execution Engine glue, or intervention
  copy paths.
- Benchmark is a proof authority, not a word that blocks normal work. Learning
  from benchmark feedback is admissible local work; README, release-note,
  publish, shipped/proven, or public-claim pressure still requires benchmark
  proof before the claim can be made.
- Proof execution is not a public claim. Running release proof, validators, or
  benchmarks is admissible local work; writing or publishing the shipped/proven
  claim remains gated on benchmark proof.
- Treat negated unsafe moves as discipline, not as attempted violations. "Do
  not spawn subagents", "do not pick up queued work", and "zero host model
  calls" should stay admissible unless the intent also asks to perform the
  unsafe move.
- CLI-first applies to CLI-owned truth or explicit CLI-writer evidence.
  Allowed authored governance surfaces, such as a technical plan, should not be
  blocked without evidence that a CLI writer owns the requested mutation.
- Named postures are UX vocabulary and benchmark labels, not the runtime state
  machine. Runtime carries open-world pressure observations, stance facets,
  ranked affordances, uncertainty, budgets, and learning signals.
- For systemic integration, voice-template, learning-feedback, recurrence, or
  urgency pressure, prefer the ranked local affordance from `character check`
  instead of forcing a fixed posture script.
- Passing checks stay quiet. Visible nudges, Observations, Proposals, and
  fallbacks need concrete recovery value and visible proof.
- Character may emit evidence, proof needs, recovery affordances, and owner
  surfaces, but it does not script final voice. Intervention and Chatter keep
  the rendered words live, evidence-shaped, and non-mechanical.
- Durable learning requires deterministic validation, benchmark evidence, or
  Tribunal/governance promotion. Store compact practice signals, not raw
  transcripts, secrets, broad context, ephemeral temp paths, shell descriptors,
  or full corpus payloads.
- Public product claims require benchmark proof, and v0.1.11 shipped-runtime
  claims require pinned dogfood proof in addition to source-local proof.
