<p align="center">
  <img
    src="docs/brand/odylith/2026-04-rebrand-package/lockup/odylith-lockup-horizontal.svg"
    alt="Odylith"
    width="560"
  />
</p>

<h2 align="center" style="font-size: 2.4rem;">Odylith Stops Coding Agents From Confidently Doing The Wrong Thing</h2>
<p align="center" style="font-size: 1.35rem;"><strong>It makes coding agents operate like disciplined engineers instead of clever tourists.</strong></p>

## Intro

Install Odylith into any repo. Use it through Codex or Claude Code.

Without Odylith, every agent session starts from scratch. Reading the repo,
inferring the architecture, guessing intent and constraints, discovering what
went wrong last time. With Odylith, the agent starts from governed truth: the
right slice, the real component boundaries, the live blockers, the invariants,
the historical learnings from past failures, and the full execution history. It
gets to the actual work faster, makes fewer wrong moves, and leaves durable
evidence behind for the next session. The more you use Odylith, the better it
gets. Every workstream, every bug, every component boundary, every decision
teaches it more about your repo, so it grounds the next session deeper than the
last.

Odylith reasons about your repo through delivery intelligence, grounds every
turn through local-first retrieval, governs every action through execution
admissibility, adjudicates ambiguous postures through its Tribunal, and keeps
its own durable memory across sessions. It runs through both Codex and Claude
Code as first-class hosts.

More on the operating frame:
[Why Bolting Odylith Onto Codex Or Claude Code Changes The Outcome](docs/WHY_ODYLITH_CHANGES_OUTCOMES.md)

## Quick Start

Install Odylith from the Git-backed repository you want to augment:

```bash
curl -fsSL https://odylith.ai/install.sh | bash
```

Run it from the repo root when you can; Odylith can also detect that root from
any subdirectory inside the same repo. The current GA platform contract covers
macOS (Apple Silicon) and Linux (`x86_64`, `ARM64`). Intel macOS and Windows
are not part of the current GA platform set.

## Prove It In 2 Minutes

Open the repo in Codex or Claude Code and say:

> **"Odylith, show me what you can do."**

Odylith reads your repo — source structure, import graph, manifest files — and
shows you the component boundaries, workstreams, architecture diagrams, and
issues it can create. Each suggestion comes with the command to run it.

Then open `odylith/index.html` in a browser and follow the Cheatsheet in the
drawer.

See **[Operator Instructions](docs/OPERATOR_INSTRUCTIONS.md)** for the full
set of things you can ask the agent to do.

> [!TIP]
> **⭐ If Odylith makes your coding agent materially sharper in real repo work,
> star the repo so other operators can find it.**

## What Does The Name "Odylith" Mean?

Odylith combines "Ody," suggesting a journey, with "lith," from the Greek
_lithos_, meaning stone. The result is a name that suggests movement guided by
permanence: exploration anchored by a stable core. It reflects the idea at the
heart of the product: motion with a center, exploration with structure, and a
path toward agentic AI swarms that replace rigid monoliths with adaptive,
living networks.

## Context Engine

The Context Engine answers one question: **"what is true and relevant?"** It
narrows the repo to the smallest grounded slice before the agent reasons,
plans, or asks the execution engine whether a move is admissible.

More on the Context Engine:
[Context Engine](docs/CONTEXT_ENGINE.md)

## Execution Engine

The execution engine answers one question: **"given what we know is true,
what is the next admissible move?"** It sits between the Context Engine and
the actual tool invocation layer, turning grounded context into a
machine-readable contract that governs what the agent can and cannot do next.

More on the execution engine:
[Execution Engine](docs/EXECUTION_ENGINE.md)

## Tribunal

One of Odylith's core strengths is that it can take one blocked or ambiguous repo posture, run ten specialist actors over the same grounded evidence, and force an adjudicated case before the agent acts. Tribunal is the engine for that step. It is not the first-turn grounding path. It runs in higher-level delivery-intelligence flows such as odylith sync, governed surface refresh, and evaluation or benchmark paths when Odylith needs to explain a live blocker, conflict, failure, or ambiguous posture in a workstream, component, or diagram.

<p align="center">
  <img
    src="docs/readme/tribunal-flow.png"
    alt="Tribunal diagnosis flow from live actionable scope to grounded dossier, actor review, adjudicated case, Remediator packet, and Odylith surfaces"
    width="1100"
  />
</p>

- It builds a grounded case file for the blocked scope.
- It runs specialist review and adjudicates one explicit read of the problem.
- It hands bounded remediation forward with validation and rollback guards.

More on Tribunal and the product control plane:
[Odylith Product Components](odylith/PRODUCT_COMPONENTS.md)

## Surface Tour

Captured from the local Odylith shell in this repository. The screenshots below
were refreshed on `2026-04-05`. Click any screengrab to open the full-size
image.

All of the views below are the canonical `odylith/index.html` shell with a
specific surface tab active, because that is the actual operator experience
Odylith ships.

### Radar

The example below shows workstream `B-040` inside the Radar shell.

<a href="docs/readme/surfaces/radar-shell.png">
  <img
    src="docs/readme/surfaces/radar-shell.png"
    alt="Odylith Radar surface inside the Odylith shell"
    width="100%"
  />
</a>

- **Ranked backlog:** the left rail is the active delivery queue, grouped by
  execution state so the agent sees what is moving, parked, or already done.
- **Selected workstream detail:** the right pane turns one workstream into
  execution truth with score, dates, confidence, traceability, and linked
  specs or plans.
- **Delivery controls:** the search and filter bar lets you narrow by section,
  phase, activity, lane, priority, and sort order without leaving the shell.

### Compass

The example below shows the live global Compass brief in the `48h` window.

<a href="docs/readme/surfaces/compass-shell.png">
  <img
    src="docs/readme/surfaces/compass-shell.png"
    alt="Odylith Compass surface inside the Odylith shell"
    width="100%"
  />
</a>

- **Standup brief:** the left column summarizes what changed, what matters
  now, and what the current execution slice is trying to achieve.
- **Audit timeline:** the right column is the timeline audit, showing
  timestamped execution evidence for the selected audit day.
- **Scope and time controls:** the top pills switch between `24h` and `48h`
  windows, set the audit day, and move between global and workstream-scoped
  views.

### Atlas

The example below shows diagram `D-017` inside the Atlas shell.

<a href="docs/readme/surfaces/atlas-shell.png">
  <img
    src="docs/readme/surfaces/atlas-shell.png"
    alt="Odylith Atlas surface inside the Odylith shell"
    width="100%"
  />
</a>

- **Diagram catalog:** the left rail is the searchable Atlas index, with
  filters for kind, workstream, and freshness.
- **Connected workstream context:** the header binds each diagram to owners,
  active touches, and historical references so topology stays grounded in live
  delivery.
- **Diagram viewer:** the center pane is the zoomable diagram itself, with
  controls to pan, fit, export, and inspect the architecture without leaving
  the shell.

### Registry

The example below shows the `Tribunal` component dossier inside the Registry shell.

<a href="docs/readme/surfaces/registry-shell.png">
  <img
    src="docs/readme/surfaces/registry-shell.png"
    alt="Odylith Registry surface inside the Odylith shell"
    width="100%"
  />
</a>

- **Component inventory:** the left column is the curated component list, which
  gives the agent a governed map of what exists.
- **Component dossier:** the main panel explains what a component is, why it is
  tracked, what spec or topology is attached, and which forensic evidence
  supports it.
- **Change chronology:** the lower forensic stream is the audit trail for that
  component, so history and evidence stay attached to the current spec.

### Casebook

The example below shows case `CB-009` inside the Casebook shell.

<a href="docs/readme/surfaces/casebook-shell.png">
  <img
    src="docs/readme/surfaces/casebook-shell.png"
    alt="Odylith Casebook surface inside the Odylith shell"
    width="100%"
  />
</a>

- **Bug case queue:** the left column is the searchable case list, with
  severity and status filters to separate active incidents from resolved
  learnings.
- **Selected bug detail:** the main pane turns one failure into a reusable
  dossier with description, failure signature, detection path, ownership, and
  fix history.
- **Prevention memory:** the lower sections keep the root cause, verification,
  rollback, and regression tests visible so the same bug is less likely to
  return.

## Benchmarks

### v0.1.11 Current Benchmark Report

Odylith publishes two benchmark views and keeps their claims separate:

- `Grounding Benchmark`: measures how well Odylith builds the right grounded
  context before the live agent run
- `Live Benchmark`: measures how well Odylith completes the real task end to
  end against the raw host CLI

In README framing, `odylith_off` is the raw host CLI lane.

Current v0.1.11 public proof posture is local-first on the Odylith Memory
Substrate. These are first public eval runs and should be read as a baseline,
not a ceiling. The current full live proof was executed on Codex, while bounded
Codex and Claude smokes provide host-agnostic coverage and the benchmark
contract remains host-neutral. Odylith wins by grounding and operationalizing
shared repo truth better, not by hiding truth from the baseline lane or quietly
using undeclared benchmark affordances.

### Grounding Benchmark

> [!NOTE]
> The Grounding Benchmark is not the product claim. It isolates packet and
> prompt construction quality before any live host session begins.

The Grounding Benchmark answers:

- "Does Odylith build a better grounded packet/prompt than `odylith_off`?"
- "What is the prep-time and prompt-size cost of Odylith's retrieval/memory layer?"
- "Does Odylith improve required-path coverage before the model starts working?"

Current grounding report:
[9dcae95d5bb62c75](docs/benchmarks/GROUNDING_BENCHMARK_SNAPSHOT.md),
generated `2026-04-25T11:20:25Z`, status `provisional_pass`.

| Signal | Current grounding delta versus `odylith_off` |
| --- | ---: |
| Required-path recall | `+0.326` |
| Required-path precision | `+0.049` |
| Validation-success proxy | `+0.689` |
| Critical required-path recall | `+0.278` |
| Critical validation-success proxy | `+0.613` |
| Expectation-success proxy | `+0.951` |
| Median prompt-bundle input tokens | `+834` |
| Median packet time | `+23 ms` |

#### Current Grounding Graphs

<p align="center">
  <img
    src="docs/benchmarks/grounding/odylith-benchmark-family-heatmap.svg"
    alt="Odylith grounding benchmark family heatmap"
    width="100%"
  />
</p>
<p align="center">
  <img
    src="docs/benchmarks/grounding/odylith-benchmark-quality-frontier.svg"
    alt="Odylith grounding benchmark quality frontier"
    width="100%"
  />
</p>
<p align="center">
  <img
    src="docs/benchmarks/grounding/odylith-benchmark-frontier.svg"
    alt="Odylith grounding benchmark frontier"
    width="100%"
  />
</p>
<p align="center">
  <img
    src="docs/benchmarks/grounding/odylith-benchmark-operating-posture.svg"
    alt="Odylith grounding benchmark operating posture"
    width="100%"
  />
</p>

### Live Benchmark

> [!TIP]
> The Live Benchmark is the product-claim lane. It measures full end-to-end task
> completion after grounding, execution posture, focused checks, and validation
> policy are allowed to operate under the declared comparison contract.

The Live Benchmark answers:

- "Does Odylith beat the raw host CLI on the same live end-to-end task contract?"
- "What is the full matched-pair time to valid outcome?"
- "Does Odylith improve required-path coverage, validation, and expectation success on the live run?"

Current live proof report:
[44f2a3d83d2c9975](docs/benchmarks/LIVE_BENCHMARK_SNAPSHOT.md),
generated `2026-04-25T11:19:38Z`, status `provisional_pass`.

| Signal | Current live proof delta versus `odylith_off` |
| --- | ---: |
| Required-path recall | `+0.258` |
| Required-path precision | `+0.421` |
| Hallucinated-surface rate | `-0.397` |
| Validation success | `+0.081` |
| Critical required-path recall | `+0.206` |
| Critical validation success | `+0.097` |
| Expectation success | `+0.688` |
| Write-surface precision | `+0.011` |
| Unnecessary widening | `-0.011` |
| Median live-session input tokens | `-206,626` |
| Median total model tokens | `-209,404` |
| Median time to valid outcome | `-1m 28s` |

Publication status:

- hard-gate blockers: none
- fairness contract passed: `True`
- corpus seriousness floor passed: `True`
- tracked-corpus coverage: `82 / 82` scenarios
- full matched pairs: `164` across `warm` and `cold`
- conservative published comparison: `82` same-scenario pairs
- warm/cold robustness consistency: `True`

Read the timing and token wins as benchmark wall-clock and full-session spend,
not solo-user interactive latency. Scenario-declared focused checks and no-op
proxy evidence are part of the declared benchmark contract and remain visible
in the machine-readable reports.

Full current artifacts:
[Live Snapshot](docs/benchmarks/LIVE_BENCHMARK_SNAPSHOT.md),
[Grounding Benchmark Snapshot](docs/benchmarks/GROUNDING_BENCHMARK_SNAPSHOT.md),
[Benchmark Tables](docs/benchmarks/BENCHMARK_TABLES.md), and
[How To Read Odylith's Benchmark Proof](docs/benchmarks/README.md).
The versioned GitHub artifact bundle, including the compressed raw source
truth, is stored under
[docs/benchmarks/v0.1.11](docs/benchmarks/v0.1.11/README.md).

#### Current Live Graphs

<p align="center">
  <img
    src="docs/benchmarks/proof/odylith-benchmark-family-heatmap.svg"
    alt="Odylith live benchmark family heatmap"
    width="100%"
  />
</p>
<p align="center">
  <img
    src="docs/benchmarks/proof/odylith-benchmark-quality-frontier.svg"
    alt="Odylith live benchmark quality frontier"
    width="100%"
  />
</p>
<p align="center">
  <img
    src="docs/benchmarks/proof/odylith-benchmark-frontier.svg"
    alt="Odylith live benchmark frontier"
    width="100%"
  />
</p>
<p align="center">
  <img
    src="docs/benchmarks/proof/odylith-benchmark-operating-posture.svg"
    alt="Odylith live benchmark operating posture"
    width="100%"
  />
</p>

### v0.1.10 Benchmark Archive

The previous README-backed benchmark bundle is retained under
[docs/benchmarks/v0.1.10](docs/benchmarks/v0.1.10/README.md) instead of being
mixed into the current v0.1.11 claim.

- archived live proof snapshot: report `2d8444952aef28d2`, generated
  `2026-04-24T00:57:09Z`, status `hold`
- archived Grounding Benchmark snapshot: report `dd35a4aab061f49f`, generated
  before the v0.1.11 refresh
- archived legacy graph set: report `926bfeab4e887ade`, retained from the
  older unprofiled graph filenames

<details>
<summary>v0.1.10 archived live graphs</summary>

<p align="center">
  <img
    src="docs/benchmarks/v0.1.10/proof/odylith-benchmark-family-heatmap.svg"
    alt="Archived Odylith live benchmark family heatmap"
    width="100%"
  />
</p>
<p align="center">
  <img
    src="docs/benchmarks/v0.1.10/proof/odylith-benchmark-quality-frontier.svg"
    alt="Archived Odylith live benchmark quality frontier"
    width="100%"
  />
</p>
<p align="center">
  <img
    src="docs/benchmarks/v0.1.10/proof/odylith-benchmark-frontier.svg"
    alt="Archived Odylith live benchmark frontier"
    width="100%"
  />
</p>
<p align="center">
  <img
    src="docs/benchmarks/v0.1.10/proof/odylith-benchmark-operating-posture.svg"
    alt="Archived Odylith live benchmark operating posture"
    width="100%"
  />
</p>

</details>

## Best Fit Use Cases

Odylith is strongest when:

- the work spans multiple files, contracts, or governance surfaces
- the repo is large enough that boundaries, ownership, bug history, and
  execution state matter
- you want specs, plans, component inventory, diagrams, and bug history to
  live beside the code instead of across separate SaaS tools
- you want recent execution and decisions visible in Compass instead of buried
  in terminal history

Odylith is not meant to replace direct file reads for tiny obvious edits. It is
most useful when the repo is large enough that repo memory, topology, workstream
state, and execution history start to matter.

## Odylith Governs Itself

This repo also uses Odylith on itself.

| Surface | Product-Owned Truth |
| --- | --- |
| Radar | `odylith/radar/` |
| Atlas | `odylith/atlas/` |
| Compass | `odylith/compass/` |
| Registry | `odylith/registry/` |
| Casebook | `odylith/casebook/` |

## Read Next

- [First Run In An Odylith Repo](odylith/README.md#first-run)
- [FAQ](odylith/FAQ.md)
- [Operating Model](odylith/OPERATING_MODEL.md)
- [Product Components](odylith/PRODUCT_COMPONENTS.md)
- [Advanced Operator Use Cases](docs/ADVANCED_OPERATOR_USE_CASES.md)
- [Governance Surfaces](odylith/surfaces/GOVERNANCE_SURFACES.md)
- [What Gets Installed](docs/specs/odylith-repo-integration-contract.md#what-gets-installed)
- [Repo Integration Contract](docs/specs/odylith-repo-integration-contract.md)
- [Install and Upgrade Runbook](odylith/INSTALL_AND_UPGRADE_RUNBOOK.md)
- [How To Read Odylith's Benchmark Proof](docs/benchmarks/README.md)
- [Project Status And Disclosures](docs/STATUS_AND_DISCLOSURES.md)
