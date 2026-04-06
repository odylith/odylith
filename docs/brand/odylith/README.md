# Odylith Brand Assets

This directory is the repository source-of-truth for Odylith logo deliveries and design handoff packages.

## Current approved package

- `2026-04-rebrand-package/`
  - root rebrand asset handoff moved from the repo staging folder
  - includes icon exports, lockup exports, and the provided favicon `.ico`

## Runtime-facing copies

The approved production subset is mirrored into:

- `src/odylith/runtime/surfaces/assets/brand/`
  - packaged application assets used by Odylith runtime surfaces
- `src/odylith/bundle/assets/odylith/surfaces/brand/`
  - installed copies materialized into repos that carry the product under `odylith/surfaces/brand/`

## Important note

The provided SVGs are image-based wrappers around approved raster artwork. They preserve the approved appearance but are not editable path-based vector sources.
