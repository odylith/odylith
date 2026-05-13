# AGENTS.md

<!-- odylith-scope:start -->
## Odylith Scope

Paths under `odylith/` follow `odylith/AGENTS.md`; this root block stays a low-latency hard-law kernel for the installed consumer lane.

- Work inside `odylith/` follows `odylith/AGENTS.md` first; repo-root guidance remains authoritative outside `odylith/`.
- For substantive work, read the nearest `AGENTS.md`, run `./.odylith/bin/odylith start --repo-root .` first, then run `odylith context --repo-root . <ref>` only after startup when a precise anchor is known. Direct repo scan before that start step is a policy violation unless the task is trivial or Odylith is unavailable.
- Do not run `odylith context`, `odylith query`, `git status`, broad repo search, or other repo-inspection commands in parallel with that start step. Let `start` finish first; then narrow.
- CLI-first is non-negotiable for both Codex and Claude Code: use the nearest `AGENTS.md`, repo-local launcher, truthful `odylith ... --help`, `odylith backlog ...`, `odylith governance ...`, `odylith validate plan-* ...`, `odylith bug ...`, `odylith component ...`, `odylith registry ...`, `odylith atlas ...`, and `odylith compass ...` before hand edits. Do not hand-edit governed files where a CLI exists. `odylith plan --help` is read-only; do not probe `odylith/technical-plans/source/`. Full policy: `odylith/agents-guidelines/CLI_FIRST_POLICY.md`, anchored by `CB-104`.
- For `odylith ... --help` discovery, run the single authoritative help command first and do not run parallel exploratory filesystem probes whose failure can cancel the visible help call. If a guess is invalid, fall back to `odylith --help` and then the nearest listed subcommand.
- Routine governance tasks that map to first-class CLI families such as `odylith bug capture`, `odylith backlog create`, `odylith component register`, `odylith atlas scaffold`, or `odylith compass log` should go straight to that CLI; keep `.agents/skills` lookup, missing-shim, and fallback-source details implicit unless they change the next user-visible action.
- Empty/thin prompts route to `odylith greenfield propose --repo-root . --prompt "<request>"` for a no-write Product Intent reasoning request. The host must write the short Product Intent Confirmation in chat from live reasoning: product story, actors, systems, assumptions, ambiguities, and proceed/edit/reject gate. Do not generate backlog, Registry, Atlas, release waves, validation obligations, proposal JSON, or prompt-only `greenfield create` records before the operator confirms the intent. After confirmation, use `odylith greenfield propose --confirm-intent` for the proposal schema/proof contract; the host authors the project-specific proposal JSON from the confirmed intent, and `odylith greenfield apply --repo-root . --proposal-file odylith-greenfield-proposal.json --confirm --release 0.0.1` validates it, runs the Tribunal write gate, and writes governed records. Do not use canned domain families, scaffolds, hand-waved templates, or code before the product gates are accepted. When the CLI returns proposal stdout directly, do not hide it behind collapsed tool output or replace it with a thin host-written summary; surface the actual confirmation or proposal content that matters.
- `odylith backlog create` is fail-closed and must receive grounded Problem, Customer, Opportunity, Product View, and Success Metrics text; never create or accept a title-only, placeholder, or boilerplate Radar workstream.
- For quick visibility after a narrow truth change, rerender only the owned surface: `odylith radar refresh`, `odylith registry refresh`, `odylith casebook refresh`, `odylith atlas refresh`, or `odylith compass refresh`; use `odylith compass deep-refresh` for brief settlement and `odylith sync` for the broader governance lane.
- Keep startup, Context Engine, Execution Engine, memory substrate, Tribunal, Intervention Engine, observers, governance, subagent routing, Surface DAGs, delivery, analysis, and migration-breakage observation active. Optimize by routing, caching, batching, and shortening prompt surface, not by disabling engines.
- Treat AI slop as a regression. Apply across consumer and maintainer lanes, Codex and Claude, any language, and any codebase or project surface. Move ownership, not file boundaries; partial shared-kernel adoption is still incomplete; if the replacement smell remains, the pass is incomplete. Prose-only hardening is incomplete. Repo-wide claims require fresh behavior proof for the touched slice and a fresh structural inventory for the claimed scope. Browser surfaces require the headless browser matrix across normal, empty/fallback, and degraded or error states. Rule: `odylith/agents-guidelines/ANTI_SLOP_AND_DECOMPOSITION.md`; use `odylith/skills/odylith-code-hygiene-guard/SKILL.md` under quality pressure.
- For guidance behavior pressure cases or discipline pressure, use `odylith validate guidance-behavior --repo-root .`, `odylith benchmark --profile quick --family guidance_behavior`, `odylith discipline status/check/explain`, `odylith validate discipline --repo-root .`, and `odylith benchmark --profile quick --family discipline --no-write-report --json`. Discipline hot paths must not call host models, providers, subagents, broad scans, full validation, or projection expansion.
- A plain `Odylith, help` request is the CLI help fast path. Use the first available `odylith --help` command and print stdout only.
- A plain `Odylith, show me what you can do` request is the advisory `odylith show` repo-capability demo. It is not a request to prove intervention UX, diagnose install posture, run `start`, run `doctor`, or explain missing launcher state. Use the first available show command and print stdout only.
- A request to list Odylith capabilities, engines, product architecture, or the capability map is the product-owned inventory path. Use `odylith capabilities` and print stdout only. Do not infer the taxonomy from `odylith --help`, `odylith show`, Claude Code, Codex, or any other host model capability surface.
- In Codex commentary, keep startup, fallback, routing, and packet-selection internals implicit. Describe task progress, not control-plane receipts, unless the user asks for the command, a real blocker requires it, or a consumer-versus-maintainer lane distinction matters. Never say `Startup fell back`.
- Keep normal commentary task-first and human; reserve `Odylith Insight:`, `Odylith History:`, or `Odylith Risks:` for rare high-signal moments. Silence is better than filler.
- Treat live teaser, `**Odylith Observation**`, and `Odylith Proposal` as the intervention-engine fast path; treat `Odylith Assist:` as the chatter-owned closeout. Do not collapse those layers. Observation stays one short labeled line like `Odylith Assist`; Proposal stays a short ruled block. Keep one stable intervention identity for a session-local moment.
- Codex checkpoint hooks may carry hidden Observation/Proposal/Assist context and surface an earned beat; Claude direct-edit and Bash PostToolUse hooks stay silent on success and emit only compact failure/skipped-refresh status. Claude Stop is memory/logging only, not a fallback closeout.
- Hook `systemMessage` or `additionalContext` is not chat-visible proof. Before claiming active intervention UX, run or cite `odylith codex intervention-status` or `odylith claude intervention-status`; it is the low-latency delivery record for Teaser, Ambient Highlight, Observation, Proposal, and Assist readiness. End-to-end proof requires `Activation: ready` plus chat visibility. When in doubt, run `odylith codex visible-intervention` or `odylith claude visible-intervention` and show that Markdown directly.
- At closeout, add at most one `Odylith Assist:` or `**Odylith Assist:**` line only when it materially helps; normal non-passthrough prompts do not get an Assist line by default. Do not add Assist just because Odylith ran. Lead with the user win, link updated governance IDs inline when they changed, name affected governance-contract IDs only when no governed file moved, frame the edge against `odylith_off` or the broader unguided path when supported, keep it crisp, authentic, clear, simple, insightful, and ground the line in concrete observed counts, measured deltas, or validation outcomes, or a concrete chat-visibility complaint.
- Explicit feedback that Odylith ambient highlights, interventions, Assist, Observations, Proposals, hooks, or chat output are not visible is a closeout signal; low-signal short turns stay silent.
- In consumer repos, grounding Odylith is diagnosis authority, not blanket write authority: if the issue target is Odylith itself, stop at diagnosis and maintainer-ready feedback unless the operator explicitly authorizes Odylith mutation.
- Treat `odylith upgrade`, `odylith reinstall`, `odylith doctor --repair`, `odylith sync`, and `odylith dashboard refresh` as writes when they change `odylith/` or `.odylith/`; do not run them autonomously as Odylith fixes in consumer repos.
- Treat backlog/workstream, plan, Registry, Atlas, Casebook, Compass, and session upkeep as one grounded workflow: search existing truth first, extend or reopen existing records when present, and create new governed records only when the slice is genuinely new.
- Queued backlog items, case queues, and shell or Compass queue previews are not implicit implementation instructions. Unless the user explicitly asks to work a queued item, do not pick it up automatically just because it appears in Radar, Compass, the shell, or another Odylith queue surface.
- If the slice expands beyond one truthful record, use child workstreams or execution waves instead of flattening everything into one note, and carry forward intent, constraints, and validation obligations through Odylith session/context packets and Compass updates so repo context compounds over time.
- `./.odylith/bin/odylith` chooses how Odylith runs; it does not decide which repo files the agent may edit, and target-repo code still validates on the target repo's own toolchain.
- Before diagnosing install, upgrade, rollback, or launcher state, run `./.odylith/bin/odylith version --repo-root .` when the launcher exists and treat that live posture as authoritative over older Compass, shell, or release-history context.
- If the launcher is missing, confirm that from the filesystem first and use Odylith's current repair contract instead of assuming the repo is on a legacy consumer path.
- In Codex, treat Odylith-routed native subagent spawn as the default candidate for substantive grounded work across the consumer lane and the Odylith product repo's maintainer mode, including pinned dogfood and detached `source-local` maintainer-dev posture, when the route is bounded and the active host policy allows spawn; keep transport support separate from current-session spawn permission/effectiveness.
- Codex and Claude Code are both validated Odylith delegation hosts under the same grounding, routing, and validation contract. Codex emits routed `spawn_agent` payloads subject to active host policy; Claude Code executes the same bounded delegation contract through Task-tool subagents and the checked-in `.claude/` project assets.
- In the Odylith product repo, maintainer-only release and benchmark publishing work follows `odylith/maintainer/AGENTS.md`.
- In the Odylith product repo's maintainer mode, pinned dogfood is the default proof posture and detached `source-local` is the explicit dev posture for live unreleased `src/odylith/*` execution.

<!-- odylith-scope:end -->

Odylith is a product repo, not a host repo.

## Scope And Precedence
- Read the nearest folder-level `AGENTS.md` before editing files in that scope.
- More specific `AGENTS.md` files override this root file for their subtree.

## Product Boundary
- Odylith owns its product code, product docs, product skills, product guidance, product tests, and its own self-governance records in this repository.
- Host-repo truth is never copied into Odylith. Downstream repos keep their own plans, bugs, workstreams, specs, and diagrams locally.
- Public Odylith content must stay generic. Do not add host-repo-branded labels, tokens, package names, or docs.

## Repo Governance
- Odylith self-governs through the local `odylith/` tree in this repository.
- `odylith/registry/source/component_registry.v1.json` is the authoritative component inventory for the product repo.
- Registry-owned component dossiers live under `odylith/registry/source/components/`.
- The canonical current spec for every Registry component lives under that tree, for example:
  - `odylith/registry/source/components/odylith/CURRENT_SPEC.md`
  - `odylith/registry/source/components/dashboard/CURRENT_SPEC.md`
  - `odylith/registry/source/components/odylith-context-engine/CURRENT_SPEC.md`
  - `odylith/registry/source/components/remediator/CURRENT_SPEC.md`
- `odylith/radar/source/` is the local workstream backlog for Odylith itself.
- `odylith/technical-plans/` is the local implementation-plan record for Odylith itself.
- `odylith/casebook/bugs/` is the local bug record for Odylith itself.
- `odylith/atlas/source/` is the local diagram source tree for Odylith itself.
- `odylith/registry/source/` is the local component-registry source tree for Odylith itself.

## Command Surface
- The supported product contract is the `odylith` CLI.
- In installed repositories, the repo-local launcher `./.odylith/bin/odylith` is the canonical operator entrypoint for that CLI.
- When the launcher is missing in a consumer repo, the canonical hosted bootstrap
  path is `curl -fsSL https://odylith.ai/install.sh | bash`.
- Public docs, help text, remediation text, and operator guidance must use `odylith ...` commands, not host-repo-local script-module entrypoints.

## Lane Model
- There are two top-level environments to keep distinct:
  - consumer lane: installed repo, pinned Odylith-managed runtime, no `source-local`
  - product-repo maintainer mode: the Odylith product repo itself
- Maintainer mode has two explicit postures:
  - pinned dogfood: default proof posture for the shipped runtime
  - detached `source-local`: explicit live-source execution posture for current unreleased changes
- Runtime boundary: the invoked Odylith executable decides which interpreter runs Odylith itself.
- Write boundary: interpreter choice does not decide which repo files the agent may edit.
- Validation boundary: the target repo's own toolchain proves the target repo's application code, while Odylith CLI commands prove Odylith-owned governance and runtime contracts.
- In consumer repos, `./.odylith/bin/odylith` runs Odylith with Odylith's managed Python, but repo tests, builds, and app commands stay on the consumer repo's own toolchain.
- In the Odylith product repo, pinned dogfood proves the shipped runtime; only explicit detached `source-local` posture inside maintainer mode is allowed to execute unreleased live `src/odylith/*` changes.

## Main Branch Safety
- In the Odylith product repo's maintainer lane, the Git `main` branch is read-only for authoring. This is non-negotiable.
- If the current branch is `main` and a task needs code edits or any other tracked repo changes, create and switch to a new branch before the first edit, stage, or commit.
- If work is already on a non-`main` branch, keep using that branch; do not create another branch just to satisfy this rule.
- Read-only inspection and canonical release proof against `origin/main` are allowed, but the Git `main` branch is never a maintainer development workspace.

## Git Branch Naming
- Never use `codex` as a branch name or branch prefix in this repository.
- New branches must use the format `<year>/freedom/<tag>`.
- `<year>` is the current calendar year at branch creation time.
- `<tag>` is a short, descriptive name for the work.

## Contributor Identity
- `freedom-research` is the sole canonical contributor identity for this
  repository, including repo metadata, docs, notices, generated governance,
  release configuration, and commits.
- Do not introduce personal names, alternate handles, or assistant/model
  identities in tracked files unless quoting immutable third-party or
  historical material that cannot be rewritten.
- Local Git config and GitHub CLI keyring operations for this repository must
  use the `freedom-research` identity.
- Commit messages must not contain `Co-Authored-By:`, assistant/tool trailers,
  or "generated with" attribution. Override assistant defaults before commit.

## Source File Size Discipline
- Hand-maintained product source has an `800` LOC soft limit; tests have a
  `1500` LOC ceiling. Generated and mirrored bundle assets are excluded.
- Do not push hand-maintained source past `1200` LOC without an explicit
  exception and decomposition plan. `2000+` LOC requires an active
  decomposition workstream before unrelated feature growth lands.
- If a touched file already exceeds the limit, prefer a focused `1-2` file
  refactor with characterization tests. Prioritize by size x churn x
  centrality, not size alone.

## Anti-Slop Non-Negotiables
- Treat AI slop as a regression in this repository.
- The bar applies to any codebase or project surface: services, libraries,
  apps, CLIs, infra glue, scripts, docs, prompts, hooks, templates, config,
  and generated assets all count.
- No transitional states: move ownership, not just file boundaries; partial
  shared-kernel adoption is still incomplete; if the replacement smell remains,
  the pass is incomplete.
- Guidance-only or prose-only hardening is incomplete. Repo-wide or lane-wide
  claims require fresh behavior proof for the touched slice and a fresh
  structural inventory for the claimed scope.
- Browser-rendered surfaces require the headless browser matrix across normal,
  empty/fallback, and degraded or error states.
- Detailed bans, examples, and proof rules live in
  `odylith/agents-guidelines/ANTI_SLOP_AND_DECOMPOSITION.md`; use
  `odylith/skills/odylith-code-hygiene-guard/SKILL.md` when refactor pressure,
  duplicate helper churn, fake extraction pressure, or AI-shaped entropy is in
  play.

## Change Hygiene
- Keep product docs and bundle docs aligned when the product contract changes.
- Keep install paths fixed: `odylith/` for installed product files and `.odylith/` for mutable runtime state.
- Avoid host-repo-specific fallback logic in public docs and guidance.
