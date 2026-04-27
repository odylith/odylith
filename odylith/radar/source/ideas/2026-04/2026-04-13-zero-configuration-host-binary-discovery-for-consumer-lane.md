status: queued

idea_id: B-095

title: Zero-Configuration Host Binary Discovery for Consumer Lane

date: 2026-04-13

priority: P0

commercial_value: 3

product_impact: 5

market_value: 3

impacted_parts: odylith-memory-backend,odylith-context-engine

sizing: S

complexity: Medium

ordering_score: 100

ordering_rationale: The consumer lane must automatically discover the correct host binary (Claude Code or Codex) without any operator setup. Currently resolve_claude_bin has no fallback candidates for the Claude.app bundle path, while resolve_codex_bin does. This causes narration to silently fall back to Codex even when running inside Claude Code, hitting wrong credit pools and giving wrong error messages. First-time install and incremental upgrade must both resolve the host binary automatically.

confidence: high

founder_override: no

promoted_to_plan: 

execution_model: standard

workstream_type: standalone

workstream_parent: 

workstream_children: 

workstream_depends_on: 

workstream_blocks: 

related_diagram_ids: 

workstream_reopens: 

workstream_reopened_by: 

workstream_split_from: 

workstream_split_into: 

workstream_merged_into: 

workstream_merged_from: 

supersedes: 

superseded_by: 

## Problem

The consumer lane must automatically discover the correct host binary (Claude
Code or Codex) without any operator configuration. This is non-negotiable for
first-time install and incremental upgrade paths.

Current state:
- `resolve_codex_bin()` in `odylith_reasoning.py` has real fallback candidates
  for the Codex.app bundle path (`/Applications/Codex.app/Contents/Resources/codex`).
- `resolve_claude_bin()` has `_DEFAULT_CLAUDE_BIN_CANDIDATES = ()` — an empty
  tuple. No fallback paths for the Claude.app bundle.
- The Claude Code binary lives at a versioned, non-PATH location:
  `~/Library/Application Support/Claude/claude-code/<version>/claude.app/Contents/MacOS/claude`
- `which claude` and `which claude-code` both fail because the binary is not
  symlinked onto PATH by the Claude.app installer.

Consequence: when running inside Claude Code, the host runtime detection
correctly identifies `claude_cli` via environment variables, but the provider
resolution falls through to Codex because the Claude binary isn't found. This
causes:
- Narration (Compass standup brief) charges the wrong credit pool (Codex/OpenAI
  instead of Claude/Anthropic)
- `credits_exhausted` errors that mislead the operator about which provider is
  actually out of budget
- The `_implicit_local_provider_name()` function prefers Codex when both
  binaries exist, even when the host hint says `claude-cli`

Additionally, `_implicit_local_provider_name()` has a Codex-first tiebreaker at
line 367-368: when both binaries are found, it returns `"codex-cli"` regardless
of the host hint. The hint check at lines 359-362 correctly prefers the
detected host, but only fires when the binary is found — which it isn't for
Claude.

## Customer

Every Claude Code operator running Odylith in any repo. First-time install must
work. Incremental upgrades (where the Claude binary path changes with each
version) must work. The consumer should never need to know where the binary
lives or configure anything.

## Opportunity

Make Odylith's narration, reasoning, and any future provider-backed features
use the correct host automatically — zero configuration, correct credit pool,
correct error attribution.

## Proposed Solution

1. **Populate `_DEFAULT_CLAUDE_BIN_CANDIDATES`** with real discovery paths:
   - Glob `~/Library/Application Support/Claude/claude-code/*/claude.app/Contents/MacOS/claude`
     and pick the highest version
   - Check `/usr/local/bin/claude`, `~/.local/bin/claude` for symlinked installs
   - Check the `CLAUDE_CODE_ENTRYPOINT` environment variable (set to
     `claude-desktop` in the current session) as a discovery hint

2. **Fix the tiebreaker in `_implicit_local_provider_name()`**: when the host
   hint says `claude-cli` and the Claude binary is found, always return
   `claude-cli` — never fall through to the Codex-first tiebreaker.

3. **Scope the narration backoff timer to the provider**: a `credits_exhausted`
   backoff from Codex should not block a retry via Claude, and vice versa. The
   maintenance state should record which provider failed so a host switch resets
   the backoff.

4. **First-time install contract**: `odylith install` and `curl | bash` must
   probe for the host binary and record the resolved path in the install
   manifest so subsequent commands don't re-probe every time.

5. **Incremental upgrade contract**: when the Claude binary path changes (new
   version), the cached resolved path becomes stale. The resolver must re-probe
   when the cached path is no longer executable.

## Scope

- Populate `_DEFAULT_CLAUDE_BIN_CANDIDATES` with glob-based discovery
- Fix `_implicit_local_provider_name()` tiebreaker
- Scope narration backoff to provider identity
- Add resolved-binary caching with staleness check
- Test coverage for both Claude-only and Codex-only machines, and dual-host

## Non-Goals

- Changing the narration architecture (provider, maintenance worker, batch
  builder) — only the binary discovery and provider selection
- Supporting hosts beyond Claude Code and Codex (no VS Code Copilot, Cursor,
  etc.)

## Risks

- The Claude binary path includes a version number that changes on every
  update. Glob-based discovery must pick the right version (latest) and handle
  mid-update states where the old version is gone and the new one isn't yet
  fully installed.
- The `~/Library/Application Support/` path is macOS-specific. Linux and
  Windows Claude Code installs (if they exist) may use different paths.

## Dependencies

- B-094 (Context Engine Connection Lifecycle) — provider selection affects the
  same reasoning runtime
- Execution Governance component — host profile detection feeds provider
  selection

## Success Metrics

- `resolve_claude_bin()` returns a valid executable path when Claude.app is
  installed, without any operator configuration
- `_implicit_local_provider_name()` returns `claude-cli` when running inside
  Claude Code and the binary is found
- Compass standup brief narration uses the correct provider for the detected
  host — Claude credits for Claude sessions, Codex credits for Codex sessions
- Zero operator configuration required on first install or upgrade

## Validation

- `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_odylith_reasoning.py`
- Live: run `compass refresh --wait` from Claude Code, verify provider is
  `ClaudeCliReasoningProvider`
- Live: run `compass refresh --wait` from Codex, verify provider is
  `CodexCliReasoningProvider`

## Rollout

Implement immediately — this is a P0 correctness bug that causes silent
provider misattribution and wrong credit charges.

## Why Now

This is actively broken in production. Claude Code operators running Compass
refresh get `credits_exhausted` from Codex instead of using their Claude Max
plan. The execution engine Claude optimization landed in this session increases
the number of provider-backed queries per session, amplifying the impact.

## Product View

The consumer lane must work like magic. When an operator installs Odylith in a
repo and opens Claude Code, every Odylith feature that needs a provider should
use Claude — automatically, without configuration, on first run and after every
upgrade. The same applies to Codex. The operator should never see a
`credits_exhausted` error from a provider they aren't using. This is
non-negotiable for the consumer experience.

## Impacted Components

- `odylith` — reasoning provider resolution
- `odylith-context-engine` — narration provider selection
- `execution-governance` — host profile detection (indirect)

## Interface Changes

- No CLI interface changes. The fix is internal to `resolve_claude_bin()` and
  `_implicit_local_provider_name()`.
- New: resolved-binary cache file in `.odylith/runtime/` for install/upgrade
  persistence.

## Migration/Compatibility

- Fully backward compatible. Existing Codex-only installs continue to work.
  Existing Claude installs with `claude` on PATH continue to work. The change
  only adds discovery paths that were previously missing.

## Test Strategy

- Unit tests for `resolve_claude_bin` with mocked filesystem paths
- Unit tests for `_implicit_local_provider_name` with both host hints
- Integration test: provider resolution from inside Claude Code session

## Open Questions

- Should the resolved binary path be cached in `.odylith/runtime/` or
  re-probed on every call? Caching is faster but needs a staleness check.
- What is the Claude Code binary path on Linux?
