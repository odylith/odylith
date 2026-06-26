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
- Keep Governance-learning current before closeout: durable errors and regressions belong in Casebook, planned work in Radar or plans, component-contract changes in Registry, flow/topology changes in Atlas, and durable decisions or proof checkpoints in Compass. Before fixing a bug, search Casebook and related governance truth, read prior failed mechanisms, failed fix attempts, and guardrails, do not repeat a fix path that already failed, and capture new mechanism-level learning.
- After editing truth here, refresh the derived surfaces with `./.odylith/bin/odylith sync --repo-root . --impact-mode selective <changed_paths...>` unless the project hook already completed that refresh.
- When the change touches product-owned docs or guidance that ship in the bundle, keep the mirrored assets under `src/odylith/bundle/assets/odylith/` aligned with the source files.
