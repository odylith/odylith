# odylith-diagram-catalog

## CLI-First Non-Negotiable
- CLI-first is non-negotiable for both Codex and Claude Code. Remove all hand-authoring for places where Odylith CLI should be doing the heavy-lifting. When an Odylith CLI command exists for an operation, you must call the CLI command and you must not hand-edit governed files the CLI owns. Hand-authoring governed truth where a CLI exists is a hard policy violation, not a stylistic preference. The authoritative policy, CLI surface enumeration, allowed hand-edit surfaces, and failure-mode handling live in `odylith/agents-guidelines/CLI_FIRST_POLICY.md`, anchored by Casebook learning `CB-104`. The rule travels through routed `spawn_agent` leaves on Codex and Task-tool subagents on Claude Code, so delegated work inherits the same contract.

Use when adding or updating Atlas Mermaid diagrams, or when a materially changed flow, boundary, or operator seam has no truthful Atlas coverage yet.

## Canonical Commands

```bash
./.odylith/bin/odylith atlas scaffold --repo-root . --diagram-id D-123 --slug example-flow --title "Example Flow" --kind flowchart --owner platform --summary "Describe the real implementation flow." --backlog odylith/radar/source/ideas/2026-03/example.md --plan odylith/technical-plans/in-progress/example.md --doc odylith/registry/source/components/atlas/CURRENT_SPEC.md --code path/to/example.py --create-source-if-missing
./.odylith/bin/odylith atlas auto-update --repo-root . --from-git-working-tree --fail-on-stale
./.odylith/bin/odylith atlas render --repo-root . --fail-on-stale
./.odylith/bin/odylith atlas install-autosync-hook --repo-root .
./.odylith/bin/odylith sync --repo-root . --force
```

## Rules

- Keep Atlas source of truth in `odylith/atlas/source/`.
- Keep the canonical Atlas component dossier under `odylith/registry/source/components/atlas/`.
- Search existing Atlas coverage first and update the current diagram before creating a duplicate.
- If no truthful Atlas coverage exists for a materially changed or newly tracked flow, create a new diagram in the same slice instead of leaving the seam undocumented.
- Treat `related_backlog`, `related_plans`, `related_docs`, `related_code`, and `change_watch_paths` as mandatory context, not optional metadata.
- Keep linked workstreams, components, docs, and code synchronized with the diagram change so Atlas does not drift away from the rest of Odylith truth.
- Fail closed on stale diagrams, broken links, or missing render assets.
