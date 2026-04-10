from __future__ import annotations

import json
from pathlib import Path

from tests.integration.runtime.compass_browser_regression_support import (
    clone_odylith_fixture,
    current_workstream_ids,
    load_runtime_payload,
    open_compass_page,
    program_member_ids,
    release_target_ids,
    render_compass_fixture,
    runtime_paths,
    scope_option_values,
    selected_scope_value,
    wait_for_current_workstreams_or_empty,
    write_runtime_payload,
)
from tests.integration.runtime.surface_browser_test_support import (
    _assert_clean_page,
    _browser,
)


def _workstream_row(payload: dict[str, object], idea_id: str) -> dict[str, object]:
    rows = []
    rows.extend(payload.get("current_workstreams", []) if isinstance(payload.get("current_workstreams"), list) else [])
    rows.extend(payload.get("workstream_catalog", []) if isinstance(payload.get("workstream_catalog"), list) else [])
    for row in rows:
        if not isinstance(row, dict):
            continue
        if str(row.get("idea_id", "")).strip() == idea_id:
            return dict(row)
    return {
        "idea_id": idea_id,
        "title": idea_id,
        "status": "implementation",
        "release": {},
        "release_history_summary": "",
        "plan": {},
        "execution_wave_programs": [],
    }


def _release_summary(*, active_ids: list[str], completed_ids: list[str]) -> dict[str, object]:
    current_release = {
        "release_id": "release-0-1-11",
        "display_label": "0.1.11",
        "status": "active",
        "aliases": ["current"],
        "active_workstreams": list(active_ids),
        "completed_workstreams": list(completed_ids),
    }
    return {
        "catalog": [dict(current_release)],
        "current_release": dict(current_release),
        "next_release": {},
        "summary": {"active_assignment_count": len(active_ids)},
    }


def _write_source_truth_snapshot(
    fixture_root: Path,
    *,
    active_ids: list[str],
    current_ids: list[str],
    generated_utc: str,
) -> None:
    payload = load_runtime_payload(fixture_root)
    _current_json_path, _current_js_path, source_truth_path = runtime_paths(fixture_root)
    source_truth = json.loads(source_truth_path.read_text(encoding="utf-8"))
    source_truth["generated_utc"] = generated_utc
    source_truth["release_summary"] = _release_summary(
        active_ids=active_ids,
        completed_ids=["B-061", "B-062", "B-063"],
    )
    source_truth["current_workstreams"] = [_workstream_row(payload, idea_id) for idea_id in current_ids]
    source_truth["workstream_catalog"] = [
        _workstream_row(payload, idea_id)
        for idea_id in [*current_ids, *active_ids, "B-067"]
    ]
    source_truth["verified_scoped_workstreams"] = {"24h": list(current_ids), "48h": list(current_ids)}
    source_truth["promoted_scoped_workstreams"] = {"24h": list(current_ids), "48h": list(current_ids)}
    source_truth["window_scope_signals"] = {
        "24h": {idea_id: {"promoted_default": True, "budget_class": "primary"} for idea_id in current_ids},
        "48h": {idea_id: {"promoted_default": True, "budget_class": "primary"} for idea_id in current_ids},
    }
    source_truth_path.write_text(json.dumps(source_truth, indent=2) + "\n", encoding="utf-8")


def _rewrite_traceability_release_truth(
    fixture_root: Path,
    *,
    active_ids: list[str],
    completed_ids: list[str],
) -> None:
    traceability_path = fixture_root / "odylith" / "radar" / "traceability-graph.v1.json"
    traceability = json.loads(traceability_path.read_text(encoding="utf-8"))
    for release in traceability.get("releases", []):
        if str(release.get("release_id", "")).strip() != "release-0-1-11":
            continue
        release["active_workstreams"] = list(active_ids)
        release["completed_workstreams"] = list(completed_ids)
    if isinstance(traceability.get("current_release"), dict):
        traceability["current_release"]["active_workstreams"] = list(active_ids)
        traceability["current_release"]["completed_workstreams"] = list(completed_ids)
        traceability["generated_utc"] = "2026-04-09T12:00:00Z"
    rows = traceability.get("workstreams", [])
    if isinstance(rows, list):
        seen_ids = set()
        for row in rows:
            if not isinstance(row, dict):
                continue
            idea_id = str(row.get("idea_id", "")).strip()
            if not idea_id:
                continue
            seen_ids.add(idea_id)
            if idea_id in active_ids:
                row["status"] = "implementation"
                row["active_release_id"] = "release-0-1-11"
                row["active_release"] = {
                    "release_id": "release-0-1-11",
                    "display_label": "0.1.11",
                    "status": "active",
                    "aliases": ["current"],
                    "active_workstreams": list(active_ids),
                    "completed_workstreams": list(completed_ids),
                }
            elif idea_id in completed_ids:
                row["status"] = "finished"
        for idea_id in active_ids:
            if idea_id in seen_ids:
                continue
            rows.append(
                {
                    "idea_id": idea_id,
                    "title": idea_id,
                    "status": "implementation",
                    "active_release_id": "release-0-1-11",
                    "active_release": {
                        "release_id": "release-0-1-11",
                        "display_label": "0.1.11",
                        "status": "active",
                        "aliases": ["current"],
                        "active_workstreams": list(active_ids),
                        "completed_workstreams": list(completed_ids),
                    },
                }
            )
    traceability_path.write_text(json.dumps(traceability, indent=2) + "\n", encoding="utf-8")


def _write_unusable_source_truth_snapshot(
    fixture_root: Path,
    *,
    active_ids: list[str],
    generated_utc: str,
) -> None:
    _current_json_path, _current_js_path, source_truth_path = runtime_paths(fixture_root)
    source_truth_path.write_text(
        json.dumps(
            {
                "generated_utc": generated_utc,
                "release_summary": _release_summary(
                    active_ids=active_ids,
                    completed_ids=["B-061", "B-062", "B-063"],
                ),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def test_compass_browser_source_truth_snapshot_restores_active_release_and_wave_truth(tmp_path: Path) -> None:
    fixture_root = clone_odylith_fixture(tmp_path)
    render_compass_fixture(fixture_root)
    _write_source_truth_snapshot(
        fixture_root,
        active_ids=["B-072", "B-073", "B-079"],
        current_ids=["B-072", "B-073", "B-079"],
        generated_utc="2026-04-09T12:00:00Z",
    )

    payload = load_runtime_payload(fixture_root)
    stale_row = _workstream_row(payload, "B-067")
    stale_row["status"] = "implementation"
    payload["generated_utc"] = "2026-04-08T00:00:00Z"
    payload["release_summary"] = _release_summary(
        active_ids=["B-067"],
        completed_ids=["B-061", "B-062", "B-063"],
    )
    payload["current_workstreams"] = [stale_row]
    payload["workstream_catalog"] = [stale_row]
    write_runtime_payload(fixture_root, payload)

    for _pw, browser in _browser():
        context, page, compass, console_errors, page_errors, failed_requests, bad_responses = open_compass_page(
            fixture_root,
            browser,
        )
        try:
            compass.locator("#status-banner").wait_for(timeout=15000)
            banner_text = compass.locator("#status-banner").inner_text().strip()
            assert "governed source-truth snapshot" in banner_text

            release_ids = release_target_ids(compass)
            wait_for_current_workstreams_or_empty(compass)
            assert {"B-072", "B-073", "B-079"}.issubset(set(release_ids))

            current_ids = current_workstream_ids(compass)
            assert current_ids == []
            compass.locator(
                "#current-workstreams .empty",
                has_text="All current workstreams are already represented in Programs or Release Targets.",
            ).wait_for(timeout=15000)

            console_errors[:] = [row for row in console_errors if "compass-source-truth.v1.json" not in row]
            bad_responses[:] = [row for row in bad_responses if "compass-source-truth.v1.json" not in row]
            _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)
        finally:
            context.close()


def test_compass_browser_older_source_truth_snapshot_never_overrides_fresher_runtime(tmp_path: Path) -> None:
    fixture_root = clone_odylith_fixture(tmp_path)
    render_compass_fixture(fixture_root)
    _write_source_truth_snapshot(
        fixture_root,
        active_ids=["B-072", "B-073", "B-079"],
        current_ids=["B-072", "B-073", "B-079"],
        generated_utc="2026-04-01T00:00:00Z",
    )
    _rewrite_traceability_release_truth(
        fixture_root,
        active_ids=["B-067"],
        completed_ids=["B-061", "B-062", "B-063"],
    )
    traceability_path = fixture_root / "odylith" / "radar" / "traceability-graph.v1.json"
    traceability = json.loads(traceability_path.read_text(encoding="utf-8"))
    traceability["generated_utc"] = "2026-04-01T00:00:00Z"
    traceability_path.write_text(json.dumps(traceability, indent=2) + "\n", encoding="utf-8")

    payload = load_runtime_payload(fixture_root)
    stale_row = _workstream_row(payload, "B-067")
    stale_row["status"] = "implementation"
    payload["generated_utc"] = "2026-04-10T00:00:00Z"
    payload["release_summary"] = _release_summary(
        active_ids=["B-067"],
        completed_ids=["B-061", "B-062", "B-063"],
    )
    payload["current_workstreams"] = [stale_row]
    payload["workstream_catalog"] = [stale_row]
    write_runtime_payload(fixture_root, payload)

    for _pw, browser in _browser():
        context, page, compass, console_errors, page_errors, failed_requests, bad_responses = open_compass_page(
            fixture_root,
            browser,
        )
        try:
            compass.locator("#current-workstreams .empty").wait_for(timeout=15000)
            current_ids = current_workstream_ids(compass)
            assert current_ids == []
            assert "B-072" not in current_ids
            assert (
                compass.locator("#current-workstreams .empty").inner_text().strip()
                == "All current workstreams are already represented in Programs or Release Targets."
            )

            release_ids = release_target_ids(compass)
            assert "B-067" in release_ids
            assert "B-072" not in release_ids

            assert "governed source-truth snapshot" not in compass.locator("#status-banner").inner_text().strip()

            console_errors[:] = [row for row in console_errors if "ERR_CONNECTION_" not in row]
            failed_requests[:] = [
                row
                for row in failed_requests
                if "/runtime/current.v1.json" not in row
                and "runtime/history/" not in row.lower()
                and "/radar/traceability-graph.v1.json" not in row
            ]
            _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)
        finally:
            context.close()


def test_compass_browser_traceability_fallback_prioritizes_active_release_truth_when_source_snapshot_is_missing(
    tmp_path: Path,
) -> None:
    fixture_root = clone_odylith_fixture(tmp_path)
    render_compass_fixture(fixture_root)
    _rewrite_traceability_release_truth(
        fixture_root,
        active_ids=["B-072", "B-073", "B-079"],
        completed_ids=["B-061", "B-062", "B-063"],
    )

    payload = load_runtime_payload(fixture_root)
    stale_row = _workstream_row(payload, "B-067")
    stale_row["status"] = "implementation"
    payload["generated_utc"] = "2026-04-08T00:00:00Z"
    payload["release_summary"] = _release_summary(
        active_ids=["B-067"],
        completed_ids=["B-061", "B-062", "B-063"],
    )
    payload["current_workstreams"] = [stale_row]
    payload["workstream_catalog"] = [stale_row]
    write_runtime_payload(fixture_root, payload)

    _current_json_path, _current_js_path, source_truth_path = runtime_paths(fixture_root)
    source_truth_path.unlink()

    for _pw, browser in _browser():
        context, page, compass, console_errors, page_errors, failed_requests, bad_responses = open_compass_page(
            fixture_root,
            browser,
        )
        try:
            compass.locator("#status-banner").wait_for(timeout=15000)
            banner_text = compass.locator("#status-banner").inner_text().strip()
            assert "traceability-graph fallback" in banner_text

            release_ids = release_target_ids(compass)
            wait_for_current_workstreams_or_empty(compass)
            assert {"B-072", "B-073", "B-079"}.issubset(set(release_ids))

            current_ids = current_workstream_ids(compass)
            assert current_ids == []
            compass.locator(
                "#current-workstreams .empty",
                has_text="All current workstreams are already represented in Programs or Release Targets.",
            ).wait_for(timeout=15000)

            console_errors[:] = []
            bad_responses[:] = []
            failed_requests[:] = [row for row in failed_requests if "runtime/history/" not in row.lower()]
            _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)
        finally:
            context.close()


def test_compass_browser_source_truth_snapshot_keeps_release_program_and_current_workstream_sections_aligned(
    tmp_path: Path,
) -> None:
    fixture_root = clone_odylith_fixture(tmp_path)
    render_compass_fixture(fixture_root)
    _write_source_truth_snapshot(
        fixture_root,
        active_ids=["B-072", "B-073", "B-079"],
        current_ids=["B-072", "B-073", "B-079"],
        generated_utc="2026-04-09T12:00:00Z",
    )

    payload = load_runtime_payload(fixture_root)
    stale_row = _workstream_row(payload, "B-067")
    stale_row["status"] = "implementation"
    payload["generated_utc"] = "2026-04-08T00:00:00Z"
    payload["release_summary"] = _release_summary(
        active_ids=["B-067"],
        completed_ids=["B-061", "B-062", "B-063"],
    )
    payload["current_workstreams"] = [stale_row]
    payload["workstream_catalog"] = [stale_row]
    payload["verified_scoped_workstreams"] = {"24h": ["B-067"], "48h": ["B-067"]}
    payload["promoted_scoped_workstreams"] = {"24h": ["B-067"], "48h": ["B-067"]}
    payload["window_scope_signals"] = {
        "24h": {"B-067": {"promoted_default": True, "budget_class": "primary"}},
        "48h": {"B-067": {"promoted_default": True, "budget_class": "primary"}},
    }
    write_runtime_payload(fixture_root, payload)

    for _pw, browser in _browser():
        context, page, compass, console_errors, page_errors, failed_requests, bad_responses = open_compass_page(
            fixture_root,
            browser,
        )
        try:
            compass.locator("#status-banner").wait_for(timeout=15000)
            assert "governed source-truth snapshot" in compass.locator("#status-banner").inner_text().strip()

            release_ids = release_target_ids(compass)
            program_ids = program_member_ids(compass)
            compass.locator("#current-workstreams .empty", has_text="All current workstreams are already represented in Programs or Release Targets.").wait_for(timeout=15000)
            current_ids = current_workstream_ids(compass)
            scope_ids = [token for token in scope_option_values(compass) if token]
            program_text = compass.locator("#execution-waves-host").inner_text().strip()

            expected_ids = {"B-072", "B-073", "B-079"}
            assert expected_ids.issubset(set(release_ids))
            assert "B-072" in program_text
            assert {"B-073", "B-079"}.issubset(set(program_ids))
            assert set(current_ids).isdisjoint(expected_ids)
            assert "B-067" not in scope_ids
            assert "B-067" not in current_ids
            assert selected_scope_value(compass) == ""

            console_errors[:] = [row for row in console_errors if "compass-source-truth.v1.json" not in row]
            bad_responses[:] = [row for row in bad_responses if "compass-source-truth.v1.json" not in row]
            _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)
        finally:
            context.close()


def test_compass_browser_traceability_fallback_clears_stale_scoped_metadata_before_current_workstreams_render(
    tmp_path: Path,
) -> None:
    fixture_root = clone_odylith_fixture(tmp_path)
    render_compass_fixture(fixture_root)
    _rewrite_traceability_release_truth(
        fixture_root,
        active_ids=["B-072", "B-073", "B-079"],
        completed_ids=["B-061", "B-062", "B-063"],
    )

    payload = load_runtime_payload(fixture_root)
    stale_row = _workstream_row(payload, "B-067")
    stale_row["status"] = "implementation"
    payload["generated_utc"] = "2026-04-08T00:00:00Z"
    payload["release_summary"] = _release_summary(
        active_ids=["B-067"],
        completed_ids=["B-061", "B-062", "B-063"],
    )
    payload["current_workstreams"] = [stale_row]
    payload["workstream_catalog"] = [stale_row]
    payload["verified_scoped_workstreams"] = {"24h": ["B-067"], "48h": ["B-067"]}
    payload["promoted_scoped_workstreams"] = {"24h": ["B-067"], "48h": ["B-067"]}
    payload["window_scope_signals"] = {
        "24h": {"B-067": {"promoted_default": True, "budget_class": "primary"}},
        "48h": {"B-067": {"promoted_default": True, "budget_class": "primary"}},
    }
    write_runtime_payload(fixture_root, payload)

    _current_json_path, _current_js_path, source_truth_path = runtime_paths(fixture_root)
    source_truth_path.unlink()

    for _pw, browser in _browser():
        context, page, compass, console_errors, page_errors, failed_requests, bad_responses = open_compass_page(
            fixture_root,
            browser,
        )
        try:
            compass.locator("#status-banner").wait_for(timeout=15000)
            assert "traceability-graph fallback" in compass.locator("#status-banner").inner_text().strip()

            wait_for_current_workstreams_or_empty(compass)
            current_ids = current_workstream_ids(compass)
            scope_ids = [token for token in scope_option_values(compass) if token]

            assert current_ids == []
            assert "B-067" not in current_ids
            assert "B-067" not in scope_ids
            assert selected_scope_value(compass) == ""
            compass.locator(
                "#current-workstreams .empty",
                has_text="All current workstreams are already represented in Programs or Release Targets.",
            ).wait_for(timeout=15000)

            console_errors[:] = []
            bad_responses[:] = []
            failed_requests[:] = [row for row in failed_requests if "runtime/history/" not in row.lower()]
            _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)
        finally:
            context.close()


def test_compass_browser_ignores_unusable_source_truth_snapshot_and_continues_to_traceability_fallback(
    tmp_path: Path,
) -> None:
    fixture_root = clone_odylith_fixture(tmp_path)
    render_compass_fixture(fixture_root)
    _write_unusable_source_truth_snapshot(
        fixture_root,
        active_ids=["B-999"],
        generated_utc="2026-04-10T12:00:00Z",
    )
    _rewrite_traceability_release_truth(
        fixture_root,
        active_ids=["B-072", "B-073", "B-079"],
        completed_ids=["B-061", "B-062", "B-063"],
    )

    payload = load_runtime_payload(fixture_root)
    stale_row = _workstream_row(payload, "B-067")
    stale_row["status"] = "implementation"
    payload["generated_utc"] = "2026-04-08T00:00:00Z"
    payload["release_summary"] = _release_summary(
        active_ids=["B-067"],
        completed_ids=["B-061", "B-062", "B-063"],
    )
    payload["current_workstreams"] = [stale_row]
    payload["workstream_catalog"] = [stale_row]
    write_runtime_payload(fixture_root, payload)

    for _pw, browser in _browser():
        context, page, compass, console_errors, page_errors, failed_requests, bad_responses = open_compass_page(
            fixture_root,
            browser,
        )
        try:
            compass.locator("#status-banner").wait_for(timeout=15000)
            banner_text = compass.locator("#status-banner").inner_text().strip()
            assert "traceability-graph fallback" in banner_text
            assert "B-999" not in banner_text

            release_ids = release_target_ids(compass)
            wait_for_current_workstreams_or_empty(compass)
            current_ids = current_workstream_ids(compass)
            assert {"B-072", "B-073", "B-079"}.issubset(set(release_ids))
            assert current_ids == []
            assert "B-999" not in release_ids
            assert "B-067" not in current_ids
            compass.locator(
                "#current-workstreams .empty",
                has_text="All current workstreams are already represented in Programs or Release Targets.",
            ).wait_for(timeout=15000)

            console_errors[:] = []
            bad_responses[:] = []
            failed_requests[:] = [row for row in failed_requests if "runtime/history/" not in row.lower()]
            _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)
        finally:
            context.close()
