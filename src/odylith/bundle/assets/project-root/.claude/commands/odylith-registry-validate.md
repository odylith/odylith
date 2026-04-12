---
description: Validate the Odylith component Registry inventory contracts.
---

Validate the Odylith component Registry inventory contracts.

1. Run `./.odylith/bin/odylith validate component-registry-contract --repo-root .` to check the authoritative `odylith/registry/source/component_registry.v1.json` and the per-component dossiers under `odylith/registry/source/components/` for shape, linkage, and traceability invariants.
2. Read the validator output end-to-end. Treat reported failures as source-of-truth issues to fix in the Registry source files, not in derived bundle assets.
3. After fixes, re-run this validator and then refresh dependent surfaces via `/odylith-sync-governance` so derived dashboards and bundle mirrors catch up.
4. Use this command before commit or handoff whenever you have touched Registry source truth.
