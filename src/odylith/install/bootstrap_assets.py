"""Shared repo bootstrap, guidance, and managed-asset sync for installs."""

from __future__ import annotations

import contextlib
import json
import shutil
import tomllib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping

from odylith.install.agents import GUIDANCE_FILENAMES, update_guidance_file
from odylith.install.fs import atomic_write_text
from odylith.install.state import DEFAULT_REPO_SCHEMA_VERSION, version_pin_path, write_version_pin
from odylith.runtime.common import claude_cli_capabilities
from odylith.runtime.common import codex_cli_capabilities
from odylith.runtime.common.guidance_paths import existing_top_level_guidance_paths
from odylith.runtime.common.product_assets import bundled_product_root, bundled_project_root_assets_root
from odylith.runtime.governance import sync_casebook_bug_index

PRODUCT_REPO_ROLE = "product_repo"
CONSUMER_REPO_ROLE = "consumer_repo"
_GENERATED_HOST_CONFIG_RELATIVE_PATHS = {
    Path(".claude") / "settings.json",
    Path(".codex") / "config.toml",
    Path(".codex") / "hooks.json",
}
_RETIRED_PROJECT_ROOT_SKILL_SHIMS = frozenset(
    {
        "odylith-subagent-router",
    }
)


def repo_root_guidance_source() -> str:
    return "\n".join(
        [
            "# Repo Guidance",
            "",
            "This file defines repo-root guidance for this workspace.",
            "",
            "## Working Rule",
            "- Keep repo-root guidance here for paths outside `odylith/`.",
            "- When Odylith is installed, work under `odylith/` follows `odylith/AGENTS.md` first.",
            "- If this folder is not backed by Git yet, Odylith still installs here, but Git-aware features stay limited until `.git` exists.",
            "",
        ]
    )


def repo_root_claude_source() -> str:
    return "\n".join(
        [
            "# CLAUDE.md",
            "",
            "@AGENTS.md",
            "",
            "## Claude Code",
            "- This file keeps Claude aligned with the repo-root `AGENTS.md` contract instead of branching into a Claude-only lane.",
            "- This repo also ships committed Claude project assets under `.claude/`, including `.claude/CLAUDE.md`; use them for Claude-native commands, hooks, rules, subagents, and the auto-memory bridge.",
            "- Keep this file, the `.claude/` tree, and the scoped `odylith/**/CLAUDE.md` companions aligned with the same Odylith contract.",
            "- First-match help route: if the user says `Odylith, help`, use the CLI help surface and print stdout only. Do not run install, status, intervention, or launcher diagnostics first.",
            "- First-match demo route: if the user says `Odylith, show me what you can do` or asks what Odylith can do for this repo, use the advisory `odylith show` demo. Do not run install, status, intervention, launcher diagnostics, or sample-app creation first. If Odylith is not installed in the current folder, say that directly.",
            "- Capability inventory route: if the user asks to list Odylith capabilities, engines, product architecture, or the capability map, run `odylith capabilities` and print stdout only. Do not infer the taxonomy from `odylith --help`, `odylith show`, Claude Code capability prose, or any host-model surface.",
            "- Claude Code is a first-class Odylith delegation host. Codex emits routed `spawn_agent` payloads subject to active host policy; Claude Code executes the same bounded delegation contract through Task-tool subagents and the checked-in `.claude/` project assets.",
            "",
        ]
    )


def ensure_repo_root_guidance_files(*, repo_root: Path) -> tuple[str, ...]:
    created: list[str] = []
    for relative_path, source in (
        ("AGENTS.md", repo_root_guidance_source()),
        ("CLAUDE.md", repo_root_claude_source()),
    ):
        path = Path(repo_root).resolve() / relative_path
        if path.is_file():
            continue
        atomic_write_text(path, source, encoding="utf-8")
        created.append(relative_path)
    return tuple(created)


def update_root_guidance_files(*, repo_root: Path, install_active: bool, repo_role: str) -> None:
    for path in existing_top_level_guidance_paths(repo_root=repo_root):
        update_guidance_file(path, install_active=install_active, repo_role=repo_role)


def _pyproject_payload(*, repo_root: Path) -> dict[str, object]:
    path = repo_root / "pyproject.toml"
    if not path.is_file():
        return {}
    try:
        payload = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return {}
    return dict(payload) if isinstance(payload, dict) else {}


def product_source_version(*, repo_root: str | Path) -> str:
    root = Path(repo_root).expanduser().resolve()
    payload = _pyproject_payload(repo_root=root)
    project = payload.get("project")
    if not isinstance(project, Mapping):
        return ""
    return str(project.get("version") or "").strip()


def product_repo_role(*, repo_root: str | Path) -> str:
    root = Path(repo_root).expanduser().resolve()
    payload = _pyproject_payload(repo_root=root)
    project = payload.get("project")
    project_name = str(project.get("name") or "").strip().lower() if isinstance(project, Mapping) else ""
    has_product_shape = (
        project_name == "odylith"
        and (root / "src" / "odylith").is_dir()
        and (root / "odylith" / "registry" / "source" / "component_registry.v1.json").is_file()
        and (root / "odylith" / "radar" / "source" / "INDEX.md").is_file()
    )
    return PRODUCT_REPO_ROLE if has_product_shape else CONSUMER_REPO_ROLE


def customer_bootstrap_guidance() -> str:
    return "\n".join(
        [
            "# Odylith Repo Guidance",
            "",
            "Scope: applies to the local customer-owned `odylith/` tree in this repository.",
            "",
            "## Ownership",
            "- This starter tree is local repo truth, not a copy of the Odylith product repo.",
            "- `odylith/runtime/source/product-version.v1.json` pins the intended Odylith product version.",
            "- `odylith/runtime/source/tooling_shell.v1.json` is local repo shell metadata and stays customer-owned.",
            "- `.odylith/trust/managed-runtime-trust/` is local Odylith runtime trust state and may be refreshed by install, upgrade, feature-pack activation, or doctor.",
            "- `odylith/surfaces/brand/` is an Odylith-managed starter asset set for local HTML surfaces; first install and explicit repair may restore it, but normal upgrades should not rewrite it.",
            "- `.claude/`, `.codex/`, `.agents/skills/`, `odylith/AGENTS.md`, `odylith/CLAUDE.md`, the shipped scoped guidance companions under `odylith/**/AGENTS.md` and `odylith/**/CLAUDE.md`, `odylith/agents-guidelines/`, and `odylith/skills/` are Odylith-managed guidance assets and may be refreshed by install, upgrade, or doctor.",
            "- Truth under `odylith/radar/`, `odylith/technical-plans/`, `odylith/casebook/`, `odylith/registry/`, and `odylith/atlas/` belongs to this repository and must not be rewritten by normal upgrades.",
            "- Product runtime code and product-managed assets run from `.odylith/` and the installed Odylith runtime package.",
            "- Do not treat this folder as disposable cache; it belongs to the repository using Odylith.",
            "",
            "## Working Rule",
            "- For work under `odylith/`, read this file first.",
            "- Use `./.odylith/bin/odylith` for Odylith CLI workflows in this repository.",
            "- Before any substantive repo scan or code change outside trivial fixes, run `./.odylith/bin/odylith start --repo-root .` first and keep the active workstream, component, or packet in scope before raw repo search, tests, or edits. Direct repo scan before that start step is a policy violation unless the task is trivial or Odylith is unavailable.",
            "- Do not run `odylith context`, `odylith query`, `git status`, broad repo search, or other repo-inspection commands in parallel with that start step. Let `start` finish first; then run `odylith context --repo-root . <ref>` only when the user, start output, or governed truth gives an exact anchor.",
            "- Keep startup, Context Engine, Execution Engine, memory substrate, Tribunal, Intervention Engine, observers, governance, subagent routing, Surface DAGs, delivery, analysis, and migration-breakage observation active. Improve latency by routing, caching, batching, and shortening always-loaded guidance, not by disabling engines.",
            "- The repo-root managed `AGENTS.md` block is the shared hard-law kernel for both Codex and Claude Code. It owns help/show/capabilities fast paths, commentary discipline, queue adoption, governance refresh, target-repo validation, guidance-behavior proof, Discipline proof, and the default Codex/Claude lane; do not duplicate or weaken those rules here.",
            "- Codex and Claude Code share the same default Odylith lane: the repo-root `AGENTS.md` contract, `./.odylith/bin/odylith`, truthful `odylith ... --help`, and the grounded governance workflow. Keep host-specific tips rare and capability-gated.",
            "- In coding-agent commentary, keep startup, fallback, routing, and packet-selection internals implicit. Describe progress in task terms like the exact file/workstream, the bug under test, or the validation in flight. If startup needs narrowing but work can continue, do not narrate it; never say `Startup fell back`. Do not surface routine `odylith start`, `odylith context`, or `odylith query` commands in progress updates, and never prefix commentary with control-plane receipt labels. Keep normal commentary task-first and human. Reserve `Odylith Insight:`, `Odylith History:`, or `Odylith Risks:` for rare high-signal moments.",
            "- Capability inventory is product-owned and host-agnostic: if the user asks for Odylith capabilities, engines, product architecture, or the capability map, run `odylith capabilities` and print stdout only. Do not infer the taxonomy from `odylith --help`, `odylith show`, Claude Code, Codex, or any other host model capability surface.",
            "- Help and technical-plan command discovery use the single authoritative help path: do not run parallel exploratory filesystem probes whose failure can cancel the visible help call. `odylith plan --help` is read-only; do not invent plan write flows or probe `odylith/technical-plans/source/`.",
            "- CLI-first is non-negotiable here too: default to the nearest `AGENTS.md`, the repo-local launcher, and truthful `odylith ... --help`; use `odylith backlog ...`, `odylith governance ...`, `odylith validate plan-* ...`, `odylith bug ...`, `odylith component ...`, `odylith registry ...`, `odylith atlas ...`, and `odylith compass ...` before hand edits. Do not hand-edit governed files where a CLI exists. `odylith backlog create` remains fail-closed and must receive grounded Problem, Customer, Opportunity, Product View, and Success Metrics text.",
            "- Empty or thin consumer repos can still receive project-first governance from user intent. Use `odylith greenfield propose --repo-root . --prompt \"<request>\"` for the no-write Product Intent Confirmation request, then write a compact product-first interpretation in chat from live reasoning: product story, actors, systems, assumptions, ambiguities, and a clear Next step block with Confirm, Edit, and Reject choices. Do not generate backlog, Registry, Atlas, release waves, validation obligations, proposal JSON, or create writes before intent confirmation. After confirmation, write that same visible Product Intent Confirmation to `.odylith/runtime/greenfield/confirmed-intent.md`, then run `odylith greenfield create --repo-root . --prompt \"<request>\" --intent-file .odylith/runtime/greenfield/confirmed-intent.md --confirm --release 0.0.1`; Odylith builds the apply-ready proposal from the accepted narrative, validates it, runs the Tribunal write gate, writes records, and refreshes readable views. `odylith greenfield propose --intent-file .odylith/runtime/greenfield/confirmed-intent.md --confirm-intent --format json` is only an optional review artifact when explicitly requested; feed that exact generated JSON to `greenfield apply` if using the file workflow. Do not ask the operator to inspect proposal JSON or confirm a second time by default. Do not inspect Odylith source files, Python modules, `.odylith`, local examples, or bundle assets to discover schema fields, and do not hand-author or repair proposal JSON. Do not run confirmed create from a thin prompt without `--intent-file`. No canned domain families, scaffolds, or code before product gates. Surface only the human-readable created-record summary or validation/Tribunal blockers.",
            "- Treat live teaser, `**Odylith Observation**`, and `Odylith Proposal` as the intervention-engine fast path; treat `Odylith Assist:` as the chatter-owned closeout. Do not collapse those layers.",
            "- Codex checkpoint hooks may keep hidden Observation/Proposal/Assist continuity and surface earned notes; Claude direct-edit and Bash PostToolUse hooks stay silent on success and emit only compact failure/skipped-refresh status. Claude Stop is memory/logging only, not a fallback closeout or live-note recovery lane.",
            "- Hook `systemMessage` or `additionalContext` generation is not proof of chat-visible UX. Before claiming the intervention UX is active in a specific chat, run or cite `odylith codex intervention-status` or `odylith claude intervention-status`; it is the low-latency delivery record for Teaser, Ambient Highlight, Observation, Proposal, and Assist readiness. Only call a session fully end to end after it reports `Activation: ready` and a chat-visibility line is confirmed. Treat recorded-only and waiting-for-chat states as partial proof. When needed, run `odylith codex visible-intervention` or `odylith claude visible-intervention` and show that Markdown directly.",
            "- Existing Codex and Claude sessions may not hot-reload changed hooks, guidance, or source-local runtime code; prove changed visibility behavior in a fresh/reloaded session or render `visible-intervention` output in the existing chat.",
            "- At closeout, or when a visible-intervention recovery renders a prompt-submit or visibility-proof note, add at most one short `Odylith Assist:` or `**Odylith Assist:**` line only when it helps; normal non-passthrough prompts do not get an Assist line by default. Do not add Assist just because Odylith ran. Lead with the user win, updated governance IDs inline when changed, affected governance-contract IDs when no governed file moved, the `odylith_off` or broader unguided path edge when supported, keep it crisp, authentic, clear, simple, insightful, and ground the line in concrete observed counts, measured deltas, or validation outcomes, or a concrete chat-visibility complaint. Use `Odylith Insight:`, `Odylith History:`, or `Odylith Risks:` only for rare high-signal moments. Silence is better than filler.",
            "- For live blocker lanes, never say `fixed`, `cleared`, or `resolved` without qualification unless the hosted proof moved past the prior failing phase. Force three checks first: same fingerprint as the last falsification or not, hosted frontier advanced or not, and whether the claim is code-only, preview-only, or live.",
            "- In consumer repos, grounding Odylith is diagnosis authority, not blanket write authority: if the issue target is Odylith itself, stop at diagnosis and maintainer-ready feedback unless the operator explicitly authorizes Odylith mutation.",
            "- Treat `odylith upgrade`, `odylith reinstall`, `odylith doctor --repair`, `odylith sync`, and `odylith dashboard refresh` as writes when they change `odylith/` or `.odylith/`; do not run them autonomously as Odylith fixes in consumer repos.",
            "- Treat backlog/workstream, plan, Registry, Atlas, Casebook, Compass, and session upkeep as part of the same grounded Odylith workflow rather than optional aftercare; search existing workstream, plan, bug, component, diagram, and recent session/Compass context first. If the slice is genuinely new and it is repo-owned non-product work, create the missing workstream and bound plan before non-trivial implementation; if the issue is Odylith itself in a consumer repo, produce a maintainer-ready feedback packet instead.",
            "- Queued backlog items, case queues, and shell or Compass queue previews are not implicit implementation instructions. Unless the user explicitly asks to work a queued item, do not pick it up automatically just because it appears in Radar, Compass, the shell, or another Odylith queue surface.",
            "- When a routine governance task already maps to a first-class CLI family such as `odylith bug capture`, `odylith backlog create`, `odylith component register`, `odylith atlas scaffold`, or `odylith compass log`, go straight to that CLI. For quick visibility after a narrow truth change, rerender only the owned surface: `odylith radar refresh`, `odylith registry refresh`, `odylith casebook refresh`, `odylith atlas refresh`, or `odylith compass refresh`; use `odylith compass deep-refresh` for brief settlement and `odylith sync` for the broader governance lane.",
            "- Treat routed or orchestrated native delegation as the default candidate for substantive grounded consumer-lane work when the route is bounded, the host transport supports it, and the active host policy allows it; keep transport support separate from current-session spawn permission/effectiveness.",
            "- Treat AI slop as a regression. Apply across consumer/maintainer lanes, Codex/Claude, all languages, and any codebase or project surface. Codex and Claude must enforce the same anti-slop contract. Treat the slop class, not the language syntax, as the thing to ban. Consumer repos may be Python, TypeScript, JavaScript, Go, Rust, Java, shell, SQL, or mixed-language. Move ownership, not just files; partial shared-kernel adoption is still incomplete; if the replacement smell remains, the pass is incomplete. Prose-only hardening is incomplete. Repo-wide claims require fresh behavior proof for the touched slice and a fresh structural inventory for the claimed scope. Browser-rendered surfaces require the full headless browser matrix across normal, empty/fallback, and degraded or error states. Full rule: `odylith/agents-guidelines/ANTI_SLOP_AND_DECOMPOSITION.md`; use `odylith/skills/odylith-code-hygiene-guard/SKILL.md` when quality pressure is high.",
            "- For guidance behavior pressure cases, use `odylith validate guidance-behavior --repo-root .` for deterministic proof and `odylith benchmark --profile quick --family guidance_behavior` for benchmark-family proof. Compact packet summaries only prove the proof path is available; fresh validation still requires the explicit command.",
            "- Use native host capabilities where they exist: Codex uses `.codex/` hooks/config/agents plus curated `.agents/skills/` command shims in trusted projects; Claude uses `.claude/` hooks, commands, skills, Task subagents, rules, statusline, and auto-memory. Keep both on the same grounding, memory, surfaces, and orchestration contract without mixing host-only fields.",
            "- Treat the managed guidance files under `.claude/`, `.codex/`, the curated `.agents/skills/` command shims, `odylith/AGENTS.md`, `odylith/CLAUDE.md`, the shipped scoped `odylith/**/AGENTS.md` and `odylith/**/CLAUDE.md` companions, `odylith/agents-guidelines/`, and the specialist references under `odylith/skills/` as the Odylith operating layer; keep repo-specific truth in the governance surfaces beside them.",
            "",
            "## Common Fast Paths",
            "- `./.odylith/bin/odylith bug capture --help`",
            "- `./.odylith/bin/odylith backlog create --help`",
            "- `./.odylith/bin/odylith greenfield propose --help`",
            "- `./.odylith/bin/odylith component register --help`",
            "- `./.odylith/bin/odylith atlas scaffold --help`",
            "- `./.odylith/bin/odylith compass log --help`",
            "- Technical-plan maintenance: `./.odylith/bin/odylith governance --help` and `./.odylith/bin/odylith validate --help`; `./.odylith/bin/odylith plan --help` is a read-only command guide.",
            "- `./.odylith/bin/odylith radar refresh --repo-root .`",
            "- `./.odylith/bin/odylith registry refresh --repo-root .`",
            "- `./.odylith/bin/odylith casebook refresh --repo-root .`",
            "- `./.odylith/bin/odylith atlas refresh --repo-root . --atlas-sync`",
            "- `./.odylith/bin/odylith compass refresh --repo-root .`",
            "- `./.odylith/bin/odylith compass deep-refresh --repo-root .`",
            "- `./.odylith/bin/odylith validate guidance-behavior --repo-root .`",
            "- `./.odylith/bin/odylith benchmark --profile quick --family guidance_behavior`",
            "- Codex-only when useful: `./.odylith/bin/odylith codex compatibility --repo-root .` tells you whether optional project-asset optimizations are actually active on this host.",
            "- Keep `.agents/skills` lookup, missing-shim, and fallback-source details implicit unless they change the next user-visible action.",
            "",
            "## Routing",
            "- Code hygiene and decomposition: `agents-guidelines/ANTI_SLOP_AND_DECOMPOSITION.md`",
            "- Context engine behavior: `agents-guidelines/ODYLITH_CONTEXT_ENGINE.md`",
            "- Grounding and narrowing: `agents-guidelines/GROUNDING_AND_NARROWING.md`",
            "- Governance and delivery surfaces: `agents-guidelines/DELIVERY_AND_GOVERNANCE_SURFACES.md`",
            "- Product surfaces and runtime: `agents-guidelines/PRODUCT_SURFACES_AND_RUNTIME.md`",
            "- Security and trust boundaries: `agents-guidelines/SECURITY_AND_TRUST.md`",
            "- Subagent routing and execution posture: `agents-guidelines/SUBAGENT_ROUTING_AND_ORCHESTRATION.md`",
            "- Validation and testing: `agents-guidelines/VALIDATION_AND_TESTING.md`",
            "- Install, upgrade, and recovery: `agents-guidelines/UPGRADE_AND_RECOVERY.md`",
            "",
            "## Specialist Skills",
            "- `odylith/skills/` is a specialist reference layer. Routine backlog, technical-plan, bug, spec, component, and diagram upkeep should stay on `AGENTS.md`, the repo-local launcher, and truthful `odylith ... --help` first. `odylith plan --help` is a read-only guide; use `odylith governance ...` and `odylith validate plan-* ...` for technical-plan maintenance and validation.",
            "- `skills/delivery-governance-surface-ops/`",
            "- `skills/odylith-context-engine-operations/`",
            "- `skills/odylith-guidance-behavior/`",
            "- `skills/subagent-router/`",
            "- `skills/subagent-orchestrator/`",
            "- `skills/session-context/`",
            "- `skills/component-registry/`",
            "- `skills/diagram-catalog/`",
            "- `skills/casebook-bug-capture/`",
            "- `skills/casebook-bug-investigation/`",
            "- `skills/casebook-bug-preflight/`",
            "- `skills/compass-executive/`",
            "- `skills/compass-timeline-stream/`",
            "- `skills/code-hygiene-guard/`",
            "- `skills/registry-spec-sync/`",
            "- `skills/schema-registry-governance/`",
            "- `skills/security-hardening/`",
            "",
            "## Consumer Boundary",
            "- Consumer installs intentionally exclude Odylith product-maintainer release workflow from the local repo guidance and skill set.",
            "- Use the installed Odylith guidance as the default lane here, and pull in specialist skills only when the task is genuinely advanced or high-risk; do not mirror the Odylith product repo release process into this repository.",
            "",
        ]
    )


def customer_bootstrap_claude_source() -> str:
    return "\n".join(
        [
            "# CLAUDE.md",
            "",
            "@AGENTS.md",
            "",
            "## Claude Code",
            "- This file exists so Claude Code loads the `odylith/` contract from the sibling `AGENTS.md`.",
            "- For repo-owned paths outside `odylith/`, follow the repo-root `AGENTS.md` bridge loaded from root `CLAUDE.md` or `.claude/CLAUDE.md`.",
            "- Use the shared Claude project assets under `../.claude/`, including the auto-memory bridge, project commands, rules, hooks, and subagents, but do not skip the repo-local `odylith` launcher or the governed workflow contract.",
            "- First-match help route: if the user says `Odylith, help`, use the CLI help surface and print stdout only. Do not run install, status, intervention, or launcher diagnostics first.",
            "- First-match demo route: if the user says `Odylith, show me what you can do` or asks what Odylith can do for this repo, use the advisory `odylith show` demo. Do not run install, status, intervention, launcher diagnostics, or sample-app creation first. If Odylith is not installed in the current folder, say that directly.",
            "- Capability inventory route: if the user asks to list Odylith capabilities, engines, product architecture, or the capability map, run `odylith capabilities` and print stdout only. Do not infer the taxonomy from `odylith --help`, `odylith show`, Claude Code capability prose, or any host-model surface.",
            "- Claude Code is a first-class Odylith delegation host for this tree. Use the same routed grounding and validation contract as Codex, but execute delegated leaves through Task-tool subagents and the shared `.claude/` project assets.",
            "",
        ]
    )


def customer_shell_source(*, repo_root: Path) -> str:
    payload = {
        "shell_repo_label": f"Repo · {repo_root.name}",
        "maintainer_notes": [],
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def customer_shell_index_placeholder_source(*, repo_root: Path) -> str:
    repo_label = repo_root.name or "repository"
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Odylith | {repo_label}</title>
    <style>
      :root {{
        color-scheme: light;
        font-family: "SF Pro Display", "Segoe UI", sans-serif;
        background:
          radial-gradient(circle at top right, rgba(125, 211, 252, 0.18), transparent 34%),
          linear-gradient(180deg, #f6fbff 0%, #eef5ff 100%);
        color: #17324d;
      }}

      body {{
        margin: 0;
        min-height: 100vh;
        display: grid;
        place-items: center;
        padding: 24px;
      }}

      main {{
        width: min(760px, 100%);
        display: grid;
        gap: 16px;
        padding: 28px;
        border: 1px solid #cfe0f7;
        border-radius: 28px;
        background: rgba(255, 255, 255, 0.94);
        box-shadow: 0 28px 64px rgba(22, 48, 82, 0.16);
      }}

      p {{
        margin: 0;
        line-height: 1.55;
      }}

      .eyebrow {{
        font-size: 12px;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: #1f5d7a;
      }}

      h1 {{
        margin: 0;
        font-size: clamp(32px, 5vw, 46px);
        line-height: 1;
        letter-spacing: -0.04em;
        max-width: 12ch;
      }}

      .lede {{
        max-width: 62ch;
        color: #35557e;
      }}

      .card {{
        display: grid;
        gap: 10px;
        padding: 16px 18px;
        border: 1px solid #d8e5f8;
        border-radius: 20px;
        background: #f8fbff;
      }}

      code {{
        display: inline-block;
        padding: 5px 8px;
        border-radius: 10px;
        background: #edf4ff;
        border: 1px solid #d4e4fb;
        color: #17324d;
        overflow-wrap: anywhere;
      }}
    </style>
  </head>
  <body>
    <main>
      <p class="eyebrow">Odylith</p>
      <h1>The local shell is getting ready.</h1>
      <p class="lede">
        Odylith already created the repo-owned <code>odylith/</code> workspace for this {repo_label}. If the full shell
        has not rendered yet, inspect the overlap summary, then rerun
        <code>./.odylith/bin/odylith sync --repo-root . --proceed-with-overlap</code> from the repo root.
      </p>
      <section class="card">
        <p><strong>Local shell entrypoint</strong></p>
        <p><code>odylith/index.html</code></p>
      </section>
    </main>
  </body>
</html>
"""


def customer_backlog_index_source(*, repo_root: Path) -> str:
    updated = datetime.now(UTC).date().isoformat()
    return "\n".join(
        [
            "# Backlog Index",
            "",
            f"Last updated (UTC): {updated}",
            "",
            "## Ranked Active Backlog",
            "",
            "| rank | idea_id | title | priority | ordering_score | commercial_value | product_impact | market_value | sizing | complexity | status | link |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
            "",
            "## In Planning/Implementation (Linked to `odylith/technical-plans/in-progress`)",
            "",
            "| rank | idea_id | title | priority | ordering_score | commercial_value | product_impact | market_value | sizing | complexity | status | link |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
            "",
            "## Parked (No Active Plan)",
            "",
            "| rank | idea_id | title | priority | ordering_score | commercial_value | product_impact | market_value | sizing | complexity | status | link |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
            "",
            "## Finished (Linked to `odylith/technical-plans/done`)",
            "",
            "| rank | idea_id | title | priority | ordering_score | commercial_value | product_impact | market_value | sizing | complexity | status | link |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
            "",
            "## Reorder Rationale Log",
            "",
        ]
    ) + "\n"


def customer_plan_index_source() -> str:
    return "\n".join(
        [
            "# Plan Index",
            "",
            "## Active Plans",
            "",
            "| Plan | Status | Created | Updated | Backlog |",
            "| --- | --- | --- | --- | --- |",
            "",
            "## Parked Plans",
            "",
            "| Plan | Status | Created | Updated | Backlog |",
            "| --- | --- | --- | --- | --- |",
            "",
        ]
    ) + "\n"


def customer_component_registry_source() -> str:
    payload = {
        "version": "v1",
        "components": [],
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def customer_diagram_catalog_source() -> str:
    payload = {
        "version": "v1",
        "diagrams": [],
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def refresh_consumer_managed_guidance(
    *,
    repo_root: Path,
    repo_role: str,
    include_brand: bool,
    version: str = "",
    product_root: Path | None = None,
    activate_host_settings: bool = True,
) -> None:
    if str(repo_role).strip() == PRODUCT_REPO_ROLE:
        return
    source_product_root = _managed_product_root(product_root)
    source_project_root = _managed_project_root_assets_root(source_product_root)
    atomic_write_text(repo_root / "odylith" / "AGENTS.md", customer_bootstrap_guidance(), encoding="utf-8")
    atomic_write_text(repo_root / "odylith" / "CLAUDE.md", customer_bootstrap_claude_source(), encoding="utf-8")
    sync_managed_project_root_assets(
        repo_root=repo_root,
        source_root=source_project_root,
        activate_host_settings=activate_host_settings,
    )
    sync_managed_scoped_guidance(repo_root=repo_root, product_root=source_product_root)
    sync_managed_agents_guidelines(repo_root=repo_root, product_root=source_product_root)
    sync_managed_skills(repo_root=repo_root, product_root=source_product_root)
    sync_managed_release_notes(repo_root=repo_root, version=version, product_root=source_product_root)
    if include_brand:
        sync_managed_surface_brand(repo_root=repo_root, product_root=source_product_root)


def sync_consumer_casebook_bug_index(*, repo_root: Path, repo_role: str) -> None:
    if str(repo_role).strip() == PRODUCT_REPO_ROLE:
        return
    bug_root = repo_root / "odylith" / "casebook" / "bugs"
    if not any(
        path.is_file() and path.name not in {"INDEX.md", "AGENTS.md", "CLAUDE.md"}
        for path in bug_root.rglob("*.md")
    ):
        return
    sync_casebook_bug_index.sync_casebook_bug_index(repo_root=repo_root, migrate_bug_ids=True)


def ensure_customer_bootstrap(*, repo_root: Path, version: str, repo_role: str = CONSUMER_REPO_ROLE) -> None:
    directories = (
        repo_root / "odylith",
        repo_root / ".claude",
        repo_root / ".codex",
        repo_root / ".agents" / "skills",
        repo_root / "odylith" / "runtime" / "source",
        repo_root / "odylith" / "runtime" / "source" / "release-notes",
        repo_root / "odylith" / "agents-guidelines",
        repo_root / "odylith" / "skills",
        repo_root / "odylith" / "surfaces" / "brand",
        repo_root / "odylith" / "radar" / "source",
        repo_root / "odylith" / "radar" / "source" / "ideas",
        repo_root / "odylith" / "technical-plans",
        repo_root / "odylith" / "technical-plans" / "in-progress",
        repo_root / "odylith" / "technical-plans" / "done",
        repo_root / "odylith" / "technical-plans" / "parked",
        repo_root / "odylith" / "casebook" / "bugs",
        repo_root / "odylith" / "registry" / "source" / "components",
        repo_root / "odylith" / "atlas" / "source",
        repo_root / "odylith" / "atlas" / "source" / "catalog",
    )
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
    refresh_consumer_managed_guidance(
        repo_root=repo_root,
        repo_role=repo_role,
        include_brand=True,
        version=version,
        activate_host_settings=False,
    )
    shell_source_path = repo_root / "odylith" / "runtime" / "source" / "tooling_shell.v1.json"
    if not shell_source_path.exists():
        atomic_write_text(shell_source_path, customer_shell_source(repo_root=repo_root), encoding="utf-8")
    shell_index_path = repo_root / "odylith" / "index.html"
    if not shell_index_path.exists():
        atomic_write_text(
            shell_index_path,
            customer_shell_index_placeholder_source(repo_root=repo_root),
            encoding="utf-8",
        )
    backlog_index_path = repo_root / "odylith" / "radar" / "source" / "INDEX.md"
    if not backlog_index_path.exists():
        atomic_write_text(backlog_index_path, customer_backlog_index_source(repo_root=repo_root), encoding="utf-8")
    plan_index_path = repo_root / "odylith" / "technical-plans" / "INDEX.md"
    if not plan_index_path.exists():
        atomic_write_text(plan_index_path, customer_plan_index_source(), encoding="utf-8")
    component_registry_path = repo_root / "odylith" / "registry" / "source" / "component_registry.v1.json"
    if not component_registry_path.exists():
        atomic_write_text(component_registry_path, customer_component_registry_source(), encoding="utf-8")
    diagram_catalog_path = repo_root / "odylith" / "atlas" / "source" / "catalog" / "diagrams.v1.json"
    if not diagram_catalog_path.exists():
        atomic_write_text(diagram_catalog_path, customer_diagram_catalog_source(), encoding="utf-8")
    if not version_pin_path(repo_root=repo_root).is_file():
        write_version_pin(repo_root=repo_root, version=version, repo_schema_version=DEFAULT_REPO_SCHEMA_VERSION)


def _managed_product_root(product_root: Path | None = None) -> Path:
    candidate = Path(product_root).expanduser() if product_root is not None else bundled_product_root()
    return candidate if candidate.is_dir() else bundled_product_root()


def _managed_project_root_assets_root(product_root: Path | None = None) -> Path:
    if product_root is not None:
        candidate = Path(product_root).expanduser().parent / "project-root"
        if candidate.is_dir():
            return candidate
    return bundled_project_root_assets_root()


def _path_has_repo_local_symlink(*, repo_root: Path, path: Path) -> bool:
    root = Path(repo_root).resolve()
    candidate = Path(path)
    try:
        relative_path = candidate.relative_to(root)
    except ValueError:
        return True
    current = root
    for part in relative_path.parts:
        current = current / part
        if current.is_symlink():
            return True
    return False


def _copy_managed_asset(*, source_path: Path, repo_root: Path, target_path: Path) -> None:
    root = Path(repo_root).resolve()
    destination = Path(target_path)
    if _path_has_repo_local_symlink(repo_root=root, path=destination.parent):
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    if _path_has_repo_local_symlink(repo_root=root, path=destination):
        return
    shutil.copy2(source_path, destination)


def sync_managed_agents_guidelines(*, repo_root: Path, product_root: Path | None = None) -> None:
    source_root = _managed_product_root(product_root) / "agents-guidelines"
    if not source_root.is_dir():
        return
    root = Path(repo_root).resolve()
    target_root = root / "odylith" / "agents-guidelines"
    if _path_has_repo_local_symlink(repo_root=root, path=target_root):
        return
    target_root.mkdir(parents=True, exist_ok=True)
    for source_path in source_root.rglob("*"):
        if not source_path.is_file() or source_path.name == ".DS_Store":
            continue
        target_path = target_root / source_path.relative_to(source_root)
        _copy_managed_asset(source_path=source_path, repo_root=root, target_path=target_path)


def sync_managed_scoped_guidance(*, repo_root: Path, product_root: Path | None = None) -> None:
    source_root = _managed_product_root(product_root)
    root = Path(repo_root).resolve()
    target_root = root / "odylith"
    if _path_has_repo_local_symlink(repo_root=root, path=target_root):
        return
    target_root.mkdir(parents=True, exist_ok=True)
    for source_path in source_root.rglob("*"):
        if not source_path.is_file() or source_path.name not in GUIDANCE_FILENAMES:
            continue
        relative_path = source_path.relative_to(source_root)
        if len(relative_path.parts) == 1:
            continue
        target_path = target_root / relative_path
        _copy_managed_asset(source_path=source_path, repo_root=root, target_path=target_path)


def prune_removed_project_root_skill_shims(*, source_root: Path, target_root: Path) -> None:
    source_skills_root = source_root / ".agents" / "skills"
    target_skills_root = target_root / ".agents" / "skills"
    if _path_has_repo_local_symlink(repo_root=target_root, path=target_skills_root):
        return
    if not target_skills_root.exists():
        return
    expected_files = (
        {
            path.relative_to(source_skills_root).as_posix()
            for path in source_skills_root.rglob("*")
            if path.is_file() and path.name != ".DS_Store"
        }
        if source_skills_root.is_dir()
        else set()
    )
    for candidate in sorted(target_skills_root.rglob("*"), key=lambda path: len(path.parts), reverse=True):
        if candidate.name == ".DS_Store":
            continue
        if candidate.is_file():
            relative = candidate.relative_to(target_skills_root).as_posix()
            skill_name = Path(relative).parts[0] if Path(relative).parts else ""
            if relative not in expected_files and skill_name in _RETIRED_PROJECT_ROOT_SKILL_SHIMS:
                candidate.unlink()
        elif candidate.is_dir():
            relative_dir = candidate.relative_to(target_skills_root)
            skill_name = relative_dir.parts[0] if relative_dir.parts else ""
            if skill_name in _RETIRED_PROJECT_ROOT_SKILL_SHIMS:
                with contextlib.suppress(OSError):
                    candidate.rmdir()


def sync_managed_project_root_assets(
    *,
    repo_root: Path,
    source_root: Path | None = None,
    activate_host_settings: bool = True,
) -> None:
    source_root = Path(source_root).expanduser() if source_root is not None else bundled_project_root_assets_root()
    if not source_root.is_dir():
        return
    target_root = Path(repo_root).resolve()
    for source_path in source_root.rglob("*"):
        if not source_path.is_file() or source_path.name == ".DS_Store":
            continue
        relative_path = source_path.relative_to(source_root)
        if relative_path in _GENERATED_HOST_CONFIG_RELATIVE_PATHS:
            continue
        target_path = target_root / relative_path
        _copy_managed_asset(source_path=source_path, repo_root=target_root, target_path=target_path)
    prune_removed_project_root_skill_shims(source_root=source_root, target_root=target_root)
    if activate_host_settings:
        write_effective_codex_project_config(repo_root=target_root)
        write_effective_claude_project_settings(repo_root=target_root)


def write_effective_codex_project_config(*, repo_root: Path) -> None:
    target_root = Path(repo_root).resolve()
    codex_root = target_root / ".codex"
    if not codex_root.is_dir() or _path_has_repo_local_symlink(repo_root=target_root, path=codex_root):
        return
    codex_cli_capabilities.write_effective_codex_project_config(repo_root=target_root)
    codex_cli_capabilities.write_effective_codex_hooks(repo_root=target_root)


def write_effective_claude_project_settings(*, repo_root: Path) -> None:
    target_root = Path(repo_root).resolve()
    claude_root = target_root / ".claude"
    if not claude_root.is_dir() or _path_has_repo_local_symlink(repo_root=target_root, path=claude_root):
        return
    claude_cli_capabilities.write_effective_claude_project_settings(repo_root=target_root)


def sync_managed_skills(*, repo_root: Path, product_root: Path | None = None) -> None:
    source_root = _managed_product_root(product_root) / "skills"
    if not source_root.is_dir():
        return
    root = Path(repo_root).resolve()
    target_root = root / "odylith" / "skills"
    if _path_has_repo_local_symlink(repo_root=root, path=target_root):
        return
    target_root.mkdir(parents=True, exist_ok=True)
    for source_path in source_root.rglob("*"):
        if not source_path.is_file() or source_path.name == ".DS_Store":
            continue
        target_path = target_root / source_path.relative_to(source_root)
        _copy_managed_asset(source_path=source_path, repo_root=root, target_path=target_path)


def sync_managed_surface_brand(*, repo_root: Path, product_root: Path | None = None) -> None:
    source_root = _managed_product_root(product_root) / "surfaces" / "brand"
    if not source_root.is_dir():
        return
    root = Path(repo_root).resolve()
    target_root = root / "odylith" / "surfaces" / "brand"
    if _path_has_repo_local_symlink(repo_root=root, path=target_root):
        return
    target_root.mkdir(parents=True, exist_ok=True)
    for source_path in source_root.rglob("*"):
        if not source_path.is_file() or source_path.name == ".DS_Store":
            continue
        target_path = target_root / source_path.relative_to(source_root)
        _copy_managed_asset(source_path=source_path, repo_root=root, target_path=target_path)


def sync_managed_release_notes(*, repo_root: Path, version: str = "", product_root: Path | None = None) -> None:
    source_root = (product_root or bundled_product_root()) / "runtime" / "source" / "release-notes"
    root = Path(repo_root).resolve()
    target_root = root / "odylith" / "runtime" / "source" / "release-notes"
    if _path_has_repo_local_symlink(repo_root=root, path=target_root):
        return
    target_root.mkdir(parents=True, exist_ok=True)
    for candidate in target_root.iterdir():
        if candidate.is_symlink() or candidate.is_file():
            candidate.unlink()
        elif candidate.is_dir():
            shutil.rmtree(candidate)
    if not source_root.is_dir():
        return
    normalized_version = str(version or "").strip().lstrip("v")
    if not normalized_version:
        return
    source_path = source_root / f"v{normalized_version}.md"
    if not source_path.is_file() or source_path.name == ".DS_Store":
        return
    _copy_managed_asset(source_path=source_path, repo_root=root, target_path=target_root / source_path.name)
