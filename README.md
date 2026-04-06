<p align="center">
  <img
    src="docs/brand/odylith/2026-04-rebrand-package/lockup/odylith-lockup-horizontal.svg"
    alt="Odylith"
    width="560"
  />
</p>

<h2 align="center" style="font-size: 2.4rem;">Odylith Stops Coding Agents From Confidently Doing The Wrong Thing</h2>
<p align="center" style="font-size: 1.35rem;"><strong>It makes coding agents operate like disciplined engineers instead of clever tourists.</strong></p>

> [!IMPORTANT]
> Odylith is not a standalone app or IDE. Install it into a repo, then use it
> through an AI coding agent such as Codex or Claude Code. In Odylith, the
> agent is the execution interface and `odylith/index.html` is the operating
> surface that keeps intent, constraints, topology, and execution state
> visible.

## Quick Start

Install Odylith from the Git-backed repository you want to augment:

```bash
curl -fsSL https://github.com/odylith/odylith/releases/latest/download/install.sh | bash
```

Run it from the repo root when you can; Odylith can also detect that root from
any subdirectory inside the same repo. Supported public install platforms today
are macOS (Apple Silicon) and Linux (`x86_64`, `ARM64`). Intel macOS and
Windows are out of scope for the current preview contract.

After install, open the repo in Codex or Claude Code. For first-run behavior,
the first prompt to use, browser-shell behavior, and repo-root selection or
reduced-mode details, see [First Run In An Odylith Repo](odylith/README.md#first-run).
For more example prompts, see
[Starter Prompt Inspirations](docs/STARTER_PROMPT_INSPIRATIONS.md).

## Why "Odylith"?

Odylith combines movement with permanence: exploration anchored by a stable
core.

## Intro

**Odylith changes the operating conditions for Codex or Claude Code.**

- It replaces blind repo search with scoped grounding.
- It gives the agent durable repo-local memory and a forensic trail.
- It governs validation, diagnosis, recovery, and closeout.

Base coding agents can read a repo, search files, sketch a plan, write code,
and infer some local context from the code itself. But serious work depends on
intent, constraints, ownership, validation obligations, and definition of done
that are not reliably encoded in code alone.

With Odylith, that execution truth becomes explicit and durable in the
repository, so the agent starts from governed context instead of
reconstructing it from scratch on every turn.

### Turn Requests Into Execution Truth

Odylith gives coding agents two durable advantages: **delivery intelligence**
and **delivery governance**.

Delivery intelligence recovers intent, constraints, dependencies, topology,
and validation requirements from the repository's real operating history.

Delivery governance turns that into execution truth: the right slice, the
right owner, the blockers, and the real definition of done.

That is the real value: less time re-deriving the repository, more time making
the right change.

More on the operating frame:
[Why Bolting Odylith Onto Codex Or Claude Code Changes The Outcome](docs/WHY_ODYLITH_CHANGES_OUTCOMES.md)

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

Odylith publishes two benchmark views and keeps their claims separate:

- `Grounding Benchmark` (`--profile diagnostic`): measures how well Odylith
  builds the right grounded context before the live agent run
- `Live Benchmark` (`--profile proof`): measures how well Odylith completes
  the real task end to end against raw Codex CLI

In README framing, `odylith_off` is the raw Codex CLI lane.

Current public proof posture is local-first memory on LanceDB plus Tantivy.
These are first public eval runs and should be read as a baseline, not a
ceiling. Odylith wins by grounding and operationalizing shared repo truth
better, not by hiding truth from the baseline lane.

### Grounding Benchmark

> [!NOTE]
> The Grounding Benchmark (`--profile diagnostic`) is not the product claim.
> It isolates packet and prompt construction quality before any live Codex
> session begins.

The Grounding Benchmark answers:

- "Does Odylith build a better grounded packet/prompt than `odylith_off`?"
- "What is the prep-time and prompt-size cost of Odylith’s retrieval/memory layer?"
- "Does Odylith improve required-path coverage before the model starts working?"

Grounding benchmark snapshot:
[Current Grounding Benchmark Snapshot](docs/benchmarks/GROUNDING_BENCHMARK_SNAPSHOT.md)

Grounding benchmark tables:
[Benchmark Tables](docs/benchmarks/BENCHMARK_TABLES.md)

#### Grounding Graphs

**Headline win:** Odylith starts the model with materially better grounding:
`+0.320` required-path recall and `+0.690` validation-success proxy versus
`odylith_off`.

On the warm-cache diagnostic lane, `odylith_on` beat `odylith_off` across `37`
seeded packet and prompt scenarios with:

- `+0.320` required-path recall
- `+0.084` required-path precision
- `+0.690` validation-success proxy
- `+7.048 ms` median wall clock (`9.881 ms` p95, `254.219 ms` total across all `37` pairs)

The family heatmap uses the linked developer-first family order rather than raw
token cost. The grounding quality frontier credits prompt-visible repo paths on
the raw control lane, and the operating-posture view comes from the sampled
`adoption_proof` slice.

<p align="center">
  <img
    src="docs/benchmarks/diagnostic/odylith-benchmark-family-heatmap.svg"
    alt="Odylith grounding benchmark family heatmap"
    width="100%"
  />
</p>
<p align="center">
  <img
    src="docs/benchmarks/diagnostic/odylith-benchmark-quality-frontier.svg"
    alt="Odylith grounding benchmark quality frontier"
    width="100%"
  />
</p>
<p align="center">
  <img
    src="docs/benchmarks/diagnostic/odylith-benchmark-frontier.svg"
    alt="Odylith grounding benchmark frontier"
    width="100%"
  />
</p>
<p align="center">
  <img
    src="docs/benchmarks/diagnostic/odylith-benchmark-operating-posture.svg"
    alt="Odylith grounding benchmark operating posture"
    width="100%"
  />
</p>

### Live Benchmark

> [!TIP]
> The Live Benchmark (`--profile proof`) is the product-claim lane. Current
> full-proof status: `provisional_pass`.

The Live Benchmark answers:

- "Does Odylith beat raw Codex CLI on the same live end-to-end task contract?"
- "What is the full matched-pair time to valid outcome?"
- "Does Odylith improve required-path coverage, validation, and expectation success on the live run?"

Live benchmark snapshot:
[Current Live Benchmark Snapshot](docs/benchmarks/LIVE_BENCHMARK_SNAPSHOT.md)

Live benchmark tables:
[Benchmark Tables](docs/benchmarks/BENCHMARK_TABLES.md)

#### Live Graphs

**Headline win:** Odylith reaches valid outcomes faster and with far less
model spend: `-12.43s` median time to valid outcome and `-52,561` median
live-session input tokens versus `odylith_off`.

On the conservative published proof view, `odylith_on` beat `odylith_off`
across `37` seeded scenarios with:

- `-12.43s` median time to valid outcome
- `-52,561` median live-session input tokens
- `+0.227` required-path recall
- `+0.168` required-path precision
- `+0.393` expectation success

This published view keeps the scenario-wise worst-of-warm/cold result for each
scenario, drawn from `74` matched pairs (`148` total live results), so the
headline stays conservative rather than cherry-picked.

The family heatmap uses the linked developer-first family order rather than
prompt-token cost.

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

Need help reading the graphs, reports, and artifacts? See
[How To Read Odylith's Codex Benchmarks](docs/benchmarks/README.md).

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
- [How To Read Odylith's Codex Benchmarks](docs/benchmarks/README.md)
- [Project Status And Disclosures](docs/STATUS_AND_DISCLOSURES.md)
