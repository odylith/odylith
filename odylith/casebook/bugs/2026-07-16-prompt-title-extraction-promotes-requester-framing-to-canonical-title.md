- Bug ID: CB-256

- Status: Open

- Created: 2026-07-16

- Severity: P1

- Reproducibility: High

- Type: Product

- Description: The installed high-variance Greenfield campaign rejects the cli-extension-release-notes request before confirmation because title extraction promotes the prompt framing `Our developer-experience group needs a product` into the product title. That malformed title then propagates through Radar, Project Brief, next-step, and Registry prose, where the strict generated-copy gate correctly detects mid-sentence capitalization drift near `Our`.

- Impact: A concrete consumer request cannot reach the normal CONFIRM, EDIT, REJECT rail even though the package can be repaired automatically.

- Components Affected: domain-intelligence

- Environment(s): Fresh installed 0.1.15 seeded 240-case high-variance discovery campaign.

- Detected By: Installed campaign fail-fast cluster.

- Failure Signature: manifest.generated-copy-quality.radar-renderer.radar.artifactplanir-radar with mid-sentence capitalization drift near Our.

- Trigger Path: cli-extension-release-notes from tests/fixtures/greenfield-volume/developer-data-security.v1.json through bin/greenfield-matrix-campaign.

- Ownership: Domain Intelligence prompt-source title extraction and generated-copy quality enforcement.

- Timeline: Captured 2026-07-16 through `odylith bug capture`.

- Blast Radius: All `needs a product for [actor] to [action] [object]` prompts whose action complement is longer than the previous title-focus limit.

- SLO/SLA Impact: Pre-confirm compiler rejects otherwise usable intent after rescue, delaying deterministic confirmation.

- Data Risk: No write occurred; the rollback guard and commit-only path remained clean.

- Security/Compliance: No security or compliance impact.

- Invariant Violated: Repairable generated-copy defects must be repaired before confirmation rather than escaping as consumer-facing compilation failures.

- Root Cause: The specialized `needs a product for` extractor declined the long action-bearing complement, then the generic title fallback accepted the preceding requester predicate because it merely contained a product noun. Title casing later formatted that invalid source as `Our Developer-experience Group Needs a Product`; source-casing restoration was not involved.

- Solution: Extract the action object from bounded actor-led `needs a product for` requests before generic title fallback, and reject requester predicates such as `needs a product` as product-title candidates. Retain the strict capitalization quality gate.

- Rollback/Forward Fix: Forward fix in prompt-source title derivation; retain the strict capitalization quality gate.

- Verification: Replay the generated failed-subset packet with a fresh installed build, then resume the high-variance 240-case campaign.

- Prevention: Exercise request-framing, actor, action, and action-object separation before projections render; never let a requester predicate seed the canonical product title.

- Agent Guardrails: Do not weaken the capitalization gate or route the repair after CONFIRM.

- Preflight Checks: No generated package may contain mid-sentence casing drift; no post-confirm generation or repair is allowed.

- Regression Tests Added: Typed prompt-source and full confirmed-intent-to-proposal regressions cover the action-object title and prohibit requester framing; the installed failed-subset replay will prove the packaged fix.

- Monitoring Updates: Track the campaign fingerprint and generated-copy owner in Compass.

- Version/Build: 0.1.15 local distribution built from 07ddc59dd.

- Config/Flags: GREENFIELD_MATRIX_REQUIRE_HIGH_VARIANCE_STRESSORS=1; seeded discovery; stop after one failure cluster.

- Customer Comms: No customer communication; no governed records were written.

- Related Incidents/Bugs: CB-255

- GitHub Status: confirmed

- Public Response: pending

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_need_product_focus.py
- src/odylith/runtime/domain_intelligence/greenfield_confirmed_prompt_source.py

- Runbook References: - odylith/MAINTAINER_RELEASE_RUNBOOK.md
