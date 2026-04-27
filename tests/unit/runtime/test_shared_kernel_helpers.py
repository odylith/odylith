from __future__ import annotations

from pathlib import Path

import pytest

from odylith.common.json_objects import JsonObjectLoadError
from odylith.common.json_objects import load_json_object
from odylith.common.json_objects import load_json_object_or_none
from odylith.common.json_objects import read_json_object
from odylith.common.release_text import normalize_release_text
from odylith.common.release_text import normalize_release_version


def test_read_json_object_loads_dict_payload(tmp_path: Path) -> None:
    path = tmp_path / "payload.json"
    path.write_text('{"status": "ok"}', encoding="utf-8")

    assert read_json_object(path) == {"status": "ok"}


def test_read_json_object_rejects_missing_invalid_and_non_object_payloads(tmp_path: Path) -> None:
    invalid = tmp_path / "invalid.json"
    invalid.write_text("{not-json}", encoding="utf-8")
    not_object = tmp_path / "list.json"
    not_object.write_text('["oops"]', encoding="utf-8")

    with pytest.raises(JsonObjectLoadError) as missing_exc:
        read_json_object(tmp_path / "missing.json")
    assert missing_exc.value.code == "missing"

    with pytest.raises(JsonObjectLoadError) as invalid_exc:
        read_json_object(invalid)
    assert invalid_exc.value.code == "invalid_json"
    assert "Expecting property name enclosed in double quotes" in invalid_exc.value.detail

    with pytest.raises(JsonObjectLoadError) as not_object_exc:
        read_json_object(not_object)
    assert not_object_exc.value.code == "not_object"


def test_load_json_object_variants_fail_open_or_return_none(tmp_path: Path) -> None:
    invalid = tmp_path / "invalid.json"
    invalid.write_text("{not-json}", encoding="utf-8")
    not_object = tmp_path / "list.json"
    not_object.write_text('["oops"]', encoding="utf-8")

    assert load_json_object(tmp_path / "missing.json") == {}
    assert load_json_object(invalid) == {}
    assert load_json_object(not_object) == {}
    assert load_json_object_or_none(tmp_path / "missing.json") is None
    assert load_json_object_or_none(invalid) is None
    assert load_json_object_or_none(not_object) is None


def test_normalize_release_text_strips_markup_and_respects_html_flag() -> None:
    value = "  [Ship it](https://example.invalid) <b>now</b> with `proof`  "

    assert normalize_release_text(value, limit=None) == "Ship it now with proof"
    assert normalize_release_text(value, limit=None, strip_html=False) == "Ship it <bnow</b with proof"


def test_normalize_release_text_truncates_and_normalizes_release_version() -> None:
    value = "Long release note " * 40

    normalized = normalize_release_text(value, limit=40)

    assert normalized.endswith("...")
    assert len(normalized) == 40
    assert normalize_release_version("v0.1.10") == "0.1.10"
    assert normalize_release_version("0.1.10") == "0.1.10"
