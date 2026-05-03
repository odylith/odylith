import json
from pathlib import Path

from odylith.install.agents import managed_block
from odylith.runtime.analysis_engine import component_discovery
from odylith.runtime.analysis_engine import import_graph
from odylith.runtime.analysis_engine import repo_analysis
from odylith.runtime.analysis_engine import show_capabilities
from odylith.runtime.analysis_engine.show_capabilities import format_text
from odylith.runtime.analysis_engine.types import (
    ComponentSuggestion,
    DiagramSuggestion,
    ImportArtifact,
    IssueSuggestion,
    RepoIdentity,
    ShowResult,
    WorkstreamSuggestion,
)


def _write_file(repo_root: Path, rel_path: str, text: str = "") -> Path:
    path = repo_root / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _show_text(repo_root: Path) -> tuple[ShowResult, str]:
    result = show_capabilities.analyze_repo(repo_root)
    return result, format_text(result)


def _assert_no_trust_first_leaks(text: str) -> None:
    assert "Core Engine" not in text
    assert "Tests Registry component" not in text
    assert "Src Registry component" not in text
    assert "Document the " not in text
    assert "CI/CD" not in text


def test_show_text_reads_like_demo_copy_not_command_dump() -> None:
    result = ShowResult(
        identity=RepoIdentity(name="demo", languages=["Python"]),
        total_modules=12,
        already_governed={
            "backlog": True,
            "casebook": True,
            "registry": True,
            "atlas": True,
        },
        components=[
            ComponentSuggestion(
                component_id="dashboard",
                label="Dashboard",
                path="src/demo/dashboard",
                description="Dashboard surface",
                n_modules=8,
                n_inbound=42,
                n_outbound=3,
            )
        ],
        workstreams=[
            WorkstreamSuggestion(
                title="Clarify dashboard ownership",
                description="Dashboard changes cross several runtime paths.",
            )
        ],
        diagrams=[
            DiagramSuggestion(
                slug="dashboard-boundary",
                title="Dashboard Boundary Map",
                description="Show what the dashboard owns.",
            )
        ],
        issues=[
            IssueSuggestion(
                title="Dashboard stale refresh",
                detail="A stale refresh can hide the newest payload.",
            )
        ],
    )

    text = format_text(result)

    assert text.startswith("Odylith read this repo: Python, 8 app source files found.")
    assert "Registry names ownership, Radar tracks delivery, Atlas explains shape" in text
    assert "Odylith proposes them only from app-source evidence." in text
    assert "For more examples, open `odylith/index.html` and use the Cheatsheet." in text
    assert "It found 1 Registry component, 1 Radar workstream, 1 Atlas diagram, and 1 Casebook issue" in text
    assert "Say any prompt below verbatim, or use your own words." not in text
    assert "Best first move: **Dashboard Registry component**." in text
    assert "defining this logical boundary gives future changes a safer ownership anchor" in text
    assert "Registry candidates - 1 logical component" in text
    assert (
        "Defines: a logical Registry component; "
        "`src/demo/dashboard` is evidence, not the boundary itself."
        in text
    )
    assert (
        "Evidence: 8 source files anchored at `src/demo/dashboard`; "
        "42 inbound imports; 3 outbound imports."
        in text
    )
    assert "Prompt: `Define the Dashboard Registry component.`" in text
    assert "Why: Dashboard changes cross several runtime paths." in text
    assert "Prompt: `Open a Radar workstream for Clarify dashboard ownership.`" in text
    assert "Needs: Radar workstream, technical plan, and doc link before Atlas scaffold." not in text
    assert "Prompt: `Create the Dashboard Boundary Map Atlas diagram.`" in text
    assert "Prompt: `Capture a Casebook bug for Dashboard stale refresh." in text
    assert "### How to create things" not in text
    assert "Everything here: `Apply all suggestions from this Odylith show output.`" not in text
    assert "A custom slice: `Define an Odylith plan around <path or feature>" not in text
    assert "No files changed." in text
    assert "plain English" not in text
    assert "I can scaffold this as an Atlas source diagram." not in text
    assert "I can register this as a Registry boundary" not in text
    assert "Run any command to create it." not in text
    assert "odylith component register" not in text
    assert "odylith backlog create" not in text
    assert "odylith atlas scaffold" not in text
    assert "odylith bug capture" not in text


def test_show_cli_demo_stdout_stays_clean(monkeypatch, tmp_path, capsys) -> None:
    result = ShowResult(
        identity=RepoIdentity(name="demo", languages=["Python"]),
        total_modules=3,
        already_governed={
            "backlog": True,
            "casebook": True,
            "registry": True,
            "atlas": True,
        },
        components=[
            ComponentSuggestion(
                component_id="dashboard",
                label="Dashboard",
                path="src/demo/dashboard",
                description="Dashboard surface",
                n_modules=3,
                n_inbound=8,
                n_outbound=1,
            )
        ],
    )
    monkeypatch.setattr(show_capabilities, "analyze_repo", lambda repo_root: result)

    code = show_capabilities.main(["--repo-root", str(tmp_path)])

    captured = capsys.readouterr()
    assert code == 0
    assert captured.err == ""
    assert "Odylith read this repo:" in captured.out
    assert "Registry names ownership" in captured.out
    assert "Best first move:" in captured.out
    assert "Prompt: `Define the Dashboard Registry component.`" in captured.out
    assert "No files changed." in captured.out
    assert "intervention-status" not in captured.out
    assert "visible-intervention" not in captured.out
    assert "doctor" not in captured.out
    assert "odylith component register" not in captured.out


def test_show_import_graph_skips_transient_tmp_clone_trees(tmp_path: Path) -> None:
    real_source = tmp_path / "src" / "app.py"
    nested_tmp_source = tmp_path / "src" / "app" / "tmp" / "cache.py"
    tmp_source = tmp_path / "tmp" / "sim3-clone" / "app.py"
    real_source.parent.mkdir(parents=True)
    nested_tmp_source.parent.mkdir(parents=True)
    tmp_source.parent.mkdir(parents=True)
    real_source.write_text("import json\n", encoding="utf-8")
    nested_tmp_source.write_text("import pathlib\n", encoding="utf-8")
    tmp_source.write_text("import fastapi\n", encoding="utf-8")

    paths = sorted(
        path.relative_to(tmp_path).as_posix()
        for path in import_graph._iter_source_files(tmp_path)  # noqa: SLF001
    )

    assert paths == ["src/app.py", "src/app/tmp/cache.py"]


def test_show_import_graph_skips_root_odylith_but_keeps_product_source(tmp_path: Path) -> None:
    managed_source = tmp_path / "odylith" / "compass" / "runtime" / "current.v1.js"
    product_source = tmp_path / "src" / "odylith" / "cli.py"
    managed_source.parent.mkdir(parents=True)
    product_source.parent.mkdir(parents=True)
    managed_source.write_text("export const payload = {};\n", encoding="utf-8")
    product_source.write_text("import argparse\n", encoding="utf-8")

    paths = sorted(
        path.relative_to(tmp_path).as_posix()
        for path in import_graph._iter_source_files(tmp_path)  # noqa: SLF001
    )

    assert paths == ["src/odylith/cli.py"]


def test_show_import_graph_keeps_real_root_odylith_package_without_managed_markers(tmp_path: Path) -> None:
    package_init = tmp_path / "odylith" / "__init__.py"
    package_core = tmp_path / "odylith" / "core.py"
    package_init.parent.mkdir(parents=True)
    package_init.write_text("", encoding="utf-8")
    package_core.write_text("import json\n", encoding="utf-8")

    paths = sorted(
        path.relative_to(tmp_path).as_posix()
        for path in import_graph._iter_source_files(tmp_path)  # noqa: SLF001
    )

    assert paths == ["odylith/__init__.py", "odylith/core.py"]


def test_show_source_classifier_covers_trust_first_categories(tmp_path: Path) -> None:
    repo_root = tmp_path / "classifier"
    files = {
        "src/app.py": repo_analysis.SOURCE_CATEGORY_APP,
        "tests/test_app.py": repo_analysis.SOURCE_CATEGORY_TEST,
        "scripts/build.py": repo_analysis.SOURCE_CATEGORY_SUPPORT,
        "infra/main.tf": repo_analysis.SOURCE_CATEGORY_INFRA,
        "README.md": repo_analysis.SOURCE_CATEGORY_DOCS,
        "package.json": repo_analysis.SOURCE_CATEGORY_METADATA,
        "tmp/clone/app.py": repo_analysis.SOURCE_CATEGORY_ROOT_NOISE,
        "dist/generated.js": repo_analysis.SOURCE_CATEGORY_GENERATED,
        "odylith/AGENTS.md": repo_analysis.SOURCE_CATEGORY_MANAGED,
        "odylith/compass/runtime/current.v1.js": repo_analysis.SOURCE_CATEGORY_MANAGED,
    }
    for rel_path in files:
        _write_file(repo_root, rel_path, "export const value = 1;\n")

    for rel_path, category in files.items():
        assert repo_analysis.classify_repo_path(repo_root / rel_path, repo_root=repo_root) == category


def test_show_minimal_source_copy_does_not_emit_this_codebase_grammar_glitch(tmp_path: Path) -> None:
    package_init = tmp_path / "pkg" / "__init__.py"
    package_core = tmp_path / "pkg" / "core.py"
    package_init.parent.mkdir(parents=True)
    package_init.write_text("", encoding="utf-8")
    package_core.write_text("import json\n", encoding="utf-8")

    text = format_text(show_capabilities.analyze_repo(tmp_path))

    assert "the this codebase" not in text
    assert "2 app source files found, but not enough stable structure" in text
    assert "Draft a greenfield Odylith proposal for <project, architecture, or research goal>" in text
    assert "add source files" not in text


def test_show_empty_consumer_repo_does_not_suggest_odylith_managed_tree(tmp_path: Path) -> None:
    repo_root = tmp_path / "mockrepo"
    managed_runtime = repo_root / "odylith" / "compass" / "runtime"
    managed_runtime.mkdir(parents=True)
    (managed_runtime / "current.v1.js").write_text("export const current = {};\n", encoding="utf-8")
    (managed_runtime / "history.v1.js").write_text("export const history = [];\n", encoding="utf-8")
    (repo_root / "odylith" / "radar" / "source" / "ideas").mkdir(parents=True)
    (repo_root / "odylith" / "registry" / "source" / "components").mkdir(parents=True)

    result = show_capabilities.analyze_repo(repo_root)
    text = format_text(result)

    assert result.total_modules == 0
    assert result.components == []
    assert result.workstreams == []
    assert result.diagrams == []
    assert "only Odylith-managed install/governance files were found" in text
    assert "Draft a greenfield Odylith proposal for <project, architecture, or research goal>" in text
    assert "Run `odylith show` again after adding source files." not in text
    assert "Core Engine" not in text
    assert "Document the mockrepo" not in text
    assert "CI/CD" not in text


def test_show_monorepo_workspace_does_not_suggest_managed_odylith_tree(tmp_path: Path) -> None:
    repo_root = tmp_path / "mockrepo"
    managed_runtime = repo_root / "odylith" / "compass" / "runtime"
    managed_runtime.mkdir(parents=True)
    (managed_runtime / "current.v1.js").write_text("export const current = {};\n", encoding="utf-8")
    (managed_runtime / "history.v1.js").write_text("export const history = [];\n", encoding="utf-8")
    (repo_root / "package.json").write_text(
        '{"name": "mockrepo", "workspaces": ["odylith/*"]}\n',
        encoding="utf-8",
    )

    result = show_capabilities.analyze_repo(repo_root)
    text = format_text(result)

    assert result.total_modules == 0
    assert result.components == []
    assert result.workstreams == []
    assert result.diagrams == []
    assert "JavaScript metadata is present, but no application source was found." in text
    assert "Core Engine" not in text
    assert "Document the mockrepo" not in text
    assert "CI/CD" not in text


def test_show_empty_readme_manifest_tests_infra_and_thin_app_scenarios_are_quiet(tmp_path: Path) -> None:
    scenarios = {
        "empty": ([], "no application source was found."),
        "docs-only": ([("README.md", "# Demo\n")], "documentation was found, but no application source was found."),
        "metadata-only": ([("pyproject.toml", "[project]\nname='demo'\n")], "Python metadata is present, but no application source was found."),
        "tests-only": ([("tests/test_api.py", "# TODO: track real product issue here\n")], "tests/support source was found, but no application source was found."),
        "infra-only": ([(".github/workflows/ci.yml", "name: ci\n"), ("infra/main.tf", "")], "only infra/CI project assets were found"),
        "thin-app": ([("src/demo/app.py", "import json\n"), ("src/demo/config.py", "")], "2 app source files found, but not enough stable structure"),
    }
    teaching = {
        "empty": "confirmation-gated greenfield proposal",
        "docs-only": "will not turn documentation alone into governance records",
        "metadata-only": "Manifests identify the stack, but they are not an ownership boundary",
        "tests-only": "Tests prove behavior, but they are not the application boundary",
        "infra-only": "Infra and CI describe deployment mechanics, not app ownership",
        "thin-app": "Thin source exists, so Odylith will not invent a boundary",
    }

    for name, (files, expected) in scenarios.items():
        repo_root = tmp_path / name
        repo_root.mkdir()
        for rel_path, text in files:
            _write_file(repo_root, rel_path, text)

        result, text = _show_text(repo_root)

        assert result.scenario == name
        assert expected in text
        assert teaching[name] in text
        if name != "empty":
            assert "For more examples, open `odylith/index.html` and use the Cheatsheet." in text
        assert "Draft a greenfield Odylith proposal for <project, architecture, or research goal>" in text
        assert "No files changed." in text
        assert result.components == []
        assert result.workstreams == []
        assert result.diagrams == []
        assert result.issues == []
        _assert_no_trust_first_leaks(text)
        if name == "thin-app":
            assert "add source files" not in text


def test_show_managed_only_repo_ignores_odylith_assets(tmp_path: Path) -> None:
    repo_root = tmp_path / "managed"
    _write_file(repo_root, "odylith/AGENTS.md", "# Managed\n")
    _write_file(repo_root, "odylith/compass/runtime/current.v1.js", "export const current = {};\n")
    _write_file(repo_root, "odylith/registry/source/component_registry.v1.json", '{"components":[]}\n')

    result, text = _show_text(repo_root)

    assert result.scenario == "managed-only"
    assert result.app_modules == 0
    assert result.source_summary.managed_files == 3
    assert "only Odylith-managed install/governance files were found" in text
    assert "Odylith-managed files belong to Odylith, not your app" in text
    _assert_no_trust_first_leaks(text)


def test_show_flat_src_app_uses_repo_label_not_src(tmp_path: Path) -> None:
    repo_root = tmp_path / "billing-service"
    _write_file(repo_root, "src/main.py", "import json\n")
    _write_file(repo_root, "src/routes.py", "from . import main\n")
    _write_file(repo_root, "src/models.py", "from . import routes\n")

    result, text = _show_text(repo_root)

    assert result.scenario == "app-ready"
    assert result.app_modules == 3
    assert result.components
    assert result.components[0].label == "Billing Service"
    assert "Registry names ownership, Radar tracks delivery, Atlas explains shape" in text
    assert "Billing Service Registry component" in text
    assert "Src Registry component" not in text
    assert "Document the billing-service" in text
    assert "CI/CD" in text


def test_show_generic_src_app_uses_application_label_not_temp_repo_name(tmp_path: Path) -> None:
    repo_root = tmp_path / "tmp.random-demo"
    for name in ("main.py", "routes.py", "models.py"):
        _write_file(repo_root, f"src/app/{name}", "import json\n")

    result, text = _show_text(repo_root)

    assert result.scenario == "app-ready"
    assert result.components[0].label == "Application"
    assert "Application Registry component" in text
    assert "Document the Application Architecture" in text
    assert "Tmp Random Demo Registry component" not in text
    assert "tmp.random-demo" not in text


def test_show_monorepo_suggests_confident_workspace_boundaries(tmp_path: Path) -> None:
    repo_root = tmp_path / "workspace"
    _write_file(repo_root, "package.json", '{"name": "workspace", "workspaces": ["packages/*"]}\n')
    for package in ("api", "web"):
        for name in ("index.ts", "routes.ts", "client.ts"):
            _write_file(repo_root, f"packages/{package}/src/{name}", "export const value = 1;\n")
    _write_file(repo_root, "packages/thin/src/index.ts", "export const value = 1;\n")

    result, text = _show_text(repo_root)

    labels = {component.label for component in result.components}
    assert result.scenario == "app-ready"
    assert labels == {"Api", "Web"}
    assert "Thin Registry component" not in text
    assert "Api Registry component" in text
    assert "Web Registry component" in text


def test_show_app_plus_managed_assets_analyzes_only_app_source(tmp_path: Path) -> None:
    repo_root = tmp_path / "hybrid"
    _write_file(repo_root, "odylith/AGENTS.md", "# Managed\n")
    _write_file(repo_root, "odylith/compass/runtime/current.v1.js", "export const current = {};\n")
    for name in ("app.py", "routes.py", "models.py"):
        _write_file(repo_root, f"src/hybrid/{name}", "import json\n")

    result, text = _show_text(repo_root)

    assert result.scenario == "app-ready"
    assert result.app_modules == 3
    assert result.total_modules == 3
    assert result.source_summary.managed_files == 2
    assert "Core Engine" not in text
    assert "Hybrid Registry component" in text


def test_show_existing_governance_suppresses_duplicate_candidates(tmp_path: Path) -> None:
    repo_root = tmp_path / "governed"
    for name in ("app.py", "routes.py", "models.py"):
        _write_file(repo_root, f"src/governed/{name}", "import json\n")
    _write_file(
        repo_root,
        "odylith/registry/source/component_registry.v1.json",
        '{"components":[{"component_id":"governed","path_prefixes":["src/governed"]}]}\n',
    )

    result, text = _show_text(repo_root)

    assert result.components == []
    assert result.workstreams == []
    assert result.diagrams == []
    assert result.scenario == "already-governed"
    assert "existing Registry already covers this scan" in text
    assert "extend it instead of duplicating records" in text
    assert "Define an Odylith plan around <path or feature>" in text
    assert "Registry candidates" not in text


def test_show_casebook_candidates_only_come_from_app_source(tmp_path: Path) -> None:
    repo_root = tmp_path / "issues"
    _write_file(repo_root, "tests/test_bug.py", "# TODO: this test reminder should not become a Casebook candidate\n")
    for name in ("app.py", "routes.py", "models.py"):
        _write_file(repo_root, f"src/issues/{name}", "import json\n")

    result, text = _show_text(repo_root)

    assert result.issues == []
    assert "test reminder" not in text

    _write_file(repo_root, "src/issues/models.py", "# TODO: reconcile production billing state drift\n")
    result, text = _show_text(repo_root)

    assert result.issues
    assert "production billing state drift" in text


def test_show_json_adds_scenario_and_source_summary_fields(tmp_path: Path) -> None:
    repo_root = tmp_path / "json-demo"
    for name in ("app.py", "routes.py", "models.py"):
        _write_file(repo_root, f"src/json_demo/{name}", "import json\n")

    result = show_capabilities.analyze_repo(repo_root)
    payload = json.loads(show_capabilities.format_json(result))

    assert payload["scenario"] == "app-ready"
    assert payload["teaching"].startswith("Mental model: Registry names ownership")
    assert payload["cheatsheet_hint"] == "For more examples, open `odylith/index.html` and use the Cheatsheet."
    assert payload["next_prompt"].startswith("Define the Json Demo Registry component.")
    assert payload["total_modules"] == 3
    assert payload["app_modules"] == 3
    assert payload["support_modules"] == 0
    assert payload["source_summary"]["app_modules"] == 3
    assert payload["components"][0]["confidence"] in {"medium", "high"}
    assert "components" in payload
    assert "workstreams" in payload
    assert "diagrams" in payload
    assert "issues" in payload


def test_show_me_skill_blocks_host_status_detours() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    source_skill = (repo_root / "odylith" / "skills" / "odylith-show-me" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    bundle_skill = (
        repo_root
        / "src"
        / "odylith"
        / "bundle"
        / "assets"
        / "odylith"
        / "skills"
        / "odylith-show-me"
        / "SKILL.md"
    ).read_text(encoding="utf-8")
    assert bundle_skill == source_skill

    skill_paths = [
        repo_root / ".agents" / "skills" / "odylith-show-me" / "SKILL.md",
        repo_root / ".claude" / "skills" / "odylith-show-me" / "SKILL.md",
        repo_root / "odylith" / "skills" / "odylith-show-me" / "SKILL.md",
        repo_root
        / "src"
        / "odylith"
        / "bundle"
        / "assets"
        / "project-root"
        / ".agents"
        / "skills"
        / "odylith-show-me"
        / "SKILL.md",
        repo_root
        / "src"
        / "odylith"
        / "bundle"
        / "assets"
        / "odylith"
        / "skills"
        / "odylith-show-me"
        / "SKILL.md",
        repo_root
        / "src"
        / "odylith"
        / "bundle"
        / "assets"
        / "project-root"
        / ".claude"
        / "skills"
        / "odylith-show-me"
        / "SKILL.md",
    ]

    for path in skill_paths:
        text = path.read_text(encoding="utf-8")
        normalized_text = " ".join(text.split())
        if "@../../../odylith/skills/odylith-show-me/SKILL.md" in text:
            assert "clean scenario-aware show-me output" in text
            assert "with CLI commands" not in text
        else:
            assert "Run the first available show command" in text
            assert "Do not use this skill for `Odylith, help`." in text
            assert "PYTHONPATH=src python -m odylith.cli show --repo-root ." not in text
            assert "`./.odylith/bin/odylith show --repo-root .`" in text
            assert "`odylith show --repo-root .`" in text
            assert "`intervention-status`, `visible-intervention`" in text
            assert "not proof" in text
            assert "capture stdout only" in text
            assert "scenario-aware output" in text
            assert "trust-first action report" in text
            assert "short mental-model" in text
            assert "Do not summarize" in text
            assert "first-match route lock" in text
            assert "If you have not run a show command and captured stdout, do not answer" in normalized_text
            assert "Never replace `odylith show` stdout" in normalized_text
            assert "here's what Odylith demonstrated" in normalized_text
            assert "dirty-path analysis" in normalized_text
            assert "impact-packet recap" in normalized_text
            assert "module-count scan" in normalized_text
            assert "tmp-clone warning" in normalized_text
            assert "spawn-policy note" in normalized_text
            assert "Do not add bullets before or after it" in normalized_text


def test_claude_show_me_guard_is_shipped_in_project_assets() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    guard_paths = [
        repo_root / ".claude" / "hooks" / "show-me-prompt-guard.py",
        repo_root
        / "src"
        / "odylith"
        / "bundle"
        / "assets"
        / "project-root"
        / ".claude"
        / "hooks"
        / "show-me-prompt-guard.py",
    ]

    for path in guard_paths:
        text = path.read_text(encoding="utf-8")
        assert "Odylith show-me first-match route" in text
        assert "Odylith help first-match route" in text
        assert "route lock" in text
        assert "must not answer as generic Claude" in text
        assert "list Claude tool, skill, or memory inventories" in text
        assert "odylith-show-me" in text
        assert "PYTHONPATH=src python -m odylith.cli show --repo-root ." not in text
        assert "`./.odylith/bin/odylith --help`" in text
        assert "`odylith --help`" in text
        assert "`./.odylith/bin/odylith show --repo-root .`" in text
        assert "`odylith show --repo-root .`" in text
        assert "`intervention-status`, `visible-intervention`" in text


def test_managed_guidance_exempts_show_me_from_intervention_proof() -> None:
    block = managed_block(repo_role="product_repo")

    assert "Odylith, help" in block
    assert "CLI help fast path" in block
    assert "Odylith, show me what you can do" in block
    assert "advisory `odylith show` repo-capability demo" in block
    assert "not a request to prove intervention UX" in block
    assert "run `doctor`" in block
    assert "explain missing launcher state" in block
    assert "print stdout only" in block


def test_component_discovery_uses_real_anchor_for_logical_candidates() -> None:
    artifacts = [
        *[
            ImportArtifact(
                path=f"src/demo/runtime/surfaces/{name}_{idx}.py",
                module_name=f"demo.runtime.surfaces.{name}_{idx}",
                language="python",
                imports=(),
            )
            for idx, name in enumerate(
                [
                    "render_backlog",
                    "render_registry",
                    "render_compass",
                    "render_casebook",
                    "dashboard_shell",
                    "surface_bundle",
                    "brand_assets",
                    "tooling_frontend",
                    "layout_audit",
                    "deep_link",
                    "payload_builder",
                    "template_runtime",
                    "workstream_button",
                    "kpi_cards",
                    "release_targets",
                    "program_cards",
                ]
            )
        ],
        *[
            ImportArtifact(
                path=f"src/demo/runtime/common/{name}_{idx}.py",
                module_name=f"demo.runtime.common.{name}_{idx}",
                language="python",
                imports=(),
            )
            for idx, name in enumerate(
                [
                    "paths",
                    "json_cache",
                    "profile",
                    "clock",
                    "logging",
                    "checksum",
                    "filesystem",
                    "runtime_contract",
                    "process",
                    "repo_shape",
                    "dirty_overlap",
                    "command_surface",
                    "stable_utc",
                    "guidance_paths",
                    "budget_policy",
                    "casebook_ids",
                ]
            )
        ],
        *[
            ImportArtifact(
                path=f"src/demo/runtime/governance/{name}_{idx}.py",
                module_name=f"demo.runtime.governance.{name}_{idx}",
                language="python",
                imports=(),
            )
            for idx, name in enumerate(
                [
                    "component_authoring",
                    "backlog_authoring",
                    "sync_workstream",
                    "validate_backlog",
                    "delivery_intelligence",
                    "traceability",
                    "release_planning",
                    "casebook_validation",
                    "registry_intelligence",
                    "owned_refresh",
                    "plan_binding",
                    "wave_contract",
                    "risk_mitigation",
                    "scope_signal",
                    "governance_slice",
                    "capture_apply",
                ]
            )
        ],
    ]

    components = component_discovery.discover_components_from_imports(Path("."), artifacts, [])
    dashboard = next(component for component in components if component.label == "Dashboard")

    assert dashboard.component_id == "dashboard"
    assert dashboard.path == "src/demo/runtime/surfaces"
    assert dashboard.path != "src/demo/runtime/surfaces/core"
    assert len(dashboard.member_paths) == 16
    assert all(path.startswith("src/demo/runtime/surfaces/") for path in dashboard.member_paths)
    assert "16 source files anchored at `src/demo/runtime/surfaces`" in dashboard.evidence


def test_component_discovery_does_not_promote_tests_to_components() -> None:
    artifacts = [
        ImportArtifact(
            path=f"tests/test_feature_{idx}.py",
            module_name=f"tests.test_feature_{idx}",
            language="python",
            imports=(),
        )
        for idx in range(4)
    ]

    components = component_discovery.discover_components_from_imports(Path("."), artifacts, [])

    assert components == []
