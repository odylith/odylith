# CLAUDE.md

@AGENTS.md

## Claude Code

- This scoped file ensures Claude loads the same Casebook subtree contract as other hosts.
- Prefer `/odylith-case` plus the `casebook-bug-*` skill shims when you are creating or extending a bug record from concrete evidence.
- Search existing `CB-*` truth first, extend the right bug when it already exists, and keep bug markdown as the canonical record instead of editing rendered Casebook output directly.
- Do not restate or fork Casebook metadata rules in this Claude companion. `AGENTS.md` is the host-agnostic contract for `Status`, `Fixed`, `Type`, `Reproducibility`, validation, and refresh behavior.
- Use `odylith casebook validate --repo-root .` only as the shared source-truth check named by `AGENTS.md`; do not treat this file as an alternate Casebook policy surface.
- For broader Odylith context outside this subtree, follow `odylith/AGENTS.md` and the repo-root bridge.
- Do not treat this file as a bug record; it is only the Claude companion for this scope.
