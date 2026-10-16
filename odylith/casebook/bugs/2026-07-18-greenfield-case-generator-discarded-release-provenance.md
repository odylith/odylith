- Bug ID: CB-278

- Status: Open

- Created: 2026-07-18

- Severity: P1

- Reproducibility: Always

- Type: Test

- Description: The Greenfield case generator parsed source provenance from external seed cases but omitted it from generated case files. A legitimate source-provenanced corpus could therefore lose its release-admissible provenance before shard construction.

- Impact: Operational delivery risk: curated release evidence is silently downgraded, blocking an honest installed release proof after expensive corpus work.

- Components Affected: release

- Environment(s): Maintainer Greenfield corpus generation

- Detected By: Adversarial corpus provenance audit

- Failure Signature: Generated case row lacked provenance after source-provenanced input was selected.

- Trigger Path: Generate a case file from a source-provenanced external seed case and load the output for release shard construction.

- Ownership: Greenfield matrix case generator

- Timeline: Captured 2026-07-18 through `odylith bug capture`.

- Blast Radius: Every source-provenanced release-corpus candidate produced through generate_case_file.

- SLO/SLA Impact: Delivery and operational risk: release readiness is blocked and corpus curation must be repeated.

- Data Risk: Domain evidence-integrity risk: source identity, license, derivation, and hash lineage are lost from generated records.

- Security/Compliance: Security and compliance posture: no source text is exposed, but missing provenance weakens auditability for licensed source-derived evidence.

- Invariant Violated: A source-provenanced case must retain its exact provenance through every corpus-generation stage.

- Root Cause: The generator serializer did not include case.provenance while the loader and shard builder did.

- Solution: Serialize non-synthetic provenance with the shared case_provenance_to_dict helper and prove generator-to-loader round trip.

- Rollback/Forward Fix: Forward fix only; regenerate any affected corpus outputs from source evidence.

- Verification: .venv/bin/python -m pytest -q tests/unit/install/test_greenfield_matrix_case_generator.py tests/unit/install/test_greenfield_matrix_corpus_provenance.py

- Prevention: Use the shared provenance serializer at every case-file writer and test every writer-to-loader round trip.

- Agent Guardrails: Never treat a source-provenanced case as release-capable until serialization and reload retain its provenance unchanged.

- Preflight Checks: Validate generated corpus provenance before sharding or installed release proof.

- Regression Tests Added: test_case_generator_preserves_source_provenance_for_release_corpus_inputs

- Monitoring Updates: Release-corpus evaluation continues to fail closed when provenance is absent.

- Version/Build: 0.1.15 unreleased

- Config/Flags: No flags

- Customer Comms: None; maintainer release-evidence pipeline defect.

- Related Incidents/Bugs: CB-248,CB-275

- GitHub Status: fixed_pending_release

- Fixed In: 0.1.15

- Code References: - scripts/release/greenfield_matrix_case_generator.py
- tests/unit/install/test_greenfield_matrix_case_generator.py
