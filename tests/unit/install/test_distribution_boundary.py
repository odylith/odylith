from __future__ import annotations

import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_wheel_build_configuration_excludes_test_and_simulator_content() -> None:
    pyproject_path = REPO_ROOT / "pyproject.toml"
    payload = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))

    wheel_target = payload["tool"]["hatch"]["build"]["targets"]["wheel"]
    sdist_target = payload["tool"]["hatch"]["build"]["targets"]["sdist"]

    assert wheel_target["packages"] == ["src/odylith"]
    include_patterns = [str(token) for token in wheel_target["include"]]
    assert all("tests" not in pattern for pattern in include_patterns)
    assert all(
        pattern in {"LICENSE", "NOTICE", "THIRD_PARTY_ATTRIBUTION.md"} or pattern.startswith("src/odylith/")
        for pattern in include_patterns
    )
    assert wheel_target["extra-metadata"] == {
        "THIRD_PARTY_ATTRIBUTION.md": "THIRD_PARTY_ATTRIBUTION.md",
    }

    sdist_patterns = [str(token) for token in sdist_target["include"]]
    assert "tests/**" in sdist_patterns
