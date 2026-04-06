# Odylith FAQ

## What is Odylith?

Odylith is the product layer that provides context-engine commands,
governance and delivery-intelligence surfaces, guidance, skills, and
execution helpers under `odylith/`.

## Should I clone Odylith to use it here?

No.

In repos that already carry Odylith, use the repo-local launcher:

```bash
./.odylith/bin/odylith doctor --repo-root .
```

For the default grounded first turn, use:

```bash
./.odylith/bin/odylith start --repo-root .
```

## What should I use for updates?

```bash
./.odylith/bin/odylith upgrade --repo-root .
```

That moves Odylith to the latest verified release and advances the local repo
pin.
`odylith upgrade` also tells you explicitly whether it actually moved versions,
whether it only advanced the repo pin, and what changed in the release when
that metadata is available.

If you want a one-step verified restage plus pin alignment, use:

```bash
./.odylith/bin/odylith reinstall --repo-root . --latest
```

If you only need the shell current without a full governance sync, use:

```bash
./.odylith/bin/odylith dashboard refresh --repo-root .
```

If a consumer repo is still on the legacy `0.1.0` or `0.1.1` launcher, rerun
the hosted installer once from that repo root to refresh the launcher, then
use `./.odylith/bin/odylith upgrade --repo-root .` normally after that:

```bash
curl -fsSL https://github.com/freedom-research/odylith/releases/latest/download/install.sh | bash
```

## What should I use for repair?

```bash
./.odylith/bin/odylith doctor --repo-root . --repair
```

If the local cache, tuning, or derived runtime state looks compromised, use:

```bash
./.odylith/bin/odylith doctor --repo-root . --repair --reset-local-state
```

If `./.odylith/bin/odylith` itself is missing, use:

```bash
./.odylith/bin/odylith-bootstrap doctor --repo-root . --repair
```

## How do I turn Odylith off without deleting context?

```bash
./.odylith/bin/odylith off --repo-root .
./.odylith/bin/odylith on --repo-root .
```

`off` removes the Odylith block in the root `AGENTS.md` file but keeps the
local runtime and `odylith/` context in place, so Codex falls back to the
surrounding repo's default behavior. `on` restores that block and puts Odylith
back on the always-on first path for grounded turns.

## What does uninstall remove?

```bash
./.odylith/bin/odylith uninstall --repo-root .
```

That removes the repo-local runtime integration under `.odylith/` and the
Odylith block in the root `AGENTS.md` file, but it leaves the `odylith/`
context tree in place.

## What does Odylith own in this repository?

Odylith owns:

- `odylith/`
- `.odylith/`
- the Odylith block in the repository root `AGENTS.md`

Everything else remains owned by the surrounding repository unless that
repository explicitly says otherwise.

## Does Odylith copy the repository's plans, bugs, specs, or diagrams into itself?

No.

Odylith reads repo-local truth in place. It provides product code and product
assets, not the surrounding repository's source-of-truth records.

## Where should I start?

Read these first:

- `INSTALL.md`
- `OPERATING_MODEL.md`
- `PRODUCT_COMPONENTS.md`
- `surfaces/GOVERNANCE_SURFACES.md`
- `runtime/SUBAGENT_OPERATIONS.md`
