from __future__ import annotations

import json

from odylith.runtime.domain_intelligence import greenfield_apply_prewrite
from odylith.runtime.domain_intelligence import greenfield_apply_write
from odylith.runtime.domain_intelligence import greenfield_proposals
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent import parse_confirmed_intent_text
from odylith.runtime.domain_intelligence.greenfield_post_confirm_completion import build_greenfield_package_report
from odylith.runtime.domain_intelligence.proposal_tribunal import run_greenfield_tribunal


DISTRIBUTED_AGENTS_CONFIRMED_INTENT_TEXT = """# Distributed Multi-Agent Platform

## Product story
A platform for teams that need several specialized AI agents to collaborate on complex work without losing control, traceability, or accountability. Users should be able to define agent roles, assign a goal, watch the work unfold across machines or services, intervene when needed, and receive a final result with a readable audit trail.

## State object
The core product state is a durable work graph: goals, tasks, agents, messages, tool calls, artifacts, approvals, policies, failures, retries, costs, and completion evidence. Every agent action should attach to that graph so distributed execution stays inspectable and recoverable.

## First complete path
A workflow designer creates a workspace, configures a small roster of agents, grants scoped tool access, and starts a shared goal. The platform decomposes the work, routes subtasks to agents, streams progress into a live graph, asks a human for approval when policy requires it, resolves or escalates conflicts, and delivers a final artifact plus execution history.

## Human actors
- Workflow designer who defines agent roles, policies, and task templates
- Operator who launches runs and monitors active work
- Reviewer who approves risky actions or validates final outputs
- Platform admin who manages tenants, credentials, quotas, and integrations
- Developer who builds agent plugins, tools, and custom routing logic

## External systems
- Model providers and inference gateways
- Source control, ticketing, document, database, and messaging tools
- Identity provider for authentication and role-based access
- Observability, logging, metrics, and tracing backends
- Secret stores and policy engines

## Internal product systems
- Agent registry and capability catalog
- Task planner and routing engine
- Distributed run coordinator
- Message bus and event log
- Tool permission and approval system
- Artifact store and state graph
- Human review console
- Evaluation, replay, and audit subsystem

## Critical assumptions
- The first product should prioritize controlled collaboration over fully autonomous execution.
- Human review is required for destructive, costly, sensitive, or externally visible actions.
- Runs must be replayable enough to debug failures and defend decisions.
- Agent capabilities, permissions, and model choices need to be explicit rather than hidden inside prompts.
- Multi-tenant isolation, credential safety, and cost controls are first-version requirements, not later polish.

## Ambiguities
- Whether the first customer is internal engineering teams, enterprise operations teams, research labs, or AI product builders.
- Whether agents are mostly hosted by this platform or allowed to run as remote worker processes owned by customers.
- Whether the product should expose a visual workflow builder, an API-first developer platform, or both.
- How much autonomy is acceptable before human approval is mandatory.
- Whether the first release must support cross-organization collaboration or only one tenant at a time.

## Proof boundary
The first proof should show one end-to-end distributed run with at least three agents, scoped tools, live state updates, human approval, failure recovery, and a final artifact backed by an audit trail. It should prove coordination, observability, permissioning, and recovery before optimizing for large-scale agent marketplaces or advanced scheduling.
"""


def test_prewrite_package_repairs_relative_actor_clause_before_public_previews(tmp_path) -> None:
    prompt = "building a distributed multi-agent platform"
    proposal = greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt=prompt,
        release_selector="0.0.1",
        confirmed_intent=parse_confirmed_intent_text(DISTRIBUTED_AGENTS_CONFIRMED_INTENT_TEXT, prompt=prompt),
    )
    tribunal = run_greenfield_tribunal(proposal, release_selector="0.0.1")
    prewrite = greenfield_apply_prewrite.build_prewrite_completion_package(
        root=tmp_path,
        proposal=proposal,
        release_selector="0.0.1",
        backlog_args=greenfield_proposals._backlog_apply_args(proposal, release_selector="0.0.1"),
        validation_gate=tribunal.to_dict(),
        release_assignment_note=greenfield_apply_write.release_assignment_note(selector="0.0.1"),
    )

    report = build_greenfield_package_report(prewrite.package)
    preview_text = json.dumps(
        {
            "project_brief": prewrite.package.project_brief_preview,
            "next_steps": prewrite.package.next_steps_preview,
        }
    )

    assert report.passed, "\n".join(report.issues)
    assert "Launches launches" not in preview_text
    assert "Operator Who Launches" not in preview_text
    assert "Distributed Multi-Agent Operator: launches runs and monitors active work" in preview_text
