# CLAUDE.md

@AGENTS.md

## Claude Code

- This scoped file ensures Claude loads the same Casebook subtree contract as other hosts.
- Prefer `/odylith-case` plus the `casebook-bug-*` skill shims when you are creating or extending a bug record from concrete evidence.
- Search existing `CB-*` truth first, extend the right bug when it already exists, and keep bug markdown as the canonical record instead of editing rendered Casebook output directly.
- Keep `Reproducibility` to one compact token such as `High`, `Medium`, `Low`, `Always`, `Intermittent`, or `Consistent`; put repro steps and evidence in the concrete evidence fields.
- Use `odylith casebook validate --repo-root .` for source-only checks; refresh must fail closed if Casebook markdown violates the compact-field contract.
- For broader Odylith context outside this subtree, follow `odylith/AGENTS.md` and the repo-root bridge.
- Do not treat this file as a bug record; it is only the Claude companion for this scope.
