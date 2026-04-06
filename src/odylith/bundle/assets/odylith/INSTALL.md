# Install

1. Run the latest Odylith release bootstrap command from the repository or folder you want to augment. A repo root is ideal, but Odylith also supports subdirectories and folder-only installs.
2. Use a supported platform: macOS (Apple Silicon) or Linux
   (`x86_64` or `ARM64`).
3. Let that bootstrap detect the install boundary, create a root `AGENTS.md`
   if it is missing, create `./.odylith/bin/odylith`, install Odylith's own
   managed runtime under `.odylith/`, and materialize the managed `odylith/`
   tree.
4. Run `./.odylith/bin/odylith doctor --repo-root .`.
5. Use `./.odylith/bin/odylith reinstall --repo-root . --latest` later when you want to rematerialize the local install and align the runtime plus repo pin in one step.
6. If you just need the local shell current, use `./.odylith/bin/odylith dashboard refresh --repo-root .`.
7. If `./.odylith/bin/odylith` itself is missing, use `./.odylith/bin/odylith-bootstrap doctor --repo-root . --repair` to restore the launcher.
8. Keep using the repo normally. `./.odylith/bin/odylith` runs Odylith inside
   `.odylith/`; the repo's own project commands stay on the consumer toolchain.
9. Keep Odylith on the verified managed runtime described here rather than
   routing Odylith commands through the repo's own Python environment.

## Legacy Install Migration

- If this repo still has customer-owned truth under `odyssey/` or runtime state under `.odyssey/`, rerun the latest hosted installer from the repo root instead of trying to revive the old `odyssey` launcher.
- That hosted installer renames `odyssey/` to `odylith/`, renames `.odyssey/` to `.odylith/`, rewrites managed config paths, and purges old volatile memory, cache, and benchmark state.
- If `./.odylith/bin/odylith` already exists, you can run `./.odylith/bin/odylith migrate-legacy-install --repo-root .` directly.

## Folder-Only Install Caveat

- If no enclosing `.git` exists, Odylith still installs and treats the current
  folder as the repo root.
- In that mode, Git-aware features stay limited until the folder is backed by
  Git.
- Today that mainly means working-tree intelligence, background autospawn, and
  git-fsmonitor watcher help stay reduced.

## Isolation Promise

- Odylith runs from `.odylith/`, not from the repo's existing Python
  environment.
- Odylith does not modify the repo's own runtime manifests or toolchain files
  during normal install or upgrade.
- Odylith does not require shell activation or global PATH rewrites.
- If Odylith's runtime becomes unhealthy, it fails closed into repair instead
  of silently borrowing the consumer machine's Python.

## Secure-By-Default Posture

- Install and upgrade verify the signed release manifest, managed runtime
  bundle, provenance, and SBOM before activation.
- Odylith scrubs ambient virtualenv, Conda, `PYTHONPATH`, `PYTHONHOME`,
  `PYTHONEXECUTABLE`, `PYENV_VERSION`, `UV_*`, and Poetry/Pipenv/PDM selectors
  before starting its own runtime.
- Managed runtime versions are staged side-by-side under
  `.odylith/runtime/versions/` so upgrade and rollback do not trample the
  consumer repo's setup.
