# AGENTS.md

<!-- odylith-scope:start -->
## Odylith Scope

Paths under `odylith/` follow `odylith/AGENTS.md`; this root block stays a low-latency hard-law kernel for the installed consumer lane.

- Work inside `odylith/` follows `odylith/AGENTS.md` first; repo-root guidance remains authoritative outside `odylith/`.
- For substantive work, read the nearest `AGENTS.md`, run `./.odylith/bin/odylith start --repo-root .` first, then run `odylith context --repo-root . <ref>` only after startup when a precise anchor is known. Direct repo scan before that start step is a policy violation unless the task is trivial or Odylith is unavailable.
- Do not run `odylith context`, `odylith query`, `git status`, broad repo search, or other repo-inspection commands in parallel with that start step. Let `start` finish first; then narrow.
- CLI-first is non-negotiable for both Codex and Claude Code: use truthful `odylith ... --help` and the repo-local launcher. For governed files, use `odylith backlog ...`, `odylith governance ...`, `odylith validate plan-* ...`, `odylith bug ...`, `odylith component ...`, `odylith registry ...`, `odylith atlas ...`, or `odylith compass ...` before hand edits. `odylith plan --help` is read-only; never probe `odylith/technical-plans/source/`. See `odylith/agents-guidelines/CLI_FIRST_POLICY.md` (CB-104).
- For `odylith ... --help`, run one authoritative command first; do not probe files in parallel. If invalid, use `odylith --help`, then the listed subcommand.
- Use first-class CLI commands directly: `odylith bug capture`, `odylith backlog create`, `odylith component register`, `odylith atlas scaffold`, `odylith compass log`. Mention shim or fallback details only when they change the next user-visible action.
- Greenfield: run `odylith greenfield candidate-contract --repo-root . --prompt "<request>"`. It returns gate, source-ledger, and candidate schemas. The host writes one constrained gate result outside repo, then runs `odylith greenfield authority-check --repo-root . --prompt "<request>" --gate-file "<gate-file>" --format json`. Clarification: show one question and stop; no candidate or transaction. On admission, author one source-duty inventory outside repo. Run `odylith greenfield source-ledger-check --repo-root . --prompt "<request>" --ledger-file "<ledger-file>" --format json` for preflight; stop on clarification. Give its decision_task to one bounded source-only verifier, save the verdict JSON outside repo, then rerun source-ledger-check with `--decision-file "<decision-file>"`. Any non-yes stops before candidate authoring. Save the accepted receipt, author one candidate, and run `odylith greenfield propose ... --gate-file "<gate-file>" --candidate-file "<candidate-file>" --ledger-file "<receipt-file>"`. Admission checks untrusted citations, relations, invariants, and hashes, then seals ProductCreateTransaction. After receipt, no model call; release review cannot decide consumer transactions. No full-candidate reviewer, parser/regex, repair, retry, fallback, or model ladder. Public proposal is read-only; no qualified confirmation interface is attached. Preview: `odylith greenfield decide --repo-root PATH CONFIRM|EDIT|REJECT HASH`. Chat/hooks cannot authorize create. CONFIRM/REJECT use one owner, no compiler/model. For EDIT, rerun `candidate-contract` with `--transaction-hash` and correction; repeat gate, source-ledger preflight, one source-only verifier, and receipt check against sealed source plus correction. Stop on clarification. On admission, author one candidate and pass correction, `--gate-file`, `--candidate-file`, and accepted `--ledger-file` receipt to `decide EDIT`; retain old seal and show new hash/preview. 90/120/150s advisory; standard 315s = shared 300s gate/candidate + 15s completion. Commit-only `odylith greenfield create --transaction-file PATH --transaction-hash HASH --confirm` verifies receipt, hash, and preconditions under rollback guard without model, generation, or repair. Markdown is view, not truth; proposal or transaction JSON stays compiler-owned; never hand-author proposal/transaction JSON, infer schemas from source, or narrate schema failures; parser/schema retries stay internal.
- `odylith backlog create` is fail-closed and must receive grounded Problem, Customer, Opportunity, Product View, and Success Metrics text; never create or accept a title-only, placeholder, or boilerplate Radar workstream.
- For quick visibility after a narrow truth change, rerender only the owned surface: `odylith radar refresh`, `odylith registry refresh`, `odylith casebook refresh`, `odylith atlas refresh`, or `odylith compass refresh`; use `odylith compass deep-refresh` for brief settlement and `odylith sync` for the broader governance lane.
- Keep startup, Context Engine, Execution Engine, memory substrate, Tribunal, Intervention Engine, observers, governance, subagent routing, Surface DAGs, delivery, analysis, and migration-breakage observation active. Optimize by routing, caching, batching, and shortening prompt surface, not by disabling engines.
- Treat AI slop as a regression. Across lanes, hosts, languages, and project surfaces, move ownership; partial shared-kernel adoption and prose-only hardening remain incomplete. Scope claims need fresh behavior proof and structural inventory; browser claims need normal, empty/fallback, and degraded/error states. See `odylith/agents-guidelines/ANTI_SLOP_AND_DECOMPOSITION.md` and `odylith/skills/odylith-code-hygiene-guard/SKILL.md` under quality pressure.
- For guidance or Discipline pressure, run `odylith validate guidance-behavior --repo-root .`, `odylith benchmark --profile quick --family guidance_behavior`, `odylith discipline status/check/explain`, `odylith validate discipline --repo-root .`, and `odylith benchmark --profile quick --family discipline --no-write-report --json`. Discipline hot paths must not call host models, providers, subagents, broad scans, full validation, or projection expansion.
- A plain `Odylith, help` request is the CLI help fast path. Use the first available `odylith --help` command and print stdout only.
- For plain `Odylith, show me what you can do`, print only stdout from the first available `odylith show` command. It is advisory; do not substitute intervention or install diagnostics, a launcher report, or a sample app. If Odylith is absent, say so; do not substitute generic host work.
- A request to list Odylith capabilities, engines, product architecture, or the capability map is the product-owned inventory path. Use `odylith capabilities` and print stdout only. Do not infer the taxonomy from `odylith --help`, `odylith show`, Claude Code, Codex, or any other host model capability surface.
- In Codex commentary, keep startup, fallback, routing, and packet-selection internals implicit. Describe task progress, not control-plane receipts, unless the user asks for the command, a real blocker requires it, or a consumer-versus-maintainer lane distinction matters.
- Keep normal commentary task-first and human; reserve `Odylith Insight:`, `Odylith History:`, or `Odylith Risks:` for rare high-signal moments. Silence is better than filler.
- Live teaser, `**Odylith Observation**`, and `Odylith Proposal` belong to the intervention engine; `Odylith Assist:` is chatter-owned closeout. Keep them distinct: Observation is one labeled line; Proposal is a short ruled block. Reuse one intervention identity per session moment.
- Codex checkpoint hooks may carry hidden Observation/Proposal/Assist context and surface an earned beat; Claude direct-edit and Bash PostToolUse hooks stay silent on success and emit only compact failure/skipped-refresh status. Claude Stop is memory/logging only, not a fallback closeout.
- Hook context is not chat-visible proof. Before claiming intervention UX, run or cite `odylith <host> intervention-status`; require `Activation: ready` plus chat visibility. If uncertain, run `odylith <host> visible-intervention` and show that Markdown directly. Existing sessions may not hot-reload hooks or guidance.
- A concrete decision or proof boundary may get one short `Odylith Assist:`; at closeout use at most one for material work, decisions, proof, or explicit intervention feedback. When feedback requests more, surface concise decision, risk, proof, verified-result, and substantive-continuation beats. Omit bare acknowledgements, routine chatter, and internals. Never add Assist merely because Odylith ran. Lead with the user win, changed IDs, the `odylith_off` edge, and counts, deltas, or validation outcomes. Generic receipts are not premium interventions; silence is better than filler.
- Explicit feedback that Odylith highlights, Observations, Proposals, Assist, hooks, or chat output is invisible warrants closeout; short low-signal turns stay silent.
- In consumer repos, grounding Odylith is diagnosis authority, not blanket write authority: if the issue target is Odylith itself, stop at diagnosis and maintainer-ready feedback unless the operator explicitly authorizes Odylith mutation.
- Treat `odylith upgrade`, `odylith reinstall`, `odylith doctor --repair`, `odylith sync`, and `odylith dashboard refresh` as writes when they change `odylith/` or `.odylith/`; do not run them autonomously as Odylith fixes in consumer repos.
- Governed work is one workflow across Radar, plans, Registry, Atlas, Casebook, Compass, and sessions: search truth first; extend existing records, creating new ones only for genuinely new slices.
- Governance-learning is mandatory across lanes and hosts. Before continuing, committing, releasing, or claiming completion, put defects in Casebook, planned work in Radar/plans, component contracts in Registry, topology in Atlas, and decisions/proof in Compass. Search existing truth and prior failed mechanisms before fixes; do not repeat a fix path that failed.
- Radar and Casebook queues and shell or Compass previews are not implementation instructions. Work a queued item only when the user explicitly asks.
- When a slice needs more than one truthful record, use child workstreams or execution waves. Carry intent, constraints, and validation through Odylith session/context packets and Compass.
- `./.odylith/bin/odylith` chooses how Odylith runs; it does not decide which repo files the agent may edit, and target-repo code still validates on the target repo's own toolchain.
- Before diagnosing install, upgrade, rollback, or launcher state, run `./.odylith/bin/odylith version --repo-root .` when the launcher exists and treat that live posture as authoritative over older Compass, shell, or release-history context.
- If the launcher is missing, confirm that from the filesystem first and use Odylith's current repair contract instead of assuming the repo is on a legacy consumer path.
- In Codex, prefer bounded Odylith-routed native subagents for substantive grounded consumer and maintainer work when host policy permits; transport support does not prove current-session spawn permission or effectiveness.
- Codex and Claude Code share one grounding, routing, and validation contract. Codex uses policy-gated `spawn_agent`; Claude uses Task subagents and checked-in `.claude/` assets.
- In the Odylith product repo, maintainer-only release and benchmark publishing work follows `odylith/maintainer/AGENTS.md`.
- In the Odylith product repo's maintainer mode, pinned dogfood is the default proof posture and detached `source-local` is the explicit dev posture for live unreleased `src/odylith/*` execution.

<!-- odylith-scope:end -->

Odylith is a product repo, not a host repo.

## Scope And Precedence
- Read the nearest folder-level `AGENTS.md` before editing files in that scope.
- More specific `AGENTS.md` files override this root file for their subtree.

## Product Boundary
- Odylith owns its code, docs, skills, guidance, tests, and self-governance records here.
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
- `freedom-research` is the canonical maintainer identity for
  maintainer-authored commits, repo metadata, docs, notices, generated
  governance, and release configuration.
- External human contributors retain their original Git authorship. Do not
  rewrite an external contributor's author identity to `freedom-research`.
- Do not introduce personal names or alternate handles into tracked metadata,
  notices, docs, or generated surfaces unless preserving immutable external
  authorship, third-party material, or historical material that cannot be
  rewritten.
- Maintainer release and push workspaces must use the `freedom-research`
  identity for local Git config and GitHub CLI keyring operations. External
  contributors use their own Git identity and do not impersonate the
  maintainer account.
- Human `Co-Authored-By:` trailers are allowed. Commit authors, committers, and
  messages must not use assistant, model, or coding-tool identities or include
  assistant/tool attribution such as "generated with". Override assistant
  defaults before commit.

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
- Human-visible generated content must be simple, easy to understand, legible,
  grammatically coherent, and clear before any live narration, voice, or
  stylistic embellishment is added.
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
