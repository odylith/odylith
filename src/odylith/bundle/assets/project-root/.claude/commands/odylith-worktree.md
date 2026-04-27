---
description: Create an isolated Odylith worktree for a bounded slice using the required branch shape.
argument-hint: <tag> (e.g. claude-host-bake, compass-refresh)
---

Create an isolated Odylith worktree for a bounded slice.

Tag (from user): `$ARGUMENTS`

1. If `$ARGUMENTS` is empty, ask the user for the short `<tag>` before creating any branch or worktree.
2. Use the required branch shape `<year>/freedom/$ARGUMENTS`.
3. Create the worktree under `.claude/worktrees/$ARGUMENTS/`.
4. Immediately provision Odylith in the new worktree from the parent repo with `./.odylith/bin/odylith doctor --repo-root .claude/worktrees/$ARGUMENTS --repair` so `.claude/worktrees/$ARGUMENTS/.odylith/bin/odylith` exists before any host hook or slash command tries to call it.
5. If that repair step fails or the new worktree still lacks `.odylith/bin/odylith`, stop and report that the worktree is degraded. Even after repair, only call intervention or self-host posture fully end to end there after `intervention-status` reports `Activation: ready` and `Chat-visible proof: proven_this_session`.
6. Ground the new worktree before broad repo search so the delegated slice starts with the right Odylith context.
