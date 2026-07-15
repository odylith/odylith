"""Shared fixtures for Greenfield matrix campaign tests."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = REPO_ROOT / "scripts" / "release"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def matrix_campaign_runner_module(name: str):
    return load_module(SCRIPTS_ROOT / "greenfield_matrix_campaign_runner.py", name)


def command_arg(command: list[str], flag: str) -> str:
    return command[command.index(flag) + 1]


def write_payload(path: Path, *, status: str, cluster: str = "") -> None:
    clusters = [{"cluster": cluster, "count": 1, "cases": ["case one"]}] if cluster else []
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "status": status,
                "campaign": {
                    "completed_case_count": 1,
                    "failed_case_count": 0 if status == "passed" else 1,
                    "failure_clusters": clusters,
                },
            }
        ),
        encoding="utf-8",
    )


def write_case_file(
    path: Path,
    *,
    name: str,
    stressors: tuple[str, ...],
    case_id: str = "",
) -> None:
    path.write_text(
        json.dumps(
            {
                "version": "odylith.greenfield.matrix.case-file.v1",
                "cases": [
                    {
                        "name": name,
                        **({"case_id": case_id} if case_id else {}),
                        "prompt": (
                            f"Create a greenfield proposal for {name} with modal registry proof "
                            f"and {name} leakage phrase."
                        ),
                        "required_terms": ("modal", "registry"),
                        "leakage_terms": (f"{name} leakage phrase",),
                        "stressors": stressors,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
