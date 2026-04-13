# Context Engine

The Context Engine answers one question:
**"what is true and relevant?"**

It sits between raw repository state and the rest of Odylith's delivery
machinery. It does not begin from a blind repo sweep. It narrows the evidence
cone to the smallest grounded slice the system can honestly trust before the
agent reasons, plans, edits, or delegates.

## Pipeline

1. **Take the strongest available anchor**  
   Start from the prompt, explicit paths, worktree state, known workstream
   ids, components, diagrams, or exact refs.

2. **Choose the smallest fitting packet lane**  
   Prefer narrow, explicit packets over broad scans. New or ambiguous work
   starts from session grounding; explicit paths go straight to `impact` or
   `architecture`.

3. **Assemble repo-local evidence**  
   Pull from the component registry, plans, workstreams, bugs, diagrams,
   session state, code or test structure, and other local truth sources.

4. **Score precision and ambiguity**  
   Mark whether the slice is explicit, inferred with confidence, ambiguous, or
   too weak to trust without widening.

5. **Shape a grounded context packet**  
   Produce a bounded packet that carries the active slice, supporting
   evidence, ambiguity level, validation hints, and routing handoff needed by
   downstream systems.

6. **Emit widen signals when coverage is weak**  
   If the packet cannot honestly bound the slice, emit signals such as
   `full_scan_recommended` instead of pretending the repo is fully covered.

7. **Hand off the retained execution bridge**  
   Preserve `routing_handoff`, packet quality, and narrowing guidance so
   orchestration and execution governance can act on the same grounded truth.

Common packet shapes include `bootstrap-session`, `impact`, `architecture`,
`governance-slice`, `session-brief`, `context`, and `query`.

## What It Does Not Do

- It does not decide whether an intended action is admissible. That is the
  execution engine.
- It does not diagnose why a blocker or ambiguous posture exists. That is
  Tribunal.
- It does not replace tracked markdown or JSON source-of-truth files. It is a
  local accelerator layered on top of them.
- It does not justify broad repo discovery when the slice is still ambiguous.
  In that case it should explicitly tell the caller to widen.

## Design Principle

The Context Engine is grounded and fail-closed by default. If it cannot bound
the slice truthfully, it should say so and force widening rather than return a
confident-looking packet built on weak evidence.

That same packet contract is host-general. Codex and Claude Code can consume
the same grounded context, while host-specific behavior stays outside the
shared retrieval and packet-shaping layer.
