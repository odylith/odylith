---
description: Sync mapped Compass requirement evidence into component living specs.
---

Sync mapped Compass requirement evidence into component living specs.

1. Run `./.odylith/bin/odylith governance sync-component-spec-requirements --repo-root .` to fold mapped Compass requirement evidence into the per-component `CURRENT_SPEC.md` files under `odylith/registry/source/components/`.
2. Treat the run as a write to governed truth: in a consumer repo, only run it when the operator has authorized Odylith mutation. In maintainer mode it is part of the standard governance refresh contract.
3. After the sync, review the touched `CURRENT_SPEC.md` files and run `/odylith-registry-validate` to confirm the spec contract still holds.
4. Use this command before commit or handoff whenever Compass requirement evidence has changed for a Registry component.
