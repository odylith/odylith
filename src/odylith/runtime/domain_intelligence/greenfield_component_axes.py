"""Generic semantic axes for greenfield component differentiation."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ComponentAxis:
    key: str
    triggers: tuple[str, ...]
    owned_state: str
    accepted_inputs: str
    produced_outputs: str
    states_or_transitions: str
    outside_boundary: str
    local_proof: tuple[str, ...]
    unique_failure: str


COMPONENT_AXES: tuple[ComponentAxis, ...] = (
    ComponentAxis(
        key="submission_versioning",
        triggers=(
            "submission",
            "submit",
            "version",
            "versioning",
            "file",
            "upload",
        ),
        owned_state="submitted item identity, intake status, actor-supplied payload, file set, version chain, missing-field blocker, and intake handoff state",
        accepted_inputs="submitting actor identity, submitted payload, uploaded files, metadata, version reference, required-field answers, and intake command",
        produced_outputs="accepted submission, version snapshot, missing-input blocker, rejected intake signal, file association, and downstream review handoff",
        states_or_transitions="draft, submitted, validation-failed, missing-required-input, versioned, withdrawn, accepted-for-review, and handed-off",
        outside_boundary="downstream workflow routing, protected access decisions, decision comparison, immutable audit retention, notification delivery, and sibling product responsibilities",
        local_proof=(
            "A submitted item carries the right actor, payload, file set, metadata, and version before downstream review begins.",
            "Missing required intake data blocks submission instead of creating trusted downstream state.",
            "Assignment, scoring, notification, and final decision changes do not mutate intake identity or version history.",
        ),
        unique_failure="A submitted item can enter review with the wrong identity, missing files, stale metadata, or an incorrect version snapshot.",
    ),
    ComponentAxis(
        key="request_intake_capture",
        triggers=(
            "intake",
            "capture",
            "captures",
            "form",
            "answer",
            "answers",
            "request",
            "entry",
            "input",
        ),
        owned_state="intake request, submitted answers, required-input status, validation context, actor identity, intake timestamp, and handoff state",
        accepted_inputs="actor identity, intake command, submitted answers, required fields, validation rules, source context, and prior intake state",
        produced_outputs="validated intake request, missing-input blocker, rejected-input signal, accepted answer set, intake summary, and downstream handoff",
        states_or_transitions="not-started, in-progress, submitted, missing-required-input, validation-failed, accepted, corrected, withdrawn, and handed-off",
        outside_boundary="source import ownership, downstream calculation, final decision authority, immutable audit retention, notification delivery, and sibling product responsibilities",
        local_proof=(
            "Intake proof shows actor identity, submitted answers, required-input status, validation context, and downstream handoff.",
            "Missing, malformed, stale, or unauthorized intake data blocks downstream handoff instead of creating trusted state.",
            "Import, calculation, decision, notification, and audit changes do not rewrite the submitted intake answer set.",
        ),
        unique_failure="Downstream work can trust the wrong request, missing required input, stale context, or an answer set that lost actor and validation evidence.",
    ),
    ComponentAxis(
        key="option_evaluation_ranking",
        triggers=(
            "comparison",
            "compare",
            "ranking",
            "rank",
            "select",
            "selection",
            "order",
            "ordered",
            "alternative",
            "alternatives",
            "option",
            "choice",
        ),
        owned_state="candidate option set, comparison criteria, ranking rule, selected option, ordered alternatives, explanation, and ranking handoff state",
        accepted_inputs="candidate options, comparison criteria, actor context, ranking command, tie-break rule, exclusion reason, and prior selection state",
        produced_outputs="ranked option list, selected option, ordered alternatives, comparison explanation, blocked-selection marker, and downstream handoff",
        states_or_transitions="empty, candidates-loaded, comparable, ranked, selected, tied, blocked, revised, and handed-off",
        outside_boundary="raw option intake, quote calculation, final user commitment, notification delivery, immutable audit retention, and sibling product responsibilities",
        local_proof=(
            "Ranking proof shows candidate options, comparison criteria, tie-break rule, selected option, ordered alternatives, and explanation together.",
            "Missing candidates, invalid criteria, excluded options, or unresolved ties block selection instead of producing a trusted ranking.",
            "Input capture, quote calculation, final commitment, and audit changes do not rewrite the ranked option list or selection rationale.",
        ),
        unique_failure="A user can trust the wrong selected option, an excluded alternative can be ranked as eligible, or the ranking rationale can detach from the criteria.",
    ),
    ComponentAxis(
        key="external_handoff",
        triggers=(
            "handoff",
            "handoffs",
            "provider",
            "recipient",
            "endpoint",
            "fulfillment",
            "delivery",
            "dispatch",
        ),
        owned_state="approved handoff payload, recipient reference, provider status, failed-handoff marker, retry state, provider reference, and handoff evidence",
        accepted_inputs="approved handoff command, actor identity, recipient reference, payload snapshot, provider status, validation context, and prior handoff state",
        produced_outputs="provider handoff record, accepted or failed marker, provider reference, retry blocker, handoff evidence, and downstream status handoff",
        states_or_transitions="not-requested, ready, sent, accepted, failed, retry-blocked, acknowledged, reconciled, and handed-off",
        outside_boundary="upstream approval ownership, provider system truth, fulfillment execution, notification delivery, immutable audit retention, and sibling product responsibilities",
        local_proof=(
            "Handoff proof shows actor identity, approved payload, recipient reference, provider status, failure marker, and provider reference together.",
            "Missing approval, recipient, payload, or provider acknowledgement blocks downstream handoff instead of creating trusted external state.",
            "Approval, provider execution, notification, and audit changes do not rewrite the submitted handoff payload or failure evidence.",
        ),
        unique_failure="An external handoff can look sent while the payload, recipient, provider status, or failure evidence is missing or assigned to the wrong boundary.",
    ),
    ComponentAxis(
        key="quote_calculation",
        triggers=(
            "price",
            "pricing",
            "quote",
            "cost",
            "estimate",
            "rate",
            "amount",
            "charge",
        ),
        owned_state="quote request, pricing inputs, cost rule, calculated amount, quote explanation, invalid-quote blocker, and quote handoff state",
        accepted_inputs="quote request, actor context, priced item or option, quantity or usage context, cost rule, validation context, and prior quote state",
        produced_outputs="calculated quote, cost breakdown, quote explanation, invalid-quote blocker, pricing provenance reference, and downstream quote handoff",
        states_or_transitions="not-requested, input-ready, calculated, invalid-input-blocked, stale, revised, accepted, expired, and handed-off",
        outside_boundary="raw intake ownership, option ranking, payment capture, final commitment authority, immutable audit retention, and sibling product responsibilities",
        local_proof=(
            "Quote proof ties request input, priced option, cost rule, calculated amount, explanation, and provenance reference together.",
            "Missing, stale, malformed, or unauthorized quote inputs block calculated output instead of creating trusted pricing state.",
            "Input capture, option ranking, payment, and audit changes do not rewrite calculated quote state or explanation.",
        ),
        unique_failure="A calculated quote can use the wrong input, stale cost rule, missing quantity context, or detached explanation while still looking trusted.",
    ),
    ComponentAxis(
        key="review_presentation_surface",
        triggers=(
            "surface",
            "screen",
            "view",
            "dashboard",
            "display",
            "presentation",
            "visible",
            "shows",
            "show",
            "review",
            "rationale",
            "selected",
        ),
        owned_state="visible item state, display context, user action state, explanation panel, blocker message, selected item marker, and presentation handoff state",
        accepted_inputs="upstream result, evidence reference, actor context, display request, visible blocker state, selected item command, and prior visible state",
        produced_outputs="reviewable display, selected item acknowledgement, visible blocker message, correction request, user action event, and downstream presentation handoff",
        states_or_transitions="empty, loading, visible, explanation-visible, action-pending, selected, corrected, blocked, confirmed, and handed-off",
        outside_boundary="upstream calculation, source import, final decision authority, notification delivery, immutable audit retention, and sibling product responsibilities",
        local_proof=(
            "Presentation proof shows upstream result, evidence reference, visible explanation, blocker message, and actor action together.",
            "Missing upstream evidence, hidden blockers, or invalid actor actions keep the display blocked instead of producing trusted downstream state.",
            "Upstream calculation, source import, final decision, notification, and audit changes do not rewrite the visible action state.",
        ),
        unique_failure="A user can act on a stale display, miss a blocker, trust an unexplained result, or select an item without evidence tied to the upstream result.",
    ),
    ComponentAxis(
        key="case_workspace",
        triggers=(
            "case",
            "workspace",
            "agenda",
            "checklist",
            "notes",
            "note",
        ),
        owned_state="case identity, workspace status, checklist progress, actor notes, readiness marker, blocked item, and workspace handoff state",
        accepted_inputs="case or item identity, actor note, checklist answer, status update, source context, blocker signal, and workspace command",
        produced_outputs="workspace state update, checklist result, saved note, readiness or blocked marker, case summary, and downstream handoff",
        states_or_transitions="not-started, opened, in-review, noted, blocked, ready, revised, decided, closed, and handed-off",
        outside_boundary="source-system import, specialized context rendering, feedback grouping, final decision authority, immutable audit retention, and sibling product responsibilities",
        local_proof=(
            "The workspace shows the correct case identity, checklist progress, saved notes, blockers, and readiness marker before downstream work uses it.",
            "A missing case identity, unresolved blocker, or incomplete checklist prevents the workspace from appearing ready.",
            "Specialized map, feedback, decision, audit, or export changes do not rewrite workspace status or notes.",
        ),
        unique_failure="A user can act on the wrong case, miss a blocker, trust an incomplete checklist, or lose the notes that explain readiness.",
    ),
    ComponentAxis(
        key="definition_rules",
        triggers=(
            "criteria",
            "criterion",
            "protocol",
            "rule",
            "definition",
            "eligibility",
            "inclusion",
            "exclusion",
            "threshold",
            "policy",
        ),
        owned_state="criteria definitions, protocol version, inclusion and exclusion rules, rule validity, exception notes, and rule-change history",
        accepted_inputs="domain question, rule draft, threshold, policy source, exception note, actor identity, and prior protocol version",
        produced_outputs="active criteria set, protocol version, rule validation result, exception blocker, and rule-change handoff",
        states_or_transitions="draft, active, revised, superseded, exception-blocked, invalid-rule, and retired",
        outside_boundary="assignment routing, permission grants, independent review decisions, evidence extraction, scoring output, synthesis conclusions, and sibling product responsibilities",
        local_proof=(
            "Criteria and protocol rules are versioned before downstream decisions use them.",
            "Invalid or missing rules block downstream review instead of creating trusted decisions.",
            "Changing assignment routing does not mutate criteria or protocol state.",
        ),
        unique_failure="The wrong rule version can drive downstream decisions, an invalid criterion can look active, or a protocol change can lose its audit context.",
    ),
    ComponentAxis(
        key="onboarding_consent",
        triggers=("onboarding", "consent", "signup", "sign", "registration", "profile", "preference", "permission"),
        owned_state="onboarding step, consent choice, actor profile, required disclosure, eligibility answer, preference snapshot, and entry handoff state",
        accepted_inputs="actor identity, onboarding answer, consent decision, required disclosure, eligibility response, preference value, and entry command",
        produced_outputs="created profile, consent record, missing-disclosure blocker, eligibility marker, preference snapshot, and downstream entry handoff",
        states_or_transitions="not-started, started, consented, declined, missing-disclosure, ineligible, profile-created, revised, and handed-off",
        outside_boundary="measurement storage, plan recommendation, daily tracking, analytics calculation, immutable audit retention, and sibling product responsibilities",
        local_proof=(
            "The entry flow records actor identity, consent, required disclosures, eligibility answers, and preferences before downstream state uses them.",
            "Missing consent, missing disclosure, or ineligible answers block downstream handoff instead of creating trusted state.",
            "Measurement, plan, tracking, analytics, and retention changes do not rewrite onboarding consent state.",
        ),
        unique_failure="A downstream workflow can start without valid consent, required disclosures, eligibility context, or the actor profile needed to explain the first path.",
    ),
    ComponentAxis(
        key="measurement_capture",
        triggers=("measurement", "measure", "metric", "metrics", "reading", "capture", "baseline", "observation", "value"),
        owned_state="measurement entry, baseline snapshot, metric value, unit, capture timestamp, source reference, invalid-measurement blocker, and measurement handoff state",
        accepted_inputs="actor identity, metric value, unit, measurement timestamp, baseline context, source reference, and validation rule",
        produced_outputs="validated measurement record, baseline snapshot, invalid-measurement blocker, source reference, and downstream measurement handoff",
        states_or_transitions="empty, entered, validated, rejected, source-linked, baseline-set, revised, and handed-off",
        outside_boundary="onboarding consent, goal recommendation, habit logging, analytics interpretation, privacy deletion authority, and sibling product responsibilities",
        local_proof=(
            "A measurement keeps actor identity, metric value, unit, timestamp, source, and validation status before downstream guidance uses it.",
            "Invalid, missing, stale, or unauthorized measurements block downstream handoff instead of appearing trusted.",
            "Goal, habit, analytics, safety, and privacy changes do not mutate captured measurement history.",
        ),
        unique_failure="A user can see guidance based on the wrong metric, unit, timestamp, source, or baseline measurement.",
    ),
    ComponentAxis(
        key="symptom_self_tracking",
        triggers=(
            "symptom",
            "symptoms",
            "pain",
            "episode",
            "intensity",
            "body",
            "location",
            "relief",
            "medication",
            "dose",
            "side",
            "effect",
            "trigger",
            "timeline",
        ),
        owned_state="symptom entry, episode timestamp, intensity rating, body location, trigger note, relief method, medication-taken record, dose-as-recorded value, side-effect note, timeline event, correction history, and safety disclaimer marker",
        accepted_inputs="actor identity, symptom entry command, episode timestamp, intensity rating, body location, trigger note, relief method, medication-taken record, dose-as-recorded value, side-effect note, and validation context",
        produced_outputs="validated symptom entry, timeline event, trend snapshot update, correction history, safety disclaimer marker, invalid-entry blocker, and downstream handoff",
        states_or_transitions="draft, recorded, validated, corrected, deleted, blocked, stale, visible-on-timeline, and handed-off",
        outside_boundary="diagnosis, prescribing, medication dosing advice, emergency-care authority, clinician sharing, immutable audit retention, and sibling product responsibilities",
        local_proof=(
            "Symptom entry proof keeps actor identity, timestamp, intensity, body location, trigger, relief method, and medication facts attached to the timeline event.",
            "Invalid, missing, stale, or corrected symptom entries remain visible instead of becoming trusted trend evidence.",
            "Safety proof keeps diagnosis, prescribing, dosing advice, emergency escalation, and clinician-sharing authority outside symptom-entry ownership.",
        ),
        unique_failure="A user can trust a timeline or trend built from the wrong symptom entry, missing intensity, hidden correction, unreviewed medication fact, or unsafe health claim.",
    ),
    ComponentAxis(
        key="medication_relief_tracking",
        triggers=(
            "medication",
            "medicine",
            "dose",
            "dosage",
            "relief",
            "reminder",
            "reminders",
            "missed",
            "side",
            "effect",
        ),
        owned_state="medication-taken record, dose-as-recorded value, relief attempt, reminder preference, missed-reminder marker, side-effect note, safety disclaimer marker, and medication-relief handoff state",
        accepted_inputs="actor identity, medication fact command, dose-as-recorded value, relief attempt, reminder preference, side-effect note, validation context, and prior tracking state",
        produced_outputs="validated medication fact, relief tracking event, reminder setting state, missed-reminder state, side-effect review marker, safety disclaimer marker, and downstream handoff",
        states_or_transitions="not-recorded, recorded, validated, corrected, reminder-disabled, reminder-set, missed, side-effect-noted, safety-blocked, and handed-off",
        outside_boundary="diagnosis, prescribing, medication dosing advice, emergency-care authority, clinician sharing, immutable audit retention, and sibling product responsibilities",
        local_proof=(
            "Medication fact proof keeps actor identity, dose-as-recorded value, relief attempt, reminder preference, side-effect note, and safety disclaimer evidence attached.",
            "Invalid, missing, stale, or corrected medication facts remain visible instead of becoming trusted trend or summary evidence.",
            "Safety proof records medication facts exactly as user-entered while refusing diagnosis, prescribing, dosing advice, and emergency-care authority.",
        ),
        unique_failure="A medication or relief record can imply unsafe advice, hide a correction, lose reminder state, or treat a user-entered dose as a recommendation.",
    ),
    ComponentAxis(
        key="goal_plan_generation",
        triggers=(
            "goal",
            "goals",
            "plan",
            "planning",
            "generation",
            "generate",
            "guidance",
            "recommendation",
            "recommend",
            "adjustment",
            "adjust",
            "target",
            "targets",
            "computed",
        ),
        owned_state="goal target, plan rule, progress snapshot, status window, adjustment rationale, safety constraint, and plan handoff state",
        accepted_inputs="baseline state, progress snapshot, status window, actor preference, target goal, safety constraint, and adjustment request",
        produced_outputs="plan target, recommendation result, adjustment rationale, unsafe-plan blocker, confidence marker, and downstream plan handoff",
        states_or_transitions="not-generated, goal-set, input-ready, generated, stale-input-blocked, safety-blocked, adjusted, accepted, revised, and handed-off",
        outside_boundary="raw measurement capture, daily progress logging, status analytics, policy guardrail ownership, immutable audit retention, and sibling product responsibilities",
        local_proof=(
            "Plan adjustment proof ties baseline context, progress snapshot, status window, safety constraint, recommendation result, and adjustment rationale together.",
            "Unsafe, impossible, missing, or stale goal context blocks plan generation instead of producing trusted guidance.",
            "Measurement capture, progress logging, analytics, and policy guardrails do not rewrite the recommendation result or rationale.",
        ),
        unique_failure="A generated plan or adjustment result can imply unsafe guidance, detach from baseline context, ignore progress evidence, or lose the rationale needed to review it.",
    ),
    ComponentAxis(
        key="habit_activity_tracking",
        triggers=("habit", "habits", "activity", "tracking", "track", "log", "logging", "daily", "progress", "checkin"),
        owned_state="daily log entry, habit status, activity summary, check-in response, progress signal, missed-entry blocker, and tracking handoff state",
        accepted_inputs="actor identity, habit log, activity event, check-in answer, timestamp, reminder context, and prior tracking state",
        produced_outputs="recorded daily log, progress signal, missed-entry marker, habit summary, check-in status, and downstream tracking handoff",
        states_or_transitions="not-logged, logged, partial, missed, corrected, stale, summarized, and handed-off",
        outside_boundary="onboarding consent, measurement baseline ownership, plan generation, status interpretation, immutable audit retention, and sibling product responsibilities",
        local_proof=(
            "Daily tracking records the actor, timestamp, habit entry, activity marker, check-in response, and progress status.",
            "Missing, partial, stale, or corrected logs stay visible instead of being counted as ordinary completed progress.",
            "Plan, measurement, analytics, safety, and retention changes do not rewrite daily tracking entries.",
        ),
        unique_failure="Progress can look complete when logs are missing, stale, attached to the wrong actor, or detached from the check-in state.",
    ),
    ComponentAxis(
        key="status_analytics_explanation",
        triggers=("analytics", "analysis", "explanation", "explanations", "status", "progress", "trend", "summary"),
        owned_state="progress summary, status explanation, analytics window, trend signal, evidence reference, confidence marker, and explanation handoff state",
        accepted_inputs="tracking summary, measurement snapshot, status window, evidence reference, explanation rule, actor context, and prior analytics state",
        produced_outputs="status explanation, progress trend, analytics finding, confidence marker, stale-data blocker, and downstream explanation handoff",
        states_or_transitions="not-calculated, input-ready, explained, low-confidence, stale-data-blocked, disputed, revised, and handed-off",
        outside_boundary="raw tracking entry ownership, measurement capture, plan generation, policy guardrail ownership, immutable audit retention, and sibling product responsibilities",
        local_proof=(
            "Analytics proof links tracking summary, measurement snapshot, status window, evidence reference, status explanation, and confidence marker.",
            "Missing, stale, low-confidence, or disputed inputs block the status explanation instead of creating trusted analytics output.",
            "Tracking, measurement, plan, policy, and audit changes do not rewrite the analytics finding or explanation rationale.",
        ),
        unique_failure="A status explanation can look current while progress inputs are stale, confidence is low, evidence is missing, or the analytics rationale is detached from source state.",
    ),
    ComponentAxis(
        key="communication_log",
        triggers=("communication", "message", "messages", "notify", "notification", "response", "reply"),
        owned_state="message history, notification request, delivery status, response marker, unresolved-response blocker, actor contact reference, and communication handoff state",
        accepted_inputs="actor identity, message command, contact reference, message template or body, delivery context, response event, and prior communication state",
        produced_outputs="recorded message, delivery marker, response status, unresolved-response blocker, communication summary, and downstream handoff",
        states_or_transitions="not-started, drafted, sent, delivered, failed, response-needed, responded, stale, and handed-off",
        outside_boundary="upstream decision ownership, provider delivery execution, source import ownership, immutable audit retention, and sibling product responsibilities",
        local_proof=(
            "Communication proof records actor identity, contact reference, message body or template, delivery marker, response status, and downstream handoff.",
            "Missing contact details, failed delivery, or unresolved response requirements remain visible instead of appearing complete.",
            "Decision, provider delivery, source import, and audit changes do not rewrite the message history or response marker.",
        ),
        unique_failure="A user can appear notified or responded-to when contact evidence, delivery status, message content, or response state is missing.",
    ),
    ComponentAxis(
        key="privacy_data_lifecycle",
        triggers=("privacy", "retention", "export", "deletion", "delete", "erase", "consent", "data", "download"),
        owned_state="privacy preference, retention rule, export request, deletion request, protected-data classification, consent history, and data-lifecycle handoff state",
        accepted_inputs="actor identity, privacy preference, retention policy, export command, deletion command, protected-state reference, consent record, and audit context",
        produced_outputs="privacy decision, retained or deleted marker, export package, deletion confirmation, access blocker, consent-history reference, and lifecycle handoff",
        states_or_transitions="requested, allowed, denied, exported, deletion-pending, deleted, retained, restored, blocked, and handed-off",
        outside_boundary="onboarding question ownership, measurement interpretation, plan generation, daily tracking, trend analytics, and sibling product responsibilities",
        local_proof=(
            "Privacy lifecycle proof shows who requested export or deletion, what protected state was affected, and which retention rule applied.",
            "Unauthorized export, missing consent, or blocked deletion remains visible instead of silently changing protected data.",
            "Onboarding, measurement, plan, tracking, and analytics changes do not override privacy or retention decisions.",
        ),
        unique_failure="Protected data can be exported, retained, deleted, or exposed without the right actor, consent, retention rule, or replayable lifecycle evidence.",
    ),
    ComponentAxis(
        key="check_rule_ledger",
        triggers=(
            "check",
            "checks",
            "ledger",
            "code",
            "reference",
            "references",
            "pass",
            "block",
            "outcome",
            "outcomes",
        ),
        owned_state="check record, reviewer comments, rule references, pass or block outcome, check evidence, and handoff state",
        accepted_inputs="item to check, rule reference, reviewer comment, pass or block command, blocker signal, actor identity, and prior check state",
        produced_outputs="recorded check, rule-linked comment, pass or block outcome, blocker signal, and downstream decision handoff",
        states_or_transitions="not-checked, checking, passed, blocked, commented, revised, disputed, and handed-off",
        outside_boundary="submission intake, document versioning, final decision authority, immutable audit retention, work routing, and sibling product responsibilities",
        local_proof=(
            "The check ledger records the reviewed item, rule reference, reviewer comment, pass or block outcome, and handoff evidence.",
            "Missing rule references or unresolved blockers prevent a pass outcome from appearing decision-ready.",
            "Submission, revision, assignment, and final decision changes do not silently rewrite the check record.",
        ),
        unique_failure="A reviewed item can look passed without the rule reference, reviewer comment, blocker state, or source evidence needed to trust the check.",
    ),
    ComponentAxis(
        key="intake_import",
        triggers=("ingestion", "ingest", "import", "deduplication", "dedupe", "citation", "metadata", "activity", "attribution", "normalize", "record"),
        owned_state="import batch, source identity, normalized record, duplicate match, rejected input, provenance marker, and intake handoff state",
        accepted_inputs="source payload, import file, source timestamp, actor identity, deduplication key, normalization rule, and upstream source metadata",
        produced_outputs="normalized record, duplicate or rejected-input signal, provenance reference, import summary, and downstream intake handoff",
        states_or_transitions="not-imported, imported, normalized, duplicate-found, rejected, quarantined, provenance-attached, and handed-off",
        outside_boundary="criteria definition, downstream work routing, review decisions, evidence extraction, synthesis conclusions, and sibling product responsibilities",
        local_proof=(
            "Accepted source input produces a normalized record with provenance.",
            "Duplicates and malformed inputs are rejected or quarantined before downstream state changes.",
            "Import provenance remains visible after handoff.",
        ),
        unique_failure="A duplicate or malformed source record can be trusted as new, provenance can be lost, or downstream review can use the wrong source identity.",
    ),
    ComponentAxis(
        key="tracked_selection_list",
        triggers=("follow", "following", "watchlist", "watch", "selected", "saved", "list", "bookmark", "portfolio"),
        owned_state="selected item membership, follow or watch state, actor note, source reference, blocked membership marker, and list handoff state",
        accepted_inputs="actor identity, item identity, selection command, source reference, note, visibility rule, and prior membership state",
        produced_outputs="saved selection, follow or watch marker, removed or blocked marker, list snapshot, and downstream signal handoff",
        states_or_transitions="empty, added, watched, followed, ignored, removed, blocked, source-linked, and handed-off",
        outside_boundary="source ingestion, confidence calculation, recommendation ownership, notification delivery, immutable audit retention, and sibling product responsibilities",
        local_proof=(
            "A selected item carries the right actor, item identity, source reference, note, and follow or watch state before downstream work uses it.",
            "A blocked, removed, or hidden item cannot appear as an active selection.",
            "Source ingestion, confidence scoring, notification, and final decision changes do not mutate list membership.",
        ),
        unique_failure="A user can follow or watch the wrong item, a removed item can remain active, or list membership can detach from the source reference that explains it.",
    ),
    ComponentAxis(
        key="signal_quality_deduplication",
        triggers=("signal", "signals", "confidence", "deduplication", "dedupe", "duplicate", "quality", "score"),
        owned_state="candidate signal identity, confidence marker, duplicate cluster, quality flag, source reference, rejected-signal blocker, and signal handoff state",
        accepted_inputs="normalized source signal, source reference, duplicate key, confidence rule, quality threshold, actor context, and prior signal state",
        produced_outputs="deduplicated signal, confidence result, duplicate marker, rejected or low-quality blocker, source-linked explanation, and downstream signal handoff",
        states_or_transitions="unscored, scored, duplicate-found, low-confidence, rejected, source-linked, accepted, disputed, and handed-off",
        outside_boundary="source import ownership, selected-list membership, action recommendation, notification delivery, immutable audit retention, and sibling product responsibilities",
        local_proof=(
            "A candidate signal is deduplicated and carries source reference, confidence, and quality status before downstream display or action.",
            "Duplicate, low-confidence, or source-missing signals are blocked or marked instead of appearing trusted.",
            "List membership, notification, and final decision changes do not mutate confidence or duplicate state.",
        ),
        unique_failure="A duplicate or low-confidence signal can look actionable, a signal can lose its source reference, or two source events can be merged incorrectly.",
    ),
    ComponentAxis(
        key="condition_model",
        triggers=(
            "model",
            "profile",
            "health",
            "condition",
            "trend",
            "telemetry",
            "signal",
            "summary",
            "classification",
            "metric",
            "normalization",
            "normalize",
            "generation",
        ),
        owned_state="derived condition model, measurement summary, trend signal, confidence marker, readiness classification, model input version, and model handoff state",
        accepted_inputs="normalized observations, prior state, measurement summary, inspection notes, model rule version, actor identity, and validation context",
        produced_outputs="condition profile, trend classification, confidence result, model blocker, readiness signal, and downstream alert or decision handoff",
        states_or_transitions="unmodeled, input-ready, modeled, low-confidence, trend-detected, validation-failed, classified, and handed-off",
        outside_boundary="raw source import, alert acknowledgement, operational decision authority, immutable audit retention, notification delivery, and sibling product responsibilities",
        local_proof=(
            "Accepted observations produce a derived condition profile with confidence and model-input provenance.",
            "Missing or invalid observations block model readiness instead of creating a trusted condition result.",
            "Alert, notification, and decision changes do not mutate the model input version or derived classification.",
        ),
        unique_failure="A stale or low-confidence model output can look ready, a condition trend can detach from its source inputs, or a downstream decision can trust an invalid classification.",
    ),
    ComponentAxis(
        key="alert_signal",
        triggers=("alert", "warning", "degradation", "anomaly", "threshold", "flag", "indicator", "loss", "risk"),
        owned_state="alert rule, threshold evaluation, signal severity, warning state, acknowledgement marker, alert evidence, and escalation handoff state",
        accepted_inputs="condition signal, threshold rule, severity policy, source evidence, actor acknowledgement, prior alert state, and escalation trigger",
        produced_outputs="alert event, warning severity, acknowledged or blocked marker, escalation signal, alert evidence record, and downstream action handoff",
        states_or_transitions="inactive, evaluating, triggered, acknowledged, escalated, suppressed, stale, cleared, and handed-off",
        outside_boundary="raw source import, derived model ownership, final action decision, read-model ranking, immutable audit retention, and sibling product responsibilities",
        local_proof=(
            "A qualifying signal creates an alert with threshold evidence, severity, and acknowledgement state.",
            "A stale, suppressed, or missing signal cannot appear as a current actionable warning.",
            "Model recalculation and final action decisions do not rewrite the alert event history.",
        ),
        unique_failure="A serious signal can fail to alert, a stale warning can look current, or an alert can lose the evidence needed for a safe downstream action.",
    ),
    ComponentAxis(
        key="action_decision",
        triggers=("maintenance", "action", "recommendation", "clearance", "resolve", "resolution"),
        owned_state="action recommendation, source evidence, decision rationale, approval or blocked outcome, required follow-up, responsible actor, and decision handoff evidence",
        accepted_inputs="recommendation context, source evidence, actor identity, policy constraint, decision command, unresolved blocker, and prior action state",
        produced_outputs="action decision, blocked or approved outcome, rationale note, follow-up requirement, review-visible decision evidence, and release handoff",
        states_or_transitions="draft, review-ready, blocked, approved, rejected, watched, deferred, completed, and handed-off",
        outside_boundary="raw source import, model calculation, alert triggering, notification delivery, immutable audit retention, and sibling product responsibilities",
        local_proof=(
            "The action decision shows source evidence, responsible actor, unresolved blockers, rationale, and final outcome.",
            "Unresolved blockers prevent an approved or cleared outcome from appearing final.",
            "Source import, evidence review, and sibling state changes do not silently rewrite the recorded decision rationale.",
        ),
        unique_failure="A decision can appear approved while blockers remain unresolved, the rationale can detach from evidence, or a follow-up requirement can disappear.",
    ),
    ComponentAxis(
        key="user_decision_journal",
        triggers=("journal", "decision", "note", "notes", "rationale", "plan", "ignore", "watch", "research", "saved"),
        owned_state="user decision entry, rationale note, planned next action, ignored or watched marker, timestamp, evidence reference, and decision-journal handoff state",
        accepted_inputs="actor identity, selected item, evidence reference, rationale note, decision command, planned action, and prior journal state",
        produced_outputs="recorded decision entry, rationale note, watch or ignore marker, planned-action state, decision timestamp, and downstream journal handoff",
        states_or_transitions="draft, recorded, watched, ignored, research-planned, action-planned, revised, archived, and handed-off",
        outside_boundary="source ingestion, confidence calculation, regulated recommendation ownership, notification delivery, immutable audit retention, and sibling product responsibilities",
        local_proof=(
            "The decision journal records the actor, selected item, evidence reference, rationale, timestamp, and planned next action.",
            "A missing rationale or evidence reference keeps the journal entry incomplete instead of decision-ready.",
            "Source ingestion, confidence scoring, and notification changes do not rewrite the user's recorded decision.",
        ),
        unique_failure="A user decision can appear documented without rationale, attach to the wrong item, or imply a recommendation that the product does not own.",
    ),
    ComponentAxis(
        key="policy_risk_guardrails",
        triggers=("risk", "risks", "disclaimer", "compliance", "policy", "privacy", "guardrail", "guardrails", "safety", "consent"),
        owned_state="policy rule, risk disclosure, disclaimer text, consent requirement, privacy constraint, blocked-action marker, and guardrail review state",
        accepted_inputs="actor context, policy rule, risk fact, disclaimer copy, consent marker, privacy classification, and attempted action",
        produced_outputs="allowed or blocked action, risk disclosure, disclaimer requirement, privacy decision, compliance review marker, and guardrail handoff",
        states_or_transitions="unchecked, allowed, blocked, disclaimer-required, consent-required, privacy-restricted, reviewed, revised, and handed-off",
        outside_boundary="source import ownership, confidence scoring, list membership, user decision ownership, notification delivery, immutable audit retention, and sibling product responsibilities",
        local_proof=(
            "Policy guardrails show the rule, risk disclosure, consent or privacy requirement, and allow or block outcome before downstream action.",
            "Missing consent, unsafe policy posture, or undisclosed risk blocks the action instead of allowing it silently.",
            "Source ingestion, confidence scoring, and user decision changes do not mutate the policy rule or disclaimer state.",
        ),
        unique_failure="A risky or restricted action can proceed without disclosure, consent, privacy handling, or compliance review evidence.",
    ),
    ComponentAxis(
        key="recommendation_impact_summary",
        triggers=(
            "recommendation",
            "recommended",
            "impact",
            "finding",
            "findings",
            "summary",
            "analysis",
            "supporting",
        ),
        owned_state="recommendation text, impact findings, supporting source references, comparison points, conditions under consideration, and summary handoff state",
        accepted_inputs="upstream case context, source evidence, impact finding, recommendation draft, comparison point, actor identity, and summary command",
        produced_outputs="recommendation summary, impact finding set, source-backed comparison point, missing-evidence blocker, and downstream decision handoff",
        states_or_transitions="draft, source-linked, incomplete, ready-for-comparison, disputed, revised, accepted-for-decision, and handed-off",
        outside_boundary="upstream summary intake, final vote or approval authority, immutable audit retention, feedback grouping, and sibling product responsibilities",
        local_proof=(
            "The recommendation summary keeps recommendation text, impact findings, comparison points, and source references together before a decision uses it.",
            "Missing source evidence or disputed impact findings block decision readiness instead of appearing as trusted summary output.",
            "Final decision, vote, audit, feedback, and workspace changes do not rewrite the recommendation analysis.",
        ),
        unique_failure="A downstream decision can trust a recommendation that lost its source references, impact findings, comparison context, or disputed-evidence marker.",
    ),
    ComponentAxis(
        key="assignment_permission",
        triggers=(
            "assignment",
            "assign",
            "routing",
            "conflict",
            "eligibility",
            "escalation",
        ),
        owned_state="assignee eligibility, assignment routing, access grants, conflict constraints, permission state, and assignment state",
        accepted_inputs="assignee role, availability, conflict signal, permission request, source actor, and assignment trigger",
        produced_outputs="assignee selection, permission decision, access grant or denial, conflict blocker, and assignment handoff",
        states_or_transitions="unassigned, eligible, assigned, access-granted, access-denied, conflict-blocked, and reassigned",
        outside_boundary="criteria definition, form layout, scoring rubric, score calculation, immutable audit storage, comparison dashboard, and sibling product responsibilities",
        local_proof=(
            "The right assignee is selected, permission limits are applied, and conflicts block assignment.",
            "An actor without permission cannot access or mutate the assigned work.",
            "Missing eligibility creates an assignment blocker instead of a valid assignment.",
        ),
        unique_failure="The wrong assignee can receive access, a conflict can be hidden, or an unauthorized assignment can look valid.",
    ),
    ComponentAxis(
        key="access_audit",
        triggers=(
            "access",
            "permission",
            "role",
            "visibility",
            "rbac",
            "grant",
            "redaction",
            "subscription",
            "entitlement",
            "paid",
        ),
        owned_state="role policy, visibility rule, permission grant, protected access decision, audit event, version reference, and history retention state",
        accepted_inputs="actor identity, role attribute, visibility rule, access request, protected state reference, state-change event, timestamp, and retention rule",
        produced_outputs="access grant or denial, protected visibility decision, audit entry, version snapshot, retention decision, and replay evidence",
        states_or_transitions="requested, granted, denied, redacted, recorded, versioned, retained, expired, restored, and audit-blocked",
        outside_boundary="domain workflow intake, sibling state derivation, recommendation logic, notification delivery, final release approval, and sibling product responsibilities",
        local_proof=(
            "Only authorized actors can view or mutate protected state, and every access decision is replayable.",
            "A denied or redacted view blocks protected data exposure while preserving an audit entry.",
            "Audit history can reconstruct changes without rewriting sibling workflow or dashboard state.",
        ),
        unique_failure="Protected state can be exposed to the wrong actor, a permission decision can be untraceable, or retention can erase required audit evidence.",
    ),
    ComponentAxis(
        key="screening_decision",
        triggers=("screening", "screen", "independent", "decision", "disagreement", "resolve", "resolution", "include", "exclude"),
        owned_state="independent review decision, reviewer response, disagreement marker, resolution reason, decision status, and decision handoff evidence",
        accepted_inputs="assigned item, active criteria version, reviewer identity, review answer, exclusion reason, disagreement signal, and resolution action",
        produced_outputs="screening decision, disagreement blocker, resolved outcome, decision reason, and downstream review handoff",
        states_or_transitions="not-screened, in-review, included, excluded, disagreed, resolution-needed, resolved, and handed-off",
        outside_boundary="criteria definition, assignment routing, permission grants, evidence extraction, scoring rubric ownership, synthesis conclusions, and sibling product responsibilities",
        local_proof=(
            "Independent decisions remain separate until a resolution reason is recorded.",
            "A disagreement blocks downstream completion until the resolution action is traceable.",
            "Changing criteria or assignment state does not silently rewrite recorded decisions.",
        ),
        unique_failure="A disagreement can disappear, an exclusion reason can be lost, or a downstream handoff can treat unresolved decisions as final.",
    ),
    ComponentAxis(
        key="evidence_extraction",
        triggers=("annotation", "annotate", "extraction", "extract", "evidence", "field", "pdf", "document", "capture", "source"),
        owned_state="source annotation, extracted field, evidence reference, source location, missing-evidence blocker, extraction version, and handoff history",
        accepted_inputs="included source, source document, actor identity, extraction field definition, annotation target, evidence text, and provenance reference",
        produced_outputs="validated extraction field, annotation record, missing-evidence blocker, source reference, and downstream assessment handoff",
        states_or_transitions="not-started, annotated, extracted, missing-evidence, validation-failed, revised, source-linked, and handed-off",
        outside_boundary="criteria definition, assignment routing, screening inclusion decisions, score calculation, synthesis conclusions, and sibling product responsibilities",
        local_proof=(
            "Extracted fields stay attached to their source location and actor.",
            "Missing evidence blocks downstream assessment instead of producing trusted output.",
            "Screening decisions do not rewrite extraction provenance.",
        ),
        unique_failure="Evidence can be extracted from the wrong source, a missing field can pass as complete, or provenance can detach from the downstream claim.",
    ),
    ComponentAxis(
        key="evidence_review",
        triggers=("evidence", "review", "trace", "inspect", "inspection", "source", "readiness"),
        owned_state="review evidence package, source references, inspection notes, evidence completeness, review-visible blockers, readiness evidence, and review handoff state",
        accepted_inputs="source evidence, inspection notes, derived signals, actor identity, completeness rule, blocker state, and review command",
        produced_outputs="review-ready evidence package, missing-evidence blocker, source trace, readiness finding, review-visible explanation, and downstream decision handoff",
        states_or_transitions="not-reviewed, evidence-linked, incomplete, blocked, review-ready, disputed, accepted-for-decision, and handed-off",
        outside_boundary="final decision authority, action recommendation ownership, assignment routing, permission grants, immutable audit retention, and sibling product responsibilities",
        local_proof=(
            "The review evidence package shows source references, inspection notes, blockers, and readiness evidence before a downstream decision uses it.",
            "Missing or disputed evidence blocks review readiness instead of producing a trusted decision handoff.",
            "Decision, assignment, permission, and audit changes do not rewrite the source evidence package.",
        ),
        unique_failure="A downstream decision can trust incomplete evidence, a source reference can detach from the review, or a disputed finding can look ready.",
    ),
    ComponentAxis(
        key="risk_review_workspace",
        triggers=("risk", "review", "readiness", "blocker", "blocked", "flag", "flags", "note", "notes", "workspace", "assessment"),
        owned_state="risk review record, risk flags, reviewer notes, readiness blockers, review status, decision rationale, and review handoff state",
        accepted_inputs="item or request identity, source evidence, risk signal, reviewer note, actor identity, readiness rule, and prior review state",
        produced_outputs="risk review finding, readiness blocker, review-visible rationale, approval or blocked recommendation, and downstream review handoff",
        states_or_transitions="not-reviewed, in-review, risk-flagged, blocked, rationale-recorded, ready, returned, and handed-off",
        outside_boundary="source intake, checklist rule ownership, final decision authority, notification delivery, immutable audit retention, and sibling product responsibilities",
        local_proof=(
            "Risk review proof shows source evidence, risk flags, reviewer notes, readiness blockers, and rationale before downstream approval uses it.",
            "Missing rationale, unresolved risk flags, or stale source evidence block readiness instead of producing a trusted review handoff.",
            "Checklist rules, source intake, notification, final decision, and audit changes do not rewrite the risk review record.",
        ),
        unique_failure="A product can appear ready while risk flags, reviewer rationale, source evidence, or readiness blockers are missing or assigned to the wrong boundary.",
    ),
    ComponentAxis(
        key="decision_review",
        triggers=("decision", "workflow", "editorial", "ledger", "approval", "approve", "package", "blocker", "note", "readiness", "final", "outcome", "compare", "comparison"),
        owned_state="decision evidence package, reviewer notes, unresolved blockers, final approval state, decision readiness, and decision rationale",
        accepted_inputs="assembled evidence, reviewer note, blocker state, actor identity, readiness signal, approval command, and prior decision state",
        produced_outputs="decision package, approval or blocked outcome, review-visible rationale, final decision state, and release handoff",
        states_or_transitions="draft, review-ready, blocked, returned, approved, rejected, finalized, and handed-off",
        outside_boundary="criteria definition, work routing, permission grants, revision intake, raw evidence extraction, score ownership, immutable audit storage, and sibling product responsibilities",
        local_proof=(
            "The decision package shows evidence, reviewer notes, unresolved blockers, and final approval state before release handoff.",
            "Unresolved blockers prevent an approval outcome from appearing final.",
            "Changing upstream revision, assignment, or extraction state does not silently rewrite the recorded decision rationale.",
        ),
        unique_failure="A decision can appear approved while blockers remain unresolved, reviewer rationale can detach from evidence, or a final outcome can hide missing review context.",
    ),
    ComponentAxis(
        key="form_scoring",
        triggers=("form", "scoring", "score", "template", "rubric", "assessment", "rating", "quality", "bias"),
        owned_state="review fields, scoring rubric, scoring templates, validation rules, scoring inputs, and score outputs",
        accepted_inputs="review evidence, reviewer answers, rubric version, required fields, score input, and validation context",
        produced_outputs="validated review form, score output, missing-field blocker, rubric result, and scoring evidence handoff",
        states_or_transitions="not-started, in-progress, missing-required-field, validation-failed, scored, revised, and submitted",
        outside_boundary="form layout outside the scoring fields, reviewer assignment, assignment routing, permission grants, immutable audit storage, retention enforcement, dashboard ranking, and sibling product responsibilities",
        local_proof=(
            "Required review fields and rubric inputs produce the expected score output.",
            "Missing required fields block submission before a score is trusted.",
            "The scoring surface refuses reviewer assignment and permission grants while keeping rubric validation separate.",
            "Changing assignment or permission state does not mutate the scoring template.",
        ),
        unique_failure="A missing required field can be scored, the wrong rubric version can be used, or a score can be trusted without validation evidence.",
    ),
    ComponentAxis(
        key="revision_lifecycle",
        triggers=("revision", "round", "resubmission", "revise", "changes", "response", "return", "requested"),
        owned_state="revision round, requested-change set, actor response, resubmission version, round deadline, unresolved revision blocker, and decision handoff state",
        accepted_inputs="prior decision, requested changes, actor identity, revised payload, response notes, deadline rule, and previous version reference",
        produced_outputs="revision request, resubmission snapshot, response package, round status, unresolved-change blocker, and downstream decision handoff",
        states_or_transitions="not-requested, requested, awaiting-response, resubmitted, under-review, incomplete, accepted, rejected, and handed-off",
        outside_boundary="initial submission identity, work routing, score ownership, immutable audit retention, notification delivery, read-model ranking, and sibling product responsibilities",
        local_proof=(
            "A requested change produces a traceable revision round with response notes and a resubmission version.",
            "Incomplete responses block the revision round before a downstream decision can treat it as ready.",
            "Initial intake, assignment, scoring, and audit records remain separate from revision-round state.",
        ),
        unique_failure="A revision round can lose the requested change, attach the wrong resubmission version, or make an incomplete actor response look decision-ready.",
    ),
    ComponentAxis(
        key="notification_deadline",
        triggers=("notification", "notify", "deadline", "reminder", "due", "overdue", "email", "alert", "escalation"),
        owned_state="deadline rule, due date, reminder schedule, notification delivery request, delivery status, overdue marker, escalation state, and stale-work signal",
        accepted_inputs="lifecycle event, actor contact reference, deadline policy, due date, reminder preference, delivery provider status, and escalation trigger",
        produced_outputs="notification request, delivered or failed marker, overdue indicator, reminder event, escalation signal, and freshness handoff",
        states_or_transitions="scheduled, pending, sent, failed, acknowledged, overdue, escalated, stale, and resolved",
        outside_boundary="submission intake, work routing, score ownership, final decision state, immutable audit retention, dashboard query ownership, and sibling product responsibilities",
        local_proof=(
            "A lifecycle event creates the right deadline, reminder, delivery status, and overdue marker.",
            "Failed or missing delivery leaves visible stale-work evidence instead of pretending the actor was notified.",
            "Deadline and notification changes do not mutate the underlying submission, review, score, or decision state.",
        ),
        unique_failure="A required actor can miss a deadline silently, a stale item can look current, or a failed notification can be treated as delivered.",
    ),
    ComponentAxis(
        key="search_status_view",
        triggers=(
            "search",
            "filter",
            "filtering",
            "dashboard",
            "dashboards",
            "status",
            "queue",
        ),
        owned_state="search query, filter set, result list, status facet, visible dashboard state, next-action summary, blocked or stale indicator, and role-appropriate read model",
        accepted_inputs="indexed product state, status event, actor role, filter criteria, search query, blocker marker, freshness timestamp, and read-model request",
        produced_outputs="filtered result set, status summary, dashboard view, blocked or stale indicator, role-appropriate next action, and read-model handoff",
        states_or_transitions="empty, filtered, sorted, stale, blocked, needs-action, hidden-by-role, visible, refreshed, and exported",
        outside_boundary="submission mutation, work routing, final decision authority, immutable audit retention, notification delivery, and sibling product responsibilities",
        local_proof=(
            "The dashboard renders filtered results, status facets, blocked or stale indicators, and next actions from current product state.",
            "Role-inappropriate or stale data is hidden or marked instead of appearing as current actionable truth.",
            "Search, filtering, and display changes do not mutate submission, assignment, scoring, decision, or audit ownership.",
        ),
        unique_failure="A stale or unauthorized dashboard view can look current, a blocked item can disappear from the queue, or search output can imply a decision that another component owns.",
    ),
    ComponentAxis(
        key="synthesis_export",
        triggers=("synthesis", "table", "export", "package", "report", "summary", "output", "deliverable"),
        owned_state="synthesis table, export package, included evidence summary, output format, completeness marker, and release handoff evidence",
        accepted_inputs="validated evidence, assessment result, source references, actor identity, output format request, and completeness rule",
        produced_outputs="synthesis table, exportable package, completeness blocker, evidence summary, and release proof handoff",
        states_or_transitions="not-started, draft, incomplete, ready-for-export, exported, blocked, revised, and accepted",
        outside_boundary="source ingestion, criteria definition, work routing, raw extraction ownership, immutable audit storage, and sibling product responsibilities",
        local_proof=(
            "Synthesis output includes only validated upstream evidence.",
            "Incomplete evidence blocks export instead of creating a trusted package.",
            "Export format changes do not mutate upstream decisions or extraction state.",
        ),
        unique_failure="An export can omit required evidence, summarize unvalidated inputs, or make an incomplete synthesis look release-ready.",
    ),
    ComponentAxis(
        key="dashboard_comparison",
        triggers=("dashboard", "comparison", "compare", "summary", "readiness", "display"),
        owned_state="current decision summary, comparison display, review readiness, user-facing decision state, visible blockers, and comparison filters",
        accepted_inputs="review status, score output, assignment status, evidence references, comparison criteria, and user role context",
        produced_outputs="decision summary, comparison view, readiness indicator, visible blocker, and user-facing next action",
        states_or_transitions="ready, blocked, needs-review, comparable, not-comparable, changed, and decided",
        outside_boundary="immutable audit storage, version chain, retention enforcement, score ownership, permission grants, and sibling product responsibilities",
        local_proof=(
            "The dashboard shows the current decision summary, comparison display, readiness state, and blocker.",
            "A blocked or incomplete review cannot appear ready for decision.",
            "Audit retention or immutable history changes do not mutate the comparison view.",
        ),
        unique_failure="A stale summary can look current, an incomplete review can appear ready, or comparison output can hide the blocker behind a decision view.",
    ),
    ComponentAxis(
        key="source_claim_lineage",
        triggers=("claim", "claims", "citation", "citations", "lineage", "traceability", "provenance", "reference", "references"),
        owned_state="claim-source lineage, citation set, source reference history, provenance marker, replayable claim version, and public evidence handoff state",
        accepted_inputs="material claim, cited source, source timestamp, actor identity, version reference, provenance note, and retention rule",
        produced_outputs="source-linked claim record, citation history, provenance marker, replay evidence, missing-source blocker, and audit handoff",
        states_or_transitions="uncited, cited, source-linked, disputed, versioned, replayed, retained, missing-source-blocked, and handed-off",
        outside_boundary="current dashboard ranking, final decision authority, feedback grouping, assignment routing, and sibling product responsibilities",
        local_proof=(
            "Every material claim keeps its source reference, citation history, version marker, and replay evidence.",
            "A claim without source evidence stays blocked instead of appearing trustworthy.",
            "Decision, dashboard, feedback, and assignment changes do not rewrite source lineage or citation history.",
        ),
        unique_failure="A material claim can appear trustworthy without its source, cite the wrong version, lose public replay evidence, or detach from retention history.",
    ),
    ComponentAxis(
        key="audit_retention",
        triggers=("audit", "trail", "version", "history", "retention", "archive", "provenance"),
        owned_state="immutable event history, version chain, retention policy state, audit reconstruction, change provenance, and replay evidence",
        accepted_inputs="state change event, actor identity, timestamp, prior version, retention rule, and provenance reference",
        produced_outputs="audit entry, version snapshot, retention decision, replay record, and immutable history evidence",
        states_or_transitions="recorded, versioned, retained, expired, restored, replayed, and audit-blocked",
        outside_boundary="dashboard ranking, comparison display, current decision summary, protected access decisions, and sibling product responsibilities",
        local_proof=(
            "Every state change creates an immutable audit entry with actor, timestamp, prior version, and provenance.",
            "Retention rules keep or expire history without changing the current decision view.",
            "Audit replay reconstructs the decision history without relying on dashboard text.",
        ),
        unique_failure="A version can disappear, retention can delete required evidence, or audit replay can reconstruct the wrong decision history.",
    ),
    ComponentAxis(
        key="spatial_context",
        triggers=("map", "location", "geospatial", "geometry", "boundary", "overlay", "layer"),
        owned_state="location context, spatial identity, boundary geometry, contextual overlay, map layer selection, source freshness, and context handoff state",
        accepted_inputs="case or item identity, location reference, spatial identifier, boundary geometry, map layer request, source timestamp, and actor context",
        produced_outputs="contextual map view, location summary, overlay result, source-freshness marker, missing-context blocker, and downstream context handoff",
        states_or_transitions="unlocated, located, layer-selected, source-stale, missing-context, context-ready, revised, and handed-off",
        outside_boundary="submission mutation, work routing, final decision authority, immutable audit retention, and sibling product responsibilities",
        local_proof=(
            "The location context shows the right boundary, overlay, source timestamp, and missing-context blocker.",
            "Stale or missing map context cannot appear as current contextual truth.",
            "Decision, audit, and question changes do not mutate the location context source marker.",
        ),
        unique_failure="A user can trust the wrong location, stale overlay, missing boundary, or detached spatial source when making a downstream decision.",
    ),
    ComponentAxis(
        key="question_issue_tracking",
        triggers=("question", "issue", "concern", "follow-up", "followup", "comment", "response", "answer", "unresolved"),
        owned_state="question list, issue category, concern marker, follow-up request, answer status, unresolved blocker, and issue handoff state",
        accepted_inputs="actor question, concern text, source reference, issue category, response note, owner identity, and follow-up command",
        produced_outputs="tracked issue, answer or follow-up request, unresolved blocker, grouped concern signal, response history, and downstream decision handoff",
        states_or_transitions="draft, open, assigned, answered, unresolved, escalated, closed, stale, and handed-off",
        outside_boundary="work routing, permission grants, final decision authority, immutable audit retention, and sibling product responsibilities",
        local_proof=(
            "A submitted question or issue keeps its source, owner, answer status, unresolved blocker, and follow-up history.",
            "Unanswered or stale issues remain visible instead of appearing decision-ready.",
            "Form scoring, assignment, audit, and final decision changes do not rewrite the issue history.",
        ),
        unique_failure="A serious question or public concern can disappear, look answered without source evidence, or lose the owner responsible for follow-up.",
    ),
    ComponentAxis(
        key="feedback_grouping",
        triggers=("feedback", "comment", "comments", "public", "theme", "grouping", "cluster", "sentiment", "concern"),
        owned_state="feedback source, comment grouping, theme label, duplicate marker, concern summary, visibility state, and grouping handoff evidence",
        accepted_inputs="feedback text, commenter or source identity, timestamp, grouping rule, duplicate signal, visibility policy, and actor context",
        produced_outputs="grouped feedback set, theme summary, duplicate or rejected signal, concern count, source reference, and downstream issue handoff",
        states_or_transitions="received, grouped, duplicate-marked, hidden-by-policy, source-linked, disputed, summarized, and handed-off",
        outside_boundary="final decision authority, immutable audit retention, work routing, and sibling product responsibilities",
        local_proof=(
            "Feedback groups keep source references, theme labels, duplicate markers, and visibility state.",
            "Hidden, duplicate, or disputed comments cannot be counted as ordinary unreviewed feedback.",
            "Decision, audit, and question state changes do not mutate the original feedback source.",
        ),
        unique_failure="A feedback theme can misrepresent source comments, duplicate input can inflate concern counts, or hidden comments can leak into a public decision view.",
    ),
    ComponentAxis(
        key="decision_rationale_vote",
        triggers=("vote", "motion", "rationale", "reason", "recommendation", "condition", "abstain", "approve", "deny"),
        owned_state="decision rationale, recommendation comparison, motion or decision command, vote outcome, condition set, abstention marker, and final outcome state",
        accepted_inputs="decision-ready evidence, recommendation, actor identity, rationale note, motion or command, condition request, conflict marker, and prior outcome",
        produced_outputs="recorded decision, rationale statement, approval or denial outcome, condition list, vote or signoff record, and downstream outcome handoff",
        states_or_transitions="draft, ready-for-decision, blocked, approved, denied, conditioned, abstained, finalized, and handed-off",
        outside_boundary="source import, work routing, immutable audit storage, read-model ranking, and sibling product responsibilities",
        local_proof=(
            "The decision record shows the evidence, recommendation comparison, actor, rationale, conditions, and final outcome.",
            "Missing rationale, unresolved blockers, or conflict markers prevent a final outcome from looking ready.",
            "Audit, context, question, and feedback changes do not silently rewrite the recorded decision rationale.",
        ),
        unique_failure="A final decision can look valid while rationale, conditions, conflict handling, or source evidence is missing.",
    ),
)


def component_axis_key_for_label(label_text: str) -> str:
    """Return the strongest generic ownership axis implied by a component label."""

    text = _normalize_axis_text(label_text)
    check_text = re.sub(r"\bcheck\s+in\b", "", text)
    if re.search(r"\b(criteria|criterion|protocol|rule|eligibility policy|inclusion|exclusion)\b", text):
        return "definition_rules"
    if re.search(r"\b(checklists?|checks?)\b", check_text) or (
        re.search(r"\bledger\b", check_text)
        and re.search(r"\b(rule|reference|pass|block|outcome|compliance|check)\b", check_text)
    ):
        return "check_rule_ledger"
    if re.search(r"\brisk\b", text) and re.search(r"\b(review|assessment|workspace|readiness|flags?)\b", text):
        return "risk_review_workspace"
    if re.search(r"\b(onboarding|consent|signup|registration)\b", text):
        return "onboarding_consent"
    if re.search(r"\b(privacy|export|deletion|delete|erase|protected data)\b", text):
        return "privacy_data_lifecycle"
    if re.search(r"\b(risk|disclaimer|compliance|policy|guardrails?|safety)\b", text):
        return "policy_risk_guardrails"
    if re.search(r"\b(submission|submit|file upload|upload)\b", text):
        return "submission_versioning"
    if re.search(r"\b(evidence|checklist|photos?|findings?|diagnostics?|inspection)\b", text) and re.search(
        r"\b(capture|review|trace|source|readiness|complete|completion)\b",
        text,
    ):
        return "evidence_review"
    if re.search(r"\b(medication|medicine|dose|dosage|relief|reminders?|missed reminder|side effect)\b", text) and not re.search(
        r"\b(?:pain|symptom)\s+entry\b|\bentry\s+capture\b",
        text,
    ):
        return "medication_relief_tracking"
    if re.search(r"\b(symptoms?|pain|episode|intensity|body location|relief|medication|dose|side effect|trigger|timeline)\b", text):
        return "symptom_self_tracking"
    if re.search(r"\b(intake|capture|captures|form|answers?|request|entry|input)\b", text) and not re.search(
        r"\b(import|ingestion|ingest|deduplication|dedupe|duplicate|normalize|metadata|measurement|metric|reading|baseline|observation|evidence|checklist|photos?|findings?|scoring|score|rubric|assessment)\b",
        text,
    ):
        return "request_intake_capture"
    if re.search(r"\b(measurement|measurements?|metrics?|readings?|capture|baseline|observation|value)\b", text):
        return "measurement_capture"
    if re.search(r"\b(price|pricing|quote|cost|estimate|rate|amount|charge)\b", text):
        return "quote_calculation"
    if re.search(r"\b(handoff|handoffs|provider|recipient|endpoint|fulfillment|delivery|dispatch)\b", text):
        return "external_handoff"
    if re.search(r"\b(surface|screen|presentation|portal|ui|client)\b", text) and re.search(
        r"\b(comparison|compare|ranking|ranked|select|selected|selection|options?|choices?|alternatives?|rationale|review)\b",
        text,
    ):
        return "review_presentation_surface"
    if re.search(r"\b(dashboard|display|readiness view)\b", text):
        return "dashboard_comparison"
    if re.search(r"\b(comparison|compare|ranking|rank|select|selection|order|ordered|alternatives?|options?|choices?)\b", text):
        return "option_evaluation_ranking"
    if re.search(r"\b(summary|summaries|report|package|findings?|analysis|supporting)\b", text):
        return "recommendation_impact_summary"
    if re.search(r"\b(goals?|plan|planning|guidance|targets?|adjustment|computed)\b", text):
        return "goal_plan_generation"
    if re.search(r"\b(access|permission|role|rbac|grant|visibility|redaction)\b", text) and re.search(
        r"\b(audit|history|version|retention|replay)\b", text
    ):
        return "access_audit"
    if re.search(r"\b(audit|trail|version|history|retention|archive)\b", text) and not re.search(
        r"\b(privacy|export|deletion|delete|erase|protected data)\b", text
    ):
        return "audit_retention"
    if re.search(r"\b(assignment|assign|permission|access|conflict|routing|eligibility)\b", text):
        return "assignment_permission"
    if (
        re.search(r"\b(communication|message|messages|notify|notification)\b", text)
        or (
            re.search(r"\b(response|reply)\b", text)
            and re.search(r"\b(contact|message|communication|notify|notification)\b", text)
        )
    ) and not re.search(
        r"\b(deadline|reminder|due|overdue|escalation)\b",
        text,
    ):
        return "communication_log"
    if re.search(r"\b(notification|notify|deadline|reminder|due|overdue|email|escalation)\b", text):
        return "notification_deadline"
    if re.search(r"\b(analytics|analysis|explanations?|trend|summary)\b", text) and re.search(
        r"\b(progress|status|readiness|state)\b",
        text,
    ):
        return "status_analytics_explanation"
    if re.search(r"\b(habits?|activity|logs?|logging|daily|progress|check[- ]?in)\b", text):
        return "habit_activity_tracking"
    if re.search(r"\b(admin|inspection|disputed|readiness|evidence review|review tools)\b", text) and re.search(
        r"\b(review|evidence|source|signal|quality|disputed|inspection)\b", text
    ):
        return "evidence_review"
    if re.search(r"\b(confidence|signal quality|quality signal)\b", text) or (
        re.search(r"\b(signal|signals|deduplication|dedupe|duplicate)\b", text)
        and not re.search(r"\b(intake|ingestion|ingest|import|source attribution|metadata import)\b", text)
    ):
        return "signal_quality_deduplication"
    if re.search(r"\b(ingestion|ingest|import|deduplication|dedupe|normalize)\b", text):
        return "intake_import"
    if re.search(r"\b(form|scoring|score|template|rubric|assessment)\b", text):
        return "form_scoring"
    if re.search(r"\b(case|workspace|agenda|checklist)\b", text):
        return "case_workspace"
    if re.search(r"\b(map|parcel|location|geospatial|geometry|overlay|layer|zoning)\b", text):
        return "spatial_context"
    if re.search(r"\b(question|issue|concern|follow-up|followup|response|answer|unresolved)\b", text):
        return "question_issue_tracking"
    if re.search(r"\b(feedback|comment|comments|theme|grouping|cluster|sentiment)\b", text):
        return "feedback_grouping"
    if re.search(r"\b(journal|decision note|decision journal|rationale journal)\b", text):
        return "user_decision_journal"
    if re.search(r"\b(decision|approval|approve|final outcome|outcome|blocker)\b", text):
        return "decision_review"
    if re.search(r"\b(follow list|watchlist|watch list|saved list|selected list|bookmark)\b", text):
        return "tracked_selection_list"
    return ""


def component_axis_for_label(label_text: str) -> ComponentAxis | None:
    """Resolve a component label to a reusable semantic ownership axis."""

    key = component_axis_key_for_label(label_text)
    if key:
        for axis in COMPONENT_AXES:
            if axis.key == key:
                return axis
    text = _normalize_axis_text(label_text)
    if not text:
        return None
    best: tuple[int, ComponentAxis] | None = None
    for axis in COMPONENT_AXES:
        score = sum(1 for trigger in axis.triggers if re.search(rf"\b{re.escape(trigger)}\b", text))
        if score and (best is None or score > best[0]):
            best = (score, axis)
    return best[1] if best else None


def _normalize_axis_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").replace("_", " ").replace("-", " ")).strip().casefold()


__all__ = ["COMPONENT_AXES", "ComponentAxis", "component_axis_for_label", "component_axis_key_for_label"]
