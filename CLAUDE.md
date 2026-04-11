# CLAUDE.md

@AGENTS.md

## Claude Code

- This file keeps Claude aligned with the repo-root `AGENTS.md` contract instead of branching into a Claude-only lane.
- This repo also ships committed Claude project assets under `.claude/`, including `.claude/CLAUDE.md`; use them for Claude-native commands, hooks, rules, subagents, and the auto-memory bridge.
- Keep this file, the `.claude/` tree, and the scoped `odylith/**/CLAUDE.md` companions aligned with the same Odylith contract.
- Claude Code is a first-class Odylith delegation host. Codex executes routed leaves through `spawn_agent`; Claude Code executes the same bounded delegation contract through Task-tool subagents and the checked-in `.claude/` project assets.
