"""Negative controls for missing-target honesty and exact click recovery."""

import sys

import pytest

from tests.greenfield_matrix_campaign_test_support import SCRIPTS_ROOT

if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from greenfield_browser_selection_proof import missing_selection_issues, recovered_selection_issues, wait_for_selection_route


@pytest.mark.parametrize("invalid", ("B-999999", "does-not-exist", "D-999999"))
def test_missing_selection_preserves_request_and_meaningful_empty_state(invalid: str) -> None:
    assert missing_selection_issues(
        requested=invalid, invalid=invalid, active_count=0,
        empty_visible=True, empty_text="No matching records. Choose a record from the list.",
        empty_heading="No matching records",
    ) == ()


@pytest.mark.parametrize("change", (
    {"requested": ""}, {"requested": "B-001"}, {"active_count": 1},
    {"empty_visible": False}, {"empty_text": ""}, {"empty_text": "   "},
    {"empty_text": "Loading records, please wait."},
))
def test_missing_selection_rejects_silent_fallback_erased_route_and_blank_status(change: dict) -> None:
    observed = dict(requested="B-999999", invalid="B-999999", active_count=0,
                    empty_visible=True, empty_text="No matching records. Choose a record from the list.",
                    empty_heading="No matching records")
    assert missing_selection_issues(**(observed | change))


@pytest.mark.parametrize("expected", ("B-001", "request-intake", "D-001"))
def test_recovered_selection_requires_the_clicked_identity(expected: str) -> None:
    assert recovered_selection_issues(expected=expected, active=expected, detail=expected) == ()
    assert recovered_selection_issues(expected=expected, active="", detail=expected)
    assert recovered_selection_issues(expected=expected, active="wrong", detail=expected)
    assert recovered_selection_issues(expected=expected, active=expected, detail="stale")


@pytest.mark.parametrize("key, value", (("workstream", "B-001"), ("component", "request-intake"), ("diagram", "D-001")))
def test_route_wait_binds_exact_query_key_and_clicked_identity(key: str, value: str) -> None:
    calls = []

    class Page:
        def wait_for_function(self, expression, *, arg, timeout):
            calls.append((expression, arg, timeout))

    wait_for_selection_route(Page(), key, value, 15000)
    assert calls == [("([key, value]) => new URL(location.href).searchParams.get(key) === value", [key, value], 15000)]
