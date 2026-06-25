from __future__ import annotations

import re

from odylith.runtime.domain_intelligence.greenfield_confirmed_completion import _security_posture_text


def test_security_posture_completion_avoids_repeated_component_keep_shape() -> None:
    rows = [
        _security_posture_text("Intake Register Service"),
        _security_posture_text("Review Workspace"),
        _security_posture_text("Proof Ledger"),
        _security_posture_text("Release Path"),
    ]
    second_sentences = [row.split(". ", 1)[1] for row in rows]
    leading_shapes = {" ".join(sentence.split()[:5]) for sentence in second_sentences}

    assert len(leading_shapes) == len(rows)
    assert not any(re.search(r"\bkeeps?\s+privacy policy\b", row, flags=re.IGNORECASE) for row in rows)
    assert not any(
        re.search(r"\b[A-Z][A-Za-z0-9 -]+\s+keeps\s+[^.]+before release\b", row)
        for row in rows
    )
