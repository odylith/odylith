.PHONY: help validate dev-validate dev-refresh license-audit lane-show benchmark-analysis release-version-preview release-version-show release-session-show release-session-clear release-candidate release-preflight release-dispatch dogfood-activate consumer-rehearsal ga-gate

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
