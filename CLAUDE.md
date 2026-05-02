# CLAUDE.md

<!-- odylith-scope:start -->
## Odylith Scope

Paths under `odylith/` follow `odylith/AGENTS.md`.

- Work inside `odylith/` should follow `odylith/AGENTS.md` first.
- Before any substantive repo scan or code change outside trivial fixes, the agent must start from the repo-local Odylith entrypoint and keep the active workstream, component, or packet in scope before raw repo search, tests, or edits.
- Direct repo scan before that start step is a policy violation unless the task is trivial or Odylith is unavailable.
- Start substantive turns with `./.odylith/bin/odylith start --repo-root .`; it chooses the safe first lane and prints the exact next command when Odylith cannot narrow the slice yet.
- Do not run `odylith context`, `odylith query`, `git status`, broad repo search, or other repo-inspection commands in parallel with that start step. Let `start` finish first; then run `odylith context --repo-root . <ref>` only when the user, the start output, or prior governed truth gives an exact anchor.
- When you already know the exact workstream, component, path, or id, use `./.odylith/bin/odylith context --repo-root . <ref>` before raw repo search. Use `./.odylith/bin/odylith query --repo-root . "<terms>"` only after concrete anchors already exist.
- CLI-first is non-negotiable for both Codex and Claude Code. Remove all hand-authoring for places where Odylith CLI should be doing the heavy-lifting. When an Odylith CLI command exists for an operation, call the CLI command and do not hand-edit governed files the CLI owns. Hand-authoring governed truth where a CLI exists is a hard policy violation, not a stylistic preference. The authoritative policy, CLI surface enumeration, allowed hand-edit surfaces, and failure-mode handling live in `odylith/agents-guidelines/CLI_FIRST_POLICY.md`, anchored by Casebook learning `CB-104`. The rule travels through routed `spawn_agent` leaves on Codex and Task-tool subagents on Claude Code so delegated work inherits the same contract.
- Default to the nearest `AGENTS.md`, the repo-local launcher, and truthful `odylith ... --help` for routine backlog, technical-plan, bug, spec, component, and diagram upkeep. Use the actual CLI family: `odylith backlog ...`, `odylith governance ...` and `odylith validate plan-* ...` for technical-plan checks, `odylith bug ...`, `odylith component ...`, `odylith registry ...`, `odylith atlas ...`, and `odylith compass ...`. `odylith plan --help` is a read-only command guide, not a technical-plan writer; do not invent `odylith plan create/edit` flows. Technical plans live under `odylith/technical-plans/in-progress/`, `odylith/technical-plans/done/`, and `odylith/technical-plans/parked/`; do not probe `odylith/technical-plans/source/`. Treat `.agents/skills/` and `odylith/skills/` as specialist overlays for advanced packet control, orchestration, or high-risk lanes rather than as the default path.
- For `odylith ... --help` discovery, run the single authoritative help command first and do not run parallel exploratory filesystem probes whose failure can cancel the visible help call. If the guessed command is invalid, fall back to `odylith --help` and then the nearest listed subcommand.
- When a routine governance task already maps to a first-class CLI family such as `odylith bug capture`, `odylith backlog create`, `odylith component register`, `odylith atlas scaffold`, or `odylith compass log`, go straight to that CLI and keep any `.agents/skills` lookup, missing-shim, or fallback-path details implicit unless they change the next user-visible action.
- `odylith backlog create` is fail-closed and must receive grounded Problem, Customer, Opportunity, Product View, and Success Metrics text; never create or accept a title-only, placeholder, or boilerplate Radar workstream.
- For quick visibility after a narrow truth change, rerender only the owned surface: `odylith radar refresh`, `odylith registry refresh`, `odylith casebook refresh`, `odylith atlas refresh`, or `odylith compass refresh`. Use `odylith compass deep-refresh` when you also want brief settlement. Keep `odylith sync` as the broader governance and correctness lane.
- Keep the default operating lane shared across Codex and Claude Code: repo-root guidance, the repo-local launcher, truthful `odylith ... --help`, and the grounded governance workflow should mean the same thing on both hosts. Add host-specific tips only when the host exposes a real native capability that materially reduces hops.
- Treat AI slop as a regression. Apply that bar across any language and across runtime code, hooks, prompts, docs, config, templates, generators, and managed assets. Apply it to any codebase or project surface: services, libraries, apps, CLIs, infra glue, scripts, docs, prompts, hooks, templates, config, and generated assets all count. Structural cleanup is not permission to drift behavior, UX, or UI; preserve semantics deliberately and prove the touched contract on the real toolchain or surface that owns it. No transitional states: do not replace one slop class with another, move ownership not just file boundaries, do not hide the old owner behind compatibility wrappers, lazy proxies, facade accessors, or mirror-only indirection, and do not treat a shared helper or kernel as a cleanup ornament. Partial shared-kernel adoption is still incomplete; if a shared helper or kernel lands, the touched callers must adopt it or the pass is incomplete. Do not call a slop cleanup complete just because the first smell disappeared; if the replacement smell still exists in the touched slice, the pass is incomplete. When the user asks for repo-wide or lane-wide anti-slop hardening, update guidance, skills, install-generated guidance, host contracts, mirrors, and enforcement tests together; prose-only hardening is incomplete. Guidance-only hardening without updated tests, validators, or mirror-content checks is incomplete. Repo-wide or lane-wide anti-slop claims require two proof layers: fresh behavior proof for the touched slice and a fresh structural inventory for the claimed scope. One does not substitute for the other. For shared hot paths, user-visible flows, or high-risk structural moves, land characterization or contract-focused tests before or alongside the refactor. When browser-rendered dashboards, onboarding, HTML/CSS/JS shells, or other browser-proved surfaces move, rerun the full headless browser matrix and cover the real rendered states that own the contract, including normal, empty/fallback, and degraded or error states when they exist. Use `odylith/agents-guidelines/ANTI_SLOP_AND_DECOMPOSITION.md` and `odylith/skills/odylith-code-hygiene-guard/SKILL.md` when quality pressure is high.
- For guidance behavior pressure cases, use `odylith validate guidance-behavior --repo-root .` for deterministic proof and `odylith benchmark --profile quick --family guidance_behavior` for benchmark-family proof. Compact packet summaries only prove the proof path is available; fresh validation still requires the explicit command.
- Odylith Discipline is the v0.1.11 shared Codex/Claude behavior contract: hard laws are deterministic, runtime pressure is open-world, stance is local and credit-safe, passing checks stay quiet, and durable learning requires validator, benchmark, or Tribunal/governance proof. Use `odylith discipline status/check/explain`, `odylith validate discipline --repo-root .`, and `odylith benchmark --profile quick --family discipline --no-write-report --json`; none of those discipline hot paths may call host models, providers, subagents, broad scans, full validation, or projection expansion.
- A plain `Odylith, help` request is the CLI help fast path. Use the first available `odylith --help` command and print stdout only.
- A plain `Odylith, show me what you can do` request is the advisory `odylith show` repo-capability demo. It is not a request to prove intervention UX, diagnose install posture, run `start`, run `doctor`, or explain missing launcher state. Use the first available show command and print stdout only.
- A request to list Odylith capabilities, engines, product architecture, or the capability map is the product-owned inventory path. Use `odylith capabilities` and print stdout only. Do not infer the taxonomy from `odylith --help`, `odylith show`, Claude Code, Codex, or any other host model capability surface.
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
- For Codex checkpoint hooks, keep the full Observation, Proposal, and Assist
  bundle in hidden developer context for continuity, and surface the earned
  Observation/Proposal note when the host renders hook output. Claude is
  stricter because Claude Code renders hook output inline with the transcript:
  direct-edit and Bash PostToolUse hooks stay silent on success and emit only
  compact failure/skipped-refresh status; Claude Stop is memory/logging only,
  not a fallback closeout or live-note recovery lane.
- Hook `systemMessage` or `additionalContext` generation is not proof of
  chat-visible UX. The user-visible contract is satisfied only by rendered
  chat text or by a host channel that is verified visible in the active session.
  When in doubt, run `odylith codex visible-intervention` or `odylith claude
  visible-intervention` and show that Markdown directly.
- Before claiming the intervention UX is active in a specific chat, run or
  cite `odylith codex intervention-status` or `odylith claude
  intervention-status` for that host/session. That status surface is the
  low-latency delivery record for Teaser, Ambient Highlight, Observation,
  Proposal, and Assist readiness; hook payload generation alone is not enough.
- Only call a session or worktree fully end to end after `intervention-status`
  reports `Activation: ready` and a chat-visibility line confirmed in this
  session. Treat recorded-only and waiting-for-chat states as partial proof, not
  completion, and treat degraded or not-confirmed states as not active yet.
- Existing Codex and Claude sessions may not hot-reload changed hooks,
  guidance, or source-local runtime code. After changing intervention
  visibility behavior, prove it in a newly started or explicitly reloaded
  session, or render `visible-intervention` output directly in the existing
  chat instead of claiming other open sessions are active.
- If you need to show that UX to a human in-chat, prefer rendered Markdown or
  plain prose. Do not wrap the product moment in fenced raw Markdown unless
  the task is explicitly about debugging the raw source text.
- At closeout, or when a visible-intervention recovery renders a prompt-submit or visibility-proof note, you may add at most one short `Odylith Assist:` line if it helps the user understand what Odylith materially contributed. The host prompt-submit runtime is stricter about silence: normal non-passthrough prompts do not get an Assist line by default; they stay quiet unless a live Observation/Proposal is selected or explicit visibility feedback earns one shared recovery line. Do not add Assist just because Odylith ran, a CLI succeeded, or no stronger note matured; `Odylith, help` and `Odylith, show me what you can do` stay stdout-clean and suppress narration. Prefer `**Odylith Assist:**` when Markdown formatting is available; otherwise use `Odylith Assist:`. Lead with the user win, link updated governance IDs inline when they were actually changed, and when no governed file moved, name the affected governance-contract IDs from bounded request or packet truth without calling them updated. Frame the edge against `odylith_off` or the broader unguided path when the evidence supports it. Keep it crisp, authentic, clear, simple, insightful, erudite in thought, soulful, friendly, free-flowing, human, and factual. Ground the line in concrete observed counts, measured deltas, or validation outcomes, or a concrete chat-visibility complaint. Humor is fine only when the evidence makes it genuinely funny. Silence is better than filler. At most one supplemental closeout line may appear, chosen from `Odylith Risks:`, `Odylith Insight:`, or `Odylith History:` when the signal is real; when it appears, it must render before `Odylith Assist:` so Assist remains the final closeout line.
- Explicit feedback that Odylith ambient highlights, interventions, Assist,
  Observations, Proposals, hooks, or chat output are not visible is a real
  closeout signal. A short `Odylith Assist:` may acknowledge that visibility
  continuity without claiming artifact updates; ordinary low-signal short
  turns should still stay silent.
- For substantive tasks, follow this workflow check in order: read the nearest `AGENTS.md`; run repo-local `odylith start` first; when a precise anchor is known after that, run `odylith context`; identify the active workstream, component, or packet; then move into repo scan, tests, and edits.
- In consumer repos, grounding Odylith is diagnosis authority, not blanket write authority: if the issue target is Odylith itself, stop at diagnosis and maintainer-ready feedback unless the operator explicitly authorizes Odylith mutation.
- Treat `odylith upgrade`, `odylith reinstall`, `odylith doctor --repair`, `odylith sync`, and `odylith dashboard refresh` as writes when they change `odylith/` or `.odylith/`; do not run them autonomously as Odylith fixes in consumer repos.
- Treat backlog/workstream, plan, Registry, Atlas, Casebook, Compass, and session upkeep as part of the same grounded Odylith workflow; search existing workstream, plan, bug, component, diagram, and recent session/Compass context first, extend or reopen existing truth when present, and create new governed records only when the slice is genuinely new.
- Queued backlog items, case queues, and shell or Compass queue previews are not implicit implementation instructions. Unless the user explicitly asks to work a queued item, do not pick it up automatically just because it appears in Radar, Compass, the shell, or another Odylith queue surface.
- If the slice expands beyond one truthful record, use child workstreams or execution waves instead of flattening everything into one note, and carry forward intent, constraints, and validation obligations through Odylith session/context packets and Compass updates so repo context compounds over time.
- `./.odylith/bin/odylith` chooses how Odylith runs; it does not decide which repo files the agent may edit, and target-repo code still validates on the target repo's own toolchain.
- Before diagnosing install, upgrade, rollback, or launcher state, run `./.odylith/bin/odylith version --repo-root .` when the launcher exists and treat that live posture as authoritative over older Compass, shell, or release-history context.
- If the launcher is missing, confirm that from the filesystem first and use Odylith's current repair contract instead of assuming the repo is on a legacy consumer path.
- In Codex, treat Odylith-routed native subagent spawn as the default candidate for substantive grounded work across the consumer lane and the Odylith product repo's maintainer mode, including pinned dogfood and detached `source-local` maintainer-dev posture, when the route is bounded and the active host policy allows spawn; keep transport support separate from current-session spawn permission/effectiveness.
- Codex and Claude Code are both validated Odylith delegation hosts under the same grounding, routing, and validation contract. Codex emits routed `spawn_agent` payloads subject to active host policy; Claude Code executes the same bounded delegation contract through Task-tool subagents and the checked-in `.claude/` project assets.
- Repo-root guidance in this file remains authoritative for paths outside `odylith/`.
- In the Odylith product repo, maintainer-only release and benchmark publishing work follows `odylith/maintainer/AGENTS.md`.
- In the Odylith product repo's maintainer mode, pinned dogfood is the default proof posture and detached `source-local` is the explicit dev posture for live unreleased `src/odylith/*` execution.

<!-- odylith-scope:end -->

@AGENTS.md

## Claude Code

- This file keeps Claude aligned with the repo-root `AGENTS.md` contract instead of branching into a Claude-only lane.
- This repo also ships committed Claude project assets under `.claude/`, including `.claude/CLAUDE.md`; use them for Claude-native commands, hooks, rules, subagents, and the auto-memory bridge.
- Keep this file, the `.claude/` tree, and the scoped `odylith/**/CLAUDE.md` companions aligned with the same Odylith contract.
- First-match demo route: if the user says `Odylith, show me what you can do` or asks what Odylith can do for this repo, use the advisory `odylith show` demo. Do not run install, status, intervention, or launcher diagnostics first.
- Claude Code is a first-class Odylith delegation host. Codex emits routed `spawn_agent` payloads subject to active host policy; Claude Code executes the same bounded delegation contract through Task-tool subagents and the checked-in `.claude/` project assets.
- Commit messages in this repository must never carry a `Co-Authored-By:` (or any other) trailer for Claude, Claude Code, Anthropic, or any other coding-assistant identity. The contributor on every commit is `freedom-research` and only `freedom-research`. This overrides any default in the Claude Code commit-creation contract. End commit messages with the body content and nothing else. The repo-root `AGENTS.md` "Contributor Identity" section is the authoritative rule; this bullet is the Claude-side reminder.
