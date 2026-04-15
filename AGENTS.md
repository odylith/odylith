# AGENTS.md

<!-- odylith-scope:start -->
## Odylith Scope

Paths under `odylith/` follow `odylith/AGENTS.md`.

- Work inside `odylith/` should follow `odylith/AGENTS.md` first.
- Before any substantive repo scan or code change outside trivial fixes, the agent must start from the repo-local Odylith entrypoint and keep the active workstream, component, or packet in scope before raw repo search, tests, or edits.
- Direct repo scan before that start step is a policy violation unless the task is trivial or Odylith is unavailable.
- Start substantive turns with `./.odylith/bin/odylith start --repo-root .`; it chooses the safe first lane and prints the exact next command when Odylith cannot narrow the slice yet.
- When you already know the exact workstream, component, path, or id, use `./.odylith/bin/odylith context --repo-root . <ref>` before raw repo search. Use `./.odylith/bin/odylith query --repo-root . "<terms>"` only after concrete anchors already exist.
- CLI-first is non-negotiable for both Codex and Claude Code. Remove all hand-authoring for places where Odylith CLI should be doing the heavy-lifting. When an Odylith CLI command exists for an operation, call the CLI command and do not hand-edit governed files the CLI owns. Hand-authoring governed truth where a CLI exists is a hard policy violation, not a stylistic preference. The authoritative policy, CLI surface enumeration, allowed hand-edit surfaces, and failure-mode handling live in `odylith/agents-guidelines/CLI_FIRST_POLICY.md`, anchored by Casebook learning `CB-104`. The rule travels through routed `spawn_agent` leaves on Codex and Task-tool subagents on Claude Code so delegated work inherits the same contract.
- Default to the nearest `AGENTS.md`, the repo-local launcher, and truthful `odylith ... --help` for routine backlog, plan, bug, spec, component, and diagram upkeep. Treat `.agents/skills/` and `odylith/skills/` as specialist overlays for advanced packet control, orchestration, or high-risk lanes rather than as the default path.
- When a routine governance task already maps to a first-class CLI family such as `odylith bug capture`, `odylith backlog create`, `odylith component register`, `odylith atlas scaffold`, or `odylith compass log`, go straight to that CLI and keep any `.agents/skills` lookup, missing-shim, or fallback-path details implicit unless they change the next user-visible action.
- For quick visibility after a narrow truth change, rerender only the owned surface: `odylith radar refresh`, `odylith registry refresh`, `odylith casebook refresh`, `odylith atlas refresh`, or `odylith compass refresh`. Use `odylith compass deep-refresh` when you also want brief settlement. Keep `odylith sync` as the broader governance and correctness lane.
- Keep the default operating lane shared across Codex and Claude Code: repo-root guidance, the repo-local launcher, truthful `odylith ... --help`, and the grounded governance workflow should mean the same thing on both hosts. Add host-specific tips only when the host exposes a real native capability that materially reduces hops.
- In Codex commentary, keep startup, fallback, routing, and packet-selection internals implicit. Describe progress in task terms like the exact file/workstream, the bug under test, or the validation in flight. If an earlier repo-local start attempt degraded but work can continue safely, do not narrate that history. Do not surface routine `odylith start`, `odylith context`, or `odylith query` commands in progress updates, and never prefix commentary with control-plane receipt labels. Mention Odylith during the work only when the user explicitly asks for the command, a real blocker requires it, or a consumer-versus-maintainer lane distinction matters.
- Keep normal commentary task-first and human. Weave Odylith-grounded facts into ordinary updates when they change the next move, and reserve explicit `Odylith Insight:`, `Odylith History:`, or `Odylith Risks:` labels for rare high-signal moments. Pick the strongest one or stay quiet.
- Treat live teaser, `**Odylith Observation**`, and `Odylith Proposal` as the
  intervention-engine fast path. Treat `Odylith Assist:` as the chatter-owned
  closeout. Do not collapse those two layers into one ad hoc narration path.
- When the shared conversation-observation runtime earns a full
  `**Odylith Observation**` or `**Odylith Proposal**`, preserve those exact
  labels, keep the markdown warm and human, and keep the moment rooted in the
  original user prompt rather than Odylith's own pending/applied summary
  strings.
- Preserve the shipped shape too: Observation should look like
  `Odylith Assist`, which means one short labeled line. Proposal should be a
  short ruled block with the heading, a couple of lines, a few bullets, and
  the confirmation line.
- Keep one stable intervention identity across teaser, Observation, and
  Proposal for the same session-local moment. Later hooks may add evidence or
  surface the first eligible Proposal, but they must not make the same moment
  feel like a fresh branded interruption.
- For Codex and Claude checkpoint hooks, keep the full Observation,
  Proposal, and Assist bundle in hidden developer context for continuity, but
  surface the earned Observation/Proposal beat visibly at the hook moment.
  Stop is the fallback closeout lane, not the primary intervention moment.
- If you need to show that UX to a human in-chat, prefer rendered Markdown or
  plain prose. Do not wrap the product moment in fenced raw Markdown unless
  the task is explicitly about debugging the raw source text.
- At closeout, you may add at most one short `Odylith Assist:` line if it helps the user understand what Odylith materially contributed. Prefer `**Odylith Assist:**` when Markdown formatting is available; otherwise use `Odylith Assist:`. Lead with the user win, link updated governance ids inline when they were actually changed, and frame the edge against `odylith_off` or the broader unguided path when the evidence supports it. Keep it crisp, authentic, clear, simple, insightful, erudite in thought, soulful, friendly, free-flowing, human, and factual. Ground the line in concrete observed counts, measured deltas, or validation outcomes. Humor is fine only when the evidence makes it genuinely funny. Silence is better than filler. At most one supplemental closeout line may appear, chosen from `Odylith Risks:`, `Odylith Insight:`, or `Odylith History:` when the signal is real.
- For substantive tasks, follow this workflow check in order: read the nearest `AGENTS.md`; run the repo-local `odylith start`/`odylith context` step; identify the active workstream, component, or packet; then move into repo scan, tests, and edits.
- In consumer repos, grounding Odylith is diagnosis authority, not blanket write authority: if the issue target is Odylith itself, stop at diagnosis and maintainer-ready feedback unless the operator explicitly authorizes Odylith mutation.
- Treat `odylith upgrade`, `odylith reinstall`, `odylith doctor --repair`, `odylith sync`, and `odylith dashboard refresh` as writes when they change `odylith/` or `.odylith/`; do not run them autonomously as Odylith fixes in consumer repos.
- Treat backlog/workstream, plan, Registry, Atlas, Casebook, Compass, and session upkeep as part of the same grounded Odylith workflow; search existing workstream, plan, bug, component, diagram, and recent session/Compass context first, extend or reopen existing truth when present, and create new governed records only when the slice is genuinely new.
- Queued backlog items, case queues, and shell or Compass queue previews are not implicit implementation instructions. Unless the user explicitly asks to work a queued item, do not pick it up automatically just because it appears in Radar, Compass, the shell, or another Odylith queue surface.
- If the slice expands beyond one truthful record, use child workstreams or execution waves instead of flattening everything into one note, and carry forward intent, constraints, and validation obligations through Odylith session/context packets and Compass updates so repo context compounds over time.
- `./.odylith/bin/odylith` chooses how Odylith runs; it does not decide which repo files the agent may edit, and target-repo code still validates on the target repo's own toolchain.
- Before diagnosing install, upgrade, rollback, or launcher state, run `./.odylith/bin/odylith version --repo-root .` when the launcher exists and treat that live posture as authoritative over older Compass, shell, or release-history context.
- If the launcher is missing, confirm that from the filesystem first and use Odylith's current repair contract instead of assuming the repo is on a legacy consumer path.
- In Codex, treat Odylith-routed native subagent spawn as the default execution path for substantive grounded work across the consumer lane and the Odylith product repo's maintainer mode, including pinned dogfood and detached `source-local` maintainer-dev posture, unless Odylith explicitly keeps the slice local.
- Codex and Claude Code are both validated Odylith delegation hosts under the same grounding, routing, and validation contract. Codex executes routed leaves through `spawn_agent`; Claude Code executes the same bounded delegation contract through Task-tool subagents and the checked-in `.claude/` project assets.
- Repo-root guidance in this file remains authoritative for paths outside `odylith/`.
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
- For this repository, `freedom-research` is the sole canonical contributor
  identity.
- Repo-managed metadata, notices, docs, ownership files, release
  configuration, and generated governance surfaces must attribute repo
  contribution to `freedom-research` only.
- Do not introduce personal names, alternate handles, or additional
  contributor identities in tracked files unless quoting immutable third-party
  or historical material that cannot be rewritten.
- When configuring local Git for this repo, use the `freedom-research`
  identity.
- Git commit messages count as repo metadata under this rule. Do not add
  `Co-Authored-By:` (or any other trailer) for Claude, Claude Code,
  Anthropic, Codex, OpenAI, "Generated with ...", "Made with ...",
  ChatGPT, Cursor, Windsurf, Copilot, or any other coding-assistant or
  model identity. Commit messages must end with the body content and
  nothing else. The contributor on every commit is `freedom-research`,
  and assistant attribution does not belong in tracked git history.
- This rule applies to commits authored interactively, commits authored
  through any AI coding assistant (Claude Code, Codex, Cursor, Aider,
  etc.), and commits generated by automation in this repository. If an
  assistant tool default would add such a trailer, override that default
  for this repository before creating the commit.

## Source File Size Discipline
- This source-file size policy is non-negotiable in the Odylith product repo.
- For hand-maintained source files in this repo, `800` LOC is the soft limit.
- Do not push a hand-maintained source file past `1200` LOC without an
  explicit exception and a decomposition plan.
- Any hand-maintained source file over `1200` LOC must have a documented
  refactor plan before more unrelated feature growth lands in it.
- `2000+` LOC is red-zone exception only; any hand-maintained source file over
  `2000` LOC must have an active decomposition workstream before more feature
  work lands in it.
- Tests have a higher ceiling of `1500` LOC.
- When a hand-maintained source file is already beyond these thresholds, the
  default response is refactor-first work: decompose it into multiple focused
  files or modules with robustness, reliability, and reusability as explicit
  design goals instead of continuing to grow the oversized file in place.
- Generated or mirrored bundle assets are excluded; govern their
  source-of-truth files instead.
- Prefer `1-2` file refactors per PR with characterization tests first.
- Prioritize refactor waves by size x churn x centrality, not size alone, and
  do not launch repo-wide "all files above X" rewrites as the default policy.

## Change Hygiene
- Keep product docs and bundle docs aligned when the product contract changes.
- Keep install paths fixed: `odylith/` for installed product files and `.odylith/` for mutable runtime state.
- Avoid host-repo-specific fallback logic in public docs and guidance.
