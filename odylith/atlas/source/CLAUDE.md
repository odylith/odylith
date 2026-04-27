# CLAUDE.md

@AGENTS.md

## Claude Code

- This scoped file ensures Claude loads the same Atlas subtree contract as other hosts.
- Prefer the `odylith-atlas-diagrammer` subagent or the diagram-catalog skill shim when the slice is mostly diagram or catalog work.
- Treat `.mmd` files and `catalog/diagrams.v1.json` as the canonical Atlas source surfaces. Keep rendered dashboard artifacts aligned, but do not treat them as source truth.
- For broader Odylith context outside this subtree, follow `odylith/AGENTS.md` and the repo-root bridge.
- Do not treat this file as architecture source truth; it is only the Claude companion for this scope.
