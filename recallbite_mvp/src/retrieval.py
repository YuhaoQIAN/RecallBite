"""Retrieve the most relevant RecallBite cards for a current task.

Topic relevance and output intent are separated:
- Retrieval scores ONLY on thematic overlap.
- Output intent (proposal, meeting, CPD, etc.) is used later in activation.
"""

from __future__ import annotations

import re


# ── Domain and stopword data ──────────────────────────────────────────────

DOMAIN_KEYWORDS = [
    "AI governance", "AI治理", "accountability", "责任分配",
    "risk ownership", "模型风险", "climate risk", "气候风险",
    "ESG", "greenwashing", "披露", "监管",
    "proposal", "meeting", "客户会议", "manager discussion",
    "CPD", "internal sharing", "LinkedIn", "webinar",
    "transcript", "slide", "screenshot", "review", "report",
]

_STOPWORDS_EN = {
    "the", "and", "for", "are", "but", "not", "you", "all", "can", "had", "her", "was", "one", "our", "out",
    "day", "get", "has", "him", "his", "how", "its", "may", "new", "now", "old", "see", "two", "who", "boy",
    "did", "she", "use", "way", "many", "oil", "sit", "set", "run", "eat", "far", "sea", "eye", "ago",
    "off", "too", "any", "say", "man", "try", "ask", "end", "why", "let", "put",
    "own", "tell", "very", "when", "much", "would", "there", "their", "what", "said",
    "have", "each", "which", "will", "about", "could", "other", "after", "first", "never", "these", "think",
    "where", "being", "every", "great", "might", "shall", "still", "those", "while", "this", "that", "with",
    "from", "they", "know", "want", "been", "were", "time", "than", "them", "into", "just",
    "like", "over", "also", "back", "only", "then", "come", "here", "look", "make", "well", "work", "even",
    "more", "most", "some", "take", "year", "good", "life", "long", "part", "such", "down", "find", "give",
    "does", "made", "call", "came", "move", "both", "five", "once", "same", "must", "name", "left",
    "done", "open", "case", "show", "live", "play", "went", "told", "seen", "heard", "land", "home", "side",
    "hand", "high", "kind", "next", "word", "current", "need", "should", "using", "based", "under",
    "through", "during", "before", "above", "below", "between", "among", "within", "without",
}

_STOPWORDS_ZH = {
    "一个", "这个", "关于", "当前", "工作", "问题", "观点", "需要", "可以", "我们", "如何",
    "什么", "为什么", "怎么", "时候", "地方", "事情", "东西", "人员", "公司", "项目",
    "进行", "完成", "处理", "开展", "推进", "落实", "相关", "有关", "一定", "非常",
    "很多", "一些", "部分", "所有", "每个", "其他", "另外", "同时", "然后", "接着",
    "但是", "不过", "因此", "所以", "如果", "虽然", "尽管", "由于", "并且", "或者",
    "以及", "还有", "就是", "不是", "没有", "已经", "正在", "将要", "曾经", "总是",
}

_OUTPUT_INTENT_KEYWORDS = {
    "proposal": ["proposal", "opening", "report", "memo", "draft", "文案", "撰写", "报告"],
    "meeting": ["meeting", "manager", "client", "discussion", "会议", "讨论", "会谈", "沟通"],
    "cpd": ["cpd", "reflection", "development", "学习", "反思", "成长", "培训"],
    "sharing": ["sharing", "linkedin", "分享", "internal", "内部", "post", "发布"],
    "review": ["review", "复盘", "总结", "评估", "audit", "检查"],
}


# ── Public API ────────────────────────────────────────────────────────────


def retrieve_relevant_cards(
    current_task: str,
    cards: list[dict],
    top_k: int = 3,
) -> list[tuple[dict, int]]:
    """
    Retrieve cards ranked by thematic relevance only.

    Returns:
        list of (card, score) tuples. Score == 0 means no thematic match
        (caller may treat these as fallback results).
    """
    if not cards:
        return []

    parsed = _parse_task(current_task)
    topic_terms = _build_topic_terms(parsed["topic_query"])

    scored = []
    for card in cards:
        score = _calculate_topic_score(topic_terms, parsed["topic_query"], card)
        scored.append((card, score))

    scored.sort(key=lambda x: x[1], reverse=True)

    # If top score is 0, return most recent cards as fallback
    if scored[0][1] == 0:
        scored.sort(key=lambda x: x[0].get("created_at", ""), reverse=True)
        return scored[:top_k]

    return scored[:top_k]


def parse_task(current_task: str) -> dict:
    """Parse a free-form task into structured components."""
    return _parse_task(current_task)


# ── Task parsing ──────────────────────────────────────────────────────────


def _parse_task(current_task: str) -> dict:
    task_lower = current_task.lower().strip()
    return {
        "topic_query": _extract_topic_query(task_lower),
        "output_intent": _detect_output_intent(task_lower),
        "audience": _detect_audience(task_lower),
        "language": _detect_language(current_task),
        "desired_length": _detect_desired_length(task_lower),
        "raw": current_task,
    }


def _extract_topic_query(task_lower: str) -> str:
    """Strip output-intent words to isolate the topic query."""
    cleaned = task_lower
    for intent_keywords in _OUTPUT_INTENT_KEYWORDS.values():
        for kw in intent_keywords:
            cleaned = cleaned.replace(kw, " ")
    return " ".join(cleaned.split())


def _detect_output_intent(task_lower: str) -> str:
    for intent, keywords in _OUTPUT_INTENT_KEYWORDS.items():
        if any(kw in task_lower for kw in keywords):
            return intent
    return "general"


def _detect_audience(task_lower: str) -> str:
    if any(kw in task_lower for kw in ["partner", "client", "客户", "合伙人"]):
        return "client"
    if any(kw in task_lower for kw in ["manager", "上级", "主管", "经理"]):
        return "manager"
    if any(kw in task_lower for kw in ["internal", "team", "内部", "团队"]):
        return "internal"
    return "general"


def _detect_language(text: str) -> str:
    zh_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
    total = max(len(text), 1)
    en_words = len(re.findall(r"\b[a-zA-Z]{3,}\b", text.lower()))
    if zh_chars / total > 0.3:
        return "zh" if en_words < 3 else "bilingual"
    return "en"


def _detect_desired_length(task_lower: str) -> str:
    if any(kw in task_lower for kw in ["short", "brief", "一句话", "简短"]):
        return "short"
    if any(kw in task_lower for kw in ["long", "detailed", "详细", "完整"]):
        return "long"
    return "medium"


# ── Scoring internals ─────────────────────────────────────────────────────


def _build_topic_terms(topic_query: str) -> list[str]:
    terms: set[str] = set()

    # English words
    for word in re.findall(r"\b[a-zA-Z]{3,}\b", topic_query):
        w = word.lower()
        if w not in _STOPWORDS_EN:
            terms.add(w)

    # Chinese words (2-6 chars)
    for chunk in re.findall(r"[\u4e00-\u9fff]{2,6}", topic_query):
        if chunk not in _STOPWORDS_ZH:
            terms.add(chunk)
            # Substrings for richer matching on long chunks
            if len(chunk) >= 4:
                for size in range(2, min(5, len(chunk))):
                    for i in range(0, len(chunk) - size + 1):
                        sub = chunk[i:i + size]
                        if sub not in _STOPWORDS_ZH:
                            terms.add(sub)

    # Domain keywords that appear in query
    for kw in DOMAIN_KEYWORDS:
        if kw.lower() in topic_query:
            terms.add(kw.lower())

    return list(terms)


def _calculate_topic_score(topic_terms: list[str], topic_query: str, card: dict) -> int:
    """Score based only on thematic relevance."""
    score = 0
    searchable = _card_search_text(card)
    topic_query = topic_query.lower()

    # Topic tags exact match (+5 per tag, max 10)
    topic_tags = [t.lower() for t in card.get("topic_tags", [])]
    tag_hits = 0
    for tag in topic_tags:
        if tag in topic_query:
            score += 5
            tag_hits += 1
            if tag_hits >= 2:
                break

    # Core insight overlap (+4)
    core = card.get("core_insight", "").lower()
    if core and any(term in core for term in topic_terms if len(term) >= 3):
        score += 4

    # Knowledge seed / evidence overlap (+3 per hit, max 6)
    seed = card.get("knowledge_seed", "").lower()
    evidence_hits = 0
    for term in topic_terms:
        if len(term) < 3:
            continue
        if term in seed:
            score += 3
            evidence_hits += 1
            if evidence_hits >= 2:
                break

    # Domain keywords match (+2)
    if _match_domain_keywords(topic_query, searchable):
        score += 2

    # Rich-content bonus (+1) — only if there is already a topical match
    if score > 0 and card.get("card_type") == "Insight Pack":
        score += 1

    return score


def _match_domain_keywords(topic_query: str, card_text: str) -> bool:
    for kw in DOMAIN_KEYWORDS:
        kw_lower = kw.lower()
        if kw_lower in topic_query and kw_lower in card_text:
            return True
    return False


def _card_search_text(card: dict) -> str:
    parts: list[str] = []

    def _collect(value):
        if isinstance(value, dict):
            for item in value.values():
                _collect(item)
        elif isinstance(value, list):
            for item in value:
                _collect(item)
        elif value is not None:
            parts.append(str(value))

    _collect(card.get("knowledge_seed", ""))
    _collect(card.get("core_insight", ""))
    _collect(card.get("topic_tags", []))
    _collect(card.get("trigger_map", {}))
    _collect(card.get("use_cases", {}))
    _collect(card.get("copy_ready_lines", {}))
    _collect(card.get("insight_pack", {}))
    _collect(card.get("use_card", {}))
    _collect(card.get("clue_card", {}))

    return " ".join(parts).lower()
