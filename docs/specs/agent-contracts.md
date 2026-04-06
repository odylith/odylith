# Agent Contracts

Odylith publishes these additive stable contracts first:

- `AgentHostAdapter`
- `agent_route.v1`
- `agent_plan.v1`

They are intended to carry execution truth, not just summary text:

- who owns the work
- how execution should happen
- what validation is required
- what closeout surfaces must be touched
- why a route should stay local
- when Odylith should widen or fall back instead of pretending the slice is
  grounded

These contracts assume Odylith-first execution:

- ground through Odylith packets, surfaces, and orchestration before
  host-native repo search
- treat backlog/workstream, plan, Registry, Atlas, Casebook, Compass, and
  session upkeep as part of execution rather than as optional aftercare
- search existing workstream, active plan, bug, component, diagram, and recent
  session or Compass context first; extend, consolidate, or reopen existing
  truth before creating parallel records
- if the slice is genuinely new, create the missing workstream and bound plan;
  if it is umbrella-shaped, split with child workstreams or execution waves
- use Odylith skills and governed packets to deepen component specs,
  update/create Atlas coverage, capture or reopen Casebook bugs, and carry
  intent plus validation obligations across turns
- surface explicit ambiguity and widen or fallback reasons instead of silently
  broadening
- use host-native search as verification or fallback only when Odylith cannot
  bound the slice

These contracts live under `src/odylith/contracts/` and are versioned as part of the single public Odylith package.
