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
from odylith.install.value_engine_migration import migrate_visible_intervention_value_engine
from odylith.runtime.common import claude_cli_capabilities
from odylith.runtime.common import codex_cli_capabilities
from odylith.runtime.common.guidance_paths import existing_top_level_guidance_paths
from odylith.runtime.common.product_assets import bundled_product_root, bundled_project_root_assets_root
from odylith.runtime.governance import sync_casebook_bug_index

PRODUCT_REPO_ROLE = "product_repo"
CONSUMER_REPO_ROLE = "consumer_repo"


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
            "- First-match demo route: if the user says `Odylith, show me what you can do` or asks what Odylith can do for this repo, use the advisory `odylith show` demo. Do not run install, status, intervention, or launcher diagnostics first.",
            "- Claude Code is a first-class Odylith delegation host. Codex executes routed leaves through `spawn_agent`; Claude Code executes the same bounded delegation contract through Task-tool subagents and the checked-in `.claude/` project assets.",
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
            "- Before any substantive repo scan or code change outside trivial fixes, the agent must start from the repo-local Odylith entrypoint and keep the active workstream, component, or packet in scope before raw repo search, tests, or edits.",
            "- Direct repo scan before that start step is a policy violation unless the task is trivial or Odylith is unavailable.",
            "- Start substantive turns with `./.odylith/bin/odylith start --repo-root .`; it chooses the safe first lane and prints the exact next command when Odylith cannot narrow the slice yet.",
            "- When you already know the exact workstream, component, path, or id, use `./.odylith/bin/odylith context --repo-root . <ref>` before raw repo search. Use `./.odylith/bin/odylith query --repo-root . \"<terms>\"` only after concrete anchors already exist.",
            "- In coding-agent commentary, keep startup, fallback, routing, and packet-selection internals implicit. Describe progress in task terms like the exact file/workstream, the bug under test, or the validation in flight. If an earlier repo-local start attempt degraded but work can continue safely, do not narrate that history. Do not surface routine `odylith start`, `odylith context`, or `odylith query` commands in progress updates, and never prefix commentary with control-plane receipt labels. Mention Odylith during the work only when the user explicitly asks for the command, a real blocker requires it, or a consumer-versus-maintainer lane distinction matters.",
            "- Keep normal commentary task-first and human. Weave Odylith-grounded facts into ordinary updates when they change the next move, and reserve explicit `Odylith Insight:`, `Odylith History:`, or `Odylith Risks:` labels for rare high-signal moments. Pick the strongest one or stay quiet.",
            "- A plain `Odylith, show me what you can do` request is the advisory `odylith show` repo-capability demo. It is not a request to prove intervention UX, diagnose install posture, run `start`, run `doctor`, or explain missing launcher state. Use the first available show command and print stdout only.",
            "- Treat live teaser, `**Odylith Observation**`, and `Odylith Proposal` as the\n  intervention-engine fast path. Treat `Odylith Assist:` as the chatter-owned\n  closeout. Do not collapse those two layers into one ad hoc narration path.",
            "- For Codex and Claude checkpoint hooks, keep the full Observation,\n  Proposal, and Assist bundle in hidden developer context for continuity, but\n  surface the earned Observation/Proposal beat visibly at the hook moment when\n  the host renders hook output. If the host keeps hook output hidden, render\n  the assistant-visible fallback Markdown in chat instead of claiming the\n  engine is active. Stop is the fallback closeout and live-beat recovery lane,\n  not the primary intervention moment; unseen Ambient Highlight,\n  Observation, or Proposal beats may replay there before Assist.",
            "- Hook `systemMessage` or `additionalContext` generation is not proof of\n  chat-visible UX. The user-visible contract is satisfied only by rendered\n  chat text or by a host channel that is proven visible in the active session.\n  When in doubt, run `odylith codex visible-intervention` or `odylith claude\n  visible-intervention` and show that Markdown directly.",
            "- Before claiming the intervention UX is active in a specific chat, run or\n  cite `odylith codex intervention-status` or `odylith claude\n  intervention-status` for that host/session. That status surface is the\n  low-latency delivery ledger for Teaser, Ambient Highlight, Observation,\n  Proposal, and Assist readiness; hook payload generation alone is not enough.",
            "- Existing Codex and Claude sessions may not hot-reload changed hooks,\n  guidance, or source-local runtime code. After changing intervention\n  visibility behavior, prove it in a newly started or explicitly reloaded\n  session, or render `visible-intervention` output directly in the existing\n  chat instead of claiming other open sessions are active.",
            "- At closeout, you may add at most one short `Odylith Assist:` line if it helps the user understand what Odylith materially contributed. Prefer `**Odylith Assist:**` when Markdown formatting is available; otherwise use `Odylith Assist:`. Lead with the user win, link updated governance IDs inline when they were actually changed, and when no governed file moved, name the affected governance-contract IDs from bounded request or packet truth without calling them updated. Frame the edge against `odylith_off` or the broader unguided path when the evidence supports it. Keep it crisp, authentic, clear, simple, insightful, erudite in thought, soulful, friendly, free-flowing, human, and factual. Ground the line in concrete observed counts, measured deltas, or validation outcomes. Humor is fine only when the evidence makes it genuinely funny. Silence is better than filler. At most one supplemental closeout line may appear, chosen from `Odylith Risks:`, `Odylith Insight:`, or `Odylith History:` when the signal is real.",
            "- Explicit feedback that Odylith ambient highlights, interventions, Assist,\n  Observations, Proposals, hooks, or chat output are not visible is a real\n  closeout signal. A short `Odylith Assist:` may acknowledge that visibility\n  continuity without claiming artifact updates; ordinary low-signal short\n  turns should still stay silent.",
            "- For live blocker lanes, never say `fixed`, `cleared`, or `resolved` without qualification unless the hosted proof moved past the prior failing phase. Force three checks first: same fingerprint as the last falsification or not, hosted frontier advanced or not, and whether the claim is code-only, preview-only, or live.",
            "- For substantive tasks, follow this workflow check in order: read the nearest `AGENTS.md`; run the repo-local `odylith start`/`odylith context` step; identify the active workstream, component, or packet; then move into repo scan, tests, and edits.",
            "- In consumer repos, grounding Odylith is diagnosis authority, not blanket write authority: if the issue target is Odylith itself, stop at diagnosis and maintainer-ready feedback unless the operator explicitly authorizes Odylith mutation.",
            "- Treat `odylith upgrade`, `odylith reinstall`, `odylith doctor --repair`, `odylith sync`, and `odylith dashboard refresh` as writes when they change `odylith/` or `.odylith/`; do not run them autonomously as Odylith fixes in consumer repos.",
            "- Treat backlog/workstream, plan, Registry, Atlas, Casebook, Compass, and session upkeep as part of the same grounded Odylith workflow rather than as optional aftercare, but switch to evidence-and-handoff when the issue is Odylith itself in a consumer repo.",
            "- Queued backlog items, case queues, and shell or Compass queue previews are not implicit implementation instructions. Unless the user explicitly asks to work a queued item, do not pick it up automatically just because it appears in Radar, Compass, the shell, or another Odylith queue surface.",
            "- Search existing workstream, plan, bug, component, diagram, and recent session/Compass context first; for consumer Odylith-fix requests, cite that evidence and hand it off to the platform maintainer instead of extending or creating Odylith truth locally.",
            "- If the slice is genuinely new and it is repo-owned non-product work, create the missing workstream and bound plan before non-trivial implementation; if the issue is Odylith itself in a consumer repo, produce a maintainer-ready feedback packet instead.",
            "- Default to the nearest `AGENTS.md`, the repo-local launcher, and truthful `odylith ... --help` for routine backlog, plan, bug, spec, component, and diagram upkeep. Treat `.agents/skills/` and `odylith/skills/` as specialist overlays for advanced packet control, orchestration, or high-risk lanes rather than as the default path.",
            "- When a routine governance task already maps to a first-class CLI family such as `odylith bug capture`, `odylith backlog create`, `odylith component register`, `odylith atlas scaffold`, or `odylith compass log`, go straight to that CLI and keep any `.agents/skills` lookup, missing-shim, or fallback-path details implicit unless they change the next user-visible action.",
            "- `odylith backlog create` is fail-closed and must receive grounded Problem, Customer, Opportunity, Product View, and Success Metrics text; never create or accept a title-only, placeholder, or boilerplate Radar workstream.",
            "- For quick visibility after a narrow truth change, rerender only the owned surface: `odylith radar refresh`, `odylith registry refresh`, `odylith casebook refresh`, `odylith atlas refresh`, or `odylith compass refresh`. Use `odylith compass deep-refresh` when you also want brief settlement. Keep `odylith sync` as the broader governance and correctness lane.",
            "- Treat routed or orchestrated native delegation as the default execution path for substantive grounded consumer-lane work when the current host supports it unless Odylith explicitly keeps the slice local.",
            "- Codex and Claude Code share the same default Odylith lane: the repo-root `AGENTS.md` contract, `./.odylith/bin/odylith`, truthful `odylith ... --help`, and the grounded governance workflow. Keep host-specific tips rare and capability-gated.",
            "- Treat AI slop as a regression. Apply that bar across any language and across runtime code, hooks, prompts, docs, config, templates, generators, and managed assets. Apply it to any codebase or project surface: services, libraries, apps, CLIs, infra glue, scripts, docs, prompts, hooks, templates, config, and generated assets all count. No transitional states: do not replace one slop class with another, move ownership not just file boundaries, and do not treat a shared helper or kernel as a cleanup ornament. Partial shared-kernel adoption is still incomplete; if a shared helper or kernel lands, the touched callers must adopt it or the pass is incomplete. Do not call a slop cleanup complete just because the first smell disappeared; if the replacement smell still exists in the touched slice, the pass is incomplete. When the user asks for repo-wide or lane-wide anti-slop hardening, update guidance, skills, install-generated guidance, host contracts, mirrors, and enforcement tests together; prose-only hardening is incomplete. Repo-wide or lane-wide anti-slop claims require two proof layers: fresh behavior proof for the touched slice and a fresh structural inventory for the claimed scope. One does not substitute for the other. Use `odylith/agents-guidelines/ANTI_SLOP_AND_DECOMPOSITION.md` and `odylith/skills/odylith-code-hygiene-guard/SKILL.md` when quality pressure is high.",
            "- For guidance behavior pressure cases, use `odylith validate guidance-behavior --repo-root .` for deterministic proof and `odylith benchmark --profile quick --family guidance_behavior` for benchmark-family proof. Compact packet summaries only prove the proof path is available; fresh validation still requires the explicit command.",
            "- On Codex, the managed `.codex/` project assets and curated `.agents/skills/` command shims are best-effort enhancements for trusted projects, and install or repair derives the effective `.codex/config.toml` from the local Codex capability snapshot when possible. Claude Code uses Task-tool subagents plus the installed `.claude/` project assets under the same grounding, memory, surfaces, and orchestration contract.",
            "- Treat the managed guidance files under `.claude/`, `.codex/`, the curated `.agents/skills/` command shims, `odylith/AGENTS.md`, `odylith/CLAUDE.md`, the shipped scoped `odylith/**/AGENTS.md` and `odylith/**/CLAUDE.md` companions, `odylith/agents-guidelines/`, and the specialist references under `odylith/skills/` as the Odylith operating layer; keep repo-specific truth in the governance surfaces beside them.",
            "",
            "## Common Fast Paths",
            "- `./.odylith/bin/odylith bug capture --help`",
            "- `./.odylith/bin/odylith backlog create --help`",
            "- `./.odylith/bin/odylith component register --help`",
            "- `./.odylith/bin/odylith atlas scaffold --help`",
            "- `./.odylith/bin/odylith compass log --help`",
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
            "- `odylith/skills/` is a specialist reference layer. Routine backlog, plan, bug, spec, component, and diagram upkeep should stay on `AGENTS.md`, the repo-local launcher, and truthful `odylith ... --help` first.",
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
            "- First-match demo route: if the user says `Odylith, show me what you can do` or asks what Odylith can do for this repo, use the advisory `odylith show` demo. Do not run install, status, intervention, or launcher diagnostics first.",
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
        has not rendered yet, rerun <code>./.odylith/bin/odylith sync --repo-root . --force --impact-mode full</code>
        from the repo root.
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


def refresh_consumer_managed_guidance(*, repo_root: Path, repo_role: str, include_brand: bool, version: str = "") -> None:
    if str(repo_role).strip() == PRODUCT_REPO_ROLE:
        return
    atomic_write_text(repo_root / "odylith" / "AGENTS.md", customer_bootstrap_guidance(), encoding="utf-8")
    atomic_write_text(repo_root / "odylith" / "CLAUDE.md", customer_bootstrap_claude_source(), encoding="utf-8")
    sync_managed_project_root_assets(repo_root=repo_root)
    sync_managed_scoped_guidance(repo_root=repo_root)
    sync_managed_agents_guidelines(repo_root=repo_root)
    sync_managed_skills(repo_root=repo_root)
    sync_managed_release_notes(repo_root=repo_root, version=version)
    if include_brand:
        sync_managed_surface_brand(repo_root=repo_root)


def sync_consumer_casebook_bug_index(*, repo_root: Path, repo_role: str) -> None:
    if str(repo_role).strip() == PRODUCT_REPO_ROLE:
        return
    sync_casebook_bug_index.sync_casebook_bug_index(repo_root=repo_root, migrate_bug_ids=True)


def value_engine_migration_payload(
    *,
    repo_root: Path,
    repo_role: str,
    previous_version: str,
    target_version: str,
    runtime_root: Path | None,
) -> dict[str, object]:
    if str(repo_role).strip() == PRODUCT_REPO_ROLE:
        return {
            "migration_id": "v0.1.11-visible-intervention-value-engine",
            "applied": False,
            "previous_version": str(previous_version or "").strip(),
            "target_version": str(target_version or "").strip(),
            "skipped_reason": "product_repo_source_truth",
        }
    return migrate_visible_intervention_value_engine(
        repo_root=repo_root,
        previous_version=previous_version,
        target_version=target_version,
        runtime_root=runtime_root,
    ).as_dict()


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


def sync_managed_agents_guidelines(*, repo_root: Path) -> None:
    source_root = bundled_product_root() / "agents-guidelines"
    if not source_root.is_dir():
        return
    target_root = repo_root / "odylith" / "agents-guidelines"
    target_root.mkdir(parents=True, exist_ok=True)
    for source_path in source_root.rglob("*"):
        if not source_path.is_file() or source_path.name == ".DS_Store":
            continue
        target_path = target_root / source_path.relative_to(source_root)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target_path)


def sync_managed_scoped_guidance(*, repo_root: Path) -> None:
    source_root = bundled_product_root()
    target_root = repo_root / "odylith"
    target_root.mkdir(parents=True, exist_ok=True)
    for source_path in source_root.rglob("*"):
        if not source_path.is_file() or source_path.name not in GUIDANCE_FILENAMES:
            continue
        relative_path = source_path.relative_to(source_root)
        if len(relative_path.parts) == 1:
            continue
        target_path = target_root / relative_path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target_path)


def prune_removed_project_root_skill_shims(*, source_root: Path, target_root: Path) -> None:
    source_skills_root = source_root / ".agents" / "skills"
    target_skills_root = target_root / ".agents" / "skills"
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
            if relative not in expected_files:
                candidate.unlink()
        elif candidate.is_dir():
            with contextlib.suppress(OSError):
                candidate.rmdir()


def sync_managed_project_root_assets(*, repo_root: Path) -> None:
    source_root = bundled_project_root_assets_root()
    if not source_root.is_dir():
        return
    target_root = Path(repo_root).resolve()
    for source_path in source_root.rglob("*"):
        if not source_path.is_file() or source_path.name == ".DS_Store":
            continue
        target_path = target_root / source_path.relative_to(source_root)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target_path)
    prune_removed_project_root_skill_shims(source_root=source_root, target_root=target_root)
    write_effective_codex_project_config(repo_root=target_root)
    write_effective_claude_project_settings(repo_root=target_root)


def write_effective_codex_project_config(*, repo_root: Path) -> None:
    target_root = Path(repo_root).resolve()
    codex_root = target_root / ".codex"
    if not codex_root.is_dir():
        return
    codex_cli_capabilities.write_effective_codex_project_config(repo_root=target_root)


def write_effective_claude_project_settings(*, repo_root: Path) -> None:
    target_root = Path(repo_root).resolve()
    claude_root = target_root / ".claude"
    if not claude_root.is_dir():
        return
    claude_cli_capabilities.write_effective_claude_project_settings(repo_root=target_root)


def sync_managed_skills(*, repo_root: Path) -> None:
    source_root = bundled_product_root() / "skills"
    if not source_root.is_dir():
        return
    target_root = repo_root / "odylith" / "skills"
    target_root.mkdir(parents=True, exist_ok=True)
    for source_path in source_root.rglob("*"):
        if not source_path.is_file() or source_path.name == ".DS_Store":
            continue
        target_path = target_root / source_path.relative_to(source_root)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target_path)


def sync_managed_surface_brand(*, repo_root: Path) -> None:
    source_root = bundled_product_root() / "surfaces" / "brand"
    if not source_root.is_dir():
        return
    target_root = repo_root / "odylith" / "surfaces" / "brand"
    target_root.mkdir(parents=True, exist_ok=True)
    for source_path in source_root.rglob("*"):
        if not source_path.is_file() or source_path.name == ".DS_Store":
            continue
        target_path = target_root / source_path.relative_to(source_root)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target_path)


def sync_managed_release_notes(*, repo_root: Path, version: str = "") -> None:
    source_root = bundled_product_root() / "runtime" / "source" / "release-notes"
    target_root = repo_root / "odylith" / "runtime" / "source" / "release-notes"
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
    shutil.copy2(source_path, target_root / source_path.name)
