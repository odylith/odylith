# Odylith GTM and Release Checklist

Last updated: 2026-04-03

Use this with [Maintainer Release Runbook](../MAINTAINER_RELEASE_RUNBOOK.md).
The runbook is the canonical command order. This checklist is the reusable
launch-readiness, narrative-alignment, and asset-review overlay for any Odylith
release.

## How To Use It
- Replace `[version]` and `[previous_version]` with the candidate release
  before launch review starts.
- Treat every unchecked blocker as real release debt, not launch-day cleanup.
- Publish only claims backed by the current proof report, current release-note
  source, and current hosted assets.

## Narrative Lock
- [ ] One-sentence launch statement is finalized for `[version]`.
- [ ] The three release pillars are locked and non-overlapping.
- [ ] Audience framing is explicit: elite developers, reviewers, and
      architects who will inspect trust, proof, and operator ergonomics.
- [ ] Claim boundaries are explicit: what Odylith proved, what improved, what
      did not improve, and what remains blocked.

## Claim Guardrails
- [ ] Public benchmark claims come from the latest `proof` report and the
      conservative published view, not warm-only or diagnostic-only data.
- [ ] No one claims the hard quality gate cleared unless the report says it
      cleared.
- [ ] No one claims write behavior improved unless the report shows it.
- [ ] Supported-platform claims match the maintained runtime contract exactly.
- [ ] Popup, release note, GitHub release body, README, and launch posts tell
      the same story with the same proof boundary.

## Product Truth And Release Assets
- [ ] Version truth is aligned across `pyproject.toml`, generated version
      surfaces, authored release notes, and bundled mirrors.
- [ ] The release popup uses a short left-side brief that does not duplicate
      the full release note.
- [ ] The full release-note page has no clipped copy, duplicate narrative, or
      layout regressions.
- [ ] The GitHub release title and body match the final approved launch
      narrative.
- [ ] The repo-root `README.md` benchmark snapshot and `docs/benchmarks/*.svg`
      are refreshed from the current report.
- [ ] Screenshots, demos, or walkthrough captures are current for the popup,
      release note, benchmark views, and key shell surfaces.
- [ ] Built-in release-surface controls work end to end in browser coverage.

## Proof And Benchmark Integrity
- [ ] Run `./.odylith/bin/odylith benchmark --repo-root . --profile proof`.
- [ ] Regenerate benchmark graphs from the same `latest.v1.json` report.
- [ ] Refresh the published README benchmark snapshot from that same report.
- [ ] Review wins and regressions against the last shipped release, not just
      against `odylith_off`.
- [ ] Review hard-gate status, warm-cold consistency, and any `hold` posture
      before ship/no-ship.
- [ ] Confirm launch copy describes both the strongest wins and the material
      regressions honestly.

## Canonical Release Lane
- [ ] `make release-version-preview`
- [ ] `make release-version-show`
- [ ] `make release-preflight [VERSION=[version]]`
- [ ] `make release-session-show`
- [ ] `make release-dispatch`
- [ ] Wait for the canonical GitHub release workflow to finish cleanly.
- [ ] `make dogfood-activate`
- [ ] `./.odylith/bin/odylith validate self-host-posture --repo-root . --mode local-runtime`
- [ ] `make consumer-rehearsal PREVIOUS_VERSION=[previous_version]`
- [ ] `make ga-gate PREVIOUS_VERSION=[previous_version]`
- [ ] `make release-session-clear`

## GTM Package
- [ ] GitHub release copy is finalized and proof-linked.
- [ ] The short launch post is drafted and reviewed.
- [ ] The longer technical launch post or thread is drafted and reviewed.
- [ ] One architecture or trust-boundary visual is ready.
- [ ] One benchmark-proof visual is ready.
- [ ] One product-surface or operator-cockpit visual set is ready.
- [ ] Objection-handling notes are ready for trust, latency, supported
      platforms, and benchmark caveats.

## Day-Of Launch
- [ ] Publish the GitHub release.
- [ ] Verify the release tag, hosted assets, and release-note links resolve.
- [ ] Publish the primary launch announcement.
- [ ] Publish the longer technical post or thread.
- [ ] Verify GitHub renders the README and benchmark graphs correctly.
- [ ] Verify the popup and release-note links still resolve from the shipped
      runtime.

## Post-Launch Follow-Through
- [ ] Monitor install, upgrade, rollback, and doctor reports.
- [ ] Monitor questions about benchmark method, proof posture, and supported
      platforms.
- [ ] Capture meaningful launch objections or regressions into Casebook or
      Radar when they become product work.
- [ ] Decide within 24 hours whether follow-up messaging is required on proof
      regressions, platform scope, or launch clarifications.

## No-Ship Conditions
- [ ] Version truth is still split.
- [ ] The proof report is still on `hold` without explicit and honest public
      framing.
- [ ] Consumer rehearsal or GA gate failed.
- [ ] Popup, release note, GitHub release, README, and launch posts diverge.
- [ ] Built-in release surfaces still have clipped copy, dead links, or broken
      controls.
