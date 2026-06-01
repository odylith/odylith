"""Source-launch prompt generation for accepted greenfield Project dashboards."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_semantic_quality import first_path_model
from odylith.runtime.project_intelligence.utils import display_text, list_value, sentence, short, strings


@dataclass(frozen=True)
class _LanguageSignal:
    name: str
    reason: str


_LANGUAGE_MARKERS: tuple[tuple[str, tuple[str, ...], tuple[str, ...]], ...] = (
    ("Python", ("pyproject.toml", "requirements.txt", "setup.py", "Pipfile"), (".py",)),
    ("TypeScript", ("package.json", "tsconfig.json", "vite.config.ts"), (".ts", ".tsx")),
    ("JavaScript", ("package.json", "vite.config.js"), (".js", ".jsx", ".mjs")),
    ("Go", ("go.mod", "go.sum"), (".go",)),
    ("Rust", ("Cargo.toml", "Cargo.lock"), (".rs",)),
    ("Java", ("pom.xml", "build.gradle", "settings.gradle"), (".java",)),
)

_IGNORED_SCAN_PARTS = {
    ".git",
    ".mypy_cache",
    ".odylith",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
    "odylith",
}

_PROTECTED_SCOPE = (
    "authentication",
    "billing",
    "full UI",
    "database persistence",
    "external APIs",
    "background queues",
    "admin consoles",
    "deployment infrastructure",
    "observability platforms",
    "multi-tenant policy systems",
)


def build_source_launch_handoff(
    *,
    repo_root: Path,
    title: str,
    first_path: str,
    actors: Sequence[tuple[str, str, str]],
    components: Sequence[Mapping[str, Any]],
    risks: Sequence[Any],
    validation: Sequence[str],
    non_goals: Sequence[str],
) -> dict[str, Any]:
    """Return the accepted-greenfield launch sequence from product facts."""

    product = _clean_title(title)
    path = _first_path_phrase(first_path)
    actor = _primary_actor(actors)
    participant = _secondary_actor(actors)
    capabilities = _capability_phrase(components=components, first_path=path)
    risk = _risk_phrase(risks)
    proof = _proof_phrase(validation=validation, first_path=path)
    excluded = _exclusion_phrase(non_goals)
    boundary = _source_boundary_hint(product)
    language = _language_signal(repo_root)
    return {
        "title": "First source creation sequence",
        "note": (
            f"Use these prompts to turn {product} from accepted product direction into its first runnable source slice. "
            "Each prompt has a stop condition so planning, coding, proof, and record refresh do not blur together."
        ),
        "steps": [
            "Choose or confirm the implementation language and runtime.",
            "Create the first source-editable implementation plan.",
            "Build the smallest runnable product slice.",
            "Add behavior proof and run validation.",
            "Refresh governed records from the implemented source.",
        ],
        "prompts": [
            _language_prompt(product=product, path=path, language=language),
            _plan_prompt(
                product=product,
                path=path,
                actor=actor,
                participant=participant,
                capabilities=capabilities,
                proof=proof,
                excluded=excluded,
                boundary=boundary,
                language=language,
            ),
            _implementation_prompt(
                product=product,
                path=path,
                capabilities=capabilities,
                risk=risk,
                excluded=excluded,
                boundary=boundary,
            ),
            _proof_prompt(product=product, path=path, risk=risk, proof=proof),
            _refresh_prompt(product=product, path=path, capabilities=capabilities),
        ],
        "next_title": "Start source creation",
        "next_note": (
            "Confirm language first, then create the implementation plan; source edits should begin only after the plan "
            "names the first boundary, files, proof gates, validation commands, excluded scope, and stop conditions."
        ),
    }


def _language_prompt(*, product: str, path: str, language: _LanguageSignal | None) -> dict[str, str]:
    if language:
        prompt = (
            f"Odylith, prepare {product} for implementation in {language.name}. Confirm that {language.reason} is still "
            f"the right runtime for this accepted product. Use the accepted first path as the only initial scope: {path}. "
            "Before editing source, show the package layout, runtime assumptions, test approach, tradeoffs, and any reason "
            "to choose a different language."
        )
        stop = "Do not edit source yet. Stop after confirming the language, runtime assumptions, and recommendation."
        result = f"A {language.name} implementation recommendation with package layout, test approach, and tradeoffs."
    else:
        prompt = (
            f"Odylith, prepare {product} for implementation. Inspect this repo for existing language signals and use the "
            f"accepted first path as the only initial scope: {path}. If no language is already clear, propose two suitable "
            "implementation options, one optimized for a Python runtime and one optimized for a TypeScript runtime, with "
            "package layout, runtime assumptions, test approach, and tradeoffs for this product."
        )
        stop = "Do not edit source yet. Stop after recommending the best default and asking me to confirm the language."
        result = "A language recommendation, package-shape options, runtime assumptions, and test strategy."
    return {
        "label": "Choose implementation language",
        "when": "Use this first when the accepted project does not already have a confirmed implementation language.",
        "prompt": prompt,
        "result": result,
        "stop": stop,
    }


def _plan_prompt(
    *,
    product: str,
    path: str,
    actor: str,
    participant: str,
    capabilities: str,
    proof: str,
    excluded: str,
    boundary: str,
    language: _LanguageSignal | None,
) -> dict[str, str]:
    language_name = language.name if language else "the confirmed language"
    prompt = (
        f"Odylith, expand the accepted {product} direction into an implementation plan using {language_name}. Keep this first "
        f"path as the only implementation scope: {path}. Before editing source, propose the first source boundary "
        f"around {boundary}, the files or modules to create, domain objects for {actor}, interactions involving "
        f"{participant}, product responsibilities to cover: {capabilities}; validation points, test commands, proof gates for {proof}, "
        f"and excluded scope: {excluded}."
    )
    return {
        "label": "Create first implementation plan",
        "when": "Use this after the language and runtime are confirmed.",
        "prompt": prompt,
        "result": "A concrete plan with source boundary, files, domain objects, interfaces, validation commands, and proof gates.",
        "stop": "Stop after proposing the plan. Do not edit source until I accept the boundary, files, tests, and excluded scope.",
    }


def _implementation_prompt(
    *,
    product: str,
    path: str,
    capabilities: str,
    risk: str,
    excluded: str,
    boundary: str,
) -> dict[str, str]:
    prompt = (
        f"Odylith, implement the smallest runnable {product} product slice from the accepted plan. Restate the target files "
        f"before editing. Build only this path: {path}. Create the minimal domain model, source boundary around {boundary}, "
        f"product behavior for these responsibilities: {capabilities}; input validation, structured result, and user-visible explanation. Protect "
        f"against this product risk while coding: {risk}. Keep outside the slice: {excluded}. If one excluded capability is "
        "actually required, explain why and stop before editing."
    )
    return {
        "label": "Build smallest runnable slice",
        "when": "Use this only after the first implementation plan is accepted.",
        "prompt": prompt,
        "result": "The first working product behavior, limited to the accepted path and minimal source boundary.",
        "stop": "Stop after the smallest runnable slice works. Do not add unrelated screens, integrations, storage, queues, or infrastructure.",
    }


def _proof_prompt(*, product: str, path: str, risk: str, proof: str) -> dict[str, str]:
    prompt = (
        f"Odylith, add behavior proof for the first {product} source slice. Test the accepted path: {path}. Add tests for "
        "valid input, missing or incomplete required input, an unfavorable or blocked outcome, and reproducibility from "
        f"the same submitted inputs, configuration, and state. Preserve the explanation in a testable structure. Prove this "
        f"risk is controlled by the tests: {risk}. Run the validation commands from the plan."
    )
    return {
        "label": "Add tests and proof",
        "when": "Use this after the first runnable slice exists.",
        "prompt": prompt,
        "result": f"Tests and validation evidence showing {proof}.",
        "stop": "Stop if validation fails. Do not refresh governed records until the failed behavior is fixed or recorded.",
    }


def _refresh_prompt(*, product: str, path: str, capabilities: str) -> dict[str, str]:
    prompt = (
        f"Odylith, refresh governed records from the implemented {product} source slice. Align the Project dashboard, Radar "
        f"workstreams, Registry components, Atlas diagrams when architecture exists, Compass evidence, and Casebook only if "
        f"bugs were created. Ensure the product story, first path, participants, risks, owned capabilities, and proof records "
        f"match the implemented behavior: {path}. Keep capability records centered on these responsibilities: {capabilities}."
    )
    return {
        "label": "Refresh governed records",
        "when": "Use this only after tests and validation pass.",
        "prompt": prompt,
        "result": "Updated governed surfaces that reflect implemented source behavior instead of accepted-intent assumptions.",
        "stop": "Stop after refresh and validation results are visible. Do not claim broader release readiness without source proof.",
    }


def _language_signal(repo_root: Path) -> _LanguageSignal | None:
    markers: dict[str, int] = {}
    suffixes: dict[str, int] = {}
    for path in _repo_paths(repo_root):
        name = path.name
        suffix = path.suffix.casefold()
        for language, marker_names, marker_suffixes in _LANGUAGE_MARKERS:
            if name in marker_names:
                markers[language] = markers.get(language, 0) + 5
            if suffix in marker_suffixes:
                suffixes[language] = suffixes.get(language, 0) + 1
    scores = {language: markers.get(language, 0) + suffixes.get(language, 0) for language, _m, _s in _LANGUAGE_MARKERS}
    best = max(scores.items(), key=lambda row: row[1], default=("", 0))
    if best[1] < 3:
        return None
    reason = "existing repo language signals point to " + best[0]
    return _LanguageSignal(name=best[0], reason=reason)


def _repo_paths(repo_root: Path) -> list[Path]:
    root = Path(repo_root)
    paths: list[Path] = []
    if not root.exists():
        return paths
    for path in root.rglob("*"):
        if len(paths) >= 350:
            break
        relative_parts = set(path.relative_to(root).parts)
        if relative_parts & _IGNORED_SCAN_PARTS:
            continue
        if path.is_file():
            paths.append(path)
    return paths


def _primary_actor(actors: Sequence[tuple[str, str, str]]) -> str:
    return _actor_at(actors, 0) or "the primary participant"


def _secondary_actor(actors: Sequence[tuple[str, str, str]]) -> str:
    return _actor_at(actors, 1) or "the next participant"


def _actor_at(actors: Sequence[tuple[str, str, str]], index: int) -> str:
    try:
        return sentence(actors[index][1])
    except IndexError:
        return ""


def _capability_phrase(*, components: Sequence[Mapping[str, Any]], first_path: str) -> str:
    phrases: list[str] = []
    for component in components:
        text = (
            sentence(component.get("responsibility"))
            or sentence(component.get("boundary"))
            or sentence(component.get("label"))
            or sentence(component.get("component_id"))
        )
        if text:
            phrases.append(_clean_fragment(text))
    if phrases:
        return _join(phrases[:3])
    return _clean_fragment(first_path) or "the accepted product outcome"


def _risk_phrase(risks: Sequence[Any]) -> str:
    for risk in risks:
        if isinstance(risk, Mapping):
            text = sentence(risk.get("statement") or risk.get("description") or risk.get("risk") or risk.get("title"))
        else:
            text = sentence(risk)
        if text:
            return short(_clean_fragment(text), limit=220)
    return "the real-world failure modes named by the accepted product direction"


def _proof_phrase(*, validation: Sequence[str], first_path: str) -> str:
    for row in validation:
        text = sentence(row)
        if text:
            return short(_clean_fragment(text), limit=220)
    return short(f"the accepted path produces its intended result: {first_path}", limit=220)


def _exclusion_phrase(non_goals: Sequence[str]) -> str:
    rows = [_clean_fragment(row) for row in non_goals if sentence(row)]
    if rows:
        return _join(rows[:4])
    return _join(_PROTECTED_SCOPE[:5])


def _source_boundary_hint(product: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", product.casefold()).strip("_")
    return slug or "the first product module"


def _first_path_phrase(value: str) -> str:
    text = _clean_fragment(value)
    model = first_path_model(text)
    if model.steps:
        rows: list[str] = []
        for step in model.steps:
            clean = _clean_fragment(step)
            if not clean:
                continue
            if not rows and re.search(r"\bopens?\s+(?:the\s+)?(?:app|web app|application|site|website)\b", clean, flags=re.I):
                continue
            rows.append(_subjectify_path_step(clean))
            if len(rows) >= 3:
                break
        if rows:
            return short(". ".join(row.rstrip(".") for row in rows), limit=360)
    return short(text, limit=360) if text else "the accepted first product path"


def _subjectify_path_step(value: str) -> str:
    text = _clean_fragment(value)
    if not text:
        return ""
    text = _normalize_embedded_action_verbs(text)
    if re.match(
        r"^(?:add|adds|log|logs|manually\s+log|manually\s+logs|enter|enters|select|selects|submit|submits|save|saves|choose|chooses|click|clicks|accept|accepts|dismiss|dismisses|record|records|capture|captures)\b",
        text,
        flags=re.IGNORECASE,
    ):
        return f"the user {text}"
    return text


def _normalize_embedded_action_verbs(value: str) -> str:
    return re.sub(
        r",\s+and\s+(manually\s+)?(logs?|enters?|selects?|submits?|saves?|chooses?|clicks?|accepts?|dismisses?|records?|captures?|reviews?)\b",
        r" and \1\2",
        value,
        flags=re.IGNORECASE,
    )


def _clean_title(value: str) -> str:
    return display_text(value, "Accepted greenfield project")


def _clean_fragment(value: object) -> str:
    text = display_text(value)
    text = re.sub(r"\b(?:first_slice_proof|validation_strategy)\s*:\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\bvisible[- ]result\s+event\b", "visible result", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+is\s+the\s+visible\s+result\b.*$", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\breadout\s+plus\b", "readout and", text, flags=re.IGNORECASE)
    text = _normalize_leading_capability_verb(text)
    text = text.strip(" .")
    return text[:1].lower() + text[1:] if text else ""


def _normalize_leading_capability_verb(value: str) -> str:
    replacements = {
        "calculates": "calculate",
        "captures": "capture",
        "derives": "derive",
        "displays": "display",
        "flags": "flag",
        "holds": "maintain",
        "manages": "manage",
        "records": "record",
        "renders": "render",
        "returns": "return",
        "routes": "route",
        "shows": "show",
        "stores": "store",
        "tracks": "track",
        "validates": "validate",
    }
    first, sep, rest = sentence(value).partition(" ")
    replacement = replacements.get(first.casefold().strip(".,;:"))
    if replacement:
        return f"{replacement}{sep}{rest}".strip()
    return value


def _join(values: Sequence[str]) -> str:
    rows = [sentence(value).strip(" .") for value in values if sentence(value)]
    if not rows:
        return ""
    if len(rows) == 1:
        return rows[0]
    if len(rows) == 2:
        return f"{rows[0]} and {rows[1]}"
    return ", ".join(rows[:-1]) + f", and {rows[-1]}"


__all__ = ["build_source_launch_handoff"]
