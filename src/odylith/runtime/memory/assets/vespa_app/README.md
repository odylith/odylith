# Odylith Vespa App

This directory is the minimal Vespa application package for Odylith's optional
shared remote retrieval lane.

It matches the current runtime sync/query contract in
`src/odylith/runtime/memory/odylith_remote_retrieval.py`:

- schema name: `odylith_memory`
- namespace: `odylith`
- document id: `doc_key`
- indexed fields: `kind`, `entity_id`, `title`, `path`, `content`
- embedding field: deterministic local Odylith embedding for future hybrid or
  semantic rank profiles

The local Odylith runtime remains complete without this service. This package is
only for operators who want an explicit shared retrieval tier.

## Layout

- `services.xml`: query/feed container and one content cluster
- `deployment.xml`: deploys the same application package
- `schemas/odylith_memory.sd`: sparse-first text schema with a future-ready
  embedding field

## Deploy

Use the standard Vespa application-package deploy flow against your Vespa
cluster:

```bash
vespa deploy odylith/runtime/source/odylith-vespa-app
```

Then point the runtime at the deployed endpoint:

```bash
export ODYLITH_VESPA_URL="https://<vespa-endpoint>"
export ODYLITH_VESPA_MODE=augment
export ODYLITH_VESPA_SCHEMA=odylith_memory
export ODYLITH_VESPA_NAMESPACE=odylith
odylith context-engine --repo-root . odylith-remote-sync --dry-run
```

Optional:

- set `ODYLITH_VESPA_PRUNE_MISSING=1` if you want explicit sync runs to delete
  remote documents that disappeared from the current local Odylith corpus
- repeated live sync runs now skip unchanged document sets automatically instead
  of refeeding the whole remote corpus

## Rollback

- Remove the `ODYLITH_VESPA_*` environment variables from the runtime process.
- Re-deploy the previous Vespa application package revision if the schema or
  services definition needs to be backed out.
- Re-run `odylith context-engine --repo-root . status` and confirm
  `remote_retrieval.enabled=false` or that the expected Vespa endpoint is back.
