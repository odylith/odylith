Status: In progress

Created: 2026-05-01

Updated: 2026-05-01

Backlog: B-141

Goal: Reduce Claude and Codex host-turn latency without losing Odylith's
automatic prompt context assessment, ambient intervention blocks, visible
Assists, safety guards, or governance capture. The v0.1.13 implementation
must keep the same product behavior while moving heavy work out of the
critical path: Claude prompt-submit work becomes one bundled route, Claude
PostToolUse refreshes become async where the host supports it, Codex
PostToolUse records cheap dirty events and settles them at Stop, and
Casebook/Radar migration evidence stays captured when legacy records or
launcher repair states break.

Assumptions:
- Claude and Codex have different native hook semantics, so performance wins
  must use host-supported primitives instead of one lowest-common-denominator
  config shape.
- Prompt context, ambient highlights, Observations, Proposals, Assists, and
  governed refresh evidence are product features, not optional debug output.
- Direct-dispatch host hooks remain the reliable fallback until a long-lived
  hook daemon is separately designed, secured, and proven.
- Legacy consumer Casebook records may be missing newer metadata fields and
  must migrate before stricter v0.1.13 validation runs.

Constraints:
- Do not remove safety gates. PreToolUse guards stay synchronous when they can
  block destructive or governed writes.
- Do not add unsupported host settings. Codex must not receive Claude-only
  async or `if` fields.
- Keep show/help/capability route locks stdout-clean and fast.
- Keep Status and Type in Casebook as single-word tokens in source truth,
  projection payloads, and visible chips.
- Keep generated project-root assets, Claude skills, and source bundle mirrors
  aligned with the source contracts.

Reversibility: The prompt-bundle and dirty-event settlement paths are additive
around the existing direct-dispatch runtime. If a host adapter regresses, the
settings renderers can point back to the previous command hooks while retaining
the shared route-lock and Casebook migration code.

Boundary Conditions:
- Scope includes Claude prompt-bundle rendering, Claude effective settings,
  Codex Bash guard and PostToolUse checkpoint behavior, Stop-time dirty-event
  settlement, Casebook metadata migration, host contract docs, explicit-only
  skill invocation flags, bundled project-root mirrors, and focused tests.
- Scope excludes model switching, removing Odylith grounding, MCP server
  cleanup outside the repo, and productionizing a hook daemon in v0.1.13.

Related Bugs:
- [CB-147](../../../casebook/bugs/2026-05-01-claude-hooks-spam-unhealthy-launcher-repair-errors-during-bootstrap-repair.md)
  tracks migration repair hook spam around unhealthy launcher state.
- [CB-148](../../../casebook/bugs/2026-05-01-bootstrap-doctor-repair-still-surfaces-trusted-root-warning-noise.md)
  tracks trusted-root warning noise during bootstrap doctor repair.
- [CB-149](../../../casebook/bugs/2026-05-01-host-adapters-pay-too-much-odylith-hook-and-startup-latency.md)
  tracks the host latency architecture failure.
- [CB-150](../../../casebook/bugs/2026-05-01-casebook-renders-prose-status-and-type-chips.md)
  tracks the Casebook single-word Status and Type contract.

## Learnings
- [x] Latency reductions that silence prompt hooks are regressions unless the
      hidden prompt context and visible intervention lanes remain equivalent.
- [x] Claude can collapse prompt work and async refreshes natively; Codex needs
      cheap command hooks plus deferred settlement because async hook fields are
      not part of its project hook contract.
- [x] Hardening Casebook metadata needs legacy migration before strict
      validation, otherwise repair and upgrade can strand older repos.

## Must-Ship
- [x] Add shared prompt route locks so help/show/capabilities prompts bypass
      heavy context work without changing the user-visible command contract.
- [x] Add `odylith claude prompt-bundle` so show/help route locks, prompt
      context, and teaser output run through one host path.
- [x] Render Claude settings with one prompt-submit bundle hook, host-native
      Bash guard filters, and async PostToolUse checkpoints where supported.
- [x] Keep Codex PostToolUse on a cheap dirty-event recorder and settle
      governed refresh work during Stop or the next grounding cycle.
- [x] Preserve automatic context/intervention semantics with focused parity
      tests for hidden context, visible teaser output, and route locks.
- [x] Enforce Casebook single-word Status and Type metadata in validation,
      capture, projection, dashboard rendering, and migration backfills.
- [x] Mark explicit-only Claude workflow skills as slash-invocable without
      removing automatic context, bug-capture, start, show, sync, or hygiene
      skills from model invocation.
- [x] Update host contracts, source bundle mirrors, Radar, Casebook, and
      release assignments for v0.1.13.

## Should-Ship
- [ ] Convert the host hook daemon proposal into a separate design slice with
      trust, lifecycle, fallback, and local transport boundaries.
- [ ] Add a repeatable cross-host SDK benchmark harness for release evidence
      once the v0.1.13 hook architecture is stable.

## Defer
- [ ] MCP server scope cleanup remains local host configuration work, not a
      repo-shipped v0.1.13 product contract.
- [ ] Root `AGENTS.md` kernel splitting is deferred until path-scoped guidance
      behavior can be proven without weakening safety or CLI-first policy.

## Risks & Mitigations
- [x] Risk: Moving checkpoint work off the critical path could lose governance
      evidence after edits or Bash commands.
  - [x] Mitigation: Codex records durable dirty events synchronously and Stop
        settlement replays governed refresh or keeps unsettled events for the
        next prompt when refresh fails.
- [x] Risk: Claude prompt-bundle could accidentally drop visible teaser output
      or hidden prompt context.
  - [x] Mitigation: Prompt-bundle tests compare route-lock behavior and
        hidden/visible output parity against the previous prompt-context and
        prompt-teaser surfaces.
- [x] Risk: Strict Casebook Status/Type validation could break legacy
      consumer migrations.
  - [x] Mitigation: Casebook sync migration backfills missing Type and compacts
        prose Status before validation, with doctor and upgrade regression
        coverage.
- [x] Risk: Skill-surface diet could remove automatic governance capture.
  - [x] Mitigation: Explicit-only flags are limited to manual workflow skills;
        tests assert automatic context and bug-capture skills remain
        model-invokable.

## Validation
- [x] `PYTHONPATH=src pytest -q tests/unit/runtime/test_claude_host_prompt_context.py tests/unit/runtime/test_codex_host_post_bash_checkpoint.py tests/unit/runtime/test_codex_host_stop_summary.py tests/unit/runtime/test_casebook_bug_index.py tests/unit/runtime/test_host_runtime_contract.py tests/unit/runtime/test_claude_cli_capabilities.py tests/unit/install/test_claude_effective_settings.py tests/unit/runtime/test_claude_host_compatibility.py tests/unit/test_claude_host_cli.py tests/unit/test_cli_audit.py tests/unit/install/test_codex_project_assets.py tests/unit/runtime/test_source_bundle_mirror.py tests/unit/runtime/test_hygiene.py tests/integration/install/test_manager.py::test_doctor_bundle_repair_backfills_legacy_casebook_bug_ids tests/integration/install/test_manager.py::test_upgrade_same_version_backfills_legacy_casebook_bug_ids tests/integration/install/test_manager.py::test_consumer_upgrade_backfills_legacy_casebook_bug_ids_during_runtime_activation`
- [x] `./.odylith/bin/odylith casebook validate --repo-root .`
- [x] `./.odylith/bin/odylith validate version-truth --repo-root .`
- [x] `./.odylith/bin/odylith validate backlog-contract --repo-root .`
- [x] `./.odylith/bin/odylith validate plan-workstream-binding --repo-root .`
- [x] `./.odylith/bin/odylith validate plan-risk-mitigation --repo-root .`
- [x] `git diff --check`
