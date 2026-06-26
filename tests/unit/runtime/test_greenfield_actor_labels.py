from odylith.runtime.domain_intelligence.greenfield_actor_labels import accepted_actor_label
from odylith.runtime.domain_intelligence.greenfield_actor_labels import project_specific_actor_row


def test_generic_composite_actor_label_gets_project_focus() -> None:
    row = project_specific_actor_row(
        "Reviewer or collaborator",
        project_focus="Protocol outcome notebook",
    )

    assert row == "Protocol Outcome Notebook Reviewer or Collaborator"
    assert not row.startswith("Reviewer")


def test_generic_person_actor_uses_accepted_activity_not_project_fallback() -> None:
    assert accepted_actor_label(
        "Person managing their own discomfort (primary user, self-tracking)",
        project_focus="Pattern Relief",
    ) == "Person Managing Discomfort"
    assert accepted_actor_label(
        "Optionally, a coach or clinician the person shares a summary with (read-only, later)",
        project_focus="Pattern Relief",
    ) == "Coach or Clinician"


def test_actor_label_keeps_comma_gerund_descriptions_out_of_visible_actor_names() -> None:
    assert accepted_actor_label(
        "The person on the GLP-1 medication, tracking their own treatment (the only first-class user)",
        project_focus="Medication Companion",
    ) == "Person on the GLP-1 Medication"
    assert accepted_actor_label(
        "Optionally, a caregiver helping that person stay on schedule (later, not in the first path)",
        project_focus="Medication Companion",
    ) == "Caregiver"
    assert "Tracking Their Own Treatment" not in project_specific_actor_row(
        "The person on the GLP-1 medication, tracking their own treatment (the only first-class user)",
        project_focus="Medication Companion",
    )
    assert "Caregiver Helping" not in project_specific_actor_row(
        "Optionally, a caregiver helping that person stay on schedule (later, not in the first path)",
        project_focus="Medication Companion",
    )


def test_actor_label_splits_inline_activity_from_role_head() -> None:
    row = "Discomfort sufferer logging and reviewing their own episodes"

    assert accepted_actor_label(row, project_focus="Personal tracker") == "Discomfort Sufferer"
    assert project_specific_actor_row(row, project_focus="Personal tracker") == (
        "Discomfort Sufferer: logging and reviewing their own episodes"
    )
    assert accepted_actor_label(
        "Physics learner exploring tunneling behavior",
        project_focus="Scientific Lab",
    ) == "Physics Learner"
    assert project_specific_actor_row(
        "Physics learner exploring tunneling behavior",
        project_focus="Scientific Lab",
    ) == "Physics Learner: exploring tunneling behavior"


def test_actor_label_keeps_deciding_whether_out_of_actor_title() -> None:
    row = "Inventory owner deciding whether the item can return to available stock"

    assert accepted_actor_label(row, project_focus="Returns triage board") == "Inventory Owner"
    assert project_specific_actor_row(row, project_focus="Returns triage board") == (
        "Inventory Owner: deciding whether the item can return to available stock"
    )


def test_actor_label_splits_finite_actor_sentences_from_responsibility_text() -> None:
    assert accepted_actor_label(
        "Clinic reviewers use the ready-or-blocked status to decide the next action",
        project_focus="Specialty Clinic Referral Tracker",
    ) == "Clinic Reviewers"
    assert project_specific_actor_row(
        "Referral sources supply missing documents when a blocker is raised",
        project_focus="Specialty Clinic Referral Tracker",
    ) == "Referral Sources: supply missing documents when a blocker is raised"
    assert "Use the" not in accepted_actor_label(
        "Clinic reviewers use the ready-or-blocked status to decide the next action",
        project_focus="Specialty Clinic Referral Tracker",
    )


def test_actor_label_keeps_relative_clause_actions_out_of_role_label() -> None:
    assert accepted_actor_label(
        "Operator who launches runs and monitors active work",
        project_focus="Distributed Multi-Agent Platform",
    ) == "Distributed Multi-Agent Operator"
    assert project_specific_actor_row(
        "Operator who launches runs and monitors active work",
        project_focus="Distributed Multi-Agent Platform",
    ) == "Distributed Multi-Agent Operator: launches runs and monitors active work"
    assert project_specific_actor_row(
        "Operator Who Launches: launches runs and monitors active work",
        project_focus="Distributed Multi-Agent Platform",
    ) == "Distributed Multi-Agent Operator: launches runs and monitors active work"


def test_actor_label_keeps_generic_relative_role_descriptions_as_body() -> None:
    assert project_specific_actor_row(
        "Reviewer who approves risky actions or validates final outputs",
        project_focus="Distributed Multi-Agent Platform",
    ) == "Risky Actions or Validates Final Outputs Reviewer: approves risky actions or validates final outputs"
    assert project_specific_actor_row(
        "Developer who builds agent plugins, tools, and custom routing logic",
        project_focus="Distributed Multi-Agent Platform",
    ) == "Developer: builds agent plugins, tools, and custom routing logic"
    assert project_specific_actor_row(
        "Platform admin who manages tenants, credentials, quotas, and integrations",
        project_focus="Distributed Multi-Agent Platform",
    ) == "Platform Admin: manages tenants, credentials, quotas, and integrations"
