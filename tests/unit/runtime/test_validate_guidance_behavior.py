from __future__ import annotations

import json
from pathlib import Path

from odylith.runtime.governance import guidance_behavior_guidance_contracts
from odylith.runtime.governance import guidance_behavior_platform_contracts
from odylith.runtime.governance import guidance_behavior_runtime_contracts
from odylith.runtime.governance import guidance_behavior_runtime
from odylith.runtime.governance import validate_guidance_behavior


ROOT = Path(__file__).resolve().parents[3]
PUBLIC_CORPUS = ROOT / "odylith" / "runtime" / "source" / "guidance-behavior-evaluation-corpus.v1.json"
BUNDLE_CORPUS = (
    ROOT
    / "src"
    / "odylith"
    / "bundle"
    / "assets"
    / "odylith"
    / "runtime"
    / "source"
    / "guidance-behavior-evaluation-corpus.v1.json"
)


def _case(case_id: str = "guidance-fixture", *, related_refs: list[str] | None = None) -> dict[str, object]:
    return {
        "id": case_id,
        "family": "guidance_behavior",
        "prompt": "Check the guidance behavior contract.",
        "expected_behavior": ["Stay grounded before broad scan."],
        "forbidden_behavior": ["Do not skip grounding."],
        "required_evidence": ["Fresh proof is present."],
        "related_guidance_refs": related_refs or ["AGENTS.md", "odylith/AGENTS.md"],
        "severity": "high",
    }


def _write_corpus(root: Path, *, cases: list[dict[str, object]] | None = None) -> None:
    selected_cases = cases if cases is not None else [_case()]
    path = root / validate_guidance_behavior.CORPUS_RELATIVE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    corpus_text = json.dumps(
        {
            "version": validate_guidance_behavior.EXPECTED_CORPUS_VERSION,
            "contract": validate_guidance_behavior.CONTRACT,
            "family": "guidance_behavior",
            "cases": selected_cases,
        },
        indent=2,
    )
    path.write_text(corpus_text, encoding="utf-8")
    mirror = root / validate_guidance_behavior.BUNDLE_CORPUS_RELATIVE_PATH
    mirror.parent.mkdir(parents=True, exist_ok=True)
    mirror.write_text(corpus_text, encoding="utf-8")
    benchmark_cases = [
        {
            "case_id": case.get("id", ""),
            "family": "guidance_behavior",
            "priority": case.get("severity", "high"),
            "label": str(case.get("id", "")),
            "summary": "Fixture guidance behavior scenario.",
            "benchmark": {
                "prompt": case.get("prompt", ""),
                "required_paths": [
                    *[
                        str(ref).strip()
                        for ref in case.get("related_guidance_refs", [])
                        if str(ref).strip()
                    ],
                    str(validate_guidance_behavior.CORPUS_RELATIVE_PATH),
                ],
                "critical_paths": [
                    *[
                        str(ref).strip()
                        for ref in case.get("related_guidance_refs", [])
                        if str(ref).strip()
                    ],
                    str(validate_guidance_behavior.CORPUS_RELATIVE_PATH),
                ],
                "correctness_critical": True,
                "validation_commands": [
                    "odylith validate guidance-behavior "
                    f"--repo-root . --case-id {case.get('id', '')}"
                ],
            },
            "expect": {"within_budget": True},
        }
        for case in selected_cases
        if case.get("id")
    ]
    benchmark_text = json.dumps(
        {"version": "v1", "scenarios": benchmark_cases, "architecture_scenarios": []},
        indent=2,
    )
    benchmark_path = root / validate_guidance_behavior.BENCHMARK_CORPUS_RELATIVE_PATH
    benchmark_path.parent.mkdir(parents=True, exist_ok=True)
    benchmark_path.write_text(benchmark_text, encoding="utf-8")
    benchmark_mirror = root / validate_guidance_behavior.BUNDLE_BENCHMARK_CORPUS_RELATIVE_PATH
    benchmark_mirror.parent.mkdir(parents=True, exist_ok=True)
    benchmark_mirror.write_text(benchmark_text, encoding="utf-8")


def _write_guidance_fixture(
    root: Path,
    *,
    skill_description: str = "Use when fixture behavior needs a check.",
) -> None:
    root.mkdir(parents=True, exist_ok=True)
    base_guidance = (
        "CLI-first guidance says hand-edit governed files is forbidden when odylith backlog create exists.\n"
        "Queued backlog items are not implicit implementation instructions unless the user explicitly asks.\n"
        "Run intervention-status before visible-intervention claims and show that Markdown directly.\n"
    )
    proof_guidance = base_guidance + (
        "For live blockers, never say fixed, cleared, or resolved unless hosted proof moved past the prior failing phase.\n"
    )
    (root / "AGENTS.md").write_text(base_guidance, encoding="utf-8")
    (root / "odylith").mkdir(parents=True, exist_ok=True)
    (root / "odylith" / "AGENTS.md").write_text(proof_guidance, encoding="utf-8")
    bundle_agents = root / "src" / "odylith" / "bundle" / "assets" / "odylith"
    bundle_agents.mkdir(parents=True, exist_ok=True)
    (bundle_agents / "AGENTS.md").write_text(proof_guidance, encoding="utf-8")
    spec = (
        root
        / "odylith"
        / "registry"
        / "source"
        / "components"
        / "subagent-orchestrator"
        / "CURRENT_SPEC.md"
    )
    spec.parent.mkdir(parents=True, exist_ok=True)
    spec.write_text(
        "A subtask carries explicit owner, goal, expected output, termination condition, and validation commands.\n",
        encoding="utf-8",
    )
    required_surface_text = {
        "odylith/agents-guidelines/ODYLITH_CONTEXT_ENGINE.md": (
            "Guidance Behavior packets carry a compact `guidance_behavior_summary`; "
            "the full validator stays explicit.\n"
        ),
        "odylith/agents-guidelines/VALIDATION_AND_TESTING.md": (
            "Use odylith validate guidance-behavior --repo-root . and "
            "odylith benchmark --profile quick --family guidance_behavior across "
            "consumer, pinned dogfood, and source-local lanes.\n"
        ),
        "odylith/agents-guidelines/PRODUCT_SURFACES_AND_RUNTIME.md": (
            "Guidance Behavior aligns Context Engine, Execution Engine, Memory Contracts, "
            "Tribunal, and benchmark proof.\n"
        ),
        "odylith/agents-guidelines/SUBAGENT_ROUTING_AND_ORCHESTRATION.md": (
            "The guidance-bounded-delegation-contract requires owner, goal, expected output, "
            "termination condition, and validation expectation.\n"
        ),
        "odylith/agents-guidelines/CODEX_HOST_CONTRACT.md": (
            "Guidance Behavior on Codex keeps spawn_agent bounded and uses "
            "odylith validate guidance-behavior --repo-root .\n"
        ),
        "odylith/agents-guidelines/CLAUDE_HOST_CONTRACT.md": (
            "Guidance Behavior on Claude keeps Task-tool subagents bounded and uses "
            "odylith validate guidance-behavior --repo-root .\n"
        ),
        "odylith/skills/odylith-guidance-behavior/SKILL.md": (
            "Use this skill when guidance behavior pressure cases need proof.\n"
            "Run odylith validate guidance-behavior --repo-root . and "
            "odylith benchmark --profile quick --family guidance_behavior.\n"
            "Keep Codex and Claude behavior aligned across consumer lane, pinned dogfood, and source-local proof.\n"
        ),
        "src/odylith/bundle/assets/odylith/skills/odylith-guidance-behavior/SKILL.md": (
            "Use this skill when guidance behavior pressure cases need proof.\n"
            "Run odylith validate guidance-behavior --repo-root . and "
            "odylith benchmark --profile quick --family guidance_behavior.\n"
            "Keep Codex and Claude behavior aligned across consumer lane, pinned dogfood, and source-local proof.\n"
        ),
        "odylith/skills/odylith-context-engine-operations/SKILL.md": (
            "Guidance Behavior packets carry guidance_behavior_summary; the full validator is explicit.\n"
        ),
        "odylith/skills/odylith-subagent-orchestrator/SKILL.md": (
            "guidance-bounded-delegation-contract owner goal expected output termination condition "
            "validation expectation.\n"
        ),
        ".claude/commands/odylith-guidance-behavior.md": (
            "Run odylith validate guidance-behavior --repo-root . with $ARGUMENTS.\n"
            "Run odylith benchmark --profile quick --family guidance_behavior for quick benchmark proof.\n"
        ),
        "src/odylith/bundle/assets/project-root/.claude/commands/odylith-guidance-behavior.md": (
            "Run odylith validate guidance-behavior --repo-root . with $ARGUMENTS.\n"
            "Run odylith benchmark --profile quick --family guidance_behavior for quick benchmark proof.\n"
        ),
    }
    for relative_path, text in required_surface_text.items():
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    for skill_root in (
        root / ".agents" / "skills" / "fixture",
        root / "src" / "odylith" / "bundle" / "assets" / "project-root" / ".agents" / "skills" / "fixture",
    ):
        skill_root.mkdir(parents=True, exist_ok=True)
        description = skill_description
        target = "@../../../odylith/skills/fixture/SKILL.md"
        (skill_root / "SKILL.md").write_text(
            "---\n"
            f"name: {skill_root.name}\n"
            f"description: {description}\n"
            "---\n"
            f"{target}\n",
            encoding="utf-8",
        )
    for skill_root in (
        root / ".agents" / "skills" / "odylith-guidance-behavior",
        root
        / "src"
        / "odylith"
        / "bundle"
        / "assets"
        / "project-root"
        / ".agents"
        / "skills"
        / "odylith-guidance-behavior",
        root / ".claude" / "skills" / "odylith-guidance-behavior",
        root
        / "src"
        / "odylith"
        / "bundle"
        / "assets"
        / "project-root"
        / ".claude"
        / "skills"
        / "odylith-guidance-behavior",
    ):
        skill_root.mkdir(parents=True, exist_ok=True)
        (skill_root / "SKILL.md").write_text(
            "---\n"
            "name: odylith-guidance-behavior\n"
            "description: Use when guidance behavior pressure cases need deterministic proof.\n"
            "---\n"
            "@../../../odylith/skills/odylith-guidance-behavior/SKILL.md\n",
            encoding="utf-8",
        )

    def _ensure_tokens(relative_path: str, tokens: list[str]) -> None:
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        text = path.read_text(encoding="utf-8") if path.is_file() else ""
        additions = [token for token in dict.fromkeys(tokens) if token and token not in text]
        if additions:
            suffix = "" if text.endswith("\n") or not text else "\n"
            path.write_text(text + suffix + "\n".join(additions) + "\n", encoding="utf-8")

    source_tokens_by_path: dict[str, list[str]] = {}
    for contract in guidance_behavior_runtime_contracts.RUNTIME_LAYER_CONTRACTS:
        for relative_path, tokens in dict(contract.get("source_tokens", {})).items():
            source_tokens_by_path.setdefault(str(relative_path), [])
            source_tokens_by_path[str(relative_path)].extend(str(token) for token in tokens)
    for contract in guidance_behavior_platform_contracts.PLATFORM_CONTRACTS:
        for relative_path, tokens in dict(contract.get("source_tokens", {})).items():
            source_tokens_by_path.setdefault(str(relative_path), [])
            source_tokens_by_path[str(relative_path)].extend(str(token) for token in tokens)
    for relative_path, tokens in source_tokens_by_path.items():
        _ensure_tokens(relative_path, tokens)

    for relative_path in guidance_behavior_platform_contracts.ODYLITH_BUNDLE_MIRROR_PARITY_PATHS:
        live_path = root / relative_path
        if not live_path.is_file():
            live_path.parent.mkdir(parents=True, exist_ok=True)
            live_path.write_text("Guidance Behavior mirror parity fixture.\n", encoding="utf-8")
        mirror_path = (
            root
            / "src"
            / "odylith"
            / "bundle"
            / "assets"
            / "odylith"
            / Path(relative_path).relative_to("odylith")
        )
        mirror_path.parent.mkdir(parents=True, exist_ok=True)
        mirror_path.write_bytes(live_path.read_bytes())
    for relative_path in guidance_behavior_platform_contracts.PROJECT_ROOT_BUNDLE_MIRROR_PARITY_PATHS:
        live_path = root / relative_path
        if not live_path.is_file():
            live_path.parent.mkdir(parents=True, exist_ok=True)
            live_path.write_text("Guidance Behavior project-root mirror parity fixture.\n", encoding="utf-8")
        mirror_path = root / "src" / "odylith" / "bundle" / "assets" / "project-root" / relative_path
        mirror_path.parent.mkdir(parents=True, exist_ok=True)
        mirror_path.write_bytes(live_path.read_bytes())


def test_public_and_bundle_guidance_behavior_corpus_stay_aligned() -> None:
    assert json.loads(PUBLIC_CORPUS.read_text(encoding="utf-8")) == json.loads(
        BUNDLE_CORPUS.read_text(encoding="utf-8")
    )


def test_load_guidance_behavior_cases_reads_seeded_corpus() -> None:
    cases = validate_guidance_behavior.load_guidance_behavior_cases(repo_root=ROOT)

    case_ids = {case["id"] for case in cases}

    assert len(cases) == 6
    assert all(case["family"] == "guidance_behavior" for case in cases)
    assert {
        "guidance-ground-before-broad-search",
        "guidance-cli-first-governed-truth",
        "guidance-queue-non-adoption",
        "guidance-fresh-proof-completion-claim",
        "guidance-bounded-delegation-contract",
        "guidance-visible-intervention-proof",
    }.issubset(case_ids)


def test_missing_corpus_is_unavailable(tmp_path: Path) -> None:
    payload = validate_guidance_behavior.validate_guidance_behavior(repo_root=tmp_path)

    assert payload["status"] == "unavailable"
    assert payload["errors"][0]["check_id"] == "corpus_state"


def test_malformed_case_fails_before_guidance_checks(tmp_path: Path) -> None:
    broken = _case()
    broken.pop("prompt")
    _write_corpus(tmp_path, cases=[broken])
    _write_guidance_fixture(tmp_path)

    payload = validate_guidance_behavior.validate_guidance_behavior(repo_root=tmp_path)

    assert payload["status"] == "malformed"
    assert "missing `prompt`" in payload["errors"][0]["message"]
    assert payload["guidance_checks"] == []


def test_selected_case_filtering(tmp_path: Path) -> None:
    _write_corpus(tmp_path, cases=[_case("guidance-a"), _case("guidance-b")])
    _write_guidance_fixture(tmp_path)

    payload = validate_guidance_behavior.validate_guidance_behavior(repo_root=tmp_path, case_ids=["guidance-b"])

    assert payload["status"] == "passed"
    assert payload["selected_case_ids"] == ["guidance-b"]
    assert payload["case_count"] == 1


def test_unknown_case_id_is_input_malformed(tmp_path: Path) -> None:
    _write_corpus(tmp_path, cases=[_case("guidance-a")])
    _write_guidance_fixture(tmp_path)

    payload = validate_guidance_behavior.validate_guidance_behavior(repo_root=tmp_path, case_ids=["missing"])

    assert payload["status"] == "malformed"
    assert payload["errors"][0]["check_id"] == "case_selection"


def test_runtime_summary_is_compact_and_does_not_claim_full_validation(tmp_path: Path) -> None:
    _write_corpus(tmp_path, cases=[_case("guidance-a"), _case("guidance-b")])

    payload = guidance_behavior_runtime.guidance_behavior_runtime_summary(repo_root=tmp_path)

    assert payload["contract"] == "odylith_guidance_behavior_runtime_summary.v1"
    assert payload["family"] == "guidance_behavior"
    assert payload["status"] == "available"
    assert payload["validation_status"] == "not_run"
    assert payload["case_count"] == 2
    assert payload["selected_case_ids"] == ["guidance-a", "guidance-b"]
    assert payload["severity_counts"] == {"high": 2}
    assert payload["critical_or_high_case_count"] == 2
    assert len(payload["corpus_fingerprint"]) == 16
    assert payload["hot_path_contract"] == {
        "provider_calls": False,
        "repo_wide_scan": False,
        "context_store_expansion": False,
        "full_guidance_validation": False,
    }
    assert payload["runtime_layer_contract"]["layers"] == [
        "context_engine",
        "execution_engine",
        "memory_substrate",
        "intervention_engine",
        "tribunal",
    ]
    assert payload["runtime_layer_contract"]["hot_path"]["summary_only"] is True
    assert payload["guidance_surface_contract"]["hosts"] == ["codex", "claude"]
    assert payload["guidance_surface_contract"]["lanes"] == [
        "consumer",
        "pinned_dogfood",
        "source_local",
    ]
    assert payload["platform_contract"]["domains"] == [
        "benchmark_eval",
        "host_lane_bundle_mirrors",
        "hot_path_efficiency",
    ]
    assert payload["platform_contract"]["hot_path"]["repo_wide_scan"] is False
    assert payload["validator_command"].endswith("validate guidance-behavior --repo-root .")


def test_runtime_packet_summary_keeps_case_scoped_validation_command(tmp_path: Path) -> None:
    _write_corpus(tmp_path, cases=[_case("guidance-a"), _case("guidance-b")])

    payload = guidance_behavior_runtime.summary_for_packet(
        repo_root=tmp_path,
        family_hint="guidance_behavior",
        changed_paths=[],
        explicit_paths=[],
        docs=[],
        recommended_commands=[
            "odylith validate guidance-behavior --repo-root . --case-id guidance-b"
        ],
    )
    commands = guidance_behavior_runtime.commands_with_validator([], payload)

    assert payload["case_count"] == 1
    assert payload["selected_case_ids"] == ["guidance-b"]
    assert payload["case_validation_commands"] == [
        "odylith validate guidance-behavior --repo-root . --case-id guidance-b"
    ]
    assert commands == [
        "odylith validate guidance-behavior --repo-root . --case-id guidance-b",
        "odylith validate guidance-behavior --repo-root .",
    ]


def test_runtime_packet_summary_ignores_broad_guidance_files_without_guidance_family(tmp_path: Path) -> None:
    _write_corpus(tmp_path, cases=[_case("guidance-a")])

    payload = guidance_behavior_runtime.summary_for_packet(
        repo_root=tmp_path,
        family_hint="architecture",
        changed_paths=["AGENTS.md", "odylith/agents-guidelines/VALIDATION_AND_TESTING.md"],
        explicit_paths=[],
        docs=[],
        recommended_commands=[],
    )

    assert payload == {}


def test_summary_from_sources_canonicalizes_nested_and_direct_payloads() -> None:
    command = "odylith validate guidance-behavior --repo-root ."

    nested = guidance_behavior_runtime.summary_from_sources(
        {"unrelated": {"status": "ignored"}},
        {
            "guidance_behavior_summary": {
                "family": "guidance_behavior",
                "status": "available",
                "case_count": 2,
                "selected_case_ids": ["guidance-a", "guidance-b", "guidance-c"],
                "validator_command": command,
            }
        },
        limit=2,
    )
    direct = guidance_behavior_runtime.summary_from_sources(
        {
            "family": "guidance_behavior",
            "status": "failed",
            "validation_status": "failed",
            "failed_check_ids": ["guidance-contract"],
            "validator_command": command,
        },
    )

    assert nested == {
        "family": "guidance_behavior",
        "status": "available",
        "case_count": 2,
        "selected_case_ids": ["guidance-a", "guidance-b"],
        "validator_command": command,
    }
    assert direct["status"] == "failed"
    assert direct["failed_check_ids"] == ["guidance-contract"]
    assert guidance_behavior_runtime.validator_command_from_sources({"guidance_behavior_summary": direct}) == command


def test_runtime_summary_can_include_full_validation_failures(tmp_path: Path) -> None:
    _write_corpus(tmp_path)
    _write_guidance_fixture(tmp_path, skill_description="Fixture workflow summary.")

    payload = guidance_behavior_runtime.guidance_behavior_runtime_summary(
        repo_root=tmp_path,
        include_validation=True,
    )

    assert payload["status"] == "failed"
    assert payload["validation_status"] == "failed"
    assert "skill_description_trigger_only" in payload["failed_check_ids"]
    assert payload["tribunal_signal"]["operator_readout"]["severity"] == "p1"


def test_json_output_contract(tmp_path: Path, capsys) -> None:  # noqa: ANN001
    _write_corpus(tmp_path, cases=[_case("guidance-a")])
    _write_guidance_fixture(tmp_path)

    rc = validate_guidance_behavior.main(["--repo-root", str(tmp_path), "--json"])

    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert payload["contract"] == "odylith_guidance_behavior_validation.v1"
    assert payload["status"] == "passed"
    assert payload["selected_case_ids"] == ["guidance-a"]
    assert payload["critical_or_high_case_count"] == 1
    assert payload["check_count"] == len(payload["guidance_checks"])
    assert payload["guidance_checks"]


def test_skill_description_lint_requires_trigger_conditions(tmp_path: Path) -> None:
    _write_corpus(tmp_path)
    _write_guidance_fixture(tmp_path, skill_description="Build a fixture workflow summary.")

    payload = validate_guidance_behavior.validate_guidance_behavior(repo_root=tmp_path)

    assert payload["status"] == "failed"
    assert any(error["check_id"] == "skill_description_trigger_only" for error in payload["errors"])


def test_cli_first_guidance_lint_requires_governed_truth_cli_paths(tmp_path: Path) -> None:
    _write_corpus(tmp_path)
    _write_guidance_fixture(tmp_path)
    (tmp_path / "AGENTS.md").write_text("CLI-first only.\n", encoding="utf-8")

    payload = validate_guidance_behavior.validate_guidance_behavior(repo_root=tmp_path)

    assert payload["status"] == "failed"
    assert any(error["check_id"] == "cli_first_governed_truth" for error in payload["errors"])


def test_runtime_layer_integration_lint_requires_end_to_end_wires(tmp_path: Path) -> None:
    _write_corpus(tmp_path)
    _write_guidance_fixture(tmp_path)
    wire = tmp_path / "src" / "odylith" / "runtime" / "context_engine" / "execution_engine_handshake.py"
    wire.write_text("guidance_behavior_summary\nrecommended_validation\n", encoding="utf-8")

    payload = validate_guidance_behavior.validate_guidance_behavior(repo_root=tmp_path)

    assert payload["status"] == "failed"
    assert any(
        error["check_id"] == "guidance_behavior_runtime_layer_integration"
        and "validator_command" in error["message"]
        for error in payload["errors"]
    )


def test_guidance_surface_lint_requires_host_lane_guidance(tmp_path: Path) -> None:
    _write_corpus(tmp_path)
    _write_guidance_fixture(tmp_path)
    (
        tmp_path
        / "odylith"
        / "agents-guidelines"
        / "VALIDATION_AND_TESTING.md"
    ).write_text("generic validation guidance\n", encoding="utf-8")

    payload = validate_guidance_behavior.validate_guidance_behavior(repo_root=tmp_path)

    assert payload["status"] == "failed"
    assert any(
        error["check_id"] == guidance_behavior_guidance_contracts.CHECK_ID
        and "odylith validate guidance-behavior --repo-root ." in error["message"]
        for error in payload["errors"]
    )


def test_platform_lint_requires_benchmark_and_host_mirror_wires(tmp_path: Path) -> None:
    _write_corpus(tmp_path)
    _write_guidance_fixture(tmp_path)
    (
        tmp_path
        / "src"
        / "odylith"
        / "runtime"
        / "evaluation"
        / "odylith_benchmark_runner.py"
    ).write_text("guidance_behavior_runtime.summary_from_sources\n", encoding="utf-8")

    payload = validate_guidance_behavior.validate_guidance_behavior(repo_root=tmp_path)

    assert payload["status"] == "failed"
    assert any(
        error["check_id"] == guidance_behavior_platform_contracts.CHECK_ID
        and "_cache_profiles_for_selection" in error["message"]
        for error in payload["errors"]
    )


def test_platform_lint_rejects_stale_source_bundle_mirrors(tmp_path: Path) -> None:
    _write_corpus(tmp_path)
    _write_guidance_fixture(tmp_path)
    stale_mirror = (
        tmp_path
        / "src"
        / "odylith"
        / "bundle"
        / "assets"
        / "odylith"
        / "agents-guidelines"
        / "VALIDATION_AND_TESTING.md"
    )
    stale_mirror.write_text("stale validation guidance mirror\n", encoding="utf-8")

    payload = validate_guidance_behavior.validate_guidance_behavior(repo_root=tmp_path)

    assert payload["status"] == "failed"
    assert any(
        error["check_id"] == guidance_behavior_platform_contracts.CHECK_ID
        and error["path"].endswith("agents-guidelines/VALIDATION_AND_TESTING.md")
        and "mirror is stale" in error["message"]
        for error in payload["errors"]
    )


def test_corpus_rejects_external_guidance_refs(tmp_path: Path) -> None:
    _write_corpus(tmp_path, cases=[_case("guidance-a", related_refs=["../outside/README.md"])])

    payload = validate_guidance_behavior.validate_guidance_behavior(repo_root=tmp_path)

    assert payload["status"] == "malformed"
    assert "unsafe guidance ref" in payload["errors"][0]["message"]


def test_guidance_behavior_sources_use_repo_local_contracts_only() -> None:
    cases = validate_guidance_behavior.load_guidance_behavior_cases(repo_root=ROOT)
    source_paths = [
        ROOT / "src" / "odylith" / "runtime" / "governance" / "validate_guidance_behavior.py",
        ROOT / "src" / "odylith" / "runtime" / "governance" / "guidance_behavior_runtime.py",
        ROOT / "src" / "odylith" / "runtime" / "governance" / "guidance_behavior_guidance_contracts.py",
        ROOT / "src" / "odylith" / "runtime" / "governance" / "guidance_behavior_benchmark_contracts.py",
        ROOT / "src" / "odylith" / "runtime" / "governance" / "guidance_behavior_platform_contracts.py",
        ROOT / "src" / "odylith" / "runtime" / "governance" / "guidance_behavior_runtime_contracts.py",
        PUBLIC_CORPUS,
    ]

    for case in cases:
        for ref in case["related_guidance_refs"]:
            assert not str(ref).startswith("/")
            assert ".." not in Path(str(ref)).parts

    for path in source_paths:
        text = path.read_text(encoding="utf-8")
        assert "/Users/freedom/code/" not in text
        assert "github.com/obra" not in text
