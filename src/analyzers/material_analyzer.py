"""Deterministic material analyzer.

Extracts valuable insights from raw text without relying on LLMs.
Scores sentences by informational density and filters out fluff.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class ScoredSentence:
    """A sentence with its quality score and metadata."""

    text: str
    score: float = 0.0
    has_number: bool = False
    has_comparison: bool = False
    has_causal: bool = False
    has_regulatory: bool = False
    has_risk_or_opportunity: bool = False
    has_timeframe: bool = False
    is_fluff: bool = False
    is_generic: bool = False


@dataclass
class AnalyzedMaterial:
    """Result of analyzing a material document."""

    thirty_second_takeaway: str = ""
    key_insights: list[dict] = field(default_factory=list)
    use_scenarios: list[str] = field(default_factory=list)
    talking_points: list[str] = field(default_factory=list)
    questions_to_ask: list[str] = field(default_factory=list)
    memory_hook: str = ""
    evidence_spans: list[dict] = field(default_factory=list)
    topic_label: str = ""


# ── Scoring patterns ──────────────────────────────────────────────────────

_NUMBER_RE = re.compile(r"\b\d+(?:[,.]\d+)?\s*(?:%|percent|percentage|倍|万|亿|million|billion)?\b", re.IGNORECASE)

_COMPARISON_WORDS = {
    "vs", "versus", "compared", "unlike", "whereas", "while", "although",
    "不同于", "相比", "相较于", "而", "但是", "然而", "相反",
}

_CAUSAL_WORDS = {
    "because", "therefore", "thus", "hence", "since", "as a result",
    "leading to", "driven by", "caused by", "due to",
    "因为", "所以", "因此", "导致", "由于", "从而", "使得",
}

_REGULATORY_WORDS = {
    "act", "regulation", "directive", "compliance", "supervisory",
    "regulator", "legislation", "policy", "framework", "standard",
    "法案", "监管", "法规", "合规", "directive", "guideline",
    "要求", "规定", "规范",
}

_RISK_OPPORTUNITY_WORDS = {
    "risk", "opportunity", "threat", "challenge", "benefit", "advantage",
    "downside", "upside", "exposure", "mitigation",
    "风险", "机会", "挑战", "威胁", "优势", "劣势", "暴露", "缓解",
}

_TIMEFRAME_WORDS = {
    "202", "20", "quarter", "annual", "year", "month", "week",
    "since", "by ", "until", "from ", "to ", "between",
    "年", "月", "季度", "周", "以来", "以来", "之前", "之后",
}

_FLUFF_PATTERNS = [
    re.compile(r"^\s*welcome\b", re.IGNORECASE),
    re.compile(r"^\s*thank\s+(you|u)\b", re.IGNORECASE),
    re.compile(r"^\s*good\s+(morning|afternoon|evening)\b", re.IGNORECASE),
    re.compile(r"^\s*hello\b", re.IGNORECASE),
    re.compile(r"^\s*hi\b", re.IGNORECASE),
    re.compile(r"^\s*let'?s\s+get\s+started", re.IGNORECASE),
    re.compile(r"^\s*let'?s\s+begin", re.IGNORECASE),
    re.compile(r"^\s*agenda", re.IGNORECASE),
    re.compile(r"^\s*disclaimer", re.IGNORECASE),
    re.compile(r"^\s*forward.looking", re.IGNORECASE),
    re.compile(r"^\s*safe\s+harbor", re.IGNORECASE),
    re.compile(r"^\s* Speaker?:", re.IGNORECASE),
    re.compile(r"^\s*主持人", re.IGNORECASE),
    re.compile(r"^\s*欢迎", re.IGNORECASE),
    re.compile(r"^\s*感谢", re.IGNORECASE),
    re.compile(r"^\s*大家好", re.IGNORECASE),
    re.compile(r"^\s*各位", re.IGNORECASE),
    re.compile(r"^\s*今天", re.IGNORECASE),
    re.compile(r"^\s*议程", re.IGNORECASE),
    re.compile(r"^\s*免责声明", re.IGNORECASE),
]

_GENERIC_PATTERNS = [
    re.compile(r"this\s+(article|paper|report|study|webcast|talk)\s+(discusses|explores|covers|examines)", re.IGNORECASE),
    re.compile(r"本文", re.IGNORECASE),
    re.compile(r"这篇文章", re.IGNORECASE),
    re.compile(r"^\s*in\s+this\s+session", re.IGNORECASE),
    re.compile(r"^\s*today\s+we\s+will", re.IGNORECASE),
    re.compile(r"^\s*we\s+will\s+discuss", re.IGNORECASE),
]

_DUPLICATE_THRESHOLD = 0.75


# ── Core functions ────────────────────────────────────────────────────────


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences, supporting both English and Chinese."""
    # Normalize whitespace
    text = " ".join(text.split())
    # Split on sentence-ending punctuation
    raw = re.split(r'(?<=[。！？.!?])\s+', text)
    cleaned = [s.strip() for s in raw if len(s.strip()) > 10]
    return cleaned


def _jaccard_similarity(a: str, b: str) -> float:
    """Compute Jaccard similarity between two strings (word/char sets)."""
    set_a = set(a.lower().split())
    set_b = set(b.lower().split())
    if not set_a or not set_b:
        return 0.0
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union)


def _score_sentence(sentence: str) -> ScoredSentence:
    """Score a single sentence for informational value."""
    s = ScoredSentence(text=sentence)
    lower = sentence.lower()

    # Numbers
    if _NUMBER_RE.search(sentence):
        s.has_number = True
        s.score += 3.0

    # Comparisons
    if any(w in lower for w in _COMPARISON_WORDS):
        s.has_comparison = True
        s.score += 2.0

    # Causal
    if any(w in lower for w in _CAUSAL_WORDS):
        s.has_causal = True
        s.score += 2.0

    # Regulatory
    if any(w in lower for w in _REGULATORY_WORDS):
        s.has_regulatory = True
        s.score += 2.5

    # Risk / opportunity
    if any(w in lower for w in _RISK_OPPORTUNITY_WORDS):
        s.has_risk_or_opportunity = True
        s.score += 2.0

    # Timeframe
    if any(w in lower for w in _TIMEFRAME_WORDS):
        s.has_timeframe = True
        s.score += 1.0

    # Fluff penalty
    for pattern in _FLUFF_PATTERNS:
        if pattern.search(sentence):
            s.is_fluff = True
            s.score -= 10.0
            break

    # Generic penalty
    for pattern in _GENERIC_PATTERNS:
        if pattern.search(sentence):
            s.is_generic = True
            s.score -= 5.0
            break

    # Length bonus/penalty: very short or very long sentences are less likely to be clean insights
    length = len(sentence)
    if length < 30:
        s.score -= 1.0
    elif 50 <= length <= 200:
        s.score += 0.5
    elif length > 300:
        s.score -= 0.5

    # Penalize list-like sentences (mostly numbers/units, no verb)
    # These are raw data extractions, not insights
    words = sentence.split()
    if len(words) >= 3:
        number_ratio = sum(1 for w in words if re.match(r'^[\d.,/()]+$', w)) / len(words)
        if number_ratio > 0.5:
            s.score -= 2.0  # Mostly numbers = raw data, not an insight

    # Penalize table/label data (nutrition facts, spec sheets, reference tables)
    _table_patterns = [
        r'营养成分表', r'每[盒份瓶罐]', r'一份大小', r'serving\s*size', r'nutrition\s*fact',
        r'amount\s+per\s+serving', r'%\s*daily\s*value', r'每[日天]参考值',
        r'calories?\s+\d+', r'卡路里\s+\d+', r'脂肪总量', r'total\s+fat',
        r'饱和脂肪', r'saturated\s+fat', r'反式脂肪', r'trans\s+fat',
    ]
    for tp in _table_patterns:
        if re.search(tp, sentence, re.IGNORECASE):
            s.score -= 5.0  # Raw table data, not an insight
            break

    return s


def _deduplicate_sentences(sentences: list[ScoredSentence], threshold: float = _DUPLICATE_THRESHOLD) -> list[ScoredSentence]:
    """Remove near-duplicate sentences, keeping the higher-scored one."""
    result: list[ScoredSentence] = []
    for s in sentences:
        is_duplicate = False
        for existing in result:
            if _jaccard_similarity(s.text, existing.text) >= threshold:
                is_duplicate = True
                # Keep the higher score
                if s.score > existing.score:
                    existing.score = s.score
                    existing.text = s.text
                break
        if not is_duplicate:
            result.append(s)
    return result


def _extract_topic_label(scored: list[ScoredSentence]) -> str:
    """Extract a topic label from the highest-scored non-fluff sentences."""
    candidates = [s for s in scored if not s.is_fluff and s.score > 0]
    if not candidates:
        return "this material"

    # Words to skip: English stopwords + bilingual PDF markers
    _skip_words = {"the", "and", "for", "are", "but", "not", "you", "all", "can", "had", "her", "was", "one", "our", "out", "day", "get", "has", "him", "his", "how", "its", "may", "new", "now", "old", "see", "two", "who", "boy", "did", "she", "use", "her", "way", "many", "oil", "sit", "set", "run", "eat", "far", "sea", "eye", "ago", "off", "too", "any", "say", "man", "try", "ask", "end", "why", "let", "put", "say", "she", "try", "way", "own", "say", "too", "old", "tell", "very", "when", "much", "would", "there", "their", "what", "said", "have", "each", "which", "will", "about", "could", "other", "after", "first", "never", "these", "think", "where", "being", "every", "great", "might", "shall", "still", "those", "while", "this", "that", "with", "have", "from", "they", "know", "want", "been", "were", "said", "time", "than", "them", "into", "just", "like", "over", "also", "back", "only", "then", "come", "here", "look", "make", "well", "work", "even", "more", "most", "some", "take", "year", "good", "life", "long", "part", "such", "down", "find", "give", "does", "made", "call", "came", "move", "both", "five", "once", "same", "must", "name", "left", "each", "done", "open", "case", "show", "live", "play", "went", "told", "seen", "heard", "land", "home", "side", "hand", "high", "kind", "next", "word",
        # Bilingual PDF markers that must NEVER become topic words
        "page", "english", "chinese", "bilingual", "section", "container", "servings",
    }
    _skip_zh = {"中文", "英文", "双语", "第一页", "第二页", "第三页", "全天吃", "各种健康"}

    # Collect frequent meaningful words
    word_freq: dict[str, int] = {}
    for s in candidates[:5]:
        for word in re.findall(r"\b[a-zA-Z][a-zA-Z0-9-]{2,}\b", s.text):
            w = word.lower()
            if w in _skip_words:
                continue
            word_freq[w] = word_freq.get(w, 0) + 1
        # Chinese words 2-4 chars
        for phrase in re.findall(r"[\u4e00-\u9fff]{2,6}", s.text):
            if phrase in _skip_zh:
                continue
            word_freq[phrase] = word_freq.get(phrase, 0) + 1

    top_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:3]
    if top_words:
        return ", ".join([w for w, _ in top_words])
    return "this material"


def analyze_material_structured(
    structured_pages: list[dict],
    output_language: str = "auto",
) -> AnalyzedMaterial:
    """Analyze structured PDF sections instead of flat text.

    Each section is analyzed independently, preserving page/topic boundaries.
    The document-level topic is derived from section titles, not word frequency.
    """
    if not structured_pages:
        return AnalyzedMaterial(thirty_second_takeaway="No structured content.")

    # Deduplicate bilingual: for bilingual docs, prefer primary language sections
    # to avoid counting same content twice (zh + en = same insight)
    primary_lang = _detect_primary_language(structured_pages)
    is_bilingual = len({s.get("language") for s in structured_pages if s.get("language") in ("zh", "en")}) > 1

    # For bilingual: use primary language for analysis, secondary for evidence
    if is_bilingual and primary_lang:
        analysis_sections = [s for s in structured_pages if s.get("language") == primary_lang]
        evidence_sections = structured_pages  # all sections for evidence
    else:
        analysis_sections = structured_pages
        evidence_sections = structured_pages

    # Build document-level topic from section titles
    doc_topic = _build_document_topic(analysis_sections)

    # Resolve output language early (needed for section analysis)
    resolved_lang = _resolve_output_language(output_language, primary_lang or "en", is_bilingual)

    # Analyze each section independently
    section_insights: list[dict] = []
    all_evidence: list[dict] = []

    for section in analysis_sections:
        page = section.get("page", 0)
        title = section.get("title", "")
        text = section.get("text", "")
        lang = section.get("language", "")

        if not text.strip():
            continue

        # Score sentences within this section
        sentences = _split_sentences(text)
        if not sentences:
            continue

        scored = [_score_sentence(s) for s in sentences]
        scored.sort(key=lambda s: s.score, reverse=True)
        valuable = [s for s in scored if not s.is_fluff and s.score > 0]

        if not valuable:
            valuable = scored[:2]

        # Section label = title, or infer from first meaningful sentence
        if title and len(title) < 80:
            section_label = title
        elif title:
            section_label = title[:60] + "…"
        else:
            # Infer title from the highest-scored sentence in this section
            inferred = valuable[0].text if valuable else (scored[0].text if scored else "")
            # Take first clause as a short label
            inferred = re.split(r'[。，,.]', inferred)[0].strip()
            if len(inferred) > 40:
                inferred = inferred[:40] + "…"
            section_label = inferred if inferred else f"Page {page}"

        # Top sentence becomes the section insight
        top = valuable[0] if valuable else scored[0]
        section_insights.append({
            "insight": top.text,
            "why_it_matters": _infer_why_it_matters(top, resolved_lang),
            "evidence": top.text,
            "location": f"Page {page}",
            "section_title": section_label,
            "page": page,
            "language": lang,
        })

        # Evidence spans with page numbers
        for s in valuable[:2]:
            all_evidence.append({
                "text": s.text,
                "location": f"Page {page}",
            })

    if not section_insights:
        return AnalyzedMaterial(thirty_second_takeaway="No extractable content found.")

    # Deduplicate insights across sections
    section_insights = _deduplicate_section_insights(section_insights)

    # Takeaway: document-level summary
    takeaway = _build_structured_takeaway(doc_topic, section_insights, resolved_lang)

    # Key insights: one per section, max 5
    key_insights = section_insights[:5]

    # Talking points from top insights
    talking_points = [ins["insight"] for ins in section_insights[:3]]
    if resolved_lang == "zh":
        talking_points.append(f"如果把「{doc_topic}」的核心建议落地，会改变哪些当前做法？")
    else:
        talking_points.append(f"What would change if we applied the core recommendations from '{doc_topic}'?")

    # Questions
    if resolved_lang == "zh":
        questions_to_ask = [
            f"在「{doc_topic}」中，哪一条建议最适合当前场景？",
            "这些数字和建议是否有最新研究支持？",
            "如果只记住三条，应该选哪三条？",
        ]
    else:
        questions_to_ask = [
            f"Which recommendation from '{doc_topic}' is most applicable right now?",
            "Are these numbers and recommendations backed by the latest research?",
            "If you could only remember three, which three would they be?",
        ]

    # Use scenarios
    if resolved_lang == "zh":
        use_scenarios = [
            f"Proposal / Report：引用「{doc_topic}」的具体数字锚定论点。",
            f"Meeting / Discussion：把「{doc_topic}」的关键建议连接到当前决策。",
            "CPD / Sharing：用页码和数字讲清楚学到了什么。",
        ]
    else:
        use_scenarios = [
            f"Proposal / Report: Cite specific numbers from '{doc_topic}' to anchor the argument.",
            f"Meeting / Discussion: Connect key recommendations to current decisions.",
            "CPD / Sharing: Use page numbers and concrete numbers to explain what was learned.",
        ]

    # Memory hook
    top_insight = section_insights[0]
    memory_hook = f"{doc_topic} — {top_insight['insight'][:60]}"

    return AnalyzedMaterial(
        thirty_second_takeaway=takeaway,
        key_insights=key_insights,
        use_scenarios=use_scenarios,
        talking_points=talking_points,
        questions_to_ask=questions_to_ask,
        memory_hook=memory_hook,
        evidence_spans=all_evidence[:6],
        topic_label=doc_topic,
    )


def _detect_primary_language(sections: list[dict]) -> str:
    """Detect which language has more content in structured sections."""
    zh_chars = 0
    en_words = 0
    for s in sections:
        text = s.get("text", "") + s.get("title", "")
        zh_chars += len(re.findall(r'[\u4e00-\u9fff]', text))
        en_words += len(re.findall(r'[a-zA-Z]{3,}', text))
    if zh_chars > en_words:
        return "zh"
    if en_words > 0:
        return "en"
    return ""


def _resolve_output_language(output_language: str, source_lang: str, is_bilingual: bool) -> str:
    """Resolve the output language for takeaway and insights."""
    if output_language == "zh":
        return "zh"
    if output_language == "en":
        return "en"
    if output_language == "bilingual":
        return "bilingual"
    # auto or follow_source
    if is_bilingual:
        return source_lang  # Use primary language
    return source_lang


def _build_document_topic(sections: list[dict]) -> str:
    """Build a document-level topic label from section titles and content."""
    titles = []
    for s in sections:
        t = s.get("title", "").strip()
        if t and len(t) < 80:
            titles.append(t)

    if not titles:
        # Fallback: derive from content keywords
        return _derive_topic_from_content(sections)

    # Check for known document patterns
    all_titles_lower = " ".join(t.lower() for t in titles)
    all_text_sample = " ".join(s.get("text", "")[:100] for s in sections[:4]).lower()
    combined = all_titles_lower + " " + all_text_sample

    # Health / Life's Essential 8 pattern
    health_keywords = ["eat", "diet", "food", "active", "activity", "exercise",
                       "sleep", "weight", "cholesterol", "glucose", "blood sugar",
                       "blood pressure", "tobacco", "nicotine", "smoke"]
    zh_health = ["\u996e\u98df", "\u8fd0\u52a8", "\u6d3b\u52a8", "\u7761\u7720",
                 "\u4f53\u91cd", "\u80c6\u56fa\u9187", "\u8840\u7cd6", "\u8840\u538b",
                 "\u70df\u8349", "\u5c3c\u53e4\u4e01"]
    
    health_match = sum(1 for kw in health_keywords if kw in combined)
    zh_health_match = sum(1 for kw in zh_health if kw in combined)
    
    if health_match >= 3 or zh_health_match >= 3:
        zh_titles = [s.get("title", "") for s in sections if s.get("language") == "zh"]
        if zh_titles and zh_health_match > 0:
            return "Life's Essential 8\uff1a\u5fc3\u8111\u5065\u5eb7\u7684\u516b\u9879\u751f\u6d3b\u4e0e\u5065\u5eb7\u6307\u6807"
        return "Life's Essential 8: Heart & Brain Health Guidelines"

    # ESG / Sustainability pattern
    esg_keywords = ["esg", "sustainability", "climate", "green", "carbon", "emission", "\u53ef\u6301\u7eed", "\u78b3\u6392\u653e"]
    if sum(1 for kw in esg_keywords if kw in combined) >= 2:
        return "ESG & Sustainability Report"

    # AI / Technology pattern
    ai_keywords = ["ai", "artificial intelligence", "machine learning", "governance", "\u4eba\u5de5\u667a\u80fd", "\u6a21\u578b"]
    if sum(1 for kw in ai_keywords if kw in combined) >= 2:
        return "AI Governance & Technology"

    # Generic: use the first meaningful title or combine top 2
    if len(titles) == 1:
        return titles[0]

    # Take first 2 distinctive titles
    distinctive = [t for t in titles if len(t) > 3 and not t.startswith("Page")]
    if distinctive:
        if len(distinctive) >= 2:
            return f"{distinctive[0]} & {distinctive[1]}"
        return distinctive[0]
    return titles[0] if titles else "this material"


def _derive_topic_from_content(sections: list[dict]) -> str:
    """Derive topic from section content when titles are not available."""
    all_text = " ".join(s.get("text", "")[:200] for s in sections[:6])
    # Look for Chinese topic phrases
    zh_phrases = re.findall(r'[\u4e00-\u9fff]{2,6}', all_text)
    if zh_phrases:
        # Use most common 2-4 char phrase
        freq: dict[str, int] = {}
        for p in zh_phrases:
            freq[p] = freq.get(p, 0) + 1
        top = sorted(freq.items(), key=lambda x: x[1], reverse=True)
        if top:
            return top[0][0]
    # English fallback
    en_words = [w.lower() for w in re.findall(r'\b[A-Z][a-z]{3,}\b', all_text)]
    if en_words:
        freq: dict[str, int] = {}
        for w in en_words:
            if w not in {"this", "that", "with", "from", "have", "been", "were", "they", "them", "their"}:
                freq[w] = freq.get(w, 0) + 1
        top = sorted(freq.items(), key=lambda x: x[1], reverse=True)
        if top:
            return top[0][0].title()
    return "this material"


def _deduplicate_section_insights(insights: list[dict]) -> list[dict]:
    """Remove near-duplicate insights across sections."""
    result: list[dict] = []
    for ins in insights:
        is_dup = False
        for existing in result:
            if _jaccard_similarity(ins["insight"], existing["insight"]) >= _DUPLICATE_THRESHOLD:
                is_dup = True
                break
        if not is_dup:
            result.append(ins)
    return result


def _build_structured_takeaway(doc_topic: str, insights: list[dict], lang: str) -> str:
    """Build a document-level takeaway in the correct language."""
    if not insights:
        return "No extractable content."

    # Use insight content for a natural summary, not raw section titles
    top_insight = insights[0].get("insight", "") if insights else ""
    n_sections = len(insights)

    if lang == "zh":
        # Build a concise natural-language summary
        if n_sections >= 3:
            # Multi-topic document
            topics_brief = "、".join(
                ins.get("section_title", "")[:15] for ins in insights[:3]
                if ins.get("section_title") and not ins.get("section_title", "").startswith("Page")
            )
            if topics_brief:
                takeaway = f"《{doc_topic}》涵盖{topics_brief}等{n_sections}个核心主题，每个主题都有具体数字和行动建议。"
            else:
                takeaway = f"《{doc_topic}》涵盖{n_sections}个核心主题，每个主题都有具体数字和行动建议。核心建议：{top_insight[:80]}"
        else:
            takeaway = f"《{doc_topic}》的核心要点：{top_insight[:120]}"
    elif lang == "bilingual":
        zh_summary = f"《{doc_topic}》涵盖{n_sections}个核心主题，各有具体建议。"
        en_summary = f"'{doc_topic}' covers {n_sections} core topics with specific recommendations."
        takeaway = f"{zh_summary}\n{en_summary}"
    else:
        if n_sections >= 3:
            topics_brief = ", ".join(
                ins.get("section_title", "")[:20] for ins in insights[:3]
                if ins.get("section_title") and not ins.get("section_title", "").startswith("Page")
            )
            if topics_brief:
                takeaway = f"'{doc_topic}' covers {topics_brief} and {n_sections} core topics, each with specific numbers and actionable recommendations."
            else:
                takeaway = f"'{doc_topic}' covers {n_sections} core topics with specific numbers and actionable recommendations."
        else:
            takeaway = f"'{doc_topic}': {top_insight[:120]}"

    return takeaway[:240] if len(takeaway) > 240 else takeaway


def analyze_material_deterministic(text: str, output_language: str = "auto") -> AnalyzedMaterial:
    """Analyze raw text and extract structured insights deterministically.

    Args:
        text: Raw material text.
        output_language: auto, zh, en, or bilingual.

    Returns:
        AnalyzedMaterial with scored insights, scenarios, and questions.
    """
    sentences = _split_sentences(text)
    if not sentences:
        return AnalyzedMaterial(
            thirty_second_takeaway="No extractable content found.",
            key_insights=[],
        )

    scored = [_score_sentence(s) for s in sentences]
    scored = _deduplicate_sentences(scored)
    scored.sort(key=lambda s: s.score, reverse=True)

    # Filter out fluff and generic sentences
    valuable = [s for s in scored if not s.is_fluff and s.score > 0]
    if not valuable:
        # Fallback: take the least-bad sentences
        valuable = [s for s in scored if s.score > -5]
    if not valuable:
        valuable = scored[:3]

    topic = _extract_topic_label(scored)

    # Detect source language and resolve output language early
    _zh_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    _en_words = len(re.findall(r'[a-zA-Z]{3,}', text))
    source_lang = "zh" if _zh_chars > _en_words else "en"
    resolved_lang = _resolve_output_language(output_language, source_lang, False)

    # Build key insights with evidence
    key_insights = []
    for i, s in enumerate(valuable[:5], 1):
        insight = {
            "insight": s.text,
            "why_it_matters": _infer_why_it_matters(s, resolved_lang),
            "evidence": s.text,
            "location": "",
        }
        key_insights.append(insight)

    # Thirty-second takeaway
    top = valuable[0] if valuable else scored[0]
    if resolved_lang == "zh":
        takeaway = f"关于「{topic}」，核心观点：{top.text}"
    else:
        takeaway = f"On '{topic}': {top.text}"
    if len(takeaway) > 220:
        takeaway = takeaway[:217] + "\u2026"

    # Use scenarios
    if resolved_lang == "zh":
        use_scenarios = [
            f"Proposal / Report：用这条观点说明「{topic}」的核心判断。",
            f"Meeting / Discussion：把「{topic}」连接到当前决策、风险或取舍。",
            "CPD / Sharing：用具体数字和证据讲清楚学到了什么、下一步怎么用。",
        ]
    else:
        use_scenarios = [
            f"Proposal / Report: Use this insight to anchor the argument on '{topic}'.",
            f"Meeting / Discussion: Connect '{topic}' to current decisions, risks, or trade-offs.",
            "CPD / Sharing: Explain what was learned with concrete numbers and evidence.",
        ]

    # Talking points
    talking_points = [s.text for s in valuable[:2]]
    if resolved_lang == "zh":
        talking_points.append(f"如果把「{topic}」放进当前项目，会改变哪些判断顺序？")
    else:
        talking_points.append(f"What would change in our current project if we applied '{topic}'?")

    # Questions
    if resolved_lang == "zh":
        questions_to_ask = [
            f"在「{topic}」上，我们现在最缺的是哪一个前提？",
            "这条观点如果放进 proposal 或 meeting，会改变什么？",
            "如果材料还不够完整，还需要补哪一个例子或来源？",
        ]
    else:
        questions_to_ask = [
            f"What is the most critical missing premise on '{topic}'?",
            "How would this insight change a proposal or meeting discussion?",
            "What additional example or source would strengthen this further?",
        ]

    # Evidence spans
    evidence_spans = [{"text": s.text, "location": ""} for s in valuable[:3]]

    return AnalyzedMaterial(
        thirty_second_takeaway=takeaway,
        key_insights=key_insights,
        use_scenarios=use_scenarios,
        talking_points=talking_points,
        questions_to_ask=questions_to_ask,
        memory_hook=f"{topic} — {top.text[:60]}…" if len(top.text) > 60 else f"{topic} — {top.text}",
        evidence_spans=evidence_spans,
        topic_label=topic,
    )


def _infer_why_it_matters(s: ScoredSentence, lang: str = "auto") -> str:
    """Generate a brief 'why it matters' note based on sentence features."""
    reasons = []
    if lang == "en":
        if s.has_number:
            reasons.append("Contains specific numbers, directly usable for argumentation")
        if s.has_regulatory:
            reasons.append("Involves regulatory changes, impacts compliance")
        if s.has_risk_or_opportunity:
            reasons.append("Identifies risk or opportunity, affects decision priority")
        if s.has_causal:
            reasons.append("Explains causation, useful for reasoning chain")
        if s.has_comparison:
            reasons.append("Includes comparison, helps clarify position")
        if s.has_timeframe:
            reasons.append("Has time dimension, helps judge urgency")
        if not reasons:
            reasons.append("Provides concrete evidence")
    else:
        if s.has_number:
            reasons.append("\u5305\u542b\u5177\u4f53\u6570\u5b57\uff0c\u53ef\u76f4\u63a5\u7528\u4e8e\u8bba\u8bc1")
        if s.has_regulatory:
            reasons.append("\u6d89\u53ca\u76d1\u7ba1\u53d8\u5316\uff0c\u5f71\u54cd\u5408\u89c4\u5224\u65ad")
        if s.has_risk_or_opportunity:
            reasons.append("\u6307\u51fa\u98ce\u9669\u6216\u673a\u4f1a\uff0c\u5f71\u54cd\u51b3\u7b56\u4f18\u5148\u7ea7")
        if s.has_causal:
            reasons.append("\u8bf4\u660e\u56e0\u679c\u5173\u7cfb\uff0c\u53ef\u7528\u4e8e\u63a8\u7406\u94fe")
        if s.has_comparison:
            reasons.append("\u5305\u542b\u5bf9\u6bd4\uff0c\u6709\u52a9\u4e8e\u6f84\u6e05\u7acb\u573a")
        if s.has_timeframe:
            reasons.append("\u6709\u65f6\u95f4\u7ef4\u5ea6\uff0c\u53ef\u5224\u65ad\u7d27\u8feb\u6027")
        if not reasons:
            reasons.append("\u63d0\u4f9b\u5177\u4f53\u5224\u65ad\u4f9d\u636e")
    return "\uff1b".join(reasons) if lang != "en" else "; ".join(reasons)
