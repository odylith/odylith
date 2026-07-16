"""Action and result fragment grammar for first-path rendering."""

from __future__ import annotations

import re

from odylith.runtime.common.prose_grammar import (
    action_base_verb_pattern,
    base_action_clause,
    base_following_action_verbs,
    gerund_action_verb,
)
from odylith.runtime.domain_intelligence.greenfield_first_path_subjects import (
    SYSTEM_SUBJECT_TERMS,
    actor_led_action_parts,
    actor_signature,
    leading_subject_prefix,
    looks_like_actor_subject_prefix,
    modal_action_fragment,
    modal_actor_action_parts,
    strip_action_subject,
)
from odylith.runtime.domain_intelligence.greenfield_domain_term_index import label_terms
from odylith.runtime.domain_intelligence.greenfield_first_path_common import MATERIAL_ACTION_RE, clean_first_path_text
from odylith.runtime.domain_intelligence.greenfield_first_path_common import clip_first_path_phrase, lowercase_leading_article
from odylith.runtime.domain_intelligence.greenfield_first_path_control_steps import is_declarative_visible_result_prefix
from odylith.runtime.domain_intelligence.greenfield_first_path_control_steps import strip_requirement_control_tail
from odylith.runtime.domain_intelligence.greenfield_first_path_control_steps import word_sense_metadata_start
from odylith.runtime.domain_intelligence.greenfield_word_sense_metadata import REQUEST_REPORTING_VERBS
from odylith.runtime.domain_intelligence.greenfield_word_sense_metadata import strip_request_reporting_custody_tail
from odylith.runtime.domain_intelligence.greenfield_word_sense_metadata import word_sense_content_clause_describes_comparison
from odylith.runtime.domain_intelligence.greenfield_word_sense_metadata import word_sense_tail_starts_content_clause
from odylith.runtime.domain_intelligence.greenfield_first_path_action_results import nominal_action_result_object
from odylith.runtime.domain_intelligence.greenfield_first_path_action_results import nominalize_leading_result_action
from odylith.runtime.domain_intelligence.greenfield_first_path_noun_compounds import action_word_inside_compound_noun
from odylith.runtime.domain_intelligence.greenfield_first_path_noun_compounds import action_word_starts_result_list_noun
from odylith.runtime.domain_intelligence.greenfield_first_path_types import FirstPathModel
from odylith.runtime.domain_intelligence.greenfield_first_path_result_objects import (
    drop_result_recipient,
    handoff_visible_result_object,
    is_routing_pronoun_result,
    saved_destination_result_object,
)
from odylith.runtime.domain_intelligence.greenfield_first_path_routing import routing_action_clause as _routing_action_clause
from odylith.runtime.domain_intelligence.greenfield_first_path_display_results import display_carrier_result_object
from odylith.runtime.domain_intelligence.greenfield_first_path_short_results import short_nominal_result_phrase
from odylith.runtime.domain_intelligence.greenfield_first_path_text_case import lower_initial_for_fragment as _lower_initial_for_fragment
from odylith.runtime.domain_intelligence.greenfield_gerund_actions import GERUND_ACTION_VERBS
from odylith.runtime.domain_intelligence.greenfield_text import normalize_reviewed_result_nouns, normalize_visible_result_language
from odylith.runtime.domain_intelligence.greenfield_visible_result_focus import focused_visible_result_object

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
_VISIBLE_RESULT_OBJECT_LIMIT = 240

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
        r"advances?|applies?|asks?|assigns?|calculates?|captures?|checks?|computes?|confirms?|controls?|derives?|displays?|emits?|evaluates?|generates?|ingests?|marks?|monitors?|normalizes?|notifies?|presents?|preserves?|processes?|publishes?|records?|renders?|returns?|routes?|runs?|saves?|tracks?|turns?|"
        r"persists?|pulls?|pushes?|saves?|scores?|shows?|stores?|transforms?|updates?|validates?"
    )
    system_subject = (
        r"product|system|os|app|application|service|platform|tool|workspace|engine|pipeline|calculator|dashboard|view|model"
    )
    if re.match(rf"^(?:the\s+)?(?:{system_subject})\s+(?:{system_verb})\b", text, flags=re.IGNORECASE):
        return True
    return bool(re.match(rf"^[A-Z][A-Za-z0-9_-]{{1,}}\s+(?:{system_verb})\b", text))

def looks_like_visible_result(value: str) -> bool:
    text = clean_first_path_text(value)
    return bool(
        re.search(
            r"\b(?:compare|compares|confirm|confirms|correlate|correlates|decide|decides|display|displays|emit|emits|export|exports|find|finds|highlight|highlights|keep|keeps|prepare|prepares|present|presents|produce|produces|publish|publishes|recompute|recomputes|report|reports|render|renders|return|returns|save|saves|see|sees|show|shows|store|stores|surfaces|update|updates|view|views|receive|receives)\b",
            text,
            re.IGNORECASE,
        )
        or re.search(
            r"\b(?:available|card|dashboard|event|indicator|projection|proof|readout|recommendation|result|saved|summary|timeline|trend|view|viewable)\b",
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
        r"^.*?\b(?:display|displays|present|presents|render|renders|show|shows|surface|surfaces)\s+(?:the\s+)?(?:progress|status|current\s+state|result\s+status)\s*,?\s+and\s+(?:ends?|finishes?|produces?|reaches?|returns?|shows?)\s+",
        "",
        text,
        flags=re.IGNORECASE,
    )
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
    raw_text = clean_first_path_text(value).strip(" .")
    transformation_action = _raw_transformation_action_clause(raw_text)
    if transformation_action:
        return transformation_action
    text = clean_visible_result_phrase(raw_text) or raw_text
    text = re.sub(r"^(?:and|then|later|then\s+later)\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+and,\s+if\b.+$", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+if\b.+$", "", text, flags=re.IGNORECASE)
    result_list_fragment = _result_list_capability_fragment(text)
    if result_list_fragment:
        return result_list_fragment
    _modal_actor, modal_action = modal_actor_action_parts(text)
    if modal_action:
        text = modal_action
    routing_action = _routing_action_clause(text, strip_subject=strip_action_subject)
    if routing_action:
        return _lower_initial_for_fragment(routing_action)
    conditional_result = re.search(
        r"\bshows?\s+whether\s+(?P<result>.+)$",
        text,
        flags=re.IGNORECASE,
    )
    if conditional_result:
        result = clean_first_path_text(conditional_result.group("result"))
        return f"review whether {lowercase_leading_article(result)}".strip(" .")
    outcome = "" if (re.search(r"\b(?:route|routes|send|sends|submit|submits)\b", text, flags=re.IGNORECASE) and re.search(r"\bto\s+(?:a|an|the)?\s*[A-Za-z0-9]", text, flags=re.IGNORECASE)) else visible_result_object(text)
    if outcome and not re.search(r"\b(?:receives?|gets?)\b", text, flags=re.IGNORECASE):
        stripped = strip_action_subject(text)
        if re.match(r"^confirms?\b", stripped, flags=re.IGNORECASE) and _confirm_action_is_actor_led(text):
            return base_action_clause(stripped).strip(" .")
        if re.match(
            r"^(?:checks?|closes?|decides?|inspects?|launches?|opens?|publishes?|reads?|reports?|reviews?|sees?|starts?|uses?|views?)\b",
            stripped,
            flags=re.IGNORECASE,
        ):
            return base_action_clause(stripped).strip(" .")
        if _is_transformation_action_clause(stripped):
            return base_action_clause(stripped).strip(" .")
        material_result_action = _material_result_action_clause(stripped, source=text)
        if material_result_action:
            return material_result_action
        if "," in stripped and MATERIAL_ACTION_RE.match(stripped):
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
    text = base_adverbial_note_action(text)
    text = _strip_action_possessives(text)
    text = re.sub(r",\s+and\s+", " and ", text)
    text = re.sub(r"\s+", " ", text).strip(" ,.")
    return _lower_initial_for_fragment(text)

def _raw_transformation_action_clause(value: str) -> str:
    text = clean_first_path_text(value).strip(" .")
    if not text:
        return ""
    text = re.sub(r"^(?:and|then|later|then\s+later)\s+", "", text, flags=re.IGNORECASE)
    _modal_actor, modal_action = modal_actor_action_parts(text)
    candidate = modal_action or strip_action_subject(text)
    if not _is_transformation_action_clause(candidate):
        return ""
    candidate = re.split(
        r"\s+\b(?:including|using|via|with)\b\s+",
        candidate,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0].strip(" .")
    return base_action_clause(candidate).strip(" .")

def base_adverbial_note_action(value: str) -> str:
    return re.sub(
        r"\b(?P<modifier>[a-z]+ly)\s+notes\b",
        lambda match: f"{match.group('modifier')} note",
        clean_first_path_text(value),
        flags=re.IGNORECASE,
    )

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

def _confirm_action_is_actor_led(value: str) -> bool:
    text = clean_first_path_text(value).strip(" .")
    match = MATERIAL_ACTION_RE.search(text)
    if not match:
        return True
    prefix = text[: match.start()].strip(" ,.")
    if not prefix:
        return True
    if looks_like_actor_subject_prefix(prefix):
        return True
    terms = {term.casefold() for term in label_terms(prefix)}
    return not bool(terms & SYSTEM_SUBJECT_TERMS)

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

def _nominal_result_after_control_strip(value: str) -> str:
    text = clean_visible_result_phrase(value)
    if not text or MATERIAL_ACTION_RE.search(text):
        return ""
    if is_declarative_visible_result_prefix(text):
        return ""
    if not re.match(r"^(?:a|an|the)\s+\S", text, flags=re.IGNORECASE):
        return ""
    if len(label_terms(text)) < 3:
        return ""
    result = focused_visible_result_object(nominal_visible_result_object(text))
    return clip_first_path_phrase(result, limit=_VISIBLE_RESULT_OBJECT_LIMIT)

def _prefix_visible_result_before_word_sense_clause(value: str) -> str:
    text = clean_visible_result_phrase(value)
    if not text:
        return ""
    action_match = MATERIAL_ACTION_RE.search(text)
    if action_match and not (
        re.match(r"^(?:a|an|the)\s+", text, flags=re.IGNORECASE) and action_match.end() == len(text)
    ):
        return ""
    if is_declarative_visible_result_prefix(text):
        return ""
    result = focused_visible_result_object(nominal_visible_result_object(text))
    return clip_first_path_phrase(result, limit=_VISIBLE_RESULT_OBJECT_LIMIT)

def _nominal_result_before_reporting_clause(value: str) -> str:
    text = clean_visible_result_phrase(value)
    if not text:
        return ""
    match = re.search(
        r"\b(?:the\s+)?(?:instruction|instructions|prompt|request)\s+"
        r"(?:adds|clarifies|explains|indicates|notes|says|specifies|states|warns)\b",
        text,
        flags=re.IGNORECASE,
    )
    if not match or match.start() <= 0:
        return ""
    prefix = text[: match.start()].strip(" ,.;:")
    return _prefix_visible_result_before_word_sense_clause(prefix)

def _nominal_result_before_request_word_sense_clause(value: str) -> str:
    text = clean_visible_result_phrase(value)
    if not text:
        return ""
    match = re.search(
        r"\b(?:the\s+)?(?:instruction|instructions|prompt|request)\s+"
        r"(?:calls|describes|frames|mentions|treats|uses|adds|clarifies|explains|indicates|notes|says|specifies|states|warns)\b"
        r"[^.]{0,180}\b(?:as\s+both|both|as\s+[A-Za-z][A-Za-z0-9'-]*\s+and\s+as)\b",
        text,
        flags=re.IGNORECASE,
    )
    if not match or match.start() <= 0:
        return ""
    prefix = text[: match.start()].strip(" ,.;:")
    return _prefix_visible_result_before_word_sense_clause(prefix)

def _nominal_result_before_word_sense_content_clause(value: str) -> str:
    text = clean_visible_result_phrase(value)
    if not text:
        return ""
    word_sense_descriptor = (
        r"(?:act|action|adjective|adverb|artifact|entity|gerund|label|name|noun|object|"
        r"operation|participle|predicate|record|subject|term|verb|word)s?"
    )
    match = re.search(
        rf"\b(?:a|an|the|this|that)?\s*[A-Za-z][A-Za-z0-9'-]*(?:\s+[A-Za-z][A-Za-z0-9'-]*){{0,3}}\s+"
        rf"(?:captures?|classif(?:y|ies)|contains?|demonstrates?|displays?|explains?|helps?|includes?|"
        rf"labels?|maps?|models?|presents?|renders?|reviews?|shows?|teaches?|tracks?|treats?|turns?|uses?)\s+"
        rf"[^.]*\b(?:as\s+both|both|as\s+{word_sense_descriptor}\s+and\s+as)\b[^.]*\b{word_sense_descriptor}\b",
        text,
        flags=re.IGNORECASE,
    )
    if not match or match.start() <= 0:
        return ""
    prefix = text[: match.start()].strip(" ,.;:")
    return _prefix_visible_result_before_word_sense_clause(prefix)

def _standalone_request_reporting_product_clause(value: str) -> str:
    text = clean_visible_result_phrase(value)
    if not text:
        return ""
    words = re.findall(r"[A-Za-z][A-Za-z0-9'-]*", text)
    if len(words) < 5:
        return ""
    lowered = [word.casefold() for word in words]
    subject_index = 1 if lowered[0] in {"a", "an", "the", "this", "that"} else 0
    if subject_index + 2 >= len(lowered):
        return ""
    if lowered[subject_index] not in {"instruction", "instructions", "prompt", "request"}:
        return ""
    if lowered[subject_index + 1] not in REQUEST_REPORTING_VERBS:
        return ""
    tail_words = words[subject_index + 2 :]
    if tail_words and tail_words[0].casefold() == "that":
        tail_words = tail_words[1:]
    tail_tokens = [word.casefold() for word in tail_words]
    if not word_sense_tail_starts_content_clause(tail_tokens):
        return ""
    return strip_request_reporting_custody_tail(" ".join(tail_words)).strip(" .")

def _standalone_word_sense_content_clause(value: str) -> bool:
    tokens = [token.casefold() for token in re.findall(r"[A-Za-z][A-Za-z0-9'-]*", clean_visible_result_phrase(value))]
    return word_sense_content_clause_describes_comparison(tokens)

def visible_result_object(value: str) -> str:
    raw_text = clean_first_path_text(value)
    metadata_start = word_sense_metadata_start(raw_text)
    if metadata_start == 0:
        return ""
    request_reporting_text = _standalone_request_reporting_product_clause(raw_text)
    if request_reporting_text:
        raw_text = request_reporting_text
    stripped_text = clean_visible_result_phrase(strip_requirement_control_tail(raw_text))
    if metadata_start > 0 and is_declarative_visible_result_prefix(stripped_text):
        return ""
    raw_visible_text = clean_visible_result_phrase(raw_text)
    control_tail_removed = bool(stripped_text and stripped_text != raw_visible_text)
    text = stripped_text or raw_text
    reporting_prefix_result = _nominal_result_before_reporting_clause(raw_text)
    if reporting_prefix_result:
        return reporting_prefix_result
    request_word_sense_prefix_result = _nominal_result_before_request_word_sense_clause(raw_text)
    if request_word_sense_prefix_result:
        return request_word_sense_prefix_result
    word_sense_prefix_result = _nominal_result_before_word_sense_content_clause(raw_text)
    if word_sense_prefix_result:
        return word_sense_prefix_result
    if _standalone_word_sense_content_clause(raw_text):
        return ""
    display_result = display_carrier_result_object(text, limit=_VISIBLE_RESULT_OBJECT_LIMIT)
    if display_result:
        return display_result
    short_nominal = short_nominal_result_phrase(text, limit=_VISIBLE_RESULT_OBJECT_LIMIT)
    if short_nominal:
        return short_nominal
    nominal = nominal_visible_result_object(text)
    if nominal.casefold().startswith("the tracked metric trend view"):
        return nominal
    result_list_object = _result_list_visible_object(text)
    if result_list_object:
        return result_list_object
    transformation_object = _transformation_result_object(text)
    if transformation_object:
        return transformation_object
    text = strip_action_subject(text)
    handoff_result = handoff_visible_result_object(text)
    if handoff_result:
        return handoff_result
    conditional_result = re.search(
        r"\b(?:sees?|shows?|views?|reviews?)\s+(?P<result>whether\s+.+)$",
        text,
        flags=re.IGNORECASE,
    )
    if conditional_result:
        return clean_first_path_text(conditional_result.group("result")).strip(" .")
    if _routing_action_clause(text, strip_subject=strip_action_subject):
        return ""
    nominal = nominal_visible_result_object(text)
    if nominal.casefold().startswith("the tracked metric trend view"):
        return nominal
    patterns = (
        r":\s*(?:the\s+)?(?:user|owner|person|participant|actor|operator|applicant|customer)\s+"
        r"(?:sees?|views?|receives?|gets?|reads?)\s+(?P<object>.+)$",
        r"(?<![A-Za-z0-9_-])(?P<verb>sends?|publishes?|returns?|delivers?)\s+or\s+"
        r"(?:sends?|publishes?|returns?|delivers?)\s+(?P<object>.+)$",
        r"(?<![A-Za-z0-9_-])(?P<verb>closes?|compares?|confirms?|correlates?|decides?|delivers?|displays?|emits?|finds?|hands?|highlights?|keeps?|prepares?|presents?|produces?|publishes?|reports?|renders?|returns?|saves?|sends?|sees?|shows?|stores?|surfaces|views?|receives?|gets?|reads?|reaches?|reviews?|checks?|uses?|inspects?)\s+(?P<object>.+)$",
    )
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            verb_start = match.start("verb") if "verb" in match.groupdict() else -1
            if verb_start >= 0 and action_word_inside_compound_noun(text, verb_start):
                continue
            result = match.group("object")
            verb = match.groupdict().get("verb", "")
            if is_routing_pronoun_result(verb, result):
                continue
            destination_result = saved_destination_result_object(verb, result)
            if destination_result:
                result = destination_result
            decision_result = _decision_result_object(verb, result)
            if decision_result:
                result = decision_result
            result = re.split(r"(?<=[.!?])\s+", result, maxsplit=1)[0]
            result = re.split(r"\s+[–—-]\s+(?:all|under|while|with|within)\b", result, maxsplit=1, flags=re.IGNORECASE)[0]
            result = re.sub(r"\s+is\s+the\s+visible\s+result\b.*$", "", result, flags=re.IGNORECASE)
            result = re.sub(r"^(?:it|them)\s+(?:on|in|with|as)\s+", "", result, flags=re.IGNORECASE)
            result = drop_result_recipient(result)
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
            result = focused_visible_result_object(nominal_visible_result_object(result))
            return clip_first_path_phrase(result, limit=_VISIBLE_RESULT_OBJECT_LIMIT)
    if not MATERIAL_ACTION_RE.search(text) and looks_like_visible_result(text):
        return clip_first_path_phrase(
            focused_visible_result_object(
                nominal_visible_result_object(re.sub(r"^(?:this|the)\s+", "", text, flags=re.IGNORECASE))
            ),
            limit=_VISIBLE_RESULT_OBJECT_LIMIT,
        )
    if control_tail_removed:
        return _nominal_result_after_control_strip(stripped_text)
    return ""

def _result_list_capability_fragment(value: str) -> str:
    result_object = _result_list_visible_object(value)
    return f"see {_lower_initial_for_fragment(result_object)}".strip(" .") if result_object else ""


def _result_list_visible_object(value: str) -> str:
    text = clean_first_path_text(value).strip(" .")
    for match in MATERIAL_ACTION_RE.finditer(text):
        if action_word_starts_result_list_noun(text, match.start()):
            result = focused_visible_result_object(nominal_visible_result_object(text))
            return clip_first_path_phrase(result, limit=_VISIBLE_RESULT_OBJECT_LIMIT)
    return ""

def _transformation_result_object(value: str) -> str:
    """Return the target object from transformation clauses such as `turn X into Y using Z`."""

    text = clean_first_path_text(value).strip(" .")
    if not text:
        return ""
    match = re.search(
        r"\b(?:turn|turns|convert|converts|transform|transforms)\b.+?\binto\s+(?P<object>.+)$",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return ""
    full_result = focused_visible_result_object(nominal_visible_result_object(match.group("object")))
    if re.match(r"^(?:(?:a|an|the)\s+)?final\b", full_result, flags=re.IGNORECASE):
        return clip_first_path_phrase(full_result, limit=_VISIBLE_RESULT_OBJECT_LIMIT)
    result = re.split(
        r"\s+\b(?:using|with|from|based\s+on|backed\s+by|supported\s+by)\b\s+",
        match.group("object"),
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]
    result = re.split(r"(?<=[.!?])\s+", result, maxsplit=1)[0]
    result = result.strip(" ,.;:")
    if not result:
        return ""
    result = focused_visible_result_object(nominal_visible_result_object(result))
    return clip_first_path_phrase(result, limit=_VISIBLE_RESULT_OBJECT_LIMIT)


def _is_transformation_action_clause(value: str) -> bool:
    text = clean_first_path_text(value).strip(" .")
    first = text.split(maxsplit=1)[0].casefold().strip(".,:;") if text.split() else ""
    return first in {"convert", "converts", "transform", "transforms", "turn", "turns"} and " into " in f" {text.casefold()} "


def _material_result_action_clause(value: str, *, source: str = "") -> str:
    text = clean_first_path_text(value).strip(" .")
    if source and is_system_generated_action(source):
        return ""
    for match in MATERIAL_ACTION_RE.finditer(text):
        verb = match.group(0).casefold().strip(".,:;")
        if verb not in {"confirm", "confirms", "publish", "publishes", "record", "records", "save", "saves"}:
            continue
        if action_word_inside_compound_noun(text, match.start()):
            continue
        return base_action_clause(text[match.start() :]).strip(" .")
    return ""


def _decision_result_object(verb: str, result: str) -> str:
    token = str(verb or "").casefold().strip(".,:;")
    text = clean_first_path_text(result).strip(" .")
    if token not in {"decide", "decides"} or not text.casefold().startswith("whether "):
        return ""
    return f"a decision about {text}"

def nominal_visible_result_object(value: str) -> str:
    text = clean_first_path_text(value).strip(" .")
    if not text:
        return ""
    text = normalize_reviewed_result_nouns(text).strip(" .")
    nominal = nominalize_leading_result_action(text)
    if nominal:
        return nominal
    if re.fullmatch(
        r"(?:the\s+)?tracked\s+metric\s+trend\s+view(?:\s+for\s+.+)?",
        text,
        flags=re.IGNORECASE,
    ):
        return "the tracked metric trend view"
    if re.fullmatch(
        r"(?:whether\s+)?(?:the\s+)?tracked\s+metrics?\s+(?:changed|moved|trended)\s+with\s+usage"
        r"(?:\s+for\s+.+)?",
        text,
        flags=re.IGNORECASE,
    ):
        return "the tracked metric trend view"
    return text

def outcome_capability_fragment(value: str) -> str:
    text = clean_first_path_text(value).strip(" .")
    if not text:
        return ""
    if re.match(r"^(?:a|an|the)\s+", text, flags=re.IGNORECASE):
        return f"see {lowercase_leading_article(text)}".strip(" .")
    fragment = action_chain_fragment(text)
    if fragment and MATERIAL_ACTION_RE.match(fragment):
        return fragment
    return f"see {_lower_initial_for_fragment(text)}".strip(" .")

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

def gerund_action_fragment(value: str) -> str:
    text = clean_first_path_text(value).strip(" .")
    text = re.sub(r"^(?:and|then|later|then\s+later)\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+and,\s+if\b.+$", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+if\b.+$", "", text, flags=re.IGNORECASE)
    text = action_chain_fragment(text) or text
    return _gerund_following_action_verbs(text).strip(" ,.") or _lower_initial_for_fragment(text)

def _gerund_following_action_verbs(value: str) -> str:
    text = clean_first_path_text(value)
    return _gerund_segment_actions(text)

def _gerund_segment_actions(value: str) -> str:
    words = value.split()
    converted: list[str] = []
    convert_next_action = True
    converted_action_seen = False
    connector_pending = False
    for index, word in enumerate(words):
        token = word.strip(".,:;").casefold()
        tail = " ".join(words[index + 1 :])
        gerund = _gerund_for_action_token(token)
        if gerund and convert_next_action:
            if _looks_like_ambiguous_artifact_noun(
                token,
                tail,
                after_coordinated_object=connector_pending and converted_action_seen,
            ):
                converted.append(word)
                convert_next_action = False
                connector_pending = False
                continue
            converted.append(_replace_word_token(word, gerund))
            convert_next_action = False
            converted_action_seen = True
            connector_pending = False
            continue
        converted.append(word)
        if token in {"and", "or"}:
            convert_next_action = True
            connector_pending = True
        elif word.rstrip().endswith(",") and converted_action_seen:
            convert_next_action = True
            connector_pending = True
        elif token.endswith("ly") and convert_next_action:
            convert_next_action = True
        else:
            convert_next_action = False
            connector_pending = False
    return " ".join(converted).strip(" ,.")

def _gerund_for_action_token(token: str) -> str:
    mapped = GERUND_ACTION_VERBS.get(token)
    if mapped:
        return mapped
    if re.fullmatch(action_base_verb_pattern(), token):
        return gerund_action_verb(token)
    return ""

def _looks_like_ambiguous_artifact_noun(
    token: str,
    tail: str,
    *,
    after_coordinated_object: bool = False,
) -> bool:
    if token in {"record", "records"} and re.match(
        r"^(?:owner|reviewer|recipient|actor|user|operator|publisher)\b",
        tail,
        flags=re.IGNORECASE,
    ):
        return True
    if token in {"surface", "surfaces"} and after_coordinated_object and _looks_like_nominal_object_tail(tail):
        return True
    if token in {"rate"} and after_coordinated_object and _looks_like_nominal_object_tail(tail):
        return True
    if token in {"block", "blocks"} and (not tail or tail.lstrip().startswith("(")):
        return True
    return False

def _looks_like_nominal_object_tail(value: str) -> bool:
    first = str(value or "").strip().split(" ", 1)[0].strip(".,:;").casefold()
    if not first or first in {"a", "an", "the", "this", "that", "their", "its", "our", "your"}:
        return False
    if first.endswith("ly"):
        return False
    if _gerund_for_action_token(first):
        return False
    return True

def _replace_word_token(value: str, replacement: str) -> str:
    suffix = ""
    while value and value[-1] in ".,:;":
        suffix = value[-1] + suffix
        value = value[:-1]
    return f"{replacement}{suffix}"

__all__ = ["MATERIAL_ACTION_RE", "action_chain_fragment", "actor_led_action_parts", "actor_signature", "base_adverbial_note_action", "clean_first_path_text", "clean_visible_result_phrase", "clip_first_path_phrase", "gerund_action_fragment", "is_system_generated_action", "is_trivial_start", "leading_subject_prefix", "looks_like_visible_result", "lowercase_leading_article", "modal_action_fragment", "modal_actor_action_parts", "nominal_action_result_object", "nominal_visible_result_object", "outcome_capability_fragment", "primary_actor_signature", "strip_action_subject", "visible_action_clause", "visible_result_object"]
