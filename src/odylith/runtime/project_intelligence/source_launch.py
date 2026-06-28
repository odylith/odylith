"""Source-launch prompt generation for accepted greenfield Project dashboards."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any

from odylith.runtime.common.prose_grammar import base_action_clause
from odylith.runtime.common.prose_grammar import looks_like_action_clause
from odylith.runtime.domain_intelligence.greenfield_domain_term_index import ordered_terms
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import first_path_action_phrase
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import first_path_model
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import first_path_outcome_phrase
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

_SEMANTIC_FRAGMENT_STOPWORDS = frozenset(
    {
        "accepted",
        "across",
        "after",
        "and",
        "app",
        "application",
        "before",
        "can",
        "direction",
        "evidence",
        "first",
        "for",
        "from",
        "into",
        "its",
        "multiple",
        "path",
        "product",
        "project",
        "receive",
        "receives",
        "release",
        "result",
        "source",
        "system",
        "the",
        "this",
        "to",
        "user",
        "users",
        "workspace",
    }
)
_PROMPT_DANGLING_TAILS = frozenset(
    {
        "about",
        "across",
        "against",
        "after",
        "around",
        "before",
        "between",
        "during",
        "for",
        "from",
        "into",
        "through",
        "until",
        "while",
        "with",
        "without",
    }
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
    source_launch_context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return the accepted-greenfield launch sequence from product facts."""

    context = source_launch_context if isinstance(source_launch_context, Mapping) else {}
    product = _clean_title(title)
    path = _first_path_phrase(first_path)
    actor = _primary_actor(actors)
    participant = _secondary_actor(actors)
    capabilities = _capability_phrase(components=components, first_path=first_path)
    risk = _risk_phrase(risks)
    proof = _proof_phrase(validation=validation, first_path=first_path)
    excluded = _exclusion_phrase(non_goals)
    boundary = _source_boundary_hint(product)
    language = _language_signal(repo_root)
    target = _target_workstream(context)
    readiness = _context_list(context, "coding_readiness_gates", limit=4)
    validation_context = _context_list(context, "validation_gates", limit=4)
    commands = _command_context_list(context, limit=4)
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
                target=target,
                readiness=readiness,
                commands=commands,
            ),
            _implementation_prompt(
                product=product,
                path=path,
                capabilities=capabilities,
                risk=risk,
                excluded=excluded,
                boundary=boundary,
                target=target,
                readiness=readiness,
            ),
            _proof_prompt(
                product=product,
                path=path,
                risk=risk,
                proof=proof,
                target=target,
                validation_context=validation_context,
                commands=commands,
            ),
            _refresh_prompt(product=product, path=path, capabilities=capabilities, target=target, commands=commands),
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
            f"Odylith, prepare {product} for implementation in {language.name}. Current signal: {language.reason}. "
            f"Confirm that {language.name} is still the right runtime for this accepted product. Use the accepted first path as the only initial scope: {path}. "
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
    target: str,
    readiness: Sequence[str],
    commands: Sequence[str],
) -> dict[str, str]:
    language_name = language.name if language else "the confirmed language"
    product_responsibilities = _prompt_phrase(capabilities, fallback="the accepted product responsibilities")
    proof_clause = _prompt_clause(proof, fallback="the accepted proof boundary")
    excluded_clause = _prompt_clause(excluded, fallback="the excluded first-release scope")
    target_clause = f" Governed target: {target}." if target else ""
    readiness_clause = f" Coding-readiness gates to preserve: {_join(readiness)}." if readiness else ""
    command_clause = f" Validation commands to plan around: {_join(commands)}." if commands else ""
    prompt = (
        f"Odylith, expand the accepted {product} direction into an implementation plan using {language_name}. Keep this first "
        f"path as the only implementation scope: {path}. Before editing source, propose the first source boundary "
        f"around {boundary}, the files or modules to create, the product objects {actor} changes or reads, the handoff for "
        f"{participant}, product responsibilities to cover: {product_responsibilities}, validation points, test commands, "
        f"proof gates for {proof_clause}, and excluded scope: {excluded_clause}.{target_clause}{readiness_clause}{command_clause}"
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
    target: str,
    readiness: Sequence[str],
) -> dict[str, str]:
    product_responsibilities = _prompt_phrase(capabilities, fallback="the accepted product responsibilities")
    risk_clause = _prompt_clause(risk, fallback="the named product risk")
    excluded_clause = _prompt_clause(excluded, fallback="the excluded first-release scope")
    target_clause = f" Use governed workstream {target} as the source of truth for the coding slice." if target else ""
    readiness_clause = f" Do not edit until these readiness gates are accepted: {_join(readiness)}." if readiness else ""
    prompt = (
        f"Odylith, implement the smallest runnable {product} product slice from the accepted plan. Restate the target files "
        f"before editing. Build only this path: {path}. Create the minimal domain model, source boundary around {boundary}, "
        f"product behavior for these responsibilities: {product_responsibilities}, input validation, structured result, and user-visible explanation. Protect "
        f"against this product risk while coding: {risk_clause}. Keep outside the slice: {excluded_clause}. If one excluded capability is "
        f"actually required, explain why and stop before editing.{target_clause}{readiness_clause}"
    )
    return {
        "label": "Build smallest runnable slice",
        "when": "Use this only after the first implementation plan is accepted.",
        "prompt": prompt,
        "result": "The first working product behavior, limited to the accepted path and minimal source boundary.",
        "stop": "Stop after the smallest runnable slice works. Do not add unrelated screens, integrations, storage, queues, or infrastructure.",
    }


def _proof_prompt(
    *,
    product: str,
    path: str,
    risk: str,
    proof: str,
    target: str,
    validation_context: Sequence[str],
    commands: Sequence[str],
) -> dict[str, str]:
    target_clause = f" Bind the proof to governed workstream {target}." if target else ""
    validation_clause = f" Include these accepted validation gates: {_join(validation_context)}." if validation_context else ""
    command_clause = f" Run or update these verification commands: {_join(commands)}." if commands else ""
    risk_clause = _prompt_clause(risk, fallback="the named product risk")
    prompt = (
        f"Odylith, add behavior proof for the first {product} source slice. Test the accepted path: {path}. Add tests for "
        "valid input, missing or incomplete required input, an unfavorable or blocked outcome, and reproducibility from "
        f"the same submitted inputs, configuration, and state. Preserve the explanation in a testable structure. Prove this "
        f"risk is controlled by the tests: {risk_clause}. Run the validation commands from the plan.{target_clause}{validation_clause}{command_clause}"
    )
    return {
        "label": "Add tests and proof",
        "when": "Use this after the first runnable slice exists.",
        "prompt": prompt,
        "result": _proof_result_sentence(proof),
        "stop": "Stop if validation fails. Do not refresh governed records until the failed behavior is fixed or recorded.",
    }


def _refresh_prompt(*, product: str, path: str, capabilities: str, target: str, commands: Sequence[str]) -> dict[str, str]:
    target_clause = f" Start with governed workstream {target} and its implementation evidence." if target else ""
    command_clause = f" Cite verification command results from: {_join(commands)}." if commands else ""
    prompt = (
        f"Odylith, refresh governed records from the implemented accepted {product} source slice. Align the Project dashboard, Radar "
        f"workstreams, Registry components, Atlas diagrams when architecture exists, Compass evidence, and Casebook only if "
        f"bugs were created. Ensure the product story, first path, participants, risks, owned capabilities, and proof records "
        f"match the implemented behavior from the accepted path: {path}. Keep capability records centered on these responsibilities: {capabilities}.{target_clause}{command_clause}"
    )
    return {
        "label": "Refresh governed records",
        "when": "Use this only after tests and validation pass.",
        "prompt": prompt,
        "result": "Updated governed surfaces that reflect implemented source behavior instead of accepted-intent assumptions.",
        "stop": "Stop after refresh and validation results are visible. Do not claim broader release readiness without source proof.",
    }


def _target_workstream(context: Mapping[str, Any]) -> str:
    workstream_id = sentence(context.get("start_workstream_id")).upper()
    title = sentence(context.get("start_workstream_title"))
    release = sentence(context.get("release_selector"))
    if workstream_id and title and release:
        return f"{workstream_id} ({title}) in release {release}"
    if workstream_id and title:
        return f"{workstream_id} ({title})"
    return workstream_id or title


def _context_list(context: Mapping[str, Any], key: str, *, limit: int) -> list[str]:
    raw = context.get(key)
    values = raw if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes)) else (raw,)
    rows: list[str] = []
    for value in values:
        text = _prompt_phrase(value, fallback="", limit=180)
        if text and text not in rows:
            rows.append(text)
        if len(rows) >= limit:
            break
    return rows


def _command_context_list(context: Mapping[str, Any], *, limit: int) -> list[str]:
    raw = context.get("verification_commands")
    values = raw if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes)) else (raw,)
    rows: list[str] = []
    for value in values:
        label = _command_purpose(value)
        if label and label not in rows:
            rows.append(label)
        if len(rows) >= limit:
            break
    return rows


def _command_purpose(value: object) -> str:
    text = str(value or "").casefold()
    if not text.strip():
        return ""
    if "plan-workstream-binding" in text:
        return "plan-workstream-binding validation"
    if "plan-traceability" in text:
        return "plan-traceability validation"
    if "context" in text:
        return "context lookup for the governed workstream"
    if "sync" in text:
        return "selective governed-record refresh"
    if "validate" in text:
        return "listed validation command"
    return "listed verification command"


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
        text = sentence(actors[index][1])
    except IndexError:
        return ""
    text = re.split(r"\s+[—-]\s+|:", text, maxsplit=1)[0].strip(" .")
    return text


def _capability_phrase(*, components: Sequence[Mapping[str, Any]], first_path: str) -> str:
    action = first_path_action_phrase(first_path, fallback="", limit=110, max_fragments=1)
    outcome = first_path_outcome_phrase(first_path, fallback="", limit=110)
    action = _drop_embedded_outcome(action)
    outcome = _sentence_case_fragment(_prompt_fragment(outcome))
    if _outcome_starts_with_actor_action(outcome) or _outcome_restates_action(action, outcome):
        outcome = ""
    if action and outcome:
        return f"capture the information needed to {action} and return {outcome}"
    if outcome:
        return f"return {outcome} with enough context for the next participant"
    if action:
        return f"capture the information needed to {action} and return a clear, reviewable result"
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
            first_sentence = re.split(r"(?<=[.!?])\s+", text, maxsplit=1)[0].strip()
            if first_sentence:
                text = first_sentence
            return _prompt_phrase(text, fallback="the real-world failure modes named by the accepted product direction", limit=260)
    return "the real-world failure modes named by the accepted product direction"


def _proof_phrase(*, validation: Sequence[str], first_path: str) -> str:
    semantic_clause = _first_path_proof_clause(first_path)
    if semantic_clause:
        return semantic_clause
    for row in validation:
        text = sentence(row)
        if text:
            clean = _prompt_phrase(text, fallback="", limit=260)
            if _looks_scaffolded_proof(clean):
                outcome = first_path_outcome_phrase(first_path, fallback="", limit=110)
                if outcome:
                    return f"the accepted path returns {outcome} with repeatable evidence"
                return "the accepted path returns its promised result with repeatable evidence"
            clean = re.sub(r"^(?:the\s+)?accepted\s+first\s+path\s+proves\s+", "", clean, flags=re.IGNORECASE).strip(" .")
            clean = re.sub(r"^(?:success\s+proof|proof)\s+includes\s+", "", clean, flags=re.IGNORECASE).strip(" .")
            return clean
    safe_path = _first_path_phrase(first_path)
    return short(f"the accepted path produces its intended result: {safe_path}", limit=220)


def _proof_result_sentence(proof: str) -> str:
    clean = _prompt_fragment(proof).rstrip(" .!?;:")
    if not clean:
        return "Tests and validation evidence that the accepted path can produce its promised result."
    lowered = clean.casefold()
    if lowered.startswith("the accepted path "):
        return f"Tests and validation evidence that {clean}."
    if lowered.startswith("accepted path "):
        return f"Tests and validation evidence that the {clean}."
    if lowered.startswith(("can ", "must ", "should ", "will ")):
        return f"Tests and validation evidence that the accepted path {clean}."
    return f"Tests and validation evidence that the accepted path can {clean}."


def _first_path_proof_clause(first_path: str) -> str:
    """Render proof obligations from first-path actions without gerundizing nouns."""

    rows: list[str] = []
    seen: set[str] = set()
    for step in first_path_model(first_path).steps:
        action = _base_action_from_step(str(step))
        key = action.casefold()
        if not action or key in seen:
            continue
        rows.append(action)
        seen.add(key)
        if len(rows) >= 5:
            break
    if not rows:
        return ""
    return short(_join(rows), limit=260).rstrip(" .!?;:")


def _base_action_from_step(value: str) -> str:
    text = _clean_fragment(value)
    if not text:
        return ""
    tokens = text.split()
    candidates = [text]
    for index in range(1, min(len(tokens), 9)):
        candidates.append(" ".join(tokens[index:]))
    for candidate in candidates:
        if not looks_like_action_clause(candidate):
            continue
        action = base_action_clause(candidate)
        if action:
            return _drop_embedded_outcome(_prompt_fragment(action))
    return ""


def _exclusion_phrase(non_goals: Sequence[str]) -> str:
    rows = [re.sub(r":\s+(?:and|or)\s+", ": ", _clean_fragment(row), flags=re.IGNORECASE) for row in non_goals if sentence(row)]
    if rows:
        return _join(rows[:4])
    return _join(_PROTECTED_SCOPE[:5])


def _source_boundary_hint(product: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", product.casefold()).strip("_")
    return slug or "the first product module"


def _first_path_phrase(value: str) -> str:
    text = _clean_fragment(value)
    action = first_path_action_phrase(text, fallback="", limit=180, max_fragments=1)
    outcome = first_path_outcome_phrase(text, fallback="", limit=150)
    action = _drop_embedded_outcome(action)
    outcome = _sentence_case_fragment(_prompt_fragment(outcome))
    if _outcome_starts_with_actor_action(outcome) or _outcome_restates_action(action, outcome):
        outcome = ""
    if action and outcome:
        subject_action = _subjectify_path_step(action)
        joiner = "and receive" if subject_action.casefold().startswith("the user can ") else "and receives"
        return short(f"{subject_action} {joiner} {outcome}", limit=320)
    if action:
        return short(_subjectify_path_step(action), limit=260)
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
    if looks_like_action_clause(text):
        action = base_action_clause(text)
        return f"the user can {action}" if action else text
    return text


def _prompt_phrase(value: object, *, fallback: str, limit: int = 180) -> str:
    """Keep host prompts specific without copying whole component contracts into chat."""

    text = _clean_fragment(value)
    if not text:
        return fallback
    text = re.sub(r"\b(?:proof gates?|validation points?)\s+for\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\bThe weak inputs are\s*[. ]*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+(?:and|or|asks?|check|checks)\s*$", "", text, flags=re.IGNORECASE).strip(" .,;:")
    text = re.sub(r"\.\.+", ".", text)
    return _prompt_fragment(short(text, limit=limit, fallback=fallback))


def _prompt_clause(value: object, *, fallback: str, limit: int = 180) -> str:
    return _prompt_phrase(value, fallback=fallback, limit=limit).rstrip(" .!?;:")


def _prompt_fragment(value: object) -> str:
    words = sentence(value).strip(" .!?;:").split()
    while words and words[-1].casefold().strip(".,;:") in _PROMPT_DANGLING_TAILS:
        words.pop()
    return " ".join(words)


def _outcome_restates_action(action: str, outcome: str) -> bool:
    action_terms = _semantic_fragment_terms(action)
    outcome_terms = _semantic_fragment_terms(outcome)
    if not action_terms or not outcome_terms:
        return False
    if outcome_terms <= action_terms:
        return True
    overlap = len(action_terms & outcome_terms)
    if overlap < 3:
        return False
    return overlap / max(1, min(len(action_terms), len(outcome_terms))) >= 0.55


def _semantic_fragment_terms(value: object) -> set[str]:
    return set(ordered_terms(value, minimum=3, stopwords=_SEMANTIC_FRAGMENT_STOPWORDS, stem_ing=True))


def _drop_embedded_outcome(value: str) -> str:
    text = sentence(value).strip(" .")
    text = re.sub(r"\s+and\s+receives?\s+.+$", "", text, flags=re.IGNORECASE).strip(" .")
    text = re.sub(r"^(?:the\s+user\s+can\s+)", "", text, flags=re.IGNORECASE).strip(" .")
    return text


def _looks_scaffolded_proof(value: str) -> bool:
    lowered = sentence(value).casefold()
    return bool(
        "success proof:" in lowered
        or "letting a representative user" in lowered
        or re.search(r"\b(?:asks?|checks?|shows?|displays?)\s*[.]$", lowered)
    )


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
    return _sentence_case_fragment(text)


def _sentence_case_fragment(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    words = text.split()
    first = words[0].strip(".,;:")
    if first.isupper() or (
        first[:1].isupper()
        and any(word.strip(".,;:")[:1].isupper() for word in words[1:5])
    ):
        return text
    return text[:1].lower() + text[1:]


def _outcome_starts_with_actor_action(value: str) -> bool:
    words = [word.casefold().strip(".,;:'") for word in str(value or "").split()]
    if len(words) < 3:
        return False
    if words[0] in {"a", "an", "the"}:
        words = words[1:]
    if len(words) < 2 or words[0] not in {"participant", "person", "user"}:
        return False
    return words[1].endswith(("s", "ed"))


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
