from __future__ import annotations

from odylith.runtime.context_engine import tooling_context_routing_support as support


def test_normalized_string_list_preserves_context_routing_row_semantics() -> None:
    assert support.normalized_string_list([" path/a.py ", "", "path/a.py", "keep  spacing"]) == [
        "path/a.py",
        "path/a.py",
        "keep  spacing",
    ]
    assert support.normalized_string_list(" one  command ") == ["one  command"]
    assert support.normalized_string_list(None) == []


def test_count_or_list_len_preserves_non_empty_list_counting() -> None:
    assert (
        support.count_or_list_len(
            {"strict_gate_commands": ["pytest", "", [], {}, None, " "], "strict_gate_command_count": 0},
            list_key="strict_gate_commands",
            count_key="strict_gate_command_count",
        )
        == 2
    )
    assert (
        support.count_or_list_len(
            {"strict_gate_commands": "pytest", "strict_gate_command_count": 3},
            list_key="strict_gate_commands",
            count_key="strict_gate_command_count",
        )
        == 3
    )


def test_fallback_anchor_commands_quote_paths_and_docs() -> None:
    command, followup = support.fallback_anchor_commands(
        {"kind": "doc", "value": "docs/path with spaces.md"}
    )

    assert command == "./.odylith/bin/odylith context --repo-root . 'docs/path with spaces.md'"
    assert followup == "sed -n '1,200p' 'docs/path with spaces.md'"


def test_fallback_scan_commands_preserve_first_retained_path_followup() -> None:
    command, followup = support.fallback_scan_commands(
        fallback_scan={"query": "tenant boundary", "changed_paths": ["src/a.py"]},
        retained_paths=["src/a.py", "src/b.py"],
    )

    assert command == "rg -n --context 2 'tenant boundary' -- src/a.py src/b.py"
    assert followup == "sed -n '1,200p' src/a.py"


def test_fallback_scan_commands_keep_default_grounding_command() -> None:
    command, followup = support.fallback_scan_commands(fallback_scan={}, retained_paths=[])

    assert command == r"rg --files | rg 'AGENTS\.md|CLAUDE\.md|odylith/(AGENTS|CLAUDE)\.md|pyproject\.toml'"
    assert followup == "if [ -f AGENTS.md ]; then sed -n '1,200p' AGENTS.md; else sed -n '1,200p' CLAUDE.md; fi"
