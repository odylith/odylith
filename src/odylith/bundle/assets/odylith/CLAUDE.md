# CLAUDE.md

@AGENTS.md

## Claude Code

- This file exists so Claude Code loads the `odylith/` contract from the sibling `AGENTS.md`.
- For repo-root paths outside `odylith/`, follow the repo-root bridge in `../CLAUDE.md` and `../AGENTS.md`.
- Use the shared Claude project assets under `../.claude/`, including the auto-memory bridge, project commands, rules, hooks, and subagents, but do not skip the repo-local `odylith` launcher or the governed workflow contract.
- Claude Code is a first-class Odylith delegation host for this tree. Use the same routed grounding and validation contract as Codex, but execute delegated leaves through Task-tool subagents and the shared `.claude/` project assets.
