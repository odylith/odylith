from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse
from urllib.error import HTTPError

import pytest

from odylith.runtime.domain_intelligence.greenfield_confirmed_prompt_source import prompt_intent_source


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_ROOT = REPO_ROOT / "scripts" / "release"
CAPTURED_AT = "2026-07-18T12:00:00Z"


def _module():
    spec = importlib.util.spec_from_file_location(
        "greenfield_release_corpus_test",
        SCRIPTS_ROOT / "greenfield_release_corpus.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _json_bytes(value: Mapping[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=True).encode("utf-8")


def _json_text(value: Mapping[str, Any]) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n"


def _repository(*, repository_id: int, family_topic: str) -> dict[str, Any]:
    owner = f"source{repository_id}"
    name = f"{family_topic}-evidence"
    return {
        "id": repository_id,
        "node_id": f"R_kgDO{repository_id:08d}",
        "full_name": f"{owner}/{name}",
        "name": name,
        "description": (
            f"Public {family_topic} evidence tooling that records traceable decisions for operators."
        ),
        "html_url": f"https://github.com/{owner}/{name}",
        "topics": [family_topic, "public-evidence"],
        "private": False,
        "fork": False,
        "archived": False,
        "disabled": False,
        "license": {"key": "mit", "name": "MIT License", "spdx_id": "MIT"},
        "default_branch": "main",
        "pushed_at": "2026-07-17T10:00:00Z",
    }


def _fetcher(repositories: Sequence[Mapping[str, Any]]) -> Callable[[str], tuple[Mapping[str, Any], bytes]]:
    responses = iter(repositories)

    def fetch_json(_url: str) -> tuple[Mapping[str, Any], bytes]:
        payload = {"items": [dict(next(responses))]}
        return payload, _json_bytes(payload)

    return fetch_json


def _capture_fixture(module: Any, tmp_path: Path):
    families = (
        module.SourceFamily("climate", "climate"),
        module.SourceFamily("health", "health"),
    )
    output_root = tmp_path / "captured"
    manifest = module.capture_release_sources(
        output_root=output_root,
        query_specs=families,
        artifacts_per_family=1,
        retrieved_on=CAPTURED_AT[:10],
        captured_at=CAPTURED_AT,
        fetch_json=_fetcher(
            (
                _repository(repository_id=701, family_topic="climate"),
                _repository(repository_id=702, family_topic="health"),
            )
        ),
    )
    return output_root, manifest


def _write_manifest(path: Path, manifest: Mapping[str, Any]) -> None:
    path.write_text(_json_text(manifest), encoding="utf-8")


def _assert_no_staging_or_lock(output: Path) -> None:
    assert not output.exists()
    assert not output.with_name(f".{output.name}.lock").exists()
    assert not list(output.parent.glob(f".{output.name}.staging-*"))


def _audit_request(
    *,
    case_id: str,
    source_id: str,
    source_uri: str,
    prompt_sha256: str = "0" * 64,
    source_artifact_sha256: str = "1" * 64,
    source_excerpt_sha256: str = "2" * 64,
    source_family: str = "climate",
    stressors: Sequence[str] = ("evidence-bound",),
) -> dict[str, Any]:
    evidence = sys.modules["greenfield_matrix_release_audit_evidence"]
    request = {
        "case_id": case_id,
        "prompt_sha256": prompt_sha256,
        "source_artifact_sha256": source_artifact_sha256,
        "source_excerpt_sha256": source_excerpt_sha256,
        "source_id": source_id,
        "source_uri": source_uri,
        "source_family": source_family,
        "stressors": list(stressors),
        "source_verification_method": "github-repository-api-check-v1",
        "source_verification_uri": f"https://api.github.com/repositories/{source_id.rsplit(':', 1)[1]}",
        "required_assessments": {
            "source_binding": "verified",
            "source_family_assessment": "approved",
            "derivation_assessment": "approved",
        },
    }
    request["audit_request_sha256"] = evidence.audit_request_sha256(request)
    return request


def _approved_review(case_id: str, audit_request_sha256: str) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "audit_request_sha256": audit_request_sha256,
        "review_context_label": "adversarial-context",
        "reviewer_kind": "automated_adversarial",
        "review_method": "adversarial-source-to-prompt-v1",
        "reviewed_on": CAPTURED_AT[:10],
        "review_status": "approved",
        "source_binding": "verified",
        "source_family_assessment": "approved",
        "derivation_assessment": "approved",
        "rationale": "The reviewer explicitly approved the bound source and prompt.",
    }


def _prepared_single_audit(
    module: Any,
    tmp_path: Path,
    *,
    confirmed_intent_markdown: str = "",
) -> tuple[Path, Any, Mapping[str, Any], Path, Path, Any]:
    source_root, _manifest = _capture_fixture(module, tmp_path)
    case_file = tmp_path / "cases.json"
    module.build_release_case_file(
        source_manifest=source_root / "source-manifest.v2.json",
        output_json=case_file,
        repo_root=tmp_path,
        paired_artifacts_per_family=0,
    )
    loader = sys.modules["greenfield_matrix_case_file"].load_case_file
    if confirmed_intent_markdown:
        case_payload = json.loads(case_file.read_text(encoding="utf-8"))
        case_payload["cases"][0]["confirmed_intent_markdown"] = confirmed_intent_markdown
        case_file.write_text(_json_text(case_payload), encoding="utf-8")
    case = loader(case_file)[0]
    verifier = sys.modules["greenfield_release_audit_verification"]
    evidence = sys.modules["greenfield_matrix_release_audit_evidence"]
    request = evidence.audit_request_for_case(
        case,
        source_verification_method="github-repository-api-check-v1",
        source_verification_uri=f"https://api.github.com/repositories/{case.provenance.source_id.rsplit(':', 1)[1]}",
    )
    request["audit_request_sha256"] = evidence.audit_request_sha256(request)
    plan_path = tmp_path / "audit-plan.json"
    plan_path.write_text(
        _json_text(
            {
                "version": verifier.AUDIT_REQUEST_PLAN_VERSION,
                "claim_class": "audit-requests-only",
                "source_case_file": "cases.json",
                "requests": [request],
            }
        ),
        encoding="utf-8",
    )
    verification_root = tmp_path / "source-verifications"
    remote = {
        "id": int(case.provenance.source_id.rsplit(":", 1)[1]),
        "html_url": case.provenance.source_uri,
    }
    verifier.capture_audit_source_verifications(
        audit_request_plan=plan_path,
        output_root=verification_root,
        repo_root=tmp_path,
        captured_at=CAPTURED_AT,
        fetch_json=lambda _url: (remote, _json_bytes(remote)),
    )
    writer = sys.modules["greenfield_release_audit_writer"]
    return case_file, case, request, plan_path, verification_root, writer


def test_capture_binds_a_case_to_the_raw_github_repository_id(tmp_path: Path) -> None:
    module = _module()
    output_root = tmp_path / "captured"
    repository = _repository(repository_id=701, family_topic="climate")

    manifest = module.capture_release_sources(
        output_root=output_root,
        query_specs=(module.SourceFamily("climate", "climate"),),
        artifacts_per_family=1,
        retrieved_on=CAPTURED_AT[:10],
        captured_at=CAPTURED_AT,
        fetch_json=_fetcher((repository,)),
    )

    source = manifest["sources"][0]
    artifact_path = output_root / source["artifact_path"]
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    response_path = output_root / source["search_response_path"]

    assert source["source_id"] == "github-repository:701"
    assert artifact["source_id"] == "github-repository:701"
    assert artifact["repository"]["id"] == 701
    assert artifact["repository"]["node_id"] == repository["node_id"]
    assert source["selection_index"] == artifact["selection_index"] == 1
    assert source["response_item_index"] == artifact["response_item_index"] == 0
    assert response_path.read_bytes() == _json_bytes({"items": [repository]})
    assert source["search_response_sha256"] == _sha256_bytes(response_path.read_bytes())

    artifact["source_id"] = "github-repository:999"
    artifact["repository"]["id"] = 999
    artifact_text = _json_text(artifact)
    artifact_path.write_text(artifact_text, encoding="utf-8")
    source["source_id"] = "github-repository:999"
    source["artifact_sha256"] = _sha256_bytes(artifact_text.encode("utf-8"))
    _write_manifest(output_root / "source-manifest.v2.json", manifest)

    with pytest.raises(RuntimeError, match="source capture fields diverge from retained response"):
        module.build_release_case_file(
            source_manifest=output_root / "source-manifest.v2.json",
            output_json=tmp_path / "cases.json",
            repo_root=tmp_path,
            paired_artifacts_per_family=0,
        )


def test_builds_source_provenanced_discovery_cases_from_multiple_families(tmp_path: Path) -> None:
    module = _module()
    output_root, manifest = _capture_fixture(module, tmp_path)
    case_file = tmp_path / "cases.json"

    payload = module.build_release_case_file(
        source_manifest=output_root / "source-manifest.v2.json",
        output_json=case_file,
        repo_root=tmp_path,
        paired_artifacts_per_family=1,
    )
    written = json.loads(case_file.read_text(encoding="utf-8"))

    assert written == payload
    assert payload["version"] == module.SOURCE_CASE_FILE_VERSION
    assert payload["claim_class"] == "source-provenanced-discovery"
    assert payload["claim_class"] != "source-provenanced-release"
    assert payload["release_readiness_boundary"] == (
        "Hash-bound automated review evidence and installed release proof are still required."
    )
    assert payload["source_manifest"] == "captured/source-manifest.v2.json"
    assert payload["source_case_count"] == 4
    assert {case["provenance"]["source_family"] for case in payload["cases"]} == {"climate", "health"}
    assert {case["provenance"]["source_id"] for case in payload["cases"]} == {
        "github-repository:701",
        "github-repository:702",
    }
    assert {case["metamorphic_transform"] for case in payload["cases"]} == {
        "description_evidence",
        "topic_evidence",
    }
    assert all(case["provenance"]["corpus_tier"] == "source_provenanced" for case in payload["cases"])
    assert all(case["provenance"]["schema_version"] == module.CASE_PROVENANCE_VERSION for case in payload["cases"])
    assert all(case["provenance"]["source_artifact_path"].startswith("captured/sources/") for case in payload["cases"])
    assert all(case["provenance"]["source_span"].startswith("line ") for case in payload["cases"])
    explicit_intent_cases = [case for case in payload["cases"] if "explicit-user-intent" in case["tags"]]
    evidence_only_cases = [case for case in payload["cases"] if "source-evidence-only" in case["tags"]]
    assert len(explicit_intent_cases) == len(evidence_only_cases) == 2
    for case in payload["cases"]:
        source_id = case["provenance"]["source_id"].split(":")[-1]
        family = case["provenance"]["source_family"]
        assert case["leakage_terms"] == [f"source{source_id}/{family}-evidence"]
        assert case["leakage_terms"][0] in case["prompt"]
        if case.get("confirmed_intent_markdown"):
            confirmation = case["confirmed_intent_markdown"]
            first_path = confirmation.split("## First Complete Path", maxsplit=1)[1]
            assert case["leakage_terms"][0] not in first_path
            assert "Repository: " + case["leakage_terms"][0] in confirmation
    for case in explicit_intent_cases:
        assert case.get("expectation", "transaction_committed") == "transaction_committed"
        assert "User intent: " in case["prompt"]
        assert case["prompt"].index("User intent:") < case["prompt"].index("Source evidence:")
        assert case["required_terms"][0] == case["provenance"]["source_family"]
        assert len(case["required_terms"]) == 4
        assert all(term in case["prompt"] for term in case["required_terms"][1:])
    for case in evidence_only_cases:
        assert case["expectation"] == "clarification_required"
        assert "User intent: " not in case["prompt"]
        assert case["required_terms"] == [case["provenance"]["source_family"]]
    assert all(
        case["provenance"]["derived_prompt_sha256"]
        == _sha256_bytes(case["prompt"].encode("utf-8"))
        for case in payload["cases"]
    )
    assert manifest["source_count"] == 2


def test_confirmed_source_case_keeps_user_first_path_after_source_evidence() -> None:
    module = _module()
    user_intent, terms = module.user_intent_for_case(0)

    confirmation = module.confirmed_intent(
        "climate",
        "source/climate-evidence",
        "Climate evidence tooling.",
        "Climate evidence tooling.",
        user_intent,
    )

    first_path = confirmation.split("## First Complete Path\n", maxsplit=1)[1].split("\n\n## Proof Boundary", maxsplit=1)[0]
    assert first_path == user_intent
    assert "source/climate-evidence" not in first_path
    assert all(term in first_path for term in terms)


def test_source_fixture_keeps_explicit_intent_and_source_only_cases_separate() -> None:
    payload = json.loads(
        (
            REPO_ROOT
            / "tests/fixtures/greenfield-release-corpus/greenfield-release-source-provenanced.v3.json"
        ).read_text(encoding="utf-8")
    )
    cases = payload["cases"]
    confirmed_case = next(case for case in cases if case.get("confirmed_intent_markdown"))
    clarification_case = next(case for case in cases if case.get("expectation") == "clarification_required")

    explicit_path = confirmed_case["prompt"].split("User intent:", maxsplit=1)[1].split("Source repository:", maxsplit=1)[0].strip()
    first_path = (
        confirmed_case["confirmed_intent_markdown"]
        .split("## First Complete Path\n", maxsplit=1)[1]
        .split("\n\n## Proof Boundary", maxsplit=1)[0]
    )
    assert first_path == explicit_path
    assert all(term in first_path for term in confirmed_case["required_terms"][1:])
    assert confirmed_case["leakage_terms"][0] not in first_path
    assert "User intent:" not in clarification_case["prompt"]
    assert clarification_case.get("confirmed_intent_markdown") is None


def test_source_fixture_explicit_user_intent_is_the_recovered_prompt_path() -> None:
    payload = json.loads(
        (
            REPO_ROOT
            / "tests/fixtures/greenfield-release-corpus/greenfield-release-source-provenanced.v3.json"
        ).read_text(encoding="utf-8")
    )

    explicit_intent_cases = (case for case in payload["cases"] if "User intent:" in case["prompt"])
    for case in explicit_intent_cases:
        source = prompt_intent_source(case["prompt"])
        expected = case["prompt"].split("User intent:", maxsplit=1)[1].split("Source repository:", maxsplit=1)[0].strip(" .")

        assert source.first_path == expected, case["case_id"]
        assert source.actor, case["case_id"]
        assert "User intent:" not in source.actor
        assert "User intent:" not in source.first_path


def test_shipped_release_audit_fixture_is_hash_bound_and_evaluable() -> None:
    _module()
    corpus_root = REPO_ROOT / "tests/fixtures/greenfield-release-corpus"
    cases = sys.modules["greenfield_matrix_case_file"].load_case_file(
        corpus_root / "greenfield-release-source-provenanced.v3.json"
    )
    provenance = sys.modules["greenfield_matrix_corpus_provenance"]
    audits = provenance.load_release_audit_file(
        corpus_root / "audit-evidence-v15/greenfield-release-audit.v9.json",
        repo_root=REPO_ROOT,
    )

    evaluation = provenance.evaluate_release_corpus(cases, audits, repo_root=REPO_ROOT)

    assert evaluation.passed, evaluation.issues
    assert any(case.confirmed_intent_markdown for case in cases)
    assert any(case.expectation == "clarification_required" for case in cases)


def test_build_keeps_singletons_unpaired_and_hashes_loaded_prompt_text(tmp_path: Path) -> None:
    module = _module()
    output_root = tmp_path / "captured"
    repositories = (
        _repository(repository_id=710, family_topic="climate"),
        _repository(repository_id=711, family_topic="climate"),
    )
    raw_payload = {"items": list(repositories)}
    module.capture_release_sources(
        output_root=output_root,
        query_specs=(module.SourceFamily("climate", "climate"),),
        artifacts_per_family=2,
        retrieved_on=CAPTURED_AT[:10],
        captured_at=CAPTURED_AT,
        fetch_json=lambda _url: (raw_payload, _json_bytes(raw_payload)),
    )
    case_file = tmp_path / "cases.json"
    payload = module.build_release_case_file(
        source_manifest=output_root / "source-manifest.v2.json",
        output_json=case_file,
        repo_root=tmp_path,
        paired_artifacts_per_family=1,
    )
    loader = sys.modules["greenfield_matrix_case_file"].load_case_file
    loaded_cases = loader(case_file)

    assert len(payload["cases"]) == 3
    assert sum("metamorphic_group" not in case for case in payload["cases"]) == 1
    assert all(
        case["provenance"]["source_excerpt"] in case["prompt"] for case in payload["cases"]
    )
    assert all(
        case.provenance.derived_prompt_sha256 == _sha256_bytes(case.prompt.encode("utf-8"))
        for case in loaded_cases
    )


def test_build_preserves_quoted_source_excerpt_traceability(tmp_path: Path) -> None:
    module = _module()
    output_root = tmp_path / "captured"
    repository = _repository(repository_id=712, family_topic="climate")
    repository["description"] = 'Climate evidence for the "verified outcome" review workflow.'
    payload = {"items": [repository]}
    module.capture_release_sources(
        output_root=output_root,
        query_specs=(module.SourceFamily("climate", "climate", ("climate",)),),
        artifacts_per_family=1,
        retrieved_on=CAPTURED_AT[:10],
        captured_at=CAPTURED_AT,
        fetch_json=lambda _url: (payload, _json_bytes(payload)),
    )
    case_file = tmp_path / "cases.json"
    module.build_release_case_file(
        source_manifest=output_root / "source-manifest.v2.json",
        output_json=case_file,
        repo_root=tmp_path,
        paired_artifacts_per_family=0,
    )
    loader = sys.modules["greenfield_matrix_case_file"].load_case_file
    provenance = sys.modules["greenfield_matrix_corpus_provenance"]
    evaluation = provenance.evaluate_release_corpus(loader(case_file), repo_root=tmp_path)

    assert not any("source_excerpt is not present" in issue for issue in evaluation.issues)


def test_prompt_styles_use_correct_indefinite_articles() -> None:
    module = _module()
    prompt = module.prompt_for_style(
        input_style="direct_request",
        family="accessibility",
        full_name="source/accessibility",
        description="Accessible workflow evidence.",
        source_excerpt="Accessible workflow evidence.",
    )
    brief = module.prompt_for_style(
        input_style="pasted_brief",
        family="open-data",
        full_name="source/open-data",
        description="Open data workflow evidence.",
        source_excerpt="Open data workflow evidence.",
    )
    explicit_intent = module.prompt_for_style(
        input_style="direct_request",
        family="accessibility",
        full_name="source/accessibility",
        description="Accessible workflow evidence.",
        source_excerpt="Accessible workflow evidence.",
        user_intent="A service coordinator opens an intake request, assigns a resolution owner, and verifies a decision receipt.",
    )

    assert prompt.startswith("Create an accessibility product")
    assert brief.startswith("Project brief for an open-data team")
    assert ". User intent: A service coordinator opens an intake request" in explicit_intent
    assert explicit_intent.index("User intent:") < explicit_intent.index("Source evidence:")


def test_default_source_shape_meets_every_non_audit_release_policy(tmp_path: Path) -> None:
    module = _module()

    def fetch_json(url: str) -> tuple[Mapping[str, Any], bytes]:
        topic = parse_qs(urlparse(url).query)["q"][0].split("topic:", 1)[1]
        family_index = next(
            index for index, family in enumerate(module.SOURCE_FAMILIES) if family.topic == topic
        )
        repositories = []
        for offset in range(module.DEFAULT_ARTIFACTS_PER_FAMILY):
            repository = _repository(
                repository_id=(family_index + 1) * 1000 + offset,
                family_topic=topic,
            )
            distinctive_terms = " ".join(
                f"signal{family_index}_{offset}_{term}" for term in range(12)
            )
            repository["description"] = (
                f"Public {topic} evidence tooling {distinctive_terms} supports traceable operator decisions."
            )
            repository["topics"].append(f"source-evidence-{family_index}-{offset}")
            repositories.append(repository)
        payload = {"items": repositories}
        return payload, _json_bytes(payload)

    output_root = tmp_path / "captured"
    module.capture_release_sources(
        output_root=output_root,
        retrieved_on=CAPTURED_AT[:10],
        captured_at=CAPTURED_AT,
        fetch_json=fetch_json,
    )
    case_file = tmp_path / "cases.json"
    module.build_release_case_file(
        source_manifest=output_root / "source-manifest.v2.json",
        output_json=case_file,
        repo_root=tmp_path,
    )
    loader = sys.modules["greenfield_matrix_case_file"].load_case_file
    provenance = sys.modules["greenfield_matrix_corpus_provenance"]
    evaluation = provenance.evaluate_release_corpus(loader(case_file), repo_root=tmp_path)
    audit_plan_file = tmp_path / "audit-plan.json"
    audit_plan = module.build_release_audit_request_plan(
        source_case_file=case_file,
        output_json=audit_plan_file,
        repo_root=tmp_path,
    )

    assert evaluation.summary["case_count"] == 200
    assert evaluation.summary["source_artifact_count"] == 180
    assert evaluation.summary["complete_metamorphic_group_count"] == 20
    assert evaluation.issues
    assert all("audit" in issue for issue in evaluation.issues)
    assert audit_plan["claim_class"] == "audit-requests-only"
    assert audit_plan["requested_audit_count"] == 40
    assert len({request["source_artifact_sha256"] for request in audit_plan["requests"]}) == 40
    cases_by_id = {case.case_id: case for case in loader(case_file)}
    audited_cases = [cases_by_id[request["case_id"]] for request in audit_plan["requests"]]
    assert any(case.confirmed_intent_markdown for case in audited_cases)
    assert any(case.expectation == "clarification_required" for case in audited_cases)
    assert all(
        request["source_verification_uri"].startswith("https://api.github.com/repositories/")
        for request in audit_plan["requests"]
    )


def test_build_rejects_rehashed_response_tampering(tmp_path: Path) -> None:
    module = _module()
    output_root, manifest = _capture_fixture(module, tmp_path)
    response_path = output_root / "responses" / "climate.json"
    tampered_repository = _repository(repository_id=701, family_topic="climate")
    tampered_repository["description"] = "Tampered climate evidence metadata that no longer matches the capture."
    response_bytes = _json_bytes({"items": [tampered_repository]})
    response_path.write_bytes(response_bytes)
    response_sha256 = _sha256_bytes(response_bytes)

    artifact_path = output_root / "sources" / "climate-01-source701-climate-evidence.json"
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    artifact["search_response_sha256"] = response_sha256
    artifact_text = _json_text(artifact)
    artifact_path.write_text(artifact_text, encoding="utf-8")
    source = manifest["sources"][0]
    source["search_response_sha256"] = response_sha256
    source["artifact_sha256"] = _sha256_bytes(artifact_text.encode("utf-8"))
    _write_manifest(output_root / "source-manifest.v2.json", manifest)
    case_file = tmp_path / "cases.json"

    with pytest.raises(RuntimeError, match="source capture fields diverge from retained response"):
        module.build_release_case_file(
            source_manifest=output_root / "source-manifest.v2.json",
            output_json=case_file,
            repo_root=tmp_path,
            paired_artifacts_per_family=0,
        )

    _assert_no_staging_or_lock(case_file)


def test_build_rejects_an_artifact_path_that_escapes_the_capture_root(tmp_path: Path) -> None:
    module = _module()
    output_root, manifest = _capture_fixture(module, tmp_path)
    manifest["sources"][0]["artifact_path"] = "../escaped.json"
    _write_manifest(output_root / "source-manifest.v2.json", manifest)
    case_file = tmp_path / "cases.json"

    with pytest.raises(RuntimeError, match="source artifact escapes manifest root: ../escaped.json"):
        module.build_release_case_file(
            source_manifest=output_root / "source-manifest.v2.json",
            output_json=case_file,
            repo_root=tmp_path,
            paired_artifacts_per_family=0,
        )

    _assert_no_staging_or_lock(case_file)


def test_capture_rejects_a_source_family_shortfall_and_cleans_staging(tmp_path: Path) -> None:
    module = _module()
    output_root = tmp_path / "shortfall"
    payload = {"items": [_repository(repository_id=703, family_topic="health")]}

    with pytest.raises(RuntimeError, match="source family `climate` yielded 0 eligible repositories; need 1"):
        module.capture_release_sources(
            output_root=output_root,
            query_specs=(module.SourceFamily("climate", "climate"),),
            artifacts_per_family=1,
            retrieved_on=CAPTURED_AT[:10],
            captured_at=CAPTURED_AT,
            fetch_json=lambda _url: (payload, _json_bytes(payload)),
        )

    _assert_no_staging_or_lock(output_root)


def test_capture_requires_description_level_family_evidence(tmp_path: Path) -> None:
    module = _module()
    output_root = tmp_path / "unrelated-topic"
    repository = _repository(repository_id=704, family_topic="climate")
    repository["description"] = "Public operations tooling for traceable decisions without domain evidence."
    payload = {"items": [repository]}

    with pytest.raises(RuntimeError, match="source family `climate` yielded 0 eligible repositories; need 1"):
        module.capture_release_sources(
            output_root=output_root,
            query_specs=(module.SourceFamily("climate", "climate", ("climate", "weather")),),
            artifacts_per_family=1,
            retrieved_on=CAPTURED_AT[:10],
            captured_at=CAPTURED_AT,
            fetch_json=lambda _url: (payload, _json_bytes(payload)),
        )

    _assert_no_staging_or_lock(output_root)


def test_capture_binds_declared_and_matched_description_evidence_terms(tmp_path: Path) -> None:
    module = _module()
    output_root = tmp_path / "matched-evidence"
    repository = _repository(repository_id=705, family_topic="climate")
    repository["description"] = "Climate weather evidence for traceable operator decisions."
    family = module.SourceFamily("climate", "climate", ("climate", "weather", "energy"))

    manifest = module.capture_release_sources(
        output_root=output_root,
        query_specs=(family,),
        artifacts_per_family=1,
        retrieved_on=CAPTURED_AT[:10],
        captured_at=CAPTURED_AT,
        fetch_json=lambda _url: ({"items": [repository]}, _json_bytes({"items": [repository]})),
    )

    artifact_path = output_root / manifest["sources"][0]["artifact_path"]
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert artifact["family_description_evidence_terms"] == ["climate", "weather", "energy"]
    assert artifact["matched_description_evidence_terms"] == ["climate", "weather"]


def test_fetch_reports_rate_limits_and_uses_an_available_github_token(monkeypatch: pytest.MonkeyPatch) -> None:
    _module()
    source_capture = sys.modules["greenfield_release_source_capture"]
    monkeypatch.setenv("GITHUB_TOKEN", "capture-token")

    def rate_limited(request: Any, *, timeout: int) -> Any:
        assert timeout == 30
        assert request.get_header("Authorization") == "Bearer capture-token"
        raise HTTPError(
            request.full_url,
            403,
            "rate limit exceeded",
            {"x-ratelimit-remaining": "0", "x-ratelimit-reset": "1784410000"},
            None,
        )

    monkeypatch.setattr(source_capture, "urlopen", rate_limited)

    with pytest.raises(RuntimeError, match="rate limit is exhausted; retry after Unix time 1784410000"):
        source_capture.fetch_github_json("https://api.github.com/search/repositories?q=topic%3Aclimate")


def test_capture_audit_source_verifications_retains_only_bound_remote_records(tmp_path: Path) -> None:
    _module()
    verifier = sys.modules["greenfield_release_audit_verification"]
    plan_path = tmp_path / "audit-plan.json"
    plan = {
        "version": verifier.AUDIT_REQUEST_PLAN_VERSION,
        "claim_class": "audit-requests-only",
        "requests": [
            _audit_request(
                case_id="release-climate-001-description",
                source_id="github-repository:701",
                source_uri="https://github.com/source701/climate-evidence",
            )
        ],
    }
    plan_path.write_text(_json_text(plan), encoding="utf-8")
    response = {"id": 701, "html_url": "https://github.com/source701/climate-evidence"}
    output_root = tmp_path / "source-verifications"

    manifest = verifier.capture_audit_source_verifications(
        audit_request_plan=plan_path,
        output_root=output_root,
        repo_root=tmp_path,
        captured_at=CAPTURED_AT,
        fetch_json=lambda _url: (response, _json_bytes(response)),
    )

    record = manifest["records"][0]
    assert manifest["claim_class"] == "source-verification-only"
    assert manifest["record_count"] == 1
    assert record["source_verification_sha256"] == _sha256_bytes(_json_bytes(response))
    assert (output_root / record["source_verification_path"]).read_bytes() == _json_bytes(response)
    assert "review_evidence_path" not in record
    assert "review_status" not in record


def test_rebind_audit_source_verifications_reuses_only_matching_verified_bytes(tmp_path: Path) -> None:
    _module()
    verifier = sys.modules["greenfield_release_audit_verification"]
    source_id = "github-repository:701"
    source_uri = "https://github.com/source701/climate-evidence"
    old_request = _audit_request(
        case_id="release-climate-001-description",
        source_id=source_id,
        source_uri=source_uri,
        prompt_sha256="0" * 64,
    )
    old_plan_path = tmp_path / "old-audit-plan.json"
    old_plan_path.write_text(
        _json_text(
            {
                "version": verifier.AUDIT_REQUEST_PLAN_VERSION,
                "claim_class": "audit-requests-only",
                "requests": [old_request],
            }
        ),
        encoding="utf-8",
    )
    old_root = tmp_path / "old-source-verifications"
    response = {"id": 701, "html_url": source_uri}
    verifier.capture_audit_source_verifications(
        audit_request_plan=old_plan_path,
        output_root=old_root,
        repo_root=tmp_path,
        captured_at=CAPTURED_AT,
        fetch_json=lambda _url: (response, _json_bytes(response)),
    )
    new_request = _audit_request(
        case_id="release-climate-001-description",
        source_id=source_id,
        source_uri=source_uri,
        prompt_sha256="3" * 64,
    )
    new_plan_path = tmp_path / "new-audit-plan.json"
    new_plan_path.write_text(
        _json_text(
            {
                "version": verifier.AUDIT_REQUEST_PLAN_VERSION,
                "claim_class": "audit-requests-only",
                "requests": [new_request],
            }
        ),
        encoding="utf-8",
    )
    output_root = tmp_path / "rebound-source-verifications"

    manifest = verifier.rebind_audit_source_verifications(
        audit_request_plan=new_plan_path,
        source_verification_root=old_root,
        expected_source_verification_sha256=_sha256_bytes(
            (old_root / "source-verifications.v2.json").read_bytes()
        ),
        output_root=output_root,
        repo_root=tmp_path,
    )

    record = manifest["records"][0]
    assert record["audit_request_sha256"] == new_request["audit_request_sha256"]
    assert record["source_custody_sha256"]
    assert record["source_verification_sha256"] == _sha256_bytes(_json_bytes(response))
    assert (output_root / record["source_verification_path"]).read_bytes() == _json_bytes(response)
    assert manifest["audit_request_plan"] == "new-audit-plan.json"
    assert manifest["rebound_from"] == "old-source-verifications/source-verifications.v2.json"


def test_rebind_audit_source_verifications_rejects_tampered_or_divergent_inputs(tmp_path: Path) -> None:
    _module()
    verifier = sys.modules["greenfield_release_audit_verification"]
    source_id = "github-repository:701"
    source_uri = "https://github.com/source701/climate-evidence"
    request = _audit_request(
        case_id="release-climate-001-description",
        source_id=source_id,
        source_uri=source_uri,
    )
    old_plan_path = tmp_path / "old-audit-plan.json"
    old_plan_path.write_text(
        _json_text(
            {
                "version": verifier.AUDIT_REQUEST_PLAN_VERSION,
                "claim_class": "audit-requests-only",
                "requests": [request],
            }
        ),
        encoding="utf-8",
    )
    old_root = tmp_path / "old-source-verifications"
    response = {"id": 701, "html_url": source_uri}
    verifier.capture_audit_source_verifications(
        audit_request_plan=old_plan_path,
        output_root=old_root,
        repo_root=tmp_path,
        captured_at=CAPTURED_AT,
        fetch_json=lambda _url: (response, _json_bytes(response)),
    )
    divergent_request = _audit_request(
        case_id="release-climate-001-description",
        source_id=source_id,
        source_uri="https://github.com/source701/other-evidence",
    )
    divergent_plan_path = tmp_path / "divergent-audit-plan.json"
    divergent_plan_path.write_text(
        _json_text(
            {
                "version": verifier.AUDIT_REQUEST_PLAN_VERSION,
                "claim_class": "audit-requests-only",
                "requests": [divergent_request],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="source custody fingerprint diverges"):
        verifier.rebind_audit_source_verifications(
            audit_request_plan=divergent_plan_path,
            source_verification_root=old_root,
            expected_source_verification_sha256=_sha256_bytes(
                (old_root / "source-verifications.v2.json").read_bytes()
            ),
            output_root=tmp_path / "divergent-output",
            repo_root=tmp_path,
        )

    custody_divergent_request = _audit_request(
        case_id="release-climate-001-description",
        source_id=source_id,
        source_uri=source_uri,
        source_artifact_sha256="4" * 64,
    )
    custody_divergent_plan_path = tmp_path / "custody-divergent-audit-plan.json"
    custody_divergent_plan_path.write_text(
        _json_text(
            {
                "version": verifier.AUDIT_REQUEST_PLAN_VERSION,
                "claim_class": "audit-requests-only",
                "requests": [custody_divergent_request],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="source custody fingerprint diverges"):
        verifier.rebind_audit_source_verifications(
            audit_request_plan=custody_divergent_plan_path,
            source_verification_root=old_root,
            expected_source_verification_sha256=_sha256_bytes(
                (old_root / "source-verifications.v2.json").read_bytes()
            ),
            output_root=tmp_path / "custody-divergent-output",
            repo_root=tmp_path,
        )

    with pytest.raises(RuntimeError, match="prior manifest SHA-256 does not match"):
        verifier.rebind_audit_source_verifications(
            audit_request_plan=old_plan_path,
            source_verification_root=old_root,
            expected_source_verification_sha256="0" * 64,
            output_root=tmp_path / "wrong-manifest-output",
            repo_root=tmp_path,
        )

    manifest = json.loads((old_root / "source-verifications.v2.json").read_text(encoding="utf-8"))
    response_path = old_root / manifest["records"][0]["source_verification_path"]
    response_path.write_text("{}", encoding="utf-8")

    with pytest.raises(RuntimeError, match="response hash does not match"):
        verifier.rebind_audit_source_verifications(
            audit_request_plan=old_plan_path,
            source_verification_root=old_root,
            expected_source_verification_sha256=_sha256_bytes(
                (old_root / "source-verifications.v2.json").read_bytes()
            ),
            output_root=tmp_path / "tampered-output",
            repo_root=tmp_path,
        )

    _assert_no_staging_or_lock(tmp_path / "divergent-output")
    _assert_no_staging_or_lock(tmp_path / "custody-divergent-output")
    _assert_no_staging_or_lock(tmp_path / "wrong-manifest-output")
    _assert_no_staging_or_lock(tmp_path / "tampered-output")


def test_capture_audit_source_verifications_rejects_remote_identity_mismatch(tmp_path: Path) -> None:
    _module()
    verifier = sys.modules["greenfield_release_audit_verification"]
    plan_path = tmp_path / "audit-plan.json"
    plan_path.write_text(
        _json_text(
            {
                "version": verifier.AUDIT_REQUEST_PLAN_VERSION,
                "claim_class": "audit-requests-only",
                "requests": [
                    _audit_request(
                        case_id="release-climate-001-description",
                        source_id="github-repository:701",
                        source_uri="https://github.com/source701/climate-evidence",
                    )
                ],
            }
        ),
        encoding="utf-8",
    )
    output_root = tmp_path / "source-verifications"
    response = {"id": 702, "html_url": "https://github.com/source702/climate-evidence"}

    with pytest.raises(RuntimeError, match="does not match source ID"):
        verifier.capture_audit_source_verifications(
            audit_request_plan=plan_path,
            output_root=output_root,
            repo_root=tmp_path,
            captured_at=CAPTURED_AT,
            fetch_json=lambda _url: (response, _json_bytes(response)),
        )

    _assert_no_staging_or_lock(output_root)


def test_audit_writer_binds_explicit_review_results_to_verified_source_records(tmp_path: Path) -> None:
    module = _module()
    case_file, case, request, plan_path, verification_root, writer = _prepared_single_audit(module, tmp_path)
    results_path = tmp_path / "review-results.json"
    results_path.write_text(
        _json_text(
            {
                "version": writer.AUDIT_REVIEW_RESULTS_VERSION,
                "claim_class": writer.AUDIT_REVIEW_RESULTS_CLAIM_CLASS,
                "reviews": [_approved_review(case.case_id, request["audit_request_sha256"])],
            }
        ),
        encoding="utf-8",
    )
    audit_root = tmp_path / "audit-bundle"

    bundle = writer.write_release_audit_bundle(
        source_case_file=case_file,
        audit_request_plan=plan_path,
        source_verification_root=verification_root,
        review_results_file=results_path,
        output_root=audit_root,
        repo_root=tmp_path,
    )
    provenance = sys.modules["greenfield_matrix_corpus_provenance"]
    audits = provenance.load_release_audit_file(
        audit_root / writer.AUDIT_BUNDLE_FILENAME,
        repo_root=tmp_path,
    )
    evaluation = provenance.evaluate_release_corpus((case,), audits, repo_root=tmp_path)

    assert bundle["claim_class"] == "operator-supplied-hash-bound-review-evidence"
    assert len(audits) == 1
    assert not any(f"release audit `{case.case_id}`" in issue for issue in evaluation.issues)


def test_audit_writer_binds_edited_intent_hash_into_the_reviewed_record(tmp_path: Path) -> None:
    module = _module()
    edit = "# Edited Intent\n\n## First Complete Path\nAn operator records one evidence-backed decision."
    case_file, case, request, plan_path, verification_root, writer = _prepared_single_audit(
        module,
        tmp_path,
        confirmed_intent_markdown=edit,
    )
    results_path = tmp_path / "review-results.json"
    results_path.write_text(
        _json_text(
            {
                "version": writer.AUDIT_REVIEW_RESULTS_VERSION,
                "claim_class": writer.AUDIT_REVIEW_RESULTS_CLAIM_CLASS,
                "reviews": [_approved_review(case.case_id, request["audit_request_sha256"])],
            }
        ),
        encoding="utf-8",
    )

    bundle = writer.write_release_audit_bundle(
        source_case_file=case_file,
        audit_request_plan=plan_path,
        source_verification_root=verification_root,
        review_results_file=results_path,
        output_root=tmp_path / "audit-bundle",
        repo_root=tmp_path,
    )

    expected_hash = hashlib.sha256(edit.encode("utf-8")).hexdigest()
    assert bundle["audits"][0]["confirmed_intent_sha256"] == expected_hash
    evidence_path = tmp_path / bundle["audits"][0]["review_evidence_path"]
    assert json.loads(evidence_path.read_text(encoding="utf-8"))["confirmed_intent_sha256"] == expected_hash


@pytest.mark.parametrize(
    "trail_field",
    ("source_case_file", "audit_request_plan", "source_verifications", "review_results"),
)
def test_audit_loader_rejects_a_tampered_trail_reference(tmp_path: Path, trail_field: str) -> None:
    module = _module()
    case_file, case, request, plan_path, verification_root, writer = _prepared_single_audit(module, tmp_path)
    results_path = tmp_path / "review-results.json"
    results_path.write_text(
        _json_text(
            {
                "version": writer.AUDIT_REVIEW_RESULTS_VERSION,
                "claim_class": writer.AUDIT_REVIEW_RESULTS_CLAIM_CLASS,
                "reviews": [_approved_review(case.case_id, request["audit_request_sha256"])],
            }
        ),
        encoding="utf-8",
    )
    audit_root = tmp_path / "audit-bundle"
    writer.write_release_audit_bundle(
        source_case_file=case_file,
        audit_request_plan=plan_path,
        source_verification_root=verification_root,
        review_results_file=results_path,
        output_root=audit_root,
        repo_root=tmp_path,
    )
    bundle_path = audit_root / writer.AUDIT_BUNDLE_FILENAME
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    bundle[f"{trail_field}_sha256"] = "a" * 64
    bundle_path.write_text(_json_text(bundle), encoding="utf-8")
    provenance = sys.modules["greenfield_matrix_corpus_provenance"]

    with pytest.raises(RuntimeError, match=f"{trail_field}_sha256 does not match {trail_field}"):
        provenance.load_release_audit_file(bundle_path, repo_root=tmp_path)


def test_audit_loader_rejects_a_review_semantic_claim_that_diverges_from_hash_bound_evidence(
    tmp_path: Path,
) -> None:
    module = _module()
    case_file, case, request, plan_path, verification_root, writer = _prepared_single_audit(module, tmp_path)
    results_path = tmp_path / "review-results.json"
    results_path.write_text(
        _json_text(
            {
                "version": writer.AUDIT_REVIEW_RESULTS_VERSION,
                "claim_class": writer.AUDIT_REVIEW_RESULTS_CLAIM_CLASS,
                "reviews": [_approved_review(case.case_id, request["audit_request_sha256"])],
            }
        ),
        encoding="utf-8",
    )
    audit_root = tmp_path / "audit-bundle"
    bundle = writer.write_release_audit_bundle(
        source_case_file=case_file,
        audit_request_plan=plan_path,
        source_verification_root=verification_root,
        review_results_file=results_path,
        output_root=audit_root,
        repo_root=tmp_path,
    )
    result_payload = json.loads(results_path.read_text(encoding="utf-8"))
    result_payload["reviews"][0]["rationale"] = "A different review claim."
    results_path.write_text(_json_text(result_payload), encoding="utf-8")
    bundle_path = audit_root / writer.AUDIT_BUNDLE_FILENAME
    bundle_payload = json.loads(bundle_path.read_text(encoding="utf-8"))
    bundle_payload["review_results_sha256"] = _sha256_bytes(results_path.read_bytes())
    bundle_path.write_text(_json_text(bundle_payload), encoding="utf-8")
    provenance = sys.modules["greenfield_matrix_corpus_provenance"]

    with pytest.raises(RuntimeError, match="review results and evidence diverge on rationale"):
        provenance.load_release_audit_file(bundle_path, repo_root=tmp_path)


def test_audit_loader_rejects_a_request_row_that_no_longer_matches_its_own_hash(tmp_path: Path) -> None:
    module = _module()
    case_file, case, request, plan_path, verification_root, writer = _prepared_single_audit(module, tmp_path)
    results_path = tmp_path / "review-results.json"
    results_path.write_text(
        _json_text(
            {
                "version": writer.AUDIT_REVIEW_RESULTS_VERSION,
                "claim_class": writer.AUDIT_REVIEW_RESULTS_CLAIM_CLASS,
                "reviews": [_approved_review(case.case_id, request["audit_request_sha256"])],
            }
        ),
        encoding="utf-8",
    )
    audit_root = tmp_path / "audit-bundle"
    bundle = writer.write_release_audit_bundle(
        source_case_file=case_file,
        audit_request_plan=plan_path,
        source_verification_root=verification_root,
        review_results_file=results_path,
        output_root=audit_root,
        repo_root=tmp_path,
    )
    request_payload = json.loads(plan_path.read_text(encoding="utf-8"))
    request_payload["requests"][0]["stressors"] = ["mutated-request-only-stressor"]
    plan_path.write_text(_json_text(request_payload), encoding="utf-8")
    bundle_path = audit_root / writer.AUDIT_BUNDLE_FILENAME
    bundle_payload = json.loads(bundle_path.read_text(encoding="utf-8"))
    bundle_payload["audit_request_plan_sha256"] = _sha256_bytes(plan_path.read_bytes())
    bundle_path.write_text(_json_text(bundle_payload), encoding="utf-8")
    provenance = sys.modules["greenfield_matrix_corpus_provenance"]

    with pytest.raises(RuntimeError, match="request plan does not self-bind audit_request_sha256"):
        provenance.load_release_audit_file(bundle_path, repo_root=tmp_path)


@pytest.mark.parametrize(
    ("trail_field", "rows_field", "expected_message"),
    (
        (
            "source_verifications",
            "records",
            "source verification manifest case IDs must match audit records",
        ),
        ("review_results", "reviews", "review results case IDs must match audit records"),
    ),
)
def test_audit_loader_rejects_hash_bound_trails_that_do_not_describe_the_audited_cases(
    tmp_path: Path,
    trail_field: str,
    rows_field: str,
    expected_message: str,
) -> None:
    module = _module()
    case_file, case, request, plan_path, verification_root, writer = _prepared_single_audit(module, tmp_path)
    results_path = tmp_path / "review-results.json"
    results_path.write_text(
        _json_text(
            {
                "version": writer.AUDIT_REVIEW_RESULTS_VERSION,
                "claim_class": writer.AUDIT_REVIEW_RESULTS_CLAIM_CLASS,
                "reviews": [_approved_review(case.case_id, request["audit_request_sha256"])],
            }
        ),
        encoding="utf-8",
    )
    audit_root = tmp_path / "audit-bundle"
    bundle = writer.write_release_audit_bundle(
        source_case_file=case_file,
        audit_request_plan=plan_path,
        source_verification_root=verification_root,
        review_results_file=results_path,
        output_root=audit_root,
        repo_root=tmp_path,
    )
    trail_path = tmp_path / bundle[trail_field]
    trail = json.loads(trail_path.read_text(encoding="utf-8"))
    trail[rows_field][0]["case_id"] = "unbound-case"
    trail_path.write_text(_json_text(trail), encoding="utf-8")
    bundle_path = audit_root / writer.AUDIT_BUNDLE_FILENAME
    bundle_payload = json.loads(bundle_path.read_text(encoding="utf-8"))
    bundle_payload[f"{trail_field}_sha256"] = _sha256_bytes(trail_path.read_bytes())
    bundle_path.write_text(_json_text(bundle_payload), encoding="utf-8")
    provenance = sys.modules["greenfield_matrix_corpus_provenance"]

    with pytest.raises(RuntimeError, match=expected_message):
        provenance.load_release_audit_file(bundle_path, repo_root=tmp_path)


def test_audit_loader_rejects_boolean_verification_record_count(tmp_path: Path) -> None:
    module = _module()
    case_file, case, request, plan_path, verification_root, writer = _prepared_single_audit(module, tmp_path)
    results_path = tmp_path / "review-results.json"
    results_path.write_text(
        _json_text(
            {
                "version": writer.AUDIT_REVIEW_RESULTS_VERSION,
                "claim_class": writer.AUDIT_REVIEW_RESULTS_CLAIM_CLASS,
                "reviews": [_approved_review(case.case_id, request["audit_request_sha256"])],
            }
        ),
        encoding="utf-8",
    )
    audit_root = tmp_path / "audit-bundle"
    bundle = writer.write_release_audit_bundle(
        source_case_file=case_file,
        audit_request_plan=plan_path,
        source_verification_root=verification_root,
        review_results_file=results_path,
        output_root=audit_root,
        repo_root=tmp_path,
    )
    verification_manifest = tmp_path / bundle["source_verifications"]
    verification_payload = json.loads(verification_manifest.read_text(encoding="utf-8"))
    verification_payload["record_count"] = True
    verification_manifest.write_text(_json_text(verification_payload), encoding="utf-8")
    bundle_path = audit_root / writer.AUDIT_BUNDLE_FILENAME
    bundle_payload = json.loads(bundle_path.read_text(encoding="utf-8"))
    bundle_payload["source_verifications_sha256"] = _sha256_bytes(verification_manifest.read_bytes())
    bundle_path.write_text(_json_text(bundle_payload), encoding="utf-8")
    provenance = sys.modules["greenfield_matrix_corpus_provenance"]

    with pytest.raises(RuntimeError, match="record_count does not match records"):
        provenance.load_release_audit_file(bundle_path, repo_root=tmp_path)


def test_audit_loader_rejects_a_source_verification_custody_fingerprint_mismatch(tmp_path: Path) -> None:
    module = _module()
    case_file, case, request, plan_path, verification_root, writer = _prepared_single_audit(module, tmp_path)
    results_path = tmp_path / "review-results.json"
    results_path.write_text(
        _json_text(
            {
                "version": writer.AUDIT_REVIEW_RESULTS_VERSION,
                "claim_class": writer.AUDIT_REVIEW_RESULTS_CLAIM_CLASS,
                "reviews": [_approved_review(case.case_id, request["audit_request_sha256"])],
            }
        ),
        encoding="utf-8",
    )
    audit_root = tmp_path / "audit-bundle"
    bundle = writer.write_release_audit_bundle(
        source_case_file=case_file,
        audit_request_plan=plan_path,
        source_verification_root=verification_root,
        review_results_file=results_path,
        output_root=audit_root,
        repo_root=tmp_path,
    )
    verification_manifest = tmp_path / bundle["source_verifications"]
    verification_payload = json.loads(verification_manifest.read_text(encoding="utf-8"))
    verification_payload["records"][0]["source_custody_sha256"] = "0" * 64
    verification_manifest.write_text(_json_text(verification_payload), encoding="utf-8")
    bundle_path = audit_root / writer.AUDIT_BUNDLE_FILENAME
    bundle_payload = json.loads(bundle_path.read_text(encoding="utf-8"))
    bundle_payload["source_verifications_sha256"] = _sha256_bytes(verification_manifest.read_bytes())
    bundle_path.write_text(_json_text(bundle_payload), encoding="utf-8")
    provenance = sys.modules["greenfield_matrix_corpus_provenance"]

    with pytest.raises(RuntimeError, match="diverges on source_custody_sha256"):
        provenance.load_release_audit_file(bundle_path, repo_root=tmp_path)


@pytest.mark.parametrize(
    ("trail_field", "misleading_claim_class"),
    (
        ("source_case_file", "source-provenanced-release"),
        ("audit_request_plan", "third-party-attested-review-requests"),
        ("source_verifications", "independent-third-party-attestation"),
        ("review_results", "independent-human-review-results"),
    ),
)
def test_audit_loader_rejects_a_misleading_trail_claim_class(
    tmp_path: Path,
    trail_field: str,
    misleading_claim_class: str,
) -> None:
    module = _module()
    case_file, case, request, plan_path, verification_root, writer = _prepared_single_audit(module, tmp_path)
    results_path = tmp_path / "review-results.json"
    results_path.write_text(
        _json_text(
            {
                "version": writer.AUDIT_REVIEW_RESULTS_VERSION,
                "claim_class": writer.AUDIT_REVIEW_RESULTS_CLAIM_CLASS,
                "reviews": [_approved_review(case.case_id, request["audit_request_sha256"])],
            }
        ),
        encoding="utf-8",
    )
    audit_root = tmp_path / "audit-bundle"
    bundle = writer.write_release_audit_bundle(
        source_case_file=case_file,
        audit_request_plan=plan_path,
        source_verification_root=verification_root,
        review_results_file=results_path,
        output_root=audit_root,
        repo_root=tmp_path,
    )
    trail_path = tmp_path / bundle[trail_field]
    trail = json.loads(trail_path.read_text(encoding="utf-8"))
    trail["claim_class"] = misleading_claim_class
    trail_path.write_text(_json_text(trail), encoding="utf-8")
    bundle_path = audit_root / writer.AUDIT_BUNDLE_FILENAME
    persisted_bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    persisted_bundle[f"{trail_field}_sha256"] = _sha256_bytes(trail_path.read_bytes())
    bundle_path.write_text(_json_text(persisted_bundle), encoding="utf-8")
    provenance = sys.modules["greenfield_matrix_corpus_provenance"]

    with pytest.raises(RuntimeError, match=f"{trail_field} must declare claim_class"):
        provenance.load_release_audit_file(bundle_path, repo_root=tmp_path)


@pytest.mark.parametrize(
    ("trail_field", "misleading_claim_class", "expected_message"),
    (
        ("audit_request_plan", "third-party-attested-review-requests", "requests-only claim class"),
        ("source_verifications", "independent-third-party-attestation", "verification-only claim class"),
    ),
)
def test_audit_writer_rejects_a_misleading_input_trail_claim_class(
    tmp_path: Path,
    trail_field: str,
    misleading_claim_class: str,
    expected_message: str,
) -> None:
    module = _module()
    case_file, case, request, plan_path, verification_root, writer = _prepared_single_audit(module, tmp_path)
    results_path = tmp_path / "review-results.json"
    results_path.write_text(
        _json_text(
            {
                "version": writer.AUDIT_REVIEW_RESULTS_VERSION,
                "claim_class": writer.AUDIT_REVIEW_RESULTS_CLAIM_CLASS,
                "reviews": [_approved_review(case.case_id, request["audit_request_sha256"])],
            }
        ),
        encoding="utf-8",
    )
    trail_path = plan_path if trail_field == "audit_request_plan" else verification_root / "source-verifications.v2.json"
    trail = json.loads(trail_path.read_text(encoding="utf-8"))
    trail["claim_class"] = misleading_claim_class
    trail_path.write_text(_json_text(trail), encoding="utf-8")

    with pytest.raises(RuntimeError, match=expected_message):
        writer.write_release_audit_bundle(
            source_case_file=case_file,
            audit_request_plan=plan_path,
            source_verification_root=verification_root,
            review_results_file=results_path,
            output_root=tmp_path / "audit-bundle",
            repo_root=tmp_path,
        )


def test_capture_audit_source_verifications_rejects_an_unsafe_case_id(tmp_path: Path) -> None:
    _module()
    verifier = sys.modules["greenfield_release_audit_verification"]
    evidence = sys.modules["greenfield_matrix_release_audit_evidence"]
    request = _audit_request(
        case_id="../../escaped",
        source_id="github-repository:701",
        source_uri="https://github.com/source701/climate-evidence",
    )
    request["audit_request_sha256"] = evidence.audit_request_sha256(request)
    plan_path = tmp_path / "audit-plan.json"
    plan_path.write_text(
        _json_text(
            {
                "version": verifier.AUDIT_REQUEST_PLAN_VERSION,
                "claim_class": "audit-requests-only",
                "requests": [request],
            }
        ),
        encoding="utf-8",
    )
    output_root = tmp_path / "source-verifications"

    with pytest.raises(RuntimeError, match="must use safe case IDs"):
        verifier.capture_audit_source_verifications(
            audit_request_plan=plan_path,
            output_root=output_root,
            repo_root=tmp_path,
            captured_at=CAPTURED_AT,
            fetch_json=lambda _url: ({"id": 701, "html_url": "https://github.com/source701/climate-evidence"}, b"{}"),
        )

    _assert_no_staging_or_lock(output_root)
    assert not (tmp_path / "escaped.json").exists()


def test_audit_writer_rejects_a_review_result_not_bound_to_its_request(tmp_path: Path) -> None:
    module = _module()
    case_file, case, request, plan_path, verification_root, writer = _prepared_single_audit(module, tmp_path)
    results_path = tmp_path / "review-results.json"
    review = _approved_review(case.case_id, "0" * 64)
    results_path.write_text(
        _json_text(
            {
                "version": writer.AUDIT_REVIEW_RESULTS_VERSION,
                "claim_class": writer.AUDIT_REVIEW_RESULTS_CLAIM_CLASS,
                "reviews": [review],
            }
        ),
        encoding="utf-8",
    )
    output_root = tmp_path / "audit-bundle"

    with pytest.raises(RuntimeError, match="does not bind the audit request"):
        writer.write_release_audit_bundle(
            source_case_file=case_file,
            audit_request_plan=plan_path,
            source_verification_root=verification_root,
            review_results_file=results_path,
            output_root=output_root,
            repo_root=tmp_path,
        )

    _assert_no_staging_or_lock(output_root)
    assert request["audit_request_sha256"] != review["audit_request_sha256"]


def test_audit_writer_rejects_a_review_replayed_after_the_case_prompt_changes(tmp_path: Path) -> None:
    module = _module()
    case_file, case, request, plan_path, verification_root, writer = _prepared_single_audit(module, tmp_path)
    case_payload = json.loads(case_file.read_text(encoding="utf-8"))
    case_payload["cases"][0]["prompt"] = (
        "Create a materially different product for "
        f"{case.required_terms[0]} from source {case.leakage_terms[0]} after review approval. "
        + " ".join(case.required_terms[1:])
    )
    case_payload["cases"][0]["provenance"]["derived_prompt_sha256"] = _sha256_bytes(
        case_payload["cases"][0]["prompt"].encode("utf-8")
    )
    case_file.write_text(_json_text(case_payload), encoding="utf-8")
    results_path = tmp_path / "review-results.json"
    results_path.write_text(
        _json_text(
            {
                "version": writer.AUDIT_REVIEW_RESULTS_VERSION,
                "claim_class": writer.AUDIT_REVIEW_RESULTS_CLAIM_CLASS,
                "reviews": [_approved_review(case.case_id, request["audit_request_sha256"])],
            }
        ),
        encoding="utf-8",
    )
    output_root = tmp_path / "audit-bundle"

    with pytest.raises(RuntimeError, match="case provenance diverge on prompt_sha256"):
        writer.write_release_audit_bundle(
            source_case_file=case_file,
            audit_request_plan=plan_path,
            source_verification_root=verification_root,
            review_results_file=results_path,
            output_root=output_root,
            repo_root=tmp_path,
        )

    _assert_no_staging_or_lock(output_root)


@pytest.mark.parametrize("field", ("review_context_label", "review_method", "reviewed_on", "rationale"))
def test_audit_writer_requires_each_review_result_field(tmp_path: Path, field: str) -> None:
    module = _module()
    case_file, case, request, plan_path, verification_root, writer = _prepared_single_audit(module, tmp_path)
    review = _approved_review(case.case_id, request["audit_request_sha256"])
    review.pop(field)
    results_path = tmp_path / "review-results.json"
    results_path.write_text(
        _json_text(
            {
                "version": writer.AUDIT_REVIEW_RESULTS_VERSION,
                "claim_class": writer.AUDIT_REVIEW_RESULTS_CLAIM_CLASS,
                "reviews": [review],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match=f"review result lacks {field}"):
        writer.write_release_audit_bundle(
            source_case_file=case_file,
            audit_request_plan=plan_path,
            source_verification_root=verification_root,
            review_results_file=results_path,
            output_root=tmp_path / "audit-bundle",
            repo_root=tmp_path,
        )
