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
- First-match demo route: if the user says `Odylith, show me what you can do` or asks what Odylith can do for this repo, use the advisory `odylith show` demo. Do not run install, status, intervention, or launcher diagnostics first.
- Project subagents in `.claude/agents/` are part of the validated Claude Code delegation lane for this repo. Use them together with the routed Odylith contract instead of treating Claude as a downgraded local-only host.
