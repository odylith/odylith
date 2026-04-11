# Security And Trust

## CLI-First Non-Negotiable
- CLI-first is non-negotiable for both Codex and Claude Code. Remove all hand-authoring for places where Odylith CLI should be doing the heavy-lifting. When an Odylith CLI command exists for an operation, you must call the CLI command and you must not hand-edit governed files the CLI owns. Hand-authoring governed truth where a CLI exists is a hard policy violation, not a stylistic preference. The authoritative policy, CLI surface enumeration, allowed hand-edit surfaces, and failure-mode handling live in `odylith/agents-guidelines/CLI_FIRST_POLICY.md`, anchored by Casebook learning `CB-104`. The rule travels through routed `spawn_agent` leaves on Codex and Task-tool subagents on Claude Code, so delegated work inherits the same contract.

## Security Boundary
- Treat the repo launcher, the managed runtime, the repo-root trust anchor,
  and the signed release asset path as one connected trust boundary.
- Fail closed when runtime trust is ambiguous. Do not widen into host Python
  or insecure local asset overrides just to keep work moving.
- `source-local` is an explicit maintainer development posture, not a
  tamper-proof or release-eligible runtime.

## Lane Rules
- Consumer lane:
  - use only the verified managed runtime behind `./.odylith/bin/odylith`
  - reject `ODYLITH_RELEASE_BASE_URL`,
    `ODYLITH_RELEASE_ALLOW_INSECURE_LOCALHOST`, and
    `ODYLITH_RELEASE_SKIP_SIGSTORE_VERIFY`
  - treat `.odylith/trust/managed-runtime-trust/` as the gitignored
    local trust anchor for managed-runtime integrity
  - allow legacy `0.1.0` and `0.1.1` compatibility only long enough to
    bootstrap onto a newer trusted release
- Pinned dogfood:
  - same trust expectations as consumer lane
  - use this posture for shipped-runtime proof
- Detached `source-local`:
  - validate wrapper and source-root integrity
  - do not describe this posture as immutable or release-grade

## Runtime Integrity Rules
- The launcher must only execute trusted managed runtimes or validated
  maintainer wrappers.
- Legacy `0.1.0` and `0.1.1` managed runtimes are compatibility exceptions,
  not full-trust peers; prefer repairing or upgrading away from them.
- Managed-runtime trust must live outside `.odylith/` so runtime-only tamper
  cannot rewrite its own proof.
- Hot-path verification happens before `odylith.cli` import; deeper tree
  verification belongs in doctor, repair, and same-version runtime reuse.
- Feature packs only attach to already trusted managed runtimes.

## Supply-Chain Rules
- Release assets must come from trusted hosts and verify against the expected
  Sigstore signer identity plus OIDC issuer.
- Canonical workflows should pin first-party GitHub Actions to immutable SHAs,
  pin the runner image, and avoid floating maintainer tooling installs.
- Local hosted-release overrides are maintainer-only rehearsal tools and must
  stay unavailable in consumer posture.

## Process-Lifetime Rules
- Treat unexpected long-lived Odylith Python helpers as bugs until proven
  otherwise.
- Startup, daemon readiness, timed-out child process groups, and worker
  shutdown should all fail closed.
- After runtime or daemon changes, explicitly verify that Odylith-owned Python
  processes exit when the command or timeout path is complete.

## Canonical Commands
```bash
./.odylith/bin/odylith version --repo-root .
./.odylith/bin/odylith doctor --repo-root . --repair
./.odylith/bin/odylith reinstall --repo-root . --latest
./.odylith/bin/odylith context-engine status --repo-root .
make release-candidate
```
