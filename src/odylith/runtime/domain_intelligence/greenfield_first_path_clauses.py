"""First-path clause rendering for generated greenfield artifacts."""

from __future__ import annotations

import re
from typing import Any, Sequence

from odylith.runtime.common.prose_grammar import action_base_verb_pattern
from odylith.runtime.common.prose_grammar import base_action_clause
from odylith.runtime.common.prose_grammar import base_following_action_verbs
from odylith.runtime.domain_intelligence.greenfield_domain_term_index import label_terms
from odylith.runtime.domain_intelligence.greenfield_domain_term_index import ordered_terms
from odylith.runtime.domain_intelligence.greenfield_first_path_types import FirstPathClauses
from odylith.runtime.domain_intelligence.greenfield_first_path_types import FirstPathModel
from odylith.runtime.domain_intelligence.greenfield_text import clean_text


TRIVIAL_START_RE = re.compile(
    r"^(?:a|an|the)?\s*[^,.;]{0,40}?\b(?:open|opens|launch|launches|start|starts)\s+"
    r"(?:the\s+)?(?:(?:web\s+)?app(?:lication)?|product|tool|site|website|screen|page|dashboard|portal|console)\b\s*$",
    re.IGNORECASE,
)
TRIVIAL_NAMED_PRODUCT_START_RE = re.compile(
    r"^(?:a|an|the)?\s*[^,.;]{0,40}?\b(?:open|opens|launch|launches|start|starts)\s+"
    r"[A-Z][A-Za-z0-9_-]{2,40}\b\s*$"
)
TRIVIAL_AUTH_RE = re.compile(
    r"^(?:a|an|the)?\s*[^,.;]{0,60}?\b(?:authenticates?|logs?\s+in|signs?\s+in)\b\s*$",
    re.IGNORECASE,
)

MATERIAL_ACTION_RE = re.compile(
    r"\b(?:"
    r"accept|accepts|add|adds|adjust|adjusts|approve|approves|assign|assigns|attach|attaches|calculate|calculates|capture|captures|"
    r"book|books|check|checks|choose|chooses|compare|compares|complete|completes|confirm|confirms|correct|corrects|decide|decides|"
    r"click|clicks|create|creates|delete|deletes|describe|describes|dismiss|dismisses|edit|edits|enter|enters|export|exports|fetch|fetches|finalize|finalizes|"
    r"display|displays|highlight|highlights|import|imports|inspect|inspects|let|lets|log|logs|mark|marks|notify|notifies|persist|persists|play|plays|"
    r"preserve|preserves|produce|produces|provide|provides|publish|publishes|rank|ranks|read|reads|receive|receives|record|records|render|renders|request|requests|review|reviews|"
    r"return|returns|route|routes|run|runs|save|saves|schedule|schedules|screen|screens|see|sees|select|selects|send|sends|share|shares|"
    r"show|shows|stop|stops|store|stores|submit|submits|sync|syncs|tap|taps|track|tracks|update|updates|"
    r"validate|validates|view|views"
    r")\b",
    re.IGNORECASE,
)

_ACTOR_SIGNATURE_STOPWORDS = frozenset(
    {"a", "an", "the", "one", "this", "that", "each", "another", "can"}
)
_PRESERVED_SHORT_ACTOR_TERMS = frozenset({"ai", "ml", "ui", "ux"})


def first_path_capability_phrase(
    value: Any,
    *,
    fallback: str = "accepted first path",
    limit: int = 180,
    gerund: bool = False,
    max_fragments: int = 4,
) -> str:
    """Return a compact action-chain phrase for Radar and project-story prose."""

    model = _model_for(value)
    text = _first_path_capability_text(model, fallback=fallback, limit=limit, gerund=gerund, max_fragments=max_fragments)
    return text or clean_first_path_text(fallback)


def first_path_clauses(
    value: Any,
    *,
    proof_boundary: Any = "",
    action_fallback: str = "complete the first product action",
    capability_fallback: str = "accepted first path",
    outcome_fallback: str = "the promised user-visible result",
    action_limit: int = 220,
    capability_limit: int = 220,
    outcome_limit: int = 220,
) -> FirstPathClauses:
    """Compile a first path once into the clauses shared by all renderers."""

    model = _model_for(value)
    return FirstPathClauses(
        model=model,
        action_chain=_first_path_action_text(model, fallback=action_fallback, limit=action_limit, max_fragments=3),
        capability_chain=_first_path_capability_text(
            model,
            fallback=capability_fallback,
            limit=capability_limit,
            gerund=False,
            max_fragments=7,
        ),
        visible_result=_first_path_outcome_text(
            model,
            proof_boundary=proof_boundary,
            fallback=outcome_fallback,
            limit=outcome_limit,
        ),
    )


def first_path_action_phrase(
    value: Any,
    *,
    fallback: str = "complete the first product action",
    limit: int = 220,
    max_fragments: int = 3,
) -> str:
    """Return only the user-side action chain from a first path."""

    model = _model_for(value)
    return _first_path_action_text(model, fallback=fallback, limit=limit, max_fragments=max_fragments)


def first_path_outcome_phrase(
    value: Any,
    *,
    proof_boundary: Any = "",
    fallback: str = "the promised user-visible result",
    limit: int = 220,
) -> str:
    """Return the object/result a participant can use after the first path."""

    model = _model_for(value)
    return _first_path_outcome_text(model, proof_boundary=proof_boundary, fallback=fallback, limit=limit)


def _model_for(value: Any) -> FirstPathModel:
    from odylith.runtime.domain_intelligence.greenfield_first_path_semantics import first_path_model

    return first_path_model(value)


def _first_path_capability_text(
    model: FirstPathModel,
    *,
    fallback: str,
    limit: int,
    gerund: bool,
    max_fragments: int,
) -> str:
    steps = [step for step in model.steps if step and not is_trivial_start(step)]
    selected: list[str] = []
    primary_actor = _primary_actor_signature(model)
    if model.material_action and not is_system_generated_action(model.material_action):
        selected.append(model.material_action)
    selected_fragments = {action_chain_fragment(row).casefold() for row in selected if action_chain_fragment(row)}
    included_visible_result = False
    visible_seen = False
    for step in steps:
        fragment_key = action_chain_fragment(step).casefold()
        if fragment_key and fragment_key in selected_fragments:
            continue
        visible_object = visible_result_object(step)
        visible_step = bool(visible_object and looks_like_visible_result(step))
        if is_system_generated_action(step):
            visible_seen = visible_seen or visible_step
            continue
        if primary_actor and _actor_signature(step) and _actor_signature(step) != primary_actor and visible_seen:
            continue
        if visible_object and clean_first_path_text(visible_object).casefold() == clean_first_path_text(model.visible_outcome).casefold():
            included_visible_result = True
        if len(selected) >= max(1, max_fragments):
            break
        if MATERIAL_ACTION_RE.search(step) or re.search(
            r"\b(?:display|displays|produce|produces|render|renders|return|returns|see|sees|show|shows|view|views|review|reviews|receive|receives)\b",
            step,
            re.IGNORECASE,
        ):
            selected.append(step)
            if fragment_key:
                selected_fragments.add(fragment_key)
        visible_seen = visible_seen or visible_step
    fragmenter = _gerund_action_fragment if gerund else action_chain_fragment
    fragments = _unique([fragmenter(step) for step in selected])
    if not gerund and model.visible_outcome and not included_visible_result:
        outcome = visible_result_object(model.visible_outcome) or clean_first_path_text(model.visible_outcome)
        if outcome:
            fragments.append(_outcome_capability_fragment(outcome))
    text = _join_series(fragments[: max(1, max_fragments)]) or clean_first_path_text(fallback)
    return _clip_phrase(text, limit=limit) or clean_first_path_text(fallback)


def _first_path_action_text(
    model: FirstPathModel,
    *,
    fallback: str,
    limit: int,
    max_fragments: int,
) -> str:
    visible = clean_first_path_text(model.visible_outcome).casefold()
    primary_actor = _primary_actor_signature(model)
    fragments: list[str] = []
    visible_seen = False
    for step in model.steps:
        visible_object = clean_first_path_text(visible_result_object(step)).casefold()
        visible_step = bool(visible_object and looks_like_visible_result(step))
        if is_trivial_start(step):
            continue
        if is_system_generated_action(step):
            visible_seen = visible_seen or visible_step
            continue
        if primary_actor and _actor_signature(step) and _actor_signature(step) != primary_actor and visible_seen:
            continue
        if fragments and (visible_object == visible or (looks_like_visible_result(step) and visible_object)):
            visible_seen = visible_seen or visible_step
            continue
        fragment = action_chain_fragment(step)
        if fragment:
            fragments.append(fragment)
        if len(fragments) >= max(1, max_fragments):
            break
        visible_seen = visible_seen or visible_step
    if not fragments and model.material_action:
        fragments.append(action_chain_fragment(model.material_action))
    return _clip_phrase(_join_series(_unique(fragments)), limit=limit) or clean_first_path_text(fallback)


def _first_path_outcome_text(
    model: FirstPathModel,
    *,
    proof_boundary: Any,
    fallback: str,
    limit: int,
) -> str:
    visible = clean_first_path_text(model.visible_outcome)
    proof = clean_first_path_text(proof_boundary)
    text = proof if _is_low_information_visible_outcome(visible) and proof else visible or proof or clean_first_path_text(model.raw_path)
    text = visible_result_object(text) or action_chain_fragment(text) or text
    text = _lowercase_leading_article(text)
    text = re.sub(r"^(?:It|Them|They|This|That)\b", lambda match: match.group(0).casefold(), text)
    return _clip_phrase(text, limit=limit) or clean_first_path_text(fallback)


def _is_low_information_visible_outcome(value: str) -> bool:
    text = clean_first_path_text(value).casefold().strip(" .")
    return text in {
        "next action",
        "next step",
        "the next action",
        "the next step",
        "what happened next",
        "what happens next",
    }


def visible_action_clause(value: str) -> str:
    text = strip_action_subject(clean_visible_result_phrase(value) or clean_first_path_text(value))
    if re.match(r"^(?:gets?|reads?|receives?|sees?|views?)\b", text, flags=re.IGNORECASE):
        return action_chain_fragment(text)
    return ""


def is_system_generated_action(value: str) -> bool:
    """Return whether a first-path clause describes internal processing, not a user capability."""

    text = clean_first_path_text(value)
    if not text:
        return False
    system_verb = (
        r"asks?|calculates?|checks?|computes?|derives?|displays?|evaluates?|generates?|presents?|renders?|returns?|runs?|"
        r"persists?|saves?|scores?|shows?|stores?|updates?|validates?"
    )
    system_subject = (
        r"product|system|app|application|service|platform|tool|workspace|engine|calculator|dashboard|view|model"
    )
    if re.match(rf"^(?:the\s+)?(?:{system_subject})\s+(?:{system_verb})\b", text, flags=re.IGNORECASE):
        return True
    return bool(re.match(rf"^[A-Z][A-Za-z0-9_-]{{2,}}\s+(?:{system_verb})\b", text))


def looks_like_visible_result(value: str) -> bool:
    text = clean_first_path_text(value)
    return bool(
        re.search(
            r"\b(?:decide|decides|display|displays|export|exports|highlight|highlights|present|presents|produce|produces|publish|publishes|render|renders|return|returns|see|sees|show|shows|view|views|review|reviews|receive|receives)\b",
            text,
            re.IGNORECASE,
        )
        or re.search(
            r"\b(?:card|dashboard|indicator|readout|recommendation|result|summary|timeline|trend|view)\b",
            text,
            re.IGNORECASE,
        )
    )


def clean_visible_result_phrase(value: str) -> str:
    """Remove parser metadata from a visible-result phrase without losing the product outcome."""

    text = clean_first_path_text(value).strip(" .")
    if not text:
        return ""
    text = re.sub(r"^on\s+save,\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\bvisible[- ]result\s+event\b", "visible result", text, flags=re.IGNORECASE)
    match = re.match(
        r"^(?:this|the)\s+(?P<head>.+?)\s+[–—-]\s+(?P<detail>.+?)\s+[–—-]\s+is\s+the\s+visible\s+result\b.*$",
        text,
        flags=re.IGNORECASE,
    )
    if match:
        text = f"{match.group('head')} with {match.group('detail')}"
    text = re.sub(r"\s+is\s+the\s+visible\s+result\b.*$", "", text, flags=re.IGNORECASE).strip(" .")
    text = re.sub(
        r"\s+and\s+the\s+(?:dashboard|screen|view)\s+renders?\s+the\s+visible\s+result\s*:\s*(?:the\s+)?",
        " and the ",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\b(?:dashboard|screen|view)\s+renders?\s+the\s+visible\s+result\s*:\s*(?:the\s+)?",
        "",
        text,
        flags=re.IGNORECASE,
    )
    visible_tail = re.match(
        r"^.+\s+and\s+(?P<tail>(?:the\s+)?[A-Za-z0-9][A-Za-z0-9 '-]{1,60}\s+"
        r"(?:sees?|views?|receives?|gets?|reads?)\s+.+)$",
        text,
        flags=re.IGNORECASE,
    )
    if visible_tail:
        text = visible_tail.group("tail")
    text = re.sub(r"\breadout\s+plus\b", "readout and", text, flags=re.IGNORECASE)
    text = re.sub(r"\bon\s+screen,\s+alongside\b", "on screen with", text, flags=re.IGNORECASE)
    text = re.sub(r"\balongside\b", "with", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(?:this|the)\s+rendered\b", "rendered", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text).strip(" .")
    return text


def is_trivial_start(value: str) -> bool:
    text = clean_first_path_text(value).strip(" .")
    if re.search(r"\b(?:opens?|launches?|starts?)\b", text, flags=re.IGNORECASE) and re.search(
        r"(?:,\s*|\s+and\s+).*\b(?:add|adds|choose|chooses|describe|describes|enter|enters|log|logs|provide|provides|record|records|select|selects|submit|submits)\b",
        text,
        flags=re.IGNORECASE,
    ):
        return False
    return bool(TRIVIAL_START_RE.match(text) or TRIVIAL_NAMED_PRODUCT_START_RE.match(text) or TRIVIAL_AUTH_RE.match(text))


def action_chain_fragment(value: str) -> str:
    text = clean_visible_result_phrase(value) or clean_first_path_text(value).strip(" .")
    text = re.sub(r"^(?:and|then|later|then\s+later)\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+and,\s+if\b.+$", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+if\b.+$", "", text, flags=re.IGNORECASE)
    outcome = visible_result_object(text)
    if outcome and not re.search(r"\b(?:receives?|gets?)\b", text, flags=re.IGNORECASE):
        stripped = strip_action_subject(text)
        if re.match(r"^(?:checks?|decides?|inspects?|reads?|reviews?|sees?|uses?|views?)\b", stripped, flags=re.IGNORECASE):
            return base_action_clause(stripped).strip(" .")
        return f"review {_lowercase_leading_article(outcome)}".strip(" .")
    click = re.search(r"\bclicks?\s+(?P<object>.+?)(?:\s+and\s+.+)?$", text, flags=re.IGNORECASE)
    if click:
        clicked = clean_first_path_text(click.group("object"))
        clicked = re.sub(r"\bon\s+that\b", "on the", clicked, flags=re.IGNORECASE)
        return _clip_phrase(f"choose {clicked.casefold()}", limit=120)
    text = strip_action_subject(text)
    text = _drop_launcher_prefix(text)
    text = base_action_clause(text)
    text = base_following_action_verbs(text)
    text = re.sub(r",\s+and\s+", " and ", text)
    text = re.sub(r"\s+", " ", text).strip(" ,.")
    return text[:1].casefold() + text[1:] if text else ""


def _drop_launcher_prefix(value: str) -> str:
    """Remove app-opening setup when a real action follows in the same clause."""

    text = clean_first_path_text(value).strip(" .")
    if not text:
        return ""
    match = re.match(
        r"^(?:opens?|launches?|starts?)\s+"
        r"(?:(?:the\s+)?(?:(?:web\s+)?app(?:lication)?|product|tool|site|website|screen|page|dashboard|portal|console)"
        r"|[A-Z][A-Za-z0-9_-]{2,})"
        r"(?:\s*,\s*|\s+and\s+)(?P<tail>.+)$",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return text
    tail = clean_first_path_text(match.group("tail")).strip(" .")
    if not MATERIAL_ACTION_RE.search(tail):
        return text
    return tail


def visible_result_object(value: str) -> str:
    text = clean_visible_result_phrase(value) or clean_first_path_text(value)
    text = strip_action_subject(text)
    patterns = (
        r":\s*(?:the\s+)?(?:user|owner|person|participant|actor|operator|applicant|customer)\s+"
        r"(?:sees?|views?|receives?|gets?|reads?)\s+(?P<object>.+)$",
        r"\b(?:decides?|displays?|highlights?|presents?|produces?|renders?|returns?|sees?|shows?|views?|receives?|gets?|reads?|reviews?|checks?|uses?|inspects?)\s+(?P<object>.+)$",
    )
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            result = match.group("object")
            result = re.split(r"(?<=[.!?])\s+", result, maxsplit=1)[0]
            result = re.sub(r"\s+is\s+the\s+visible\s+result\b.*$", "", result, flags=re.IGNORECASE)
            result = re.sub(r"^(?:it|them)\s+(?=(?:on|in|with|as)\b)", "the result ", result, flags=re.IGNORECASE)
            result = _drop_result_recipient(result)
            result = re.sub(
                r",?\s+and\s+(?:reads?|receives?|sees?|views?)\b.+$",
                "",
                result,
                flags=re.IGNORECASE,
            ).strip(" .")
            result = re.sub(
                r",?\s+and\s+(?:adds?|checks?|makes?|places?|records?|routes?|saves?|stores?|updates?)\b.+$",
                "",
                result,
                flags=re.IGNORECASE,
            ).strip(" .")
            return _clip_phrase(result, limit=150)
    if not MATERIAL_ACTION_RE.search(text) and looks_like_visible_result(text):
        return _clip_phrase(re.sub(r"^(?:this|the)\s+", "", text, flags=re.IGNORECASE), limit=150)
    return ""


def _drop_result_recipient(value: str) -> str:
    """Remove a short recipient phrase before the actual visible result object."""

    text = clean_first_path_text(value).strip(" .")
    if not text:
        return ""
    text = re.sub(
        r"^(?:the\s+)?[A-Za-z][A-Za-z0-9'-]*(?:\s+[A-Za-z][A-Za-z0-9'-]*){0,3}\s+"
        r"(?=(?:a|an|the|their|its|what|whether|when|where|why)\b)",
        "",
        text,
        count=1,
        flags=re.IGNORECASE,
    ).strip(" .")
    return text


def _outcome_capability_fragment(value: str) -> str:
    text = clean_first_path_text(value).strip(" .")
    if not text:
        return ""
    fragment = action_chain_fragment(text)
    if fragment and MATERIAL_ACTION_RE.match(fragment):
        return fragment
    return f"see {_lowercase_leading_article(text)}".strip(" .")


def strip_action_subject(value: str) -> str:
    text = clean_first_path_text(value)
    text = re.sub(r"^on\s+save,\s*", "save, ", text, flags=re.IGNORECASE)
    match = MATERIAL_ACTION_RE.search(text)
    if match and match.start() > 0:
        prefix = text[: match.start()].strip(" ,")
        if re.search(r"\b(?:if|that|when|where|which|while)\b", prefix, flags=re.IGNORECASE):
            return text
        if len(label_terms(prefix)) <= 6 and (
            re.search(
                r"\b(?:actor|applicant|borrower|coordinator|customer|owner|participant|patient|person|requester|reviewer|supervisor|user)\b",
                prefix,
                flags=re.IGNORECASE,
            )
            or re.search(r"\b(?:app|application|dashboard|engine|product|service|system|view|workspace)\b", prefix, flags=re.IGNORECASE)
            or (
                re.match(r"^(?:a|an|the|one)\s+", prefix, flags=re.IGNORECASE)
                and not re.search(
                    r"\b(?:app|application|dashboard|engine|product|service|system|view|workspace)\b",
                    prefix,
                    flags=re.IGNORECASE,
                )
            )
        ):
            text = text[match.start() :]
    return text


def _actor_signature(value: str) -> str:
    subject = leading_subject_prefix(value)
    if not subject:
        text = clean_first_path_text(value)
        match = MATERIAL_ACTION_RE.search(text)
        if match and match.start() > 0:
            candidate = text[: match.start()].strip(" ,")
            if len(label_terms(candidate)) <= 6 and (
                re.search(
                    r"\b(?:actor|applicant|borrower|coordinator|customer|owner|participant|patient|person|requester|reviewer|supervisor|user)\b",
                    candidate,
                    flags=re.IGNORECASE,
                )
                or (
                    re.match(r"^(?:a|an|the|one)\s+", candidate, flags=re.IGNORECASE)
                    and not re.search(
                        r"\b(?:app|application|dashboard|engine|product|service|system|view|workspace)\b",
                        candidate,
                        flags=re.IGNORECASE,
                    )
                )
            ):
                subject = candidate
    if not subject:
        return ""
    subject = re.sub(r"^(?:a|an|the|one)\s+", "", subject, flags=re.IGNORECASE)
    subject = re.sub(r"\s+can\s*$", "", subject, flags=re.IGNORECASE)
    subject = re.sub(r"\b(?:product|system|app|application|workspace|engine|dashboard|view)\b", "", subject, flags=re.IGNORECASE)
    return " ".join(
        ordered_terms(
            subject,
            minimum=3,
            stopwords=_ACTOR_SIGNATURE_STOPWORDS,
            preserve_terms=_PRESERVED_SHORT_ACTOR_TERMS,
        )
    )


def _primary_actor_signature(model: FirstPathModel) -> str:
    """Return the actor for the first material user action, if the path names one."""

    actor = _actor_signature(model.material_action)
    if actor:
        return actor
    for step in model.steps:
        if is_trivial_start(step) or is_system_generated_action(step):
            continue
        if not MATERIAL_ACTION_RE.search(step):
            continue
        actor = _actor_signature(step)
        if actor:
            return actor
    return ""


def leading_subject_prefix(value: str) -> str:
    text = re.sub(r"^(?:and|then|later|then\s+later)\s+", "", clean_first_path_text(value), flags=re.IGNORECASE).strip()
    match = MATERIAL_ACTION_RE.search(text)
    if not match or match.start() == 0:
        return ""
    subject = text[: match.start()].strip()
    if not re.match(r"^(?:a|an|the|one|this|that|each|another)\s+", subject, flags=re.IGNORECASE):
        return ""
    if len(label_terms(subject)) > 6:
        return ""
    return subject


def _lowercase_leading_article(value: str) -> str:
    text = clean_first_path_text(value).strip(" .")
    return re.sub(r"^(?:A|An|The)\b", lambda match: match.group(0).casefold(), text)


def _gerund_action_fragment(value: str) -> str:
    text = clean_first_path_text(value).strip(" .")
    text = re.sub(r"^(?:and|then|later|then\s+later)\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+and,\s+if\b.+$", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+if\b.+$", "", text, flags=re.IGNORECASE)
    verb_map = {
        "add": "adding",
        "adds": "adding",
        "adjust": "adjusting",
        "adjusts": "adjusting",
        "approve": "approving",
        "approves": "approving",
        "check": "checking",
        "checks": "checking",
        "choose": "choosing",
        "chooses": "choosing",
        "compare": "comparing",
        "compares": "comparing",
        "complete": "completing",
        "completes": "completing",
        "create": "creating",
        "creates": "creating",
        "edit": "editing",
        "edits": "editing",
        "enter": "entering",
        "enters": "entering",
        "export": "exporting",
        "exports": "exporting",
        "fetch": "fetching",
        "fetches": "fetching",
        "finalize": "finalizing",
        "finalizes": "finalizing",
        "highlight": "highlighting",
        "highlights": "highlighting",
        "import": "importing",
        "imports": "importing",
        "let": "letting",
        "lets": "letting",
        "log": "logging",
        "logs": "logging",
        "publish": "publishing",
        "publishes": "publishing",
        "rank": "ranking",
        "ranks": "ranking",
        "read": "reading",
        "reads": "reading",
        "receive": "receiving",
        "receives": "receiving",
        "record": "recording",
        "records": "recording",
        "review": "reviewing",
        "reviews": "reviewing",
        "save": "saving",
        "saves": "saving",
        "see": "seeing",
        "sees": "seeing",
        "select": "selecting",
        "selects": "selecting",
        "show": "showing",
        "shows": "showing",
        "store": "storing",
        "stores": "storing",
        "submit": "submitting",
        "submits": "submitting",
        "validate": "validating",
        "validates": "validating",
        "view": "viewing",
        "views": "viewing",
    }
    pattern = "|".join(re.escape(item) for item in sorted(verb_map, key=len, reverse=True))
    for match in re.finditer(rf"\b(?P<verb>{pattern})\b", text, flags=re.IGNORECASE):
        verb = match.group("verb").casefold()
        tail = text[match.end() :]
        if verb in {"record", "records"} and re.match(
            r"\s+(?:owner|reviewer|recipient|actor|user|operator|publisher)\b",
            tail,
            flags=re.IGNORECASE,
        ):
            continue
        return _gerund_following_action_verbs(f"{verb_map[verb]}{tail}").strip(" ,.")
    return text[:1].casefold() + text[1:] if text else ""


def _gerund_following_action_verbs(value: str) -> str:
    text = clean_first_path_text(value)
    verb_pairs = {
        "add": "adding",
        "adds": "adding",
        "calculate": "calculating",
        "calculates": "calculating",
        "click": "clicking",
        "clicks": "clicking",
        "display": "displaying",
        "displays": "displaying",
        "enter": "entering",
        "enters": "entering",
        "log": "logging",
        "logs": "logging",
        "produce": "producing",
        "produces": "producing",
        "record": "recording",
        "records": "recording",
        "render": "rendering",
        "renders": "rendering",
        "return": "returning",
        "returns": "returning",
        "save": "saving",
        "saves": "saving",
        "see": "seeing",
        "sees": "seeing",
        "show": "showing",
        "shows": "showing",
        "submit": "submitting",
        "submits": "submitting",
        "update": "updating",
        "updates": "updating",
    }
    for finite, gerund in verb_pairs.items():
        text = re.sub(
            rf"\b(and|or)\s+((?:[a-z]+ly\s+)?)({finite})\b",
            rf"\1 \2{gerund}",
            text,
            flags=re.IGNORECASE,
        )
    return re.sub(r",\s+and\s+", " and ", text, flags=re.IGNORECASE)


def _join_series(values: Sequence[str]) -> str:
    rows = [clean_first_path_text(value).strip(" .") for value in values if clean_first_path_text(value).strip(" .")]
    if not rows:
        return ""
    if len(rows) == 1:
        return rows[0]
    if len(rows) == 2:
        return f"{rows[0]} and {rows[1]}"
    return f"{', '.join(rows[:-1])}, and {rows[-1]}"


def _clip_phrase(value: str, *, limit: int) -> str:
    text = clean_first_path_text(value).strip(" .")
    if len(text) <= limit:
        return text
    clipped = text[: max(0, limit - 1)].rstrip(" ,;:")
    if " " in clipped:
        clipped = clipped.rsplit(" ", 1)[0].rstrip(" ,;:")
    while True:
        cleaned = re.sub(
            r"\b(?:a|an|and|as|at|because|by|for|from|if|in|into|of|on|or|required|that|the|this|to|when|while|with|alongside)$",
            "",
            clipped,
            flags=re.IGNORECASE,
        ).rstrip(" ,;:")
        if cleaned == clipped:
            return cleaned
        clipped = cleaned


def clean_first_path_text(value: Any) -> str:
    text = clean_text(value).replace("`", "")
    text = re.sub(r"\s+([,.;:?!])", r"\1", text)
    return re.sub(r"\s+", " ", text).strip()


def _unique(values: Sequence[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = clean_first_path_text(value)
        key = text.casefold()
        if text and key not in seen:
            seen.add(key)
            result.append(text)
    return result


__all__ = [
    "FirstPathClauses",
    "MATERIAL_ACTION_RE",
    "action_chain_fragment",
    "clean_first_path_text",
    "clean_visible_result_phrase",
    "first_path_action_phrase",
    "first_path_capability_phrase",
    "first_path_clauses",
    "first_path_outcome_phrase",
    "is_system_generated_action",
    "is_trivial_start",
    "leading_subject_prefix",
    "looks_like_visible_result",
    "strip_action_subject",
    "visible_action_clause",
    "visible_result_object",
]
