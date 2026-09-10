- Bug ID: CB-326

- Status: InProgress

- Created: 2026-09-03

- Severity: P1

- Reproducibility: Intermittent

- Type: Product

- Description: The immutable dist-v11 public community-refrigerator recovery run reached model authoring, then rejected the one-pass response because the flat heterogeneous facts array contained multiple citations for a singular intent field.

- Impact: A grounded public Greenfield request can fail before producing a transaction despite remaining within the selected time tier.

- Components Affected: domain-intelligence

- Environment(s): Immutable local release dist-v11 at source commit 583319062821c07dd9fbc196e7b32d9379512db4, installed consumer recovery proof, public community-refrigerator case.

- Detected By: Installed SIGKILL recovery proof precondition run.

- Failure Signature: Greenfield authoring returned multiple source facts for one singular field; no records were created.

- Trigger Path: Installed odylith greenfield propose for public-2026-09-01-community-fridge inside the commit-recovery proof.

- Ownership: Domain Intelligence Greenfield model authoring response contract.

- Timeline: Dist-v11 passed release leakage and provenance checks. The installed recovery proof invoked the public standard-tier case and authoring failed before crash injection or transaction staging.

- Blast Radius: Any request where the model emits more than one citation for a scalar intent field in the flat facts array.

- SLO/SLA Impact: Violates the every-request success invariant for the 60-second standard tier; the transaction is never staged.

- Data Risk: Fail-closed; no governed writes were observed.

- Security/Compliance: No authority or write-boundary breach; failure occurs before confirmation.

- Invariant Violated: Every admissible Greenfield request must produce one source-grounded, quality-gated transaction within its 60, 90, or 120 second tier.

- Workaround: None. Do not retry or repair the response through prose parsing.

- Root Cause: The response schema represents scalar and repeated intent facts in one flat array, so scalar cardinality is described in prompt prose and rejected only after model completion rather than being structurally unrepresentable.

- Solution: Replace the heterogeneous flat fact list with a closed typed fact object whose scalar fields accept at most one citation and whose repeated fields accept bounded citation arrays; keep one model call and exact-quote custody.

- Rollback/Forward Fix: Forward fix only; preserve fail-closed behavior until the typed schema is proven.

- Verification: Intent-authoring v19 encodes scalar versus repeated cardinality in the closed output schema; immutable dist-v14 passes installed recovery and all three unchanged public 60/90/120 cases at release-quality 10/10.

- Prevention: Encode cardinality in the structured output schema instead of prompt-only conventions or downstream repair.

- Agent Guardrails: Do not add regexes, retries, response rewriting, or example-specific exceptions. Remove the flat fact contract once the typed contract lands.

- Preflight Checks: Search Casebook and B-142; retain one semantic model pass, exact custody, and no post-CONFIRM work.

- Regression Tests Added: `test_authoring_schema_encodes_scalar_and_repeated_fact_cardinality`, `test_authoring_rejects_the_retired_flat_fact_array`, and `test_authoring_rejects_typed_facts_over_the_total_citation_cap` prove the replacement shape and its fail-closed envelope.

- Monitoring Updates: Public matrix reports authoring rejection class and no-write evidence.

- Version/Build: 0.1.15 dist-v11, 583319062821c07dd9fbc196e7b32d9379512db4

- Related Incidents/Bugs: CB-303, CB-325, B-142

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_model_intent_authoring.py

- Source Resolution (2026-09-03): Intent-authoring v19 replaces the mixed
  citation array with one closed `facts` object. Every scalar source-fact key
  admits exactly one citation or null; every repeated key admits a bounded
  ordered array, and the compiler still enforces the aggregate 256-citation
  envelope before resolving bytes. The old flat response and downstream
  singular-cardinality rejection are removed together. One model call still
  owns semantic selection, deterministic code still verifies exact quote
  custody, and no regex, retry, response rewrite, case exception, or
  post-confirm work was added. Focused authoring/custody proof passes `140/140`,
  the complete Greenfield runtime selection passes `616/616`, install/release
  passes `459/459`, and static compilation plus diff checks pass. This is
  source closure only; immutable installed recovery and public `60/90/120`
  proof remain open.

- Immutable Installed Advancement (2026-09-03): Clean dist-v12 at
  `18f226fb39e0a3736d949672339274ce179a5936` accepted the v19 typed fact object
  for the same public standard-tier case and advanced beyond the escaped
  singular-cardinality failure. It later failed on the distinct product-owner
  alias defect recorded as `CB-327`, before staging or writes. This is live
  installed evidence that the old cardinality failure is removed, but release
  closure still requires the complete recovery and public matrix gates.

- Immutable Installed V14 Verification (2026-09-03): Clean dist-v14 from
  candidate `62bcdd8147e47874e984483b48fb1fb0a20ca413` passes the installed
  recovery gate and the unchanged public three-case matrix. The typed v19 fact
  contract accepts the community, subsea, and neuromorphic requests without a
  cardinality rejection; proposal times are `44.315s`, `44.053s`, and
  `66.854s` inside their exact `60/90/120` budgets, create times are `1.712s`,
  `1.733s`, and `1.752s`, and every package scores release-quality `10/10`.
  Browser proof passes `3/3`, cleanup passes, and the matrix reports no failure
  cluster. CB-326 is fixed pending release. No regex, retry, response rewrite,
  or post-confirm interpretation was introduced.

- Reopened Ownership Cardinality Variant (2026-09-04): A fresh standard
  Terra-medium semiconductor development request returned in 44.883 seconds
  with five exact responsibility citations and one product owner. The compiler
  rejected it before staging because two model-visible arrays had to have equal
  length. One component owning five responsibilities is valid product meaning;
  representing ownership through synchronized array positions is the defect.
  This is not the product-title alias issue in CB-327. The source-frozen attempt
  is retained at
  `/private/tmp/odylith-greenfield-v32-source.EfRGyu/semiconductor-standard`.
  Replace the model wire with owner groups containing their responsibility
  citations, deterministically flatten into the existing canonical facts and
  relations, and remove the parallel-array wire. Preserve the shared exact owner
  resolver, contradictory-owner rejection, citation limits, and no post-confirm
  interpretation. Do not broadcast a missing owner, infer one from prose, or
  support both response formats. Focused structural proof and fresh complete
  package quality are required before closure.

- Goal Alignment (2026-09-04): One model call and exact-quote rendering were
  selected mechanisms, not original goal invariants. The original contract
  permits bounded pre-confirm repair and entailed concise copy within the fixed
  60/90/120 budgets. The ownership correction does not add a call or relax
  source custody; no new repair mechanism is approved merely by this note.
