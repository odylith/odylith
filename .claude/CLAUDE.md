# CLAUDE.md

@../AGENTS.md

## Claude Code

- This bridge imports the repo-root contract instead of restating it.
- Use `/odylith-start` before broad repo search; run `/odylith-context` only after startup when an exact workstream, component, path, or bug id is known. Do not launch them in parallel.
- Use `/odylith-query` only after concrete anchors exist, and `/odylith-sync-governance` only when a manual refresh is needed beyond hooks.
- For high-pressure cleanup, route through `odylith-code-hygiene-guard` with `ANTI_SLOP_AND_DECOMPOSITION.md` in scope.
- SessionStart writes compact Compass memory; SubagentStart injects the active Odylith slice into Claude subagents without replacing the launcher-first contract.
- Governance-learning is not chat memory: escaped defects go to Casebook, planned work to Radar/plans, component contracts to Registry, flows to Atlas, and decisions/proof checkpoints to Compass before closeout. Before fixing a bug, search Casebook and governance truth, read prior failed mechanisms, failed fix attempts, and guardrails, do not repeat a fix path that already failed, and capture new mechanism-level learning.
- Keep help, show-me, and capabilities prompts stdout-clean: run `odylith --help`, `odylith show`, or `odylith capabilities`, print stdout only, and do not infer from Claude, Codex, or any host-model surface.
- `odylith plan --help` is read-only; do not probe `odylith/technical-plans/source/`, and do not pair help with parallel exploratory filesystem probes that can cancel the visible help call.
