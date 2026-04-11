# compass-executive

Use when you need Compass-driven executive or operator summaries over recent work, current execution, and next actions.

## Canonical Commands

```bash
odylith compass log --repo-root . --kind decision --summary "<decision>"
odylith compass log --repo-root . --kind implementation --summary "<implementation update>"
odylith compass update --repo-root . --statement "<current execution state>"
odylith compass refresh --repo-root . --wait
odylith sync --repo-root . --force
```

## Rules

- Follow the canonical brief contract in [Briefs Voice Contract](../registry/source/components/briefs-voice-contract/CURRENT_SPEC.md).
- Keep Compass narrative concise, execution-meaningful, grounded in local repo truth, and in friendly grounded maintainer narration.
- `LLM writes, local code thinks` is the brief-generation rule. Build the
  winning local story first; do not ask the provider to rediscover it from a
  raw packet.
- Sound like a thoughtful maintainer talking to a teammate: calm, direct, simple, factual, precise, and human.
- Celebrate real wins with restraint. When things are shaky, offer calm reassurance only when a concrete reassuring fact exists.
- Stock framing is forbidden. Do not use repeated house phrases, queue-label restatement, repeated window leads, workstream roll calls, generic priority wrappers, or canned `next/current/why/timing` scaffolding.
- Stagey metaphor is forbidden too. Do not write `pressure point`, `center of gravity`, `muddy`, `slippery`, `top lane`, or other dashboard-wise phrases that sound vivid but explain nothing.
- Stock lines like `Most of the work here was in ...`, `X and Y are still moving together`, and `X is there because ...` are forbidden too.
- Bullet labels like `Executive/Product` and `Operator/Technical` are forbidden. Compass briefs are unlabeled narrative bullets now; do not reintroduce a voice split in cached prose, copied summaries, or compatibility rewrites.
- Every bullet must stay tethered to the cited fact language. If it still reads clean after the facts are stripped away, it is too generic for Compass.
- Apply that bar to provider output, exact-cache replay, and any manual Compass-facing summary you write.
- If a Compass summary sounds templated, rhythmic, or dashboard-polished, treat that as a product regression in governed truth or narrator policy, not as a copy-polish pass.
- Keep the normal refresh path cheap. Timeline material should be reused from deterministic Compass state, and the blocking path must stay exact-cache or truthful explicit state only.
- Cheap also means selective. Reuse the last validated live brief only when the exact narration-substrate fingerprint is unchanged, rebuild local runtime only when repo truth actually moved, and leave fresh narration to the background warmer.
- Background brief warming must detect the active local host, stay on `medium` reasoning, and use the governed ladder: Codex = `gpt-5.3-codex-spark` -> `gpt-5.3-codex` -> `gpt-5.4-mini`; Claude = `haiku` -> `sonnet`.
- Advance one rung only after a provider budget, rate-limit, or model-availability failure. Do not keep retrying the same exhausted cheap rung indefinitely.
- Provider payloads should be compact delta substrates:
  - top winner facts
  - compact storyline/self-host summary
  - prior accepted brief snapshot
  - changed and dropped winner facts
- If the winner story did not change, skip provider generation explicitly and
  record the skip instead of retrying or falling back to fake narration.
- Scoped selection does not buy a foreground provider exception. If a scoped brief is still warming, show the governed global live brief with a clear notice when one exists; otherwise stay explicitly unavailable.
- Prefer Compass for recent activity and current execution posture, not as a replacement for direct bug/plan/workstream inspection.
