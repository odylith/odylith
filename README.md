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

Install Odylith into a project folder on your laptop. Use it through Codex or Claude Code.

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
its own durable memory across sessions. In empty or thin repos, it can also
turn broad greenfield intent into a staged, read-only governance proposal
before source exists. It runs through both Codex and Claude Code as first-class
hosts.

More on the operating frame:
[Why Bolting Odylith Onto Codex Or Claude Code Changes The Outcome](docs/WHY_ODYLITH_CHANGES_OUTCOMES.md)

## Quick Start

Install Odylith in a project folder on your laptop:

```bash
curl -fsSL https://odylith.ai/install.sh | bash
```

Open a terminal in the project folder on your laptop, then run the command.
Odylith installs into that folder on your laptop. It does not install into
GitHub or any external service. The folder can be a Git repo, but it does not
have to be.
The current GA platform contract covers macOS (Apple Silicon) and Linux
(`x86_64`, `ARM64`). Intel macOS and Windows are not part of the current GA
platform set.

## Prove It In 2 Minutes

Open the repo in Codex or Claude Code and say:

> **"Odylith, show me what you can do."**

Odylith reads your repo — source structure, import graph, manifest files — and
shows you the component boundaries, workstreams, architecture diagrams, and
issues it can create. Each suggestion comes with the command to run it.

If the repo is still empty or too thin for source-backed boundaries, Odylith
switches to greenfield mode instead of dead-ending. Odylith compiles untrusted
evidence into typed product facts, the complete governed package, and a clear
sectioned, read-only preview. Native chat confirmation remains unqualified;
the preview does not offer publication.

For example:

```bash
odylith greenfield candidate-contract --repo-root . --prompt "build an ecommerce site"
# The active host writes one complete matching candidate outside the repository.
odylith greenfield propose --repo-root . --prompt "build an ecommerce site" --candidate-file "<temporary-file>"
```

The active host reasons once over the returned contract. Odylith deterministically
validates that untrusted candidate and, before confirmation, stores each compiled
package at an immutable,
transaction-addressed pending path under `.odylith/runtime/greenfield/`. That package already
contains the quality-gated backlog, first-release plan, Registry components,
Atlas topology, assumptions, risks, open questions, validation obligations, and
post-commit handoff. The separate, explicit operator `greenfield create` command
requires the canonical transaction file, hash and confirmation. It publishes only
sealed bytes, without model interpretation or generation. No semantic, model, or
provider call runs after candidate receipt; detached semantic and UX review
qualifies frozen release evidence rather than consumer transactions. A chat approval must
not be converted into that command by a model. The commit-only path materializes an immutable generation, switches one
active pointer, validates readback, and directs the operator to that exact project view.

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

Tribunal is Odylith's structured diagnosis engine. It is what Odylith uses when
the repo is no longer a cold-start mystery, but the current posture is still
blocked, ambiguous, disputed, or risky enough that a normal "just continue"
agent move would be a bad bet. The Context Engine answers what is true and
relevant. The Execution Engine answers what move is admissible. Tribunal
answers a different question: **what is actually going on here, what rival
explanation could still be true, and what check would discriminate between
them?**

That is why Tribunal matters to the Odylith claim. It changes the failure mode
from "the model guessed and continued" into "the system opened a grounded case
before action." Same model, better operating frame: explicit evidence, rival
diagnosis, risk if wrong, discriminating next check, and bounded remediation.

Tribunal does not run on every turn and it is not the first-turn grounding
path. It runs inside higher-level delivery-intelligence flows such as
`odylith sync`, governed surface refresh, and evaluation or benchmark paths
when Odylith needs to explain a live blocker, conflict, failure, or ambiguous
posture in a workstream, component, or diagram.

<p align="center">
  <img
    src="docs/readme/tribunal-flow.png"
    alt="Tribunal diagnosis flow from live actionable scope to grounded dossier, actor review, adjudicated case, Remediator packet, and Odylith surfaces"
    width="1100"
  />
</p>

The pipeline is deliberately closer to an engineering review board than a
generic summarizer:

1. Delivery intelligence identifies live actionable scopes and filters out
   clear-path work.
2. Tribunal ranks candidates by scope type, scenario, severity, decision debt,
   governance lag, blast radius, and stable identity tie-breaks.
3. It builds a dossier for each focused case: subject, decision at stake,
   observations, evidence quality, proof refs, explanation facts, and compact
   evidence items.
4. Ten fixed actors review the same dossier: observer, ownership resolver,
   causal analyst, policy judge, normative judge, adversary, counterfactual
   analyst, gap analyst, risk analyst, and prescriber.
5. The adjudicator synthesizes one case form with a leading explanation,
   strongest rival, risk if wrong, discriminating next check, confidence,
   actor influence, and maintainer brief.
6. Optional provider enrichment can refine only named fields, and only when the
   result cites grounded evidence. Deterministic reasoning remains the baseline
   and provider failure degrades explicitly.
7. Remediator turns the adjudicated prescription into one bounded correction
   packet with validation, rollback, and stale guards.
8. The case queue, systemic brief, and correction packet feed the shell,
   Compass, Registry, benchmarks, and downstream intervention surfaces.

More on the Tribunal claim, pipeline, and product control plane:
[Tribunal and Remediation](odylith/runtime/TRIBUNAL_AND_REMEDIATION.md),
[Tribunal Component Spec](odylith/registry/source/components/tribunal/CURRENT_SPEC.md),
and [Odylith Product Components](odylith/PRODUCT_COMPONENTS.md)

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

### v0.1.15 Candidate Benchmark Report

The current live benchmark covers **82 scenarios** on Codex, with 164 matched
pairs across warm and cold caches. Its conservative published view clears the
hard quality gates and secondary guardrails. Required-path recall is **99.2%**,
critical recall **97.9%**, and validation success **98.6%**. These results qualify
the measured candidate, not the production release.

Both sides use the same live Codex CLI model selection and reasoning contract,
with an isolated temporary host home and stripped auto-loaded repository
guidance. The run used detached `source-local` at `433f0e38a`, medium reasoning,
and the host's default model selector. It does not establish native Claude or
installed-package qualification.

`odylith_off` is the raw host CLI lane, called `raw_agent_baseline` inside the
report. The separate repository-scan scaffold is a secondary control. Timing
measures benchmark time to a valid outcome; token counts measure full-session
spend. Validator-backed closure can avoid unnecessary changes and a host model
call, so the savings reflect Odylith's operating policy as a whole.

### Grounding Diagnostic

The diagnostic isolates packet and prompt construction. Report
[b75f850362a680d2](docs/benchmarks/GROUNDING_BENCHMARK_SNAPSHOT.md), generated
`2026-10-15T19:31:51Z`, is on **HOLD**: surface drift and packet latency, prompt,
and payload costs exceed its existing thresholds. Its quality proxies improve,
but this report remains an internal tuning result.

| Signal | Diagnostic delta versus the raw prompt bundle |
| --- | ---: |
| Required-path recall | `+0.316` |
| Required-path precision | `+0.047` |
| Validation-success proxy | `+0.648` |
| Critical required-path recall | `+0.256` |
| Critical validation-success proxy | `+0.548` |
| Expectation-success proxy | `+0.823` |
| Median prompt-bundle input tokens | `+871` |
| Median total prompt-bundle payload tokens | `+1,124` |
| Median packet time | `+59 ms` |

#### Diagnostic Graphs

<p align="center">
  <img
    src="docs/benchmarks/diagnostic/odylith-benchmark-family-heatmap.svg"
    alt="Odylith diagnostic benchmark family heatmap"
    width="100%"
  />
</p>
<p align="center">
  <img
    src="docs/benchmarks/diagnostic/odylith-benchmark-quality-frontier.svg"
    alt="Odylith diagnostic benchmark quality frontier"
    width="100%"
  />
</p>
<p align="center">
  <img
    src="docs/benchmarks/diagnostic/odylith-benchmark-frontier.svg"
    alt="Odylith diagnostic benchmark frontier"
    width="100%"
  />
</p>
<p align="center">
  <img
    src="docs/benchmarks/diagnostic/odylith-benchmark-operating-posture.svg"
    alt="Odylith diagnostic benchmark operating posture"
    width="100%"
  />
</p>

### Live Benchmark

Report [ea0fbd0916ee9690](docs/benchmarks/LIVE_BENCHMARK_SNAPSHOT.md), generated
`2026-10-15T15:08:18Z`, has status **provisional pass**. All 82 scenarios are
included; each published pair uses the conservative warm/cold view.

| Signal | Live delta versus the raw host CLI |
| --- | ---: |
| Required-path recall | `+0.227` |
| Required-path precision | `+0.502` |
| Hallucinated-surface rate | `-0.502` |
| Validation success | `+0.013` |
| Critical required-path recall | `+0.205` |
| Critical validation success | `0.000` |
| Expectation success | `+0.652` |
| Write-surface precision | `+0.286` |
| Unnecessary widening | `0.000` |
| Median live-session input tokens | `-245,206` |
| Median total model tokens | `-246,380` |
| Median time to valid outcome | `-48s` |

Fairness, corpus coverage, warm/cold consistency, and the tighter-budget
secondary guardrail clear. The destructive-scope family remains an attention
area. Supplementary repeat probes report quality consistency of 66.7% and
unstable latency; those diagnostics remain visible alongside the main gates.

The corrected comparison selects the completed v0.1.14 report and retains its
HOLD warning. Odylith's recall is unchanged between releases; validation success
increases by 0.027. Two scenarios add four supporting paths relative to that
release, so this is not an identical-input causal comparison. The original
failed comparison is retained, and final-commit proof remains required.

The measured memory posture is local LanceDB and Tantivy retrieval, with remote
retrieval disabled. On strictly bounded cases, first-pass reads stay within the
approved anchors; validator-only tests and generated artifacts become read
candidates only when a concrete contradiction warrants them.

See the [Live Snapshot](docs/benchmarks/LIVE_BENCHMARK_SNAPSHOT.md),
[Diagnostic Snapshot](docs/benchmarks/GROUNDING_BENCHMARK_SNAPSHOT.md),
[Benchmark Tables](docs/benchmarks/BENCHMARK_TABLES.md),
[Benchmark Guide](docs/benchmarks/README.md), and
[Interpretation Contract](docs/research/BENCHMARK_INTERPRETATION_CONTRACT.md).
The [v0.1.11 artifact bundle](docs/benchmarks/v0.1.11/README.md) remains historical.

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

The [v0.1.10 benchmark bundle](docs/benchmarks/v0.1.10/README.md) remains
available as historical evidence.

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
- the repo is new and you want a project-specific governance proposal before
  source-backed boundaries exist
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
