# Odylith

This directory is the bundled Odylith reference tree shipped into installed
repos. First install bootstraps a consumer-owned `odylith/` tree, while the
managed runtime itself lives under `.odylith/`.

This bundled tree is consumer-facing. It ships the installed guidance, skills,
and reference surfaces for repo-local Odylith use.

Odylith runs on its own managed runtime under `.odylith/`, but that does not
change what files the agent may edit or which toolchain proves repo code. Keep
these boundaries explicit:

- runtime boundary: which interpreter runs Odylith
- write boundary: which files the agent may edit
- validation boundary: which toolchain proves the target repo still works

`./.odylith/bin/odylith` uses the Odylith runtime. Repo code still validates on
the repo's own `python`, `uv`, Poetry, Conda, or equivalent toolchain.
Consumer installs stay on the verified managed runtime described in this
bundle. Hosted install currently supports macOS (Apple Silicon) and Linux
(`x86_64`, `ARM64`). For runtime and release-trust details, see
`SECURITY_POSTURE.md`.

## First Run

After install, you should have:

- repo-local launcher at `./.odylith/bin/odylith`
- local Odylith shell at `odylith/index.html`
- managed starter tree under `odylith/`
- root `.gitignore` updated with `/.odylith/` when the repo is Git-backed
- gitignored managed-runtime trust anchors under
  `.odylith/trust/managed-runtime-trust/` when the repo is Git-backed

Odylith is not a standalone app or IDE. Use it through an AI coding agent such
as Codex or Claude Code. In Odylith, the agent is the execution interface and
`odylith/index.html` is the operating surface that keeps intent, constraints,
topology, and execution state visible.

For the normal first grounded turn, run:

```bash
./.odylith/bin/odylith start --repo-root .
```

When you already know the exact workstream, component, path, or id, use:

```bash
./.odylith/bin/odylith context --repo-root . <ref>
```

Once concrete nouns exist, use:

```bash
./.odylith/bin/odylith query --repo-root . "<text>"
```

On a successful first local install, Odylith tries to open
`odylith/index.html` automatically when the session is local and interactive.
Use `ODYLITH_NO_BROWSER=1` for the hosted bootstrap or `odylith install --no-open`
for direct CLI installs if you want to suppress that.

> [!CAUTION]
> **Odylith is designed to anchor to a git repo root.** If there is no
> enclosing `.git`, install still succeeds, but Odylith treats the current
> folder as the repo root, creates a root `AGENTS.md` there, and runs with
> reduced Git-aware behavior until that folder is backed by Git.

Before activation, the installer picks the install boundary like this:

- If it finds a root `AGENTS.md`, it uses that repo root.
- Otherwise, if it finds an enclosing `.git`, it uses that Git root and
  creates a root `AGENTS.md` there.
- Otherwise, it treats the current folder as the repo root and creates a root
  `AGENTS.md` in place.

If no `.git` exists yet, install still succeeds, but Git-aware features stay
limited until the folder is Git-backed. Today that mainly means working-tree
intelligence, background autospawn, and git-fsmonitor watcher help stay
reduced.

Starter prompt for your agent:

**Use Odylith to define this repo's first governed slice. Pick one path to own, one seam to guard, one component to define, one diagram to draw, and one backlog to open, all tied to the same slice. First show me 5 bullets. Then create the Odylith files. Plain English. Real file paths only. No IDs. No hedging. Only write under `odylith/`.**

Here are some starter prompt inspirations:

`Backlog`
- Create: "Create a new backlog item and queue it for [codepath {or} backlog item description]."
- Edit: "Tighten the Radar item for [B###]."
- Delete: "Drop the Radar item [B###]"

`Components`
- Create: "Define the Registry component for [component description]."
- Edit: "Tighten the Registry boundary for [component]."
- Delete: "Drop the Registry component for [component]"

`Diagrams`
- Create: "Draw the Atlas diagram for [codepath]."
- Edit: "Update the Atlas diagram for [codepath]."
- Delete: "Drop the Atlas diagram [D###]."

`Developer Notes`
- Create: "Add developer note [Note Brief]."
- Edit: "Update developer note [N###] with [...]."
- Delete: "Delete developer note [N###]."

For more prompt examples, see
[Starter Prompt Inspirations](../docs/STARTER_PROMPT_INSPIRATIONS.md).

If the local shell is already open, the Cheatsheet drawer in
`odylith/index.html` mirrors the strongest prompt patterns.

The shell refreshes itself as Odylith updates local surfaces.

If a final handoff benefits from naming Odylith directly, keep it to one short
`Odylith assist:` line. Prefer `**Odylith assist:**` when Markdown formatting
is available. Lead with the user win, not Odylith mechanics. When the evidence
supports it, frame the edge against `odylith_off` or the broader unguided
path. Keep it soulful, friendly, authentic, and factual. Use only concrete
observed counts, measured deltas, or validation outcomes.

## What Is Here

- `AGENTS.md`
  Odylith guidance entrypoint for this tree.
- `agents-guidelines/`
  Shared consumer-safe Odylith guidance for installed trees.
- `skills/`
  Bundled consumer-safe and shared Odylith skills.
- `FAQ.md`, `INSTALL.md`, `OPERATING_MODEL.md`, `PRODUCT_COMPONENTS.md`
  Product-level references that apply across this tree.
- `SECURITY_POSTURE.md`
  Runtime-trust, supply-chain, and process-lifetime contract.
- `radar/`, `atlas/`, `compass/`, `registry/`, `casebook/`
  Odylith governance surface roots, with surface-owned truth and specs.
- `technical-plans/`
  Technical-plan root shipped with the product reference tree.
- `surfaces/`
  Shell-wide surface assets and cross-surface notes.
- `runtime/`
  Context Engine, subagent, Tribunal, and Remediator runtime docs, specs, and
  source state.
- `INSTALL_AND_UPGRADE_RUNBOOK.md`
  Install, upgrade, and repair procedure for this tree.

## Recovery

If this tree looks incomplete or stale, run:

```bash
./.odylith/bin/odylith doctor --repo-root . --repair
```

If the main launcher is missing, use:

```bash
./.odylith/bin/odylith-bootstrap doctor --repo-root . --repair
```

If local cache or learned runtime state looks poisoned, run:

```bash
./.odylith/bin/odylith doctor --repo-root . --repair --reset-local-state
```

If you want Odylith temporarily off for coding agents without removing the
local runtime, run:

```bash
./.odylith/bin/odylith off --repo-root .
./.odylith/bin/odylith on --repo-root .
```

If you want to remove the runtime integration but keep this `odylith/` context
tree in place, run:

```bash
./.odylith/bin/odylith uninstall --repo-root .
```

If you need an older Compass day that aged out of the active window, restore
it from the compressed archive with:

```bash
./.odylith/bin/odylith compass restore-history --repo-root . --date YYYY-MM-DD
```

## License And Attribution

Odylith itself is Apache-2.0 under the product `LICENSE` and `NOTICE`
materials.

Maintained third-party attribution and acknowledgements live in
`THIRD_PARTY_ATTRIBUTION.md` in the official Odylith repository and source
distributions. Release validation in the Odylith source repo fails closed if
the runtime dependency closure or bundled managed-runtime supplier inputs
drift into unknown, commercial/proprietary, or otherwise disallowed licenses.
