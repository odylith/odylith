# Odylith Guidance Behavior

Use this skill when guidance behavior pressure cases, high-risk agent
instructions, or cross-host guidance contracts need deterministic validation.
Guidance Behavior is the first deterministic pressure-family proof lane under
Odylith Discipline; it proves concrete hard-law families while
the broader Odylith Discipline layer handles open-world stance, credit budgets, learning
signals, and benchmark sovereignty.

## Default Flow
- Run `./.odylith/bin/odylith validate guidance-behavior --repo-root .`.
- Add `--case-id <id>` when the task names one pressure case or a packet
  already carried a case-scoped validation command.
- Add `--json` when the result will feed another tool, a report, or a
  benchmark fixture.
- For benchmark proof, run
  `./.odylith/bin/odylith benchmark --profile quick --family guidance_behavior`
  unless the task explicitly asks for a slower profile or live model proof.
- Treat a passing compact `guidance_behavior_summary` as evidence that the
  proof path is available, not as fresh proof that validation already ran.
- Treat low latency as part of the proof. The Guidance Behavior hot path
  should carry the compact summary and validator command without session/full
  scan widening, projection-store opens, delivery-ledger reads, provider
  calls, or host capability probes unless the packet is route-ready and can
  actually use that host capability.
- Treat bundle parity as part of cross-lane proof. The validator must catch
  stale live/source-bundle mirrors for guidance docs, skills, host shims,
  governed program/spec truth, and benchmark corpora before consumer or
  dogfood lanes can claim the guidance behavior contract is green.

## Rules
- Keep the full validator explicit and out of the live hot path.
- Do not import code, prose, assets, naming, or examples from external
  reference repositories into the corpus, guidance, or tests.
- Keep Codex and Claude behavior aligned: grounding before broad scans,
  CLI-first governed truth, queue non-adoption, fresh proof for completion
  claims, bounded delegation, and visible-intervention proof mean the same
  thing on both hosts.
- Keep lane posture explicit:
  - consumer lane uses the installed managed runtime and diagnosis-first
    Odylith product-fix posture
  - pinned dogfood proves the shipped runtime in the product repo
  - detached `source-local` is maintainer-only proof for unreleased
    `src/odylith/*` changes
