# Greenfield proposal, confirmation, and recovery

Greenfield creates a reviewable governance package, not application code or a
deployed service. This procedure describes the current source contract; it does
not qualify an unreleased model profile or establish package-wide atomicity.
Check the [versioned operating envelope](../specs/greenfield-operating-envelope.md)
for supported evidence, filesystem assumptions, hosts, profile caps, and current
proof limitations. Use the installed repository's `odylith` command from its root.

## Prepare and propose

Run `odylith start --repo-root .`. If the installed runtime is in doubt, inspect
`odylith version --repo-root .`; use the
[install and upgrade runbook](../../odylith/INSTALL_AND_UPGRADE_RUNBOOK.md) for an
authorized repair. Do not switch runtime versions silently to obtain a passing
proposal. Preserve any existing pending transaction or recovery journal.

Use `odylith greenfield propose --repo-root . --prompt "<project evidence>"`.
Supply the user's actual request. Prompts, pasted Markdown, edits, extracted
documents, and model output are evidence, not execution authority. Do not
hand-author a proposal JSON file or repair a staged package by editing its files.

Select the v13 budget before starting: `auto`/`standard` must finish below 90
seconds, explicit `rescue` below 120 seconds, and explicit `deep` below 150 seconds.
Sixty seconds is an advisory normal-case proposal target; the separate commit-only
step must still finish below 60 seconds. Historical trials retain their original
budgets and verdicts. Model windows are 55/80/105 seconds and the reviewer is
bounded to 20 seconds within the remaining model window. A timeout never promotes the request to another
tier. The default proposal already compiles the complete package; `--detail`
does not defer missing artifacts until confirmation.

The useful result is a sealed preview, one material question, an actionable
unsupported-evidence notice, or a separated environment/transaction outcome.
Do not relay internal parsing retries as product guidance. A material answer
becomes additional evidence; a non-material omission can remain an explicit
assumption. Never invent a user, external dependency, authority, or source fact.

## Review and choose

Review the product story, first complete path, source constraints, actors,
external systems, proposed ownership boundaries, assumptions, and proof. Check
that Radar, Registry, and Atlas explain different responsibilities instead of
repeating one paragraph. Counts alone do not prove useful governance depth.

The preview's `Choose one command` block carries the exact transaction hash:

- `CONFIRM <hash>` authorizes only that sealed package.
- `EDIT <hash> <corrections>` supplies new evidence and builds a new package and
  hash. It does not modify the old confirmed package.
- `REJECT <hash>` publishes no governed records.

Use the eligible host's deterministic confirmation callback. It must pass the
reviewed identity directly to the commit kernel, without another semantic model
turn. Hosts without that callback may display read-only proposals, not offer a
governed write. Never infer confirmation from an unrelated “yes” or ask for a
second approval of unchanged bytes.

The commit CLI is `odylith greenfield create`; inspect its `--help` for the
transaction-file, transaction-hash, and confirmation arguments. It is not a
replacement authoring path. Only invoke it with the exact previously reviewed
transaction and the user's applicable confirmation. Do not regenerate artifacts,
change preconditions, or repair copy after that authorization.

## Completion checks

Keep the returned receipt, transaction hash, and committed dashboard path. Verify
readback and open the committed dashboard when supported; otherwise return its
exact absolute path and one next action. Do not open staging or test pages as the
consumer's project. Browser-opening failure does not undo successful publication.

Check Project, Radar, Registry, Atlas, and Compass for the same project meaning,
valid navigation, complete prose, and no unrequested program/wave records. This
manual check complements, but does not replace, the desktop/mobile normal,
empty/fallback, and degraded/error browser matrix required for release.

## Interrupted or rejected publication

Distinguish the outcome before acting:

- `BUSY_NO_WRITE`: another writer owns the lock. Observe that operation's actual
  process or terminal outcome; do not delete the lock or launch overlapping work.
  Retry the same authorized transaction only after the owning operation settles.
- `STALE_TRANSACTION`: repository preconditions no longer match. Do not force
  the old package through. Obtain a new preview for the current repository and
  a new confirmation if the reviewed package changes.
- An already-active repeated hash returns its existing receipt. Preserve that
  identity rather than creating a duplicate project to recover a lost response.
- `RECOVERY_REQUIRED` or an uncertain post-publication outcome: preserve staged
  bytes, journal, immutable generation, and active-generation evidence. Do not
  delete them, silently roll back an observed package, or run a new semantic
  compiler as “repair.” Inspect the exact transaction and use its supported
  deterministic recovery path; if the current CLI cannot settle it, retain the
  evidence and report the specific transaction/environment failure.

Before publication, an abort must leave governed truth unchanged. After an
observed publication, verification or explicit recovery owns the next action;
a changed compensating package needs its own review. Clean temporary assets only
after authoritative state proves them terminal and no recovery depends on them.
The current envelope's journaled-recovery limitation must not be described as
universal all-old/all-new visibility for every repository reader.
