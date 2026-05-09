"""Repairs for legacy greenfield records whose product model was misclassified."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
import shutil
from typing import Any, Mapping

from odylith.install.fs import atomic_write_text
from odylith.runtime.common.consumer_profile import truth_root_path
from odylith.runtime.governance import backlog_authoring


@dataclass(frozen=True)
class LegacyGreenfieldRepairResult:
    changed: bool
    repaired_specs: tuple[str, ...] = ()


_CHECKOUT_LEAK_RE = re.compile(
    r"\b(shopper|checkout|cart|order draft|payment callback|payment sandbox|storefront|checkout-order-core|checkout proof harness)\b",
    re.IGNORECASE,
)
_CONTROL_PLANE_LEAK_RE = re.compile(
    r"\bOdylith surfaces\b|Radar/Registry/Atlas/Compass|Compass Radar Registry Atlas",
    re.IGNORECASE,
)
_MERCHANT_LENDING_RE = re.compile(
    r"(?=.*\b(smb|merchant|shopify|seller|business)\b)"
    r"(?=.*\b(lending|loan|credit|borrower|underwriting|repayment|capital)\b)"
    r"(?=.*\b(defi|stable\s*coins?|stablecoin|usdc|liquidity|protocol|vault|pool)\b)",
    re.IGNORECASE | re.DOTALL,
)


def repair_legacy_merchant_lending_checkout_workstreams(*, repo_root: str | Path) -> LegacyGreenfieldRepairResult:
    """Rewrite already-applied merchant-lending workstreams that leaked checkout semantics.

    v0.1.15 fixed fresh scaffolding, but repos that had already applied the bad
    scaffold could still carry checkout/cart/shopper workstreams for merchant
    lending. This repair is intentionally narrow: it only fires when the same
    record contains merchant-lending intent and retail-checkout leakage.
    """

    root = Path(repo_root).expanduser().resolve()
    idea_root = truth_root_path(repo_root=root, key="radar_source") / "ideas"
    if not idea_root.is_dir():
        return LegacyGreenfieldRepairResult(changed=False)

    candidates = _legacy_candidates(idea_root)
    poisoned_surfaces = _poisoned_project_surface_paths(root)
    if not candidates and not poisoned_surfaces:
        return LegacyGreenfieldRepairResult(changed=False)

    proposal = _merchant_lending_proposal(repo_root=root, candidates=candidates, poisoned_surfaces=poisoned_surfaces)
    rows = _proposal_rows_by_kind(proposal)
    components = _proposal_components(proposal)
    diagrams = _proposal_diagrams(proposal)
    idea_ids = _candidate_ids_by_kind(candidates)
    repaired: list[str] = []
    index_titles: dict[str, str] = {}

    for path, kind in candidates:
        row = rows.get(kind)
        if not row:
            continue
        metadata, sections = backlog_authoring._parse_metadata_and_sections(path)  # noqa: SLF001
        idea_id = str(metadata.get("idea_id", "")).strip().upper()
        metadata["title"] = str(row.get("title", "")).strip()
        metadata["impacted_parts"] = "merchant-capital,credit-liquidity,shopify-data,stablecoin-liquidity,compliance,proof"
        _patch_merchant_lending_sections(sections=sections, row=row, components=components, proposal=proposal)
        rendered = backlog_authoring._render_idea_text(metadata=metadata, sections=sections)  # noqa: SLF001
        current = path.read_text(encoding="utf-8")
        if rendered != current:
            atomic_write_text(path, rendered, encoding="utf-8")
            repaired.append(str(path))
            if idea_id:
                index_titles[idea_id] = metadata["title"]

    if index_titles:
        _repair_index_titles(repo_root=root, titles_by_id=index_titles)

    repaired.extend(_repair_merchant_lending_registry(repo_root=root, proposal=proposal, rows=rows, components=components))
    repaired.extend(_repair_merchant_lending_atlas(repo_root=root, proposal=proposal, diagrams=diagrams))
    repaired.extend(_repair_merchant_lending_programs(repo_root=root, proposal=proposal, idea_ids=idea_ids))

    return LegacyGreenfieldRepairResult(
        changed=bool(repaired),
        repaired_specs=tuple(_repo_relative(repo_root=root, path=Path(item)) for item in repaired),
    )


def _legacy_candidates(idea_root: Path) -> list[tuple[Path, str]]:
    candidates: list[tuple[Path, str]] = []
    for path in sorted(idea_root.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        if not _is_poisoned_merchant_lending_record(text):
            continue
        metadata, _sections = backlog_authoring._parse_metadata_and_sections(path)  # noqa: SLF001
        kind = _legacy_kind(metadata.get("title", ""), text)
        if kind:
            candidates.append((path, kind))
    return candidates


def _is_poisoned_merchant_lending_record(text: str) -> bool:
    return bool(_MERCHANT_LENDING_RE.search(text) and (_CHECKOUT_LEAK_RE.search(text) or _CONTROL_PLANE_LEAK_RE.search(text)))


def _poisoned_project_surface_paths(root: Path) -> list[Path]:
    manifest_path = _component_registry_manifest_path(root)
    specs_root = manifest_path.parent / "components"
    paths: list[Path] = []
    for candidate in [
        manifest_path,
        *specs_root.glob("*/CURRENT_SPEC.md"),
        *(root / "odylith" / "atlas" / "source").glob("*.mmd"),
        root / "odylith" / "atlas" / "source" / "catalog" / "diagrams.v1.json",
    ]:
        if not candidate.is_file():
            continue
        try:
            text = candidate.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if _is_poisoned_merchant_lending_record(text):
            paths.append(candidate)
    return sorted(paths)


def _legacy_kind(title: object, text: str) -> str:
    lowered = f"{title} {text[:400]}".casefold()
    if "define first operator workflow" in lowered or "first operator workflow" in lowered:
        return "experience"
    if "define domain contract and ownership" in lowered or "domain contract and ownership" in lowered:
        return "domain"
    if "add release proof and operations harness" in lowered or "release proof" in lowered:
        return "validation"
    if lowered.startswith("govern ") or "\nworkstream_type: umbrella\n" in f"\n{lowered}\n":
        return "program"
    return ""


def _candidate_ids_by_kind(candidates: list[tuple[Path, str]]) -> dict[str, str]:
    ids: dict[str, str] = {}
    for path, kind in candidates:
        if not kind:
            continue
        metadata, _sections = backlog_authoring._parse_metadata_and_sections(path)  # noqa: SLF001
        idea_id = str(metadata.get("idea_id", "")).strip().upper()
        if idea_id:
            ids[kind] = idea_id
    return ids


def _merchant_lending_proposal(
    *,
    repo_root: Path,
    candidates: list[tuple[Path, str]],
    poisoned_surfaces: list[Path],
) -> Mapping[str, Any]:
    from odylith.runtime.domain_intelligence import greenfield_proposals

    prompt = _prompt_from_candidates(candidates=candidates, poisoned_surfaces=poisoned_surfaces)
    envelope = greenfield_proposals.build_greenfield_proposal(repo_root=repo_root, prompt=prompt)
    proposal = envelope.get("proposal_template") if isinstance(envelope, Mapping) else None
    if not isinstance(proposal, Mapping):
        raise ValueError("could not build merchant-lending repair proposal")
    return proposal


def _prompt_from_candidates(*, candidates: list[tuple[Path, str]], poisoned_surfaces: list[Path]) -> str:
    text = "\n".join(
        [
            *(path.read_text(encoding="utf-8")[:1200] for path, _kind in candidates),
            *(path.read_text(encoding="utf-8")[:1200] for path in poisoned_surfaces[:5]),
        ]
    )
    project_match = re.search(
        r"SMB Lending Application Pulling Stable Coins From DeFi Protocols To(?: merchants on Shopify)?",
        text,
        flags=re.IGNORECASE,
    )
    if project_match:
        prompt = project_match.group(0).strip()
        if "shopify" not in prompt.casefold():
            prompt = f"{prompt} for Shopify merchants"
        return prompt
    title_match = re.search(r"(?m)^title:\s*(.+?)\s*$", text)
    title = title_match.group(1).strip() if title_match else "SMB lending application pulling stable coins from DeFi protocols to merchants on Shopify"
    if "shopify" not in title.casefold():
        title = f"{title} for Shopify merchants"
    return title


def _proposal_rows_by_kind(proposal: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    rows = [row for row in proposal.get("backlog", []) if isinstance(row, Mapping)]
    result: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        row_id = str(row.get("id", "")).strip().upper()
        title = str(row.get("title", "")).strip().casefold()
        if row_id == "WS-00" or str(row.get("workstream_type", "")).strip().casefold() == "umbrella":
            result["program"] = row
        elif row_id == "WS-01" or "workflow" in title or "portal" in title:
            result["experience"] = row
        elif row_id == "WS-02" or "contract" in title or "liquidity" in title:
            result["domain"] = row
        elif row_id == "WS-03" or "proof" in title or "harness" in title:
            result["validation"] = row
    return result


def _proposal_components(proposal: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    components: dict[str, Mapping[str, Any]] = {}
    for row in proposal.get("components", []):
        if not isinstance(row, Mapping):
            continue
        component_id = str(row.get("component_id") or row.get("id") or "").strip()
        if component_id:
            components[component_id] = row
    return components


def _proposal_diagrams(proposal: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    diagrams: dict[str, Mapping[str, Any]] = {}
    for row in proposal.get("diagrams", []):
        if not isinstance(row, Mapping):
            continue
        slug = str(row.get("slug") or "").strip()
        if slug:
            diagrams[slug] = row
    return diagrams


def _patch_merchant_lending_sections(
    *,
    sections: dict[str, str],
    row: Mapping[str, Any],
    components: Mapping[str, Mapping[str, Any]],
    proposal: Mapping[str, Any],
) -> None:
    first_slice = str(row.get("recommended_first_slice", "")).strip()
    product_view = str(row.get("product_view", "")).strip()
    sections["Problem"] = str(row.get("problem", "")).strip()
    sections["Customer"] = str(row.get("customer", "")).strip()
    sections["Opportunity"] = str(row.get("opportunity", "")).strip()
    sections["Product View"] = product_view
    sections["Proposed Solution"] = _paragraph([product_view, f"First slice: {first_slice}" if first_slice else ""])
    sections["Scope"] = _bullets([first_slice, *_component_lines(row=row, components=components)])
    sections["Non-Goals"] = _bullets(
        [
            "No retail-buyer purchase journey, card-processing flow, or consumer purchase path in this merchant-lending release.",
            "No live Shopify production data, live DeFi protocol execution, custody, private keys, production stablecoin movement, or legal underwriting claim.",
            "No source-backed implementation ownership until code paths and repo-native proof exist.",
        ]
    )
    sections["Dependencies"] = _bullets(_text_items(row.get("dependencies")))
    sections["Success Metrics"] = _bullets(_text_items(row.get("success_metrics")))
    sections["Validation"] = _bullets(_text_items(row.get("validation")))
    sections["Test Strategy"] = _bullets(
        [
            "Turn each merchant application, eligibility, liquidity, compliance, disbursement, and repayment state into deterministic fixture proof before implementation starts.",
            *_text_items(row.get("validation")),
        ]
    )
    sections["Risks"] = _bullets(
        [
            "Credit risk: loose eligibility semantics can overstate available capital or facility terms.",
            "Liquidity risk: stale stablecoin-liquidity snapshots can imply funding that cannot be allocated.",
            "Compliance risk: KYB/AML/sanctions posture must fail closed before any funding state is presented as actionable.",
            "Replay risk: disbursement and repayment events must be idempotent under duplicate or late ledger events.",
        ]
    )
    sections["Rollout"] = _bullets(
        [
            "Release 0.0.1 stays fixture-backed until merchant borrower workflow, credit-liquidity contract, and proof harness pass.",
            "Production Shopify access, DeFi protocol calls, custody, and stablecoin movement remain blocked until explicit release gates are added.",
        ]
    )
    sections["Why Now"] = str(row.get("opportunity", "")).strip()
    sections["Impacted Components"] = _bullets(_component_lines(row=row, components=components))
    sections["Interface Changes"] = _bullets(_text_items(row.get("interfaces")))
    sections["Migration/Compatibility"] = (
        "No production data migration is in scope. Legacy retail-commerce greenfield records are rewritten in place "
        "to merchant-lending requirements so future plans do not inherit consumer-purchase semantics."
    )
    sections["Open Questions"] = _bullets(
        [
            "Which Shopify merchant data fields are allowed in the first fixture schema, and who approves their use?",
            "Which KYB/AML/sanctions and jurisdiction rules block an offer, funding, or repayment state in release 0.0.1?",
            "Which stablecoin liquidity source, custody boundary, and no-live-protocol gate must be explicit before implementation?",
        ]
    )

    from odylith.runtime.domain_intelligence.greenfield_workstream_intelligence import SECTION_TITLE
    from odylith.runtime.domain_intelligence.greenfield_workstream_intelligence import render_domain_intelligence_section

    domain_intelligence = render_domain_intelligence_section(row.get("domain_intelligence"))
    if domain_intelligence:
        sections[SECTION_TITLE] = domain_intelligence
    if str(row.get("workstream_type", "")).strip().casefold() == "umbrella" or "Project Intelligence" in sections:
        from odylith.runtime.domain_intelligence.greenfield_project_intelligence import render_project_intelligence_section

        project_intelligence = render_project_intelligence_section(proposal.get("project_intelligence"))
        if project_intelligence:
            sections["Project Intelligence"] = project_intelligence


def _repair_merchant_lending_registry(
    *,
    repo_root: Path,
    proposal: Mapping[str, Any],
    rows: Mapping[str, Mapping[str, Any]],
    components: Mapping[str, Mapping[str, Any]],
) -> list[str]:
    manifest_path = _component_registry_manifest_path(repo_root)
    specs_root = manifest_path.parent / "components"
    surface_text = _surface_text([manifest_path, *sorted(specs_root.glob("*/CURRENT_SPEC.md"))])
    if not _is_poisoned_merchant_lending_record(surface_text):
        return []

    repaired: list[str] = []
    _remove_poisoned_component_specs(specs_root=specs_root)
    manifest = {
        "components": [
            _registry_entry_for_component(row=row, rows=rows, proposal=proposal)
            for row in components.values()
        ],
        "version": "v1",
    }
    rendered_manifest = json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
    if not manifest_path.is_file() or manifest_path.read_text(encoding="utf-8") != rendered_manifest:
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(manifest_path, rendered_manifest, encoding="utf-8")
        repaired.append(str(manifest_path))

    for row in components.values():
        component_id = str(row.get("component_id") or row.get("id") or "").strip()
        if not component_id:
            continue
        spec_path = specs_root / component_id / "CURRENT_SPEC.md"
        rendered_spec = _component_spec_for_merchant_lending(row=row, rows=rows)
        if not spec_path.is_file() or spec_path.read_text(encoding="utf-8") != rendered_spec:
            spec_path.parent.mkdir(parents=True, exist_ok=True)
            atomic_write_text(spec_path, rendered_spec, encoding="utf-8")
            repaired.append(str(spec_path))
    return repaired


def _component_registry_manifest_path(repo_root: Path) -> Path:
    path = truth_root_path(repo_root=repo_root, key="component_registry")
    if path.name == "component_registry.v1.json":
        return path
    return path / "component_registry.v1.json"


def _repair_merchant_lending_atlas(
    *,
    repo_root: Path,
    proposal: Mapping[str, Any],
    diagrams: Mapping[str, Mapping[str, Any]],
) -> list[str]:
    atlas_root = repo_root / "odylith" / "atlas" / "source"
    catalog_path = atlas_root / "catalog" / "diagrams.v1.json"
    source_paths = [atlas_root / f"{slug}.mmd" for slug in diagrams]
    surface_text = _surface_text([catalog_path, *source_paths])
    if not _is_poisoned_merchant_lending_record(surface_text):
        return []

    repaired: list[str] = []
    for slug, row in diagrams.items():
        source = str(row.get("mermaid_source") or row.get("source") or "").strip() + "\n"
        if not source.strip():
            continue
        path = atlas_root / f"{slug}.mmd"
        if not path.is_file() or path.read_text(encoding="utf-8") != source:
            path.parent.mkdir(parents=True, exist_ok=True)
            atomic_write_text(path, source, encoding="utf-8")
            repaired.append(str(path))
        svg_path = atlas_root / f"{slug}.svg"
        if svg_path.is_file():
            svg_path.unlink()
            repaired.append(str(svg_path))

    rendered_catalog = json.dumps(_merchant_lending_catalog(proposal=proposal), indent=2, ensure_ascii=False) + "\n"
    if not catalog_path.is_file() or catalog_path.read_text(encoding="utf-8") != rendered_catalog:
        catalog_path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(catalog_path, rendered_catalog, encoding="utf-8")
        repaired.append(str(catalog_path))
    return repaired


def _repair_merchant_lending_programs(
    *,
    repo_root: Path,
    proposal: Mapping[str, Any],
    idea_ids: Mapping[str, str],
) -> list[str]:
    umbrella_id = str(idea_ids.get("program", "")).strip().upper()
    if not umbrella_id:
        return []
    programs_root = repo_root / "odylith" / "radar" / "source" / "programs"
    path = programs_root / f"{umbrella_id}.execution-waves.v1.json"
    if not path.is_file():
        return []
    text = path.read_text(encoding="utf-8", errors="ignore")
    if not (_is_poisoned_merchant_lending_record(text) or _CONTROL_PLANE_LEAK_RE.search(text)):
        return []

    workstream_ids = {
        "WS-00": umbrella_id,
        "WS-01": str(idea_ids.get("experience", "")).strip().upper(),
        "WS-02": str(idea_ids.get("domain", "")).strip().upper(),
        "WS-03": str(idea_ids.get("validation", "")).strip().upper(),
    }
    waves: list[dict[str, Any]] = []
    for row in _proposal_program_waves(proposal):
        wave_id = str(row.get("wave_id", "")).strip() or f"W{len(waves) + 1}"
        mapped_workstreams = [
            workstream_ids[ws]
            for ws in (str(value).strip().upper() for value in row.get("workstreams", []))
            if ws in workstream_ids and workstream_ids[ws]
        ]
        validation_gate = str(row.get("validation_gate", "")).strip()
        waves.append(
            {
                "wave_id": wave_id,
                "label": str(row.get("label", "")).strip() or wave_id,
                "status": "active" if not waves else "planned",
                "summary": str(row.get("goal", "")).strip(),
                "exit_gate": validation_gate,
                "validation": [validation_gate] if validation_gate else [],
                "depends_on": [] if not waves else [waves[-1]["wave_id"]],
                "primary_workstreams": mapped_workstreams,
                "carried_workstreams": [],
                "in_band_workstreams": [],
                "gate_refs": [],
            }
        )
    if not waves:
        return []

    rendered = json.dumps({"umbrella_id": umbrella_id, "version": "v1", "waves": waves}, indent=2) + "\n"
    atomic_write_text(path, rendered, encoding="utf-8")
    return [str(path)]


def _proposal_program_waves(proposal: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    program = proposal.get("program")
    if not isinstance(program, Mapping):
        return []
    return [row for row in program.get("waves", []) if isinstance(row, Mapping)]


def _surface_text(paths: list[Path]) -> str:
    chunks: list[str] = []
    for path in paths:
        if path.is_file():
            chunks.append(path.read_text(encoding="utf-8", errors="ignore"))
    return "\n".join(chunks)


def _remove_poisoned_component_specs(*, specs_root: Path) -> None:
    if not specs_root.is_dir():
        return
    for spec_path in sorted(specs_root.glob("*/CURRENT_SPEC.md")):
        text = spec_path.read_text(encoding="utf-8", errors="ignore")
        parent = spec_path.parent
        if _is_poisoned_merchant_lending_record(text) or _CHECKOUT_LEAK_RE.search(parent.name):
            shutil.rmtree(parent)


def _registry_entry_for_component(
    *,
    row: Mapping[str, Any],
    rows: Mapping[str, Mapping[str, Any]],
    proposal: Mapping[str, Any],
) -> dict[str, Any]:
    component_id = str(row.get("component_id") or row.get("id") or "").strip()
    label = str(row.get("label") or component_id).strip()
    kind = str(row.get("kind") or "service").strip()
    intended_path = str(row.get("intended_path") or f"src/{component_id}").strip()
    responsibility = _clean_owns_text(row.get("responsibility"))
    boundary = _clean_owns_text(row.get("boundary"))
    return {
        "component_id": component_id,
        "name": label,
        "kind": kind,
        "category": "application",
        "qualification": str(row.get("qualification") or "candidate").strip(),
        "aliases": [],
        "path_prefixes": [intended_path],
        "workstreams": _component_workstreams(component_id=component_id, rows=rows),
        "diagrams": _component_diagram_ids(component_id=component_id, proposal=proposal),
        "owner": "repo",
        "status": str(row.get("status") or "planned").strip(),
        "what_it_is": f"{label} owns {responsibility.rstrip('.')}. Source boundary starts at `{intended_path}`.",
        "why_tracked": f"{label} is a product boundary for the merchant-lending first release: {boundary.rstrip('.')}.",
        "spec_ref": f"odylith/registry/source/components/{component_id}/CURRENT_SPEC.md",
        "sources": ["user_intent"],
        "subcomponents": [],
        "product_layer": "application",
    }


def _component_spec_for_merchant_lending(*, row: Mapping[str, Any], rows: Mapping[str, Mapping[str, Any]]) -> str:
    component_id = str(row.get("component_id") or row.get("id") or "").strip()
    label = str(row.get("label") or component_id).strip()
    kind = str(row.get("kind") or "service").strip()
    intended_path = str(row.get("intended_path") or f"src/{component_id}").strip()
    responsibility = _clean_owns_text(row.get("responsibility"))
    boundary = _clean_owns_text(row.get("boundary"))
    dependencies = _text_items(row.get("dependencies"))
    interfaces = _text_items(row.get("interfaces"))
    validation = _text_items(row.get("validation"))
    risks = _text_items(row.get("risks"))
    workstreams = ", ".join(f"`{item}`" for item in _component_workstreams(component_id=component_id, rows=rows))
    diagrams = ", ".join(f"`{item}`" for item in _component_diagram_ids(component_id=component_id, proposal={"diagrams": []}))
    if not diagrams:
        diagrams = "assigned during architecture refresh"
    return (
        f"# {label}\n\n"
        f"> Candidate component for the SMB merchant lending proposal. No source-backed runtime claim is made yet.\n\n"
        "## Component Snapshot\n\n"
        "| Field | Value |\n"
        "| --- | --- |\n"
        f"| Component ID | `{component_id}` |\n"
        f"| Kind | `{kind}` |\n"
        "| Status | planned |\n"
        "| Qualification | candidate |\n"
        "| Evidence | user_intent |\n"
        f"| First source boundary | `{intended_path}` |\n"
        f"| Workstreams | {workstreams or 'TBD'} |\n"
        f"| Diagrams | {diagrams} |\n\n"
        "## Product Boundary\n\n"
        f"{boundary}\n\n"
        "### Owns\n\n"
        f"{_bullets([responsibility])}\n\n"
        "### Outside Boundary\n\n"
        f"{_bullets(_outside_boundary_for_component(label))}\n\n"
        "## Contract Surface\n\n"
        f"{_bullets(interfaces)}\n\n"
        "## Dependencies\n\n"
        f"{_bullets(dependencies)}\n\n"
        "## Proof Obligations\n\n"
        f"{_bullets(validation)}\n\n"
        "## Failure Modes\n\n"
        f"{_bullets(risks or _default_component_risks(label))}\n\n"
        "## First Slice Rule\n\n"
        f"- Start inside `{intended_path}` until the technical plan proves a narrower boundary.\n"
        "- Keep fixtures closed-world: no live Shopify data, live DeFi protocol calls, custody keys, private keys, production credentials, or production stablecoin movement.\n"
        "- Promote from candidate only after source paths and repo-native proof exist.\n"
    )


def _component_workstreams(*, component_id: str, rows: Mapping[str, Mapping[str, Any]]) -> list[str]:
    defaults = {
        "merchant-capital-portal": "B-002",
        "credit-liquidity-core": "B-003",
        "lending-proof-harness": "B-004",
    }
    for suffix, workstream_id in defaults.items():
        if component_id.endswith(suffix):
            return [workstream_id]
    matches: list[str] = []
    fallback = {"program": "B-001", "experience": "B-002", "domain": "B-003", "validation": "B-004"}
    for kind, row in rows.items():
        if component_id in _text_items(row.get("component_focus")):
            matches.append(fallback.get(kind, ""))
    return [item for item in matches if item]


def _component_diagram_ids(*, component_id: str, proposal: Mapping[str, Any]) -> list[str]:
    if component_id.endswith("merchant-capital-portal"):
        return ["D-002", "D-003"]
    if component_id.endswith("credit-liquidity-core"):
        return ["D-002", "D-003", "D-004"]
    if component_id.endswith("lending-proof-harness"):
        return ["D-005"]
    return []


def _outside_boundary_for_component(label: str) -> list[str]:
    lowered = label.casefold()
    if "portal" in lowered:
        return [
            "Underwriting math and facility invariants.",
            "Treasury adapters, custody, private keys, and live DeFi protocol execution.",
            "Production Shopify data access and legal lending decisions.",
        ]
    if "credit" in lowered or "liquidity" in lowered:
        return [
            "Borrower-facing presentation.",
            "Live Shopify adapters, custody, private keys, and production protocol calls.",
            "Legal underwriting approval and accounting ledger finality.",
        ]
    return [
        "Production merchant data.",
        "Live DeFi credentials, custody keys, production disbursements, and real lending approval.",
    ]


def _default_component_risks(label: str) -> list[str]:
    lowered = label.casefold()
    if "portal" in lowered:
        return ["Borrower-visible status can imply approved capital before eligibility, compliance, and liquidity proof exist."]
    if "credit" in lowered or "liquidity" in lowered:
        return ["Facility state can overstate credit or funding if Shopify freshness, compliance, liquidity, or replay semantics are implicit."]
    return ["Proof can become meaningless if fixtures touch live systems or omit blocked and replay scenarios."]


def _clean_owns_text(value: object) -> str:
    text = str(value or "").strip()
    return re.sub(r"^\s*owns?\s+", "", text, flags=re.IGNORECASE).strip()


def _merchant_lending_catalog(*, proposal: Mapping[str, Any]) -> dict[str, Any]:
    diagrams = [row for row in proposal.get("diagrams", []) if isinstance(row, Mapping)]
    entries: list[dict[str, Any]] = []
    for index, row in enumerate(diagrams, start=1):
        slug = str(row.get("slug") or "").strip()
        if not slug:
            continue
        entries.append(
            {
                "id": f"D-{index:03d}",
                "slug": slug,
                "title": str(row.get("title") or slug).strip(),
                "kind": str(row.get("kind") or "flowchart").strip(),
                "summary": str(row.get("summary") or "").strip(),
                "review_focus": str(row.get("review_focus") or "").strip(),
                "operator_question": str(row.get("operator_question") or "").strip(),
                "proof_gate": str(row.get("proof_gate") or "").strip(),
                "link_state": str(row.get("link_state") or "architecture_first_draft").strip(),
                "source_mmd": f"odylith/atlas/source/{slug}.mmd",
                "source_svg": f"odylith/atlas/source/{slug}.svg",
                "source_png": f"odylith/atlas/source/{slug}.png",
                "source_files": [f"odylith/atlas/source/{slug}.mmd"],
                "components": list(row.get("components") or []),
                "related_workstreams": list(row.get("related_workstreams") or []),
                "evidence_tier": str(row.get("evidence_tier") or "user_intent").strip(),
            }
        )
    return {"version": "v1", "diagrams": entries}


def _component_lines(*, row: Mapping[str, Any], components: Mapping[str, Mapping[str, Any]]) -> list[str]:
    lines: list[str] = []
    for component_id in _text_items(row.get("component_focus")):
        component = components.get(component_id)
        if not component:
            continue
        label = str(component.get("label", "")).strip()
        responsibility = str(component.get("responsibility", "")).strip()
        boundary = str(component.get("boundary", "")).strip()
        detail = responsibility or boundary
        if label and detail:
            lines.append(f"{component_id} ({label}): {detail}")
        elif detail:
            lines.append(f"{component_id}: {detail}")
        else:
            lines.append(component_id)
    return lines


def _text_items(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, Mapping):
        return [f"{key}: {item}" for key, item in value.items() if str(item).strip()]
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    return [text] if text else []


def _paragraph(items: list[str]) -> str:
    return "\n\n".join(item.strip() for item in items if item.strip())


def _bullets(items: list[str]) -> str:
    rows = [item.strip() for item in items if item.strip()]
    return "\n".join(f"- {item}" for item in rows) if rows else "TBD."


def _repair_index_titles(*, repo_root: Path, titles_by_id: Mapping[str, str]) -> None:
    index_path = truth_root_path(repo_root=repo_root, key="radar_source") / "INDEX.md"
    if not index_path.is_file():
        return
    lines = index_path.read_text(encoding="utf-8").splitlines()
    updated: list[str] = []
    changed = False
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("|") or stripped.startswith("| ---"):
            updated.append(line)
            continue
        cells = [cell.strip() for cell in stripped.split("|")[1:-1]]
        if len(cells) < 3 or cells[0].casefold() == "rank":
            updated.append(line)
            continue
        idea_id = cells[1].strip().upper()
        title = titles_by_id.get(idea_id)
        if not title:
            updated.append(line)
            continue
        cells[2] = title
        if len(cells) >= 12:
            cells[-1] = re.sub(r"^\[[^\]]+\]\(", f"[{title}](", cells[-1], count=1)
        new_line = "| " + " | ".join(cells) + " |"
        updated.append(new_line)
        changed = changed or new_line != line
    if changed:
        atomic_write_text(index_path, "\n".join(updated).rstrip() + "\n", encoding="utf-8")


def _repo_relative(*, repo_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root).as_posix()
    except ValueError:
        return path.as_posix()
