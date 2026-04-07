# Odylith Install And Upgrade

## Happy Path

- From the repository root you want to augment, run the release bootstrap command.
- The supported public install platforms are macOS (Apple Silicon) and Linux
  (`x86_64`, `ARM64`). Intel macOS and Windows are not supported in this
  slice.
- The bootstrap downloads release assets from GitHub, verifies the signed
  release manifest, managed runtime bundle, provenance, and SBOM, stages the
  product runtime under `.odylith/runtime/versions/<version>`, and creates
  `./.odylith/bin/odylith`.
- On supported platforms, first install does not depend on any preinstalled
  machine Python. The bootstrap uses Odylith's verified managed runtime bundle
  as its own bootstrap interpreter.
- Managed runtime bundles are built from pinned upstream Python archive
  digests, and the installer fails closed if those upstream inputs drift.
- The bootstrap also creates a minimal consumer-owned `odylith/` tree for local repo truth and bootstrap metadata. It does not copy a full Odylith source checkout into the consumer repository.
- The bootstrap also seeds `odylith/surfaces/brand/` so local Odylith HTML surfaces can resolve stable in-repo brand paths without reaching back into the product checkout.
- The bootstrap seeds `odylith/agents-guidelines/` as Odylith-managed guidance. That subtree may be refreshed later by install, upgrade, or doctor.
- The bootstrap also renders the first local HTML surfaces, including `odylith/index.html`, so the repo has an immediately viewable Odylith shell after install.
- On a successful first local install, Odylith also tries to open `odylith/index.html` automatically when the session is local and interactive.
- On a fresh repo, the shell opens on a welcome state with one chosen slice, copyable prompts for Backlog, Components, and Diagrams, and local auto-refresh when Odylith updates surfaces.
- If the repo is not Git-backed yet, that same shell shows reduced mode clearly instead of implying full repo intelligence.
- Odylith is meant to be used through an AI coding agent such as Codex or Claude Code. The agent is the execution interface, and `odylith/index.html` is the operating surface that keeps intent, constraints, topology, and execution state visible.
- Use `./.odylith/bin/odylith start --repo-root .` as the default first grounded turn. It chooses between status, repair, install guidance, bootstrap grounding, and explicit fallback without mutating by default.
- Use `ODYLITH_NO_BROWSER=1` to suppress auto-open during the hosted bootstrap, or `odylith install --no-open` when running the CLI directly.
- Use `./.odylith/bin/odylith upgrade --repo-root .` later to move a consumer repo to the latest verified release and advance the local repo pin.
- Use `./.odylith/bin/odylith reinstall --repo-root . --latest` to rematerialize the local install and align the active runtime plus repo pin in one step. `./.odylith/bin/odylith install --repo-root . --adopt-latest` is the equivalent explicit install-form spelling.
- Use `--dry-run` on `install`, `reinstall`, `upgrade`, `sync`, `dashboard refresh`, and `atlas auto-update` when you want the exact mutation plan and dirty-worktree overlap before Odylith writes files.
- Consumer repos still carrying a legacy install, including repo-owned truth under `odyssey/` and runtime state under `.odyssey/`, should rerun the latest hosted installer from the repo root. That rescue path renames the legacy roots into `odylith/` and `.odylith/`, preserves repo-owned truth, and purges old volatile state before normal Odylith upgrade continues:
  `curl -fsSL https://odylith.ai/install.sh | bash`
- If the repo already has `./.odylith/bin/odylith`, `./.odylith/bin/odylith migrate-legacy-install --repo-root .` performs the same legacy-root migration directly.
- Consumer repos still pinned to the legacy `0.1.0` or `0.1.1` Odylith launcher need that same hosted-installer rerun once to pick up the safer launcher bootstrap before plain `odylith upgrade` can jump to the latest verified release.
- Use `./.odylith/bin/odylith dashboard refresh --repo-root .` for the low-friction shell-facing refresh path; it refreshes `tooling_shell`, `radar`, and `compass` by default, prints the included and excluded surfaces, and suggests the exact Atlas follow-up command when Atlas is stale but skipped. Add `--surfaces atlas --atlas-sync` when you intentionally want Atlas source preflight plus refresh. Keep `odylith sync --repo-root . --force --impact-mode full` for authoritative write-mode regeneration.
- Use `./.odylith/bin/odylith rollback --repo-root . --previous` to return to the last verified local version if an upgrade needs an operational rollback.
- Use `./.odylith/bin/odylith version --repo-root .` to inspect the pinned, active, and locally available versions. `odylith version` also states plainly that Odylith itself runs on the managed runtime while repo-code validation still belongs to the repo's own project toolchain.
- Use `./.odylith/bin/odylith doctor --repo-root . --repair` if the local tree or AGENTS handoff drifts.
- If `./.odylith/bin/odylith` itself is missing, use `./.odylith/bin/odylith-bootstrap doctor --repo-root . --repair` to restore the repo-local launcher without a second Odylith checkout.
- Use `./.odylith/bin/odylith doctor --repo-root . --repair --reset-local-state` when local cache, tuning, or derived runtime state looks poisoned.
- If Odylith is not installed yet and no repo-local bootstrap launcher exists, rerun the hosted installer from the repo root instead of cloning a second Odylith checkout:
  `curl -fsSL https://odylith.ai/install.sh | bash`
- Use `./.odylith/bin/odylith off --repo-root .` and `./.odylith/bin/odylith on --repo-root .` to toggle Odylith guidance for coding agents without removing the runtime. `off` restores default coding-agent behavior for the repo; `on` restores Odylith as the default first path.
- Use `./.odylith/bin/odylith uninstall --repo-root .` to detach runtime integration while preserving both `odylith/` and `.odylith/`.

## Repo Integration Contract

- `odylith/` in a consumer repo is customer-owned bootstrap and local repo truth. It is not a copied product bundle.
- The bootstrap creates local truth roots under `odylith/` and seeds `odylith/runtime/source/product-version.v1.json` plus `odylith/runtime/source/tooling_shell.v1.json`.
- `odylith/agents-guidelines/` is the one consumer-side subtree that Odylith may refresh during normal upgrade.
- `odylith/surfaces/brand/` is starter surface infrastructure seeded on first install and explicit repair, not a normal-upgrade mutation target.
- Product runtime code, product-managed assets, staged versions, ledgers, and caches live under `.odylith/`.
- Odylith owns and installs its own managed runtime under
  `.odylith/runtime/versions/<version>`.
- `./.odylith/bin/odylith` always runs with Odylith's own runtime and does not
  source or mutate the consumer repo's active Python environment.
- There is no shell-level interpreter switching. Running
  `./.odylith/bin/odylith ...` executes Odylith inside `.odylith/`, while the
  consumer repo's own `python`, `uv`, Poetry, or Conda commands continue to
  resolve against the consumer toolchain.
- Keep three boundaries separate:
  - runtime boundary: `./.odylith/bin/odylith` chooses how Odylith runs
  - write boundary: interpreter choice does not limit which repo files the
    agent may edit
  - validation boundary: consumer repo code must still be proved with the
    consumer repo's own toolchain
- Odylith launchers scrub `VIRTUAL_ENV`, `CONDA_*`, `PYTHONHOME`,
  `PYTHONPATH`, `PYTHONEXECUTABLE`, `PYENV_VERSION`, `UV_*`,
  Poetry/Pipenv/PDM selectors, and user-site leakage before starting the
  Odylith runtime.
- Consumer project commands still belong to the consumer repo's own toolchain.
- Consumer launchers fail closed if the active runtime pointer leaves
  `.odylith/runtime/versions/`; they do not silently fall back into
  consumer-machine Python.
- Verified release installs are the supported consumer contract.
- Root `AGENTS.md` gets one Odylith pointer block.

## Isolation Guarantees

- Odylith runtime ownership and consumer project runtime ownership are separate
  concerns.
- `./.odylith/bin/odylith` always runs inside Odylith's managed runtime under
  `.odylith/`; the consumer repo's own `python`, `uv`, Poetry, Pipenv, or
  Conda commands stay on the consumer toolchain.
- Normal install and upgrade do not rewrite the consumer repo's own runtime
  manifest files such as `pyproject.toml`, `requirements.txt`, `uv.lock`,
  `poetry.lock`, or Conda environment files.
- Odylith does not require shell activation, global PATH mutation, or a repo
  shell bootstrap step to switch between runtimes.
- If Odylith cannot trust its own runtime pointer or staged runtime evidence,
  it fails closed into repair instead of borrowing the consumer machine's
  Python.

## Secure Runtime Guarantees

- Hosted install and CLI upgrade verify the signed release manifest, managed
  runtime bundle, provenance, and SBOM before activation.
- Managed runtime bundles are built from pinned upstream Python archive
  digests, and installer/runtime checks fail closed if those digests or local
  verification markers drift.
- Launchers scrub ambient Python and environment-manager variables before
  starting Odylith so shell state from the consumer repo cannot bleed into the
  Odylith runtime.
- Runtime staging is side-by-side under `.odylith/runtime/versions/` and
  activation is an atomic switch of `.odylith/runtime/current`.

## Upgrade Contract

- In consumer repos, `odylith upgrade` treats the latest verified release as the normal control plane and advances `odylith/runtime/source/product-version.v1.json` to the version it activates.
- `odylith reinstall --latest` is the safe consumer restage path when the operator wants latest verified runtime plus repo pin alignment in one step.
- The repo-local launcher carries a compatibility bootstrap for legacy consumer installs on `0.1.0` and `0.1.1`: a plain `odylith upgrade` from those older launchers should first be repaired by rerunning the hosted installer once from the consumer repo root.
- `odylith upgrade` verifies signed assets,
  stages the managed runtime side-by-side, health-checks it, and atomically
  switches `.odylith/runtime/current`.
- `odylith upgrade` reports explicitly whether it moved to a new version, was already current, or only advanced the repo pin, and it prints the release link plus short highlights when that metadata is available.
- Successful consumer upgrade or reinstall refreshes the local shell through the narrow dashboard-refresh path so the browser surface stays current without a full governance sync.
- A previously staged version directory is reused only when its local runtime
  verification marker still matches the newly verified release evidence;
  drifted or partially trusted directories are discarded and restaged.
- Normal upgrades must not rewrite tracked repo truth under `odylith/`; the only allowed consumer-tree refresh is `odylith/agents-guidelines/`.
- Migration-marked releases are blocked from the normal upgrade path.
- `odylith rollback --previous` only targets previously verified local versions and may temporarily diverge from the repo pin.
- `odylith version` and `odylith doctor` must report the active version and
  runtime source clearly.

## Recovery

- Preferred repair path: `./.odylith/bin/odylith doctor --repo-root . --repair`
- Missing-launcher bootstrap path: `./.odylith/bin/odylith-bootstrap doctor --repo-root . --repair`
- In consumer repos, repair must restage the pinned verified runtime or fail
  closed. It must not recreate Odylith through host-Python wrapper fallback.
- Explicit repair may restore missing starter metadata and brand assets under `odylith/` without rewriting repo-owned local truth under the governance roots.
- Poisoned-local-state repair path: `./.odylith/bin/odylith doctor --repo-root . --repair --reset-local-state`
- Temporary agent-off switch: `./.odylith/bin/odylith off --repo-root .`
- Re-enable switch: `./.odylith/bin/odylith on --repo-root .`
- Uninstall preserves customer-owned `odylith/` truth, preserved local `.odylith/` state, and only removes the Odylith block in root `AGENTS.md`.
- Do not delete customer-owned Odylith truth, context, or local operational history to "clean" an install.
- Do not ask users to clone Odylith for installation.
