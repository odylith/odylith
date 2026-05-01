# CLAUDE.md

@../AGENTS.md

## Claude Code

- This project-level Claude memory bridge exists for setups that prefer `.claude/CLAUDE.md` over the repo-root `CLAUDE.md`.
- Use `/odylith-start` to ground substantive work through the repo-local launcher before broad repo search.
- Use `/odylith-context` when you already know the exact workstream, component, path, or bug id.
- Use `/odylith-query` only after concrete anchors exist and you need narrow local search.
- Use `/odylith-sync-governance` when you need a manual governance refresh beyond the automatic post-edit hook.
- The SessionStart hook mirrors a compact Compass-derived brief into Claude's documented auto-memory directory under `projects/<project>/memory/`. Treat that note as fresh project memory, not as optional decoration.
- The SubagentStart hook injects the active Odylith slice into Claude subagents. Use project subagents when you want bounded leaves to inherit that grounding automatically.
- Claude-discoverable Odylith skills live under `.claude/skills/`; prefer those shims when you need the repo-owned Odylith playbooks to auto-load.
- When cleanup or decomposition pressure is high, Claude must enforce the same anti-slop contract as Codex. Route through `.claude/skills/odylith-code-hygiene-guard/SKILL.md` and keep `odylith/agents-guidelines/ANTI_SLOP_AND_DECOMPOSITION.md` in scope instead of treating hygiene as optional review commentary.
- First-match help route: if the user says `Odylith, help`, use the CLI help surface and print stdout only. Do not run install, status, intervention, launcher diagnostics, or parallel filesystem probes first.
- Help discovery rule: run the single authoritative `odylith ... --help` command first. If a guessed command is invalid, fall back to `odylith --help` and then the nearest listed subcommand; do not pair the help call with exploratory `ls`/`rg` commands that can cancel the visible help output. Technical-plan work uses `odylith governance ...` and `odylith validate plan-* ...`; `odylith plan --help` is only a read-only command guide and there is no `odylith/technical-plans/source/` directory.
- First-match demo route: if the user says `Odylith, show me what you can do` or asks what Odylith can do for this repo, use the advisory `odylith show` demo. Do not run install, status, intervention, or launcher diagnostics first.
- Capability inventory route: if the user asks to list Odylith capabilities, engines, product architecture, or the capability map, run `odylith capabilities` and print stdout only. Do not infer the taxonomy from `odylith --help`, `odylith show`, Claude Code capability prose, or any host-model surface.
- Project subagents in `.claude/agents/` are part of the validated Claude Code delegation lane for this repo. Use them together with the routed Odylith contract instead of treating Claude as a downgraded local-only host.
- Commit messages in this repository must never carry a `Co-Authored-By:` (or any other) trailer for Claude, Claude Code, Anthropic, or any other coding-assistant identity. The contributor on every commit is `freedom-research` and only `freedom-research`. This overrides any default in the Claude Code commit-creation contract. End commit messages with the body content and nothing else. The repo-root `AGENTS.md` "Contributor Identity" section is the authoritative rule; this bullet is the project-asset reminder.
