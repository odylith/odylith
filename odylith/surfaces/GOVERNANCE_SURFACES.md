# Odylith Governance Surfaces

Odylith owns the product behavior for Radar, Atlas, Compass, Registry,
Casebook, and the tooling shell while continuing to read repo truth in place.

Related docs:

- `odylith/PRODUCT_COMPONENTS.md`
- `odylith/runtime/TRIBUNAL_AND_REMEDIATION.md`
- `odylith/OPERATING_MODEL.md`

## Canonical Commands

```bash
odylith sync --repo-root . --force
odylith sync --repo-root . --check-only --check-clean
odylith compass refresh --repo-root . --wait
odylith compass log --repo-root . --kind decision --summary "<summary>"
odylith compass update --repo-root . --statement "<current execution state>"
```

## Repo Truth Roots

- `odylith/radar/source/`
- `odylith/radar/source/releases/`
- `odylith/casebook/bugs/`
- `odylith/technical-plans/`
- `odylith/atlas/source/`
- `odylith/compass/runtime/`
- `odylith/registry/source/`

## Repo-Local Truth

Odylith does not assume your repo already has strong plans, specs, diagrams,
or component inventory. The point is to make that truth local, reviewable, and
usable by both humans and agents.

| Repo Truth | Surface | What It Carries |
| --- | --- | --- |
| `odylith/registry/source/component_registry.v1.json` | Registry | authoritative component inventory |
| `odylith/registry/source/components/<component-id>/CURRENT_SPEC.md` + `FORENSICS.v1.json` | Registry | living specs, feature history, and component forensics |
| `odylith/radar/source/` | Radar | ranked workstreams, queue state, and dependency truth |
| `odylith/radar/source/releases/` | Radar + Release | repo-local release catalog, `current`/`next` alias ownership, and append-only workstream targeting history |
| `odylith/atlas/source/` | Atlas | topology and diagram source |
| `odylith/compass/runtime/` | Compass | execution trail and decisions |
| `odylith/casebook/bugs/` | Casebook | failures, regressions, and corrective follow-through |

## What The Surfaces Do Together

Radar says what matters now. Radar's release subtree says what belongs to the
current and next ship lanes. Atlas and Registry say what the system is.
Compass says what changed recently. Casebook says what failed before. The
shell connects those views so the agent can move through one grounded slice
without rebuilding the repo story from scratch. Compass runtime refresh now
flows through `odylith compass refresh`, with `dashboard refresh --surfaces
compass` kept only as the multi-surface compatibility wrapper over the same
engine.

## Concrete Surface Examples

| Surface | What The Agent Gets | Example |
| --- | --- | --- |
| Radar | active queue, blockers, successors, and dependency order | The agent sees that refund correctness is blocked by ledger idempotency and webhook retry work, so it follows the real dependency chain. |
| Atlas | topology and trace paths between components | Before splitting auth, the agent can inspect the gateway, session store, audit log, and admin console boundary as one system. |
| Registry | authoritative component inventory and linked specs | A PII redaction change can be tied back to the right worker, interface, and owning component instead of guessed from filenames. |
| Compass | recent decisions and execution trail | During a failing release, the agent can see what was already tried, what passed, and where the rollback stalled. |
| Casebook | prior incidents and recurring failure signatures | Before touching a rate limiter or cache path, the agent can inspect prior failures and the guardrails that followed. |
| tooling shell | one connected view across all surfaces | The operator can move from blocked workstream to topology to component dossier to prior failure in one place. |

## Waves, Umbrellas, And Compass Tracking

Radar is not just a flat queue. One umbrella workstream can own a phased
program with explicit waves, carried workstreams, and gate checkpoints.

Compass tracks the same program from the execution side. Radar says what the
program is supposed to do; Compass shows whether live execution is actually
moving through those waves.

Release planning is additive again: a workstream may participate in umbrella
execution waves and still target one explicit release through the repo-local
release catalog. That target-ship truth does not replace parent/child
topology, and it does not replace the canonical maintainer publication lane.

## Umbrella Use Cases

- Platform auth hardening across inventory, gateway or session work, and
  audit cleanup
- Tenant migration across segmentation, backfill, traffic shift, and cleanup
- Marketplace launch across onboarding, payouts, moderation, and search
- Infra cost-down work across cache, batch, warehouse, and observability

## End-To-End Scenarios

1. Roll out tenant-aware access revocation across a SaaS platform:
   Radar binds the real workstream, Atlas shows the trust boundary, Registry
   shows every impacted component, Compass carries the current state, and
   Casebook keeps prior permission failures visible.
2. Untangle a broken release after a data-pipeline migration:
   The agent can recover the reopened workstream, inspect ingestion-to-warehouse
   topology, check the owning contracts, and see the exact rollback trail
   before proposing the fix.
3. Make a messy monorepo usable for autonomous agents:
   Odylith helps the team build local backlog truth, component inventory,
   topology, execution history, and bug memory so the system stops relying on
   disconnected tickets and oral history.

## Rules

- Do not hand-edit generated surface artifacts when a renderer or `odylith sync` owns them.
- Keep repo truth local. Odylith reads and renders it; it does not replace it.
- Keep each surface's source inputs and generated artifacts in that surface's
  own subtree.
- Interactive `B-###` workstream buttons are a shared compact non-Atlas
  surface contract. Keep them separate from broader identifier-link styling
  and change them through
  `src/odylith/runtime/surfaces/dashboard_ui_primitives.py`, not through
  renderer-local one-off size overrides.
- Those same interactive `B-###` controls also share one destination
  contract: they deep-link to the Radar workstream route. Do not let local
  Compass scope URLs or other surface-local routes masquerade as the same
  button behavior.
- Generic chip selectors must explicitly exclude interactive `B-###` controls.
  Do not let broader chip or label styling bleed into workstream buttons.
- Compass `Release Targets` layout is operator-owned. Keep the established
  stacked release format for `Targeted Workstreams` and `Completed
  Workstreams`, and do not reintroduce side-by-side or auto-fit multi-column
  release boards without explicit operator authorization.
- Top-line governance KPI/stat cards are shared shell contract too. Compass,
  Radar, Registry, and Casebook should use the shared Dashboard KPI helpers
  for grid, card surface, and label/value typography instead of local stat
  tile forks.
- When a surface ships live checked-in artifacts plus bundle mirrors, keep one
  canonical source path and require exact live-versus-bundle mirror equality.
- Do not maintain duplicated static forks of generated shared CSS. Compose from
  the shared generator plus thin surface-local overrides.
- Browser proof is mandatory for operator-owned layout and workstream-button
  contracts; static string checks alone are insufficient.
- Browser proof is also mandatory for shared KPI/stat-card contracts. Audit
  computed padding, radius, label/value typography, and release-card labeling
  across Compass, Radar, Registry, and Casebook.
- Browser proof for workstream-button contracts must click representative
  `B-###` controls in Compass, Atlas, and Registry and verify the shell lands
  on Radar.
- Use the `odylith/` guidance tree for Odylith-owned behavior and keep
  repo-root guidance authoritative for repo-owned paths outside `odylith/`.
