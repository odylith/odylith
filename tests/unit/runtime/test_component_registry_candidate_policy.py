from __future__ import annotations

import json
from pathlib import Path

from odylith.runtime.governance import component_registry_candidate_policy
from odylith.runtime.governance import component_registry_intelligence


def test_execution_governance_is_retired_from_component_candidate_review() -> None:
    assert component_registry_candidate_policy.is_retired_component_candidate_token("execution-governance")
    assert component_registry_candidate_policy.is_retired_component_candidate_token("execution_governance")
    assert component_registry_candidate_policy.is_retired_component_candidate_token("Execution Governance")
    assert not component_registry_candidate_policy.is_retired_component_candidate_token("execution-engine")


def test_component_candidate_queue_suppresses_retired_execution_governance_token(tmp_path: Path) -> None:
    catalog_path = tmp_path / "odylith" / "atlas" / "source" / "catalog" / "diagrams.v1.json"
    catalog_path.parent.mkdir(parents=True)
    catalog_path.write_text(
        json.dumps(
            {
                "diagrams": [
                    {
                        "diagram_id": "D-999",
                        "components": [
                            {
                                "name": "execution-governance",
                                "inventory_candidate": True,
                            },
                            {
                                "name": "new-runtime-lane",
                                "inventory_candidate": True,
                            },
                        ],
                    }
                ]
            }
        )
        + "\n",
        encoding="utf-8",
    )
    ideas_root = tmp_path / "odylith" / "radar" / "source" / "ideas"
    ideas_root.mkdir(parents=True)
    stream_path = tmp_path / "odylith" / "compass" / "runtime" / "agent-stream.v1.jsonl"
    stream_path.parent.mkdir(parents=True)
    stream_path.write_text(
        "\n".join(
            [
                json.dumps({"components": ["execution-governance"]}),
                json.dumps({"components": ["stream-runtime-lane"]}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    queue = component_registry_intelligence.build_candidate_component_queue(
        repo_root=tmp_path,
        catalog_path=catalog_path,
        ideas_root=ideas_root,
        stream_path=stream_path,
        alias_to_component={"execution-engine": "execution-engine"},
    )

    tokens = [row["token"] for row in queue]
    assert "execution-governance" not in tokens
    assert set(tokens) == {"new-runtime-lane", "stream-runtime-lane"}
