---
description: Create an isolated Odylith worktree for a bounded slice using the required branch shape.
argument-hint: <tag> (e.g. claude-host-bake, compass-refresh)
---

Create an isolated Odylith worktree for a bounded slice.

Tag (from user): `$ARGUMENTS`

1. If `$ARGUMENTS` is empty, ask the user for the short `<tag>` before creating any branch or worktree.
2. Use the required branch shape `<year>/freedom/$ARGUMENTS`.
3. Create the worktree under `.claude/worktrees/$ARGUMENTS/`.
4. Ground the new worktree before broad repo search so the delegated slice starts with the right Odylith context.
