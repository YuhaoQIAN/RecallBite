"""
test_generator.py - 测试 generator 模块
"""

import pytest
from pathlib import Path
import sys

# 添加项目根目录到 path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.generator import generate_card
from src.card_schema import validate_card


def test_generate_card_returns_dict():
    """测试 generate_card() 返回 dict"""
    card = generate_card(
        knowledge_seed="AI governance is important",
        source_type="Webcast",
        topic_tags_text="AI, governance",
        source="Test source"
    )
    
    assert isinstance(card, dict)


def test_generate_card_has_all_required_fields():
    """测试返回 card 包含所有必填字段"""
    card = generate_card(
        knowledge_seed="AI governance is important for business",
        source_type="Article",
        topic_tags_text="AI governance, risk",
        source="Test article"
    )
    
    is_valid, missing_fields = validate_card(card)
    
    assert is_valid is True
    assert len(missing_fields) == 0


def test_fog_index_very_foggy():
    """测试 knowledge_seed 短文本时 Fog Index 是 Very Foggy"""
    card = generate_card(
        knowledge_seed="AI is important",  # 长度 < 40
        source_type="Note",
        topic_tags_text="AI",
        source=""
    )
    
    assert card["fog_index"]["level"] == "Very Foggy"


def test_fog_index_foggy():
    """测试 knowledge_seed 中等长度时 Fog Index 是 Foggy"""
    card = generate_card(
        knowledge_seed="AI governance 的重点不只是模型准确性,而是 accountability 在业务之间如何分配,并且需要把责任边界写进 proposal opening。",  # 长度 >= 40 且 < 120
        source_type="Webcast",
        topic_tags_text="AI governance",
        source=""
    )
    
    assert card["fog_index"]["level"] == "Foggy"


def test_fog_index_clear():
    """测试 knowledge_seed 长文本时 Fog Index 是 Clear"""
    base_text = "AI governance 的重点不只是模型准确性，而是 accountability 在业务、IT、risk、legal 和 compliance 之间如何分配。"
    long_seed = base_text * 3
    
    assert len(long_seed) >= 120, f"Seed length is {len(long_seed)}, need >= 120"
    
    card = generate_card(
        knowledge_seed=long_seed,
        source_type="Lecture",
        topic_tags_text="AI governance, accountability",
        source="Test lecture"
    )
    
    assert card["fog_index"]["level"] == "Clear"
    assert card["card_type"] == "Insight Pack"


def test_empty_knowledge_seed_raises_error():
    """测试 knowledge_seed 为空时抛出 ValueError"""
    with pytest.raises(ValueError):
        generate_card(
            knowledge_seed="",
            source_type="Note"
        )


def test_topic_tags_parsing():
    """测试标签解析"""
    card = generate_card(
        knowledge_seed="Test seed",
        source_type="Note",
        topic_tags_text="AI governance, accountability, risk management",
        source=""
    )
    
    assert len(card["topic_tags"]) == 3
    assert "AI governance" in card["topic_tags"]
    assert "accountability" in card["topic_tags"]
    assert "risk management" in card["topic_tags"]


def test_card_type_clue_card():
    """测试短输入生成 Clue Card"""
    card = generate_card(
        knowledge_seed="AI is important",  # 短文本
        source_type="Note",
        topic_tags_text="AI",
        source=""
    )
    
    assert card["card_type"] == "Clue Card"
    assert card["fog_index"]["level"] == "Very Foggy"


def test_card_type_use_card():
    """测试中等输入生成 Use Card"""
    card = generate_card(
        knowledge_seed="AI governance is about accountability across business, IT, and risk.",  # 中等文本
        source_type="Webcast",
        topic_tags_text="AI governance",
        source=""
    )
    
    assert card["card_type"] == "Use Card"
    assert card["fog_index"]["level"] == "Foggy"


def test_card_type_insight_pack():
    """测试长输入生成 Insight Pack"""
    base_text = "AI governance 的重点不只是模型准确性，而是 accountability 在业务、IT、risk、legal 和 compliance 之间如何分配，这是一个非常重要的观点。"
    long_seed = base_text * 2
    
    card = generate_card(
        knowledge_seed=long_seed,
        source_type="Transcript",
        topic_tags_text="AI governance, accountability",
        source=""
    )
    
    assert card["card_type"] == "Insight Pack"
    assert card["fog_index"]["level"] == "Clear"


def test_generated_card_contains_nested_detail_block():
    card = generate_card(
        knowledge_seed="AI governance 的重点不只是模型准确性，而是 accountability 在业务、IT、risk、legal 和 compliance 之间如何分配。",
        source_type="Webcast",
        topic_tags_text="AI governance",
        source=""
    )

    assert card["card_type"] in {"Use Card", "Insight Pack"}
    assert isinstance(card.get("copy_ready_lines", {}), dict)
    assert isinstance(card.get("use_cases", {}), dict)
    assert card.get("core_insight")
