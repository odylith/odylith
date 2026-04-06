# Odylith Migration

Legacy installs should take one explicit migration path:

1. Run the latest Odylith hosted installer from the repo root:
   `curl -fsSL https://github.com/odylith/odylith/releases/latest/download/install.sh | bash`
2. Let that installer rename legacy repo-owned roots from `odyssey/` to `odylith/` and from `.odyssey/` to `.odylith/`.
3. If the repo already has `./.odylith/bin/odylith`, you can run the same migration directly with `./.odylith/bin/odylith migrate-legacy-install --repo-root .`.
4. Switch automation and local habits from `odyssey` to `odylith`.
5. Use `./.odylith/bin/odylith start --repo-root .` for normal operation.
6. Delete any stale `.odyssey/` tree only if one is still present after the migration command confirms success.

Migration preserves repo-owned truth under the renamed `odylith/` tree and purges volatile legacy mutable state rather than preserving it:

- local LanceDB and Tantivy indexes under the old memory root
- legacy context-engine cache and lock state
- old benchmark and compiler runtime caches
- old Vespa sync manifests and local remote-retrieval state

If the old `./.odyssey/bin/odyssey upgrade` path no longer works, do not try to repair the old launcher first. The Odylith hosted installer is the supported rescue path because it can migrate the legacy repo roots directly.

Some checked-in historical records may still mention the former product name. That is preserved as history, not live product identity.
