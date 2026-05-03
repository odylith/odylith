# CLAUDE.md

@../AGENTS.md

## Claude Code

- This project-level bridge exists for setups that prefer `.claude/CLAUDE.md`; it imports the repo-root contract instead of restating it.
- Use `/odylith-start` before broad repo search, then `/odylith-context` only after startup when an exact workstream, component, path, or bug id is known. Do not launch them in parallel.
- Use `/odylith-query` only after concrete anchors exist, and `/odylith-sync-governance` only when a manual refresh is needed beyond hooks.
- For high-pressure cleanup, route through `odylith-code-hygiene-guard` with `ANTI_SLOP_AND_DECOMPOSITION.md` in scope.
- SessionStart writes the compact Compass-derived note into Claude auto-memory; routine stdout is intentionally quiet to avoid duplicating that memory.
- SubagentStart injects the active Odylith slice into Claude subagents, and `.claude/skills/` exposes repo-owned playbooks without replacing the launcher-first contract.
- Keep help, show-me, and Odylith capabilities/engines prompts stdout-clean: run the single authoritative `odylith --help`, `odylith show`, or `odylith capabilities` route, print stdout only, and do not infer from Claude, Codex, or any host-model surface.
- `odylith plan --help` is read-only; do not probe `odylith/technical-plans/source/`, and do not pair help with parallel exploratory filesystem probes that can cancel the visible help call.
- Commit messages in this repository must use only the `freedom-research` contributor identity and must not include coding-assistant trailers.
