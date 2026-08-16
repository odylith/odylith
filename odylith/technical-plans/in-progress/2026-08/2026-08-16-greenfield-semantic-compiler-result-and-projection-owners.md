Status: In progress

Created: 2026-08-16

Updated: 2026-08-16

Backlog: B-144

Goal: Decompose the Greenfield semantic pipeline into explicit result,
projection, and reporting owners without changing the sealed pre-confirm
transaction or commit-only confirmation contracts.

## Scope

- Move result selection and projection repair out of
  `greenfield_semantic_compiler.py` until the root is at or below 1,200 lines.
- Continue the real reporting-owner extraction already started in
  `greenfield_preconfirm_matrix.py`; the runner may orchestrate, but it must not
  regain terminal-result construction or duplicated semantic normalization.
- Characterize the prompt-source and confirmed-intent recovery phases, then
  move cohesive parsing, composition, and recovery ownership out of their
  red-zone roots without alias walls or private-host tunneling.
- Keep shared semantic normalization in one owner and adopt it across every
  touched evaluator caller.

## Current Safety-Critical Exception

The active Greenfield release repair may make bounded safety-critical changes
in the red-zone files named above only when a focused regression demonstrates
the escaped custody, clarification, or evaluator defect. This exception does
not permit unrelated feature growth. Any unavoidable growth must stay bounded
to the reproduced safety defect, while new terminal, normalization, and
projection phases move to real owners. The final release checkpoint must retain
this plan as active until the size and ownership targets are met.

## Non-Goals

- Do not weaken semantic, custody, provenance, materiality, or quality gates.
- Do not move semantic interpretation after confirmation.
- Do not add holdout-specific vocabulary or scorer exceptions.
- Do not create wrapper-only modules, duplicate normalizers, or compatibility
  facades that leave the original ownership in place.

## Ownership Waves

1. Seal evaluator semantic text, frozen-contract provenance preparation, and
   early-stop reporting behind dedicated owners; keep the matrix runner as an
   orchestrator.
2. Extract semantic result selection and projection repair behind typed result
   contracts; reduce the compiler root below 1,200 lines.
3. Extract prompt-source composition and intent-recovery phases with their
   characterization tests; remove obsolete local parsing and normalization.
4. Run structural inventory, full runtime/install proof, and close the
   temporary safety-critical exception only after every named owner meets its
   contract.

## Proof Gates

- Focused characterization and adversarial regressions pass for each owner.
- Atomic accepted-fact custody remains 80/80 on the disclosed replay.
- The full Greenfield runtime, release evaluator, transaction, recovery, and
  browser matrices pass without exclusions.
- `git diff --check`, Python compilation, source-size inventory, and banned
  shim/duplicate-helper scans pass.
- No product or campaign execution is used as decomposition proof.

## Implementation Checkpoint — 2026-08-16

- Evaluator semantic text and action-order normalization now have one shared
  owner. Frozen synthetic identity is bound only after external manifest and
  holdout validation, and non-compiled terminal reporting has one dedicated
  owner rather than duplicated runner construction.
- Prompt-source command-audience composition and proof-boundary normalization
  moved behind typed, reusable owners. The structured first-path owner is at
  the `800`-line boundary; prompt evidence interpretation is `1192` lines and
  the matrix runner remains a documented safety-critical red-zone exception.
- No gate, scorer floor, source-provenance rule, or post-confirm boundary was
  weakened. Production sources contain no disclosed case IDs or fixture
  vocabulary, and new modules do not private-import the owners they replace.
- Current behavior proof is `396/396` for the final runtime compatibility
  matrix, `80/80` strict disclosed custody, `193/193` evaluator,
  `46/46` security/proof, and `211/211` independent closure with no P0/P1.
- Wave 1 is materially implemented, but this plan remains active: the semantic
  compiler, confirmed prompt source, confirmed intent recovery, and matrix
  runner still exceed their target sizes. Exact installed and browser proof
  is also pending before any safety-critical exception can narrow.

## Stop Conditions

- Stop if an extraction changes the sealed transaction hash for unchanged
  accepted facts without an explained contract change.
- Stop if an owner must import private helpers from the module it replaces.
- Stop if a gate, scorer, source-provenance rule, or post-confirm boundary must
  be weakened to keep tests green.

## Validation

```bash
odylith validate plan-workstream-binding --repo-root .
odylith validate plan-traceability --repo-root .
odylith validate plan-risk-mitigation --repo-root .
odylith validate backlog-contract --repo-root .
```

Run the focused and full Greenfield proof commands recorded in the active
B-142 release-repair checkpoint before closing this plan.

## Risks And Mitigations

- Risk: extraction silently changes semantic selection. Mitigation: preserve
  typed inputs and outputs, land characterization tests first, and compare
  sealed transaction facts before and after each move.
- Risk: fake modularization increases indirection. Mitigation: reject private
  host imports, alias walls, and duplicate normalizers through structural
  tests and review.
- Risk: red-zone safety fixes become open-ended feature growth. Mitigation:
  limit the exception to reproduced release blockers and keep B-144 active
  until the named size and ownership targets are met.
