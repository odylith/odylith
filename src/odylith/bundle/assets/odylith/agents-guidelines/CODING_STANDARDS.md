# Coding Standards

## Documentation, Reuse, And Robustness
- Clear code documentation, reusability, and robustness are non-negotiable.
- Prefer extending shared helpers, shared contracts, and existing runtime
  primitives over copy-paste or near-duplicate logic.
- If equivalent behavior already exists, reuse it or consolidate toward one
  canonical implementation instead of growing a parallel fork.
- When behavior changes would otherwise stop being obvious to the next
  maintainer, update the governing doc, spec, or nearest high-signal code
  comment in the same change.
- New helpers should stay bounded, named for the real contract they carry, and
  covered by focused validation rather than introduced as one-off glue.

## Source File Discipline
- The repo-root file-size policy is non-negotiable for Odylith-owned product
  code.
- For hand-maintained Odylith source, `800` LOC is the soft limit, `1200` LOC
  requires an explicit exception and decomposition plan, `2000+` LOC is
  red-zone exception only, and tests cap at `1500` LOC.
- When a hand-maintained source file is already beyond those thresholds, the
  next meaningful change should be refactor-first work: split it into multiple
  focused files or modules instead of authorizing more in-place growth unless
  an explicit exception already exists.
- Generated or mirrored bundle assets are excluded; govern their
  source-of-truth files instead.
- Prefer `1-2` file decompositions with characterization tests first, and
  prioritize refactor waves by size x churn x centrality rather than launching
  repo-wide "all files above X" rewrites.

## Validation Expectations
- Every coding change should carry focused validation that proves the real
  contract touched by the change.
- When generated surfaces or bundled guidance change, validate both the source
  artifact and the shipped mirror instead of trusting one side alone.
- Use [VALIDATION_AND_TESTING.md](./VALIDATION_AND_TESTING.md) for the full
  proof bundles and command-level validation guidance.
