"""Section parsing for human greenfield Product Intent Confirmations."""

from __future__ import annotations

import re

from odylith.runtime.domain_intelligence.greenfield_text import clean_markdown_text


def confirmed_intent_sections(text: str) -> dict[str, list[str]]:
    """Return normalized section rows from heading and inline-label Markdown."""

    sections: dict[str, list[str]] = {}
    current = "preamble"
    in_fence = False
    fence_header = ""
    fence_lines: list[str] = []
    pending_question = ""
    for raw_line in str(text or "").splitlines():
        line = raw_line.rstrip()
        if line.strip().startswith("```"):
            if in_fence:
                current = _consume_confirmed_intent_fence(
                    fence_lines,
                    current=current,
                    header=fence_header,
                    sections=sections,
                )
                fence_lines = []
                fence_header = ""
                in_fence = False
            else:
                in_fence = True
                fence_header = line.strip()[3:].strip()
            continue
        if in_fence:
            fence_lines.append(line)
            continue
        question = _confirmed_intent_question(line)
        if question:
            pending_question = question
            continue
        if pending_question:
            answer_row = _confirmed_intent_answer_row(pending_question, line)
            if answer_row:
                current = _consume_confirmed_intent_line(answer_row, current=current, sections=sections)
                pending_question = ""
                continue
        pending_question = ""
        for expanded_line in _expanded_confirmed_intent_rows(line):
            current = _consume_confirmed_intent_line(expanded_line, current=current, sections=sections)
    if in_fence:
        _consume_confirmed_intent_fence(
            fence_lines,
            current=current,
            header=fence_header,
            sections=sections,
        )
    return sections


def _expanded_confirmed_intent_rows(line: str) -> list[str]:
    text = str(line or "")
    if not text.strip():
        return [""]
    if "|" in text and text.strip().startswith("|"):
        return [text]
    replacements = (
        (r"\s+(?:the\s+)?durable\s+state\s+object\s+is\s+(?:this\s*)?:", "\nState object:"),
        (r"\s+(?:the\s+)?state\s+object\s+is\s+(?:this\s*)?:", "\nState object:"),
        (r"\s+(?:the\s+)?first\s+complete\s+path\s+is\s*:", "\nFirst complete path:"),
        (r"\s+(?:the\s+)?first\s+workflow\s+is\s*:", "\nFirst complete path:"),
        (r"\s+human\s+actors\s+are\s+", "\nHuman actors are "),
        (r"\s+external\s+systems\s+are\s+", "\nExternal systems are "),
        (r"\s+internal\s+product\s+systems\s+are\s+", "\nInternal product systems are "),
        (r"\s+proof\s+boundary\s*:", "\nProof boundary:"),
        (r"\s+metric\s+note\b", "\nMetric note"),
        (r"\s+success\s+metric\s*:", "\nSuccess metric:"),
        (r"\s+non[-\s]?goal\s*:", "\nNon-goal:"),
        (r"\s+open\s+question\s*:", "\nOpen question:"),
        (r"\s+remaining\s+ambiguity\s*:", "\nRemaining ambiguity:"),
    )
    for pattern, replacement in replacements:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return [row.strip() for row in text.splitlines()]


def _confirmed_intent_question(line: str) -> str:
    match = re.match(r"^\s*Q\s*:\s*(?P<question>.+?)\s*$", str(line or ""), flags=re.IGNORECASE)
    return clean_markdown_text(match.group("question")) if match else ""


def _confirmed_intent_answer_row(question: str, line: str) -> str:
    match = re.match(r"^\s*A\s*:\s*(?P<answer>.+?)\s*$", str(line or ""), flags=re.IGNORECASE)
    if not match:
        return ""
    answer = clean_markdown_text(match.group("answer"))
    normalized = normalize_confirmed_intent_heading(question)
    if not answer:
        return ""
    if "product called" in normalized or "product name" in normalized or "project called" in normalized:
        return f"Product name: {answer}"
    if "who" in normalized and ("serve" in normalized or "user" in normalized):
        return f"Product story: The product serves {answer.rstrip('.') }."
    if "durable record" in normalized or "durable state" in normalized or "state object" in normalized:
        return f"State object: {answer}"
    if "must work first" in normalized or "first path" in normalized or "first workflow" in normalized:
        return f"First complete path: {answer}"
    if "prove" in normalized or "proof" in normalized:
        return f"Proof boundary: {answer}"
    if "systems" in normalized and ("own" in normalized or "product" in normalized):
        return f"Internal product systems: {answer}"
    if "outside system" in normalized or "external" in normalized:
        return f"External systems: {answer}"
    if "metric" in normalized:
        return f"Success metrics: {answer}"
    if "excluded" in normalized or "out of scope" in normalized:
        return f"Non-goal: {answer}"
    if "ambiguous" in normalized or "ambiguity" in normalized or "open question" in normalized:
        return f"Open question: {answer}"
    return ""


def _consume_confirmed_intent_line(line: str, *, current: str, sections: dict[str, list[str]]) -> str:
    if _looks_like_operator_instruction_body(line):
        return current
    if is_confirmed_intent_ignored_section(current) or is_confirmed_intent_supporting_section(current):
        explicit_heading = _explicit_markdown_heading_key(line)
        heading = explicit_heading or confirmed_intent_heading_key(line)
        if (
            heading
            and is_confirmed_intent_supporting_section(current)
            and not is_confirmed_intent_ignored_section(heading)
            and (not explicit_heading or _explicit_markdown_heading_depth(line) > 2)
            and not _supporting_heading_can_reenter_product_truth(line, heading)
        ):
            heading = ""
        if (
            heading
            and is_confirmed_intent_ignored_section(current)
            and explicit_heading
            and _explicit_markdown_heading_depth(line) > 2
            and not is_confirmed_intent_ignored_section(heading)
        ):
            heading = ""
        if heading:
            sections.setdefault(heading, [])
            return heading
        sections.setdefault(current, []).append(line)
        return current
    embedded = _confirmed_intent_embedded_inline_value(line, current=current)
    if embedded:
        for heading, value in embedded:
            sections.setdefault(heading, [])
            if value:
                sections[heading].append(value)
        return current
    table_row = confirmed_intent_table_row_value(line)
    if table_row:
        heading, value = table_row
        sections.setdefault(heading, [])
        if value:
            sections[heading].append(value)
        return heading
    inline_heading = confirmed_intent_inline_heading_value(line)
    if inline_heading:
        heading, value = inline_heading
        sections.setdefault(heading, [])
        if value:
            sections[heading].append(value)
        return heading
    sentence_heading = confirmed_intent_sentence_heading_value(line)
    if sentence_heading:
        heading, value = sentence_heading
        if current == "systems" and heading in {"external_systems", "internal_systems"}:
            sections.setdefault(current, []).append(line)
            return current
        sections.setdefault(heading, [])
        if value:
            sections[heading].append(value)
        return heading
    heading = confirmed_intent_heading_key(line)
    if heading:
        if current == "preamble" and is_confirmed_intent_supporting_section(heading) and _looks_like_document_title_heading(line):
            sections.setdefault(current, []).append(line)
            return current
        sections.setdefault(heading, [])
        return heading
    if not line.strip() and current == "preamble":
        return current
    sections.setdefault(current, []).append(line)
    return current


def _supporting_heading_can_reenter_product_truth(line: str, heading: str) -> bool:
    if is_confirmed_intent_ignored_section(heading):
        return True
    normalized = normalize_confirmed_intent_heading(line)
    base = _section_heading_base(normalized)
    if re.match(r"^(?:slide\s+)?[0-9]+[a-z]?\s+", normalized):
        return heading in {"first_path", "proof_boundary", "state_object"}
    if heading == "state_object":
        return base in {"product object", "state", "state object", "record", "method"}
    if heading == "first_path":
        return base in {"contribution", "contributions", "evaluation case", "release motion"}
    if heading == "proof_boundary":
        return "proof" in base or "boundary" in base or base in {"acceptance", "reproducibility"}
    return False


def _explicit_markdown_heading_key(line: str) -> str:
    text = str(line or "").strip()
    if not text.startswith("#"):
        return ""
    return confirmed_intent_heading_key(text)


def _explicit_markdown_heading_depth(line: str) -> int:
    match = re.match(r"^(?P<hashes>#{1,6})\s+\S", str(line or "").strip())
    return len(match.group("hashes")) if match else 0


def _looks_like_document_title_heading(line: str) -> bool:
    text = str(line or "").strip()
    if not re.match(r"^#(?!#)\s+\S", text):
        return False
    heading = clean_markdown_text(text.lstrip("#").strip())
    normalized = normalize_confirmed_intent_heading(heading)
    if classify_confirmed_intent_heading(heading):
        return False
    words = [word for word in re.split(r"\s+", normalized) if word]
    if len(words) < 2:
        return False
    support_heads = {
        "abstract",
        "appendix",
        "background",
        "benchmarks",
        "conclusion",
        "discussion",
        "evidence",
        "findings",
        "introduction",
        "methods",
        "references",
        "results",
    }
    return not bool(set(words) & support_heads)


def _confirmed_intent_embedded_inline_value(line: str, *, current: str) -> list[tuple[str, str]] | None:
    if ":" not in str(line or ""):
        return None
    match = re.match(
        r"^(?P<prefix>.+?[.!?])\s+"
        r"(?P<label>remaining\s+ambiguity|open\s+question|success\s+metric|metric|proof\s+boundary|non[-\s]?goal)"
        r"\s*:\s*(?P<value>.+)$",
        str(line or "").strip(),
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    label_heading = classify_confirmed_intent_heading(match.group("label"))
    if not label_heading:
        return None
    rows: list[tuple[str, str]] = []
    if current and not is_confirmed_intent_ignored_section(current) and not is_confirmed_intent_supporting_section(current):
        prefix = clean_markdown_text(match.group("prefix"))
        if prefix:
            rows.append((current, prefix))
    rows.append((label_heading, clean_markdown_text(match.group("value"))))
    return rows


def confirmed_intent_heading_key(line: str) -> str:
    text = line.strip()
    if not text:
        return ""
    if re.match(r"^(?:[-*]|\d+[.)])\s+", text):
        return ""
    if text.startswith("#"):
        heading_text = text.lstrip("#").strip()
        return classify_confirmed_intent_heading(heading_text) or _noncanonical_section_key(heading_text)
    if text.endswith(":") and len(text.split()) <= 8:
        heading_text = text[:-1].strip()
        return classify_confirmed_intent_heading(heading_text) or _noncanonical_section_key(heading_text)
    if _looks_like_body_sentence(text):
        return ""
    classified = classify_confirmed_intent_heading(text)
    if classified:
        return classified
    return _noncanonical_section_key(text) if _looks_like_plain_heading(text) else ""


def confirmed_intent_inline_heading_value(line: str) -> tuple[str, str] | None:
    text = line.strip()
    if not text or ":" not in text:
        return None
    label, value = text.split(":", 1)
    normalized_label = normalize_confirmed_intent_heading(label)
    if normalized_label.startswith("metric note"):
        return "success_metrics", _clean_metric_note_value(value)
    if len(label.split()) > 8:
        return None
    heading = classify_confirmed_intent_heading(label.strip())
    if not heading and re.search(r"\b(?:are|contains?|is|tracks?)\b", normalized_label):
        return None
    if not heading:
        return None
    return heading, clean_markdown_text(value)


def confirmed_intent_table_row_value(line: str) -> tuple[str, str] | None:
    text = str(line or "").strip()
    if not text.startswith("|") or not text.endswith("|"):
        return None
    cells = [clean_markdown_text(cell.strip()) for cell in text.strip("|").split("|")]
    cells = [cell for cell in cells if cell]
    if len(cells) < 2:
        return None
    label = cells[0]
    value = " | ".join(cells[1:]).strip()
    normalized_label = normalize_confirmed_intent_heading(label)
    normalized_value = normalize_confirmed_intent_heading(value)
    if not normalized_label or set(normalized_label) <= {"-"}:
        return None
    if normalized_label in {"field", "fact", "section", "product fact", "product field", "product intent field"}:
        return None
    if not normalized_value or set(normalized_value) <= {"-"}:
        return None
    heading = classify_confirmed_intent_heading(label)
    if not heading or is_confirmed_intent_ignored_section(heading):
        return None
    return heading, value


def confirmed_intent_sentence_heading_value(line: str) -> tuple[str, str] | None:
    text = line.strip()
    if not text:
        return None
    if normalize_confirmed_intent_heading(text).startswith("next step instructions"):
        return _ignored_section_key("next step"), ""
    match = re.match(
        r"^(?P<label>human\s+actors|external\s+systems|internal\s+product\s+systems)\s+are\s+(?P<value>.+)$",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    heading = classify_confirmed_intent_heading(match.group("label"))
    if not heading:
        return None
    return heading, clean_markdown_text(match.group("value"))


def _clean_metric_note_value(value: str) -> str:
    text = clean_markdown_text(value)
    text = re.split(r"\s*;\s*do\s+not\s+", text, maxsplit=1, flags=re.IGNORECASE)[0]
    return text.strip(" .")


def _looks_like_plain_heading(text: str) -> bool:
    lowered = normalize_confirmed_intent_heading(text)
    known = {
        "accepted facts",
        "acceptance",
        "acceptance proof",
        "abstract",
        "appendix",
        "background",
        "benchmarks",
        "business goals",
        "conclusion",
        "conclusions",
        "contributions",
        "discussion",
        "evidence",
        "experimental results",
        "experiments",
        "findings",
        "introduction",
        "acknowledgements",
        "acknowledgments",
        "author information",
        "authors",
        "bibliography",
        "citations",
        "copyright",
        "limitations",
        "license",
        "market",
        "method",
        "methods",
        "personas",
        "prd",
        "references",
        "requirements",
        "research findings",
        "results",
        "scope",
        "use cases",
        "user stories",
        "product story",
        "product overview",
        "presenter notes",
        "overview",
        "speaker notes",
        "summary",
        "goal",
        "goals",
        "mission",
        "why",
        "intent",
        "narrative",
        "product title",
        "project title",
        "product name",
        "project name",
        "state object",
        "state",
        "core state",
        "core object",
        "primary object",
        "state model",
        "record",
        "record model",
        "first complete path",
        "first path",
        "first journey",
        "first workflow",
        "workflow",
        "user journey",
        "happy path",
        "golden path",
        "user problem",
        "user problem and risk",
        "problem",
        "customer",
        "customers",
        "opportunity",
        "product view",
        "success metrics",
        "proof metrics",
        "state object that changes through the first journey",
        "first complete path odylith should prove before broader scope",
        "first complete path the product should prove before broader scope",
        "human actors",
        "users",
        "user roles",
        "roles",
        "primary actors",
        "main actors",
        "participants",
        "stakeholders",
        "people who participate",
        "who participates",
        "external systems",
        "external dependencies",
        "integrations",
        "dependencies",
        "external systems not owned by this product",
        "internal systems",
        "internal product systems",
        "owned systems",
        "product modules",
        "modules",
        "capabilities",
        "primary systems",
        "primary product systems",
        "product systems",
        "assumptions",
        "critical assumptions",
        "constraints",
        "ambiguities that would change the first path",
        "material ambiguities",
        "ambiguities",
        "open questions",
        "proof boundary",
        "proof",
        "evidence boundary",
        "release proof",
        "done when",
        "next step",
        "non goals",
        "non-goals",
        "systems",
        "component responsibilities",
        "owned capabilities",
    }
    if lowered in known:
        return True
    if re.match(r"^(?:[0-9]+(?:\.[0-9]+)*|[a-z])\s+[a-z0-9][a-z0-9 ]{2,100}$", lowered):
        return not re.search(r"\b(?:can|could|may|must|shall|should|will|would)\b", lowered)
    words = text.split()
    if not 1 <= len(words) <= 10:
        return False
    if text.endswith((".", "!", "?")):
        return False
    content_words = [word.strip("()[]{}.,:;") for word in words if word.strip("()[]{}.,:;")]
    if not content_words:
        return False
    title_like = sum(1 for word in content_words if word[:1].isupper() or word.isupper())
    if title_like < max(1, len(content_words) - 1):
        return False
    lowered_words = {word.casefold() for word in content_words}
    if lowered_words & {
        "abstract",
        "appendix",
        "architecture",
        "background",
        "benchmark",
        "benchmarks",
        "business",
        "conclusion",
        "contributions",
        "evidence",
        "experiment",
        "experiments",
        "limitations",
        "market",
        "method",
        "methods",
        "requirements",
        "results",
        "scope",
        "references",
    }:
        return True
    return False


def _looks_like_body_sentence(text: str) -> bool:
    value = str(text or "").strip()
    if not value.endswith((".", "!", "?")):
        return False
    return len(value.split()) > 4


def _consume_confirmed_intent_fence(
    lines: list[str],
    *,
    current: str,
    header: str,
    sections: dict[str, list[str]],
) -> str:
    if is_confirmed_intent_ignored_section(current) or is_confirmed_intent_supporting_section(current):
        return current
    rows = _confirmed_intent_fence_rows(lines)
    if not rows or not _fence_looks_like_product_truth(rows, header=header):
        return current
    for row in rows:
        current = _consume_confirmed_intent_line(row, current=current, sections=sections)
    return current


def _confirmed_intent_fence_rows(lines: list[str]) -> list[str]:
    rows: list[str] = []
    for raw_line in lines:
        text = str(raw_line or "").strip()
        if not text:
            continue
        text = text.strip("{}[]")
        text = text.rstrip(",")
        text = re.sub(r'^\s*["\'](?P<label>[^"\']+)["\']\s*:\s*', r"\g<label>: ", text)
        text = re.sub(r"^\s*(?P<label>[A-Za-z0-9_ -]+)\s*:\s*", lambda match: f"{match.group('label')}: ", text)
        text = re.sub(r":\s*[\"'](?P<value>.*?)[\"']$", r": \g<value>", text)
        if text.startswith(("- ", "* ")):
            text = text[2:].strip()
        text = text.strip().strip('"\'')
        text = text.rstrip(",")
        text = re.sub(r'"\s*,\s*"', "; ", text)
        text = text.replace('["', "").replace('"]', "")
        text = text.replace("['", "").replace("']", "")
        if text:
            rows.append(text)
    return rows


def _fence_looks_like_product_truth(rows: list[str], *, header: str) -> bool:
    header_text = normalize_confirmed_intent_heading(header)
    if header_text and _looks_like_operator_instruction_heading(header_text):
        return False
    label_count = 0
    operator_count = 0
    for row in rows:
        label, separator, _value = row.partition(":")
        normalized_label = normalize_confirmed_intent_heading(label)
        if _looks_like_operator_instruction_heading(normalized_label) or _looks_like_operator_instruction_body(row):
            operator_count += 1
            continue
        if separator and classify_confirmed_intent_heading(label):
            label_count += 1
    if label_count < 2:
        return False
    return operator_count < label_count


def classify_confirmed_intent_heading(value: str) -> str:
    normalized = normalize_confirmed_intent_heading(value)
    if not normalized:
        return ""
    normalized = _section_heading_base(normalized)
    normalized = re.sub(r"^(?:the|this|that)\s+", "", normalized).strip()
    normalized = re.sub(r"\s+(?:is|are)$", "", normalized).strip()
    if "product intent confirmation" in normalized:
        return "title"
    if normalized in {"product title", "project title", "product name", "project name", "name", "title"}:
        return "title"
    if (
        "product story" in normalized
        or normalized
        in {
            "accepted facts",
            "business goal",
            "business goals",
            "intent",
            "mission",
            "narrative",
            "overview",
            "product narrative",
            "product overview",
            "problem paragraph",
            "situation",
            "summary",
            "why",
            "why this exists",
            "abstract",
        }
        or normalized in {"goal", "goals"}
    ):
        return "product_story"
    if normalized in {"user problem", "user problem and risk", "problem"}:
        return "problem"
    if normalized in {"customer", "customers"}:
        return "customer"
    if normalized == "opportunity":
        return "opportunity"
    if normalized == "product view":
        return "product_view"
    if normalized in {"metric", "metrics", "success metric", "success metrics", "proof metric", "proof metrics"}:
        return "success_metrics"
    if "human actor" in normalized or normalized in {
        "actors",
        "primary actors",
        "main actors",
        "participants",
        "people",
        "personas",
        "primary users",
        "stakeholders",
        "people who participate",
        "roles",
        "user roles",
        "users",
        "who participates",
    }:
        return "human_actors"
    if normalized in {
        "capabilities",
        "modules",
        "owned capabilities",
        "owned systems",
        "internal services",
        "internal service",
        "primary systems",
        "primary product systems",
        "product capabilities",
        "product modules",
        "product systems",
        "systems on slide",
    }:
        return "internal_systems"
    if normalized == "systems":
        return "systems"
    if "component responsibilit" in normalized or "owned capabilit" in normalized:
        return "component_responsibilities"
    if normalized.startswith("internal ") and (
        "internal product system" in normalized or "internal system" in normalized
    ):
        return "internal_systems"
    if normalized in {
        "dependencies",
        "external dependencies",
        "external integration",
        "external integrations",
        "feed",
        "feeds",
        "integrations",
    }:
        return "external_systems"
    if normalized.startswith("external ") and "external system" in normalized:
        return "external_systems"
    if "internal product system" in normalized or "internal system" in normalized:
        return "internal_systems"
    if "external system" in normalized:
        return "external_systems"
    if "critical assumption" in normalized or normalized in {"assumptions", "constraints"}:
        return "assumptions"
    if "ambiguity" in normalized or "ambiguities" in normalized or "open question" in normalized:
        return "ambiguities"
    if (
        "state object" in normalized
        or normalized
        in {
            "core object",
            "core record",
            "core state",
            "durable state",
            "primary object",
            "product object",
            "record",
            "record model",
            "state",
            "state model",
        }
    ):
        return "state_object"
    if (
        "first complete path" in normalized
        or "first workflow" in normalized
        or "first path" in normalized
        or normalized
        in {
            "first journey",
            "golden path",
            "happy path",
            "use case",
            "use cases",
            "user journey",
            "workflow",
            "contribution",
            "contributions",
            "release path",
            "first release path",
            "evaluation case",
            "release motion",
        }
        or normalized.endswith("release path")
        or normalized.endswith("complete path")
    ):
        return "first_path"
    if "job" in normalized and ("release path" in normalized or "complete this release" in normalized):
        return "first_path"
    if (
        "proof boundary" in normalized
        or normalized
        in {
            "acceptance",
            "acceptance proof",
            "done when",
            "evidence boundary",
            "proof",
            "release proof",
            "reproducibility",
            "reproducibility boundary",
            "reproducibility proof",
        }
    ):
        return "proof_boundary"
    if "non goal" in normalized or "non-goal" in normalized:
        return "non_goals"
    if normalized in {"deferred", "out of scope", "deferred scope", "exclusions", "excluded scope", "limitation", "limitations"}:
        return "non_goals"
    if normalized in {"open product question", "open question", "open questions", "remaining ambiguity"}:
        return "ambiguities"
    return ""


def normalize_confirmed_intent_heading(value: str) -> str:
    text = re.sub(r"[*_`]+", " ", str(value or "")).strip().casefold()
    text = re.sub(r"[–—-]+", " ", text)
    text = re.sub(r"[^a-z0-9\s]+", "", text)
    return re.sub(r"\s+", " ", text).strip()


def _section_heading_base(normalized: str) -> str:
    """Drop paper-style leading section numbers before heading classification."""

    text = re.sub(r"^slide\s+[0-9]+[a-z]?\s+(?=[a-z])", "", str(normalized or "")).strip()
    return re.sub(r"^(?:[0-9]+[a-z]?|[a-z])\s+(?=[a-z])", "", text).strip()


def is_confirmed_intent_ignored_section(key: str) -> bool:
    return str(key or "").startswith("__ignored__:")


def is_confirmed_intent_supporting_section(key: str) -> bool:
    return str(key or "").startswith("__supporting__:")


def _noncanonical_section_key(value: str) -> str:
    normalized = normalize_confirmed_intent_heading(value)
    if not normalized:
        return ""
    if normalized in {"accepted intent begins below", "actual intent", "actual intent begins below", "product intent begins below"}:
        return "preamble"
    if _looks_like_operator_instruction_heading(normalized):
        return _ignored_section_key(normalized)
    return _supporting_section_key(normalized)


def _looks_like_operator_instruction_heading(normalized: str) -> bool:
    if normalized in {
        "after confirmation",
        "child boundaries",
        "coding notes",
        "confirmed cli after confirmation",
        "development notes",
        "do not",
        "execution plan",
        "host reasoning task",
        "implementation notes",
        "implementation plan",
        "next step",
        "next steps",
        "operator instructions",
        "implementation prompt",
        "planning notes",
        "planning scratch",
        "presenter notes",
        "program formation",
        "program plan",
        "release selector",
        "speaker notes",
        "technical plan",
        "visible format contract",
        "write in chat",
        "acknowledgements",
        "acknowledgments",
        "author information",
        "authors",
        "bibliography",
        "citations",
        "copyright",
        "license",
        "references",
    }:
        return True
    instruction_terms = {
        "after confirmation",
        "claude",
        "cli",
        "codex",
        "command",
        "instruction",
        "next step",
        "write in chat",
    }
    planning_terms = {"backlog", "child", "implementation", "plan", "program", "roadmap", "wave"}
    return bool(set(normalized.split()) & instruction_terms) or bool(
        ("formation" in normalized or "notes" in normalized) and set(normalized.split()) & planning_terms
    )


def _looks_like_operator_instruction_body(value: str) -> bool:
    normalized = normalize_confirmed_intent_heading(value)
    if not normalized:
        return False
    if normalized.startswith(("todo for the agent", "todo for agent", "next step instructions")):
        return True
    return "ignore this section as product facts" in normalized or "not product truth" in normalized


def _ignored_section_key(value: str) -> str:
    normalized = normalize_confirmed_intent_heading(value)
    if not normalized:
        return ""
    return "__ignored__:" + normalized.replace(" ", "_")


def _supporting_section_key(value: str) -> str:
    normalized = normalize_confirmed_intent_heading(value)
    if not normalized:
        return ""
    return "__supporting__:" + normalized.replace(" ", "_")


__all__ = [
    "classify_confirmed_intent_heading",
    "confirmed_intent_heading_key",
    "confirmed_intent_inline_heading_value",
    "confirmed_intent_sections",
    "is_confirmed_intent_ignored_section",
    "is_confirmed_intent_supporting_section",
    "normalize_confirmed_intent_heading",
]
