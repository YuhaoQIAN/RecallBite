"""Generate RecallBite memory cards from rough material.

The generator uses LLM when available, falling back to deterministic rule-based analysis.
"""

from __future__ import annotations

import re

from src.analyzers.material_analyzer import AnalyzedMaterial, analyze_material_deterministic
from src.card_schema import create_empty_card
from src.llm_client import create_llm_client


LONG_FORM_INPUTS = {"article", "transcript", "webcast", "lecture", "report", "meeting", "notes"}
TRIGGER_SCENARIOS = [
    "proposal",
    "meeting",
    "client discussion",
    "manager discussion",
    "internal sharing",
    "CPD reflection",
]

# English stopwords that should never become tags or trigger keywords
_TAG_STOPWORDS_EN = {
    "the", "and", "for", "are", "but", "not", "you", "all", "can", "had", "her", "was",
    "one", "our", "out", "day", "get", "has", "him", "his", "how", "its", "may", "new",
    "now", "old", "see", "two", "who", "did", "she", "use", "way", "many", "set", "run",
    "own", "tell", "very", "when", "much", "would", "there", "their", "what", "said",
    "have", "each", "which", "will", "about", "could", "other", "after", "first", "never",
    "these", "think", "where", "being", "every", "great", "might", "shall", "still", "those",
    "while", "this", "that", "with", "from", "they", "know", "want", "been", "were", "time",
    "than", "them", "into", "just", "like", "over", "also", "back", "only", "then", "come",
    "here", "look", "make", "well", "work", "even", "more", "most", "some", "take", "year",
    "good", "life", "long", "part", "such", "down", "find", "give", "does", "made", "call",
    "came", "move", "both", "once", "same", "must", "name", "left", "done", "open", "case",
    "show", "play", "went", "told", "seen", "heard", "land", "home", "side", "hand", "high",
    "kind", "next", "word", "current", "need", "should", "using", "based", "under", "through",
    "during", "before", "above", "below", "between", "among", "within", "without",
    # Output intent words must never become topic tags
    "proposal", "meeting", "client", "manager", "discussion", "sharing", "review", "report",
    "draft", "memo", "opening", "cpd", "reflection", "development", "linkedin", "post",
    "internal", "webinar", "lecture", "talk", "seminar", "transcript", "slide", "screenshot",
    # Generic adjectives/nouns that produce noise
    "social", "ecological", "challenge", "modern", "economic", "system", "important",
    "powerful", "engine", "innovation", "prosperity",
    # PDF noise: organization names, copyright, URLs that must never become tags
    "heart", "american", "association", "copyright", "healthy", "health",
    "org", "orgname", "learn", "more", "www", "http", "https",
    "not", "profit", "reserved", "rights", "check", "page",
    "lifestyle", "essential", "essentials", "blood", "pressure", "sugar",
    "cholesterol", "weight", "tobacco", "sleep", "exercise", "activity",
    "body", "mass", "index", "bmi", "minutes", "hours", "adult",
    "risk", "factor", "factors", "disease", "cardiovascular",
}

_DOMAIN_HINTS = [
    "AI governance", "AI治理", "accountability", "责任分配",
    "risk ownership", "climate risk", "气候风险",
    "ESG", "greenwashing", "披露", "监管",
    "cross-border data compliance", "data ownership",
]


def _analyze_material_with_fallback(
    text: str,
    output_language: str = "auto",
    structured_pages: list[dict] | None = None,
) -> tuple[AnalyzedMaterial, dict]:
    """Try LLM analysis first, fallback to deterministic on failure.

    When structured_pages is available (from PDF parser), uses section-aware analysis.
    Returns:
        (AnalyzedMaterial, meta_dict) where meta_dict records the analysis path.
    """
    # If structured pages available, use section-aware analysis
    if structured_pages:
        from src.analyzers.material_analyzer import analyze_material_structured
        try:
            client = create_llm_client()
            if "AI" in client.mode_label:
                result = client.analyze_material({"text": text}, {}, output_language=output_language)
                # ... use LLM result with structured context
                insights = []
                for item in result.get("key_insights", []):
                    if isinstance(item, dict):
                        insights.append(item)
                    else:
                        insights.append({"insight": str(item), "why_it_matters": "", "evidence": str(item), "location": ""})
                evidence_spans = []
                for span in result.get("evidence_spans", []):
                    if isinstance(span, dict):
                        evidence_spans.append(span)
                    else:
                        evidence_spans.append({"text": str(span), "location": ""})
                analysis = AnalyzedMaterial(
                    thirty_second_takeaway=result.get("thirty_second_takeaway", ""),
                    key_insights=insights,
                    use_scenarios=result.get("use_scenarios", []),
                    talking_points=result.get("talking_points", []),
                    questions_to_ask=result.get("questions_to_ask", []),
                    memory_hook=result.get("memory_hook", ""),
                    evidence_spans=evidence_spans,
                    topic_label=result.get("topic_label", ""),
                )
                return analysis, {"mode": "AI", "fallback": False, "reason": ""}
        except Exception:
            pass  # Fall through to structured deterministic
        # Structured deterministic analysis
        analysis = analyze_material_structured(structured_pages, output_language)
        return analysis, {"mode": "deterministic", "fallback": False, "reason": ""}

    # Flat text path (no structured pages)
    client = create_llm_client()
    if "AI" in client.mode_label:
        try:
            result = client.analyze_material({"text": text}, {}, output_language=output_language)
            insights = []
            for item in result.get("key_insights", []):
                if isinstance(item, dict):
                    insights.append(item)
                else:
                    insights.append({"insight": str(item), "why_it_matters": "", "evidence": str(item), "location": ""})

            evidence_spans = []
            for span in result.get("evidence_spans", []):
                if isinstance(span, dict):
                    evidence_spans.append(span)
                else:
                    evidence_spans.append({"text": str(span), "location": ""})

            analysis = AnalyzedMaterial(
                thirty_second_takeaway=result.get("thirty_second_takeaway", ""),
                key_insights=insights,
                use_scenarios=result.get("use_scenarios", []),
                talking_points=result.get("talking_points", []),
                questions_to_ask=result.get("questions_to_ask", []),
                memory_hook=result.get("memory_hook", ""),
                evidence_spans=evidence_spans,
                topic_label=result.get("topic_label", ""),
            )
            return analysis, {"mode": "AI", "fallback": False, "reason": ""}
        except Exception as exc:
            analysis = analyze_material_deterministic(text, output_language=output_language)
            return analysis, {"mode": "AI", "fallback": True, "reason": f"LLM failed: {type(exc).__name__}"}
    analysis = analyze_material_deterministic(text, output_language=output_language)
    return analysis, {"mode": "deterministic", "fallback": False, "reason": ""}


def generate_card(
    knowledge_seed: str,
    source_type: str,
    topic_tags_text: str = "",
    source: str = "",
    input_type: str = "auto-detect",
    output_language: str = "auto",
    structured_pages: list[dict] | None = None,
) -> dict:
    """Generate a Memory Card from user input.

    Args:
        knowledge_seed: Raw material text.
        source_type: Type of source (e.g. 'Webcast', 'Article').
        topic_tags_text: Comma-separated tags.
        source: Source reference string.
        input_type: auto-detect or explicit type.
        output_language: auto, zh, en, or bilingual.
        structured_pages: Structured PDF sections (from pdf_parser) for section-aware analysis.

    Returns:
        Complete Memory Card dict.
    """
    knowledge_seed = _clean_text(knowledge_seed)
    if not knowledge_seed:
        raise ValueError("knowledge_seed cannot be empty")

    source_type = _clean_text(source_type) or "Auto-detected"
    source = _clean_text(source)
    manual_tags = _parse_tags(topic_tags_text)

    if input_type == "auto-detect" or not input_type:
        input_type = _detect_input_type(knowledge_seed)

    inferred_tags = _infer_topic_tags(knowledge_seed, source_type, source)
    topic_tags = _merge_unique(manual_tags + inferred_tags, limit=8)

    card_type = _determine_card_type(knowledge_seed, input_type)
    fog_index = _calculate_fog_index(knowledge_seed, input_type, source)
    keywords = _extract_keywords(knowledge_seed, topic_tags)

    # Run LLM analysis if available, fallback to deterministic
    analysis, analysis_meta = _analyze_material_with_fallback(
        knowledge_seed, output_language=output_language, structured_pages=structured_pages
    )

    # Resolve effective output language for card content
    _zh_chars = len(re.findall(r'[\u4e00-\u9fff]', knowledge_seed))
    _en_words = len(re.findall(r'[a-zA-Z]{3,}', knowledge_seed))
    _source_lang = "zh" if _zh_chars > _en_words else "en"
    if output_language == "zh":
        _card_lang = "zh"
    elif output_language == "en":
        _card_lang = "en"
    elif output_language == "bilingual":
        _card_lang = "bilingual"
    else:  # auto
        _card_lang = _source_lang

    # Determine source title: use actual source (filename, page title, user input) not topic label
    source_title = source or analysis.topic_label or "Untitled"
    topic_label = analysis.topic_label or ""

    # NOTE: generate_card() is pure — it does NOT persist to the knowledge base.
    # Persistence (save_document + chunk_document) is handled by ingest_material().

    card = create_empty_card()
    card["knowledge_seed"] = knowledge_seed
    card["source_type"] = source_type
    card["source"] = source
    card["topic_tags"] = topic_tags
    card["card_type"] = card_type
    card["fog_index"] = fog_index
    card["topic_label"] = topic_label
    card["trigger_map"] = {
        "keywords": keywords,
        "scenarios": TRIGGER_SCENARIOS,
    }
    card["source_grounding"] = {
        "source_kind": _map_input_to_source_kind(input_type),
        "source_title": source_title,
        "source_reference": source,
        "retrieved_at": card["created_at"],
        "is_verifiable": input_type not in {"thought", "link"} and len(knowledge_seed) >= 40,
        "evidence_spans": analysis.evidence_spans,
    }
    card["_analysis_meta"] = analysis_meta
    # document_id is set externally by ingest_material() after persistence
    card["document_id"] = ""

    if card_type == "Insight Pack":
        detail = _build_insight_pack(analysis, fog_index, _card_lang)
        card["insight_pack"] = detail
        card["core_insight"] = detail["thirty_second_takeaway"]
        card["use_cases"] = detail["use_cases"]
        card["copy_ready_lines"] = detail["copy_ready_lines"]
    elif card_type == "Use Card":
        detail = _build_use_card(analysis, fog_index, _card_lang)
        card["use_card"] = detail
        card["core_insight"] = detail["what_it_means"]
        card["use_cases"] = detail["use_cases"]
        card["copy_ready_lines"] = detail["copy_ready_lines"]
    else:
        detail = _build_clue_card(analysis, fog_index, _card_lang)
        card["clue_card"] = detail
        card["core_insight"] = detail["possible_direction"]
        card["use_cases"] = detail["use_cases"]
        card["copy_ready_lines"] = detail["copy_ready_lines"]

    return card


def ingest_material(
    knowledge_seed: str,
    source_type: str,
    topic_tags_text: str = "",
    source: str = "",
    input_type: str = "auto-detect",
    intended_use: str = "",
    output_language: str = "auto",
    structured_pages: list[dict] | None = None,
    processing_depth: str = "auto",
) -> dict:
    """Full ingestion pipeline: parse, save to KB, generate card, persist card.

    This is the orchestration function that app.py and other callers should use
    for the complete add-knowledge flow.

    Args:
        processing_depth: "auto", "archive", "digest", or "deep_distill".
            - auto: router decides
            - archive: save + index only (no card generation)
            - digest: save + index + Memory Card (default behavior)
            - deep_distill: save + index + Memory Card + candidate Activation Units

    Returns:
        The generated card dict (already saved to cards.json and KB).
        For archive mode, returns a minimal card stub.
        For deep_distill, card includes '_candidate_units' key.
    """
    from src.knowledge_base import chunk_document, save_document
    from src.storage import add_card
    from src.depth_router import route_depth

    # 0. Route processing depth
    user_override = processing_depth if processing_depth != "auto" else ""
    depth_decision = route_depth(
        text=knowledge_seed,
        input_type=input_type,
        intended_use=intended_use,
        user_override=user_override,
    )
    effective_depth = depth_decision.selected_depth

    # 1. Save document to knowledge base (with dedup) — always happens
    doc_id = save_document(
        content=knowledge_seed,
        title=source or "Untitled",
        source_kind=_map_input_to_source_kind(input_type),
        source_reference=source,
    )

    # 2. Chunk and index the document — always happens
    chunk_document(doc_id, knowledge_seed)

    # 3. Archive only: save minimal stub, no card generation
    if effective_depth == "archive":
        card = create_empty_card()
        card["knowledge_seed"] = knowledge_seed[:200]
        card["source_type"] = source_type
        card["source"] = source
        card["card_type"] = "Archived"
        card["core_insight"] = f"Archived: {source or 'Untitled'}"
        card["document_id"] = doc_id
        card["_depth_decision"] = {
            "selected_depth": effective_depth,
            "reason": depth_decision.reason,
            "confidence": depth_decision.confidence,
        }
        add_card(card)
        return card

    # 4. Generate the card (digest and deep_distill both get a card)
    card = generate_card(
        knowledge_seed=knowledge_seed,
        source_type=source_type,
        topic_tags_text=topic_tags_text,
        source=source,
        input_type=input_type,
        output_language=output_language,
        structured_pages=structured_pages,
    )

    if intended_use.strip() if isinstance(intended_use, str) else False:
        card["intended_use"] = intended_use.strip()

    # Link card to document
    card["document_id"] = doc_id
    card["_depth_decision"] = {
        "selected_depth": effective_depth,
        "reason": depth_decision.reason,
        "confidence": depth_decision.confidence,
    }

    # 5. Persist the card
    add_card(card)

    # 6. Deep Distill: extract candidate Activation Units
    if effective_depth == "deep_distill":
        from src.deep_distill import deep_distill
        from src.activation_unit import add_unit

        source_title = card.get("source_grounding", {}).get("source_title", source or "Untitled")
        distill_meta: dict = {}
        candidates = deep_distill(
            text=knowledge_seed,
            document_id=doc_id,
            source_title=source_title,
            output_language=output_language,
            meta_out=distill_meta,
        )
        # Save candidates as draft units
        for unit in candidates:
            add_unit(unit)
        card["_candidate_units"] = [
            {"id": u["id"], "name": u["name"], "type": u["type"], "status": "draft"}
            for u in candidates
        ]
        card["_distill_meta"] = distill_meta

    return card


def _clean_text(value: str) -> str:
    return value.strip() if isinstance(value, str) else ""


def _parse_tags(topic_tags_text: str) -> list[str]:
    if not topic_tags_text:
        return []
    tags = [tag.strip() for tag in re.split(r"[,，/;；\n]+", topic_tags_text)]
    return [tag for tag in tags if tag]


def _merge_unique(values: list[str], limit: int | None = None) -> list[str]:
    seen: set[str] = set()
    merged: list[str] = []
    for value in values:
        key = value.lower()
        if key in seen:
            continue
        seen.add(key)
        merged.append(value)
        if limit is not None and len(merged) >= limit:
            break
    return merged


def _detect_input_type(text: str) -> str:
    lowered = text.lower()
    line_count = text.count("\n")

    if lowered.startswith(("http://", "https://", "www.")):
        return "link"
    if line_count >= 8 and len(text) >= 180:
        return "transcript"
    if line_count >= 3 and len(text) >= 120:
        return "notes"
    if len(text) < 40:
        return "thought"
    if any(token in lowered for token in ["webinar", "lecture", "talk", "seminar"]):
        return "webcast"
    if any(token in lowered for token in ["slide", "deck", "presentation"]):
        return "slide"
    return "article"


def _determine_card_type(text: str, input_type: str) -> str:
    length = len(text)
    if length >= 120:
        return "Insight Pack"
    if length >= 40:
        return "Use Card"
    return "Clue Card"


def _calculate_fog_index(knowledge_seed: str, input_type: str, source: str) -> dict:
    """Evidence-based fog index. Length sets the baseline; source/numbers adjust evidence quality."""
    length = len(knowledge_seed)
    has_source = bool(source.strip())
    has_numbers = bool(re.search(r"\d+(?:[,.]\d+)?\s*(?:%|percent)?", knowledge_seed))
    has_evidence = has_numbers or "http" in knowledge_seed.lower()
    is_rough_memory = input_type == "thought" and length < 40

    if is_rough_memory:
        return {
            "level": "Very Foggy",
            "reason": "Only a rough memory or keyword. No verifiable source or context.",
            "evidence_quality": "low",
            "what_to_add": "Add the original article, transcript, notes, or a concrete example with source.",
        }

    if length >= 120:
        if has_source and has_evidence:
            reason = "Material is long enough, has a source, and contains concrete evidence (numbers, specifics)."
            evidence_quality = "high"
        elif has_source or has_evidence:
            reason = "Material is long enough to form structured insights, though evidence could be stronger."
            evidence_quality = "medium"
        else:
            reason = "Material is long enough to form structured insights, though source verification is missing."
            evidence_quality = "low"
        return {
            "level": "Clear",
            "reason": reason,
            "evidence_quality": evidence_quality,
            "what_to_add": "Can still add an example, data point, speaker quote, or intended use case to make it directly reusable.",
        }

    if length >= 40:
        if has_source or has_evidence:
            reason = "Direction is clear, and some source or evidence is present."
            evidence_quality = "medium"
        else:
            reason = "Direction is clear based on length, but source verification is missing."
            evidence_quality = "low"
        return {
            "level": "Foggy",
            "reason": reason,
            "evidence_quality": evidence_quality,
            "what_to_add": "Add industry background, source details, concrete scenario, speaker example, or original text fragment.",
        }

    return {
        "level": "Very Foggy",
        "reason": "Input is too short or lacks verifiable evidence to form a confident conclusion.",
        "evidence_quality": "low",
        "what_to_add": "Add the original material (article, transcript, notes) or concrete examples with source.",
    }


def _extract_keywords(knowledge_seed: str, topic_tags: list[str]) -> list[str]:
    candidates = list(topic_tags)
    candidates.extend(_keywords_from_text(knowledge_seed))
    candidates.extend([hint for hint in _DOMAIN_HINTS if hint.lower() in knowledge_seed.lower()])
    # Filter out stopwords
    candidates = [c for c in candidates if c.lower() not in _TAG_STOPWORDS_EN]
    return _merge_unique(candidates, limit=8)


def _keywords_from_text(text: str) -> list[str]:
    english_words = [word.lower() for word in re.findall(r"\b[a-zA-Z][a-zA-Z0-9-]{2,}\b", text)]
    # Filter out English stopwords
    english_words = [w for w in english_words if w not in _TAG_STOPWORDS_EN]
    chinese_phrases = [phrase for phrase in re.findall(r"[\u4e00-\u9fff]{2,6}", text) if len(phrase) >= 2]
    return english_words + chinese_phrases


def _infer_topic_tags(knowledge_seed: str, source_type: str, source: str) -> list[str]:
    haystack = f"{knowledge_seed} {source_type} {source}".lower()
    inferred: list[str] = []

    tag_map = [
        ("AI governance", ["ai governance", "aigovernance", "ai\u6cbb\u7406"]),
        ("accountability", ["accountability", "\u8d23\u4efb\u5206\u914d"]),
        ("risk ownership", ["risk ownership"]),  # NOT triggered by generic "risk" or "\u6a21\u578b\u98ce\u9669"
        ("climate risk", ["climate risk", "\u6c14\u5019\u98ce\u9669"]),
        ("ESG", ["esg", "greenwashing", "\u62ab\u9732"]),
        ("data compliance", ["data compliance", "cross-border data", "\u6570\u636e\u5408\u89c4"]),
        ("regulatory", ["regulation", "\u76d1\u7ba1", "\u5408\u89c4", "\u6cd5\u6848"]),
        ("\u5065\u5eb7\u751f\u6d3b\u65b9\u5f0f", ["life's essential", "lifes essential", "heart association", "\u5fc3\u8111\u5065\u5eb7", "\u5065\u5eb7\u751f\u6d3b", "\u516b\u9879\u6307\u6807"]),
        ("\u8425\u517b\u4e0e\u996e\u98df", ["nutrition", "\u8425\u517b", "\u996e\u98df", "dietary", "calories", "fat"]),
        ("\u8eab\u4f53\u6d3b\u52a8", ["physical activity", "exercise", "aerobic", "\u8fd0\u52a8", "\u6d3b\u52a8", "minutes"]),
        ("\u7761\u7720\u5065\u5eb7", ["sleep", "\u7761\u7720", "bedtime"]),
        ("\u5fc3\u8840\u7ba1\u5065\u5eb7", ["blood pressure", "cholesterol", "glucose", "\u8840\u538b", "\u80c6\u56fa\u9187", "\u8840\u7cd6"]),
    ]
    # Output intent words (proposal, meeting, CPD, etc.) are deliberately excluded
    # from topic tags. They belong only to output intent detection.

    for label, needles in tag_map:
        if any(needle in haystack for needle in needles):
            inferred.append(label)

    return inferred


def _map_input_to_source_kind(input_type: str) -> str:
    mapping = {
        "article": "pasted_text",
        "transcript": "pasted_text",
        "notes": "pasted_text",
        "webcast": "pasted_text",
        "slide": "pasted_text",
        "link": "public_url",
        "thought": "rough_memory",
    }
    return mapping.get(input_type, "pasted_text")


def _trim(text: str, limit: int) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1].rstrip() + "…"


# ── Card builders using analyzer output ───────────────────────────────────


def _build_insight_pack(analysis, fog_index: dict, lang: str = "en") -> dict:
    topic = analysis.topic_label or "this material"
    insights = analysis.key_insights

    key_insights_list = [i["insight"] for i in insights[:5]]
    # Do NOT pad with templates. Only return insights actually found in the material.

    if lang == "zh":
        use_scenarios = [
            f"提案 / 报告：引用「{topic}」的具体数字锚定论点。",
            f"会议 / 讨论：把「{topic}」的关键建议连接到当前决策。",
            "CPD / 分享：用页码和数字讲清楚学到了什么。",
        ]
    else:
        use_scenarios = [
            f"Proposal / Report Opening: use the evidence on {topic} to anchor the argument.",
            f"Meeting / Discussion: connect {topic} to current decisions, risks, or trade-offs.",
            f"CPD / Sharing: explain what changed and how you will apply it, using concrete numbers.",
        ]

    talking_points = []
    for i in insights[:2]:
        talking_points.append(i["insight"])
    if lang == "zh":
        talking_points.append(f"如果把「{topic}」的核心建议落地，会改变哪些当前做法？")
    else:
        talking_points.append(f"How would integrating {topic} change our current prioritization?")

    if lang == "zh":
        questions_to_ask = [
            f"在「{topic}」中，哪一条建议最适合当前场景？",
            "这些数字和建议是否有最新研究支持？",
            "如果只记住三条，应该选哪三条？",
        ]
    else:
        questions_to_ask = [
            f"What is the most critical assumption we are missing about {topic}?",
            f"If this insight is applied to our current project, what changes?",
            f"What additional example or source would strengthen this further?",
        ]

    if lang == "zh":
        top_insight = insights[0]['insight'] if insights else ''
        copy_ready_lines = {
            "professional_sentence": _trim(
                f"{top_insight} 这条观点塑造了我们在{topic}上的框架，可在提案或复盘中复用。",
                240,
            ),
            "meeting_question": _trim(
                f"我们在{topic}上最需要验证的核心假设是什么？",
                220,
            ),
            "reflection_sentence": _trim(
                f"我把{topic}的核心判断提炼为可复用的工作表达。",
                220,
            ),
        }
    else:
        copy_ready_lines = {
            "professional_sentence": _trim(
                f"{insights[0]['insight'] if insights else ''} This perspective shapes our framework on {topic} and can be reused in proposals or reviews.",
                240,
            ),
            "meeting_question": _trim(
                f"How do we validate the core assumption about {topic} before acting on it?",
                220,
            ),
            "reflection_sentence": _trim(
                f"I distilled the core judgment on {topic} into a reusable working expression for similar future scenarios.",
                220,
            ),
        }

    if lang == "zh":
        use_cases = {
            "work_angle": _trim(f"把{topic}转化为具体决策输入，而不只是概念。", 180),
            "conversation_angle": _trim(f"在经理/客户讨论中，用{topic}的证据作为切入点。", 180),
            "question_angle": _trim(f"问一个关于{topic}的质量问题：行动前需要验证什么？", 180),
            "personal_asset_angle": _trim("记录为可复用的 CPD / 内部分享资产，附带证据。", 180),
        }
    else:
        use_cases = {
            "work_angle": _trim(f"Turn {topic} into a concrete decision input, not just a concept.", 180),
            "conversation_angle": _trim(f"Use the evidence on {topic} as a specific entry point in manager/client discussions.", 180),
            "question_angle": _trim(f"Ask a quality question about {topic}: what needs verification before we act?", 180),
            "personal_asset_angle": _trim(f"Record this as a reusable CPD / internal sharing asset with evidence attached.", 180),
        }

    return {
        "thirty_second_takeaway": _trim(analysis.thirty_second_takeaway, 220),
        "key_insights": key_insights_list,
        "use_scenarios": use_scenarios,
        "talking_points": talking_points,
        "questions_to_ask": questions_to_ask,
        "copy_ready_paragraph": _trim(
            f"{analysis.thirty_second_takeaway}",
            260,
        ),
        "trigger_map_note": f"Revisit this card when working on {topic}, proposals, meetings, or internal sharing.",
        "fog_note": f"Fog Index: {fog_index['level']} — {fog_index['reason']}",
        "use_cases": use_cases,
        "copy_ready_lines": copy_ready_lines,
    }


def _build_use_card(analysis, fog_index: dict, lang: str = "en") -> dict:
    topic = analysis.topic_label or "this material"
    top = analysis.key_insights[0]["insight"] if analysis.key_insights else ""

    if lang == "zh":
        what_it_means = _trim(f"关于{topic}：{top}", 220) if top else _trim(f"在{topic}上有一些方向，但上下文还不完整。", 220)
        where_to_use = _trim("适合用于提案开场、会议发言要点、复盘笔记或内部分享。", 180)
        how_to_say_it = _trim(f"「{top}」— 然后立刻连接到它对当前任务的影响。", 220) if top else _trim(f"先从{topic}的观察说起，再接到它改变了什么。", 220)
        what_to_ask = _trim(f"在{topic}的这个判断可以应用之前，我们还缺什么前提？", 180)
    else:
        what_it_means = _trim(f"About {topic}: {top}", 220) if top else _trim(f"A useful direction on {topic}, but context is still partial.", 220)
        where_to_use = _trim("Suitable for proposal openings, meeting talking points, review notes, or internal sharing.", 180)
        how_to_say_it = _trim(f"' {top} ' — then immediately connect it to the impact on the current task.", 220) if top else _trim(f"Start with the observation on {topic}, then bridge to what it changes.", 220)
        what_to_ask = _trim(f"What prerequisite are we missing before this judgment on {topic} can be applied?", 180)

    if fog_index["level"] == "Foggy":
        if lang == "zh":
            professional_sentence = _trim(f"{topic}的方向值得注意，但正式引用前最好再核对一条来源或例子。", 220)
            meeting_question = _trim(f"在承诺{topic}的路径之前，我们需要再确认一个前提吗？", 220)
            reflection_sentence = _trim(f"我记录了{topic}的方向，会在形成最终表达前补完上下文。", 220)
        else:
            professional_sentence = _trim(
                f"The direction on {topic} is worth noting, but verify with a source or example before formal use.", 220,
            )
            meeting_question = _trim(
                f"Do we need to confirm one more premise about {topic} before committing to a path?", 220,
            )
            reflection_sentence = _trim(
                f"I noted the direction on {topic} and will complete the context before forming a final expression.", 220,
            )
    else:
        if lang == "zh":
            professional_sentence = _trim(f"{top} 这可以作为{topic}上专业表达的起点。", 220)
            meeting_question = _trim(f"能把{topic}的观察转化成更具体的讨论问题吗？", 220)
            reflection_sentence = _trim(f"这份材料帮我把{topic}从概念推进到了可复用的工作表达。", 220)
        else:
            professional_sentence = _trim(
                f"{top} This can serve as a starting point for professional expression on {topic}.", 220,
            )
            meeting_question = _trim(
                f"Can we turn the observation on {topic} into a more specific discussion question?", 220,
            )
            reflection_sentence = _trim(
                f"This material helped me move {topic} from concept to a reusable working expression.", 220,
            )

    if lang == "zh":
        use_cases = {
            "work_angle": _trim(f"在提案、复盘或项目讨论中应用{topic}。", 180),
            "conversation_angle": _trim("在会议中把这条洞察作为讨论切入点。", 180),
            "question_angle": _trim("问一个推进判断的问题，而不是泛泛的趋势问题。", 180),
            "personal_asset_angle": _trim("保存这段表达，在 CPD 或内部分享中复用。", 180),
        }
    else:
        use_cases = {
            "work_angle": _trim(f"Apply {topic} in proposals, reviews, or project discussions.", 180),
            "conversation_angle": _trim("Use the insight as a discussion entry point in meetings.", 180),
            "question_angle": _trim("Ask a judgment-advancing question rather than a generic trend question.", 180),
            "personal_asset_angle": _trim("Save the expression for reuse in CPD or internal sharing.", 180),
        }

    return {
        "what_it_means": what_it_means,
        "where_to_use": where_to_use,
        "how_to_say_it": how_to_say_it,
        "what_to_ask": what_to_ask,
        "copy_ready_lines": {
            "professional_sentence": professional_sentence,
            "meeting_question": meeting_question,
            "reflection_sentence": reflection_sentence,
        },
        "fog_note": f"Fog Index: {fog_index['level']} — {fog_index['reason']}",
        "trigger_keywords": _extract_keywords(top, [topic]),
        "use_cases": use_cases,
    }


def _build_clue_card(analysis, fog_index: dict, lang: str = "en") -> dict:
    topic = analysis.topic_label or "this topic"
    if lang == "zh":
        possible_direction = _trim(
            f"这条线索可能指向{topic}的一个有用方向，但目前信息太薄，无法确认。", 220,
        )
        what_is_missing = "缺少：行业背景、来源、具体场景、演讲者举例或原始文本片段。"
        do_not_use_as_confirmed = "这张卡片来自非常有限的输入。请勿在正式交付物中将其作为已确认结论。"
        what_to_add_next = _trim(
            f"补充原始文章、转录、笔记或一个例子。告诉我这条线索来自哪里。", 220,
        )
        copy_ready_lines = {
            "professional_sentence": _trim(
                f"我标记了{topic}的这条线索，但在引用前需要恢复原始上下文。", 220,
            ),
            "meeting_question": _trim(
                f"我们见过{topic}的完整材料吗？我想先恢复原始来源。", 220,
            ),
            "reflection_sentence": _trim(
                f"这条线索只提醒我去找{topic}的原始来源；它还不是结论。", 220,
            ),
        }
        use_cases = {
            "work_angle": _trim(f"把{topic}当作未验证线索，而不是直接判断。", 180),
            "conversation_angle": _trim("在讨论中标记为未验证，然后找到原始材料。", 180),
            "question_angle": _trim("问这条线索最初出现在哪里、什么场景下。", 180),
            "personal_asset_angle": _trim("用它提醒回溯{topic}的来源材料，而不是现成知识。", 180),
        }
    else:
        possible_direction = _trim(
            f"This clue may point to a useful direction on {topic}, but current information is too thin to confirm.", 220,
        )
        what_is_missing = "Missing: industry context, source, concrete scenario, speaker example, or original text fragment."
        do_not_use_as_confirmed = "This card was generated from very limited input. Do not use it as a confirmed conclusion in formal deliverables."
        what_to_add_next = _trim(
            f"Add the original article, transcript, notes, or an example. Tell me where this clue came from.", 220,
        )
        copy_ready_lines = {
            "professional_sentence": _trim(
                f"I marked this clue about {topic} but need to recover the original context before quoting it.", 220,
            ),
            "meeting_question": _trim(
                f"Have we seen complete material on {topic}? I want to recover the original source first.", 220,
            ),
            "reflection_sentence": _trim(
                f"This clue only reminds me to find the original source on {topic}; it is not a conclusion yet.", 220,
            ),
        }
        use_cases = {
            "work_angle": _trim(f"Treat {topic} as an unverified clue, not a direct judgment.", 180),
            "conversation_angle": _trim("Flag it as unverified in discussions, then find the original material.", 180),
            "question_angle": _trim("Ask where this clue originally appeared and in what scenario.", 180),
            "personal_asset_angle": _trim("Use it as a reminder to backtrack to source material, not as ready knowledge.", 180),
        }

    return {
        "possible_direction": possible_direction,
        "what_is_missing": what_is_missing,
        "do_not_use_as_confirmed": do_not_use_as_confirmed,
        "what_to_add_next": what_to_add_next,
        "very_foggy_note": f"Fog Index: {fog_index['level']} — {fog_index['reason']}",
        "copy_ready_lines": copy_ready_lines,
        "use_cases": use_cases,
    }
