---
paths:
  - "odylith/radar/source/**/*"
  - "odylith/technical-plans/**/*"
  - "odylith/casebook/bugs/**/*"
  - "odylith/registry/source/**/*"
  - "odylith/atlas/source/**/*"
---

# Odylith Governance Rules

- These directories are source-of-truth governance records. Prefer editing them directly and treat rendered dashboards as derived outputs.
- `AGENTS.md` and `CLAUDE.md` companions inside these trees are scoped guidance files, not governance records.
- After editing truth here, refresh the derived surfaces with `./.odylith/bin/odylith sync --repo-root . --impact-mode selective <changed_paths...>` unless the project hook already completed that refresh.
- When the change touches product-owned docs or guidance that ship in the bundle, keep the mirrored assets under `src/odylith/bundle/assets/odylith/` aligned with the source files.
