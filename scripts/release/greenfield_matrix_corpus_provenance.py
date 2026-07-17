"""Source-provenance and audit policy for release-grade Greenfield corpora."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import date
import hashlib
import json
from math import ceil
from pathlib import Path
import re
from typing import Any
from urllib.parse import urlparse

from greenfield_matrix_input_axes import RELEASE_INPUT_STYLES
from greenfield_matrix_input_axes import normalize_input_style
from greenfield_matrix_stressors import DEFAULT_HIGH_VARIANCE_STRESSORS


CASE_PROVENANCE_VERSION = "odylith.greenfield.matrix.case-provenance.v1"
RELEASE_AUDIT_VERSION = "odylith.greenfield.matrix.release-audit.v1"
RELEASE_CORPUS_POLICY_VERSION = "odylith.greenfield.matrix.release-corpus-policy.v1"


@dataclass(frozen=True)
class GreenfieldCaseProvenance:
    """Immutable origin metadata retained separately from untrusted evidence text."""

    corpus_tier: str = "synthetic_regression"
    schema_version: str = ""
    source_id: str = ""
    source_uri: str = ""
    source_artifact_path: str = ""
    source_artifact_sha256: str = ""
    source_span: str = ""
    source_span_sha256: str = ""
    source_excerpt: str = ""
    source_excerpt_sha256: str = ""
    retrieved_on: str = ""
    license_or_consent: str = ""
    source_family: str = ""
    derivation_method: str = ""
    derived_prompt_sha256: str = ""
    derivation_author: str = ""


@dataclass(frozen=True)
class GreenfieldReleaseAudit:
    case_id: str
    prompt_sha256: str
    source_artifact_sha256: str
    source_excerpt_sha256: str
    reviewer_id: str
    reviewed_on: str
    review_status: str
    independent: bool
    review_evidence_path: str
    review_evidence_sha256: str


@dataclass(frozen=True)
class ReleaseCorpusPolicy:
    minimum_case_count: int = 200
    minimum_source_families: int = 10
    minimum_cases_per_family: int = 6
    maximum_family_share: float = 0.20
    maximum_cases_per_source_artifact: int = 3
    maximum_cases_per_source_id: int = 1
    maximum_cases_per_source_uri: int = 1
    minimum_cases_per_stressor: int = 8
    required_input_styles: tuple[str, ...] = RELEASE_INPUT_STYLES
    minimum_cases_per_input_style: int = 8
    minimum_complete_metamorphic_groups: int = 20
    audit_fraction: float = 0.20
    minimum_audited_cases: int = 24
    near_duplicate_jaccard_threshold: float = 0.85

    def minimum_audit_count(self, case_count: int) -> int:
        return max(self.minimum_audited_cases, ceil(max(0, case_count) * self.audit_fraction))


@dataclass(frozen=True)
class ReleaseCorpusEvaluation:
    issues: tuple[str, ...]
    summary: Mapping[str, Any]

    @property
    def passed(self) -> bool:
        return not self.issues

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": RELEASE_CORPUS_POLICY_VERSION,
            "status": "passed" if self.passed else "failed",
            "claim_class": "source-provenanced-release" if self.passed else "not-release-proven",
            "issues": list(self.issues),
            "summary": dict(self.summary),
        }


def case_provenance_from_mapping(value: Any) -> GreenfieldCaseProvenance:
    """Decode case provenance without allowing absent metadata to imply release proof."""

    if value is None:
        return GreenfieldCaseProvenance()
    if not isinstance(value, Mapping):
        raise ValueError("provenance must be a JSON object")
    return GreenfieldCaseProvenance(
        corpus_tier=_canonical_tier(value.get("corpus_tier")),
        schema_version=_text(value.get("schema_version")),
        source_id=_text(value.get("source_id")),
        source_uri=_text(value.get("source_uri")),
        source_artifact_path=_text(value.get("source_artifact_path")),
        source_artifact_sha256=_hash_text(value.get("source_artifact_sha256")),
        source_span=_text(value.get("source_span")),
        source_span_sha256=_hash_text(value.get("source_span_sha256")),
        source_excerpt=_text(value.get("source_excerpt")),
        source_excerpt_sha256=_hash_text(value.get("source_excerpt_sha256")),
        retrieved_on=_text(value.get("retrieved_on")),
        license_or_consent=_text(value.get("license_or_consent")),
        source_family=_text(value.get("source_family")),
        derivation_method=_text(value.get("derivation_method")),
        derived_prompt_sha256=_hash_text(value.get("derived_prompt_sha256")),
        derivation_author=_text(value.get("derivation_author")),
    )


def case_provenance_to_dict(provenance: GreenfieldCaseProvenance) -> dict[str, str]:
    """Encode metadata for a replay shard without embedding raw source material."""

    return {key: str(value) for key, value in asdict(provenance).items() if str(value).strip()}


def case_provenance_summary(provenance: GreenfieldCaseProvenance | None) -> dict[str, str]:
    """Return the non-sensitive provenance fields retained with matrix evidence."""

    provenance = provenance or GreenfieldCaseProvenance()
    return {
        "corpus_tier": provenance.corpus_tier,
        "source_id": provenance.source_id,
        "source_uri": provenance.source_uri,
        "source_artifact_sha256": provenance.source_artifact_sha256,
        "source_span_sha256": provenance.source_span_sha256,
        "source_excerpt_sha256": provenance.source_excerpt_sha256,
        "source_family": provenance.source_family,
        "retrieved_on": provenance.retrieved_on,
        "license_or_consent": provenance.license_or_consent,
        "derivation_method": provenance.derivation_method,
        "derived_prompt_sha256": provenance.derived_prompt_sha256,
    }


def load_release_audit_file(path: Path) -> tuple[GreenfieldReleaseAudit, ...]:
    """Load independent review records; raw source evidence is never loaded here."""

    audit_path = Path(path).expanduser().resolve()
    try:
        payload = json.loads(audit_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise RuntimeError(f"unable to read greenfield release audit file {audit_path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"greenfield release audit file {audit_path} is not valid JSON: {exc}") from exc
    if not isinstance(payload, Mapping):
        raise RuntimeError("greenfield release audit file must be a JSON object")
    if _text(payload.get("version")) != RELEASE_AUDIT_VERSION:
        raise RuntimeError(f"greenfield release audit file must declare version {RELEASE_AUDIT_VERSION}")
    rows = payload.get("audits")
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes, bytearray)):
        raise RuntimeError("greenfield release audit file must define an audits array")
    audits: list[GreenfieldReleaseAudit] = []
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, Mapping):
            raise RuntimeError(f"greenfield release audit entry {index} must be a JSON object")
        independent = row.get("independent")
        if type(independent) is not bool:
            raise RuntimeError(
                f"greenfield release audit entry {index} must define independent as a JSON boolean"
            )
        audit = GreenfieldReleaseAudit(
            case_id=_text(row.get("case_id")),
            prompt_sha256=_hash_text(row.get("prompt_sha256")),
            source_artifact_sha256=_hash_text(row.get("source_artifact_sha256")),
            source_excerpt_sha256=_hash_text(row.get("source_excerpt_sha256")),
            reviewer_id=_text(row.get("reviewer_id")),
            reviewed_on=_text(row.get("reviewed_on")),
            review_status=_text(row.get("review_status")).casefold(),
            independent=independent,
            review_evidence_path=_text(row.get("review_evidence_path")),
            review_evidence_sha256=_hash_text(row.get("review_evidence_sha256")),
        )
        if not audit.case_id:
            raise RuntimeError(f"greenfield release audit entry {index} must define case_id")
        audits.append(audit)
    return tuple(audits)


def evaluate_release_corpus(
    cases: Sequence[Any],
    audits: Sequence[GreenfieldReleaseAudit] = (),
    *,
    policy: ReleaseCorpusPolicy = ReleaseCorpusPolicy(),
    repo_root: Path | None = None,
) -> ReleaseCorpusEvaluation:
    """Fail closed before install whenever a corpus cannot support a release claim."""

    records = tuple(cases)
    root = Path(repo_root or Path(__file__).resolve().parents[2]).expanduser().resolve()
    issues: list[str] = []
    if len(records) < policy.minimum_case_count:
        issues.append(
            "release proof requires at least "
            f"{policy.minimum_case_count} source-provenanced cases; received {len(records)}"
        )

    cases_by_id: dict[str, Any] = {}
    prompt_hashes: dict[str, list[str]] = {}
    families: Counter[str] = Counter()
    artifacts: Counter[str] = Counter()
    source_ids: Counter[str] = Counter()
    source_uris: Counter[str] = Counter()
    source_id_uris: dict[str, set[str]] = {}
    source_uri_ids: dict[str, set[str]] = {}
    stressors: Counter[str] = Counter()
    input_styles: Counter[str] = Counter()
    undeclared_input_style_labels: list[str] = []
    metamorphic_cases: dict[str, list[Any]] = {}
    provenance_failures: list[str] = []
    artifact_hash_cache: dict[Path, str] = {}
    review_evidence_hash_cache: dict[Path, str] = {}
    normalized_prompts: list[tuple[str, str]] = []

    for index, case in enumerate(records, start=1):
        case_id = _case_id(case)
        label = case_id or f"case-{index}"
        if not case_id:
            provenance_failures.append(f"{label}: release cases require case_id")
        elif case_id in cases_by_id:
            provenance_failures.append(f"{case_id}: duplicate case_id")
        else:
            cases_by_id[case_id] = case

        prompt = str(getattr(case, "prompt", "") or "")
        prompt_hash = _sha256_text(prompt)
        prompt_hashes.setdefault(prompt_hash, []).append(label)
        normalized_prompts.append((label, prompt))
        provenance = getattr(case, "provenance", GreenfieldCaseProvenance())
        if not isinstance(provenance, GreenfieldCaseProvenance):
            provenance_failures.append(f"{label}: provenance is invalid")
            continue
        provenance_failures.extend(_case_provenance_issues(case, provenance, root, artifact_hash_cache))
        if provenance.source_family:
            families[provenance.source_family] += 1
        if provenance.source_artifact_sha256:
            artifacts[provenance.source_artifact_sha256] += 1
        if provenance.source_id:
            source_ids[provenance.source_id] += 1
            source_id_uris.setdefault(provenance.source_id, set()).add(
                _source_uri_identity(provenance.source_uri)
            )
        if provenance.source_uri:
            uri_identity = _source_uri_identity(provenance.source_uri)
            source_uris[uri_identity] += 1
            source_uri_ids.setdefault(uri_identity, set()).add(provenance.source_id)
        for stressor in _case_stressors(case):
            stressors[stressor] += 1
        if not bool(getattr(case, "input_style_declared", False)):
            undeclared_input_style_labels.append(label)
        else:
            try:
                input_styles[normalize_input_style(getattr(case, "input_style", ""))] += 1
            except ValueError as exc:
                issues.append(f"{label}: invalid input_style: {exc}")
        metamorphic_group = str(getattr(case, "metamorphic_group", "") or "").strip()
        metamorphic_transform = str(getattr(case, "metamorphic_transform", "") or "").strip()
        if bool(metamorphic_group) != bool(metamorphic_transform):
            issues.append(f"{label}: metamorphic_group and metamorphic_transform must be declared together")
        elif metamorphic_group:
            metamorphic_cases.setdefault(metamorphic_group, []).append(case)

    issues.extend(provenance_failures[:60])
    for prompt_hash, labels in sorted(prompt_hashes.items()):
        if prompt_hash and len(labels) > 1:
            issues.append("release corpus contains duplicate prompts: " + ", ".join(labels[:6]))
    issues.extend(_near_duplicate_issues(normalized_prompts, policy.near_duplicate_jaccard_threshold))

    if len(families) < policy.minimum_source_families:
        issues.append(
            f"release proof requires at least {policy.minimum_source_families} source families; received {len(families)}"
        )
    for family, count in sorted(families.items()):
        if count < policy.minimum_cases_per_family:
            issues.append(
                f"source family `{family}` has {count} cases; release proof requires at least "
                f"{policy.minimum_cases_per_family} per family"
            )
        if len(records) and count / len(records) > policy.maximum_family_share:
            max_count = int(len(records) * policy.maximum_family_share)
            issues.append(
                f"source family `{family}` has {count} cases; release proof permits at most {max_count} "
                f"({int(policy.maximum_family_share * 100)}%)"
            )
    for artifact, count in sorted(artifacts.items()):
        if count > policy.maximum_cases_per_source_artifact:
            issues.append(
                f"source artifact `{artifact}` produced {count} cases; release proof permits at most "
                f"{policy.maximum_cases_per_source_artifact}"
            )
    for source_id, count in sorted(source_ids.items()):
        if count > policy.maximum_cases_per_source_id:
            issues.append(
                f"source_id `{source_id}` has {count} cases; release proof permits at most "
                f"{policy.maximum_cases_per_source_id} per source ID"
            )
        if len(source_id_uris[source_id]) > 1:
            issues.append(f"source_id `{source_id}` is bound to multiple source URIs")
    for source_uri, count in sorted(source_uris.items()):
        if count > policy.maximum_cases_per_source_uri:
            issues.append(
                f"source_uri `{source_uri}` has {count} cases; release proof permits at most "
                f"{policy.maximum_cases_per_source_uri} per source URI"
            )
        if len(source_uri_ids[source_uri]) > 1:
            issues.append(f"source_uri `{source_uri}` is bound to multiple source IDs")
    for stressor in DEFAULT_HIGH_VARIANCE_STRESSORS:
        if stressors[stressor] < policy.minimum_cases_per_stressor:
            issues.append(
                f"stressor `{stressor}` has {stressor_count(stressors, stressor)} cases; release proof requires at least "
                f"{policy.minimum_cases_per_stressor}"
            )
    if undeclared_input_style_labels:
        issues.append(
            "release corpus has cases without an explicit input_style: "
            + ", ".join(undeclared_input_style_labels[:6])
        )
    for style in policy.required_input_styles:
        if input_styles[style] < policy.minimum_cases_per_input_style:
            issues.append(
                f"input_style `{style}` has {input_styles[style]} cases; release proof requires at least "
                f"{policy.minimum_cases_per_input_style}"
            )
    complete_metamorphic_groups = _complete_metamorphic_groups(metamorphic_cases)
    incomplete_metamorphic_groups = sorted(set(metamorphic_cases) - set(complete_metamorphic_groups))
    if incomplete_metamorphic_groups:
        issues.append(
            "release corpus has incomplete metamorphic groups: " + ", ".join(incomplete_metamorphic_groups[:6])
        )
    if len(complete_metamorphic_groups) < policy.minimum_complete_metamorphic_groups:
        issues.append(
            "release proof requires at least "
            f"{policy.minimum_complete_metamorphic_groups} complete metamorphic groups; received "
            f"{len(complete_metamorphic_groups)}"
        )

    audit_issues, audited_case_ids = _audit_issues(
        cases_by_id=cases_by_id,
        audits=audits,
        policy=policy,
        root=root,
        review_evidence_hash_cache=review_evidence_hash_cache,
    )
    issues.extend(audit_issues)
    summary = {
        "case_count": len(records),
        "source_family_count": len(families),
        "source_family_counts": dict(sorted(families.items())),
        "source_artifact_count": len(artifacts),
        "source_id_count": len(source_ids),
        "source_uri_count": len(source_uris),
        "stressor_counts": {key: int(stressors[key]) for key in DEFAULT_HIGH_VARIANCE_STRESSORS},
        "input_style_counts": dict(sorted(input_styles.items())),
        "undeclared_input_style_count": len(undeclared_input_style_labels),
        "complete_metamorphic_group_count": len(complete_metamorphic_groups),
        "complete_metamorphic_groups": complete_metamorphic_groups,
        "audit_count": len(audited_case_ids),
        "minimum_audit_count": policy.minimum_audit_count(len(records)),
        "policy": asdict(policy),
    }
    return ReleaseCorpusEvaluation(issues=tuple(dict.fromkeys(issues)), summary=summary)


def discovery_corpus_summary(cases: Sequence[Any]) -> dict[str, Any]:
    """Label useful synthetic coverage accurately instead of implying release readiness."""

    tiers = Counter(
        str(getattr(getattr(case, "provenance", None), "corpus_tier", "synthetic_regression"))
        for case in cases
    )
    return {
        "version": RELEASE_CORPUS_POLICY_VERSION,
        "status": "discovery",
        "claim_class": "synthetic-discovery" if tiers.get("synthetic_regression", 0) else "source-provenanced-discovery",
        "case_count": len(cases),
        "corpus_tier_counts": dict(sorted(tiers.items())),
        "release_readiness_boundary": "discovery coverage is useful regression evidence but is not a release claim",
    }


def stressor_count(counts: Counter[str], stressor: str) -> int:
    return int(counts.get(stressor) or 0)


def _complete_metamorphic_groups(groups: Mapping[str, Sequence[Any]]) -> dict[str, list[str]]:
    complete: dict[str, list[str]] = {}
    for group, cases in sorted(groups.items()):
        transforms = sorted(
            {
                str(getattr(case, "metamorphic_transform", "") or "").strip()
                for case in cases
                if str(getattr(case, "metamorphic_transform", "") or "").strip()
            }
        )
        provenances = [getattr(case, "provenance", GreenfieldCaseProvenance()) for case in cases]
        artifact_hashes = {
            str(getattr(provenance, "source_artifact_sha256", "") or "").strip()
            for provenance in provenances
            if str(getattr(provenance, "source_artifact_sha256", "") or "").strip()
        }
        spans = {
            str(getattr(provenance, "source_span", "") or "").strip()
            for provenance in provenances
            if str(getattr(provenance, "source_span", "") or "").strip()
        }
        if len(transforms) >= 2 and len(artifact_hashes) == 1 and len(spans) >= 2:
            complete[group] = transforms
    return complete


def _case_provenance_issues(
    case: Any,
    provenance: GreenfieldCaseProvenance,
    root: Path,
    artifact_hash_cache: dict[Path, str],
) -> list[str]:
    label = _case_id(case) or str(getattr(case, "name", "case") or "case")
    issues: list[str] = []
    if provenance.corpus_tier != "source_provenanced":
        issues.append(f"{label}: corpus_tier must be source_provenanced for release proof")
    if provenance.schema_version != CASE_PROVENANCE_VERSION:
        issues.append(f"{label}: provenance must declare schema_version {CASE_PROVENANCE_VERSION}")
    required = {
        "source_id": provenance.source_id,
        "source_uri": provenance.source_uri,
        "source_artifact_path": provenance.source_artifact_path,
        "source_artifact_sha256": provenance.source_artifact_sha256,
        "source_span": provenance.source_span,
        "source_span_sha256": provenance.source_span_sha256,
        "source_excerpt": provenance.source_excerpt,
        "source_excerpt_sha256": provenance.source_excerpt_sha256,
        "retrieved_on": provenance.retrieved_on,
        "license_or_consent": provenance.license_or_consent,
        "source_family": provenance.source_family,
        "derivation_method": provenance.derivation_method,
        "derived_prompt_sha256": provenance.derived_prompt_sha256,
        "derivation_author": provenance.derivation_author,
    }
    missing = [field for field, value in required.items() if not str(value).strip()]
    if missing:
        issues.append(f"{label}: provenance is missing " + ", ".join(missing))
        return issues
    parsed = urlparse(provenance.source_uri)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        issues.append(f"{label}: source_uri must be an absolute HTTP(S) URL")
    if not _is_sha256(provenance.source_artifact_sha256):
        issues.append(f"{label}: source_artifact_sha256 must be a SHA-256 digest")
    if not _is_sha256(provenance.source_span_sha256):
        issues.append(f"{label}: source_span_sha256 must be a SHA-256 digest")
    if not _is_sha256(provenance.source_excerpt_sha256):
        issues.append(f"{label}: source_excerpt_sha256 must be a SHA-256 digest")
    if not _is_sha256(provenance.derived_prompt_sha256):
        issues.append(f"{label}: derived_prompt_sha256 must be a SHA-256 digest")
    if _sha256_text(str(getattr(case, "prompt", "") or "")) != provenance.derived_prompt_sha256:
        issues.append(f"{label}: derived_prompt_sha256 does not match the case prompt")
    if _sha256_text(provenance.source_span) != provenance.source_span_sha256:
        issues.append(f"{label}: source_span_sha256 does not match source_span")
    if _sha256_text(provenance.source_excerpt) != provenance.source_excerpt_sha256:
        issues.append(f"{label}: source_excerpt_sha256 does not match source_excerpt")
    if not _is_iso_date(provenance.retrieved_on):
        issues.append(f"{label}: retrieved_on must be an ISO date")
    artifact_path = _repo_artifact_path(root, provenance.source_artifact_path)
    if artifact_path is None:
        issues.append(f"{label}: source_artifact_path must be a repository-relative file")
    elif not artifact_path.is_file():
        issues.append(f"{label}: source_artifact_path does not exist: {provenance.source_artifact_path}")
    else:
        artifact_hash = artifact_hash_cache.setdefault(artifact_path, _sha256_file(artifact_path))
        if artifact_hash != provenance.source_artifact_sha256:
            issues.append(f"{label}: source_artifact_sha256 does not match source_artifact_path")
        try:
            artifact_text = artifact_path.read_text(encoding="utf-8")
        except OSError as exc:
            issues.append(f"{label}: unable to read source_artifact_path: {exc}")
        else:
            source_span_text = _resolved_source_span(artifact_text, provenance.source_span)
            if source_span_text is None:
                issues.append(f"{label}: source_span does not resolve against source_artifact_path")
            elif provenance.source_excerpt not in source_span_text:
                issues.append(f"{label}: source_excerpt is not present in declared source_span")
    return issues


def _audit_issues(
    *,
    cases_by_id: Mapping[str, Any],
    audits: Sequence[GreenfieldReleaseAudit],
    policy: ReleaseCorpusPolicy,
    root: Path,
    review_evidence_hash_cache: dict[Path, str],
) -> tuple[list[str], set[str]]:
    issues: list[str] = []
    approved: set[str] = set()
    seen: set[str] = set()
    for audit in audits:
        if audit.case_id in seen:
            issues.append(f"release audit duplicates case_id `{audit.case_id}`")
            continue
        seen.add(audit.case_id)
        case = cases_by_id.get(audit.case_id)
        if case is None:
            issues.append(f"release audit references unknown case_id `{audit.case_id}`")
            continue
        provenance = getattr(case, "provenance", GreenfieldCaseProvenance())
        expected_prompt_hash = _sha256_text(str(getattr(case, "prompt", "") or ""))
        if audit.prompt_sha256 != expected_prompt_hash:
            issues.append(f"release audit `{audit.case_id}` does not match prompt_sha256")
            continue
        if audit.source_artifact_sha256 != provenance.source_artifact_sha256:
            issues.append(f"release audit `{audit.case_id}` does not match source_artifact_sha256")
            continue
        if audit.source_excerpt_sha256 != provenance.source_excerpt_sha256:
            issues.append(f"release audit `{audit.case_id}` does not match source_excerpt_sha256")
            continue
        if audit.review_status != "approved":
            issues.append(f"release audit `{audit.case_id}` is not approved")
            continue
        if type(audit.independent) is not bool:
            issues.append(f"release audit `{audit.case_id}` must define independent as a boolean")
            continue
        if not audit.independent:
            issues.append(f"release audit `{audit.case_id}` is not independent")
            continue
        if not audit.reviewer_id or audit.reviewer_id == provenance.derivation_author:
            issues.append(f"release audit `{audit.case_id}` must name an independent reviewer")
            continue
        if not _is_iso_date(audit.reviewed_on):
            issues.append(f"release audit `{audit.case_id}` must use an ISO reviewed_on date")
            continue
        if not _is_sha256(audit.review_evidence_sha256):
            issues.append(f"release audit `{audit.case_id}` must include review_evidence_sha256")
            continue
        review_evidence_path = _repo_artifact_path(root, audit.review_evidence_path)
        if review_evidence_path is None:
            issues.append(f"release audit `{audit.case_id}` must use a repository-relative review_evidence_path")
            continue
        if not review_evidence_path.is_file():
            issues.append(
                f"release audit `{audit.case_id}` review_evidence_path does not exist: "
                f"{audit.review_evidence_path}"
            )
            continue
        evidence_hash = review_evidence_hash_cache.setdefault(
            review_evidence_path, _sha256_file(review_evidence_path)
        )
        if evidence_hash != audit.review_evidence_sha256:
            issues.append(
                f"release audit `{audit.case_id}` review_evidence_sha256 does not match review_evidence_path"
            )
            continue
        approved.add(audit.case_id)
    required_audits = policy.minimum_audit_count(len(cases_by_id))
    if len(approved) < required_audits:
        issues.append(f"release proof requires at least {required_audits} approved independent audits; received {len(approved)}")
    audited_cases = [cases_by_id[case_id] for case_id in approved if case_id in cases_by_id]
    audited_families = {
        str(getattr(getattr(case, "provenance", None), "source_family", "") or "")
        for case in audited_cases
    }
    all_families = {
        str(getattr(getattr(case, "provenance", None), "source_family", "") or "")
        for case in cases_by_id.values()
    }
    missing_families = sorted(family for family in all_families if family and family not in audited_families)
    if missing_families:
        issues.append("release audit is not stratified across source families: " + ", ".join(missing_families))
    audited_stressors = {stressor for case in audited_cases for stressor in _case_stressors(case)}
    missing_stressors = [stressor for stressor in DEFAULT_HIGH_VARIANCE_STRESSORS if stressor not in audited_stressors]
    if missing_stressors:
        issues.append("release audit is not stratified across stressors: " + ", ".join(missing_stressors))
    return issues, approved


def _near_duplicate_issues(rows: Sequence[tuple[str, str]], threshold: float) -> list[str]:
    issues: list[str] = []
    tokens = [(label, _three_grams(text)) for label, text in rows]
    for index, (left_label, left) in enumerate(tokens):
        if not left:
            continue
        for right_label, right in tokens[index + 1 :]:
            if not right:
                continue
            overlap = len(left & right) / float(len(left | right))
            if overlap >= threshold:
                issues.append(
                    f"release corpus contains near-duplicate prompts: {left_label}, {right_label} "
                    f"({overlap:.2f} Jaccard)"
                )
                if len(issues) >= 20:
                    return issues
    return issues


def _repo_artifact_path(root: Path, value: str) -> Path | None:
    candidate = Path(value)
    if not value or candidate.is_absolute():
        return None
    resolved = (root / candidate).resolve()
    try:
        resolved.relative_to(root)
    except ValueError:
        return None
    return resolved


def _resolved_source_span(artifact_text: str, source_span: str) -> str | None:
    match = re.fullmatch(
        r"lines? (?P<start>[1-9]\d*)(?:\s*-\s*(?P<end>[1-9]\d*))?",
        source_span.casefold(),
    )
    if match is None:
        return None
    start = int(match.group("start"))
    end = int(match.group("end") or start)
    lines = artifact_text.splitlines(keepends=True)
    if end < start or end > len(lines):
        return None
    return "".join(lines[start - 1 : end])


def _source_uri_identity(value: str) -> str:
    parsed = urlparse(value)
    return parsed._replace(
        scheme=parsed.scheme.casefold(),
        netloc=parsed.netloc.casefold(),
        fragment="",
    ).geturl()


def _case_id(case: Any) -> str:
    return _text(getattr(case, "case_id", ""))


def _case_stressors(case: Any) -> tuple[str, ...]:
    return tuple(
        _text(item).casefold()
        for item in tuple(getattr(case, "stressors", ()) or ())
        if _text(item)
    )


def _three_grams(value: str) -> frozenset[str]:
    words = re.findall(r"[a-z0-9]+", str(value or "").casefold())
    if len(words) < 3:
        return frozenset(words)
    return frozenset(" ".join(words[index : index + 3]) for index in range(len(words) - 2))


def _canonical_tier(value: Any) -> str:
    token = _text(value).casefold().replace("-", "_")
    return token or "synthetic_regression"


def _text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _hash_text(value: Any) -> str:
    return _text(value).casefold()


def _sha256_text(value: str) -> str:
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_sha256(value: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-f]{64}", str(value or "")))


def _is_iso_date(value: str) -> bool:
    try:
        date.fromisoformat(str(value))
    except ValueError:
        return False
    return True


__all__ = [
    "CASE_PROVENANCE_VERSION",
    "GreenfieldCaseProvenance",
    "GreenfieldReleaseAudit",
    "RELEASE_AUDIT_VERSION",
    "RELEASE_CORPUS_POLICY_VERSION",
    "ReleaseCorpusEvaluation",
    "ReleaseCorpusPolicy",
    "case_provenance_from_mapping",
    "case_provenance_summary",
    "case_provenance_to_dict",
    "discovery_corpus_summary",
    "evaluate_release_corpus",
    "load_release_audit_file",
]
