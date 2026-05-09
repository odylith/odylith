"""Repairs for legacy greenfield records whose product model was misclassified."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
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
    if not candidates:
        return LegacyGreenfieldRepairResult(changed=False)

    proposal = _merchant_lending_proposal(repo_root=root, candidates=candidates)
    rows = _proposal_rows_by_kind(proposal)
    components = _proposal_components(proposal)
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
        _patch_merchant_lending_sections(sections=sections, row=row, components=components)
        rendered = backlog_authoring._render_idea_text(metadata=metadata, sections=sections)  # noqa: SLF001
        current = path.read_text(encoding="utf-8")
        if rendered != current:
            atomic_write_text(path, rendered, encoding="utf-8")
            repaired.append(str(path))
            if idea_id:
                index_titles[idea_id] = metadata["title"]

    if index_titles:
        _repair_index_titles(repo_root=root, titles_by_id=index_titles)

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
    return bool(_MERCHANT_LENDING_RE.search(text) and _CHECKOUT_LEAK_RE.search(text))


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


def _merchant_lending_proposal(*, repo_root: Path, candidates: list[tuple[Path, str]]) -> Mapping[str, Any]:
    from odylith.runtime.domain_intelligence import greenfield_proposals

    prompt = _prompt_from_candidates(candidates)
    envelope = greenfield_proposals.build_greenfield_proposal(repo_root=repo_root, prompt=prompt)
    proposal = envelope.get("proposal_template") if isinstance(envelope, Mapping) else None
    if not isinstance(proposal, Mapping):
        raise ValueError("could not build merchant-lending repair proposal")
    return proposal


def _prompt_from_candidates(candidates: list[tuple[Path, str]]) -> str:
    text = "\n".join(path.read_text(encoding="utf-8")[:1200] for path, _kind in candidates)
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


def _patch_merchant_lending_sections(
    *,
    sections: dict[str, str],
    row: Mapping[str, Any],
    components: Mapping[str, Mapping[str, Any]],
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
