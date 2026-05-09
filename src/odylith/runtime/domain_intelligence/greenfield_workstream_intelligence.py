"""Domain-intelligent payloads for greenfield workstreams."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.analysis_engine.types import slugify
from odylith.runtime.domain_intelligence.greenfield_domain_profile import GreenfieldDomainProfile
from odylith.runtime.domain_intelligence.greenfield_domain_profile import infer_greenfield_domain_profile
from odylith.runtime.domain_intelligence.greenfield_text import clean_text
from odylith.runtime.domain_intelligence.greenfield_text import text_values
from odylith.runtime.domain_intelligence.greenfield_workstream_terms import merchant_lending_ontology_rows
from odylith.runtime.domain_intelligence.greenfield_workstream_terms import merchant_lending_operator_rows
from odylith.runtime.domain_intelligence.greenfield_workstream_terms import merchant_lending_validation_rows
from odylith.runtime.domain_intelligence.greenfield_workstream_terms import workstream_family_terms

SECTION_TITLE = "Domain Intelligence"

_REQUIRED_LAYERS = (
    "intent",
    "scope",
    "ontology",
    "state",
    "operators",
    "constraints",
    "source_of_truth_map",
    "evidence_model",
    "decisions",
    "assumptions",
    "topology",
    "invariants",
    "risks",
    "validation_obligations",
    "artifacts",
    "authority",
    "owners",
    "execution_memory",
    "metrics",
    "change_model",
    "invalidation_rules",
    "conflict_model",
    "transfer_priors",
)

_LAYER_LABELS = {
    "intent": "Intent And Outcome",
    "scope": "Scope And Boundary",
    "ontology": "Domain Ontology",
    "state": "State Model",
    "operators": "Allowed Operators",
    "constraints": "Constraints And Boundary Conditions",
    "source_of_truth_map": "Source Of Truth Map",
    "evidence_model": "Evidence Model",
    "decisions": "Decision History",
    "assumptions": "Assumptions And Uncertainty",
    "topology": "Dependency Topology",
    "invariants": "Invariants",
    "risks": "Risk Register",
    "validation_obligations": "Validation Obligations",
    "artifacts": "Work Products And Artifact Contracts",
    "authority": "Stakeholders And Authority",
    "owners": "Ownership Map",
    "execution_memory": "Memory And Prior Executions",
    "metrics": "Metrics And Observables",
    "change_model": "Change Model",
    "invalidation_rules": "Invalidation Rules",
    "conflict_model": "Conflict Model",
    "transfer_priors": "Reuse And Transfer Priors",
}


def enrich_backlog_rows(
    rows: Sequence[Any],
    *,
    intent: Mapping[str, Any],
    program: Mapping[str, Any],
    release_plan: Mapping[str, Any],
    validation_strategy: Sequence[Any],
    security_compliance: Any,
    components: Sequence[Any],
    diagrams: Sequence[Any],
    domain_profile: GreenfieldDomainProfile | None = None,
) -> list[Any]:
    """Attach structured domain intelligence to every mapping backlog row."""

    title = clean_text(intent.get("title")) or "Greenfield Project"
    prompt = clean_text(intent.get("prompt")) or title
    slug = slugify(clean_text(intent.get("project_slug")) or title)
    profile = domain_profile or infer_greenfield_domain_profile(prompt=prompt, title=title, slug=slug)
    enriched: list[Any] = []
    for row in rows:
        if not isinstance(row, Mapping):
            enriched.append(row)
            continue
        next_row = dict(row)
        if not _has_minimum_domain_intelligence(next_row.get("domain_intelligence")):
            next_row["domain_intelligence"] = build_domain_intelligence(
                row=next_row,
                intent=intent,
                program=program,
                release_plan=release_plan,
                validation_strategy=validation_strategy,
                security_compliance=security_compliance,
                components=components,
                diagrams=diagrams,
                domain_profile=profile,
            )
        enriched.append(next_row)
    return enriched


def build_domain_intelligence(
    *,
    row: Mapping[str, Any],
    intent: Mapping[str, Any],
    program: Mapping[str, Any],
    release_plan: Mapping[str, Any],
    validation_strategy: Sequence[Any],
    security_compliance: Any,
    components: Sequence[Any],
    diagrams: Sequence[Any],
    domain_profile: GreenfieldDomainProfile,
) -> dict[str, Any]:
    """Build one workstream's structured project truth without source-backed claims."""

    title = clean_text(intent.get("title")) or "Greenfield Project"
    row_title = clean_text(row.get("title")) or "Greenfield workstream"
    selector = clean_text(release_plan.get("selector")) or "0.0.1"
    kind = _row_kind(row)
    terms = _family_terms(domain_profile=domain_profile, title=title)
    focus = _component_focus(row=row, components=components)
    diagrams_for_row = _diagram_focus(row=row, diagrams=diagrams)
    first_slice = clean_text(row.get("recommended_first_slice")) or "Confirm the smallest source-backed slice."
    wave = _wave_for_row(row=row, program=program)
    component_clause = ", ".join(focus[:3]) if focus else "candidate components"
    diagram_clause = ", ".join(diagrams_for_row[:4]) if diagrams_for_row else "first architecture views"
    profile_focus = domain_profile.components.get(_profile_role(kind), domain_profile.components["domain"])

    return {
        "schema_version": "odylith.greenfield.workstream_intelligence.v1",
        "family": domain_profile.family,
        "workstream_role": kind,
        "summary": (
            f"{row_title} captures the {terms['domain_phrase']} slice as a product-requirements record: "
            f"what exists, what may change, what must remain invariant, what counts as proof, "
            f"and what later agents should reuse before editing source."
        ),
        "intent": [
            f"Project objective: {terms['project_objective']}",
            f"Workstream objective: {profile_focus.responsibility}",
            f"Stakeholder outcome: {terms['stakeholder_outcome']}",
            f"Success condition: {first_slice}",
            f"Why now: greenfield intent needs {component_clause} and {diagram_clause} before source-backed claims.",
            f"Failure mode: {terms['failure_mode']}",
            f"Non-goals: {terms['non_goals']}",
        ],
        "scope": [
            (
                f"In scope: `{row_title}` owns {_owned_responsibility_clause(profile_focus.responsibility)} "
                f"and the first proof slice: {first_slice}"
            ),
            f"Out of scope: {terms['non_goals']}",
            f"Boundary: keep `{row_title}` tied to {component_clause}, {diagram_clause}, {wave}, and release `{selector}` until an explicit scope split changes that topology.",
            "Customization boundary: runtime, compliance, first actor, data source, and proof threshold may change only through proposal, plan, or human-decision updates, not implicit coding.",
        ],
        "ontology": _ontology(domain_profile=domain_profile, kind=kind, components=focus, title=title),
        "state": [
            f"Current state: user_intent evidence only; no source-backed runtime behavior is claimed for `{row_title}`.",
            f"Desired state: {wave} has a plan, code slice, repository-native proof, and refreshed release evidence.",
            f"Intermediate states: proposed -> queued -> planning -> implementation -> source_backed -> release-gated.",
            f"Blocked states: missing component owner, missing validation fixture, unresolved security/compliance assumption, or stale workstream/architecture links.",
            f"Invalid states: active source claim without tests; release `{selector}` advanced while first-wave proof is missing.",
            "Freshness owner: workstream records own product intent; component specs own component identity; architecture diagrams own topology; release notes own promotion posture.",
        ],
        "operators": _operators(domain_profile=domain_profile, kind=kind, selector=selector),
        "constraints": [
            *terms["constraints"],
            f"Keep source edits inside the named component boundary until the technical plan proves a narrower split: {component_clause}.",
            "Do not mark planned component specs active until source paths, tests, and proof artifacts exist.",
            "Do not change release scope without updating dependencies, wave state, and architecture topology.",
        ],
        "source_of_truth_map": [
            "Workstream source file: canonical intent, scope, non-goals, dependencies, risks, and validation obligations.",
            "Component specs: canonical component identity, component-scoped ownership boundary, collaborators, interfaces, failure modes, and proof expectations.",
            "Architecture diagram source and Mermaid files: canonical topology and cross-workstream traceability.",
            "Release and progress records: derived posture; refresh them after source, proof, or plan changes.",
            "Repo-native tests and fixtures: highest-strength implementation evidence once source exists.",
            "Generated views: readable projections, not the source of truth when they conflict with source files.",
        ],
        "evidence_model": [
            *terms["evidence_counts"],
            "Counts as evidence: passing repo-native tests, rendered architecture diagrams, component/workstream validation, release evidence refresh, and explicit human decisions.",
            "Does not count as evidence: proposal prose alone, dashboard freshness without source change, unlabeled assumptions, or host-agent summaries.",
            "Evidence strength order: source-backed tests > validated project source > explicit human confirmation > user_intent proposal > labeled assumption.",
        ],
        "decisions": [
            f"Decision: start `{selector}` with {wave} instead of broad project scaffolding.",
            f"Decision pressure: preserve correctness and operator trust before latency or breadth; {terms['decision_pressure']}",
            "Rejected path: title-only workstream items or component labels that force the next agent to rediscover domain vocabulary.",
            "Reversal criteria: operator changes runtime, compliance posture, first user role, or release target before implementation starts.",
        ],
        "assumptions": [
            *terms["assumptions"],
            f"Assumption: `{row_title}` stays candidate/user_intent until a technical plan and source proof land.",
            f"Validation path: answer open questions, bind a plan, implement the first slice, run {terms['primary_validation_command']}, then refresh release evidence.",
            "Expiration condition: source-backed implementation, changed compliance target, or changed first-wave release scope.",
        ],
        "topology": [
            f"`{row_title}` depends on {component_clause}; it must stay linked to {diagram_clause}.",
            f"{terms['topology_spine']}",
            "Workstream -> technical plan -> code paths -> tests -> component specs -> architecture diagrams -> release evidence is the required proof path.",
            "An evidence harness blocks release promotion if normal, empty, degraded, and failure fixtures are missing.",
        ],
        "invariants": [
            *terms["invariants"],
            "Every source-backed claim must name a file path, workstream, component owner, and runnable proof.",
            "Generated artifacts must be reproducible from source records and must not become hand-edited truth.",
            "Every first-release workstream must map to a component boundary, architecture view, and release validation gate.",
        ],
        "risks": [
            *terms["risks"],
            f"Topology risk: {row_title} can become disconnected if dependencies, interface expectations, or diagrams are not updated together.",
            f"Release risk: `{selector}` can look ready while the first slice lacks source-backed behavior proof.",
            _security_posture_text(security_compliance),
        ],
        "validation_obligations": [
            *_row_validation_obligations(domain_profile=domain_profile, kind=kind),
            *terms["validation_obligations"],
            f"Claim: `{row_title}` is ready for implementation. Method: technical plan names source paths, fixtures, owners, and rollback path.",
            "Claim: candidate components are coherent. Method: component validation and specs list dependencies, interfaces, first slice, and verification commands.",
            "Claim: topology is understandable. Method: architecture render passes and diagrams link back to the created workstreams.",
            "Failure condition: any proof relies on live production systems, unstated credentials, or unverifiable host-agent inference.",
        ],
        "artifacts": [
            f"Workstream `{row_title}`: product-requirements record; update when scope, assumptions, or proof obligations change.",
            f"Component specs for {component_clause}: planned ownership contracts until source-backed proof lands.",
            f"Architecture diagrams {diagram_clause}: topology and sequence/state/release views for the first slice.",
            f"Release target `{selector}`: first-wave promotion gate with explicit validation evidence.",
        ],
        "authority": [
            "Operator owns product intent, compliance posture, runtime target, and release-scope approval.",
            "Technical-plan author owns source path selection, implementation sequence, test commands, and rollback path.",
            "Validation owns pre-write topology checks and fail-closed proposal rejection.",
            "No agent may infer source-backed readiness from proposal text or generated views alone.",
        ],
        "owners": [
            f"Workstream owner: `{row_title}` owns intent, scope, dependencies, risks, assumptions, validation obligations, and execution memory.",
            f"Component owner: {component_clause} own component identity, boundaries, interfaces, collaborators, and component-specific proof.",
            f"Architecture owner: {diagram_clause} own topology claims and must be refreshed when source paths, owners, states, or release gates change.",
            "Operator owner: human direction owns primary user, runtime, compliance posture, release ambition, and any reversal of default assumptions.",
            "Implementation owner: the future technical plan owns source paths, rollback or recovery posture, repo-native tests, and proof attachment.",
        ],
        "execution_memory": [
            "Prior regression to avoid: a host agent repaired shallow greenfield JSON by hand, then authored generic workstreams and templated specs.",
            "Reusable lesson: apply-ready proposal objects must already carry dependencies, interfaces, proof gates, domain vocabulary, and source-of-truth hierarchy.",
            f"Next-session starting point: read this Domain Intelligence section before planning `{row_title}`.",
        ],
        "metrics": [
            *terms["metrics"],
            "Epistemic metric: number of claims backed by tests or validated source versus assumptions.",
            "Governance metric: orphaned component, diagram, release, or workstream links must stay at zero.",
            "Agent behavior metric: no visible canonical-object patching loop, no title-only plan, no repeated generic component-spec structure.",
        ],
        "change_model": [
            "If the runtime target changes, invalidate transport/interface assumptions and rerun component plus architecture review.",
            "If a schema, fixture, or test is removed, downgrade evidence that depended on it until replacement proof exists.",
            "If release scope changes, recompute workstream dependencies, release assignment, and wave posture.",
            "If a component owner changes, refresh component specs, impacted workstreams, and architecture ownership views together.",
        ],
        "invalidation_rules": [
            *terms["invalidation_rules"],
            f"If `{row_title}` changes first slice, owner, runtime, data boundary, or release `{selector}` assignment, expire dependent assumptions, diagrams, component interfaces, and proof gates before implementation continues.",
            "If a named test, fixture, browser proof, schema, or render disappears, downgrade every claim that depended on it from source_backed to assumption or blocked until replacement proof lands.",
            "If the operator contradicts a default assumption, the operator decision wins and this workstream must be rewritten before code uses the old assumption.",
            "If generated views disagree with workstreams, component specs, architecture diagrams, or repo-native tests, treat the projection as stale and repair source truth plus refresh before promotion.",
        ],
        "conflict_model": [
            "Conflict priority: source-backed tests beat generated views; component specs beat inferred ownership; workstream records beat chat summaries for intent.",
            "If docs, diagrams, and component specs disagree, stop promotion and open a plan or Casebook repair before coding forward.",
            "If operator answers contradict assumptions, update this workstream before source changes that depend on the old assumption.",
        ],
        "transfer_priors": [
            *terms["transfer_priors"],
            "Reusable operator: split an overloaded workstream when one slice needs different owners, evidence, or release gates.",
            "Reusable validation pattern: normal/empty/degraded/failure matrix plus topology refresh before release promotion.",
        ],
    }


def render_domain_intelligence_section(value: Any) -> str:
    """Render a domain-intelligence mapping as workstream markdown."""

    if not isinstance(value, Mapping):
        return ""
    lines: list[str] = []
    summary = clean_text(value.get("summary"))
    if summary:
        lines.append(summary)
    for key in _REQUIRED_LAYERS:
        nested = value.get(key)
        rendered = _render_layer(nested)
        if not rendered:
            continue
        if lines:
            lines.append("")
        lines.append(f"### {_LAYER_LABELS[key]}")
        lines.extend(rendered)
    return "\n".join(lines).strip()


def domain_intelligence_issues(value: Any, *, owner: str) -> list[str]:
    """Return actionable validation issues for one domain-intelligence payload."""

    if not isinstance(value, Mapping):
        return [f"{owner} must include domain_intelligence object"]
    issues: list[str] = []
    for key in _REQUIRED_LAYERS:
        nested = value.get(key)
        if not _layer_has_depth(nested):
            issues.append(f"{owner} domain_intelligence.{key} is missing or too shallow")
    if len(_list_values(value.get("ontology"))) < 4:
        issues.append(f"{owner} domain_intelligence.ontology must define at least four domain terms")
    if len(_list_values(value.get("operators"))) < 3:
        issues.append(f"{owner} domain_intelligence.operators must define at least three state-changing operations")
    if len(_list_values(value.get("validation_obligations"))) < 3:
        issues.append(f"{owner} domain_intelligence.validation_obligations must define at least three proof gates")
    duplicate_terms = _duplicate_ontology_terms(value.get("ontology"))
    if duplicate_terms:
        issues.append(
            f"{owner} domain_intelligence.ontology repeats operational term(s): {', '.join(duplicate_terms)}"
        )
    if _contains_malformed_ownership_phrase(value):
        issues.append(f"{owner} domain_intelligence contains malformed ownership phrase")
    return issues


def _has_minimum_domain_intelligence(value: Any) -> bool:
    return isinstance(value, Mapping) and not domain_intelligence_issues(value, owner="backlog row")


def _row_kind(row: Mapping[str, Any]) -> str:
    title = clean_text(row.get("title")).casefold()
    workstream_type = clean_text(row.get("workstream_type")).casefold()
    if workstream_type == "umbrella" or title.startswith("govern "):
        return "program"
    if "workflow" in title or "operator" in title or "console" in title or "experience" in title:
        return "experience"
    if "domain" in title or "contract" in title or "engine" in title or "core" in title:
        return "domain"
    if "proof" in title or "validation" in title or "harness" in title or "operations" in title:
        return "validation"
    return "child"


def _profile_role(kind: str) -> str:
    if kind == "experience":
        return "experience"
    if kind == "validation":
        return "validation"
    return "domain"


def _component_focus(row: Mapping[str, Any], components: Sequence[Any]) -> list[str]:
    explicit = [clean_text(item) for item in text_values(row.get("component_focus"), split_scalar=True, split_commas=True)]
    if explicit:
        return [item for item in explicit if item]
    values = []
    for component in components:
        if not isinstance(component, Mapping):
            continue
        component_id = clean_text(component.get("component_id")) or clean_text(component.get("label"))
        if component_id:
            values.append(component_id)
    return values[:3]


def _diagram_focus(row: Mapping[str, Any], diagrams: Sequence[Any]) -> list[str]:
    explicit = [
        clean_text(item)
        for item in text_values(row.get("related_diagram_slugs"), split_scalar=True, split_commas=True)
    ]
    if explicit:
        return [item for item in explicit if item]
    values = []
    for diagram in diagrams:
        if not isinstance(diagram, Mapping):
            continue
        slug = clean_text(diagram.get("slug"))
        if slug:
            values.append(slug)
    return values[:5]


def _wave_for_row(*, row: Mapping[str, Any], program: Mapping[str, Any]) -> str:
    title = clean_text(row.get("title"))
    title_slug = slugify(title)
    for wave in program.get("waves", []) if isinstance(program.get("waves"), list) else []:
        if not isinstance(wave, Mapping):
            continue
        refs = text_values(
            [
                wave.get("workstreams"),
                wave.get("workstream_titles"),
                wave.get("target_workstreams"),
                wave.get("component_focus"),
            ],
            split_scalar=True,
            split_commas=True,
        )
        if title_slug and title_slug in {slugify(item) for item in refs}:
            return clean_text(wave.get("label")) or clean_text(wave.get("wave_id")) or "first wave"
    first = next((wave for wave in program.get("waves", []) if isinstance(wave, Mapping)), {})
    return clean_text(first.get("label")) or clean_text(first.get("wave_id")) or "first wave"


def _family_terms(*, domain_profile: GreenfieldDomainProfile, title: str) -> dict[str, Any]:
    return workstream_family_terms(domain_profile=domain_profile, title=title)


def _ontology(
    *,
    domain_profile: GreenfieldDomainProfile,
    kind: str,
    components: Sequence[str],
    title: str,
) -> list[str]:
    if domain_profile.family == "defi_risk":
        rows_by_kind = {
            "program": [
                "Program parent: release, wave, risk ontology, and proof topology for the DeFi sentinel.",
                "Risk subject class: wallet, protocol, pool, strategy, or position set; never a custody account.",
                "Governed claim: any risk statement must carry freshness, confidence, and fixture provenance.",
                "Release gate: no live-chain, custody, or advice claim enters 0.0.1 without explicit operator approval.",
            ],
            "experience": [
                "Analyst: human operator triaging exposure, stale data, unsupported chain, and alert acknowledgement.",
                "Watchlist item: wallet, protocol, pool, or strategy tracked by the console with visible data state.",
                "Risk card: severity, trigger reason, exposure, confidence, freshness, and acknowledgement state.",
                "Degraded state: stale oracle, missing indexer, unsupported chain, or missing liquidity shown without false precision.",
            ],
            "domain": [
                "Risk subject: normalized wallet, protocol, pool, strategy, or position set consumed by risk math.",
                "Exposure snapshot: holdings, debt, collateral, chain, protocol, timestamp, and confidence.",
                "Price or oracle point: value plus freshness metadata; stale or missing data escalates data_state.",
                "Liquidity depth: stress input for exit or liquidation context; not an executable trade quote.",
                "Alert transition: clear -> warning -> critical -> acknowledged, driven by deterministic thresholds.",
            ],
            "validation": [
                "Scenario fixture: pinned local input for price shock, liquidity drain, stale oracle, or missing indexer proof.",
                "Replay report: deterministic evidence tying fixture inputs to alert state, severity, and confidence.",
                "Fault case: stale oracle, missing indexer, unsupported chain, or credential/live-network attempt.",
                "Proof artifact: repo-native test or smoke output plus refreshed release evidence.",
            ],
        }
        rows = rows_by_kind.get(kind, rows_by_kind["domain"])
        if kind == "program":
            rows = [
                *rows,
                "Execution wave: delivery checkpoint with named DeFi child workstreams and release proof.",
                "Evidence tier: user_intent, odylith_assumption, and later source_backed claims kept visibly separate.",
            ]
        else:
            rows = [
                *rows,
                "Risk subject: wallet, protocol, pool, strategy, or position set being monitored; never a custody account.",
                "Exposure snapshot: normalized holdings, debts, collateral, chain, protocol, timestamp, and confidence.",
                "Alert: severity, trigger reason, threshold, confidence, state, and acknowledgement trail.",
                "Scenario fixture: local replay input for price shock, liquidity drain, stale oracle, or missing indexer proof.",
            ]
    elif domain_profile.family == "defi_merchant_lending":
        rows = merchant_lending_ontology_rows(kind)
    elif domain_profile.family == "commerce":
        rows_by_kind = {
            "program": [
                "Program parent: checkout spine, catalog inputs, order state, payment recovery, and release gate.",
                "Purchase path: browse -> cart -> checkout -> order draft -> payment result -> recovery or completion.",
                "Release gate: no production payment, fulfillment, or inventory reservation claim before sandbox proof.",
            ],
            "experience": [
                "Shopper: browser actor moving through browse, cart, checkout, payment handoff, and recovery states.",
                "Visible checkout state: empty cart, ready, processing, failed payment, retryable, and complete.",
                "Recovery state: failed-payment or retry path that must not double-submit an order.",
            ],
            "domain": [
                "Cart: mutable shopper intent before checkout; not an order and not a payment record.",
                "Price snapshot: immutable checkout input consumed by order creation; not live merchandising state.",
                "Order draft: idempotent server-side record created before payment completion.",
                "Payment callback: provider sandbox event that may arrive once, late, or repeatedly.",
            ],
            "validation": [
                "Sandbox payment fixture: local success, failure, late callback, and replayed callback input.",
                "Browser proof: shopper-visible happy path, empty cart, failed payment, and retry state.",
                "Replay report: one order draft under repeated checkout and provider callback replay.",
            ],
        }
        rows = rows_by_kind.get(kind, rows_by_kind["domain"])
        if kind == "program":
            rows = [
                *rows,
                "Execution wave: checkout delivery checkpoint with named storefront, order, and proof workstreams.",
                "Proof obligation: sandbox, browser, idempotency, and recovery evidence required before release movement.",
            ]
        else:
            rows = [
                *rows,
                "Shopper: browser actor moving through browse, cart, checkout, payment handoff, and recovery states.",
                "Payment callback: provider sandbox event that may arrive once, late, or repeatedly.",
            ]
    else:
        compact = title.replace(" App", "").replace(" Platform", "").strip() or "product"
        rows_by_kind = {
            "program": [
                f"Program parent: {compact} waves, release target, component owners, and proof topology.",
                "Release gate: validation threshold that must pass before the first release advances.",
                "Execution wave: ordered delivery checkpoint with named child workstreams, owners, and proof obligations.",
                "Component owner: planned boundary accountable for interfaces, dependencies, validation, and later source evidence.",
                "Proof obligation: test, fixture, render, review, or human decision required before a claim can advance.",
            ],
            "experience": [
                f"Operator: first human or system actor using the {compact} workflow.",
                "Read model: user-visible projection of domain state and degraded or empty conditions.",
                "Visible state: normal, empty, degraded, and failure states derived from the domain contract.",
            ],
            "domain": [
                f"Domain object: first {compact.lower()} object whose state is controlled by the product model.",
                "Command: state-changing intent accepted only after validation and ownership checks.",
                "Invariant: domain state transition rule that remains true across transports and storage choices.",
            ],
            "validation": [
                "Proof fixture: deterministic input that lets tests exercise normal, empty, degraded, and failure states.",
                "Proof report: repo-native test, smoke, or browser artifact consumed by release review.",
                "Stale generated view: generated dashboard or diagram that no longer matches source truth.",
            ],
        }
        rows = rows_by_kind.get(kind, rows_by_kind["domain"])
    if kind == "program":
        rows.append("Program parent: umbrella workstream that owns waves, release target, topology, and cross-slice proof sequencing.")
    if components:
        rows.append("Component focus: " + ", ".join(f"`{component}`" for component in components[:4]) + ".")
    return _dedupe_ontology_rows(rows)


def _owned_responsibility_clause(value: str) -> str:
    text = clean_text(value)
    for prefix in ("Owns ", "Own "):
        if text.startswith(prefix):
            text = text[len(prefix) :]
            break
    if not text:
        return "the component-specific boundary"
    return text[:1].casefold() + text[1:]


def _dedupe_ontology_rows(rows: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for row in rows:
        text = clean_text(row)
        if not text:
            continue
        key = _ontology_term_key(text)
        if key in seen:
            continue
        seen.add(key)
        result.append(text)
    return result


def _duplicate_ontology_terms(value: Any) -> list[str]:
    seen: dict[str, str] = {}
    duplicates: list[str] = []
    for row in _list_values(value):
        label = clean_text(row.split(":", 1)[0] if ":" in row else row)
        key = _ontology_term_key(row)
        if not key:
            continue
        if key in seen and seen[key] not in duplicates:
            duplicates.append(seen[key])
        else:
            seen[key] = label
    return duplicates


def _ontology_term_key(value: str) -> str:
    text = clean_text(value)
    label = text.split(":", 1)[0] if ":" in text else text
    return label.casefold()


def _contains_malformed_ownership_phrase(value: Any) -> bool:
    for token in text_values(value):
        lowered = token.casefold()
        if " owns own " in f" {lowered} " or " owns owns " in f" {lowered} ":
            return True
    return False


def _operators(*, domain_profile: GreenfieldDomainProfile, kind: str, selector: str) -> list[str]:
    common = [
        "Bind technical plan: precondition is confirmed scope and component focus; postcondition is a plan with source paths, rollback path, and proof commands.",
        "Attach evidence: precondition is a real test, fixture, render, or human decision; postcondition is updated project traceability.",
        f"Promote release `{selector}`: precondition is source-backed first-wave proof; postcondition is release gate evidence with no unresolved blockers.",
    ]
    if domain_profile.family == "defi_risk":
        rows_by_kind = {
            "program": [
                "Set first-wave risk lane: precondition is operator-confirmed subject class and compliance posture; postcondition is release-gated workstream topology.",
                "Approve boundary change: precondition is explicit non-custody and no-advice review; postcondition is updated workstream, component, and architecture truth.",
                "Escalate compliance uncertainty: precondition is unclear regulated claim; postcondition is blocked release gate or explicit operator decision.",
            ],
            "experience": [
                "Create monitored subject: allowed for wallet, protocol, pool, or strategy fixtures; disallowed for custody accounts or private keys.",
                "Triage risk card: precondition is risk snapshot with data_state; postcondition is visible severity, trigger reason, freshness, and confidence.",
                "Acknowledge alert: precondition is analyst identity and current alert state; postcondition is idempotent acknowledgement with audit evidence.",
            ],
            "domain": [
                "Normalize exposure: precondition is fixture-backed holdings, debt, collateral, chain, and protocol inputs; postcondition is one canonical exposure snapshot.",
                "Evaluate alert threshold: precondition is exposure, price, liquidity, oracle freshness, and protocol-health data; postcondition is severity and confidence.",
                "Reject unsafe precision: precondition is stale oracle, missing indexer, or missing liquidity; postcondition is degraded data_state without numeric overclaim.",
            ],
            "validation": [
                "Replay risk scenario: precondition is pinned local fixture; postcondition is deterministic report over price shock, liquidity drain, stale oracle, or missing indexer.",
                "Assert no live network: precondition is first-release proof run; postcondition is failure on RPC, credentials, private key, or unpinned provider access.",
                "Publish release proof: precondition is replay plus UI/contract proof; postcondition is refreshed release evidence.",
            ],
        }
        rows = rows_by_kind.get(kind, rows_by_kind["domain"])
    elif domain_profile.family == "defi_merchant_lending":
        rows = merchant_lending_operator_rows(kind)
    elif domain_profile.family == "commerce":
        rows_by_kind = {
            "program": [
                "Set checkout spine: precondition is confirmed first purchase path; postcondition is release-gated storefront, checkout, and proof topology.",
                "Defer production payment: precondition is absent provider approval or credentials; postcondition is sandbox-only release scope.",
                "Split fulfillment: precondition is fulfillment risk exceeding checkout proof; postcondition is later-wave workstream.",
            ],
            "experience": [
                "Add cart item: precondition is product and price snapshot availability; postcondition is cart state without order creation.",
                "Start checkout handoff: precondition is non-empty cart; postcondition is visible processing, failed, retryable, or complete state.",
                "Show recovery: precondition is failed payment; postcondition is explicit retry state without duplicate order.",
            ],
            "domain": [
                "Create checkout: precondition is valid cart and immutable price snapshot; postcondition is one idempotent order draft.",
                "Apply payment callback: precondition is sandbox provider event; postcondition is completed, failed, or retryable state without duplicate order.",
                "Reject replay drift: precondition is duplicate callback; postcondition is unchanged order draft and recorded idempotency proof.",
            ],
            "validation": [
                "Replay payment failure: precondition is local sandbox fixture; postcondition is shopper-visible recovery proof.",
                "Replay callback duplicate: precondition is repeated sandbox event; postcondition is one order draft.",
                "Run browser matrix: precondition is UI route; postcondition is happy, empty, failure, and retry proof.",
            ],
        }
        rows = rows_by_kind.get(kind, rows_by_kind["domain"])
    else:
        rows_by_kind = {
            "program": [
                "Set first wave: precondition is confirmed objective, non-goals, and component focus; postcondition is release-gated topology.",
                "Split child boundary: precondition is distinct owner, evidence, or release gate; postcondition is updated wave graph.",
                "Reject broad scaffold: precondition is missing proof path or source owner; postcondition is blocked promotion.",
            ],
            "experience": [
                "Start first workflow: precondition is named operator role and input fixture; postcondition is visible normal, empty, degraded, or failure state.",
                "Render fallback state: precondition is empty, degraded, or invalid domain result; postcondition is visible recovery guidance.",
                "Capture interaction proof: precondition is route or command interface; postcondition is behavior evidence tied to the workstream record.",
            ],
            "domain": [
                "Execute domain command: precondition is validated input and current state; postcondition is accepted, rejected, completed, or retryable domain result.",
                "Enforce invariant: precondition is transition attempt; postcondition is valid state or explicit rejection.",
                "Publish contract: precondition is interface and schema choice; postcondition is tests consuming the same contract.",
            ],
            "validation": [
                "Run proof harness: precondition is deterministic fixture set; postcondition is repository-native evidence and stale-view detection.",
                "Refresh release evidence: precondition is changed source or proof truth; postcondition is synchronized project truth and release posture.",
                "Block release promotion: precondition is missing proof or stale topology; postcondition is failed validation gate.",
            ],
        }
        rows = rows_by_kind.get(kind, rows_by_kind["domain"])
    if kind == "program":
        rows.append("Split or sequence child workstream: precondition is distinct owner, evidence, or release gate; postcondition is updated wave topology.")
    return [*rows, *common]


def _row_validation_obligations(*, domain_profile: GreenfieldDomainProfile, kind: str) -> list[str]:
    if domain_profile.family == "defi_risk":
        rows_by_kind = {
            "program": [
                "Claim: DeFi first wave is coherent. Method: release target contains console, risk engine, scenario harness, and no live-chain scope.",
                "Claim: regulated posture is explicit. Method: non-custody, no-advice, no-private-key, and no-live-RPC constraints appear in workstream and component records.",
            ],
            "experience": [
                "Claim: analyst workflow is intelligible. Method: UI or command proof covers watchlist empty, normal risk card, stale oracle, and unsupported-chain states.",
                "Claim: acknowledgement is auditable. Method: repeated acknowledgement preserves one state change with analyst, subject, severity, and timestamp.",
            ],
            "domain": [
                "Claim: exposure normalization is deterministic. Method: same fixture produces same exposure snapshot, severity, trigger reason, and confidence.",
                "Claim: unsafe precision is blocked. Method: stale oracle, missing indexer, and missing liquidity fixtures degrade the readout.",
            ],
            "validation": [
                "Claim: replay harness is closed-world. Method: proof fails on live RPC, credentials, private keys, or unpinned provider access.",
                "Claim: scenario coverage is release-worthy. Method: price shock, liquidity drain, stale oracle, missing indexer, and acknowledgement replay all pass.",
            ],
        }
        return rows_by_kind.get(kind, rows_by_kind["domain"])
    if domain_profile.family == "defi_merchant_lending":
        return merchant_lending_validation_rows(kind)
    if domain_profile.family == "commerce":
        rows_by_kind = {
            "program": [
                "Claim: checkout-first release scope is coherent. Method: release target links storefront, checkout core, sandbox proof, and no production payment scope.",
            ],
            "experience": [
                "Claim: shopper recovery is visible. Method: browser proof covers happy path, empty cart, failed payment, and retry state.",
            ],
            "domain": [
                "Claim: order draft is idempotent. Method: repeated checkout and callback replay produce one order draft.",
            ],
            "validation": [
                "Claim: payment sandbox is deterministic. Method: success, failure, late callback, and duplicate callback fixtures all pass.",
            ],
        }
        return rows_by_kind.get(kind, rows_by_kind["domain"])
    rows_by_kind = {
        "program": [
            "Claim: first wave is coherent. Method: release target links child workstreams, component owners, diagrams, and proof gates.",
        ],
        "experience": [
            "Claim: first user workflow is visible. Method: behavior proof covers normal, empty, degraded, and failure states.",
        ],
        "domain": [
            "Claim: domain contract is executable. Method: tests cover valid transition, invalid input, and retry or idempotency semantics.",
        ],
        "validation": [
            "Claim: proof harness is trustworthy. Method: fixtures fail closed on missing inputs, skipped assertions, and stale generated views.",
        ],
    }
    return rows_by_kind.get(kind, rows_by_kind["domain"])


def _security_posture_text(value: Any) -> str:
    text = " ".join(text_values(value)).strip()
    return (
        "Security/compliance risk: " + text
        if text
        else "Security/compliance risk: unspecified posture must stay open until the operator confirms data, auth, privacy, and review boundaries."
    )


def _render_layer(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, Mapping):
        rows = []
        for key, nested in value.items():
            rendered = "; ".join(text_values(nested))
            if rendered:
                rows.append(f"- {clean_text(key)}: {rendered}")
        return rows
    values = _list_values(value)
    return [f"- {item}" for item in values if item]


def _list_values(value: Any) -> list[str]:
    return [item for item in text_values(value) if clean_text(item)]


def _layer_has_depth(value: Any) -> bool:
    text = " ".join(text_values(value)).strip()
    return len(text.split()) >= 8


__all__ = [
    "SECTION_TITLE",
    "domain_intelligence_issues",
    "enrich_backlog_rows",
    "render_domain_intelligence_section",
]
