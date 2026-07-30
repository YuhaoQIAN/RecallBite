"""Tests for activation guidance generation."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.activation import generate_apply_suggestion


def _base_card(card_type="Insight Pack", fog_level="Clear"):
    return {
        "id": "1",
        "created_at": "2024-01-01T00:00:00",
        "knowledge_seed": "AI governance 的重点不只是模型准确性，而是 accountability 在业务、IT、risk、legal 和 compliance 之间如何分配。",
        "source_type": "Webcast",
        "source": "Demo",
        "topic_tags": ["AI governance", "accountability"],
        "card_type": card_type,
        "core_insight": "AI governance 的重点不只是模型准确性，而是 accountability 在业务、IT、risk、legal 和 compliance 之间如何分配。",
        "use_cases": {
            "work_angle": "用于 proposal 或 review。",
            "conversation_angle": "用于 meeting 讨论。",
            "question_angle": "用于追问前提。",
            "personal_asset_angle": "用于 CPD。",
        },
        "copy_ready_lines": {
            "professional_sentence": "可直接复制的专业表达。",
            "meeting_question": "可在会议中提出的问题。",
            "reflection_sentence": "可用于 CPD 的表达。",
        },
        "trigger_map": {
            "keywords": ["AI governance", "accountability"],
            "scenarios": ["proposal", "meeting"],
        },
        "fog_index": {
            "level": fog_level,
            "reason": "test",
            "what_to_add": "test",
        },
        "insight_pack": {
            "thirty_second_takeaway": "卡片的核心观点。",
            "key_insights": ["第一条洞察。", "第二条洞察。", "第三条洞察。"],
            "questions_to_ask": ["当前最缺什么前提？"],
            "copy_ready_paragraph": "可复制段落。",
        },
        "use_card": {},
        "clue_card": {},
    }


def test_activation_uses_proposal_language():
    card = _base_card(card_type="Insight Pack", fog_level="Clear")
    suggestion = generate_apply_suggestion(
        "我要写一个 AI governance proposal opening，想强调 accountability 和 risk ownership。",
        card,
        8,
    )

    assert "proposal" in suggestion["how_to_use_now"].lower() or "opening" in suggestion["how_to_use_now"].lower() or "提案" in suggestion["how_to_use_now"]
    assert "accountability" in suggestion["why_relevant"].lower() or "\u8d23\u4efb" in suggestion["why_relevant"]
    assert (
        suggestion["confidence_note"].startswith("This card is based on relatively complete input")
        or "\u8fd9\u5f20\u5361\u7247\u57fa\u4e8e\u8f83\u5b8c\u6574" in suggestion["confidence_note"]
    )


def test_activation_is_conservative_for_very_foggy_cards():
    card = _base_card(card_type="Clue Card", fog_level="Very Foggy")
    suggestion = generate_apply_suggestion(
        "我要准备一个 meeting talking point。",
        card,
        2,
    )

    assert "verify the source" in suggestion["confidence_note"].lower() or "\u9a8c\u8bc1\u6765\u6e90" in suggestion["confidence_note"]
    assert "\u8fd8\u592a\u5c11" in suggestion["copy_ready_paragraph"] or "\u7ebf\u7d22" in suggestion["copy_ready_paragraph"]