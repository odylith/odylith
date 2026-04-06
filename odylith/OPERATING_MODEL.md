# Operating Model

Odylith changes how a coding agent starts, stays grounded, and closes work.
Tracked files under `odylith/` hold guidance and repo-local governance truth.
Mutable runtime state lives under `.odylith/`.

The default posture is Odylith-first:

- start with Odylith grounding before broad repo search
- recover existing workstream, plan, bug, component, diagram, and recent
  session or Compass truth before creating new records
- keep runtime, write, and validation boundaries separate

Those boundaries mean:

- runtime boundary: which interpreter runs Odylith itself
- write boundary: which repo files the agent may edit
- validation boundary: which toolchain proves the target repo still works

In consumer repos, `./.odylith/bin/odylith` runs on Odylith's managed runtime
and repo code still validates on the consumer repo's own toolchain. In the
Odylith product repo, pinned dogfood is the default proof posture and detached
`source-local` is the explicit unreleased-dev posture.

## Why This Architecture Works For Agentic Coding

Agentic coding works better when the operating truth is:

- file-backed
- versioned with the code
- diffable in review
- branchable with the work
- addressable by stable repo paths

That is the bet behind Odylith.

Instead of scattering plans, bugs, diagrams, topology, and execution context
across external tools and chat residue, Odylith keeps that truth in the repo
itself and renders usable surfaces from it.

Why that matters for agents:

- they can ground against exact files and exact repo paths
- code changes and governance changes can land in the same review
- there is no sync gap between what the repo is and what the agent sees
- the next agent inherits durable context instead of rediscovering it

Why that matters for humans:

- code, plans, bugs, diagrams, and execution evidence stay reviewable in one
  place
- handoffs get stronger because current state and recent decisions stay in the
  repo
- onboarding gets faster because architecture and operating truth are visible

## The Agent Loop In An Odylith Repo

| Phase | Odylith Capability | Why It Helps |
| --- | --- | --- |
| Start the task | Context Engine | The agent begins from grounded packets and repo memory instead of a blind repo sweep. |
| Bind to the real program | Radar + Compass | The change stays tied to the active workstream, recent execution trail, blockers, and successors. |
| Understand system shape | Registry + Atlas | The agent can see components, boundaries, linked specs, and topology before it edits across them. |
| Scale the work safely | Subagent Router + Subagent Orchestrator | Wider tasks can decompose and delegate with explicit boundaries instead of ad-hoc prompt fanout. |
| Handle failure with structure | Tribunal + Remediator + Casebook | Failures turn into grounded diagnosis, rival explanations, bounded corrective action, and reusable bug memory. |
| Leave stronger truth behind | Repo-local governance surfaces | Plans, specs, diagrams, workstream state, and execution evidence remain in the repo for the next turn. |

That is the operating model: ground first, act with bounded context, validate,
and leave the repo in a more knowable state than you found it.
