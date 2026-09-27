- Bug ID: CB-346

- Status: Open

- Created: 2026-09-27

- Severity: P1

- Reproducibility: Medium

- Type: Product

- Description: The fresh sealed V31 holdout passed its first 16 executed cases at 10/10, then the ninth commit case produced no candidate before the host-native proposal deadline. The matrix recorded command_timed_out and case-execution-exception, stopped with three cases unexecuted, and failed the release gate. The consumed holdout must not be rerun or used for case-specific tuning.

- Impact: A semantically strong Greenfield mechanism cannot claim release qualification because one valid full creation request can exhaust the bounded host-model window and abort the one-shot holdout.

- Components Affected: domain-intelligence

- Environment(s): Immutable 0.1.15 V30 distribution from commit 2c88b068a262b5195c37e545f3fd550ba11539cf; sealed V31 20-case release holdout; Astra medium standard profile; full install, browser, recovery and release proof.

- Detected By: Exactly-once sealed Greenfield V31 final holdout.

- Failure Signature: Telemetry command_timed_out returncode 124 followed by case-execution-exception: host-native candidate proposal command returned nonzero; 16/17 executed cases passed before fail-closed stop.

- Trigger Path: scripts/release/greenfield_preconfirm_matrix.py release proof with the standard participant-first Astra-medium profile.

- Ownership: Greenfield host-candidate timing envelope and release qualification harness.

- Timeline: 2026-09-27: sealed hashes verified; invalid receipt flags rejected before consumption; true one-shot ledger created; cases 1-16 passed; case 17 timed out; remaining cases were not executed; commit-recovery proof passed; overall release proof failed.

- Blast Radius: Full Greenfield creation requests whose one required host reasoning call approaches the 165-second model window; clarification no-write requests remain fast and unaffected.

- SLO/SLA Impact: Violates the required every-request success outcome and blocks release despite remaining below the separate 180-second operational safety intent at the product level.

- Data Risk: No governed corruption: the failing case produced no candidate or transaction, and the matrix failed closed.

- Security/Compliance: No direct security or compliance impact observed.

- Invariant Violated: Every supported Greenfield request must either produce one grounded preview or one material clarification within the bounded operating envelope, with no retry or fallback author.

- Workaround: None for the consumed holdout. Preserve it as terminal evidence and keep completion unclaimed.

- Root Cause: The host-native candidate call exceeded the standard profile model deadline and caused the case-loop abort. Separate release-harness defects tracked by CB-347 then produced invalid qualification output: unavailable-provider proof stopped in argument parsing, and stale relation/model-observation schemas converted incomplete proof into false semantic P0/P1 findings. No semantic defect in the 16 passed cases is established by either failure.

- Solution: First close CB-347 so public comparisons produce trustworthy evidence. Then compare one bounded public control under Sol-high authoring versus the current Astra-medium authoring profile, retaining Astra as independent final semantic adjudicator. Select only a profile that improves tail latency without reducing semantic fidelity; fully requalify public evidence and commission one newly blind holdout. Do not add retries, repair, fallback authors, parser rules or protected-case patches.

- Rollback/Forward Fix: Forward-fix only; the V31 holdout is consumed and terminal.

- Verification: Public positive, negative, equivalent-source, browser and recovery controls must pass on one immutable build; independent strong semantic review must approve retained outputs; a newly sealed one-shot holdout must then pass completely within the 180-second safety envelope.

- Prevention: Preflight release commands against proof-tier policy and qualify the chosen host profile on tail latency before sealing a holdout.

- Agent Guardrails: Never rerun or inspect the consumed holdout for tuning. Do not convert this timeout into a regex, retry, repair loop, fallback model ladder or case-specific prompt rule.

- Preflight Checks: Verify immutable revision and distribution provenance; verify holdout ledger absence before the future run; verify interpreter/browser dependencies; verify release proof rejects stop-threshold flags; require clean public profile comparison first.

- Regression Tests Added: The existing public matrix is the required development regression surface; a new independent holdout may be run only after public profile qualification, never against this consumed case.

- Monitoring Updates: Track per-profile p50, p90, maximum proposal latency, timeout count, semantic score and no-write clarification behavior separately.

- Version/Build: 0.1.15 commit 2c88b068a262b5195c37e545f3fd550ba11539cf

- Config/Flags: proof-tier=release; install-mode=full; operational timeout=180s; standard model window=165s; model=gpt-6-astra; reasoning=medium

- Customer Comms: Release remains unclaimed; no consumer package is promoted from this evidence.

- Related Incidents/Bugs: CB-347, CB-303, B-142

- GitHub Status: confirmed

- Public Response: pending

- Code References: - scripts/release/greenfield_preconfirm_matrix.py
- src/odylith/runtime/domain_intelligence/greenfield_model_profile_contract.py
- src/odylith/runtime/domain_intelligence/greenfield_host_candidate.py

- Runbook References: - odylith/MAINTAINER_RELEASE_RUNBOOK.md
