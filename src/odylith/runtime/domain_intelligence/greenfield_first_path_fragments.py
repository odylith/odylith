"""Action and result fragment grammar for first-path rendering."""

from __future__ import annotations

import re
from typing import Any

from odylith.runtime.common.prose_grammar import action_base_verb_pattern
from odylith.runtime.common.prose_grammar import base_action_clause
from odylith.runtime.common.prose_grammar import base_following_action_verbs
from odylith.runtime.domain_intelligence.greenfield_domain_term_index import label_terms
from odylith.runtime.domain_intelligence.greenfield_domain_term_index import ordered_terms
from odylith.runtime.domain_intelligence.greenfield_first_path_types import FirstPathModel
from odylith.runtime.domain_intelligence.greenfield_text import clean_markdown_text
from odylith.runtime.domain_intelligence.greenfield_text import clip_text_at_word_boundary
from odylith.runtime.domain_intelligence.greenfield_text import normalize_visible_result_language


TRIVIAL_START_RE = re.compile(
    r"^(?:a|an|the)?\s*[^,.;]{0,40}?\b(?:open|opens|launch|launches|start|starts)\s+"
    r"(?:the\s+)?(?:(?:web\s+)?app(?:lication)?|product|tool|site|website|screen|page|dashboard|portal|console)\b"
    r"(?:\s+(?:after|before|during|for|in|on|with)\b[^,.;]*)?\s*$",
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
    r"accept|accepts|add|adds|advance|advances|adjust|adjusts|answer|answers|approve|approves|assign|assigns|attach|attaches|calculate|calculates|capture|captures|"
    r"book|books|check|checks|choose|chooses|compare|compares|complete|completes|confirm|confirms|connect|connects|correct|corrects|decide|decides|"
    r"click|clicks|compute|computes|create|creates|define|defines|delete|deletes|describe|describes|dismiss|dismisses|edit|edits|emit|emits|end|ends|enter|enters|export|exports|fetch|fetches|finalize|finalizes|find|finds|forecast|forecasts|"
    r"display|displays|highlight|highlights|import|imports|inspect|inspects|let|lets|log|logs|make|makes|mark|marks|monitor|monitors|notify|notifies|open|opens|persist|persists|pick|picks|play|plays|"
    r"optimize|optimizes|preserve|preserves|produce|produces|prompt|prompts|provide|provides|publish|publishes|pull|pulls|push|pushes|rank|ranks|rate|rates|read|reads|receive|receives|record|records|render|renders|request|requests|review|reviews|"
    r"report|reports|return|returns|route|routes|run|runs|save|saves|schedule|schedules|screen|screens|see|sees|select|selects|send|sends|share|shares|"
    r"show|shows|stop|stops|store|stores|submit|submits|surface|surfaces|sync|syncs|tap|taps|track|tracks|update|updates|"
    r"transform|transforms|validate|validates|view|views|watch|watches"
    r")\b",
    re.IGNORECASE,
)

_ACTOR_SIGNATURE_STOPWORDS = frozenset(
    {"a", "an", "the", "one", "this", "that", "each", "another", "can"}
)
_PRESERVED_SHORT_ACTOR_TERMS = frozenset({"ai", "ml", "ui", "ux"})


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
        r"advances?|applies?|asks?|calculates?|checks?|computes?|derives?|displays?|emits?|evaluates?|generates?|ingests?|marks?|monitors?|normalizes?|notifies?|presents?|preserves?|processes?|records?|renders?|returns?|routes?|runs?|"
        r"persists?|pulls?|pushes?|saves?|scores?|shows?|stores?|transforms?|updates?|validates?"
    )
    system_subject = (
        r"product|system|app|application|service|platform|tool|workspace|engine|pipeline|calculator|dashboard|view|model"
    )
    if re.match(rf"^(?:the\s+)?(?:{system_subject})\s+(?:{system_verb})\b", text, flags=re.IGNORECASE):
        return True
    return bool(re.match(rf"^[A-Z][A-Za-z0-9_-]{{2,}}\s+(?:{system_verb})\b", text))


def looks_like_visible_result(value: str) -> bool:
    text = clean_first_path_text(value)
    return bool(
        re.search(
            r"\b(?:compare|compares|decide|decides|display|displays|emit|emits|export|exports|find|finds|highlight|highlights|present|presents|produce|produces|publish|publishes|report|reports|render|renders|return|returns|save|saves|see|sees|show|shows|view|views|review|reviews|receive|receives)\b",
            text,
            re.IGNORECASE,
        )
        or re.search(
            r"\b(?:available|card|dashboard|event|indicator|readout|recommendation|result|saved|summary|timeline|trend|view|viewable)\b",
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
    text = normalize_visible_result_language(text)
    text = re.sub(
        r"\s+[–—-]\s+is\s+the\s+smallest\s+version\s+of\s+the\s+whole\s+product\b.*$",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip(" .")
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
    text = re.sub(
        r"\s+[–—-]\s+is\s+(?:the\s+)?(?:whole\s+)?product\s+proven\b.*$",
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
        return f"review {lowercase_leading_article(outcome)}".strip(" .")
    click = re.search(r"\bclicks?\s+(?P<object>.+?)(?:\s+and\s+.+)?$", text, flags=re.IGNORECASE)
    if click:
        clicked = clean_first_path_text(click.group("object"))
        clicked = re.sub(r"\bon\s+that\b", "on the", clicked, flags=re.IGNORECASE)
        return clip_first_path_phrase(f"choose {clicked.casefold()}", limit=120)
    text = strip_action_subject(text)
    text = _drop_launcher_prefix(text)
    text = _drop_explanatory_action_tail(text)
    text = base_action_clause(text)
    text = base_following_action_verbs(text)
    text = _strip_action_possessives(text)
    text = re.sub(r",\s+and\s+", " and ", text)
    text = re.sub(r"\s+", " ", text).strip(" ,.")
    return text[:1].casefold() + text[1:] if text else ""


def _drop_explanatory_action_tail(value: str) -> str:
    text = clean_first_path_text(value).strip(" .")
    parts = re.split(r"\s+[–—-]\s+", text, maxsplit=1)
    if len(parts) != 2:
        return text
    head, tail = (_cleaned.strip(" .") for _cleaned in parts)
    if not head or not tail:
        return text
    if not MATERIAL_ACTION_RE.search(head):
        return text
    if MATERIAL_ACTION_RE.match(tail):
        return head
    return text


def _strip_action_possessives(value: str) -> str:
    text = clean_first_path_text(value)
    return re.sub(r"\b(?:my|your|their|his|her|our|its)\s+(?=first\b)", "", text, flags=re.IGNORECASE)


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
    nominal = nominal_visible_result_object(text)
    if nominal.casefold().startswith("the usage-linked metric change view"):
        return nominal
    text = strip_action_subject(text)
    nominal = nominal_visible_result_object(text)
    if nominal.casefold().startswith("the usage-linked metric change view"):
        return nominal
    patterns = (
        r":\s*(?:the\s+)?(?:user|owner|person|participant|actor|operator|applicant|customer)\s+"
        r"(?:sees?|views?|receives?|gets?|reads?)\s+(?P<object>.+)$",
        r"\b(?:compares?|decides?|displays?|emits?|finds?|highlights?|presents?|produces?|reports?|renders?|returns?|saves?|sees?|shows?|views?|receives?|gets?|reads?|reviews?|checks?|uses?|inspects?)\s+(?P<object>.+)$",
    )
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            result = match.group("object")
            result = re.split(r"(?<=[.!?])\s+", result, maxsplit=1)[0]
            result = re.split(r"\s+[–—-]\s+(?:all|under|while|with|within)\b", result, maxsplit=1, flags=re.IGNORECASE)[0]
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
                r",?\s+and\s+(?:adds?|checks?|completes?|ends?|finishes?|makes?|places?|records?|routes?|saves?|stores?|updates?)\b.+$",
                "",
                result,
                flags=re.IGNORECASE,
            ).strip(" .")
            result = nominal_visible_result_object(result)
            return clip_first_path_phrase(result, limit=150)
    if not MATERIAL_ACTION_RE.search(text) and looks_like_visible_result(text):
        return clip_first_path_phrase(
            nominal_visible_result_object(re.sub(r"^(?:this|the)\s+", "", text, flags=re.IGNORECASE)),
            limit=150,
        )
    return ""


def _drop_result_recipient(value: str) -> str:
    """Remove a short recipient phrase before the actual visible result object."""

    text = clean_first_path_text(value).strip(" .")
    if not text:
        return ""
    if re.match(
        r"^(?:a|an|the)\s+(?:[A-Za-z][A-Za-z0-9'-]*\s+){0,3}"
        r"(?:event|outcome|readout|record|report|result|summary|view)\b",
        text,
        flags=re.IGNORECASE,
    ):
        return text
    words = text.split()
    for index, word in enumerate(words[:5]):
        if index > 0 and re.match(r"^[A-Za-z][A-Za-z0-9'-]*'s$", word):
            return " ".join(words[index:]).strip(" .")
    text = re.sub(
        r"^(?:the\s+)?[A-Za-z][A-Za-z0-9'-]*(?:\s+[A-Za-z][A-Za-z0-9'-]*){0,3}\s+"
        r"(?=(?:a|an|the|their|its|what|whether|when|where|why|[A-Za-z][A-Za-z0-9'-]*'s)\b)",
        "",
        text,
        count=1,
        flags=re.IGNORECASE,
    ).strip(" .")
    return text


def nominal_visible_result_object(value: str) -> str:
    text = clean_first_path_text(value).strip(" .")
    if not text:
        return ""
    nominal = _nominalize_leading_result_action(text)
    if nominal:
        return nominal
    protocol_suffix = " for that protocol" if re.search(r"\bfor\s+that\s+protocol\b", text, flags=re.IGNORECASE) else ""
    if re.fullmatch(
        r"(?:the\s+)?usage-linked\s+metric\s+change\s+view(?:\s+for\s+that\s+protocol)?",
        text,
        flags=re.IGNORECASE,
    ):
        return f"the usage-linked metric change view{protocol_suffix}"
    if re.fullmatch(
        r"(?:whether\s+)?(?:the\s+)?tracked\s+metrics?\s+(?:changed|moved|trended)\s+with\s+usage"
        r"(?:\s+for\s+that\s+protocol)?",
        text,
        flags=re.IGNORECASE,
    ):
        return f"the usage-linked metric change view{protocol_suffix}"
    return text


_RESULT_ACTION_NOMINALS = {
    "capture": "captured",
    "captures": "captured",
    "confirm": "confirmed",
    "confirms": "confirmed",
    "export": "exported",
    "exports": "exported",
    "emit": "emitted",
    "emits": "emitted",
    "preserve": "preserved",
    "preserves": "preserved",
    "publish": "published",
    "publishes": "published",
    "record": "recorded",
    "records": "recorded",
    "report": "reported",
    "reports": "reported",
    "save": "saved",
    "saves": "saved",
    "select": "selected",
    "selects": "selected",
    "store": "stored",
    "stores": "stored",
}


def _nominalize_leading_result_action(value: str) -> str:
    text = clean_first_path_text(value).strip(" .")
    first, separator, rest = text.partition(" ")
    nominal = _RESULT_ACTION_NOMINALS.get(first.casefold().strip(".,:;"))
    if not nominal or not separator:
        return ""
    return f"{nominal} {_drop_leading_article(rest.strip())}".strip()


def _drop_leading_article(value: str) -> str:
    first, separator, rest = clean_first_path_text(value).strip(" .").partition(" ")
    if separator and first.casefold() in {"a", "an", "the"}:
        return rest.strip()
    return clean_first_path_text(value).strip(" .")


def outcome_capability_fragment(value: str) -> str:
    text = clean_first_path_text(value).strip(" .")
    if not text:
        return ""
    fragment = action_chain_fragment(text)
    if fragment and MATERIAL_ACTION_RE.match(fragment):
        return fragment
    return f"see {lowercase_leading_article(text)}".strip(" .")


def strip_action_subject(value: str) -> str:
    text = clean_first_path_text(value)
    text = re.sub(r"^on\s+save,\s*", "save, ", text, flags=re.IGNORECASE)
    match = MATERIAL_ACTION_RE.search(text)
    if match and match.start() > 0:
        prefix = text[: match.start()].strip(" ,")
        if match.end() == len(text) and re.match(r"^(?:a|an|the)\s+", prefix, flags=re.IGNORECASE):
            return text
        if re.search(r"\b(?:if|that|when|where|which|while)\b", prefix, flags=re.IGNORECASE):
            return text
        if len(label_terms(prefix)) <= 6 and (
            re.search(
                r"\b(?:actor|applicant|coordinator|customer|owner|participant|person|requester|reviewer|supervisor|user)\b",
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


def actor_signature(value: str) -> str:
    subject = leading_subject_prefix(value)
    if not subject:
        text = clean_first_path_text(value)
        match = MATERIAL_ACTION_RE.search(text)
        if match and match.start() > 0:
            candidate = text[: match.start()].strip(" ,")
            if len(label_terms(candidate)) <= 6 and (
                re.search(
                    r"\b(?:actor|applicant|coordinator|customer|owner|participant|person|requester|reviewer|supervisor|user)\b",
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


def primary_actor_signature(model: FirstPathModel) -> str:
    """Return the actor for the first material user action, if the path names one."""

    actor = actor_signature(model.material_action)
    if actor:
        return actor
    for step in model.steps:
        if is_trivial_start(step) or is_system_generated_action(step):
            continue
        if not MATERIAL_ACTION_RE.search(step):
            continue
        actor = actor_signature(step)
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
    subject = re.sub(r"\s+[A-Za-z]+ly$", "", subject, flags=re.IGNORECASE).strip()
    if len(label_terms(subject)) > 6:
        return ""
    return subject


def lowercase_leading_article(value: str) -> str:
    text = clean_first_path_text(value).strip(" .")
    return re.sub(r"^(?:A|An|The|Today|Tomorrow|This|That)\b", lambda match: match.group(0).casefold(), text)


_GERUND_ACTION_VERBS = {
    "accept": "accepting",
    "accepts": "accepting",
    "add": "adding",
    "adds": "adding",
    "advance": "advancing",
    "advances": "advancing",
    "adjust": "adjusting",
    "adjusts": "adjusting",
    "answer": "answering",
    "answers": "answering",
    "approve": "approving",
    "approves": "approving",
    "block": "blocking",
    "blocks": "blocking",
    "calculate": "calculating",
    "calculates": "calculating",
    "check": "checking",
    "checks": "checking",
    "choose": "choosing",
    "chooses": "choosing",
    "click": "clicking",
    "clicks": "clicking",
    "compare": "comparing",
    "compares": "comparing",
    "complete": "completing",
    "completes": "completing",
    "confirm": "confirming",
    "confirms": "confirming",
    "create": "creating",
    "creates": "creating",
    "display": "displaying",
    "displays": "displaying",
    "dismiss": "dismissing",
    "dismisses": "dismissing",
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
    "make": "making",
    "makes": "making",
    "mark": "marking",
    "marks": "marking",
    "open": "opening",
    "opens": "opening",
    "pick": "picking",
    "picks": "picking",
    "produce": "producing",
    "produces": "producing",
    "prompt": "prompting",
    "prompts": "prompting",
    "publish": "publishing",
    "publishes": "publishing",
    "pull": "pulling",
    "pulls": "pulling",
    "rank": "ranking",
    "ranks": "ranking",
    "read": "reading",
    "reads": "reading",
    "receive": "receiving",
    "receives": "receiving",
    "record": "recording",
    "records": "recording",
    "render": "rendering",
    "renders": "rendering",
    "resolve": "resolving",
    "resolves": "resolving",
    "return": "returning",
    "returns": "returning",
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
    "surface": "surfacing",
    "surfaces": "surfacing",
    "update": "updating",
    "updates": "updating",
    "validate": "validating",
    "validates": "validating",
    "view": "viewing",
    "views": "viewing",
}


def gerund_action_fragment(value: str) -> str:
    text = clean_first_path_text(value).strip(" .")
    text = re.sub(r"^(?:and|then|later|then\s+later)\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+and,\s+if\b.+$", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+if\b.+$", "", text, flags=re.IGNORECASE)
    text = action_chain_fragment(text) or text
    return _gerund_following_action_verbs(text).strip(" ,.") or (text[:1].casefold() + text[1:] if text else "")


def _gerund_following_action_verbs(value: str) -> str:
    text = clean_first_path_text(value)
    return _gerund_segment_actions(text)


def _gerund_segment_actions(value: str) -> str:
    words = value.split()
    converted: list[str] = []
    convert_next_action = True
    for index, word in enumerate(words):
        token = word.strip(".,:;").casefold()
        tail = " ".join(words[index + 1 :])
        gerund = _gerund_for_action_token(token)
        if gerund and convert_next_action:
            if _looks_like_ambiguous_artifact_noun(token, tail):
                converted.append(word)
                convert_next_action = False
                continue
            converted.append(_replace_word_token(word, gerund))
            convert_next_action = False
            continue
        converted.append(word)
        if token in {"and", "or"}:
            convert_next_action = True
        elif token.endswith("ly") and convert_next_action:
            convert_next_action = True
        else:
            convert_next_action = False
    return " ".join(converted).strip(" ,.")


def _gerund_for_action_token(token: str) -> str:
    mapped = _GERUND_ACTION_VERBS.get(token)
    if mapped:
        return mapped
    if re.fullmatch(action_base_verb_pattern(), token):
        return _regular_gerund(token)
    return ""


def _regular_gerund(token: str) -> str:
    if token.endswith("ie"):
        return f"{token[:-2]}ying"
    if token.endswith("e") and not token.endswith(("ee", "oe", "ye")):
        return f"{token[:-1]}ing"
    return f"{token}ing"


def _looks_like_ambiguous_artifact_noun(token: str, tail: str) -> bool:
    if token in {"record", "records"} and re.match(
        r"^(?:owner|reviewer|recipient|actor|user|operator|publisher)\b",
        tail,
        flags=re.IGNORECASE,
    ):
        return True
    if token in {"block", "blocks"} and (not tail or tail.lstrip().startswith("(")):
        return True
    return False


def _replace_word_token(value: str, replacement: str) -> str:
    suffix = ""
    while value and value[-1] in ".,:;":
        suffix = value[-1] + suffix
        value = value[:-1]
    return f"{replacement}{suffix}"


def clip_first_path_phrase(value: str, *, limit: int) -> str:
    text = clean_first_path_text(value).strip(" .")
    if len(text) <= limit:
        return text
    return clip_text_at_word_boundary(
        text,
        limit=max(0, limit - 1),
        dangling_words={
            "a",
            "against",
            "alongside",
            "an",
            "and",
            "around",
            "as",
            "at",
            "because",
            "between",
            "by",
            "for",
            "from",
            "if",
            "in",
            "into",
            "of",
            "on",
            "or",
            "plus",
            "required",
            "that",
            "the",
            "this",
            "to",
            "toward",
            "towards",
            "through",
            "until",
            "via",
            "when",
            "while",
            "with",
            "without",
        },
    )


def clean_first_path_text(value: Any) -> str:
    text = clean_markdown_text(value)
    text = re.sub(r"\s+[–—-]\s*,\s+(?=(?:and|then|finally|later)\b)", ", ", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+[–—-]\s+(?=(?:and|then|finally|later)\b)", ", ", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+[–—-]\s*(?=[,.;:])", "", text)
    text = re.sub(r"\s+[–—-]\s*$", "", text)
    text = re.sub(
        r",?\s+and\s+(?:completes?|ends?|finishes?)\s+(?:the\s+)?(?:flow|journey|loop|moment|path|session)\b[^.!?]*(?=[.!?]|$)",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(?:^|(?<=[.!?])\s+)that\s+single\s+(?:path|loop|journey|flow)\s+[–—-]\s*.*$",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(?:^|(?<=[.!?])\s+)(?:this|that)\s+is\s+(?:one\s+)?(?:full|complete)\s+"
        r"(?:path|loop|journey|flow)\b.*$",
        "",
        text,
        flags=re.IGNORECASE,
    )
    return clean_markdown_text(text)


__all__ = [
    "MATERIAL_ACTION_RE",
    "action_chain_fragment",
    "actor_signature",
    "clean_first_path_text",
    "clean_visible_result_phrase",
    "clip_first_path_phrase",
    "gerund_action_fragment",
    "is_system_generated_action",
    "is_trivial_start",
    "leading_subject_prefix",
    "looks_like_visible_result",
    "lowercase_leading_article",
    "nominal_visible_result_object",
    "outcome_capability_fragment",
    "primary_actor_signature",
    "strip_action_subject",
    "visible_action_clause",
    "visible_result_object",
]
