import re
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SKIP_RUNTIME_HISTORY_PREFIXES = (
    "odylith/compass/runtime/current.v1.js",
    "odylith/compass/runtime/current.v1.json",
    "odylith/compass/runtime/history/",
    "src/odylith/bundle/assets/odylith/compass/runtime/current.v1.js",
    "src/odylith/bundle/assets/odylith/compass/runtime/current.v1.json",
    "src/odylith/bundle/assets/odylith/compass/runtime/history/",
)

# Rendered Radar shards embed plan/idea markdown content verbatim; technical
# plan files document the patterns they guard against.  Neither represents a
# real legacy-code import or brand leak in product source.
_SKIP_RENDERED_SURFACE_AND_PLAN_PREFIXES: tuple[str, ...] = (
    "odylith/radar/backlog-document-shard-",
    "odylith/radar/backlog-detail-shard-",
    "odylith/radar/standalone-pages.",
    "odylith/technical-plans/",
    "src/odylith/bundle/assets/odylith/radar/backlog-document-shard-",
    "src/odylith/bundle/assets/odylith/radar/backlog-detail-shard-",
    "src/odylith/bundle/assets/odylith/radar/standalone-pages.",
    "src/odylith/bundle/assets/odylith/technical-plans/",
)
STARTER_PROMPT_BLOCK = """Here are some starter prompt inspirations:

`Backlog`
- Create: "Create a new backlog item and queue it for [codepath {or} backlog item description]."
- Edit: "Tighten the Radar item for [B###]."
- Delete: "Drop the Radar item [B###]"

`Components`
- Create: "Define the Registry component for [component description]."
- Edit: "Tighten the Registry boundary for [component]."
- Delete: "Drop the Registry component for [component]"

`Diagrams`
- Create: "Draw the Atlas diagram for [codepath]."
- Edit: "Update the Atlas diagram for [codepath]."
- Delete: "Drop the Atlas diagram [D###]."

`Developer Notes`
- Create: "Add developer note [Note Brief]."
- Edit: "Update developer note [N###] with [...]."
- Delete: "Delete developer note [N###]."
"""

README_PROOF_BENCHMARK_GRAPH_BLOCK = """<p align="center">
  <img
    src="docs/benchmarks/proof/odylith-benchmark-family-heatmap.svg"
    alt="Odylith live benchmark family heatmap"
    width="100%"
  />
</p>
<p align="center">
  <img
    src="docs/benchmarks/proof/odylith-benchmark-quality-frontier.svg"
    alt="Odylith live benchmark quality frontier"
    width="100%"
  />
</p>
<p align="center">
  <img
    src="docs/benchmarks/proof/odylith-benchmark-frontier.svg"
    alt="Odylith live benchmark frontier"
    width="100%"
  />
</p>
<p align="center">
  <img
    src="docs/benchmarks/proof/odylith-benchmark-operating-posture.svg"
    alt="Odylith live benchmark operating posture"
    width="100%"
  />
</p>
"""

README_DIAGNOSTIC_BENCHMARK_GRAPH_BLOCK = """<p align="center">
  <img
    src="docs/benchmarks/diagnostic/odylith-benchmark-family-heatmap.svg"
    alt="Odylith grounding benchmark family heatmap"
    width="100%"
  />
</p>
<p align="center">
  <img
    src="docs/benchmarks/diagnostic/odylith-benchmark-quality-frontier.svg"
    alt="Odylith grounding benchmark quality frontier"
    width="100%"
  />
</p>
<p align="center">
  <img
    src="docs/benchmarks/diagnostic/odylith-benchmark-frontier.svg"
    alt="Odylith grounding benchmark frontier"
    width="100%"
  />
</p>
<p align="center">
  <img
    src="docs/benchmarks/diagnostic/odylith-benchmark-operating-posture.svg"
    alt="Odylith grounding benchmark operating posture"
    width="100%"
  />
</p>
"""

BENCHMARK_ANTI_GAMING_LINE = "- Never game the eval."
BENCHMARK_HONEST_BASELINE_LINES = (
    "`odylith_off` means `raw_agent_baseline`",
    "`Odylith off` means `raw_agent_baseline`",
    "`odylith_off` is the raw host CLI lane",
    "`odylith_off` is the honest raw host CLI baseline",
    "`odylith_off` is the public name for the raw host CLI lane",
    "`odylith_off` is the reviewer-facing and README-facing name for the raw host CLI lane",
    "`odylith_off` in README, graphs, and review framing is the raw host CLI lane",
)
ODYLITH_ASSIST_LABEL = "`Odylith Assist:`"
ODYLITH_ASSIST_MARKDOWN_LABEL = "`**Odylith Assist:**`"
ODYLITH_ASSIST_TONE = "crisp, authentic, clear, simple, insightful"
ODYLITH_ASSIST_MIXED_EVIDENCE = "observed counts, measured deltas, or validation outcomes"
ODYLITH_ASSIST_USER_WIN = "Lead with the user win"
ODYLITH_ASSIST_UPDATED_IDS = "updated governance IDs inline"
ODYLITH_ASSIST_AFFECTED_IDS = "affected governance-contract IDs"
ODYLITH_ASSIST_UNGUIDED_PATH = "broader unguided path"
ODYLITH_CHATTER_SPEC_TOKEN = "odylith-chatter/CURRENT_SPEC.md"
ODYLITH_ASSIST_METADATA_ONLY = "metadata-only"
ODYLITH_AMBIENT_SIGNAL_LABELS = "`Odylith Insight:`, `Odylith History:`, or `Odylith Risks:`"
ODYLITH_SILENCE_RULE = "Silence is better than filler"
LEGACY_CONSUMER_CHATTER_FRAGMENTS = (
    "must ground in Odylith first",
    "Direct repo scan before Odylith grounding is a policy violation",
    "keep Odylith grounding mostly in the background. Do not require a fixed visible prefix",
    "run Odylith grounding",
    "keep Odylith in the background. Describe progress in task terms like narrowing the slice",
    "Avoid control-plane receipts such as",
    "Odylith grounding:",
    "Odylith didn't return immediately",
    "Mention Odylith during the work only for literal commands, current blockers, or maintainer-lane distinctions.",
    "Mention Odylith during the work only for literal commands, current blockers, or consumer-versus-maintainer lane distinctions.",
    "Mention Odylith during the work only when you need to show a literal command",
    "Odylith routed this slice",
    "had already degraded earlier",
    "raw repo inspection",
    "live evidence says",
    "Odylith-first guidance is active again.",
    "Odylith-first guidance is now detached.",
    "First grounded turn:",
)
RUNTIME_CHATTER_FRAGMENTS = (
    "Odylith kept",
    "Odylith control advisories",
    "Odylith self-evaluation",
    "odylith runtime ",
    "The Odylith runtime handoff",
    "The retained Odylith packet",
    "recent Odylith ",
)
INTERVENTION_CONTRACT_BUNDLE_EXPECTATIONS: tuple[tuple[str, bool], ...] = (
    ("odylith/agents-guidelines/CODEX_HOST_CONTRACT.md", True),
    ("odylith/agents-guidelines/CLAUDE_HOST_CONTRACT.md", True),
    ("odylith/agents-guidelines/PRODUCT_SURFACES_AND_RUNTIME.md", True),
    ("odylith/registry/source/components/compass/CURRENT_SPEC.md", True),
    ("odylith/registry/source/components/delivery-intelligence/CURRENT_SPEC.md", True),
    ("odylith/registry/source/components/execution-engine/CURRENT_SPEC.md", True),
    ("odylith/registry/source/components/governance-intervention-engine/CURRENT_SPEC.md", True),
    ("odylith/registry/source/components/odylith-chatter/CURRENT_SPEC.md", True),
    ("odylith/registry/source/components/proof-state/CURRENT_SPEC.md", True),
    (
        "odylith/radar/source/ideas/2026-04/2026-04-14-conversation-observation-engine-governed-proposal-flow-and-human-intervention-voice-contract.md",
        False,
    ),
    (
        "odylith/technical-plans/in-progress/2026-04/2026-04-14-conversation-observation-engine-governed-proposal-flow-and-human-intervention-voice-contract.md",
        False,
    ),
)


def test_public_tree_contains_no_legacy_contract_leaks() -> None:
    legacy_consumer_brand = "".join(("ori", "on"))
    needles = [
        "tests/scripts/",
        "backlog/ui/",
        "tools/",
        "python -m " + "scripts",
        "python -m odylith.cli",
        "prog=\"python -m " + "scripts",
        "from " + "scripts.",
        "import " + "scripts.",
        legacy_consumer_brand + "_repo" + ".yaml",
        legacy_consumer_brand,
    ]
    regexes = [
        re.compile(r'repo_root\s*/\s*"tools"'),
        re.compile(r'Path\(repo_root\)\.resolve\(\)\s*/\s*"tools"'),
        re.compile(r'explicit_prefixes\.issubset\(\{"tools"'),
    ]
    failures: list[str] = []
    for base in (ROOT / "src", ROOT / "docs", ROOT / "odylith"):
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            relative = str(path.relative_to(ROOT))
            if any(
                relative.startswith(prefix)
                for prefix in SKIP_RUNTIME_HISTORY_PREFIXES + _SKIP_RENDERED_SURFACE_AND_PLAN_PREFIXES
            ):
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            lowered = text.lower()
            if any(needle in lowered for needle in needles) or any(regex.search(text) for regex in regexes):
                failures.append(relative)
    assert not failures, f"legacy public-contract leaks remain in: {failures}"


def test_public_architecture_source_is_repo_generic() -> None:
    source = (ROOT / "src" / "odylith" / "runtime" / "context_engine" / "odylith_architecture_mode.py").read_text(encoding="utf-8")
    forbidden = (
        "control-plane",
        "shared-services",
        "shared-kafka",
        "cell-infra",
        "service-manifests",
        "wave-deploy",
    )
    for token in forbidden:
        assert token not in source, f"public architecture source still embeds consumer topology token {token!r}"


def test_public_architecture_corpus_stays_product_generic() -> None:
    for path in (
        ROOT / "odylith" / "runtime" / "source" / "optimization-evaluation-corpus.v1.json",
        ROOT / "src" / "odylith" / "bundle" / "assets" / "odylith" / "runtime" / "source" / "optimization-evaluation-corpus.v1.json",
    ):
        text = path.read_text(encoding="utf-8")
        assert "architecture-control-plane-watch-gap" not in text
        assert "architecture-control-plane-grounded" not in text


def test_public_registry_truth_contains_no_internal_bundle_asset_paths() -> None:
    for path in (
        ROOT / "odylith" / "registry" / "source" / "component_registry.v1.json",
        ROOT / "src" / "odylith" / "bundle" / "assets" / "odylith" / "registry" / "source" / "component_registry.v1.json",
    ):
        text = path.read_text(encoding="utf-8")
        assert "src/odylith/bundle/assets/odylith" not in text


def test_bundle_does_not_ship_public_live_governance_records_into_consumer_truth_roots() -> None:
    bundle = ROOT / "src" / "odylith" / "bundle" / "assets" / "odylith"
    assert not (bundle / "radar" / "source" / "ideas").exists()
    assert not (bundle / "technical-plans" / "in-progress").exists()
    assert not (bundle / "casebook" / "bugs" / "2026-02-15-mirror-registry-barrier-deadlock-in-tests.md").exists()
    assert not (bundle / "compass" / "runtime" / "codex-stream.v1.jsonl").exists()
    assert not (bundle / "compass" / "runtime" / "current.v1.json").exists()
    assert not (bundle / "compass" / "runtime" / "current.v1.js").exists()
    assert not (bundle / "compass" / "runtime" / "history").exists()


def test_intervention_contract_bundle_assets_stay_synced_or_explicitly_excluded() -> None:
    bundle_root = ROOT / "src" / "odylith" / "bundle" / "assets" / "odylith"
    for source_relative, should_ship in INTERVENTION_CONTRACT_BUNDLE_EXPECTATIONS:
        source_path = ROOT / source_relative
        bundle_path = bundle_root / Path(source_relative).relative_to("odylith")
        assert source_path.is_file(), f"source file missing: {source_relative}"
        if should_ship:
            assert bundle_path.is_file(), f"bundle mirror missing: {bundle_path.relative_to(ROOT)}"
            assert bundle_path.read_text(encoding="utf-8") == source_path.read_text(encoding="utf-8")
            continue
        assert not bundle_path.exists(), f"live governance record should stay excluded: {bundle_path.relative_to(ROOT)}"


def test_readme_operator_instructions_link_stays_present() -> None:
    root_text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "[Operator Instructions](docs/OPERATOR_INSTRUCTIONS.md)" in root_text

    for path in (
        ROOT / "odylith" / "README.md",
        ROOT / "src" / "odylith" / "bundle" / "assets" / "odylith" / "README.md",
    ):
        text = path.read_text(encoding="utf-8")
        assert "[Operator Instructions]" in text, f"Operator Instructions link missing in {path.relative_to(ROOT)}"


def test_root_readme_benchmark_graph_order_stays_verbatim() -> None:
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert README_PROOF_BENCHMARK_GRAPH_BLOCK in text
    assert README_DIAGNOSTIC_BENCHMARK_GRAPH_BLOCK in text


def test_benchmark_integrity_contract_stays_explicit() -> None:
    paths = (
        ROOT / "odylith" / "maintainer" / "AGENTS.md",
        ROOT / "odylith" / "maintainer" / "agents-guidelines" / "RELEASE_BENCHMARKS.md",
        ROOT / "odylith" / "registry" / "source" / "components" / "benchmark" / "CURRENT_SPEC.md",
    )
    for path in paths:
        text = path.read_text(encoding="utf-8")
        assert BENCHMARK_ANTI_GAMING_LINE in text, f"benchmark anti-gaming contract drifted in {path.relative_to(ROOT)}"


def test_benchmark_honest_baseline_contract_stays_explicit() -> None:
    paths = (
        ROOT / "README.md",
        ROOT / "docs" / "benchmarks" / "README.md",
        ROOT / "docs" / "benchmarks" / "REVIEWER_GUIDE.md",
        ROOT / "odylith" / "maintainer" / "AGENTS.md",
        ROOT / "odylith" / "maintainer" / "agents-guidelines" / "RELEASE_BENCHMARKS.md",
        ROOT / "odylith" / "maintainer" / "skills" / "release-benchmark-publishing" / "SKILL.md",
        ROOT / "odylith" / "registry" / "source" / "components" / "benchmark" / "CURRENT_SPEC.md",
    )
    for path in paths:
        text = path.read_text(encoding="utf-8")
        normalized = " ".join(text.split())
        assert any(" ".join(line.split()) in normalized for line in BENCHMARK_HONEST_BASELINE_LINES), (
            f"honest benchmark baseline contract drifted in {path.relative_to(ROOT)}"
        )


def test_odylith_assist_closeout_contract_stays_explicit_across_shared_and_bundled_guidance() -> None:
    paths = (
        ROOT / "AGENTS.md",
        ROOT / "odylith" / "AGENTS.md",
        ROOT / "odylith" / "README.md",
        ROOT / "odylith" / "agents-guidelines" / "GROUNDING_AND_NARROWING.md",
        ROOT / "odylith" / "agents-guidelines" / "ODYLITH_CONTEXT_ENGINE.md",
        ROOT / "odylith" / "agents-guidelines" / "SUBAGENT_ROUTING_AND_ORCHESTRATION.md",
        ROOT / "odylith" / "agents-guidelines" / "VALIDATION_AND_TESTING.md",
        ROOT / "odylith" / "skills" / "odylith-delivery-governance-surface-ops" / "SKILL.md",
        ROOT / "odylith" / "skills" / "odylith-context-engine-operations" / "SKILL.md",
        ROOT / "odylith" / "skills" / "odylith-session-context" / "SKILL.md",
        ROOT / "odylith" / "skills" / "odylith-subagent-orchestrator" / "SKILL.md",
        ROOT / "odylith" / "skills" / "odylith-subagent-router" / "SKILL.md",
        ROOT / "src" / "odylith" / "install" / "agents.py",
        ROOT / "src" / "odylith" / "install" / "manager.py",
        ROOT / "src" / "odylith" / "bundle" / "assets" / "odylith" / "AGENTS.md",
        ROOT / "src" / "odylith" / "bundle" / "assets" / "odylith" / "README.md",
        ROOT / "src" / "odylith" / "bundle" / "assets" / "odylith" / "agents-guidelines" / "GROUNDING_AND_NARROWING.md",
        ROOT / "src" / "odylith" / "bundle" / "assets" / "odylith" / "agents-guidelines" / "ODYLITH_CONTEXT_ENGINE.md",
        ROOT / "src" / "odylith" / "bundle" / "assets" / "odylith" / "agents-guidelines" / "SUBAGENT_ROUTING_AND_ORCHESTRATION.md",
        ROOT / "src" / "odylith" / "bundle" / "assets" / "odylith" / "agents-guidelines" / "VALIDATION_AND_TESTING.md",
        ROOT / "src" / "odylith" / "bundle" / "assets" / "odylith" / "skills" / "odylith-delivery-governance-surface-ops" / "SKILL.md",
        ROOT / "src" / "odylith" / "bundle" / "assets" / "odylith" / "skills" / "odylith-context-engine-operations" / "SKILL.md",
        ROOT / "src" / "odylith" / "bundle" / "assets" / "odylith" / "skills" / "odylith-session-context" / "SKILL.md",
        ROOT / "src" / "odylith" / "bundle" / "assets" / "odylith" / "skills" / "odylith-subagent-orchestrator" / "SKILL.md",
        ROOT / "src" / "odylith" / "bundle" / "assets" / "odylith" / "skills" / "odylith-subagent-router" / "SKILL.md",
    )
    for path in paths:
        normalized = " ".join(path.read_text(encoding="utf-8").split())
        assert ODYLITH_ASSIST_LABEL in normalized, f"closeout Odylith assist label drifted in {path.relative_to(ROOT)}"
        assert ODYLITH_ASSIST_MARKDOWN_LABEL in normalized, f"closeout assist markdown label drifted in {path.relative_to(ROOT)}"
        assert ODYLITH_ASSIST_USER_WIN in normalized, f"closeout assist user-win framing drifted in {path.relative_to(ROOT)}"
        assert ODYLITH_ASSIST_UPDATED_IDS in normalized, f"closeout assist updated-id framing drifted in {path.relative_to(ROOT)}"
        assert ODYLITH_ASSIST_AFFECTED_IDS in normalized, f"closeout assist affected-id framing drifted in {path.relative_to(ROOT)}"
        assert ODYLITH_ASSIST_UNGUIDED_PATH in normalized, f"closeout assist delta framing drifted in {path.relative_to(ROOT)}"
        assert ODYLITH_ASSIST_TONE in normalized, f"closeout assist tone drifted in {path.relative_to(ROOT)}"
        assert ODYLITH_ASSIST_MIXED_EVIDENCE in normalized, f"closeout assist evidence rule drifted in {path.relative_to(ROOT)}"
        assert ODYLITH_AMBIENT_SIGNAL_LABELS in normalized, f"ambient Odylith signal labels drifted in {path.relative_to(ROOT)}"
        assert ODYLITH_SILENCE_RULE in normalized, f"silence rule drifted in {path.relative_to(ROOT)}"


def test_odylith_assist_closeout_contract_stays_explicit_in_maintainer_and_benchmark_surfaces() -> None:
    full_contract_paths = (
        ROOT / "odylith" / "maintainer" / "AGENTS.md",
    )
    reference_paths = (
        ROOT / "odylith" / "maintainer" / "agents-guidelines" / "RELEASE_BENCHMARKS.md",
        ROOT / "odylith" / "maintainer" / "skills" / "release-benchmark-publishing" / "SKILL.md",
        ROOT / "docs" / "benchmarks" / "README.md",
        ROOT / "docs" / "benchmarks" / "METRICS_AND_PRIORITIES.md",
        ROOT / "docs" / "benchmarks" / "REVIEWER_GUIDE.md",
        ROOT / "odylith" / "registry" / "source" / "components" / "benchmark" / "CURRENT_SPEC.md",
    )
    governance_paths = (
        ROOT / "odylith" / "registry" / "source" / "components" / "subagent-orchestrator" / "CURRENT_SPEC.md",
        ROOT / "odylith" / "registry" / "source" / "components" / "subagent-router" / "CURRENT_SPEC.md",
        ROOT / "odylith" / "technical-plans" / "done" / "2026-03" / "2026-03-30-odylith-first-turn-bootstrap-and-short-form-grounding-commands.md",
    )
    for path in full_contract_paths:
        normalized = " ".join(path.read_text(encoding="utf-8").split())
        assert ODYLITH_ASSIST_LABEL in normalized, f"maintainer/benchmark closeout assist label drifted in {path.relative_to(ROOT)}"
        assert ODYLITH_ASSIST_MARKDOWN_LABEL in normalized, f"maintainer/benchmark assist markdown label drifted in {path.relative_to(ROOT)}"
        assert ODYLITH_ASSIST_USER_WIN in normalized, f"maintainer/benchmark assist user-win framing drifted in {path.relative_to(ROOT)}"
        assert ODYLITH_ASSIST_UPDATED_IDS in normalized, f"maintainer/benchmark updated-id framing drifted in {path.relative_to(ROOT)}"
        assert ODYLITH_ASSIST_AFFECTED_IDS in normalized, f"maintainer/benchmark affected-id framing drifted in {path.relative_to(ROOT)}"
        assert ODYLITH_ASSIST_UNGUIDED_PATH in normalized, f"maintainer/benchmark assist delta framing drifted in {path.relative_to(ROOT)}"
        assert ODYLITH_ASSIST_TONE in normalized, f"maintainer/benchmark closeout assist tone drifted in {path.relative_to(ROOT)}"
        assert ODYLITH_ASSIST_MIXED_EVIDENCE in normalized or "counts, measured deltas, or validation outcomes" in normalized, (
            f"maintainer/benchmark closeout assist evidence rule drifted in {path.relative_to(ROOT)}"
        )
    for path in reference_paths:
        normalized = " ".join(path.read_text(encoding="utf-8").split())
        assert ODYLITH_ASSIST_LABEL in normalized, f"benchmark closeout assist label drifted in {path.relative_to(ROOT)}"
        assert ODYLITH_CHATTER_SPEC_TOKEN in normalized, f"benchmark closeout contract should defer to Odylith Chatter in {path.relative_to(ROOT)}"
        assert "measured proof" in normalized or "measured report" in normalized or ODYLITH_ASSIST_MIXED_EVIDENCE in normalized, (
            f"benchmark closeout proof rule drifted in {path.relative_to(ROOT)}"
        )
    for path in governance_paths:
        normalized = " ".join(path.read_text(encoding="utf-8").split())
        assert ODYLITH_ASSIST_LABEL in normalized, f"governance closeout assist label drifted in {path.relative_to(ROOT)}"
        assert ODYLITH_ASSIST_USER_WIN in normalized, f"governance assist user-win framing drifted in {path.relative_to(ROOT)}"
        assert ODYLITH_ASSIST_UNGUIDED_PATH in normalized, f"governance assist delta framing drifted in {path.relative_to(ROOT)}"
    benchmark_spec = " ".join((ROOT / "odylith" / "registry" / "source" / "components" / "benchmark" / "CURRENT_SPEC.md").read_text(encoding="utf-8").split())
    assert ODYLITH_ASSIST_METADATA_ONLY in benchmark_spec


def test_generated_registry_detail_surface_keeps_soulful_closeout_contract() -> None:
    path = ROOT / "odylith" / "registry" / "registry-detail-shard-001.v1.js"
    text = path.read_text(encoding="utf-8")

    assert ODYLITH_ASSIST_LABEL.replace("`", "") in text
    assert ODYLITH_ASSIST_MARKDOWN_LABEL.replace("`", "") in text
    assert ODYLITH_ASSIST_USER_WIN in text
    assert ODYLITH_ASSIST_UPDATED_IDS in text
    assert ODYLITH_ASSIST_AFFECTED_IDS in text
    assert ODYLITH_ASSIST_UNGUIDED_PATH in text
    assert ODYLITH_ASSIST_TONE in text
    assert ODYLITH_ASSIST_MIXED_EVIDENCE in text
    assert "Keep it friendly," not in text
    assert "final-only, friendly," not in text


def test_odylith_chatter_component_is_tracked_in_registry_source_and_generated_surfaces() -> None:
    manifest = json.loads((ROOT / "odylith" / "registry" / "source" / "component_registry.v1.json").read_text(encoding="utf-8"))
    chatter = next(row for row in manifest["components"] if row["component_id"] == "odylith-chatter")
    odylith = next(row for row in manifest["components"] if row["component_id"] == "odylith")

    assert chatter["product_layer"] == "agent_execution"
    assert chatter["workstreams"] == ["B-031"]
    assert chatter["spec_ref"] == "odylith/registry/source/components/odylith-chatter/CURRENT_SPEC.md"
    assert "odylith-chatter" in odylith["subcomponents"]

    spec_text = (ROOT / "odylith" / "registry" / "source" / "components" / "odylith-chatter" / "CURRENT_SPEC.md").read_text(
        encoding="utf-8"
    )
    normalized_spec = " ".join(spec_text.split())
    assert ODYLITH_ASSIST_LABEL in normalized_spec
    assert ODYLITH_ASSIST_MARKDOWN_LABEL in normalized_spec
    assert ODYLITH_ASSIST_USER_WIN in normalized_spec
    assert ODYLITH_ASSIST_UPDATED_IDS in normalized_spec
    assert ODYLITH_ASSIST_AFFECTED_IDS in normalized_spec
    assert ODYLITH_ASSIST_UNGUIDED_PATH in normalized_spec
    assert ODYLITH_ASSIST_TONE in normalized_spec
    assert ODYLITH_ASSIST_MIXED_EVIDENCE in normalized_spec
    assert ODYLITH_AMBIENT_SIGNAL_LABELS in normalized_spec
    assert ODYLITH_SILENCE_RULE in normalized_spec
    assert ODYLITH_ASSIST_METADATA_ONLY in normalized_spec
    assert "[B-031](odylith/radar/radar.html?view=plan&workstream=B-031)" in spec_text

    payload_js = (ROOT / "odylith" / "registry" / "registry-payload.v1.js").read_text(encoding="utf-8")
    payload = json.loads(payload_js.split(" = ", 1)[1].rsplit(";", 1)[0])
    component_ids = {row["component_id"] for row in payload["components"]}
    assert "odylith-chatter" in component_ids
    assert payload["detail_manifest"]["odylith-chatter"].startswith("registry-detail-shard-")

    detail_text = (ROOT / "odylith" / "registry" / payload["detail_manifest"]["odylith-chatter"]).read_text(encoding="utf-8")
    assert '"component_id": "odylith-chatter"' in detail_text or '"component_id":"odylith-chatter"' in detail_text
    assert ODYLITH_ASSIST_LABEL.replace("`", "") in detail_text
    assert ODYLITH_ASSIST_TONE in detail_text


def test_memory_substrate_components_are_tracked_in_registry_source_and_generated_surfaces() -> None:
    manifest = json.loads((ROOT / "odylith" / "registry" / "source" / "component_registry.v1.json").read_text(encoding="utf-8"))
    components = {row["component_id"]: row for row in manifest["components"]}
    expected_specs = {
        "odylith-projection-bundle": "odylith/registry/source/components/odylith-projection-bundle/CURRENT_SPEC.md",
        "odylith-projection-snapshot": "odylith/registry/source/components/odylith-projection-snapshot/CURRENT_SPEC.md",
        "odylith-memory-backend": "odylith/registry/source/components/odylith-memory-backend/CURRENT_SPEC.md",
        "odylith-remote-retrieval": "odylith/registry/source/components/odylith-remote-retrieval/CURRENT_SPEC.md",
        "odylith-memory-contracts": "odylith/registry/source/components/odylith-memory-contracts/CURRENT_SPEC.md",
    }

    for component_id, spec_ref in expected_specs.items():
        assert component_id in components, f"missing memory component {component_id} from registry manifest"
        assert components[component_id]["spec_ref"] == spec_ref

    context_engine = components["odylith-context-engine"]
    odylith = components["odylith"]
    atlas = components["atlas"]
    memory_backend = components["odylith-memory-backend"]

    for component_id in expected_specs:
        assert component_id in context_engine["subcomponents"], f"{component_id} missing from context-engine subcomponents"
        assert component_id in odylith["subcomponents"], f"{component_id} missing from odylith umbrella subcomponents"
        assert "D-025" in components[component_id]["diagrams"], f"{component_id} missing D-025 atlas coverage"

    assert "src/odylith/runtime/memory" not in memory_backend["path_prefixes"]
    assert memory_backend["path_prefixes"] == [
        "src/odylith/runtime/memory/odylith_memory_backend.py",
        "odylith/registry/source/components/odylith-memory-backend/CURRENT_SPEC.md",
    ]
    assert "B-059" in atlas["workstreams"]
    assert "D-025" in atlas["diagrams"]
    assert "D-025" in odylith["diagrams"]
    assert "D-025" in context_engine["diagrams"]

    required_headings = (
        "## Purpose",
        "## Scope And Non-Goals",
        "## Developer Mental Model",
        "## Validation Playbook",
        "## Feature History",
    )
    for spec_ref in expected_specs.values():
        spec_path = ROOT / spec_ref
        text = spec_path.read_text(encoding="utf-8")
        for heading in required_headings:
            assert heading in text, f"{heading} missing from {spec_ref}"
        assert "[B-058](odylith/radar/radar.html?view=plan&workstream=B-058)" in text

    payload_js = (ROOT / "odylith" / "registry" / "registry-payload.v1.js").read_text(encoding="utf-8")
    payload = json.loads(payload_js.split(" = ", 1)[1].rsplit(";", 1)[0])
    payload_component_ids = {row["component_id"] for row in payload["components"]}
    for component_id in expected_specs:
        assert component_id in payload_component_ids, f"{component_id} missing from rendered registry payload"
        shard_name = payload["detail_manifest"][component_id]
        assert shard_name.startswith("registry-detail-shard-")
        detail_text = (ROOT / "odylith" / "registry" / shard_name).read_text(encoding="utf-8")
        assert f'"component_id": "{component_id}"' in detail_text or f'"component_id":"{component_id}"' in detail_text


def test_runtime_refresh_diagrams_cover_conversation_and_tribunal_components() -> None:
    manifest = json.loads((ROOT / "odylith" / "registry" / "source" / "component_registry.v1.json").read_text(encoding="utf-8"))
    components = {row["component_id"]: row for row in manifest["components"]}

    for component_id in ("odylith-chatter", "subagent-router", "subagent-orchestrator", "tribunal"):
        diagrams = set(components[component_id]["diagrams"])
        assert "D-002" in diagrams, f"{component_id} missing the refreshed context/runtime diagram"
        assert "D-018" in diagrams, f"{component_id} missing the refreshed layered topology diagram"
        assert "D-020" in diagrams, f"{component_id} missing the refreshed runtime boundary diagram"


def test_b022_benchmark_workstream_surfaces_as_active_with_only_current_children_in_delivery() -> None:
    radar_index = (ROOT / "odylith" / "radar" / "source" / "INDEX.md").read_text(encoding="utf-8")
    b022 = (
        ROOT
        / "odylith"
        / "radar"
        / "source"
        / "ideas"
        / "2026-03"
        / "2026-03-29-odylith-benchmark-anti-gaming-adversarial-corpus-integrity-and-independent-proof.md"
    ).read_text(encoding="utf-8")

    assert "| - | B-022 | Honest Benchmark Improvement, Anti-Gaming Integrity, and Independent Proof |" in radar_index
    assert "| 1 | B-022 |" not in radar_index
    assert "workstream_children: B-038, B-039" in b022


def test_radar_index_links_stay_repo_relative_and_portable() -> None:
    radar_index = (ROOT / "odylith" / "radar" / "source" / "INDEX.md").read_text(encoding="utf-8")

    assert "/Users/freedom/code/odylith/" not in radar_index
    assert "](/Users/" not in radar_index
    assert "](odylith/radar/source/ideas/" in radar_index


def test_consumer_guidance_contract_drops_legacy_chatter_lines() -> None:
    paths = (
        ROOT / "AGENTS.md",
        ROOT / "odylith" / "AGENTS.md",
        ROOT / "odylith" / "README.md",
        ROOT / "odylith" / "agents-guidelines" / "GROUNDING_AND_NARROWING.md",
        ROOT / "odylith" / "agents-guidelines" / "ODYLITH_CONTEXT_ENGINE.md",
        ROOT / "odylith" / "agents-guidelines" / "SUBAGENT_ROUTING_AND_ORCHESTRATION.md",
        ROOT / "odylith" / "agents-guidelines" / "VALIDATION_AND_TESTING.md",
        ROOT / "odylith" / "skills" / "odylith-delivery-governance-surface-ops" / "SKILL.md",
        ROOT / "odylith" / "skills" / "odylith-context-engine-operations" / "SKILL.md",
        ROOT / "odylith" / "skills" / "odylith-session-context" / "SKILL.md",
        ROOT / "odylith" / "skills" / "odylith-subagent-orchestrator" / "SKILL.md",
        ROOT / "odylith" / "skills" / "odylith-subagent-router" / "SKILL.md",
        ROOT / "src" / "odylith" / "cli.py",
        ROOT / "src" / "odylith" / "install" / "agents.py",
        ROOT / "src" / "odylith" / "install" / "manager.py",
        ROOT / "src" / "odylith" / "bundle" / "assets" / "odylith" / "AGENTS.md",
        ROOT / "src" / "odylith" / "bundle" / "assets" / "odylith" / "README.md",
        ROOT / "src" / "odylith" / "bundle" / "assets" / "odylith" / "agents-guidelines" / "GROUNDING_AND_NARROWING.md",
        ROOT / "src" / "odylith" / "bundle" / "assets" / "odylith" / "agents-guidelines" / "ODYLITH_CONTEXT_ENGINE.md",
        ROOT / "src" / "odylith" / "bundle" / "assets" / "odylith" / "agents-guidelines" / "SUBAGENT_ROUTING_AND_ORCHESTRATION.md",
        ROOT / "src" / "odylith" / "bundle" / "assets" / "odylith" / "agents-guidelines" / "VALIDATION_AND_TESTING.md",
        ROOT / "src" / "odylith" / "bundle" / "assets" / "odylith" / "skills" / "odylith-delivery-governance-surface-ops" / "SKILL.md",
        ROOT / "src" / "odylith" / "bundle" / "assets" / "odylith" / "skills" / "odylith-context-engine-operations" / "SKILL.md",
        ROOT / "src" / "odylith" / "bundle" / "assets" / "odylith" / "skills" / "odylith-session-context" / "SKILL.md",
        ROOT / "src" / "odylith" / "bundle" / "assets" / "odylith" / "skills" / "odylith-subagent-orchestrator" / "SKILL.md",
        ROOT / "src" / "odylith" / "bundle" / "assets" / "odylith" / "skills" / "odylith-subagent-router" / "SKILL.md",
    )
    for path in paths:
        text = path.read_text(encoding="utf-8")
        for fragment in LEGACY_CONSUMER_CHATTER_FRAGMENTS:
            assert fragment not in text, f"legacy consumer chatter remains in {path.relative_to(ROOT)}: {fragment!r}"


def test_runtime_orchestration_templates_stay_debranded() -> None:
    paths = (
        ROOT / "src" / "odylith" / "runtime" / "orchestration" / "subagent_orchestrator.py",
        ROOT / "src" / "odylith" / "runtime" / "orchestration" / "subagent_orchestrator_runtime_signals.py",
        ROOT / "src" / "odylith" / "runtime" / "orchestration" / "subagent_router.py",
        ROOT / "src" / "odylith" / "runtime" / "orchestration" / "subagent_router_assessment_runtime.py",
        ROOT / "src" / "odylith" / "runtime" / "orchestration" / "subagent_router_runtime_policy.py",
    )
    for path in paths:
        text = path.read_text(encoding="utf-8")
        for fragment in RUNTIME_CHATTER_FRAGMENTS:
            assert fragment not in text, f"runtime chatter remains in {path.relative_to(ROOT)}: {fragment!r}"


def test_runtime_user_facing_reason_templates_stay_task_first() -> None:
    paths = (
        ROOT / "src" / "odylith" / "runtime" / "orchestration" / "subagent_orchestrator_runtime_signals.py",
        ROOT / "src" / "odylith" / "runtime" / "orchestration" / "subagent_router_runtime_policy.py",
    )
    fragments = (
        "current runtime handoff",
        "retained context packet",
        "hold-local or serial execution",
        "packetizer alignment is drifting",
        "odylith ceiling kept",
        "odylith execution profile aligned",
        "odylith execution priors influenced",
        "odylith_execution=",
        "odylith_mode=",
    )
    for path in paths:
        text = path.read_text(encoding="utf-8")
        for fragment in fragments:
            assert fragment not in text, f"user-facing runtime template drifted in {path.relative_to(ROOT)}: {fragment!r}"
