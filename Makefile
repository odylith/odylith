GREENFIELD_FAST_TESTS := \
	tests/unit/runtime/test_greenfield_code_hygiene.py \
	tests/unit/runtime/test_greenfield_component_contract_profile_merge.py \
	tests/unit/runtime/test_greenfield_component_semantic_contract_quality.py \
	tests/unit/runtime/test_greenfield_component_spec_narrative_quality.py \
	tests/unit/runtime/test_greenfield_component_spec_quality.py \
	tests/unit/runtime/test_greenfield_confirmed_backlog_terms.py \
	tests/unit/runtime/test_greenfield_confirmed_diagrams.py \
	tests/unit/runtime/test_greenfield_confirmed_text.py \
	tests/unit/runtime/test_greenfield_domain_profile_quality.py \
	tests/unit/runtime/test_greenfield_preconfirm_patch_payload.py \
	tests/unit/runtime/test_greenfield_quality_lens_repair.py \
	tests/unit/runtime/test_greenfield_semantic_model_quality.py \
	tests/unit/runtime/test_greenfield_title_specificity.py \
	tests/unit/runtime/test_prose_grammar.py

GREENFIELD_LIFECYCLE_TESTS := \
	tests/unit/runtime/test_greenfield_cli_paths.py \
	tests/unit/install/test_greenfield_browser_surface_proof.py \
	tests/unit/runtime/test_greenfield_host_confirmation.py \
	tests/unit/runtime/test_greenfield_host_routing.py

.PHONY: help validate dev-validate dev-refresh license-audit lane-show benchmark-analysis release-version-preview release-version-show release-session-show release-session-clear local-release-assets greenfield-test-fast greenfield-test-lifecycle greenfield-preconfirm-matrix greenfield-matrix-generate-cases greenfield-matrix-shards greenfield-matrix-campaign release-candidate release-preflight release-dispatch dogfood-activate consumer-rehearsal ga-gate

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
	@.venv/bin/python -m pytest -q -m greenfield_lifecycle tests/unit/runtime/test_greenfield_domain_profile_quality.py

greenfield-preconfirm-matrix:
	@./bin/greenfield-preconfirm-matrix "$(VERSION)" "$(DIST)"

greenfield-matrix-generate-cases:
	@./bin/greenfield-matrix-generate-cases

greenfield-matrix-shards:
	@./bin/greenfield-matrix-shards

greenfield-matrix-campaign:
	@./bin/greenfield-matrix-campaign "$(VERSION)" "$(DIST)"

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
