"""Build deterministic Greenfield case seeds from retained source captures."""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
import json
from pathlib import Path
import sys
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
SRC_ROOT = REPO_ROOT / "src"

for import_root in (SCRIPT_DIR, SRC_ROOT):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

from greenfield_matrix_case_file import canonical_case_text  # noqa: E402
from greenfield_matrix_corpus_provenance import CASE_PROVENANCE_VERSION  # noqa: E402
from greenfield_matrix_input_axes import RELEASE_INPUT_STYLES  # noqa: E402
from greenfield_matrix_stressors import DEFAULT_HIGH_VARIANCE_STRESSORS  # noqa: E402
from greenfield_release_source_capture import DEFAULT_ARTIFACTS_PER_FAMILY  # noqa: E402
from greenfield_release_source_capture import SOURCE_FAMILIES  # noqa: E402
from greenfield_release_source_capture import SOURCE_MANIFEST_VERSION  # noqa: E402
from greenfield_release_source_capture import FetchedJson  # noqa: E402
from greenfield_release_source_capture import SourceFamily  # noqa: E402
from greenfield_release_source_capture import capture_release_sources  # noqa: E402
from greenfield_release_source_capture import json_text  # noqa: E402
from greenfield_release_source_capture import load_json_object  # noqa: E402
from greenfield_release_source_capture import load_verified_sources  # noqa: E402
from greenfield_release_source_capture import repo_relative  # noqa: E402
from greenfield_release_source_capture import sha256_text  # noqa: E402
from greenfield_release_source_capture import single_line  # noqa: E402
from greenfield_release_source_capture import slug  # noqa: E402
from greenfield_release_source_capture import write_new_json_atomically  # noqa: E402


SOURCE_CASE_FILE_VERSION = "odylith.greenfield.matrix.case-file.v1"
DEFAULT_PAIRED_ARTIFACTS_PER_FAMILY = 2


def build_release_case_file(
    *,
    source_manifest: Path,
    output_json: Path,
    repo_root: Path = REPO_ROOT,
    paired_artifacts_per_family: int = DEFAULT_PAIRED_ARTIFACTS_PER_FAMILY,
) -> dict[str, Any]:
    """Derive discovery-only case seeds without producing audit approval evidence."""

    manifest_path = Path(source_manifest).expanduser().resolve()
    manifest = load_json_object(manifest_path)
    if manifest.get("version") != SOURCE_MANIFEST_VERSION:
        raise RuntimeError(f"unsupported source manifest version in {manifest_path}")
    root = Path(repo_root).expanduser().resolve()
    manifest_relative = repo_relative(manifest_path, root)
    artifact_count = int(manifest.get("artifacts_per_family") or 0)
    if not 0 <= int(paired_artifacts_per_family) <= artifact_count:
        raise ValueError("paired_artifacts_per_family must not exceed artifacts_per_family")
    source_rows = load_verified_sources(manifest, manifest_path.parent, root)
    cases: list[dict[str, Any]] = []
    for _, rows in sorted(source_rows.items()):
        for ordinal, source in enumerate(rows, start=1):
            for transform, excerpt, span, variant_label in source_variants(
                source=source,
                paired=ordinal <= int(paired_artifacts_per_family),
            ):
                case_index = len(cases)
                cases.append(
                    case_from_source(
                        source=source,
                        case_index=case_index,
                        input_style=RELEASE_INPUT_STYLES[case_index % len(RELEASE_INPUT_STYLES)],
                        transform=transform,
                        source_excerpt=excerpt,
                        source_span=span,
                        variant_label=variant_label,
                    )
                )
    payload = {
        "version": SOURCE_CASE_FILE_VERSION,
        "claim_class": "source-provenanced-discovery",
        "release_readiness_boundary": "Independent automated audit evidence and installed release proof are still required.",
        "source_manifest": manifest_relative,
        "source_case_count": len(cases),
        "cases": cases,
    }
    write_new_json_atomically(Path(output_json), payload, "release case output")
    return payload


def source_variants(*, source: Mapping[str, Any], paired: bool) -> tuple[tuple[str, str, str, str], ...]:
    artifact_path = Path(str(source["artifact_path"]))
    artifact_text = artifact_path.read_text(encoding="utf-8")
    repository = source["repository"]
    assert isinstance(repository, Mapping)
    description = single_line(repository.get("description"))
    topics = tuple(single_line(topic) for topic in repository.get("topics", ()))
    primary = (
        "description_evidence",
        description,
        field_value_span(artifact_text, "description", description),
        "description",
    )
    if not paired:
        return (("singleton", description, primary[2], "source"),)
    topic = next((value for value in topics if value != description), "")
    if not topic:
        raise RuntimeError(f"paired source lacks a distinct topic excerpt: {artifact_path}")
    return (primary, ("topic_evidence", topic, topic_span(artifact_text, topic), "topic"))


def case_from_source(
    *,
    source: Mapping[str, Any],
    case_index: int,
    input_style: str,
    transform: str,
    source_excerpt: str,
    source_span: str,
    variant_label: str,
) -> dict[str, Any]:
    artifact = source["artifact"]
    repository = source["repository"]
    assert isinstance(artifact, Mapping)
    assert isinstance(repository, Mapping)
    family = single_line(artifact.get("source_family"))
    full_name = single_line(repository.get("full_name"))
    description = single_line(repository.get("description"))
    prompt = canonical_case_text(
        prompt_for_style(
            input_style=input_style,
            family=family,
            full_name=full_name,
            description=description,
            source_excerpt=source_excerpt,
        )
    )
    provenance = {
        "corpus_tier": "source_provenanced",
        "schema_version": CASE_PROVENANCE_VERSION,
        "source_id": single_line(artifact.get("source_id")),
        "source_uri": single_line(artifact.get("source_uri")),
        "source_artifact_path": str(source["artifact_relative"]),
        "source_artifact_sha256": str(source["artifact_sha256"]),
        "source_span": source_span,
        "source_span_sha256": sha256_text(source_span),
        "source_excerpt": source_excerpt,
        "source_excerpt_sha256": sha256_text(source_excerpt),
        "retrieved_on": single_line(artifact.get("captured_on")),
        "license_or_consent": single_line(artifact.get("rights_notice")),
        "source_family": family,
        "derivation_method": "deterministic-github-metadata-product-intent-v1",
        "derived_prompt_sha256": sha256_text(prompt),
        "derivation_author": "freedom-research",
    }
    row: dict[str, Any] = {
        "case_id": f"release-{slug(family)}-{case_index + 1:03d}-{variant_label}",
        "name": f"{family} source case {case_index + 1}",
        "prompt": prompt,
        "required_terms": [full_name],
        "leakage_terms": [full_name],
        "tags": ["release-corpus", family, "github-metadata"],
        "stressors": stressors_for_case(case_index),
        "input_style": input_style,
        "provenance": provenance,
    }
    if transform != "singleton":
        row["metamorphic_group"] = f"{slug(single_line(artifact.get('source_id')))}-pair"
        row["metamorphic_transform"] = transform
    if input_style == "edited_confirmation":
        row["confirmed_intent_markdown"] = confirmed_intent(
            family,
            full_name,
            description,
            source_excerpt,
        )
    return row


def prompt_for_style(
    *,
    input_style: str,
    family: str,
    full_name: str,
    description: str,
    source_excerpt: str,
) -> str:
    context = f"Source repository: {full_name}. Source evidence: {source_excerpt}"
    if source_excerpt != description:
        context += f". Repository description: {description}"
    article = indefinite_article(family)
    templates = {
        "direct_request": f"Create {article} {family} product from this evidence. {context}",
        "edited_confirmation": f"Create a reviewed {family} product. {context}",
        "pasted_brief": f"Project brief for {article} {family} team:\n{context}",
        "research_evidence": f"Research evidence for {article} {family} product: {source_excerpt}. {context}",
        "thin_request": f"Build around this {family} evidence: {context}",
    }
    return templates[input_style]


def indefinite_article(value: str) -> str:
    return "an" if single_line(value).casefold().startswith(("a", "e", "i", "o", "u")) else "a"


def confirmed_intent(family: str, full_name: str, description: str, source_excerpt: str) -> str:
    return "\n".join(
        (
            f"# {family.title()} Source Product",
            "",
            "## Product Story",
            description,
            "",
            "## Source Evidence",
            source_excerpt,
            "",
            "## First Complete Path",
            f"An operator reviews evidence from {full_name}, records one decision, and verifies the resulting outcome.",
            "",
            "## Proof Boundary",
            "The source evidence, decision, and outcome remain traceable.",
        )
    )


def stressors_for_case(case_index: int) -> list[str]:
    width = len(DEFAULT_HIGH_VARIANCE_STRESSORS)
    return [
        DEFAULT_HIGH_VARIANCE_STRESSORS[case_index % width],
        DEFAULT_HIGH_VARIANCE_STRESSORS[(case_index + 3) % width],
        DEFAULT_HIGH_VARIANCE_STRESSORS[(case_index + 7) % width],
    ]


def field_value_span(artifact_text: str, field: str, excerpt: str) -> str:
    encoded = json.dumps(excerpt, ensure_ascii=True)
    marker = f'"{field}": {encoded}'
    matches = [index for index, line in enumerate(artifact_text.splitlines(), start=1) if marker in line]
    if len(matches) != 1:
        raise RuntimeError(f"source field must occur on exactly one artifact line: {field}")
    return f"line {matches[0]}"


def topic_span(artifact_text: str, topic: str) -> str:
    encoded = json.dumps(topic, ensure_ascii=True)
    in_topics = False
    matches: list[int] = []
    for index, line in enumerate(artifact_text.splitlines(), start=1):
        if '"topics": [' in line:
            in_topics = True
            continue
        if in_topics and line.strip() == "]":
            in_topics = False
            continue
        if in_topics and line.strip().rstrip(",") == encoded:
            matches.append(index)
    if len(matches) != 1:
        raise RuntimeError(f"source topic must occur on exactly one topics line: {topic}")
    return f"line {matches[0]}"


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    capture = commands.add_parser("capture", help="Capture public MIT-declared repository metadata.")
    capture.add_argument("--output-root", required=True)
    capture.add_argument("--retrieved-on", default="")
    capture.add_argument("--captured-at", default="")
    capture.add_argument("--artifacts-per-family", type=int, default=DEFAULT_ARTIFACTS_PER_FAMILY)
    build = commands.add_parser("build", help="Build source-provenanced Greenfield case seeds.")
    build.add_argument("--source-manifest", required=True)
    build.add_argument("--output-json", required=True)
    build.add_argument("--repo-root", default=str(REPO_ROOT))
    build.add_argument("--paired-artifacts-per-family", type=int, default=DEFAULT_PAIRED_ARTIFACTS_PER_FAMILY)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.command == "capture":
        payload = capture_release_sources(
            output_root=Path(args.output_root),
            artifacts_per_family=int(args.artifacts_per_family),
            retrieved_on=str(args.retrieved_on or "") or None,
            captured_at=str(args.captured_at or "") or None,
        )
    else:
        payload = build_release_case_file(
            source_manifest=Path(args.source_manifest),
            output_json=Path(args.output_json),
            repo_root=Path(args.repo_root),
            paired_artifacts_per_family=int(args.paired_artifacts_per_family),
        )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
