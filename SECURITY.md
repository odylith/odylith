# Security Policy

Last updated: 2026-05-03

## Supported Versions

Odylith is GA on supported public install platforms.

Public GitHub releases are live. This release branch prepares `v0.1.13` as
the next supported line; after publication, operators should treat older
releases as upgrade targets before expecting fixes. Security reports are
handled on a best-effort basis, with the supported release posture defined
below.

| Version | Supported |
| --- | --- |
| Current release line (`v0.1.13`) | Yes, best effort |
| Older published releases | Upgrade to the latest release before expecting a fix |
| `main` | Development branch only; may contain unreleased changes |

## v0.1.13 Security-Relevant Prep

The `v0.1.13` release prep must keep these security-relevant boundaries
explicit in release notes, README/operator guidance, release-preflight proof,
and the bundled security posture docs:

- Consumer installs stay on the pinned, verified managed runtime. Detached
  `source-local` remains maintainer-only and release-ineligible.
- Greenfield Domain Intelligence may propose from user intent, but it must keep
  observed source, user intent, and Odylith assumptions separate. It must not
  claim source evidence that does not exist.
- `odylith greenfield apply` is write-capable only after explicit
  confirmation. Apply-time validation must reject missing host-authored Atlas
  Mermaid source, duplicated topology, invalid evidence tiers, and incomplete
  proposal sections before any governed file changes.
- Host adapters for Codex, Claude Code, and future hosts must preserve user
  settings additively and must not replace host configuration with
  Odylith-only templates.
- Release migration proof must include changed public docs, browser-rendered
  governance surfaces, install-managed assets, and security-facing docs through
  `odylith release migration-gate --target-version 0.1.13`.
- Release prep must avoid duplicating expensive full-suite and consumer
  rehearsal proof after the same candidate artifact is already proven; the
  release record should name the accepted proof rather than silently rerunning
  unrelated gates.

## Reporting A Vulnerability

Do not report security vulnerabilities in public GitHub issues, pull requests,
or discussion threads.

Use the repository security reporting path on GitHub when private reporting is
enabled for the repository.

If private security reporting is not available in the repository UI, do not
publish exploit details in a public issue. Open a minimal GitHub issue that
requests secure follow-up without including sensitive details.

Please include:

- a short summary of the issue
- affected versions, tags, or commit SHAs
- reproduction steps or proof-of-concept details
- impact and blast-radius assessment if known
- any suggested mitigation or fix

## Response Expectations

- This project does not currently offer a commercial security SLA.
- Reports are handled on a best-effort basis.
- You may receive follow-up questions before triage is complete.
- If the report is accepted, the goal is coordinated disclosure after a fix or
  mitigation is ready.

## Scope Notes

- Install, upgrade, rollback, release-asset verification, and local runtime
  boundaries are in scope.
- Third-party services or host platforms are only in scope to the extent that
  Odylith's own code, packaging, or documented workflow uses them.
- Secrets accidentally committed to a fork or consumer repository should still
  be reported privately if Odylith behavior materially contributed to the
  exposure.
