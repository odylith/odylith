"""Static shared contracts for context-engine projection and note slices.

This module owns small immutable constants and regex contracts that multiple
context-engine leaves need during import time. Keeping them here avoids
reaching back through the context-engine store while that larger module is
still initializing.
"""

from __future__ import annotations

import re


_WORKSTREAM_ID_RE = re.compile(r"^B-\d{3,}$")
_ENGINEERING_NOTE_KINDS = (
    "decision",
    "invariant",
    "ownership",
    "architecture",
    "deployment",
    "observability",
    "pitfall",
    "engineering_standard",
    "contract_policy",
    "schema_change",
    "contract_evolution",
    "runbook",
    "testing",
    "tooling_policy",
    "workflow",
    "entrypoint",
    "service_guidance",
    "testing_playbook",
    "guardrail",
    "bug_learning",
    "schema_contract",
    "make_target",
)
_ENGINEERING_NOTE_KIND_SET = frozenset(_ENGINEERING_NOTE_KINDS)
_SECTION_NOTE_SOURCES: tuple[tuple[str, str], ...] = (
    ("architecture", "odylith/agents-guidelines/PRODUCT_SURFACES_AND_RUNTIME.md"),
    ("deployment", "agents-guidelines/DEPLOYMENT.MD"),
    ("observability", "agents-guidelines/OBSERVABILITY.MD"),
    ("pitfall", "agents-guidelines/PITFALLS.md"),
    ("engineering_standard", "agents-guidelines/ENGINEERING_STANDARDS.MD"),
    ("contract_policy", "agents-guidelines/contracts/CONTRACTS.md"),
    ("schema_change", "agents-guidelines/SCHEMA_CHANGE_CHECKLIST.MD"),
    ("contract_evolution", "agents-guidelines/CONTRACT_EVOLUTION.MD"),
    ("testing", "agents-guidelines/TESTING.MD"),
    ("tooling_policy", "odylith/agents-guidelines/CLI_FIRST_POLICY.md"),
    ("workflow", "agents-guidelines/WORKFLOW.md"),
    ("entrypoint", "agents-guidelines/ENTRYPOINTS.MD"),
    ("service_guidance", "agents-guidelines/SERVICES.md"),
    ("testing_playbook", "agents-guidelines/TESTING_PLAYBOOK.MD"),
    ("guardrail", "agents-guidelines/GUARDRAILS.MD"),
)


__all__ = [
    "_ENGINEERING_NOTE_KINDS",
    "_ENGINEERING_NOTE_KIND_SET",
    "_SECTION_NOTE_SOURCES",
    "_WORKSTREAM_ID_RE",
]
