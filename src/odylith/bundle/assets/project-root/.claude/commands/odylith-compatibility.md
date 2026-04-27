---
description: Inspect the local Claude Code host compatibility posture for Odylith.
argument-hint: [--json] [--skip-version-probe]
---

Inspect the local Claude Code host compatibility posture for Odylith.

Forwarded flags (from user): `$ARGUMENTS`

1. Run `./.odylith/bin/odylith claude compatibility --repo-root . $ARGUMENTS` to probe the local Claude CLI, the project assets under `.claude/`, and the baked Odylith Claude host modules.
2. Read the report in full. It surfaces Claude CLI availability and version, project-hook wiring (PreToolUse, PostToolUse, SubagentStart/Stop, PreCompact), statusline support, slash-command surface coverage, trusted-project posture, project-assets mode, assistant-render fallback support, and the overall compatibility posture (`baseline_safe`, `baseline_safe_with_project_assets`, `baseline_safe_with_local_claude_cli`, or `baseline_safe_assistant_visible_ready`).
3. Use the report to decide whether routed delegation should run with the first-class `.claude/` project surface enabled or fall back to the baseline `CLAUDE.md + ./.odylith/bin/odylith` contract.
4. Pass `--json` when you need a machine-readable snapshot for downstream tooling. Pass `--skip-version-probe` when you want a fast posture read without invoking the Claude CLI binary.
5. Treat the printed posture as authoritative over older Compass, shell, or release-history context for Claude host capability questions.
