Status: In progress

Created: 2026-08-16

Updated: 2026-08-17

Backlog: B-144

Goal: Replace Greenfield's overlapping prose-pattern interpreters with one
source-cited Semantic Intent authority, then project all governance objects
from that authority without changing the commit-only confirmation contract.

## Mechanism Decision — 2026-08-16

The prior extraction strategy did not converge. It reduced some file sizes but
left product meaning distributed across regexes, token sets, score thresholds,
vocabulary signals, and downstream prose recomposition. New failures repeatedly
appeared as adjacent grammatical variants: a fixed `without <gerund>` form
failed with an intervening adverb, and a fixed anaphoric state form failed when
the source used a linker. This is evidence against the mechanism, not a request
for more patterns.

The first replacement hypothesis—a single model call that directly populated a
wide nested IR—timed out after 120 seconds. A compact generic fact/relation
graph then failed two real medium-effort trials after 61.4 and 84.9 seconds:
the model omitted a required identity attribute and then assigned ownership to
a non-workflow fact. Deterministic validation correctly rejected both. The
single-call schema is therefore retired rather than surrounded by retries,
repair prompts, coercion, or compatibility parsing.

The concern-separated generic graph remained too permissive. Medium-effort
trials varied between false clarification, invented product/system actions, and
misidentified product identity; an independently reviewed ensemble failed
closed in 52.4 seconds. A high-effort ensemble completed in 184.5 seconds but
promoted ordinary facts to constraints, invented five non-material ambiguities,
and produced weak public proof text. It is also retired.

A four-axis micro-extraction trial completed in 17.7 seconds and correctly
isolated product identity, the three source-owned human actions, state/output
links, dependency, and non-goal. Its residuals were explicit candidates: one
invented unspecified-human action and two non-material ambiguity candidates.
This evidence supports candidate adjudication rather than model-authored truth.

The provider-call variants above are retired. The active host already has the
reasoning context, whereas nested provider ensembles added 18–185 seconds,
failed structurally, or invented material semantics. The current replacement
boundary is therefore:

1. The active host authors one Semantic Intent packet through the public JSON
   Schema exposed by `odylith greenfield semantic-intent-schema`. It supplies
   typed facts, explicit relations, canonical narratives, and exact citations
   to prompt or EDIT evidence. Plain prose is evidence only.
2. Deterministic code validates exact citation bytes, schema shape, graph
   references, ownership, polarity, material completeness, operating limits,
   and stable hashes. It does not infer actors, actions, state, output,
   dependencies, constraints, or components from prose.
3. Material uncertainty produces one focused clarification before authority is
   sealed. Independent model critique is advisory evidence; it cannot silently
   rewrite the active host's packet or become a second semantic authority.
4. The verified graph is sealed as Product Intent authority v9. Components,
   backlog, semantic events, evaluator evidence, and transaction snapshots
   project from fact ids and relation coordinates rather than lexical overlap.
5. A graph-native proposal receives one read-only pre-confirm projection pass. Invalid
   output fails closed at its graph projector; no fixpoint, rescue prompt,
   regex repair, or prose normalization may change sealed meaning.
6. CONFIRM remains model-free and publishes the exact sealed transaction bytes.
7. Legacy parser and repair mechanisms are unreachable from the public graph
   proposal path and are deleted as their final compatibility callers move.

Product outcome, source fidelity, clarification policy, transaction laws,
operating envelope, and proof standards remain fixed. Provider choice, model
profile, prompts, schema layout, and projection architecture remain provisional
and must earn continued use through fresh evidence.

## Convergence Method

This work uses **outcome-anchored, mechanism-adaptive convergence**. The goal is
the simplest reliable regime that repeatedly produces useful, source-grounded
governance objects—not the survival of any chosen parser, model, schema, or
architecture.

- Fixed: consumer outcome, semantic fidelity, transaction laws, operating
  envelope, safety invariants, and completion evidence.
- Provisional: algorithms, parsing approaches, model roles, schemas, ownership
  boundaries, repair strategy, module layout, and architecture.
- After every wave, measure consumer utility, new failure classes, semantic
  drift, complexity, latency, cost, and whether a proxy displaced the product.
- Replace a mechanism when independent examples repeat a failure class, fixes
  regress elsewhere, or downstream code continues to reinterpret canonical
  meaning.
- Before replacement, state a falsifiable prediction and compare bounded
  alternatives on positive, negative, equivalent-source, and human-quality
  evidence. Remove the losing path after the winner is proved.
- Passing tests alone is not progress. Progress means fewer failure classes,
  less duplicate authority, simpler execution, and stronger independent proof.
- The replacement holdout remains untouched until development and equivalence
  evidence are clean; it never trains the mechanism.

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

1. Define the Semantic Intent IR, exact citation contract, clarification
   contract, JSON schemas, and deterministic verifier.
2. Run one prompt-only materiality critic and one independently isolated graph
   author through pinned host profiles, call/time/token budgets, and fail-closed
   host or provider errors. Neither stage may repair the other after validation.
3. Seal the verified IR into Product Intent authority and transaction hashes;
   preserve byte-exact, model-free commit-only execution.
4. Cut proposal, semantic model, components, systems, backlog, Registry, Atlas,
   and public views to typed IR nodes.
5. Delete live semantic regex/token/scoring interpreters and downstream
   prose-reparse paths; add structural enforcement against their return.
6. Run metamorphic, adversarial, model-profile, latency/cost, transaction,
   install, browser, and structural proof before any new final holdout.

## Proof Gates

- Focused characterization and adversarial regressions pass for each owner.
- Atomic accepted-fact custody remains 80/80 on the disclosed replay.
- The full Greenfield runtime, release evaluator, transaction, recovery, and
  browser matrices pass without exclusions.
- `git diff --check`, Python compilation, source-size inventory, and banned
  shim/duplicate-helper scans pass.
- No product or campaign execution is used as decomposition proof.

## Implementation Checkpoint — 2026-08-16

- The public host packet, JSON Schema, exact citation verifier, Semantic Intent
  graph, and authority v7 are implemented. The graph-authority kernel and its
  component, backlog, projection-validation, and transaction compiler modules
  contain no regex interpretation.
- The active v7 compile path is one pass and does not load the legacy prompt
  materializer, pre-confirm fixpoint, rescue planner, or patch-apply repair
  module. A structural test makes any legacy repair call fail.
- Graph-native components and backlog replace repeated prose inference. The
  first one-pass package run exposed repeated boilerplate; the projector was
  corrected with component-specific proof and workstream-specific rationale
  rather than weakening the quality gate.
- Equivalent prompt wording with independent exact citations produces the same
  semantic-meaning hash and byte-equal components, backlog, semantic model,
  diagrams, and project brief.
- Current focused proof: Semantic Intent/proposal/transaction `11/11`, graph
  drift negatives and one-pass transaction `2/2`, transaction provenance
  `36/36`, and equivalent-source projection `1/1`. Full development proof and
  final holdout remain pending.

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

## Mechanism Checkpoint — 2026-08-17

- Fresh ambiguity-frontier evidence falsified three successive contract shapes
  without prompting fixture-specific repairs: field-agnostic materiality missed
  visible-result and human-owner gaps; parallel unresolved fields could exceed
  the one-question contract; and duplicated clarification ownership allowed the
  graph author to paraphrase the critic-owned question.
- The materiality critic is now the sole material-decision owner. The graph
  author receives a provider-locked decision boundary and independently owns
  only the settled source-cited graph. Runtime validation compares the complete
  clarification, including citations, and performs no validator-guided retry.
- A fresh graph author then exposed a separate schema defect: `from_state` and
  `to_state` were independent generic attributes, so the provider could emit a
  half transition. Semantic Intent IR v3 now represents a transition as one
  nullable typed object whose `from_state` and `to_state` members are both
  required. Packet v4, authoring request v7, Product Intent authority v9, and
  compiler identity v8 fail closed on older graph contracts; no compatibility
  alias or prose repair path remains in the graph lane.
- The current frozen focused proof is `120/120` across graph validation,
  materiality, projection planning, authority severance, transaction provenance,
  post-confirm fingerprinting, commit recovery, and host execution. The fixture
  and graph-contract filenames now match their v4/v3 contracts. A fresh
  revision-bound development cohort is the next gate; no final-holdout evidence
  has been accessed.
- The first wider development wave then exposed exact-citation duplication:
  after the critic validated source bytes, the graph author independently
  retyped them and one relation citation drifted. The graph author now selects
  only from the critic-validated provider-locked citation catalog. This moves
  byte custody to one owner without changing entailment responsibility, adding
  a repair loop, or introducing prose parsing. Request v8, authority v10, and
  compiler identity v9 fail closed on the superseded contract; focused proof is
  `121/121`. The failed case remains failed evidence and will receive only a
  fresh assignment after this revision is committed.
- The first fresh catalog-bound assignment then exposed a strict provider
  limitation: newline-bearing exact quotes cannot appear inside response-schema
  enums. Citation selection now uses deterministic opaque handles in the
  author transport. The author input includes the handle-to-exact-citation
  catalog, the provider emits only handles, and the host adapter decodes them
  before canonical graph validation and output hashing. This is a typed
  transport boundary, not semantic normalization. Development author input v4
  and mechanism evidence v4 pin the rule; focused proof is `141/141`.
- The resulting 24-case one-shot cohort then exposed an overloaded component
  field before a candidate bundle could be sealed. A required local adapter
  had no result implementation, but downstream projection interpreted
  `first_path_required` as a result-owner declaration. The losing contract is
  removed: release scope is now only `first_path_required|deferred`, while the
  projection plan derives `result_implementing|boundary_supporting` from typed
  relations and persists the first-workflow start component. No label, prose,
  vocabulary, or empty-result fallback selects ownership. Focused graph/
  projection/release proof is `33/33`; the wider release-contract gate is
  `251/251`. The prior 24 segments remain failed evidence under the superseded
  contract and cannot be reused as release evidence.

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
