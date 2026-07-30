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
    "add.submit": "添加并分析",
    "add.submit_archive": "添加到知识库",
    "add.submit_digest": "添加并生成洞察",
    "add.submit_deep_distill": "添加并深度蒸馏",
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
    "memory.title": "记忆卡",
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
    "memory.no_cards": "暂无记忆卡。使用「添加知识」创建第一张。",
    "memory.no_match": "没有匹配的卡片。",
    "memory.total": "共",
    "memory.cards_unit": "张记忆卡",
    "memory.archived": "已归档",
    "memory.other": "其他",
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
    "activate.no_cards": "暂无可用记忆卡。请先添加知识。",
    "activate.no_match": "未找到与当前任务相关的记忆卡。",
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
    "activate.no_results": "暂无相关记忆卡。",
    "activate.hint_label": "可选提示",
    "activate.hint_placeholder": "例如：之前某次讲座提到 AI 治理不只是模型准确率。",
    "activate.save_hint": "将此提示保存为新记忆卡",
    "activate.hint_saved": "已将提示保存为新记忆卡。",
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
    "footer.tagline": "RecallBite 记忆面包 — 今天存一条，明天用得上。",
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

    # Processing Depth
    "depth.label": "处理深度",
    "depth.auto": "自动",
    "depth.archive": "仅存档",
    "depth.digest": "生成洞察",
    "depth.deep_distill": "深度蒸馏",
    "depth.auto_reason": "路由判断",
    "depth.confidence": "置信度",
    "depth.archive_note": "已存档。支持搜索和引用，未生成卡片。",
    "depth.candidates_found": "已提取 {n} 个候选激活单元",

    # Activation Units
    "au.title": "激活单元",
    "au.subtitle": "可执行的方法、框架和决策规则。由深度蒸馏提取，经审核后激活。",
    "au.draft": "草稿",
    "au.active": "已激活",
    "au.archived": "已归档",
    "au.activate_btn": "激活此单元",
    "au.activate_success": "已激活",
    "au.activate_failed": "未通过验证",
    "au.delete_btn": "删除",
    "au.triggers": "触发场景",
    "au.anti_triggers": "不应触发",
    "au.steps": "执行步骤",
    "au.boundaries": "边界",
    "au.quality_checks": "质量检查",
    "au.evidence": "证据",
    "au.usage": "使用记录",
    "au.decoy_test": "诱饵测试",
    "au.run_decoy": "运行诱饵测试",
    "au.pass_rate": "通过率",
    "au.no_units": "暂无激活单元。使用「深度蒸馏」处理方法论材料以提取。",
    "au.filter_all": "全部",
    "au.filter_active": "已激活",
    "au.filter_draft": "草稿",

    # Feedback
    "fb.title": "这次激活有帮助吗？",
    "fb.useful": "有用",
    "fb.not_useful": "没用",
    "fb.false_trigger": "不该触发",
    "fb.missing_context": "缺少背景",
    "fb.expression_issue": "表达不合适",
    "fb.recorded": "反馈已记录",
    "fb.comment_placeholder": "可选说明…",

    # Activate with AU
    "activate.methods_used": "调用的方法",
    "activate.why_selected": "为什么选择这些方法",
    "activate.boundaries_note": "边界与置信度",
    "activate.clarification_needed": "需要澄清",

    # Demo workspace
    "demo.badge": "演示模式",
    "demo.load_btn": "加载演示工作区",
    "demo.exit_btn": "退出演示模式",
    "demo.note": "正在使用演示数据（5 个示例激活单元），不影响真实知识库。",
    "demo.loaded": "演示工作区已加载：5 个 Activation Units（来源：AI Essentials for Project Professionals）",
    "demo.reset_btn": "重置示例工作区",
    "demo.reset_done": "示例工作区已从标准示例重建（5 个示例激活单元，使用记录已清空）。",

    # Deep Distill Review
    "review.title": "深度蒸馏审核",
    "review.subtitle": "以下候选方法由系统从材料中自动识别。请逐一审核后再决定是否启用。",
    "review.sections_analyzed": "个章节已分析",
    "review.candidates_found": "个候选方法",
    "review.rejected_note": "个候选因质量不足被拒绝或合并",
    "review.when_to_use": "何时使用",
    "review.when_not_to_use": "何时不该使用",
    "review.confirm_first": "使用前要确认什么",
    "review.how_to_execute": "具体怎样执行",
    "review.source_label": "来源",
    "review.validation": "内部验证",
    "review.internal_passed": "内部测试已通过",
    "review.not_user_validated": "尚未经过真实用户验证",
    "review.btn_activate": "启用",
    "review.btn_keep_draft": "保持草稿",
    "review.btn_reject": "拒绝",
    "review.btn_edit": "编辑",
    "review.activated": "已启用",
    "review.rejected": "已拒绝",
    "review.what_it_produces": "最终能产生什么结果",

    # AU Library (enhanced)
    "lib.filter_all": "全部",
    "lib.filter_cards": "记忆卡",
    "lib.filter_au": "激活单元",
    "lib.filter_draft": "草稿",
    "lib.filter_review": "需要复核",
    "lib.when_to_use": "适用于",
    "lib.when_not_to_use": "不适用于",
    "lib.source": "来源",
    "lib.validation_status": "验证状态",
    "lib.usage_history": "使用记录",
    "lib.never_used": "尚未被真实任务调用",
    "lib.activations": "次调用",
    "lib.useful": "有用",
    "lib.false_triggers": "误触发",

    # AU-driven Activate (restructured)
    "act.task_understanding": "当前任务理解",
    "act.goal": "目标",
    "act.audience": "对象",
    "act.focus": "重点",
    "act.selected_methods": "本次调用的方法",
    "act.why_selected": "为什么选择",
    "act.matched_signals": "匹配依据",
    "act.missing_context": "尚未满足的条件",
    "act.deliverable": "最终可用输出",
    "act.qc_results": "质量检查结果",
    "act.supported": "已有资料支持的部分",
    "act.unsupported": "当前无法可靠支持的部分",
    "act.suggest_add": "建议补充的材料或方法",
    "act.sources": "来源与证据",
    "act.boundaries": "知识支持边界",
    "act.feedback_title": "评价本次输出",
    "act.feedback_scope": "反馈对象",
    "act.feedback_overall": "整体输出",
    "act.demo_task": "填入演示任务",
    "act.no_method": "没有方法被调用",
    "act.no_method_note": "当前知识库中没有与此任务匹配的可执行方法。",
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
    "add.submit": "Add & Analyze",
    "add.submit_archive": "Add to Knowledge Base",
    "add.submit_digest": "Add & Generate Insights",
    "add.submit_deep_distill": "Add & Deep Distill",
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
    "memory.cards_unit": "memory cards",
    "memory.archived": "Archived",
    "memory.other": "Other",
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

    # Processing Depth
    "depth.label": "Processing Depth",
    "depth.auto": "Auto",
    "depth.archive": "Archive Only",
    "depth.digest": "Create Insights",
    "depth.deep_distill": "Deep Distill",
    "depth.auto_reason": "Router decision",
    "depth.confidence": "Confidence",
    "depth.archive_note": "Archived. Supports search and citation. No card generated.",
    "depth.candidates_found": "Extracted {n} candidate Activation Unit(s)",

    # Activation Units
    "au.title": "Activation Units",
    "au.subtitle": "Executable methods, frameworks, and decision rules. Extracted via Deep Distill, activated after review.",
    "au.draft": "Draft",
    "au.active": "Active",
    "au.archived": "Archived",
    "au.activate_btn": "Activate this unit",
    "au.activate_success": "Activated",
    "au.activate_failed": "Validation failed",
    "au.delete_btn": "Delete",
    "au.triggers": "Trigger scenarios",
    "au.anti_triggers": "Should NOT trigger",
    "au.steps": "Execution steps",
    "au.boundaries": "Boundaries",
    "au.quality_checks": "Quality checks",
    "au.evidence": "Evidence",
    "au.usage": "Usage history",
    "au.decoy_test": "Decoy test",
    "au.run_decoy": "Run decoy test",
    "au.pass_rate": "Pass rate",
    "au.no_units": "No Activation Units yet. Use Deep Distill on methodology material to extract them.",
    "au.filter_all": "All",
    "au.filter_active": "Active",
    "au.filter_draft": "Draft",

    # Feedback
    "fb.title": "Was this activation helpful?",
    "fb.useful": "Useful",
    "fb.not_useful": "Not useful",
    "fb.false_trigger": "Should not trigger",
    "fb.missing_context": "Missing context",
    "fb.expression_issue": "Expression issue",
    "fb.recorded": "Feedback recorded",
    "fb.comment_placeholder": "Optional comment…",

    # Activate with AU
    "activate.methods_used": "Methods used",
    "activate.why_selected": "Why these methods were selected",
    "activate.boundaries_note": "Boundaries & confidence",
    "activate.clarification_needed": "Clarification needed",

    # Demo workspace
    "demo.badge": "Demo Mode",
    "demo.load_btn": "Load Demo Workspace",
    "demo.exit_btn": "Exit Demo Mode",
    "demo.note": "Using demo data (5 sample Activation Units). Your real knowledge base is not affected.",
    "demo.loaded": "Demo workspace loaded: 5 Activation Units (source: AI Essentials for Project Professionals)",
    "demo.reset_btn": "Reset Demo Workspace",
    "demo.reset_done": "Demo workspace rebuilt from the standard examples (5 sample Activation Units, usage history cleared).",

    # Deep Distill Review
    "review.title": "Deep Distill Review",
    "review.subtitle": "Candidate methods identified automatically from your material. Review each one before activating.",
    "review.sections_analyzed": "sections analyzed",
    "review.candidates_found": "candidate methods",
    "review.rejected_note": "candidates rejected or merged for insufficient quality",
    "review.when_to_use": "When to use",
    "review.when_not_to_use": "When NOT to use",
    "review.confirm_first": "Confirm before proceeding",
    "review.how_to_execute": "How to execute",
    "review.source_label": "Source",
    "review.validation": "Internal validation",
    "review.internal_passed": "Internal validation passed",
    "review.not_user_validated": "Not yet validated by real users",
    "review.btn_activate": "Activate",
    "review.btn_keep_draft": "Keep as Draft",
    "review.btn_reject": "Reject",
    "review.btn_edit": "Edit",
    "review.activated": "Activated",
    "review.rejected": "Rejected",
    "review.what_it_produces": "What it produces",

    # AU Library (enhanced)
    "lib.filter_all": "All",
    "lib.filter_cards": "Memory Cards",
    "lib.filter_au": "Activation Units",
    "lib.filter_draft": "Drafts",
    "lib.filter_review": "Needs Review",
    "lib.when_to_use": "Use when",
    "lib.when_not_to_use": "Do not use when",
    "lib.source": "Source",
    "lib.validation_status": "Validation status",
    "lib.usage_history": "Usage history",
    "lib.never_used": "Never triggered by a real task",
    "lib.activations": "activations",
    "lib.useful": "useful",
    "lib.false_triggers": "false triggers",

    # AU-driven Activate (restructured)
    "act.task_understanding": "Task Understanding",
    "act.goal": "Goal",
    "act.audience": "Audience",
    "act.focus": "Focus areas",
    "act.selected_methods": "Methods selected",
    "act.why_selected": "Why selected",
    "act.matched_signals": "Matched signals",
    "act.missing_context": "Conditions not yet met",
    "act.deliverable": "Ready-to-use deliverable",
    "act.qc_results": "Quality check results",
    "act.supported": "Supported by current knowledge base",
    "act.unsupported": "Not reliably supported yet",
    "act.suggest_add": "Suggested materials to add",
    "act.sources": "Sources & evidence",
    "act.boundaries": "Knowledge boundaries",
    "act.feedback_title": "Rate this output",
    "act.feedback_scope": "Feedback applies to",
    "act.feedback_overall": "Overall output",
    "act.demo_task": "Fill demo task",
    "act.no_method": "No method triggered",
    "act.no_method_note": "No executable method in the current knowledge base matches this task.",
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
