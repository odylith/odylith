# Odylith Discipline

Use this skill when Odylith Discipline behavior, credit-safe hard laws,
learning-spine signals, or benchmark-proved pressure behavior need validation
or implementation.

## Default Flow
- Run `./.odylith/bin/odylith discipline status --repo-root .` for the
  human-readable local readiness and credit posture.
- Put a proposed move in a file and run
  `./.odylith/bin/odylith discipline check --repo-root . --intent-file <path>`
  for a human-readable local admissibility summary before acting on ambiguous,
  risky, proof-sensitive, delegation-sensitive, or public-claim-sensitive work.
- Run `./.odylith/bin/odylith validate discipline --repo-root .`
  for deterministic proof. Add `--case-id <id>` for a focused case and `--json`
  for machine-readable proof.
- For benchmark proof, use the existing benchmark lane:
  `./.odylith/bin/odylith benchmark --profile quick --family discipline --no-write-report --json`.
- Keep Guidance Behavior as the first deterministic pressure-family lane under
  this layer: `./.odylith/bin/odylith validate guidance-behavior --repo-root .`
  and `./.odylith/bin/odylith benchmark --profile quick --family guidance_behavior`.

## Rules
- Discipline checks are local deterministic computation. They must not call
  Codex, Claude, provider APIs, subagents, full validation, benchmark execution,
  broad scans, or projection expansion on the hot path.
- Codex and Claude are first-class host families for the shared contract across
  dev, dev-maintainer/source-local, pinned dogfood, and consumer lanes.
- Hard laws stay deterministic: CLI-first governed truth, fresh proof for
  completion claims, visible-intervention proof, queue non-adoption, bounded
  delegation, benchmark proof for public claims, consumer-lane mutation guard,
  and explicit model-credit authorization.
- Passing checks stay quiet. Visible nudges, Observations, Proposals, and
  fallbacks need concrete recovery value and visible proof.
- Odylith Discipline may emit evidence, proof needs, recovery affordances, and
  owner surfaces, but it does not script final voice. Intervention and Chatter
  keep the rendered words live, evidence-shaped, and non-mechanical.
- Durable learning requires deterministic validation, benchmark evidence, or
  Tribunal/governance promotion. Store compact practice signals, not raw
  transcripts, secrets, broad context, ephemeral temp paths, shell descriptors,
  or full corpus payloads.
- Do not expose internal acronyms or planning shorthand in user-facing output.
  Default chat summaries should contain only the decision, practical reason,
  nearest safe move, proof need, and whether the hot path stayed local.
- Keep raw labels such as `hard_law_results`, `pressure_features`,
  `retention_class`, `raw_transcript_retained`, and counter names out of
  user-facing output unless the user explicitly asks for JSON verification
  details.
