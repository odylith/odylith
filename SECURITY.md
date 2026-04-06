# Security Policy

Last updated: 2026-03-27

## Supported Versions

Odylith is still in public preview.

As of 2026-03-27, Odylith has not yet published its first public GitHub
release. Until the first release exists, security fixes are handled on `main`
only and on a best-effort basis.

| Version | Supported |
| --- | --- |
| `main` | Yes, best effort while Odylith is pre-release |
| Published release tags | None published yet as of 2026-03-27 |

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
