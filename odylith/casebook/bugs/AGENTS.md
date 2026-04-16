# Casebook Bugs AGENTS

Scope: applies to all files under `odylith/casebook/bugs/`.

## Purpose
- Keep bug records consistent, searchable, and linked to the surrounding governance surfaces.

## Ownership
- Bug entries are repo-local Odylith truth for the current repository.
- Odylith owns the guidance and renderer contract for this surface.
- In consumer repos diagnosing Odylith product issues, bug records are read-only: prepare a Casebook-ready payload for the maintainer instead of editing local Odylith bugs.
- Keep bug content under `odylith/casebook/bugs/` instead of scattering it into generic repo-level bug buckets.

## Contract
- `odylith/casebook/bugs/INDEX.md` is the canonical bug index.
- Individual bug markdown files remain the source of truth for case detail.
- Individual bug markdown files should carry a stable `- Bug ID: CB-###` field near the top of the record.
- `- Reproducibility:` must be one compact token such as `High`, `Medium`, `Low`, `Always`, `Intermittent`, or `Consistent`; put commands, repro steps, screenshots, and environment details in `Trigger Path`, `Failure Signature`, `Environment(s)`, or `Description`.
- Run `odylith casebook validate --repo-root .` when checking Casebook source truth directly; `odylith casebook refresh` must fail closed on invalid bug markdown before rewriting the index, payload shards, HTML, or bundle mirrors.
- Casebook renderers may project these files into dashboards, but must not become the authoritative source.
