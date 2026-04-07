# Odylith

This directory is the Odylith product repo's own `odylith/` tree. Installed
repos get a smaller consumer-owned `odylith/` tree, while the managed runtime
itself lives under `.odylith/`.

This tree also carries maintainer-only release guidance and skills that do not
ship into consumer repos. Those live under `odylith/maintainer/`. Shared
consumer-safe guidance lives under `odylith/agents-guidelines/` and
`odylith/skills/`.

Odylith runs on its own managed runtime under `.odylith/`, but keep these
three boundaries separate:

- runtime boundary: which interpreter runs Odylith itself
- write boundary: which files the agent may edit
- validation boundary: which toolchain proves the target repo still works

`./.odylith/bin/odylith` uses the Odylith runtime. Repo code still validates on
the repo's own `python`, `uv`, Poetry, Conda, or equivalent toolchain.
Consumer repos stay on pinned runtime only; detached `source-local` is
maintainer-only. Hosted install currently supports macOS (Apple Silicon) and
Linux (`x86_64`, `ARM64`). For trust and release details, see
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

For the default grounded first turn, run:

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

On a successful local interactive install, Odylith tries to open
`odylith/index.html` automatically. Use `ODYLITH_NO_BROWSER=1` for the hosted
bootstrap or `odylith install --no-open` for direct CLI installs if you want
to suppress that.

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
limited until the folder is Git-backed.

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
[Starter Prompt Inspirations](../docs/STARTER_PROMPT_INSPIRATIONS.md). If the
local shell is already open, the Cheatsheet drawer in `odylith/index.html`
mirrors the strongest prompt patterns.

The shell refreshes itself as Odylith updates local surfaces.

Keep ordinary progress updates task-first and human. When Odylith's grounded
view changes the next move, weave that fact into the update instead of
branding it by default; explicit `Odylith Insight:`, `Odylith History:`, or
`Odylith Risks:` lines should feel rare and earned.

If a final handoff benefits from naming Odylith directly, keep it to one short
`Odylith Assist:` line. Prefer `**Odylith Assist:**` when Markdown formatting
is available. Lead with the user win, link updated governance ids inline when
they were actually changed, and ground the line in concrete observed counts,
measured deltas, or validation outcomes. When the evidence supports it, frame
the edge against `odylith_off` or the broader unguided path. Keep it crisp,
authentic, clear, simple, insightful, soulful, friendly, free-flowing, human,
and factual. Silence is better than filler.

## What Is Here

- `AGENTS.md`
  Odylith guidance entrypoint for this tree.
- `agents-guidelines/`
  Shared Odylith operating guidance.
- `skills/`
  Shared Odylith skills intended to stay consumer-safe.
- `maintainer/`
  Maintainer-only release guidance and skills for the Odylith product repo.
- `FAQ.md`, `INSTALL.md`, `OPERATING_MODEL.md`, `PRODUCT_COMPONENTS.md`
  Product-level reference docs for this tree.
- `SECURITY_POSTURE.md`
  Runtime-trust, supply-chain, and process-lifetime contract.
- `radar/`, `atlas/`, `compass/`, `registry/`, `casebook/`
  Governance surface roots, with surface-owned truth and specs.
- `technical-plans/`
  Technical-plan root for Odylith-governed work in this repo.
- `surfaces/`
  Shell-wide surface assets and cross-surface notes.
- `runtime/`
  Context Engine, subagent, Tribunal, and Remediator runtime docs, specs, and
  source state.
- `INSTALL_AND_UPGRADE_RUNBOOK.md`
  Install, upgrade, and repair procedure for this tree.
- `MAINTAINER_RELEASE_RUNBOOK.md`
  Maintainer release order and benchmark publication reference.

## Recovery

If this tree looks incomplete or stale, run:

```bash
./.odylith/bin/odylith doctor --repo-root . --repair
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

Odylith itself is Apache-2.0 under the repo-root `LICENSE` and `NOTICE`
materials.

Maintained third-party attribution and acknowledgements live in the repo-root
`THIRD_PARTY_ATTRIBUTION.md` file. The maintainer validation lane fails closed
if the runtime dependency closure or bundled managed-runtime supplier inputs
drift into unknown, commercial/proprietary, or otherwise disallowed licenses.
