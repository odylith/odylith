"""Capture and verify source-provenanced Greenfield evidence records."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


SOURCE_CAPTURE_VERSION = "odylith.greenfield.release-source-capture.v2"
SOURCE_MANIFEST_VERSION = "odylith.greenfield.release-source-manifest.v2"
SOURCE_MANIFEST_FILENAME = "source-manifest.v2.json"
DEFAULT_ARTIFACTS_PER_FAMILY = 18
GITHUB_SEARCH_API = "https://api.github.com/search/repositories"
GITHUB_USER_AGENT = "odylith-greenfield-release-corpus"


@dataclass(frozen=True)
class SourceFamily:
    key: str
    topic: str
    description_evidence_terms: tuple[str, ...] = ()


SOURCE_FAMILIES = (
    SourceFamily(
        "climate", "climate", ("climate", "weather", "energy", "emission", "carbon", "environment")
    ),
    SourceFamily(
        "healthcare", "healthcare", ("health", "medical", "clinical", "patient", "hospital", "disease")
    ),
    SourceFamily(
        "education", "education", ("education", "learning", "student", "teaching", "school", "course")
    ),
    SourceFamily(
        "civic-tech", "civic-tech", ("civic", "government", "public", "municipal", "election", "democracy")
    ),
    SourceFamily(
        "mobility", "transportation", ("transport", "transit", "traffic", "mobility", "vehicle", "route")
    ),
    SourceFamily(
        "agriculture", "agriculture", ("agriculture", "farm", "crop", "soil", "food", "irrigation")
    ),
    SourceFamily(
        "open-data", "open-data", ("open data", "dataset", "catalog", "geospatial", "statistics", "records")
    ),
    SourceFamily(
        "accessibility", "accessibility", ("accessibility", "accessible", "a11y", "screen reader", "assistive", "disability")
    ),
    SourceFamily(
        "security", "security", ("security", "secure", "vulnerability", "threat", "privacy", "crypt")
    ),
    SourceFamily(
        "research", "research", ("research", "paper", "study", "science", "academic", "experiment")
    ),
)


@dataclass(frozen=True)
class FetchedJson:
    payload: Mapping[str, Any]
    body: bytes
    headers: Mapping[str, str]


FetchJson = Callable[[str], FetchedJson | tuple[Mapping[str, Any], bytes]]


def capture_release_sources(
    *,
    output_root: Path,
    query_specs: Sequence[SourceFamily] = SOURCE_FAMILIES,
    artifacts_per_family: int = DEFAULT_ARTIFACTS_PER_FAMILY,
    retrieved_on: str | None = None,
    captured_at: str | None = None,
    fetch_json: FetchJson | None = None,
) -> dict[str, Any]:
    """Capture local evidence envelopes with self-consistent source identifiers."""

    output = Path(output_root).expanduser().resolve()
    if output.exists():
        raise RuntimeError(f"release source output already exists: {output}")
    if int(artifacts_per_family) <= 0:
        raise ValueError("artifacts_per_family must be positive")
    if not query_specs:
        raise ValueError("at least one source family is required")
    validate_source_families(query_specs)
    fetch = fetch_json or fetch_github_json
    captured_at_token = validated_timestamp(captured_at or now_timestamp())
    date_token = validated_date(retrieved_on or captured_at_token[:10])
    if date_token != captured_at_token[:10]:
        raise ValueError("retrieved_on must match the UTC date in captured_at")
    output.parent.mkdir(parents=True, exist_ok=True)
    lock_path, lock_fd = reserve_output_lock(output)
    staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.staging-", dir=output.parent))
    try:
        sources_dir = staging / "sources"
        sources_dir.mkdir(parents=True)
        responses_dir = staging / "responses"
        responses_dir.mkdir(parents=True)
        selected: list[dict[str, Any]] = []
        seen_repositories: set[str] = set()
        for family in query_specs:
            request_url = search_url(family)
            fetched = normalize_fetch_result(fetch(request_url))
            candidates = select_repositories(
                payload=fetched.payload,
                family=family,
                limit=int(artifacts_per_family),
                seen_repositories=seen_repositories,
            )
            if len(candidates) != int(artifacts_per_family):
                raise RuntimeError(
                    f"source family `{family.key}` yielded {len(candidates)} eligible repositories; "
                    f"need {artifacts_per_family}"
                )
            response_sha256 = sha256_bytes(fetched.body)
            response_relative = (Path("responses") / f"{family.key}.json").as_posix()
            response_path = responses_dir / f"{family.key}.json"
            response_path.write_bytes(fetched.body)
            sync_file(response_path)
            for ordinal, (response_item_index, repository) in enumerate(candidates, start=1):
                artifact = capture_artifact(
                    family=family,
                    repository=repository,
                    captured_at=captured_at_token,
                    request_url=request_url,
                    response_path=response_relative,
                    response_sha256=response_sha256,
                    response_headers=fetched.headers,
                    selection_index=ordinal,
                    response_item_index=response_item_index,
                )
                file_name = f"{family.key}-{ordinal:02d}-{slug(str(repository['full_name']))}.json"
                artifact_path = sources_dir / file_name
                artifact_text = json_text(artifact)
                artifact_path.write_text(artifact_text, encoding="utf-8")
                sync_file(artifact_path)
                selected.append(
                    {
                        "source_id": artifact["source_id"],
                        "source_uri": artifact["source_uri"],
                        "source_family": family.key,
                        "artifact_path": (Path("sources") / file_name).as_posix(),
                        "artifact_sha256": sha256_text(artifact_text),
                        "search_response_path": response_relative,
                        "search_response_sha256": response_sha256,
                        "selection_index": ordinal,
                        "response_item_index": response_item_index,
                        "retrieved_on": date_token,
                    }
                )
        manifest = {
            "version": SOURCE_MANIFEST_VERSION,
            "retrieved_on": date_token,
            "captured_at": captured_at_token,
            "source_capture_version": SOURCE_CAPTURE_VERSION,
            "source_family_count": len(query_specs),
            "artifacts_per_family": int(artifacts_per_family),
            "source_count": len(selected),
            "families": [asdict(family) for family in query_specs],
            "sources": selected,
        }
        manifest_path = staging / SOURCE_MANIFEST_FILENAME
        manifest_path.write_text(json_text(manifest), encoding="utf-8")
        sync_file(manifest_path)
        sync_directory(staging)
        if output.exists():
            raise RuntimeError(f"release source output appeared during capture: {output}")
        staging.replace(output)
        sync_directory(output.parent)
    finally:
        shutil.rmtree(staging, ignore_errors=True)
        release_output_lock(lock_path, lock_fd)
    return manifest


def load_verified_sources(
    manifest: Mapping[str, Any], manifest_root: Path, repo_root: Path
) -> dict[str, list[dict[str, Any]]]:
    """Return source records only after every retained-file binding verifies."""

    families = manifest_families(manifest)
    manifest_date = validated_date(single_line(manifest.get("retrieved_on")))
    manifest_captured_at = validated_timestamp(single_line(manifest.get("captured_at")))
    rows = manifest.get("sources")
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes, bytearray)):
        raise RuntimeError("source manifest must define a sources array")
    if int(manifest.get("source_count") or -1) != len(rows):
        raise RuntimeError("source manifest source_count does not match sources")
    grouped: dict[str, list[dict[str, Any]]] = {}
    seen_source_ids: set[str] = set()
    seen_source_uris: set[str] = set()
    seen_artifacts: set[str] = set()
    selection_indexes: dict[str, set[int]] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            raise RuntimeError("source manifest contains a non-object source record")
        artifact_relative = single_line(row.get("artifact_path"))
        artifact_path = contained_path(manifest_root, artifact_relative, "source artifact")
        artifact_text = artifact_path.read_text(encoding="utf-8")
        if sha256_text(artifact_text) != single_line(row.get("artifact_sha256")):
            raise RuntimeError(f"source artifact hash mismatch: {artifact_relative}")
        artifact = load_json_object(artifact_path)
        if artifact.get("version") != SOURCE_CAPTURE_VERSION:
            raise RuntimeError(f"unsupported source capture version: {artifact_relative}")
        family_key = single_line(row.get("source_family"))
        if family_key not in families or family_key != single_line(artifact.get("source_family")):
            raise RuntimeError(f"source family mismatch: {artifact_relative}")
        if single_line(row.get("source_id")) != single_line(artifact.get("source_id")):
            raise RuntimeError(f"source identity mismatch: {artifact_relative}")
        if single_line(row.get("source_uri")) != single_line(artifact.get("source_uri")):
            raise RuntimeError(f"source URI mismatch: {artifact_relative}")
        if single_line(row.get("retrieved_on")) != manifest_date:
            raise RuntimeError(f"source retrieval date mismatch: {artifact_relative}")
        if single_line(artifact.get("captured_on")) != manifest_date:
            raise RuntimeError(f"source capture date mismatch: {artifact_relative}")
        if single_line(artifact.get("captured_at")) != manifest_captured_at:
            raise RuntimeError(f"source capture timestamp mismatch: {artifact_relative}")
        source_id = single_line(artifact.get("source_id"))
        source_uri = single_line(artifact.get("source_uri"))
        if not source_id or source_id in seen_source_ids:
            raise RuntimeError(f"source manifest repeats source_id: {source_id or artifact_relative}")
        if not source_uri or source_uri in seen_source_uris:
            raise RuntimeError(f"source manifest repeats source_uri: {source_uri or artifact_relative}")
        if artifact_relative in seen_artifacts:
            raise RuntimeError(f"source manifest repeats source artifact: {artifact_relative}")
        validate_capture_binding(
            artifact=artifact,
            row=row,
            family=families[family_key],
            manifest_root=manifest_root,
            artifact_relative=artifact_relative,
        )
        selection_index = row["selection_index"]
        family_selection_indexes = selection_indexes.setdefault(family_key, set())
        if selection_index in family_selection_indexes:
            raise RuntimeError(f"source manifest repeats selection index: {artifact_relative}")
        repository = artifact.get("repository")
        assert isinstance(repository, Mapping)
        seen_source_ids.add(source_id)
        seen_source_uris.add(source_uri)
        seen_artifacts.add(artifact_relative)
        family_selection_indexes.add(selection_index)
        grouped.setdefault(family_key, []).append(
            {
                "artifact": artifact,
                "artifact_path": artifact_path,
                "artifact_relative": repo_relative(artifact_path, repo_root),
                "artifact_sha256": single_line(row.get("artifact_sha256")),
                "repository": dict(repository),
            }
        )
    artifact_count = int(manifest.get("artifacts_per_family") or 0)
    if artifact_count <= 0:
        raise RuntimeError("source manifest artifacts_per_family must be positive")
    for family in families.values():
        if len(grouped.get(family.key, ())) != artifact_count:
            raise RuntimeError(f"source family `{family.key}` does not have {artifact_count} captured artifacts")
        if selection_indexes.get(family.key) != set(range(1, artifact_count + 1)):
            raise RuntimeError(f"source family `{family.key}` has non-contiguous selection indexes")
    return {family: sorted(values, key=lambda item: item["artifact_relative"]) for family, values in grouped.items()}


def write_new_json_atomically(output: Path, payload: Mapping[str, Any], label: str) -> None:
    """Write one new JSON artifact without exposing a partial file to readers."""

    destination = Path(output).expanduser().resolve()
    if destination.exists():
        raise RuntimeError(f"{label} already exists: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    lock_path, lock_fd = reserve_output_lock(destination)
    staging = Path(tempfile.mkdtemp(prefix=f".{destination.name}.staging-", dir=destination.parent))
    try:
        staged_output = staging / destination.name
        staged_output.write_text(json_text(payload), encoding="utf-8")
        sync_file(staged_output)
        if destination.exists():
            raise RuntimeError(f"{label} appeared during write: {destination}")
        staged_output.replace(destination)
        sync_directory(destination.parent)
    finally:
        shutil.rmtree(staging, ignore_errors=True)
        release_output_lock(lock_path, lock_fd)


def search_url(family: SourceFamily) -> str:
    query = f"license:mit fork:false archived:false topic:{family.topic}"
    return GITHUB_SEARCH_API + "?" + urlencode({"q": query, "sort": "stars", "order": "desc", "per_page": 100})


def normalize_fetch_result(value: FetchedJson | tuple[Mapping[str, Any], bytes]) -> FetchedJson:
    if isinstance(value, FetchedJson):
        return value
    if isinstance(value, tuple) and len(value) == 2:
        payload, body = value
        if isinstance(payload, Mapping) and isinstance(body, bytes):
            return FetchedJson(payload=payload, body=body, headers={})
    raise RuntimeError("source fetch must return JSON payload, raw bytes, and optional response headers")


def now_timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def validated_timestamp(value: str) -> str:
    token = single_line(value)
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", token):
        raise ValueError("captured_at must use RFC3339 UTC seconds precision")
    try:
        datetime.fromisoformat(token.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("captured_at is not a valid timestamp") from exc
    return token


def validated_date(value: str) -> str:
    token = single_line(value)
    try:
        date.fromisoformat(token)
    except ValueError as exc:
        raise ValueError("retrieved_on must use ISO date format") from exc
    return token


def validate_source_families(families: Sequence[SourceFamily]) -> None:
    seen_keys: set[str] = set()
    seen_topics: set[str] = set()
    for family in families:
        key = single_line(family.key)
        topic = single_line(family.topic)
        if not re.fullmatch(r"[a-z0-9-]+", key) or not re.fullmatch(r"[a-z0-9-]+", topic):
            raise ValueError("source family keys and topics must be lowercase ASCII tokens")
        if key in seen_keys or topic in seen_topics:
            raise ValueError("source family keys and topics must be unique")
        if any(
            not term or not term.isascii() or len(term) < 3
            for term in (single_line(term) for term in family.description_evidence_terms)
        ):
            raise ValueError("source family description evidence terms must be non-empty ASCII text")
        seen_keys.add(key)
        seen_topics.add(topic)


def reserve_output_lock(output: Path) -> tuple[Path, int]:
    lock_path = Path(output).with_name(f".{Path(output).name}.lock")
    try:
        fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise RuntimeError(f"release output is already reserved: {output}") from exc
    try:
        os.write(fd, f"pid={os.getpid()}\n".encode("ascii"))
        os.fsync(fd)
    except Exception:
        os.close(fd)
        lock_path.unlink(missing_ok=True)
        raise
    return lock_path, fd


def release_output_lock(lock_path: Path, fd: int) -> None:
    os.close(fd)
    lock_path.unlink(missing_ok=True)


def sync_file(path: Path) -> None:
    with Path(path).open("rb") as handle:
        os.fsync(handle.fileno())


def sync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def fetch_github_json(url: str) -> FetchedJson:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": GITHUB_USER_AGENT,
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token := os.environ.get("GITHUB_TOKEN", "").strip():
        headers["Authorization"] = f"Bearer {token}"
    request = Request(
        url,
        headers=headers,
    )
    try:
        with urlopen(request, timeout=30) as response:  # noqa: S310 - public GitHub API endpoint
            raw = response.read()
            response_headers = {
                key.casefold(): value
                for key in ("date", "etag", "x-github-request-id")
                if (value := response.headers.get(key))
            }
    except HTTPError as exc:
        if exc.code == 403 and exc.headers.get("x-ratelimit-remaining") == "0":
            reset = exc.headers.get("x-ratelimit-reset")
            retry = f" after Unix time {reset}" if reset else " later"
            raise RuntimeError(
                f"GitHub source capture rate limit is exhausted; retry{retry} or set GITHUB_TOKEN."
            ) from exc
        raise RuntimeError(f"GitHub source capture request failed with HTTP {exc.code}: {exc.reason}") from exc
    except URLError as exc:
        raise RuntimeError(f"GitHub source capture request failed: {exc.reason}") from exc
    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, Mapping):
        raise RuntimeError(f"GitHub search response is not a JSON object: {url}")
    return FetchedJson(payload=payload, body=raw, headers=response_headers)


def select_repositories(
    *,
    payload: Mapping[str, Any],
    family: SourceFamily,
    limit: int,
    seen_repositories: set[str],
) -> tuple[tuple[int, dict[str, Any]], ...]:
    items = payload.get("items")
    if not isinstance(items, Sequence) or isinstance(items, (str, bytes, bytearray)):
        raise RuntimeError(f"GitHub search for `{family.key}` did not return repository items")
    selected: list[tuple[int, dict[str, Any]]] = []
    for response_item_index, item in enumerate(items):
        if not isinstance(item, Mapping) or not eligible_for_family(item, family):
            continue
        full_name = str(item["full_name"])
        if full_name.casefold() in seen_repositories:
            continue
        seen_repositories.add(full_name.casefold())
        selected.append((response_item_index, dict(item)))
        if len(selected) == limit:
            return tuple(selected)
    return tuple(selected)


def eligible_repository(repository: Mapping[str, Any]) -> bool:
    full_name = single_line(repository.get("full_name"))
    description = single_line(repository.get("description"))
    html_url = single_line(repository.get("html_url"))
    license_info = repository.get("license")
    topics = repository.get("topics")
    repository_id = repository.get("id")
    node_id = single_line(repository.get("node_id"))
    if not full_name or not description or not html_url or not isinstance(license_info, Mapping):
        return False
    if type(repository_id) is not int or repository_id <= 0 or not node_id:
        return False
    if bool(repository.get("private")) or bool(repository.get("fork")) or bool(repository.get("archived")) or bool(repository.get("disabled")):
        return False
    if str(license_info.get("spdx_id") or "").strip() != "MIT":
        return False
    if not full_name.isascii() or not description.isascii() or len(description) < 24:
        return False
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", full_name):
        return False
    if not re.fullmatch(r"https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/?", html_url):
        return False
    if not isinstance(topics, Sequence) or isinstance(topics, (str, bytes, bytearray)):
        return False
    normalized_topics = [single_line(topic) for topic in topics]
    return bool(
        normalized_topics
        and all(topic and topic.isascii() for topic in normalized_topics)
        and len({topic.casefold() for topic in normalized_topics}) == len(normalized_topics)
    )


def eligible_for_family(repository: Mapping[str, Any], family: SourceFamily) -> bool:
    if not eligible_repository(repository):
        return False
    topics = repository.get("topics")
    assert isinstance(topics, Sequence)
    if family.topic not in {single_line(topic).casefold() for topic in topics}:
        return False
    return not family.description_evidence_terms or bool(
        matched_description_evidence_terms(repository, family)
    )


def matched_description_evidence_terms(
    repository: Mapping[str, Any], family: SourceFamily
) -> tuple[str, ...]:
    description = single_line(repository.get("description")).casefold().replace("-", " ")
    return tuple(
        term
        for term in family.description_evidence_terms
        if term.casefold().replace("-", " ") in description
    )


def capture_artifact(
    *,
    family: SourceFamily,
    repository: Mapping[str, Any],
    captured_at: str,
    request_url: str,
    response_path: str,
    response_sha256: str,
    response_headers: Mapping[str, str],
    selection_index: int,
    response_item_index: int,
) -> dict[str, Any]:
    full_name = single_line(repository.get("full_name"))
    repository_id = repository.get("id")
    license_info = repository.get("license")
    assert type(repository_id) is int
    assert isinstance(license_info, Mapping)
    return {
        "version": SOURCE_CAPTURE_VERSION,
        "captured_at": captured_at,
        "captured_on": captured_at[:10],
        "capture_method": "github-search-repository-metadata-v1",
        "source_id": f"github-repository:{repository_id}",
        "source_uri": single_line(repository.get("html_url")),
        "source_family": family.key,
        "family_description_evidence_terms": list(family.description_evidence_terms),
        "matched_description_evidence_terms": list(
            matched_description_evidence_terms(repository, family)
        ),
        "search_request_url": request_url,
        "search_response_path": response_path,
        "search_response_sha256": response_sha256,
        "search_response_headers": dict(sorted(response_headers.items())),
        "selection_index": selection_index,
        "response_item_index": response_item_index,
        "repository": {
            "id": repository_id,
            "node_id": single_line(repository.get("node_id")),
            "full_name": full_name,
            "name": single_line(repository.get("name")),
            "description": single_line(repository.get("description")),
            "topics": [single_line(topic) for topic in repository.get("topics", ())],
            "default_branch": single_line(repository.get("default_branch")),
            "pushed_at": single_line(repository.get("pushed_at")),
            "license": {
                "key": single_line(license_info.get("key")),
                "name": single_line(license_info.get("name")),
                "spdx_id": single_line(license_info.get("spdx_id")),
            },
        },
        "rights_notice": (
            "GitHub metadata reports repository SPDX MIT. This is not consent or copyright clearance "
            "for repository metadata reused as evidence."
        ),
    }


def manifest_families(manifest: Mapping[str, Any]) -> dict[str, SourceFamily]:
    values = manifest.get("families")
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes, bytearray)):
        raise RuntimeError("source manifest must define source families")
    families: list[SourceFamily] = []
    for value in values:
        if not isinstance(value, Mapping):
            raise RuntimeError("source manifest contains an invalid source family")
        terms = value.get("description_evidence_terms", ())
        if not isinstance(terms, Sequence) or isinstance(terms, (str, bytes, bytearray)):
            raise RuntimeError("source manifest contains invalid description evidence terms")
        families.append(
            SourceFamily(
                single_line(value.get("key")),
                single_line(value.get("topic")),
                tuple(single_line(term) for term in terms),
            )
        )
    validate_source_families(families)
    if int(manifest.get("source_family_count") or -1) != len(families):
        raise RuntimeError("source manifest source_family_count does not match families")
    return {family.key: family for family in families}


def validate_capture_binding(
    *,
    artifact: Mapping[str, Any],
    row: Mapping[str, Any],
    family: SourceFamily,
    manifest_root: Path,
    artifact_relative: str,
) -> None:
    response_relative = single_line(row.get("search_response_path"))
    response_sha256 = single_line(row.get("search_response_sha256"))
    selection_index = row.get("selection_index")
    response_item_index = row.get("response_item_index")
    if response_relative != single_line(artifact.get("search_response_path")):
        raise RuntimeError(f"search response path mismatch: {artifact_relative}")
    if response_sha256 != single_line(artifact.get("search_response_sha256")):
        raise RuntimeError(f"search response hash mismatch: {artifact_relative}")
    if type(selection_index) is not int or selection_index <= 0:
        raise RuntimeError(f"source selection index is invalid: {artifact_relative}")
    if type(response_item_index) is not int or response_item_index < 0:
        raise RuntimeError(f"source response item index is invalid: {artifact_relative}")
    if selection_index != artifact.get("selection_index"):
        raise RuntimeError(f"source selection index mismatch: {artifact_relative}")
    if response_item_index != artifact.get("response_item_index"):
        raise RuntimeError(f"source response item index mismatch: {artifact_relative}")
    response_path = contained_path(manifest_root, response_relative, "search response")
    response_bytes = response_path.read_bytes()
    if sha256_bytes(response_bytes) != response_sha256:
        raise RuntimeError(f"search response file hash mismatch: {response_relative}")
    try:
        response = json.loads(response_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"search response is not valid UTF-8 JSON: {response_relative}") from exc
    if not isinstance(response, Mapping):
        raise RuntimeError(f"search response is not a JSON object: {response_relative}")
    request_url = search_url(family)
    if single_line(artifact.get("search_request_url")) != request_url:
        raise RuntimeError(f"search request does not match source family: {artifact_relative}")
    repository = artifact.get("repository")
    if not isinstance(repository, Mapping):
        raise RuntimeError(f"source capture lacks repository metadata: {artifact_relative}")
    response_item = response_repository_at(response, response_item_index)
    if response_item is None or not eligible_for_family(response_item, family):
        raise RuntimeError(f"source capture has no eligible response repository: {artifact_relative}")
    expected = capture_artifact(
        family=family,
        repository=response_item,
        captured_at=validated_timestamp(single_line(artifact.get("captured_at"))),
        request_url=request_url,
        response_path=response_relative,
        response_sha256=response_sha256,
        response_headers=response_headers(artifact.get("search_response_headers")),
        selection_index=selection_index,
        response_item_index=response_item_index,
    )
    if dict(artifact) != expected:
        raise RuntimeError(f"source capture fields diverge from retained response: {artifact_relative}")


def response_repository_at(response: Mapping[str, Any], index: int) -> Mapping[str, Any] | None:
    items = response.get("items")
    if not isinstance(items, Sequence) or isinstance(items, (str, bytes, bytearray)):
        return None
    if index >= len(items) or not isinstance(items[index], Mapping):
        return None
    return items[index]


def response_headers(value: Any) -> dict[str, str]:
    if not isinstance(value, Mapping):
        raise RuntimeError("source capture must retain response headers as an object")
    allowed = {"date", "etag", "x-github-request-id"}
    headers: dict[str, str] = {}
    for raw_key, raw_value in value.items():
        key = single_line(raw_key).casefold()
        header_value = single_line(raw_value)
        if key not in allowed or not header_value:
            raise RuntimeError("source capture contains invalid response header evidence")
        headers[key] = header_value
    return dict(sorted(headers.items()))


def load_json_object(path: Path) -> Mapping[str, Any]:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except OSError as exc:
        raise RuntimeError(f"unable to read {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(payload, Mapping):
        raise RuntimeError(f"JSON payload must be an object: {path}")
    return payload


def repo_relative(path: Path, repo_root: Path) -> str:
    try:
        return Path(path).resolve().relative_to(repo_root).as_posix()
    except ValueError as exc:
        raise RuntimeError(f"artifact must live under repository root: {path}") from exc


def contained_path(root: Path, relative: str, label: str) -> Path:
    if not relative:
        raise RuntimeError(f"{label} path is required")
    path = (root / relative).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise RuntimeError(f"{label} escapes manifest root: {relative}") from exc
    return path


def json_text(value: Mapping[str, Any]) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n"


def sha256_text(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def single_line(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def slug(value: str) -> str:
    token = re.sub(r"[^a-z0-9]+", "-", str(value).casefold()).strip("-")
    return token or "source"
