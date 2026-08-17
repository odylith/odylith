GREENFIELD_FAST_TESTS := \
	tests/unit/runtime/test_greenfield_graph_authority_severance.py \
	tests/unit/runtime/test_greenfield_semantic_graph_v4_contract.py \
	tests/unit/runtime/test_greenfield_semantic_projection_plan.py \
	tests/unit/runtime/test_greenfield_semantic_release_custody.py \
	tests/unit/runtime/test_greenfield_semantic_artifact_consumers.py \
	tests/unit/runtime/test_greenfield_semantic_radar_write.py \
	tests/unit/runtime/test_greenfield_public_entry_contract.py \
	tests/unit/runtime/test_greenfield_semantic_preview_isolation.py \
	tests/unit/runtime/test_greenfield_postconfirm_fingerprint_boundary.py \
	tests/unit/runtime/test_greenfield_presentation_dependency_severance.py

GREENFIELD_LIFECYCLE_TESTS := \
	tests/unit/runtime/test_greenfield_host_confirmation.py \
	tests/unit/runtime/test_greenfield_host_routing.py \
	tests/unit/runtime/test_greenfield_commit_rollback.py \
	tests/unit/runtime/test_greenfield_transaction.py \
	tests/unit/runtime/test_greenfield_commit_journal.py \
	tests/unit/runtime/test_greenfield_transaction_provenance.py

.PHONY: help validate dev-validate dev-refresh license-audit lane-show benchmark-analysis release-version-preview release-version-show release-session-show release-session-clear local-release-assets greenfield-test-fast greenfield-test-lifecycle greenfield-mechanism-experiment greenfield-graph-release-proof release-candidate release-preflight release-dispatch dogfood-activate consumer-rehearsal ga-gate

help:
	@./bin/help

validate:
	@./bin/validate

dev-validate:
	@./bin/dev-validate

dev-refresh:
	@./bin/dev-refresh

license-audit:
	@./bin/license-audit

lane-show:
	@./bin/lane-show

benchmark-analysis:
	@OUT="$(OUT)" ./bin/benchmark-analysis

release-version-preview:
	@./bin/release-version-preview

release-version-show:
	@./bin/release-version-show

release-session-show:
	@./bin/release-session-show

release-session-clear:
	@./bin/release-session-clear

local-release-assets:
	@./bin/local-release-assets "$(VERSION)" "$(DIST)"

greenfield-test-fast:
	@.venv/bin/python -m pytest -q -m "not greenfield_lifecycle" $(GREENFIELD_FAST_TESTS)

greenfield-test-lifecycle:
	@.venv/bin/python -m pytest -q $(GREENFIELD_LIFECYCLE_TESTS)

greenfield-mechanism-experiment:
	@[[ -n "$(EXPERIMENT)" ]] || { echo "EXPERIMENT=/path/to/semantic-mechanism-experiment.json is required" >&2; exit 2; }
	@.venv/bin/python scripts/release/greenfield_semantic_mechanism_experiment.py --experiment-file "$(EXPERIMENT)" $(if $(OUTPUT),--output "$(OUTPUT)",)

greenfield-graph-release-proof:
	@./bin/greenfield-graph-release-proof "$(VERSION)" "$(DIST)"

release-candidate:
	@./bin/release-candidate "$(VERSION)"

release-preflight:
	@./bin/release-preflight "$(VERSION)"

release-dispatch:
	@./bin/release-dispatch "$(VERSION)"

dogfood-activate:
	@./bin/dogfood-activate

consumer-rehearsal:
	@./bin/consumer-rehearsal "$(VERSION)" "$(PREVIOUS_VERSION)"

ga-gate:
	@./bin/ga-gate "$(VERSION)" "$(PREVIOUS_VERSION)"
