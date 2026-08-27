from __future__ import annotations

import base64
from collections.abc import Mapping, Sequence
from dataclasses import fields, is_dataclass
from pathlib import Path
from typing import Any

from tests.unit.runtime.greenfield_proposal_fixtures import compiled_graph_transaction


def _structured_strings(value: Any, *, owner: str = "") -> tuple[tuple[str, str], ...]:
    rows: list[tuple[str, str]] = []
    if is_dataclass(value) and not isinstance(value, type):
        for field in fields(value):
            rows.extend(
                _structured_strings(
                    getattr(value, field.name),
                    owner=f"{owner}.{field.name}" if owner else field.name,
                )
            )
    elif isinstance(value, Mapping):
        for key, item in value.items():
            child = f"{owner}.{key}" if owner else str(key)
            rows.extend(_structured_strings(item, owner=child))
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, item in enumerate(value):
            rows.extend(_structured_strings(item, owner=f"{owner}.{index}"))
    elif isinstance(value, Path):
        rows.append((owner, str(value)))
    elif isinstance(value, str):
        rows.append((owner, value))
    return tuple(rows)


def test_prewrite_package_and_after_image_contain_no_ephemeral_repository_paths(
    tmp_path: Path,
) -> None:
    transaction = compiled_graph_transaction(tmp_path)
    package = transaction.prewrite_package
    forbidden_fragments = (
        str(tmp_path),
        "odylith-greenfield-prewrite-",
        "odylith-standard-pipeline-",
    )
    leaked = [
        (owner, value)
        for owner, value in _structured_strings(package)
        if any(fragment in value for fragment in forbidden_fragments)
    ]
    assert leaked == []

    decoded_leaks: list[tuple[str, str]] = []
    for row in package.repository_write_set["after_image"]["files"]:
        data = base64.b64decode(str(row["content_base64"]), validate=True)
        if any(fragment.encode("utf-8") in data for fragment in forbidden_fragments):
            text = data.decode("utf-8", errors="replace")
            position = next(
                text.index(fragment)
                for fragment in forbidden_fragments
                if fragment in text
            )
            decoded_leaks.append(
                (str(row["path"]), text[max(0, position - 80) : position + 240])
            )
    assert decoded_leaks == [], "\n".join(repr(row) for row in decoded_leaks)

    backlog = package.backlog_result
    assert not Path(str(backlog["backlog_index"])).is_absolute()
    assert all(
        not Path(str(row["idea_path"])).is_absolute()
        for row in backlog["created"]
    )
    assert all(
        not Path(str(spec.path)).is_absolute()
        for spec in backlog["_candidate_idea_specs"].values()
    )
    release_target = package.release_target_result or {}
    release_assignment = package.release_assignment_result or {}
    assert not Path(str(release_target["registry_path"])).is_absolute()
    assert not Path(str(release_target["release"]["source_path"])).is_absolute()
    assert not Path(str(release_assignment["event_log_path"])).is_absolute()
    assert not Path(str(release_assignment["release"]["source_path"])).is_absolute()
