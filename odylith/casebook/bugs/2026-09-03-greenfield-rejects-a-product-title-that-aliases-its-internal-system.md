- Bug ID: CB-327

- Status: FixedPendingRelease

- Created: 2026-09-03

- Severity: P1

- Reproducibility: Intermittent

- Type: Product

- Description: Immutable dist-v12 advanced beyond typed fact cardinality, then the same public standard-tier recovery case failed because an exact product label was selected both as the title and as an internal system owner.

- Impact: A valid Greenfield request can fail before transaction staging when the product name is also the natural name of its owning system.

- Components Affected: domain-intelligence

- Environment(s): Immutable local release dist-v12 at source commit 18f226fb39e0a3736d949672339274ce179a5936, installed consumer recovery proof, public community-refrigerator case.

- Detected By: Installed SIGKILL recovery proof precondition run.

- Failure Signature: Greenfield authoring returned an ambiguous product owner; no records were created.

- Trigger Path: Installed odylith greenfield propose for public-2026-09-01-community-fridge inside the commit-recovery proof.

- Ownership: Domain Intelligence direct evidence graph product-owner identity.

- Timeline: Dist-v12 passed clean provenance and platform leakage checks. Its installed recovery proposal crossed the prior cardinality failure and then stopped at duplicate product-owner interpretation.

- Blast Radius: Requests where the selected title and one selected internal system use the same exact source label.

- SLO/SLA Impact: Violates standard-tier every-request success before transaction staging; no 60-second completion evidence is produced.

- Data Risk: Fail-closed; no governed writes were observed.

- Security/Compliance: No authority or write-boundary breach; the validator rejects before confirmation.

- Invariant Violated: One real product owner must retain one canonical typed identity even when title and internal-system projections share its exact label.

- Workaround: None. Do not ask the model to retry or rewrite the response.

- Root Cause: Event binding, owner-path validation, and component ownership independently index product identities by quote and treat an exact title/internal-system alias as two conflicting owners.

- Solution: Create one shared typed product-owner resolver that collapses a title alias onto the single more-specific internal-system fact, while rejecting cross-kind collisions or multiple indistinguishable internal-system paths.

- Rollback/Forward Fix: Forward fix the shared owner identity boundary; keep ambiguous cross-kind and same-kind conflicts fail-closed.

- Verification: Title/internal-system alias success is proven through event, component, full proposal, installed recovery, and the unchanged public 60/90/120 matrix while multiple internal owners and cross-kind collisions still fail closed.

- Prevention: All event, actor, and component ownership consumers must use one canonical product-owner identity owner.

- Agent Guardrails: Do not add prompt-only duplicate warnings, regexes, retries, response rewriting, or case-specific labels.

- Preflight Checks: Search Casebook and B-142; distinguish a structural title alias from genuinely indistinguishable internal owners and cross-kind label collisions.

- Regression Tests Added: `test_authoring_canonicalizes_a_title_alias_to_its_internal_system_owner`, `test_authoring_rejects_two_indistinguishable_internal_system_paths`, and `test_authoring_rejects_a_product_and_human_label_collision` cover the accepted alias and retained denials.

- Monitoring Updates: Public matrix reports the authoring failure and preserved no-write state.

- Version/Build: 0.1.15 dist-v12, 18f226fb39e0a3736d949672339274ce179a5936

- Related Incidents/Bugs: CB-303, CB-326, B-142

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_model_direct_evidence_graph.py
- src/odylith/runtime/domain_intelligence/greenfield_authored_backlog.py
- tests/unit/runtime/test_greenfield_product_owner_identity.py

- Source Resolution (2026-09-03): Authored-semantics v10 now owns one shared
  product-owner projection resolver. When the product title and exactly one
  internal system share an exact label, the resolver binds events and component
  responsibilities to the narrower internal-system path. Multiple same-label
  internal paths and product/human label collisions still reject. The direct
  evidence graph and later sealed-semantics validator consume that same owner
  contract instead of maintaining competing quote indexes. Focused proof passes
  `92/92`, complete Greenfield runtime passes `618/618`, install/release passes
  `459/459`, and a fresh source-local standard-profile call on the same public
  case authored four grounded events in `26.465s`. No prompt-only warning,
  regex, retry, response rewrite, extra model call, or post-confirm work was
  added. Immutable installed recovery and the public matrix remain open.

- Exact Installed V13 Downstream Reopen (2026-09-03): After the recovery clone
  correction, the same immutable v13 candidate reached its one installed model
  call and then failed closed with `model-authored workstream has an uncited
  impacted component`. The direct graph and sealed semantics had already
  canonicalized the exact title/internal-system alias, but Radar independently
  rematched the rendered component label against both source paths and required
  exactly one match. That downstream reinterpretation reintroduced the same
  duplicate-owner failure class. Radar now consumes the shared canonical owner
  map produced from title and internal-system facts; it no longer maintains a
  competing quote-match rule. The title-alias regression now builds the complete
  proposal and proves every backlog workstream cites `/internal_systems/0`.
  Focused owner, backlog, and recovery proof passes `35/35`; complete Greenfield
  runtime passes `618/618`; install/release passes `460/460`. No regex, prompt
  warning, retry, response rewrite, second model call, or post-confirm work was
  added. A rebuilt immutable recovery proof and public `60/90/120` matrix remain
  required.

- Immutable Installed V14 Verification (2026-09-03): Clean dist-v14 from
  candidate `62bcdd8147e47874e984483b48fb1fb0a20ca413` passes the complete
  installed recovery gate and all three unchanged public cases. The original
  community title/internal-system alias now publishes a complete package in
  `44.315s` plus `1.712s` commit time at release-quality `10/10`; the unrelated
  rescue and deep cases also pass in `44.053s` and `66.854s`, each with
  release-quality `10/10`. Browser proof passes `3/3`, every recovery phase
  binds one identical Product Intent facts hash, and the matrix reports no
  failure cluster. CB-327 is fixed pending release. The shared typed owner map
  remains the single interpretation boundary across direct semantics, sealed
  validation, and Radar; no regex, retry, second model call, or post-confirm
  repair was added.
