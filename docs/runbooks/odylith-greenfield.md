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

Run `odylith greenfield prepare --repo-root . --prompt "<project evidence>"`.
Supply the actual request unchanged. The supported product-owned parent acquires
contracts, supervises the authority gate, source-duty inventory, source-only
verification and one candidate, then returns one question or a sealed preview.
Use `--format json` only when a machine-readable result is needed. Codex and
Claude orchestration hosts share this route; inference remains the pinned direct
Codex Astra-medium profile. Missing Codex is an explicit no-write environment
outcome, never a reason to silently change profiles.

The standard gate/candidate window is shared 300 seconds plus 15 seconds of
completion reserve. Inventory has a 300-second cap, verifier 120, and each ledger
check 30. The entire supervised journey has a fixed 660-second diagnostic cap
and a separate two-second cancellation grace, including blocked native callbacks.
Advisory 90/120/150-second targets are not admission gates. A qualified measured
whole-flow release bound remains pending. No model or semantic/provider call may
follow candidate receipt. Independent release review cannot decide a consumer
transaction. Separate file-based commands remain available; their receipts prove
source custody and local validation, not execution under the live parent.

The useful result is a sealed preview, one material question, an actionable
unsupported-evidence notice, or a separated environment/transaction outcome.
Do not add a full-candidate reviewer, parser, regex extraction pass, repair,
retry, fallback candidate, or alternate model ladder. No model call follows
candidate receipt. Do not relay internal parsing retries as product guidance. A material answer
becomes additional evidence; a non-material omission can remain an explicit
assumption. Never invent a user, external dependency, authority, or source fact.

## Review and choose

Review the product story, first complete path, source constraints, actors,
external systems, proposed ownership boundaries, assumptions, and proof. Check
that Radar, Registry, and Atlas explain different responsibilities instead of
repeating one paragraph. Counts alone do not prove useful governance depth.

Previews publish nothing. A bounded `prepare` preview prints three full,
shell-quoted terminal choices using its transaction hash and delivered
completion receipt:

```sh
odylith greenfield decide --repo-root '<path>' CONFIRM '<hash>' --completion-receipt '<receipt-file>'
odylith greenfield prepare --repo-root '<path>' --transaction-hash '<hash>' --completion-receipt '<receipt-file>' --edit '<corrections>'
odylith greenfield decide --repo-root '<path>' REJECT '<hash>' --completion-receipt '<receipt-file>'
```

Use the exact printed paths and hash. EDIT may use `--edit-evidence '<file>'`
instead of `--edit`. Keep the delivered receipt private and unchanged; stored
diagnostic records cannot replace it. Ordinary chat approval, host names, and
hook registration do not authorize these decisions.

`CONFIRM` and `REJECT` use the shared bounded deterministic owner and never run a
compiler or model. EDIT starts one new bounded journey using the retained source
plus correction, preserves the old seal and receipt, and returns a new seal and
receipt on success. A failed EDIT preserves the original package.

Unmarked file-based previews retain their source-custody contract and print
`decide` choices without a completion receipt. Their explicit `decide EDIT`
interface requires the correction, gate, candidate and admitted ledger files;
those files do not establish the complete parent deadline.

The commit CLI is `odylith greenfield create`; inspect its `--help` for the
transaction-file, transaction-hash, and confirmation arguments. It is not a
replacement for `decide` or an authoring path. Only invoke it with the exact
previously reviewed transaction and the user's applicable confirmation. Do not
regenerate artifacts, change preconditions, or repair copy after that authorization.

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
- A preparation delivery failure after certification is an accepted-or-unknown
  environment outcome. Preserve the sealed package and any delivered receipt.
  A lost completion receipt is not reissued and can leave the package
  unconfirmable; diagnostic records do not grant confirmation authority.
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

## Explicit working-file restoration

An ordinary governance command can fail after changing working projections while
the published generation remains intact. When no transaction journal owns that
failure, do not fabricate one or reset the published generation. The source
command `odylith governance restore-published-files` offers a separately reviewed,
working-only restoration from the current publication; it is not a Greenfield
CONFIRM or a retry of the failed renderer.

Use `--preview --path <repository-relative-file>` with one repeated `--path` for
each intended file. Review the exact targets, current and published hashes,
modes, repository identity, and publication identity in the resulting receipt.
Preview preserves current bytes and creates no publication. Apply only the
printed `--apply <review-hash>` command after review; changing targets or intent
requires a new preview. Prefer generated failure residue over authored records;
never select a directory or discard unrelated work to make admission pass.

Apply preserves the failed bytes in its receipt, uses the shared repository lock,
and restores only the selected sealed bytes and modes. All other managed files
and the active publication must remain unchanged. Missing or unsafe paths,
unselected drift, changed publication, and third-state target bytes cause refusal.
If apply is interrupted, retain its receipt and resume the same hash. Canonical
governed writes, Greenfield commit, and baseline activation refuse while an
admitted restoration is unclosed. Do not delete the receipt to clear that refusal.

A prepared Compass log receipt whose event reached only the working canonical
stream is a narrower case: the published stream is still unchanged and remains
the append-only historical authority. Use only this reviewed sequence:

```sh
odylith governance restore-published-files --repo-root . --preview --path odylith/compass/runtime/agent-stream.v1.jsonl
odylith governance restore-published-files --repo-root . --apply <restoration-review-hash>
odylith compass log --repo-root . --abandon-restored <restoration-review-hash> --receipt-hash <original-compass-receipt-sha256>
```

Abandonment requires the restoration to be closed, archives the exact unpublished
event and original receipt, and removes only that prepared continuation. It never
removes published history, replays the event, renders Compass, or treats a changed
runtime as authority to complete the old writer.

After verified closure, explicitly sync the intended authored source paths through
their normal owner. Restoration itself does not render, publish, repair semantic
content, or prove that a previously failed command will now succeed. This is a
current-source contract; installed availability and release qualification require
their own proof.
