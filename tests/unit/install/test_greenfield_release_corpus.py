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
        "Independent automated audit evidence and installed release proof are still required."
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
    assert all(
        case["provenance"]["derived_prompt_sha256"]
        == _sha256_bytes(case["prompt"].encode("utf-8"))
        for case in payload["cases"]
    )
    assert manifest["source_count"] == 2


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

    assert prompt.startswith("Create an accessibility product")
    assert brief.startswith("Project brief for an open-data team")


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

    assert evaluation.summary["case_count"] == 200
    assert evaluation.summary["source_artifact_count"] == 180
    assert evaluation.summary["complete_metamorphic_group_count"] == 20
    assert evaluation.issues
    assert all("audit" in issue for issue in evaluation.issues)


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
        source_capture._fetch_json("https://api.github.com/search/repositories?q=topic%3Aclimate")
