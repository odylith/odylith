# CLAUDE.md

<!-- odylith-scope:start -->
## Odylith Scope

- Load `@AGENTS.md` as the authoritative shared Odylith contract; do not duplicate that contract in Claude-specific memory.
- For substantive work, run repo-local `odylith start` first. Run `odylith context --repo-root . <ref>` only after startup and only when an exact anchor is known.
- Keep routine startup, context, query, fallback, and packet-selection internals out of normal chat updates unless the user asks for the command or a real blocker requires it.
- Preserve the intervention pipeline: prompt-bundle may surface earned Observation or Proposal output, while normal low-signal prompts stay quiet unless a visibility recovery or Odylith-directed receipt is needed.
- Claude PostToolUse hooks stay silent on success; Claude Stop is memory/logging only.
- Claude Code uses the checked-in `.claude/` project assets for hooks, commands, rules, skills, subagents, statusline, and auto-memory; keep those assets aligned with the shared `AGENTS.md` contract.
- Governance-learning is mandatory for Claude too: durable errors, failed mechanisms, bad artifacts, and validation results update the appropriate Casebook, Radar, Registry, Atlas, or Compass record before closeout. Before a fix, search existing truth, read prior failed mechanisms, and do not repeat a fix path that governance already shows failed.
- First-match help, show-me, and capability inventory routes stay stdout-clean: use `odylith --help`, `odylith show`, or `odylith capabilities` as appropriate before any diagnostics.
- Commit messages must use only the `freedom-research` contributor identity and must not include coding-assistant trailers.
- In the Odylith product repo, maintainer-only release and benchmark publishing work follows `odylith/maintainer/AGENTS.md`.
- In maintainer mode, pinned dogfood is the default proof posture and detached `source-local` is the explicit live-source posture.

<!-- odylith-scope:end -->

@AGENTS.md

## Claude Code

- This file keeps Claude aligned with the repo-root `AGENTS.md` contract instead of branching into a Claude-only lane.
- This repo also ships committed Claude project assets under `.claude/`, including `.claude/CLAUDE.md`; use them for Claude-native commands, hooks, rules, subagents, and the auto-memory bridge.
- Keep this file, the `.claude/` tree, and the scoped `odylith/**/CLAUDE.md` companions aligned with the same Odylith contract.
- First-match help route: if the user says `Odylith, help`, use the CLI help surface and print stdout only. Do not run install, status, intervention, or launcher diagnostics first.
- First-match demo route: if the user says `Odylith, show me what you can do` or asks what Odylith can do for this repo, use the advisory `odylith show` demo. Do not run install, status, intervention, or launcher diagnostics first.
- Capability inventory route: if the user asks to list Odylith capabilities, engines, product architecture, or the capability map, run `odylith capabilities` and print stdout only. Do not infer the taxonomy from `odylith --help`, `odylith show`, Claude Code capability prose, or any host-model surface.
- Claude Code is a first-class Odylith delegation host. Codex emits routed `spawn_agent` payloads subject to active host policy; Claude Code executes the same bounded delegation contract through Task-tool subagents and the checked-in `.claude/` project assets.
- Commit messages in this repository must never carry a `Co-Authored-By:` or other coding-assistant trailer. The contributor on every commit is `freedom-research`.
