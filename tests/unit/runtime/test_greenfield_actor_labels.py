from odylith.runtime.domain_intelligence.greenfield_actor_labels import accepted_actor_label
from odylith.runtime.domain_intelligence.greenfield_actor_labels import localize_leading_actor_reference
from odylith.runtime.domain_intelligence.greenfield_actor_labels import project_specific_actor_row
from odylith.runtime.domain_intelligence.greenfield_confirmed_actor_completion import completed_actor_rows
from odylith.runtime.domain_intelligence.greenfield_confirmed_actor_completion import project_specific_actor_labels
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_context_completion import (
    normalize_confirmed_actor_context,
)


def test_generic_composite_actor_label_gets_project_focus() -> None:
    row = project_specific_actor_row(
        "Reviewer or collaborator",
        project_focus="Protocol outcome notebook",
    )

    assert row == "Protocol Outcome Notebook Reviewer or Collaborator"
    assert not row.startswith("Reviewer")


def test_leading_actor_path_uses_sentence_case_for_an_accepted_role() -> None:
    assert localize_leading_actor_reference(
        "Operator picks a recipe and sees a safe finished state.",
        actor_rows=["Home Cook: selects recipes and responds to prompts."],
        project_focus="Cooking Robot Controller",
        sentence_context=True,
    ) == "Home cook picks a recipe and sees a safe finished state."
    assert localize_leading_actor_reference(
        "City Staff can register one household.",
        actor_rows=["City staff: registers households."],
        project_focus="Flood Shelter Intake",
        sentence_context=True,
    ) == "City staff can register one household."


def test_confirmed_actor_context_localizes_action_led_product_statements_before_sealing() -> None:
    intent = {
        "first_path": "Operator picks a recipe and reaches a safe state.",
        "problem": "Operator needs a dependable way to understand the cook state.",
        "success_metrics": ["Operator picks one recipe without manual reinterpretation."],
        "opportunity": "Operator console availability remains outside the first release.",
        "human_actors": ["Home cook: selects recipes and responds to prompts."],
    }

    normalize_confirmed_actor_context(intent, title="Cooking Robot Controller")

    assert intent["first_path"].startswith("Home cook picks")
    assert intent["problem"].startswith("Home cook needs")
    assert intent["success_metrics"][0].startswith("Home cook picks")
    assert intent["opportunity"].startswith("Operator console")


def test_confirmed_actor_context_preserves_generic_head_artifact_nouns() -> None:
    intent = {
        "product_story": "Reviewer scoring rubric guides final approval.",
        "problem": "Reviewer routing table needs a stable owner.",
        "opportunity": "Operator monitoring dashboard remains outside the first release.",
        "non_goals": ["Owner pricing record remains outside the first release."],
        "human_actors": ["Audit coordinator: reviews and approves audit evidence."],
    }

    normalize_confirmed_actor_context(intent, title="Audit Review Workspace")

    assert intent["product_story"].startswith("Reviewer scoring rubric")
    assert intent["problem"].startswith("Reviewer routing table")
    assert intent["opportunity"].startswith("Operator monitoring dashboard")
    assert intent["non_goals"][0].startswith("Owner pricing record")


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


def test_actor_label_splits_modal_action_from_role_head() -> None:
    assert accepted_actor_label(
        "A domain expert must see the evidence vocabulary preserved accurately",
        project_focus="Wearable arrhythmia review",
    ) == "Domain Expert"
    assert project_specific_actor_row(
        "A domain expert must see the evidence vocabulary preserved accurately",
        project_focus="Wearable arrhythmia review",
    ) == "Domain Expert: must see the evidence vocabulary preserved accurately"
    assert "Domain Expert Must" not in project_specific_actor_row(
        "A domain expert must see the evidence vocabulary preserved accurately",
        project_focus="Wearable arrhythmia review",
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
    ) == "Risky Actions Reviewer: approves risky actions or validates final outputs"
    assert project_specific_actor_row(
        "Developer who builds agent plugins, tools, and custom routing logic",
        project_focus="Distributed Multi-Agent Platform",
    ) == "Developer: builds agent plugins, tools, and custom routing logic"
    assert project_specific_actor_row(
        "Platform admin who manages tenants, credentials, quotas, and integrations",
        project_focus="Distributed Multi-Agent Platform",
    ) == "Platform Admin: manages tenants, credentials, quotas, and integrations"


def test_completed_actor_rows_do_not_promote_approval_artifacts_to_people() -> None:
    spacecraft_intent = {
        "title": "Spacecraft anomaly triage board",
        "first_path": (
            "Mission controllers compare telemetry claims, fault hypotheses, simulation evidence, command risk, "
            "operator approvals, and recovery state before a corrective procedure is released."
        ),
        "human_actors": (
            "Mission controllers compare telemetry claims, fault hypotheses, simulation evidence, command risk, "
            "operator approvals, and recovery state before a corrective procedure is released.",
        ),
        "state_object": "reviewable anomaly state",
    }
    distributed_intent = {
        "title": "Distributed agent jobs",
        "first_path": (
            "Platform operators submit distributed agent jobs, track assigned worker progress, collect execution evidence, "
            "surface blockers, and publish a final run record with reviewer approval."
        ),
        "human_actors": (
            "Platform operators submit distributed agent jobs, track assigned worker progress, collect execution evidence, "
            "surface blockers, and publish a final run record with reviewer approval.",
        ),
        "state_object": "reviewable run state",
    }

    spacecraft_rows = completed_actor_rows(spacecraft_intent, title="Spacecraft anomaly triage board")
    distributed_rows = completed_actor_rows(distributed_intent, title="Distributed agent jobs")

    assert project_specific_actor_labels({**spacecraft_intent, "human_actors": spacecraft_rows}) == [
        "Mission Controllers"
    ]
    assert project_specific_actor_labels({**distributed_intent, "human_actors": distributed_rows}) == [
        "Platform Operators"
    ]


def test_completed_actor_rows_keep_distinct_same_tail_roles() -> None:
    intent = {
        "title": "Review coordination workspace",
        "first_path": (
            "Building safety reviewers record inspection readiness while clinical reviewers compare treatment "
            "exceptions before a coordinated review packet is published."
        ),
        "human_actors": (
            "Building Safety Reviewer: reviews inspection readiness and building risk evidence.",
            "Clinical Reviewer: compares treatment exceptions and clinical review evidence.",
        ),
        "state_object": "coordinated review packet",
    }

    rows = completed_actor_rows(intent, title="Review coordination workspace")
    labels = project_specific_actor_labels({**intent, "human_actors": rows})

    assert labels == ["Building Safety Reviewer", "Clinical Reviewer"]
    assert any(row.startswith("Building Safety Reviewer: reviews inspection readiness") for row in rows)
    assert any(row.startswith("Clinical Reviewer: compares treatment exceptions") for row in rows)


def test_completed_actor_rows_collapse_context_expanded_same_role() -> None:
    intent = {
        "title": "Autonomous warehouse safety state console",
        "first_path": (
            "Operators review robot near-miss reports, aisle lockdown decisions, operator override records, "
            "and release readiness before movement authority expands."
        ),
        "human_actors": (
            "Autonomous Warehouse Operator: reviews operator override records before movement authority expands.",
            "Autonomous Warehouse Safety State Operator: reviews the safety state console.",
        ),
        "state_object": "warehouse safety state",
    }

    rows = completed_actor_rows(intent, title="Autonomous warehouse safety state console")
    labels = project_specific_actor_labels({**intent, "human_actors": rows})

    assert labels == ["Autonomous Warehouse Operator"]


def test_completed_actor_rows_do_not_add_title_expanded_generic_user() -> None:
    intent = {
        "title": "PeptideTrack Personal Peptide Protocol",
        "first_path": "A user adds a peptide, logs each dose, and reviews whether tracked metrics changed.",
        "human_actors": (
            "The individual user running and logging their own peptide protocols",
            "A coach or clinician the user may share an outcome summary with",
        ),
        "state_object": "peptide protocol",
    }

    rows = completed_actor_rows(intent, title=intent["title"])
    labels = project_specific_actor_labels({**intent, "human_actors": rows})

    assert "Individual User" in labels
    assert not any(label.startswith("PeptideTrack") and label.endswith("User") for label in labels)


def test_completed_actor_rows_contextualize_bare_roles_without_duplication_or_role_drift() -> None:
    cases = (
        ("Claims Review Workspace", "User", "Claims Review User"),
        ("Clinical Intake Board", "Person", "Clinical Intake Person"),
        ("Field Sensor Console", "Operator", "Field Sensor Operator"),
    )

    for title, actor, expected_label in cases:
        intent = {
            "title": title,
            "first_path": f"{actor} reviews one result and records the outcome.",
            "human_actors": (actor,),
            "state_object": "A review result.",
        }
        rows = completed_actor_rows(intent, title=title)
        labels = project_specific_actor_labels({**intent, "human_actors": rows})

        assert labels == [expected_label]


def test_completed_actor_rows_do_not_reclassify_the_product_title_as_a_person() -> None:
    intent = {
        "title": "Cold-chain Pantry Ledger",
        "first_path": (
            "The cold-chain pantry ledger receives donated lots from intake clerks. "
            "Nutrition leads verify allergen labels before dispatch drivers hand out parcels."
        ),
        "state_object": "A donated lot.",
        "human_actors": [
            "Nutrition leads: need the product to verify allergen labels and keep the result visible and reviewable",
            "Intake clerks: need the product to provide donated lots and keep the result visible and reviewable",
            "Dispatch drivers: need the product to hand out parcels and keep the result visible and reviewable",
        ],
    }

    rows = completed_actor_rows(intent, title=intent["title"])
    labels = {row.split(":", 1)[0].casefold() for row in rows}

    assert labels == {"nutrition leads", "intake clerks", "dispatch drivers"}
    assert "cold-chain pantry ledger" not in labels
