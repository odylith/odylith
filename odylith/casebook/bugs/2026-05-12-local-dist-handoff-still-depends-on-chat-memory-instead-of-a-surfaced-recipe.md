- Bug ID: CB-200

- Status: Open

- Created: 2026-05-12

- Severity: P2

- Reproducibility: High

- Type: Product

- Description: Local dist handoff still depends on chat memory instead of a surfaced recipe

- Impact: Maintainers repeatedly ask for a local install dist and the agent rediscovers the release-asset and localhost install recipe instead of using durable governed memory, adding delay and eroding trust.

- Components Affected: Install / Upgrade / Migration Runtime; Operator Experience

- Environment(s): Odylith maintainer lane, local release dist build for 0.1.15 on macOS Apple Silicon.

- Detected By: Operator feedback on 2026-05-11 asking why repeated local dist builds were not remembered and requesting a Casebook record.

- Failure Signature: A local dist request requires rediscovering make local-release-assets plus the localhost curl-equivalent install command; no surfaced Casebook or runbook memory points the agent directly to the known recipe.

- Trigger Path: User asks for a new dist for local installs after repeated prior local release builds.

- Ownership: Install/upgrade/release runtime and operator-experience handoff.

- Timeline: Captured 2026-05-12 through `odylith bug capture`.

- Blast Radius: Maintainer release rehearsal, local consumer install validation, and Codex/Claude handoffs that need the same localhost install recipe.

- SLO/SLA Impact: Adds avoidable latency to release-candidate handoff and risks incomplete or inconsistent local install commands.

- Data Risk: No customer data is read or written; the risk is release-handoff metadata accuracy only.

- Security/Compliance: Policy and security posture: the local HTTP server and skipped Sigstore verification flags are maintainer-only for localhost release rehearsal; public install must stay HTTPS and signed-release verified, and the recipe must not normalize insecure flags for users.

- Invariant Violated: Repeated maintainer release handoff knowledge must be captured as governed memory or runbook truth, not reconstructed from chat history.
