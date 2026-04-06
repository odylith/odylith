# Odylith Subagent Operations

Use this guide for Odylith routing and orchestration behavior in the current repo.

## Primary Rules

- Ground the slice first with Odylith packets or direct source reads before delegating.
- Treat `local_only`, `single_leaf`, `serial_batch`, and `parallel_batch` as binding control signals.
- Carry the retained `routing_handoff` forward unchanged instead of paraphrasing it into a new ad hoc contract.
- Every native spawn must set explicit `model` and `reasoning_effort`.

## Related Guidance

- `odylith/agents-guidelines/SUBAGENT_ROUTING_AND_ORCHESTRATION.md`
- `odylith/agents-guidelines/GROUNDING_AND_NARROWING.md`
- `odylith/skills/subagent-router/SKILL.md`
- `odylith/skills/subagent-orchestrator/SKILL.md`
