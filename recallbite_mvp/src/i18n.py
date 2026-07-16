"""RecallBite internationalization (i18n) module.

Provides centralized translation support for UI text.
All UI strings should use t("key") instead of hardcoded text.
"""

from __future__ import annotations


# ── Chinese translations ────────────────────────────────────────────────

ZH_CN = {
    # Hero
    "hero.title": "RecallBite 记忆面包",
    "hero.subtitle": "让知识不只被保存，而是在需要时真正派上用场。",
    "hero.slogan": "存进去 · 问得到 · 看得懂 · 用得上",

    # Navigation
    "nav.add_knowledge": "📥 添加知识",
    "nav.ask": "❓ 向知识库提问",
    "nav.memory": "🧠 记忆与洞察",
    "nav.activate": "⚡ 激活知识",

    # Add Knowledge
    "add.title": "放入你的材料",
    "add.subtitle": "选择输入方式。输入越完整，输出越深入；输入越少，系统会更保守。",
    "add.paste_text": "📝 粘贴文本",
    "add.upload_file": "📎 上传文件",
    "add.public_url": "🌐 公开链接",
    "add.material_placeholder": "在此粘贴任何内容 — 文章、转录、会议笔记、幻灯片文字、链接/标题或一个粗略想法。",
    "add.url_placeholder": "https://example.com/article",
    "add.input_type": "材料类型",
    "add.auto_detect": "自动检测",
    "add.article": "文章 / 简报",
    "add.transcript": "转录 / 会议记录",
    "add.webcast": "网络直播 / 讲座笔记",
    "add.slide": "幻灯片 / 截图文字",
    "add.link": "链接 / 标题",
    "add.thought": "一条想法 / 粗略思路",
    "add.optional_details": "可选详情",
    "add.source": "来源",
    "add.source_placeholder": "AI 治理网络研讨会 / LinkedIn 文章 / 会议笔记",
    "add.tags": "主题标签",
    "add.tags_placeholder": "AI 治理、问责制、风险管理",
    "add.intended_use": "预期用途",
    "add.intended_use_placeholder": "提案开场 / 会议发言要点 / CPD 反思",
    "add.output_language": "输出语言",
    "add.lang_auto": "自动",
    "add.lang_zh": "中文",
    "add.lang_en": "English",
    "add.lang_bilingual": "双语",
    "add.submit": "生成知识面包卡",
    "add.error_empty": "请先粘贴、上传或输入 URL。",
    "add.success_saved": "已保存为",
    "add.quick_bite": "快速预览",
    "add.quick_bite_sub": "已添加到本地知识库。洞察已生成。",
    "add.parsed_pages": "已解析 {n}",
    "add.detected_lang": "检测到语言：{lang}",
    "add.processing_error": "无法处理材料：",

    # Quick Bite sections
    "qb.takeaway": "核心要点",
    "qb.key_insights": "关键洞察",
    "qb.what_it_means": "这意味着",
    "qb.how_to_say_it": "可以这样说",
    "qb.possible_direction": "可能的方向",
    "qb.what_is_missing": "缺少什么",
    "qb.use_scenarios": "查看使用场景",
    "qb.talking_points": "查看问题与发言要点",
    "qb.copy_ready": "查看可用文案",
    "qb.source_evidence": "查看来源与证据",
    "qb.trigger_map": "在做这些事时记得召回…",
    "qb.advanced_meta": "高级元数据",

    # CTA buttons
    "cta.ask_source": "询问此来源",
    "cta.activate_task": "用于任务激活",
    "cta.add_another": "添加另一来源",

    # Right panel
    "add.what_this_does": "这是做什么的",
    "add.what_this_does_desc": "RecallBite 不是总结工具。它将粗略材料转化为未来可用的卡片，然后在需要时帮你取回。",
    "add.clear_desc": "清晰 = 足够上下文用于特定场景。模糊 = 有用但需提示。非常模糊 = 只有线索，不是结论。",
    "add.input_examples": "输入示例",
    "add.guardrails": "产品边界",
    "add.guardrails_desc": "无需登录、无需云同步、无 Teams/Zoom/Outlook 集成、不上传敏感数据、无密集表单 UI。",

    # Ask
    "ask.title": "向知识库提问",
    "ask.subtitle": "搜索已保存材料，获取带引用的证据回答。",
    "ask.question": "你的问题",
    "ask.question_placeholder": "关于 AI 问责制，我知道了什么？",
    "ask.scope": "搜索范围",
    "ask.scope_all": "全部知识",
    "ask.search_btn": "搜索知识库",
    "ask.error_empty": "请输入问题。",
    "ask.no_results": "未找到相关段落。请先添加此主题的材料。",
    "ask.grounded_answer": "基于证据的回答",
    "ask.evidence_limited": "证据有限 — 建议添加更多相关材料。",
    "ask.view_evidence": "查看 {n} 条证据段落",
    "ask.insufficient": "证据不足以生成回答。",
    "ask.based_on_one": "基于一条来源段落：",
    "ask.key_points": "来自知识库的要点：",
    "ask.synthesis": "综合分析：",
    "ask.themes": "检索到的段落涉及以下主题：",
    "ask.passage_count": "基于 {n} 条段落",
    "ask.mode_label": "模式",

    # Memory & Insights
    "memory.title": "记忆卡片",
    "memory.subtitle": "卡片集合，不是表格。按关键词、标签、触发短语或知识种子搜索。",
    "memory.search_placeholder": "按关键词、标签、场景或核心洞察搜索…",
    "memory.edit_card": "编辑卡片",
    "memory.core_insight": "核心洞察",
    "memory.topic_tags": "主题标签（逗号分隔）",
    "memory.source": "来源",
    "memory.save_changes": "保存更改",
    "memory.updated": "卡片已更新。",
    "memory.delete_confirm": "删除卡片",
    "memory.deleted": "卡片已删除。",
    "memory.no_cards": "暂无记忆卡片。使用「添加知识」创建第一张。",
    "memory.no_match": "没有匹配的卡片。",
    "memory.total": "共",
    "memory.search": "搜索",

    # Activate
    "activate.title": "激活知识",
    "activate.subtitle": "将相关知识转化为当前任务可用内容。",
    "activate.task": "当前任务",
    "activate.task_placeholder": "例如：我需要写一份关于 AI 治理的提案…",
    "activate.audience": "受众",
    "activate.audience_placeholder": "客户 / 经理 / 团队",
    "activate.output_format": "输出格式",
    "activate.format_proposal": "提案开场",
    "activate.format_meeting": "会议发言要点",
    "activate.format_cpd": "CPD 反思",
    "activate.format_sharing": "内部分享",
    "activate.activate_btn": "激活相关知识",
    "activate.error_empty": "请描述你当前的任务。",
    "activate.no_cards": "暂无可用记忆卡片。请先添加知识。",
    "activate.no_match": "未找到与当前任务相关的知识卡片。",
    "activate.need_more_info": "需要更多信息",
    "activate.clarify_topic": "请补充任务主题或粘贴相关背景，以便系统召回到相关知识。",
    "activate.related_topics": "知识库中的可用主题：",
    "activate.no_topic": "系统无法识别任务主题。请选择或描述具体方向。",
    "activate.knowledge_brief": "知识激活简报",
    "activate.current_task_label": "当前任务：",
    "activate.ready_output": "可用输出",
    "activate.fallback_mode": "回退模式：",
    "activate.analysis_mode": "分析模式：",
    "activate.questions_to_ask": "可以问的问题",
    "activate.source_notes": "来源说明",
    "activate.individual_cards": "各来源卡片",
    "activate.no_results": "暂无相关知识卡片。",
    "activate.hint_label": "可选提示",
    "activate.hint_placeholder": "例如：之前某次讲座提到 AI 治理不只是模型准确率。",
    "activate.save_hint": "将此提示保存为新记忆卡片",
    "activate.hint_saved": "已将提示保存为新记忆卡片。",
    "activate.hint_failed": "无法保存提示：",
    "activate.memory_hint": "记忆提示",

    # Settings
    "settings.interface_lang": "界面语言",
    "settings.output_lang": "输出语言",
    "settings.appearance": "外观",
    "settings.follow_interface": "跟随界面",
    "settings.follow_source": "跟随来源",
    "settings.system": "跟随系统",
    "settings.light": "浅色",
    "settings.dark": "深色",
    "settings.title": "设置",

    # Fog Index
    "fog.clear": "清晰",
    "fog.foggy": "模糊",
    "fog.very_foggy": "非常模糊",

    # Privacy / Mode
    "mode.external_ai": "外部 AI 模式",
    "mode.external_notice": "外部 AI 模式 — 材料会发送至配置的提供商。请勿上传机密或客户敏感内容。",
    "mode.local": "本地处理模式",
    "mode.local_notice": "本地处理模式 — 你的材料保留在本设备上。",
    "mode.demo": "演示回退模式（确定性规则）",

    # Common
    "common.source": "来源",
    "common.relevance": "相关度",
    "common.citation": "引用",

    # Memory card fields
    "mc.core_insight": "核心洞察",
    "mc.30s_takeaway": "30秒带走",
    "mc.key_insights": "关键洞察",
    "mc.use_scenarios": "使用场景",
    "mc.talking_points": "发言要点",
    "mc.questions_to_ask": "可以问的问题",
    "mc.what_it_means": "这意味着",
    "mc.where_to_use": "在哪里用",
    "mc.how_to_say_it": "可以这样说",
    "mc.what_to_ask": "应该问什么",
    "mc.possible_direction": "可能的方向",
    "mc.what_is_missing": "缺少什么",
    "mc.what_to_add_next": "下一步补什么",
    "mc.fog_note": "模糊度说明",
    "mc.copy_ready": "可用文案",
    "mc.meeting_question": "会议问题",
    "mc.recall_trigger": "在做这些事时记得召回…",
    "mc.source": "来源",

    # Quick bite extra
    "qb.source_label": "来源",
    "qb.mode_prefix": "模式",

    # Activation card fields
    "ac.why_relevant": "为什么与当前任务相关",
    "ac.how_to_apply": "现在怎么用",
    "ac.ready_wording": "可用措辞",
    "ac.better_question": "更好的问题",
    "ac.future_trigger": "未来触发",
    "ac.relevance": "相关度",

    # Advanced meta
    "meta.fog_index": "模糊度指数",
    "meta.evidence_quality": "证据质量",
    "meta.tags": "标签",
    "meta.created": "创建时间",
    "meta.document_id": "文档 ID",

    # Footer & misc
    "footer.tagline": "RecallBite — 今天存一条，明天用得上。",
    "add.input_examples_hint": "AI 治理 / 问责制 / 风险 / 合规",

    # Ask tab extras
    "ask.mode_deterministic": "确定性规则",
    "ask.mode_ai": "AI 辅助",
    "ask.evidence_label": "查看原文证据",

    # Activation extras
    "activate.synthesis_label": "综合分析",

    # URL / misc errors
    "add.url_invalid": "URL 必须以 http:// 或 https:// 开头",
    "add.missing_dep": "缺少依赖",
    "add.fallback_reason": "回退原因",
    "add.mode_label": "模式",

    # Theme options
    "theme.system": "跟随系统",
    "theme.light": "浅色",
    "theme.dark": "深色",

    # URL title
    "add.url_title": "标题",
}


# ── English translations ────────────────────────────────────────────────

EN = {
    # Hero
    "hero.title": "RecallBite",
    "hero.subtitle": "Knowledge that works when you need it.",
    "hero.slogan": "Save · Ask · Understand · Use",

    # Navigation
    "nav.add_knowledge": "📥 Add Knowledge",
    "nav.ask": "❓ Ask My Knowledge",
    "nav.memory": "🧠 Memory & Insights",
    "nav.activate": "⚡ Activate",

    # Add Knowledge
    "add.title": "Drop what you have",
    "add.subtitle": "Choose how to bring material in. The more complete the input, the deeper the output.",
    "add.paste_text": "📝 Paste Text",
    "add.upload_file": "📎 Upload File",
    "add.public_url": "🌐 Public URL",
    "add.material_placeholder": "Paste anything here — article, transcript, meeting notes, slide text, link/title, or one rough thought.",
    "add.url_placeholder": "https://example.com/article",
    "add.input_type": "Input Type",
    "add.auto_detect": "Auto-detect",
    "add.article": "Article / Newsletter",
    "add.transcript": "Transcript / Meeting Script",
    "add.webcast": "Webcast / Lecture Notes",
    "add.slide": "Slide / Screenshot Text",
    "add.link": "Link / Title",
    "add.thought": "One Thought / Rough Idea",
    "add.optional_details": "Optional details",
    "add.source": "Source",
    "add.source_placeholder": "AI governance webcast / LinkedIn article / meeting note",
    "add.tags": "Topic tags",
    "add.tags_placeholder": "AI governance, accountability, risk management",
    "add.intended_use": "Intended use",
    "add.intended_use_placeholder": "Proposal opening / meeting talking point / CPD reflection",
    "add.output_language": "Output language",
    "add.lang_auto": "Auto",
    "add.lang_zh": "中文",
    "add.lang_en": "English",
    "add.lang_bilingual": "Bilingual",
    "add.submit": "Generate Knowledge Card",
    "add.error_empty": "Please paste, upload, or provide a URL first.",
    "add.success_saved": "Saved as",
    "add.quick_bite": "Quick Bite",
    "add.quick_bite_sub": "Added to your local knowledge base. Insight generated.",
    "add.parsed_pages": "Parsed {n}",
    "add.detected_lang": "Detected language: {lang}",
    "add.processing_error": "Unable to process material:",

    # Quick Bite sections
    "qb.takeaway": "Takeaway",
    "qb.key_insights": "Key insights",
    "qb.what_it_means": "What it means",
    "qb.how_to_say_it": "How to say it",
    "qb.possible_direction": "Possible direction",
    "qb.what_is_missing": "What is missing",
    "qb.use_scenarios": "View use scenarios",
    "qb.talking_points": "View questions and talking points",
    "qb.copy_ready": "View copy-ready wording",
    "qb.source_evidence": "View source and evidence",
    "qb.trigger_map": "Recall this when working on...",
    "qb.advanced_meta": "Advanced metadata",

    # CTA buttons
    "cta.ask_source": "Ask this source",
    "cta.activate_task": "Activate for a task",
    "cta.add_another": "Add another source",

    # Right panel
    "add.what_this_does": "What this does",
    "add.what_this_does_desc": "RecallBite is not a summary tool. It turns rough materials into future-use cards, then helps you pull those cards back into current work.",
    "add.clear_desc": "Clear = enough context for specific use. Foggy = useful but needs a caveat. Very Foggy = only a clue, not a conclusion.",
    "add.input_examples": "Input examples",
    "add.guardrails": "Product guardrails",
    "add.guardrails_desc": "No login, no cloud sync, no Teams/Zoom/Outlook integration, no sensitive data upload, no dense form UI.",

    # Ask
    "ask.title": "Ask My Knowledge",
    "ask.subtitle": "Search saved materials for evidence-based answers with citations.",
    "ask.question": "Your question",
    "ask.question_placeholder": "What do I know about AI accountability?",
    "ask.scope": "Search scope",
    "ask.scope_all": "All knowledge",
    "ask.search_btn": "Search knowledge base",
    "ask.error_empty": "Please enter a question.",
    "ask.no_results": "No relevant passages found. Try adding material on this topic first.",
    "ask.grounded_answer": "Grounded answer",
    "ask.evidence_limited": "Evidence is limited — consider adding more materials on this topic.",
    "ask.view_evidence": "View {n} evidence passage(s)",
    "ask.insufficient": "Insufficient evidence to generate an answer.",
    "ask.based_on_one": "Based on one source passage:",
    "ask.key_points": "Key points from your knowledge base:",
    "ask.synthesis": "Synthesis:",
    "ask.themes": "The retrieved passages suggest themes around:",
    "ask.passage_count": "Based on {n} passage(s)",
    "ask.mode_label": "Mode",

    # Memory & Insights
    "memory.title": "Memory Cards",
    "memory.subtitle": "Card collection, not a table. Search by keywords, tags, trigger phrases, or the actual knowledge seed.",
    "memory.search_placeholder": "Search by keyword, tag, scenario, or core insight...",
    "memory.edit_card": "Edit card",
    "memory.core_insight": "Core insight",
    "memory.topic_tags": "Topic tags (comma-separated)",
    "memory.source": "Source",
    "memory.save_changes": "Save changes",
    "memory.updated": "Card updated.",
    "memory.delete_confirm": "Delete card",
    "memory.deleted": "Card deleted.",
    "memory.no_cards": "No memory cards yet. Use Add Knowledge to create your first card.",
    "memory.no_match": "No cards match your search.",
    "memory.total": "Total",
    "memory.search": "Search",

    # Activate
    "activate.title": "Activate Memory",
    "activate.subtitle": "Turn relevant knowledge into usable content for your current task.",
    "activate.task": "Current task",
    "activate.task_placeholder": "I need to write a proposal about AI governance...",
    "activate.audience": "Audience",
    "activate.audience_placeholder": "Client / Manager / Team",
    "activate.output_format": "Output format",
    "activate.format_proposal": "Proposal opening",
    "activate.format_meeting": "Meeting talking points",
    "activate.format_cpd": "CPD reflection",
    "activate.format_sharing": "Internal sharing",
    "activate.activate_btn": "Activate relevant memories",
    "activate.error_empty": "Please describe your current task.",
    "activate.no_cards": "No memory cards available. Add knowledge first.",
    "activate.no_match": "No knowledge cards match your current task.",
    "activate.need_more_info": "Need more information",
    "activate.clarify_topic": "Please add a task topic or paste relevant context so the system can retrieve matching knowledge.",
    "activate.related_topics": "Related topics in your knowledge base:",
    "activate.no_topic": "The system cannot identify the task topic. Please select or describe a specific direction.",
    "activate.knowledge_brief": "Knowledge activation brief",
    "activate.current_task_label": "Current task: ",
    "activate.ready_output": "Ready-to-use output",
    "activate.fallback_mode": "Fallback mode: ",
    "activate.analysis_mode": "Analysis mode: ",
    "activate.questions_to_ask": "Questions to ask",
    "activate.source_notes": "Source notes",
    "activate.individual_cards": "Individual source cards",
    "activate.no_results": "No relevant cards available yet.",
    "activate.hint_label": "Optional hint",
    "activate.hint_placeholder": "e.g., Previously a lecture mentioned AI governance is not just model accuracy.",
    "activate.save_hint": "Save this hint as a new Memory Card",
    "activate.hint_saved": "Saved your hint as a new memory card.",
    "activate.hint_failed": "Could not save the hint: ",
    "activate.memory_hint": "Memory hint",

    # Settings
    "settings.interface_lang": "Interface Language",
    "settings.output_lang": "Output Language",
    "settings.appearance": "Appearance",
    "settings.follow_interface": "Follow interface",
    "settings.follow_source": "Follow source",
    "settings.system": "System",
    "settings.light": "Light",
    "settings.dark": "Dark",
    "settings.title": "Settings",

    # Fog Index
    "fog.clear": "Clear",
    "fog.foggy": "Foggy",
    "fog.very_foggy": "Very Foggy",

    # Privacy / Mode
    "mode.external_ai": "External AI mode",
    "mode.external_notice": "External AI mode — material is sent to the configured provider. Do not upload confidential or client-sensitive content.",
    "mode.local": "Local processing mode",
    "mode.local_notice": "Local processing mode — your material stays on this device.",
    "mode.demo": "Demo fallback mode (deterministic rules)",

    # Common
    "common.source": "Source",
    "common.relevance": "Relevance",
    "common.citation": "Citation",

    # Memory card fields
    "mc.core_insight": "Core insight",
    "mc.30s_takeaway": "30-second takeaway",
    "mc.key_insights": "Key insights",
    "mc.use_scenarios": "Use scenarios",
    "mc.talking_points": "Talking points",
    "mc.questions_to_ask": "Questions to ask",
    "mc.what_it_means": "What it means",
    "mc.where_to_use": "Where to use",
    "mc.how_to_say_it": "How to say it",
    "mc.what_to_ask": "What to ask",
    "mc.possible_direction": "Possible direction",
    "mc.what_is_missing": "What is missing",
    "mc.what_to_add_next": "What to add next",
    "mc.fog_note": "Fog note",
    "mc.copy_ready": "Copy-ready lines",
    "mc.meeting_question": "Meeting question",
    "mc.recall_trigger": "Recall this when working on...",
    "mc.source": "Source",

    # Quick bite extra
    "qb.source_label": "Source",
    "qb.mode_prefix": "Mode",

    # Activation card fields
    "ac.why_relevant": "Why it matters now",
    "ac.how_to_apply": "How to apply it",
    "ac.ready_wording": "Ready-to-use wording",
    "ac.better_question": "Better question to ask",
    "ac.future_trigger": "Future trigger",
    "ac.relevance": "Relevance",

    # Advanced meta
    "meta.fog_index": "Fog Index",
    "meta.evidence_quality": "Evidence quality",
    "meta.tags": "Tags",
    "meta.created": "Created",
    "meta.document_id": "Document ID",

    # Footer & misc
    "footer.tagline": "RecallBite — Capture a thought today. Use it when it matters tomorrow.",
    "add.input_examples_hint": "AI governance / accountability / risk / compliance",

    # Ask tab extras
    "ask.mode_deterministic": "Deterministic rules",
    "ask.mode_ai": "AI-assisted",
    "ask.evidence_label": "View source evidence",

    # Activation extras
    "activate.synthesis_label": "Synthesis",

    # URL / misc errors
    "add.url_invalid": "URL must start with http:// or https://",
    "add.missing_dep": "Missing dependency",
    "add.fallback_reason": "Fallback reason",
    "add.mode_label": "Mode",

    # Theme options
    "theme.system": "System",
    "theme.light": "Light",
    "theme.dark": "Dark",

    # URL title
    "add.url_title": "Title",
}


# ── Locale registry ──────────────────────────────────────────────────────

_LOCALES: dict[str, dict[str, str]] = {
    "zh-CN": ZH_CN,
    "en": EN,
}

_current_locale: str = "zh-CN"


def set_locale(locale: str) -> None:
    """Set the current interface language."""
    global _current_locale
    if locale in _LOCALES:
        _current_locale = locale


def get_locale() -> str:
    """Get the current interface language."""
    return _current_locale


def t(key: str, **kwargs) -> str:
    """Translate a key using the current locale.
    
    Falls back to English if key not found in current locale.
    Falls back to the key itself if not found in any locale.
    Supports {variable} interpolation via kwargs.
    
    Example:
        t("ask.view_evidence", n=5)  # "View 5 evidence passage(s)"
    """
    locale_dict = _LOCALES.get(_current_locale, EN)
    text = locale_dict.get(key, EN.get(key, key))
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, IndexError):
            pass
    return text
