# Security Policy

Last updated: 2026-04-07

## Supported Versions

Odylith is GA on supported public install platforms as of 2026-04-07.

Public GitHub releases are now live. The latest published release is `v0.1.9`,
published on 2026-04-07. Security reports are handled on a best-effort basis,
with the supported release posture defined below.

| Version | Supported |
| --- | --- |
| Latest published release (`v0.1.9` as of 2026-04-07) | Yes, best effort |
| Older published releases | Upgrade to the latest release before expecting a fix |
| `main` | Development branch only; may contain unreleased changes |

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
