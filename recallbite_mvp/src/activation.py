"""Turn a recalled card into copy-ready guidance for the current task.

Activation generates concrete, task-specific output — not template blobs.
It respects fog_index and avoids strong conclusions from thin evidence.
"""

from __future__ import annotations

import re


_OUTPUT_INTENT_KEYWORDS = {
    "proposal": ["proposal", "opening", "report", "memo", "draft", "文案", "撰写", "报告"],
    "meeting": ["meeting", "manager", "client", "discussion", "会议", "讨论", "会谈", "沟通"],
    "cpd": ["cpd", "reflection", "development", "学习", "反思", "成长", "培训"],
    "sharing": ["sharing", "linkedin", "分享", "internal", "内部", "post", "发布"],
    "review": ["review", "复盘", "总结", "评估", "audit", "检查"],
}


# ── Public API (backward-compatible) ──────────────────────────────────────


def generate_apply_suggestion(
    current_task: str,
    card: dict,
    score: int,
) -> dict:
    """
    Generate application suggestion for a single card.

    Returns dict with:
        why_relevant, how_to_use_now, copy_ready_paragraph,
        question_to_ask, confidence_note
    """
    task_lower = current_task.lower().strip()
    task_intent = _detect_output_intent(task_lower)
    topic_tags = card.get("topic_tags", [])
    topic = ", ".join(topic_tags[:2]) if topic_tags else _topic_from_card(card)
    fog_level = card.get("fog_index", {}).get("level", "Foggy")
    detail = _card_detail(card)
    core = card.get("core_insight", "")

    return {
        "why_relevant": _build_why_relevant(current_task, card, score, detail, topic),
        "how_to_use_now": _build_how_to_use(task_intent, topic, card, fog_level),
        "copy_ready_paragraph": _build_copy_ready(task_intent, topic, card, detail, fog_level),
        "question_to_ask": _build_question(task_intent, topic, card, detail),
        "confidence_note": _build_confidence_note(fog_level),
    }


# ── New-style activation (multi-card synthesis) ───────────────────────────


def generate_activation_output(
    current_task: str,
    cards: list[dict],
    output_intent: str = "",
    audience: str = "general",
    preferred_language: str = "zh",
) -> dict:
    """
    Generate activation output from multiple retrieved cards.

    Uses LLM when available, falling back to deterministic synthesis.
    """
    if not cards:
        return {
            "why_these_memories": "No relevant memories found for this task.",
            "ready_to_use_output": "",
            "questions_to_ask": [],
            "source_notes": [],
            "confidence_note": "No cards available. Try adding material on this topic first.",
        }

    if not output_intent:
        output_intent = _detect_output_intent(current_task.lower())

    # Try LLM first
    llm_error = ""
    try:
        from src.llm_client import create_llm_client
        client = create_llm_client()
        if "AI" in client.mode_label:
            task_dict = {
                "current_task": current_task,
                "output_intent": output_intent,
                "audience": audience,
                "language": preferred_language,
            }
            result = client.activate_memory(task_dict, cards, {})
            result["_analysis_meta"] = {"mode": "AI", "fallback": False, "reason": ""}
            return result
    except Exception as exc:
        llm_error = f"LLM failed: {type(exc).__name__}"

    # Fallback to deterministic synthesis
    primary_cards = [item["card"] for item in cards]
    topic = _synthesize_topic(primary_cards)

    return {
        "why_these_memories": _build_why_multi(cards, topic),
        "ready_to_use_output": _build_ready_multi(output_intent, topic, primary_cards, preferred_language),
        "questions_to_ask": _build_questions_multi(output_intent, topic, primary_cards),
        "source_notes": _build_source_notes(primary_cards),
        "confidence_note": _build_confidence_multi(primary_cards),
        "_analysis_meta": {"mode": "AI" if llm_error else "deterministic", "fallback": bool(llm_error), "reason": llm_error},
    }


# ── Backward-compatible builders ──────────────────────────────────────────


def _build_why_relevant(current_task: str, card: dict, score: int, detail: dict, topic: str) -> str:
    current_task_lower = current_task.lower().strip()
    topic_tags = card.get("topic_tags", [])
    keywords = card.get("trigger_map", {}).get("keywords", [])
    scenarios = card.get("trigger_map", {}).get("scenarios", [])
    matched = _collect_matches(current_task_lower, topic_tags, keywords, scenarios, detail)

    if matched:
        elements = "、".join(matched[:3])
        anchor = detail.get("anchor") or card.get("core_insight", "核心观点")
        return f"当前任务和这张卡在 {elements} 上对上了。卡片里的 {anchor} 可以直接接到你现在要做的事上。"

    return f"这张卡和当前任务没有明显的关键词重叠，但它仍可能为你现在的工作提供一个更具体的视角（score={score}）。"


def _build_how_to_use(task_intent: str, topic: str, card: dict, fog_level: str) -> str:
    if fog_level == "Very Foggy":
        return f"这条关于 {topic} 的线索信息不足，建议先补上下文再使用。"

    if task_intent == "proposal":
        return f"把 {topic} 压成一段 opening 或 core argument，用来说明为什么这个 proposal 值得推进。"
    if task_intent == "meeting":
        return f"改成一个 meeting talking point：先说 {topic} 的判断，再接一个要确认的前提或风险。"
    if task_intent == "cpd":
        return f"整理成 CPD reflection：这条关于 {topic} 的判断让我在实际工作里改变了什么。"
    if task_intent == "sharing":
        return f"做成 internal sharing 的一段具体说明，重点放在 {topic} 如何落到实际工作。"
    return f"把这条关于 {topic} 的观点放进当前任务里，作为更具体的判断依据，而不是只做概念说明。"


def _build_copy_ready(task_intent: str, topic: str, card: dict, detail: dict, fog_level: str) -> str:
    content = detail.get("copy_line") or _extract_card_content(card)
    if not content:
        content = card.get("core_insight", "")

    if fog_level == "Very Foggy":
        return f"关于 {topic} 的线索还太少，建议先补上下文再把它写进正式材料。当前可先记住：{content}"

    if fog_level == "Foggy":
        return f"围绕 {topic}，可以先用这句：{content}。正式引用前最好再核对一条来源或例子。"

    # Clear + task-specific
    if task_intent == "proposal":
        return f"{content} 在 {topic} 上，这条判断可以直接作为 proposal 的切入锚点。"
    if task_intent == "meeting":
        return f"{content} 讨论 {topic} 时，先抛出这条观察，然后接一个需要确认的前提。"
    if task_intent == "cpd":
        return f"{content} 这条关于 {topic} 的判断让我在后续工作中有了一个可复用的参考点。"
    if task_intent == "sharing":
        return f"{content} 关于 {topic} 的一个值得分享的点：重点放在它如何影响实际决策。"

    return f"{content} 放进当前任务时，可以直接把 {topic} 作为切口，把观点接到你要写的内容里。"


def _build_question(task_intent: str, topic: str, card: dict, detail: dict) -> str:
    q = detail.get("question") or ""
    crl = card.get("copy_ready_lines", {})
    mq = crl.get("meeting_question")
    if mq:
        return mq
    if q:
        return q

    if task_intent == "proposal":
        return f"在 {topic} 上，我们还缺哪一个前提，才能把这条观点写进 proposal opening？"
    if task_intent == "meeting":
        return f"如果把 {topic} 放进这次 meeting，我们最该先确认什么？"
    if task_intent == "cpd":
        return f"这条关于 {topic} 的判断，下一次遇到类似场景时应该怎样复用？"
    return f"这条关于 {topic} 的观点，放到当前任务里最合适的用法是什么？"


def _build_confidence_note(fog_level: str) -> str:
    if fog_level == "Clear":
        return "这张卡片基于较完整的输入，但正式引用前仍建议验证。"
    if fog_level == "Foggy":
        return "这张卡片来自部分输入。在正式交付物中使用前请确认上下文。"
    return "这张卡片来自非常有限的输入。请验证来源并补充上下文后再正式使用。"


# ── Multi-card synthesis builders ─────────────────────────────────────────


def _build_why_multi(cards: list[dict], topic: str) -> str:
    strong = [c for c in cards if c.get("match_strength") == "strong"]
    weak = [c for c in cards if c.get("match_strength") == "weak"]
    fallback = [c for c in cards if c.get("match_strength") == "fallback"]

    if strong:
        return f"找到 {len(strong)} 条关于「{topic}」的强匹配。这些卡片包含直接相关的证据和措辞。"
    if weak:
        return f"找到关于「{topic}」的弱匹配。有一定上下文重叠，但建议验证。"
    if fallback:
        return f"没有找到「{topic}」的直接匹配。显示最近创建的卡片作为参考。"
    return "没有找到相关记忆。"


def _build_ready_multi(intent: str, topic: str, cards: list[dict], language: str) -> str:
    if not cards:
        return ""

    # Extract core content from each card, deduplicate by content similarity
    contents: list[str] = []
    seen: set[str] = set()
    for card in cards:
        text = _extract_card_content(card) or card.get("core_insight", "")
        if not text:
            continue
        key = text.lower().strip()[:60]
        if key not in seen:
            seen.add(key)
            contents.append(text)
        if len(contents) >= 3:
            break

    if not contents:
        return ""

    # Build synthesized paragraph
    if len(contents) == 1:
        content = contents[0]
    else:
        # Synthesize multiple cards into one flowing paragraph
        if language == "zh":
            connectors = ["首先，", "此外，", "同时，"]
        else:
            connectors = ["First, ", "Additionally, ", "Also, "]
        parts = []
        for idx, c in enumerate(contents):
            prefix = connectors[idx] if idx < len(connectors) else ""
            parts.append(f"{prefix}{c}")
        if language == "zh":
            content = "".join(parts) + f" 这些判断共同构成了 {topic} 的切入点。"
        else:
            content = " ".join(parts) + f" Together, these form a strong opening for {topic}."

    primary = cards[0]
    fog = primary.get("fog_index", {}).get("level", "Foggy")

    if fog == "Very Foggy":
        if language == "zh":
            return f"关于 {topic} 的线索还太少，建议先补上下文。当前记录：{content}"
        return f"Not enough verified content on {topic}. Current note: {content}"

    if intent == "proposal":
        tmpl = "在 {topic} 上，可直接用以下判断作为 proposal 的切入点：{content}"
        if language != "zh":
            tmpl = "For your proposal on {topic}, use this as the opening anchor: {content}"
    elif intent == "meeting":
        tmpl = "讨论 {topic} 时，可以先抛出这些观察：{content}"
        if language != "zh":
            tmpl = "In your meeting on {topic}, start with these observations: {content}"
    elif intent == "cpd":
        tmpl = "这条关于 {topic} 的材料让我意识到：{content}"
        if language != "zh":
            tmpl = "This material on {topic} highlighted: {content}"
    elif intent == "sharing":
        tmpl = "关于 {topic} 的一个值得分享的点：{content}"
        if language != "zh":
            tmpl = "A shareable point on {topic}: {content}"
    elif intent == "review":
        tmpl = "回顾 {topic} 时，这些判断值得保留：{content}"
        if language != "zh":
            tmpl = "Reviewing {topic}: {content}"
    else:
        tmpl = "关于 {topic}：{content}"
        if language != "zh":
            tmpl = "On {topic}: {content}"

    return tmpl.format(topic=topic, content=content)


def _build_questions_multi(intent: str, topic: str, cards: list[dict]) -> list[str]:
    questions: list[str] = []
    for card in cards:
        crl = card.get("copy_ready_lines", {})
        mq = crl.get("meeting_question")
        if mq and mq not in questions:
            questions.append(mq)
        ip = card.get("insight_pack", {})
        for q in ip.get("questions_to_ask", []):
            if q and q not in questions:
                questions.append(q)
                if len(questions) >= 3:
                    break
        if len(questions) >= 3:
            break

    if len(questions) < 2:
        if intent == "proposal":
            questions.append(f"在{topic}上，支持这个观点的最强证据是什么？")
        elif intent == "meeting":
            questions.append(f"在决定之前，关于{topic}我们需要确认什么？")
        elif intent == "cpd":
            questions.append(f"这条关于{topic}的洞察会如何改变我的下一步行动？")
        else:
            questions.append(f"这条关于{topic}的洞察最直接的应用是什么？")

    return questions[:3]


def _build_source_notes(cards: list[dict]) -> list[str]:
    notes: list[str] = []
    for card in cards:
        sg = card.get("source_grounding", {})
        source = card.get("source", "") or sg.get("source_reference", "")
        title = sg.get("source_title", "")
        kind = sg.get("source_kind", "")
        verifiable = sg.get("is_verifiable", False)
        if source or title:
            note = f"{title or 'Untitled'} ({kind})" if title else f"\u6765\u6e90: {source}"
            if not verifiable:
                note += " \u2014 \u672a\u9a8c\u8bc1"
            notes.append(note)
    return notes


def _build_confidence_multi(cards: list[dict]) -> str:
    levels = [c.get("fog_index", {}).get("level", "Foggy") for c in cards]
    if all(l == "Clear" for l in levels):
        return "所有卡片基于较完整的输入。正式引用前仍建议验证。"
    if any(l == "Very Foggy" for l in levels):
        return "部分卡片来自有限输入。在正式交付物中使用前请验证来源。"
    return "卡片基于部分输入。正式使用前请确认上下文。"


# ── Shared helpers ────────────────────────────────────────────────────────


def _detect_output_intent(task_lower: str) -> str:
    for intent, keywords in _OUTPUT_INTENT_KEYWORDS.items():
        if any(kw in task_lower for kw in keywords):
            return intent
    return "general"


def _topic_from_card(card: dict) -> str:
    tags = card.get("topic_tags", [])
    if tags:
        return ", ".join(tags[:2])
    seed = card.get("knowledge_seed", "")
    return seed[:24] if seed else "this topic"


def _card_detail(card: dict) -> dict:
    card_type = card.get("card_type", "Use Card")
    if card_type == "Insight Pack":
        ip = card.get("insight_pack", {})
        return {
            "anchor": ip.get("thirty_second_takeaway") or card.get("core_insight", ""),
            "copy_line": ip.get("copy_ready_paragraph") or ip.get("key_insights", [""])[0],
            "question": ip.get("questions_to_ask", [""])[0] if ip.get("questions_to_ask") else "",
        }
    if card_type == "Use Card":
        uc = card.get("use_card", {})
        return {
            "anchor": uc.get("what_it_means") or card.get("core_insight", ""),
            "copy_line": uc.get("how_to_say_it") or uc.get("what_it_means", ""),
            "question": uc.get("what_to_ask", ""),
        }
    cc = card.get("clue_card", {})
    return {
        "anchor": cc.get("possible_direction") or card.get("core_insight", ""),
        "copy_line": cc.get("possible_direction") or card.get("core_insight", ""),
        "question": cc.get("what_to_add_next", ""),
    }


def _extract_card_content(card: dict) -> str:
    ct = card.get("card_type", "Use Card")
    if ct == "Insight Pack":
        ip = card.get("insight_pack", {})
        return ip.get("thirty_second_takeaway") or ip.get("copy_ready_paragraph") or ""
    if ct == "Use Card":
        uc = card.get("use_card", {})
        return uc.get("what_it_means") or uc.get("how_to_say_it") or ""
    cc = card.get("clue_card", {})
    return cc.get("possible_direction") or ""


def _synthesize_topic(cards: list[dict]) -> str:
    tags: set[str] = set()
    for card in cards:
        for tag in card.get("topic_tags", []):
            tags.add(tag.lower())
    if tags:
        return ", ".join(sorted(tags)[:3])
    seeds = " ".join(c.get("knowledge_seed", "") for c in cards)
    words = re.findall(r"\b[a-zA-Z]{4,}\b", seeds.lower())
    if words:
        from collections import Counter
        top = Counter(words).most_common(2)
        return ", ".join(w for w, _ in top)
    return "this topic"


def _collect_matches(current_task_lower: str, topic_tags: list[str], keywords: list[str], scenarios: list[str], detail: dict) -> list[str]:
    matches: list[str] = []
    for tag in topic_tags:
        if tag.lower() in current_task_lower:
            matches.append(f"tag '{tag}'")
    for keyword in keywords:
        if keyword.lower() in current_task_lower:
            matches.append(f"keyword '{keyword}'")
    for scenario in scenarios:
        if scenario.lower() in current_task_lower:
            matches.append(f"scenario '{scenario}'")
    anchor = detail.get("anchor", "").lower()
    if anchor and any(token in anchor for token in re.findall(r"\b[a-zA-Z]{3,}\b", current_task_lower)):
        matches.append("card wording")
    return matches
