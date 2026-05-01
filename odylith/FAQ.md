# Odylith FAQ

## What is Odylith?

Odylith is the repo-local operating layer for AI coding agents. It adds
grounding, governed memory, delivery surfaces, and execution helpers under
`odylith/`, while the managed runtime lives under `.odylith/`.

## Should I clone Odylith to use it here?

No.

If this repo already carries Odylith, use the repo-local launcher:

```bash
./.odylith/bin/odylith doctor --repo-root .
```

## What should I use for updates?

```bash
./.odylith/bin/odylith upgrade --repo-root .
```

In consumer repos, that moves Odylith to the latest verified release and
advances the local repo pin. In the Odylith product repo, it follows the
tracked self-host pin.

If a consumer repo is still on the legacy `0.1.0` or `0.1.1` launcher, rerun
the hosted installer once from that repo root, then use `upgrade` normally:

```bash
curl -fsSL https://odylith.ai/install.sh | bash
```

If you want the active runtime and tracked repo pin aligned to the latest
verified release in one step, use:

```bash
./.odylith/bin/odylith reinstall --repo-root . --latest
```

To check for a newer release without upgrading:

```bash
./.odylith/bin/odylith version --repo-root . --check-upgrade
```

That remote advisory check is cached for seven days by default under
`.odylith/state/upgrade-check.v1.json`. Use `--force-upgrade-check` to bypass
the cache, `--upgrade-check-offline` to read cache only, or
`ODYLITH_UPGRADE_CHECK=off` to disable remote advisory checks in locked-down
enterprise networks. The check is advisory only; `odylith upgrade` still does
the signed release verification.

## What should I use for repair?

```bash
./.odylith/bin/odylith doctor --repo-root . --repair
```

If local cache or derived runtime state looks compromised, use:

```bash
./.odylith/bin/odylith doctor --repo-root . --repair --reset-local-state
```

## How do I turn Odylith off without deleting context?

```bash
./.odylith/bin/odylith off --repo-root .
./.odylith/bin/odylith on --repo-root .
```

`off` removes the Odylith block from supported repo-root guidance files such
as `AGENTS.md` and `CLAUDE.md`, but keeps the runtime and `odylith/` tree in
place. `on` restores those blocks and puts Odylith back on the default first
path.

## What does uninstall remove?

```bash
./.odylith/bin/odylith uninstall --repo-root .
```

That preserves the local `odylith/` governed source truth, removes
`.odylith/` local runtime state, and detaches Odylith blocks from supported
repo-root guidance files such as `AGENTS.md` and `CLAUDE.md`. It does not
remove host configuration directories such as `.claude/`, `.codex/`, or
`.agents/`. Do not uninstall with raw `rm` or Python deletion.

## What does Odylith own in this repository?

Odylith owns:

- `odylith/`
- `.odylith/`
- the Odylith block in supported repo-root guidance files such as
  `AGENTS.md` and `CLAUDE.md`

Everything else stays owned by the surrounding repository unless that
repository says otherwise.

## Does Odylith copy the repository's plans, bugs, specs, or diagrams into itself?

No.

Odylith reads repo truth in place. It ships product code and product assets;
it does not absorb the surrounding repository's source-of-truth records.

## Where should I start?

For the default grounded first turn, use:

```bash
./.odylith/bin/odylith start --repo-root .
```

Then read:

- [INSTALL.md](INSTALL.md)
- [OPERATING_MODEL.md](OPERATING_MODEL.md)
- [PRODUCT_COMPONENTS.md](PRODUCT_COMPONENTS.md)
- [surfaces/GOVERNANCE_SURFACES.md](surfaces/GOVERNANCE_SURFACES.md)
- [runtime/TRIBUNAL_AND_REMEDIATION.md](runtime/TRIBUNAL_AND_REMEDIATION.md)
