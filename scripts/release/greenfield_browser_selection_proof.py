"""Prove explicit missing selections and recovery caused by a real user click."""

from typing import Any


def missing_selection_issues(*, requested: str, invalid: str, active_count: int,
                            empty_visible: bool, empty_text: str, empty_heading: str) -> tuple[str, ...]:
    issues = []
    if requested != invalid:
        issues.append("missing selection erased or replaced the explicit route")
    if active_count:
        issues.append("missing selection silently activated a record")
    if not empty_visible or not empty_text.strip().startswith(empty_heading):
        issues.append("missing selection has no meaningful visible status")
    return tuple(issues)


def prove_missing_selection(*, page: Any, frame: Any, query_key: str, invalid: str,
                            active_selector: str, empty_selector: str, empty_heading: str,
                            timeout_ms: int) -> tuple[str, ...]:
    empty = frame.locator(empty_selector)
    empty.wait_for(state="visible", timeout=timeout_ms)
    return missing_selection_issues(
        requested=page.evaluate("key => new URL(location.href).searchParams.get(key) || ''", query_key),
        invalid=invalid, active_count=frame.locator(active_selector).count(),
        empty_visible=empty.is_visible(), empty_text=empty.inner_text(), empty_heading=empty_heading,
    )


def wait_for_selection_route(page: Any, query_key: str, expected: str, timeout_ms: int) -> None:
    page.wait_for_function(
        "([key, value]) => new URL(location.href).searchParams.get(key) === value",
        arg=[query_key, expected], timeout=timeout_ms,
    )


def recovered_selection_issues(*, expected: str, active: str, detail: str) -> tuple[str, ...]:
    if not expected or active != expected or detail != expected:
        return ("clicked selection does not match the active record and detail",)
    return ()


def prove_clicked_selection(*, page: Any, frame: Any, query_key: str,
                            active_selector: str, active_attribute: str,
                            detail_selector: str, detail_attribute: str,
                            timeout_ms: int) -> tuple[str, ...]:
    button = frame.locator(f"button[{active_attribute}]").first
    button.wait_for(state="visible", timeout=timeout_ms)
    expected = str(button.get_attribute(active_attribute) or "").strip()
    button.click()
    active = frame.locator(active_selector).first
    active.wait_for(state="visible", timeout=timeout_ms)
    detail = frame.locator(detail_selector)
    detail.wait_for(state="visible", timeout=timeout_ms)
    wait_for_selection_route(page, query_key, expected, timeout_ms)
    return recovered_selection_issues(
        expected=expected, active=str(active.get_attribute(active_attribute) or "").strip(),
        detail=str(detail.get_attribute(detail_attribute) if detail_attribute else detail.inner_text()).strip(),
    )
