from __future__ import annotations

import pytest

from odylith.runtime.domain_intelligence import greenfield_create_lifecycle as lifecycle


def test_create_lifecycle_accepts_success_path() -> None:
    history = (
        lifecycle.DRAFT,
        lifecycle.SEALED,
        lifecycle.PREPARED,
        lifecycle.PUBLISHING,
        lifecycle.PUBLISHED,
        lifecycle.VERIFIED,
        lifecycle.CLOSED,
    )

    assert lifecycle.require_create_lifecycle_history(history) == history


@pytest.mark.parametrize(
    ("before", "terminal"),
    [
        ("preparing", lifecycle.ABORTED),
        ("prepared", lifecycle.ABORTED),
        ("projecting", lifecycle.ABORTED),
        ("published", lifecycle.RECOVERY_REQUIRED),
    ],
)
def test_create_lifecycle_distinguishes_abort_from_recovery(before: str, terminal: str) -> None:
    history = lifecycle.lifecycle_history_for_journal_state(before)

    target = "recovery_required" if before == "published" else "aborted"
    advanced = lifecycle.advance_lifecycle_for_journal_state(history, target)

    assert advanced[-1] == terminal


def test_create_lifecycle_rejects_skipped_verification() -> None:
    with pytest.raises(ValueError, match="PUBLISHED -> CLOSED"):
        lifecycle.require_create_lifecycle_history(
            (
                lifecycle.DRAFT,
                lifecycle.SEALED,
                lifecycle.PREPARED,
                lifecycle.PUBLISHING,
                lifecycle.PUBLISHED,
                lifecycle.CLOSED,
            )
        )
