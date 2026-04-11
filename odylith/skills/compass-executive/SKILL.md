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
- Cheap also means selective. Reuse the last validated live brief only when the exact packet fingerprint is unchanged, rebuild local runtime only when repo truth actually moved, and leave fresh narration to the background warmer.
- Scoped selection does not buy a foreground provider exception. If a scoped brief is still warming, show the governed global live brief with a clear notice when one exists; otherwise stay explicitly unavailable.
- Prefer Compass for recent activity and current execution posture, not as a replacement for direct bug/plan/workstream inspection.
