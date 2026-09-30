- Bug ID: CB-324

## V33 single-authority public recurrence (2026-09-30)

The clean pushed `dc1dd6a08` installed 40-case public discovery campaign
stopped after 8 cases (7 passed, 1 failed) at
`release-agriculture-030-source`. The operator requested only "Build an
agriculture product" and supplied a separately labelled plantFEM repository
description as source evidence. The one Astra/medium candidate promoted "This
software" into the requested product owner and its reference simulation
capability into the task, operational constraint, and terminal proof. Citation
bytes and structural validation passed, but semantic authority did not: a
transaction was staged where one focused `first_path` clarification with no
transaction was required. Independent source-first adjudication confirms P1;
the fixed expectation is not an evaluator error. No governed publication
occurred. Retained evidence:
`/private/tmp/odylith-public40-dc1dd6a08-evidence/public40.v1.json` and
`retained/release-agriculture-030-source/` beneath that evidence root.

The same campaign passed the former `release-agriculture-037-source` latency
blocker in `138.533s` through proposal, committed a 5/5/5 package, and passed
browser checks. Compact output is therefore a useful latency improvement,
but it does not repair this source-authority regression. The current
single-authority candidate fails the predeclared public release gate; do not
add another author instruction, parser, regex, retry, or case-specific rule.
The missing invariant is that separately identified reference provenance
cannot supply the requested product's owner/task/result witness unless the
operator explicitly binds it into that product path. A different ownership
regime or a deliberately narrower product input contract requires a bounded
decision and fresh end-to-end proof before Greenfield release qualification.

## V37 source-repository title recurrence (2026-09-27)

The retained V37 mobility case completed its one host-author call in
`82.733s`, produced a schema-valid candidate, and reached independent review.
The candidate selected `bluesky` from the source-repository metadata as the
accepted product title even though the source explicitly requested a program
lead's readiness-dossier workflow. Independent review correctly denied
`candidate.accepted_source.facts.title`; proposal exited `2`, no transaction
was staged, and all retained artifact hashes verified.

This is the host-native form of the existing source-metadata custody defect,
not a provider, timeout, citation-parser, or transaction failure. The author
schema gives `title` no semantic role while the reviewer already judges that
role. Move the product-title meaning into one shared author/reviewer contract:
the title identifies the requested product, workflow, or owned state, and a
repository or evidence artifact is eligible only when the source explicitly
makes it the product identity. Preserve exact citation custody and the
independent denial. Do not add lexical exclusions, repository-name rules,
regexes, retries, repair, fallback, or another model call.

V38 now shares one title-role definition between the author schema and the
read-only reviewer and versions those contracts as intent-authoring v74 and
candidate-review v13. The complete Greenfield runtime family passes 2,011
tests and deterministic author/reviewer contract proof is green. This record
stays in progress until a fresh provider-backed replay proves that the
mobility-shaped recurrence no longer reaches reviewer denial.

- Status: InProgress

- Created: 2026-08-09

- Severity: P1

- Reproducibility: Consistent

- Type: Product

- Description: Source-only evidence was stripped by prompt_intent_source, then re-admitted by the raw-text grounded-human-action helper. Materialization generated an Untitled Project with Representative user and accepted product details instead of asking for the missing first complete task.

- Impact: A first-time user can receive a polished but invented project package when they supplied evidence without product intent.

- Components Affected: domain-intelligence-greenfield

- Environment(s): Odylith 0.1.15 source-local Greenfield pre-confirm materialization

- Detected By: Full confirmed-intent recovery regression and direct typed-intent inspection

- Failure Signature: Source evidence, Source repository, or Repository description containing an actor action produced generic product truth instead of GreenfieldClarificationRequired.

- Trigger Path: Materialize a Greenfield prompt whose only content is a source-metadata field with a plausible actor action.

- Ownership: Greenfield Product Intent evidence-custody and materiality boundary

- Timeline: Captured 2026-08-09 through `odylith bug capture`.

- Blast Radius: Any Greenfield request containing source metadata without a separate product-intent statement

- SLO/SLA Impact: Violates the pre-confirm evidence custody and consumer-utility gate; blocks release readiness.

- Data Risk: No repository write occurred in the direct repro, but an invented package could be staged for confirmation.

- Security/Compliance: Security posture: no direct exposure was observed. Compliance and policy posture: provenance and review trust are compromised when evidence metadata is promoted into accepted product facts.

- Invariant Violated: Evidence metadata may inform interpretation but cannot become product truth; materially missing first-path intent must produce one focused no-write question.

- Root Cause: The shared grounded-human-action helper scanned raw evidence instead of the product-only evidence view already owned by product_intent_source_text.

- Solution: Run grounded human-action detection only over product_intent_source_text and prove source-only prompts ask one first-task question without staging.

- Rollback/Forward Fix: Forward fix only; post-confirm repair remains forbidden.

- Verification: The source-only and prompt-plus-source focused pack passed 6 tests. The complete confirmed-intent recovery file passed 100 tests, including all three previously failing source-metadata labels, and the disclosed retired holdout passed all 124 regressions. Each source-only case raises one first-task question and leaves no Greenfield staging directory.

- Prevention: All materiality helpers must consume the same product-only evidence view before scoring title, actor, or path sufficiency.

- Agent Guardrails: Never repair missing Product Intent by generating generic product facts from source metadata.

- Preflight Checks: Require zero staging for source-only evidence and full prompt-plus-source preservation before release.

- Regression Tests Added: tests/unit/runtime/test_greenfield_confirmed_intent_recovery.py::test_source_metadata_only_requires_a_first_path_question

- Monitoring Updates: Release proof should report source-only evidence custody failures separately from ordinary material clarification.

- Version/Build: 0.1.15 branch 2026/freedom/v0.1.15

- Related Incidents/Bugs: CB-303

- GitHub Status: fixed_pending_release

- Fixed In: 0.1.15

- Public Response: pending

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_prompt_intent_materialization.py

## Host-Native V19 Reopen (2026-09-25)

The exact v19 public campaign reproduced this failure class through the current
host-native boundary. Astra returned an authored candidate for a source-only
civic-tech topic whose repository description invited people to catalog
projects but did not establish a product actor or complete product path. The
independent reviewer correctly denied the candidate at
`candidate.accepted_source.events[0].actor_fact`; proposal exited `2` after
`67.461s`, and the write audit proved zero staged or governed writes.

The earlier product-only evidence-view fix did not survive the mechanism shift
to one external host candidate plus one independent review. The bounded
replacement is not another parser or prompt cascade: the existing independent
review returns one typed outcome—admit, material clarification, or deny. A
source-insufficient candidate terminates as the canonical no-write
clarification; a source-sufficient but incorrect candidate remains denied. No
candidate revision, retry, repair, fallback, or additional model call is
permitted. CB-329 owns the separate raw-response retention and release-evaluator
classification defects exposed by the same case.
