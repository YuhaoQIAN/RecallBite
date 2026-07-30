"""
test_storage.py - 测试 storage 模块
"""

import json
import pytest
from pathlib import Path
import sys

# 添加项目根目录到 path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.storage import ensure_data_file, load_cards, save_cards, add_card, delete_card


@pytest.fixture
def temp_data_dir(tmp_path):
    """使用临时目录进行测试"""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    cards_file = data_dir / "cards.json"
    
    # 临时覆盖 CARDS_FILE 和 DATA_DIR
    import src.storage as storage_module
    original_cards_file = storage_module.CARDS_FILE
    original_data_dir = storage_module.DATA_DIR
    
    storage_module.CARDS_FILE = cards_file
    storage_module.DATA_DIR = data_dir
    
    yield cards_file
    
    # 恢复原始值
    storage_module.CARDS_FILE = original_cards_file
    storage_module.DATA_DIR = original_data_dir


def test_ensure_data_file(temp_data_dir):
    """测试可以创建 data 文件"""
    ensure_data_file()
    assert temp_data_dir.exists()
    
    # 检查文件内容
    with open(temp_data_dir, "r", encoding="utf-8") as f:
        data = json.load(f)
        assert data == []


def test_save_and_load_cards(temp_data_dir):
    """测试可以保存和读取 cards"""
    test_cards = [
        {"id": "1", "name": "Card 1"},
        {"id": "2", "name": "Card 2"}
    ]
    
    save_cards(test_cards)
    loaded_cards = load_cards()
    
    assert len(loaded_cards) == 2
    assert loaded_cards[0]["id"] == "1"
    assert loaded_cards[1]["id"] == "2"


def test_add_card(temp_data_dir):
    """测试可以添加 card"""
    # 先保存一个空列表
    save_cards([])
    
    # 添加卡片
    card = {"id": "test-1", "name": "Test Card"}
    add_card(card)
    
    # 验证
    cards = load_cards()
    assert len(cards) == 1
    assert cards[0]["id"] == "test-1"


def test_delete_card(temp_data_dir):
    """测试可以删除 card"""
    # 先添加两张卡片
    save_cards([
        {"id": "1", "name": "Card 1"},
        {"id": "2", "name": "Card 2"}
    ])
    
    # 删除一张
    result = delete_card("1")
    
    assert result is True
    
    # 验证
    cards = load_cards()
    assert len(cards) == 1
    assert cards[0]["id"] == "2"


def test_delete_nonexistent_card(temp_data_dir):
    """测试删除不存在的 card"""
    save_cards([{"id": "1", "name": "Card 1"}])
    
    result = delete_card("999")
    
    assert result is False
