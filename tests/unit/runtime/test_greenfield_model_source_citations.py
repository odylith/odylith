from __future__ import annotations

import pytest

from odylith.runtime.domain_intelligence.greenfield_model_outcomes import (
    GreenfieldModelAuthoringError,
)
from odylith.runtime.domain_intelligence.greenfield_model_source_citations import (
    canonical_citation_from_host_selection,
    exact_occurrence_start,
    exact_quote,
    resolve_source_citation,
)
from odylith.runtime.domain_intelligence.greenfield_operating_envelope import (
    MAX_AUTHORED_FIELD_VALUE_CHARS,
)


def _state(quote: str, prefix: str, anchor_occurrence: object = 1) -> dict[str, object]:
    return {
        "quote": quote,
        "prefix": prefix,
        "anchor_occurrence": anchor_occurrence,
    }


def test_legacy_exact_quote_and_occurrence_behavior_is_unchanged() -> None:
    assert exact_quote(None) == ""
    assert exact_quote("source") == "source"
    assert exact_occurrence_start(b"aba aba", b"aba", 2) == 4
    assert exact_occurrence_start(b"only", b"only", 99) == 0
    assert exact_occurrence_start(b"aaaa", b"aa", 3) == 2

    with pytest.raises(GreenfieldModelAuthoringError):
        exact_quote("x" * (MAX_AUTHORED_FIELD_VALUE_CHARS + 1))
    for occurrence in (0, -1, True, "1"):
        with pytest.raises(GreenfieldModelAuthoringError):
            exact_occurrence_start(b"source", b"source", occurrence)
    with pytest.raises(GreenfieldModelAuthoringError):
        exact_occurrence_start(b"source", b"", 1)
    with pytest.raises(GreenfieldModelAuthoringError):
        exact_occurrence_start(b"repeat repeat", b"repeat", 3)


def test_legacy_source_citation_preserves_closed_shape_and_normalization() -> None:
    evidence = b"first result; second result; unique proof"

    assert resolve_source_citation(
        evidence,
        {"quote": "result", "occurrence": 2},
    ) == ("result", evidence.index(b"result", 10))
    assert resolve_source_citation(
        evidence,
        {"quote": "unique proof", "occurrence": 7},
    ) == ("unique proof", evidence.index(b"unique proof"))

    for citation in (
        {"quote": "result", "occurrence": 1, "anchor_quote": "first result"},
        {"quote": "", "occurrence": 1},
        {"quote": "result", "occurrence": True},
    ):
        with pytest.raises(GreenfieldModelAuthoringError):
            resolve_source_citation(evidence, citation)


def test_unique_context_projects_repeated_quote_to_exact_legacy_address() -> None:
    evidence = "α result before. β result after.".encode("utf-8")

    canonical = canonical_citation_from_host_selection(
        evidence,
        {"quote": "result", "context": "β result after"},
    )

    assert canonical == {"quote": "result", "occurrence": 2}
    assert resolve_source_citation(evidence, canonical) == (
        "result",
        evidence.rindex(b"result"),
    )


def test_unique_context_projects_state_without_enlarging_its_meaning() -> None:
    evidence = "first state; selected state remains".encode("utf-8")

    canonical = canonical_citation_from_host_selection(
        evidence,
        {"quote": "state", "context": "selected state remains"},
        state_object=True,
    )

    assert canonical == {
        "quote": "state",
        "prefix": "selected ",
        "anchor_occurrence": 1,
    }
    assert resolve_source_citation(evidence, canonical, state_object=True) == (
        "state",
        evidence.rindex(b"state"),
    )


@pytest.mark.parametrize(
    "citation",
    (
        {"quote": "unique proof", "context": "unique proof"},
        {"quote": "unique proof", "context": "wrong"},
    ),
)
def test_unique_quote_projects_without_host_owned_locator_precision(
    citation: dict[str, object],
) -> None:
    evidence = b"one unique proof remains"

    canonical = canonical_citation_from_host_selection(evidence, citation)

    assert canonical == {"quote": "unique proof", "occurrence": 1}
    assert resolve_source_citation(evidence, canonical) == (
        "unique proof",
        evidence.index(b"unique proof"),
    )


def test_unique_state_quote_projects_without_host_owned_locator_precision() -> None:
    evidence = b"one durable state remains"

    canonical = canonical_citation_from_host_selection(
        evidence,
        {"quote": "durable state", "context": "durable state"},
        state_object=True,
    )

    assert canonical == {
        "quote": "durable state",
        "prefix": "",
        "anchor_occurrence": 1,
    }


def test_host_selection_requires_nonempty_context_even_when_quote_is_unique() -> None:
    for citation in (
        {"quote": "unique proof"},
        {"quote": "unique proof", "context": ""},
        {"quote": "unique proof", "context": None},
    ):
        with pytest.raises(GreenfieldModelAuthoringError):
            canonical_citation_from_host_selection(b"one unique proof remains", citation)


def test_host_selection_preserves_v26_actor_bytes_and_rejects_rewrites() -> None:
    evidence = (
        b"Project brief for an accessibility team. User intent: A program lead "
        b"registers a readiness dossier."
    )
    exact = {"quote": "A program lead", "context": "A program lead"}

    assert canonical_citation_from_host_selection(evidence, exact) == {
        "quote": "A program lead",
        "occurrence": 1,
    }

    for rewritten in (
        "a program lead",
        "the program lead",
        "A program lead.",
        "A  program lead",
    ):
        with pytest.raises(GreenfieldModelAuthoringError):
            canonical_citation_from_host_selection(
                evidence,
                {"quote": rewritten, "context": rewritten},
            )


@pytest.mark.parametrize(
    "citation",
    (
        {"quote": "result", "context": "result"},
        {"quote": "result", "context": "missing result"},
        {"quote": "result", "context": "result and result"},
        {"quote": "result", "context": "first result", "occurrence": 1},
    ),
)
def test_unique_context_fails_closed_when_address_is_not_unique(
    citation: dict[str, object],
) -> None:
    with pytest.raises(GreenfieldModelAuthoringError):
        canonical_citation_from_host_selection(
            b"first result; second result",
            citation,
        )


@pytest.mark.parametrize(
    ("evidence_text", "citation"),
    (
        (
            "The apprenticeship credential is issued before registered apprentices begin.",
            _state("apprentices", "The apprenticeship credential is issued before registered "),
        ),
        (
            "The persistent state is a feed health record. A coordinator reviews its receipt.",
            _state("feed health record", "persistent state is a "),
        ),
        (
            "The collection is a donation batch. A coordinator reviews each donation and closes each batch.",
            _state("donation batch", "The collection is a "),
        ),
        (
            "Status: ready. Status: ready.",
            _state("ready", "Status: ", 2),
        ),
        (
            "# Shifted heading\n\nThe published register is ready for council review.",
            _state("published register", "The "),
        ),
        (
            "Préface 🧭 — the café ledger is ready.",
            _state("café ledger", "Préface 🧭 — the "),
        ),
        (
            "ababa",
            _state("b", "a", 2),
        ),
        (
            "状态：等待。状态：等待。",
            _state("等待", "状态：", 2),
        ),
        (
            "ready ready",
            _state("ready", "", 2),
        ),
        (
            "ready",
            _state("ready", ""),
        ),
    ),
)
def test_state_citation_selects_exact_anchor_local_byte_span(
    evidence_text: str,
    citation: dict[str, object],
) -> None:
    evidence = evidence_text.encode("utf-8")
    quote, start = resolve_source_citation(evidence, citation, state_object=True)
    quote_bytes = quote.encode("utf-8")

    assert quote == citation["quote"]
    assert evidence[start : start + len(quote_bytes)] == quote_bytes
    assert start == evidence.rindex(quote_bytes)


@pytest.mark.parametrize(
    "citation",
    (
        {"quote": "state", "occurrence": 1},
        {"quote": "state", "anchor_quote": "the state", "anchor_occurrence": 1},
        {"quote": "state", "prefix": "the ", "anchor_occurrence": 1, "extra": "x"},
        {"quote": "state", "anchor_occurrence": 1},
        {"quote": "state", "wrong_anchor": "the state", "anchor_occurrence": 1},
        {"quote": "", "prefix": "the ", "anchor_occurrence": 1},
        {"quote": "state", "prefix": None, "anchor_occurrence": 1},
        {"quote": "state", "prefix": True, "anchor_occurrence": 1},
        {"quote": "state", "prefix": "the ", "anchor_occurrence": 0},
        {"quote": "state", "prefix": "the ", "anchor_occurrence": True},
        {"quote": "state", "prefix": "the ", "anchor_occurrence": "1"},
    ),
)
def test_state_citation_rejects_old_or_invalid_contract(citation: dict[str, object]) -> None:
    with pytest.raises(GreenfieldModelAuthoringError):
        resolve_source_citation(b"the state", citation, state_object=True)


def test_state_citation_rejects_missing_or_impossible_anchor() -> None:
    with pytest.raises(GreenfieldModelAuthoringError):
        resolve_source_citation(
            b"the selected state",
            _state("state", "missing anchor"),
            state_object=True,
        )
    with pytest.raises(GreenfieldModelAuthoringError):
        resolve_source_citation(
            b"the selected state",
            _state("state", "the selected ", 2),
            state_object=True,
        )


def test_state_address_does_not_rebind_a_semantically_wrong_selection() -> None:
    evidence = b"apprenticeship credential; coordinators register apprentices"
    quote, start = resolve_source_citation(
        evidence, _state("apprentices", ""), state_object=True,
    )

    # Address resolution is structural; the immutable reviewer owns semantic rejection.
    assert quote == "apprentices"
    assert start == 0
    assert start != evidence.rindex(b"apprentices")


def test_state_citation_requires_exact_adjacency_without_rebinding() -> None:
    with pytest.raises(GreenfieldModelAuthoringError):
        resolve_source_citation(
            b"state outside; selected anchor",
            _state("state", "selected anchor"),
            state_object=True,
        )
    with pytest.raises(GreenfieldModelAuthoringError):
        resolve_source_citation(
            b"prefix and state",
            _state("state", "prefix "),
            state_object=True,
        )


def test_split_anchor_selects_quote_after_prior_literal_matches() -> None:
    evidence = b"state and state and state"
    assert resolve_source_citation(
        evidence, _state("state", "state and state and "), state_object=True,
    ) == ("state", 20)


def test_split_anchor_total_length_keeps_the_existing_anchor_bound() -> None:
    with pytest.raises(GreenfieldModelAuthoringError):
        resolve_source_citation(
            b"x" * (MAX_AUTHORED_FIELD_VALUE_CHARS + 1),
            _state("x", "x" * MAX_AUTHORED_FIELD_VALUE_CHARS),
            state_object=True,
        )


@pytest.mark.parametrize("field", ("quote", "prefix"))
def test_state_citation_rejects_overlong_strings(field: str) -> None:
    citation = _state("state", "the ")
    citation[field] = "x" * (MAX_AUTHORED_FIELD_VALUE_CHARS + 1)

    with pytest.raises(GreenfieldModelAuthoringError):
        resolve_source_citation(b"the state", citation, state_object=True)
