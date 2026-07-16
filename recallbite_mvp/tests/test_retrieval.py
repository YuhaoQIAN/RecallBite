"""
test_retrieval.py - 测试 retrieval 模块
"""

import pytest
from pathlib import Path
import sys

# 添加项目根目录到 path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.retrieval import retrieve_relevant_cards


def create_test_card(card_id="1", tags=None, keywords=None):
    """创建测试用卡片"""
    return {
        "id": card_id,
        "created_at": "2024-01-01T00:00:00",
        "knowledge_seed": "AI governance is important for business",
        "source_type": "Test",
        "source": "Test",
        "topic_tags": tags or ["AI governance"],
        "core_insight": "AI governance relates to accountability",
        "use_cases": {},
        "copy_ready_lines": {},
        "trigger_map": {
            "keywords": keywords or ["AI", "governance"],
            "scenarios": ["proposal", "meeting"]
        },
        "fog_index": {
            "level": "Clear",
            "reason": "Test",
            "what_to_add": "Test"
        }
    }


def test_retrieval_matches_by_tag():
    """测试 retrieval 能按 tag 返回卡片"""
    card = create_test_card(tags=["AI governance"])
    cards = [card]
    
    current_task = "I need to write about AI governance"
    
    results = retrieve_relevant_cards(current_task, cards, top_k=1)
    
    assert len(results) > 0
    assert results[0][0]["id"] == "1"


def test_retrieval_score_greater_than_zero():
    """测试 score 大于 0"""
    card = create_test_card(tags=["AI governance"], keywords=["accountability"])
    cards = [card]
    
    current_task = "AI governance and accountability in proposal"
    
    results = retrieve_relevant_cards(current_task, cards, top_k=1)
    
    assert len(results) > 0
    assert results[0][1] > 0  # score 应该大于 0


def test_retrieval_fallback_when_no_match():
    """测试 fallback: 当没有匹配时返回最近的卡片"""
    card1 = create_test_card(card_id="1", tags=["机器学习"], keywords=["深度学习"])
    card1["knowledge_seed"] = "神经网络模型训练"
    card1["core_insight"] = "人工智能发展趋势"
    
    card2 = create_test_card(card_id="2", tags=["区块链"], keywords=["加密货币"])
    card2["created_at"] = "2024-01-02T00:00:00"  # 更新
    card2["knowledge_seed"] = "分布式账本技术"
    card2["core_insight"] = "去中心化应用"
    
    cards = [card1, card2]
    
    # 完全不相关的任务 (使用英文避免中文 substring 匹配)
    current_task = "cooking pizza pasta recipe"
    
    results = retrieve_relevant_cards(current_task, cards, top_k=1)
    
    # 应该返回卡片,但 score 为 0
    assert len(results) > 0
    assert results[0][1] == 0  # score 为 0


def test_retrieval_returns_recent_cards_on_fallback():
    """测试 fallback 返回最近的卡片"""
    card1 = create_test_card(card_id="1", tags=["旧主题"], keywords=["历史"])
    card1["created_at"] = "2024-01-01T00:00:00"
    card1["knowledge_seed"] = "古代文明研究"
    card1["core_insight"] = "考古学发现"
    
    card2 = create_test_card(card_id="2", tags=["新主题"], keywords=["现代"])
    card2["created_at"] = "2024-01-02T00:00:00"
    card2["knowledge_seed"] = "当代科技发展"
    card2["core_insight"] = "技术创新趋势"
    
    cards = [card1, card2]
    
    # 使用完全不相关的英文任务
    current_task = "baking bread cake cookie"
    
    results = retrieve_relevant_cards(current_task, cards, top_k=1)
    
    # 应该返回 card2 (更新的)
    assert len(results) > 0
    assert results[0][0]["id"] == "2"


def test_retrieval_empty_cards():
    """测试空卡片列表"""
    results = retrieve_relevant_cards("any task", [], top_k=3)
    
    assert len(results) == 0
