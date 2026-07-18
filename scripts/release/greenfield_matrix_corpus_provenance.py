"""Source-provenance and audit policy for release-grade Greenfield corpora."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
import json
from math import ceil
from pathlib import Path
import re
from typing import Any
from urllib.parse import urlparse

from greenfield_matrix_input_axes import RELEASE_INPUT_STYLES
from greenfield_matrix_input_axes import normalize_input_style
from greenfield_matrix_release_artifacts import is_iso_date
from greenfield_matrix_release_artifacts import is_sha256
from greenfield_matrix_release_artifacts import repo_artifact_path
from greenfield_matrix_release_artifacts import sha256_file
from greenfield_matrix_release_artifacts import sha256_text
from greenfield_matrix_release_audit import GreenfieldReleaseAudit
from greenfield_matrix_release_audit import evaluate_release_audits
from greenfield_matrix_source_identity import complete_metamorphic_groups
from greenfield_matrix_source_identity import is_explicit_metamorphic_pair
from greenfield_matrix_source_identity import source_identity_label
from greenfield_matrix_source_identity import source_uri_identity
from greenfield_matrix_stressors import DEFAULT_HIGH_VARIANCE_STRESSORS


CASE_PROVENANCE_VERSION = "odylith.greenfield.matrix.case-provenance.v2"
RELEASE_AUDIT_VERSION = "odylith.greenfield.matrix.release-audit.v4"
RELEASE_CORPUS_POLICY_VERSION = "odylith.greenfield.matrix.release-corpus-policy.v2"


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
class ReleaseCorpusPolicy:
    minimum_case_count: int = 200
    minimum_source_families: int = 10
    minimum_cases_per_family: int = 6
    maximum_family_share: float = 0.20
    minimum_source_artifact_count: int = 180
    maximum_cases_per_source_artifact: int = 2
    maximum_cases_per_source_id: int = 2
    maximum_cases_per_source_uri: int = 2
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
    """Load independent automated review records; raw source evidence is never loaded here."""

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
            source_id=_text(row.get("source_id")),
            source_uri=_text(row.get("source_uri")),
            source_verification_method=_text(row.get("source_verification_method")),
            source_verification_uri=_text(row.get("source_verification_uri")),
            source_verified_on=_text(row.get("source_verified_on")),
            source_verification_path=_text(row.get("source_verification_path")),
            source_verification_sha256=_hash_text(row.get("source_verification_sha256")),
            reviewer_id=_text(row.get("reviewer_id")),
            reviewer_kind=_text(row.get("reviewer_kind")).casefold(),
            review_method=_text(row.get("review_method")),
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
    source_id_artifacts: dict[str, set[str]] = {}
    source_uri_ids: dict[str, set[str]] = {}
    source_uri_artifacts: dict[str, set[str]] = {}
    artifact_source_ids: dict[str, set[str]] = {}
    artifact_source_uris: dict[str, set[str]] = {}
    artifact_paths: dict[str, set[str]] = {}
    source_identity_cases: dict[tuple[str, str, str], list[Any]] = {}
    stressors: Counter[str] = Counter()
    input_styles: Counter[str] = Counter()
    undeclared_input_style_labels: list[str] = []
    metamorphic_cases: dict[str, list[Any]] = {}
    provenance_failures: list[str] = []
    artifact_hash_cache: dict[Path, str] = {}
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
        prompt_hash = sha256_text(prompt)
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
            artifact_paths.setdefault(provenance.source_artifact_sha256, set()).add(
                provenance.source_artifact_path
            )
        if provenance.source_id:
            source_ids[provenance.source_id] += 1
            source_id_uris.setdefault(provenance.source_id, set()).add(
                source_uri_identity(provenance.source_uri)
            )
            source_id_artifacts.setdefault(provenance.source_id, set()).add(
                provenance.source_artifact_sha256
            )
        if provenance.source_uri:
            uri_identity = source_uri_identity(provenance.source_uri)
            source_uris[uri_identity] += 1
            source_uri_ids.setdefault(uri_identity, set()).add(provenance.source_id)
            source_uri_artifacts.setdefault(uri_identity, set()).add(provenance.source_artifact_sha256)
        if provenance.source_artifact_sha256:
            artifact_source_ids.setdefault(provenance.source_artifact_sha256, set()).add(provenance.source_id)
            artifact_source_uris.setdefault(provenance.source_artifact_sha256, set()).add(
                source_uri_identity(provenance.source_uri)
            )
            source_identity_cases.setdefault(
                (
                    provenance.source_id,
                    source_uri_identity(provenance.source_uri),
                    provenance.source_artifact_sha256,
                ),
                [],
            ).append(case)
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
    if len(artifacts) < policy.minimum_source_artifact_count:
        issues.append(
            "release proof requires at least "
            f"{policy.minimum_source_artifact_count} distinct source artifacts; received {len(artifacts)}"
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
        if len(artifact_paths[artifact]) > 1:
            issues.append(f"source artifact `{artifact}` is bound to multiple artifact paths")
        if len(artifact_source_ids[artifact]) > 1 or len(artifact_source_uris[artifact]) > 1:
            issues.append(f"source artifact `{artifact}` is bound to multiple source identities")
    for source_id, count in sorted(source_ids.items()):
        if count > policy.maximum_cases_per_source_id:
            issues.append(
                f"source_id `{source_id}` has {count} cases; release proof permits at most "
                f"{policy.maximum_cases_per_source_id} per source ID"
            )
        if len(source_id_uris[source_id]) > 1:
            issues.append(f"source_id `{source_id}` is bound to multiple source URIs")
        if len(source_id_artifacts[source_id]) > 1:
            issues.append(f"source_id `{source_id}` is bound to multiple source artifacts")
    for source_uri, count in sorted(source_uris.items()):
        if count > policy.maximum_cases_per_source_uri:
            issues.append(
                f"source_uri `{source_uri}` has {count} cases; release proof permits at most "
                f"{policy.maximum_cases_per_source_uri} per source URI"
            )
        if len(source_uri_ids[source_uri]) > 1:
            issues.append(f"source_uri `{source_uri}` is bound to multiple source IDs")
        if len(source_uri_artifacts[source_uri]) > 1:
            issues.append(f"source_uri `{source_uri}` is bound to multiple source artifacts")
    for identity, identity_cases in sorted(source_identity_cases.items()):
        if len(identity_cases) > 1 and not is_explicit_metamorphic_pair(identity_cases):
            issues.append(
                "source identity is reused outside one explicit metamorphic pair: "
                + source_identity_label(identity)
            )
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
    complete_groups = complete_metamorphic_groups(metamorphic_cases)
    incomplete_metamorphic_groups = sorted(set(metamorphic_cases) - set(complete_groups))
    if incomplete_metamorphic_groups:
        issues.append(
            "release corpus has incomplete metamorphic groups: " + ", ".join(incomplete_metamorphic_groups[:6])
        )
    if len(complete_groups) < policy.minimum_complete_metamorphic_groups:
        issues.append(
            "release proof requires at least "
            f"{policy.minimum_complete_metamorphic_groups} complete metamorphic groups; received "
            f"{len(complete_groups)}"
        )

    audit_issues, audited_case_ids = evaluate_release_audits(
        cases_by_id=cases_by_id,
        audits=audits,
        policy=policy,
        root=root,
    )
    issues.extend(audit_issues)
    audited_reviewer_kinds = Counter(
        audit.reviewer_kind for audit in audits if audit.case_id in audited_case_ids
    )
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
        "complete_metamorphic_group_count": len(complete_groups),
        "complete_metamorphic_groups": complete_groups,
        "audit_count": len(audited_case_ids),
        "audit_reviewer_kind_counts": dict(sorted(audited_reviewer_kinds.items())),
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
    if not is_sha256(provenance.source_artifact_sha256):
        issues.append(f"{label}: source_artifact_sha256 must be a SHA-256 digest")
    if not is_sha256(provenance.source_span_sha256):
        issues.append(f"{label}: source_span_sha256 must be a SHA-256 digest")
    if not is_sha256(provenance.source_excerpt_sha256):
        issues.append(f"{label}: source_excerpt_sha256 must be a SHA-256 digest")
    if not is_sha256(provenance.derived_prompt_sha256):
        issues.append(f"{label}: derived_prompt_sha256 must be a SHA-256 digest")
    if sha256_text(str(getattr(case, "prompt", "") or "")) != provenance.derived_prompt_sha256:
        issues.append(f"{label}: derived_prompt_sha256 does not match the case prompt")
    if sha256_text(provenance.source_span) != provenance.source_span_sha256:
        issues.append(f"{label}: source_span_sha256 does not match source_span")
    if sha256_text(provenance.source_excerpt) != provenance.source_excerpt_sha256:
        issues.append(f"{label}: source_excerpt_sha256 does not match source_excerpt")
    if not is_iso_date(provenance.retrieved_on):
        issues.append(f"{label}: retrieved_on must be an ISO date")
    artifact_path = repo_artifact_path(root, provenance.source_artifact_path)
    if artifact_path is None:
        issues.append(f"{label}: source_artifact_path must be a repository-relative file")
    elif not artifact_path.is_file():
        issues.append(f"{label}: source_artifact_path does not exist: {provenance.source_artifact_path}")
    else:
        artifact_hash = artifact_hash_cache.setdefault(artifact_path, sha256_file(artifact_path))
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
            elif not _source_excerpt_in_span(provenance.source_excerpt, source_span_text):
                issues.append(f"{label}: source_excerpt is not present in declared source_span")
    return issues


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


def _resolved_source_span(artifact_text: str, source_span: str) -> str | None:
    bounds = _source_span_bounds(source_span)
    if bounds is None:
        return None
    start, end = bounds
    lines = artifact_text.splitlines(keepends=True)
    if end > len(lines):
        return None
    return "".join(lines[start - 1 : end])


def _source_excerpt_in_span(source_excerpt: str, source_span_text: str) -> bool:
    if source_excerpt in source_span_text:
        return True
    # Retained source artifacts are JSON. A logical string containing quotes is
    # represented with JSON escapes in its raw line, but remains the same source value.
    encoded_excerpt = json.dumps(source_excerpt, ensure_ascii=True)
    return encoded_excerpt[1:-1] in source_span_text


def source_span_is_valid(source_span: str) -> bool:
    """Return whether a source span uses the portable release-corpus grammar."""

    return _source_span_bounds(source_span) is not None


def _source_span_bounds(source_span: str) -> tuple[int, int] | None:
    match = re.fullmatch(
        r"lines? (?P<start>[1-9]\d*)(?:\s*-\s*(?P<end>[1-9]\d*))?",
        source_span.casefold(),
    )
    if match is None:
        return None
    start = int(match.group("start"))
    end = int(match.group("end") or start)
    if end < start:
        return None
    return start, end


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
    "source_span_is_valid",
]
