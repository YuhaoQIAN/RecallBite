"""
storage.py - 负责所有本地 JSON 读写操作

Enhancements:
- update_card: partial update with history tracking
- get_card: fetch single card by id
- record_usage: track activation history
- atomic write via temp file + rename
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path


# 数据文件路径
DATA_DIR = Path(__file__).parent.parent / "data"
CARDS_FILE = DATA_DIR / "cards.json"


def ensure_data_file() -> None:
    """确保 data 目录和 cards.json 文件存在"""
    if not DATA_DIR.exists():
        DATA_DIR.mkdir(parents=True, exist_ok=True)

    if not CARDS_FILE.exists():
        with open(CARDS_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)


def load_cards() -> list[dict]:
    """
    加载所有卡片
    - 正常读取 cards.json
    - 如果文件不存在,创建后返回空数组
    - 如果 JSON 损坏,备份损坏文件并创建新的空 cards.json
    """
    ensure_data_file()

    try:
        with open(CARDS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = DATA_DIR / f"cards_corrupted_backup_{timestamp}.json"
        os.rename(CARDS_FILE, backup_file)
        with open(CARDS_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)
        return []
    except FileNotFoundError:
        ensure_data_file()
        return []


def save_cards(cards: list[dict]) -> None:
    """
    原子保存卡片列表到 cards.json。
    先写入临时文件，再重命名，避免写坏原文件。
    """
    ensure_data_file()

    data = json.dumps(cards, ensure_ascii=False, indent=2)
    # Write to temp file in same directory for atomic rename
    fd, temp_path = tempfile.mkstemp(dir=DATA_DIR, suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(data)
        os.replace(temp_path, CARDS_FILE)
    except Exception:
        # Clean up temp file on failure
        try:
            os.remove(temp_path)
        except OSError:
            pass
        raise


def get_card(card_id: str) -> dict | None:
    """Fetch a single card by id."""
    cards = load_cards()
    for card in cards:
        if card.get("id") == card_id:
            return card
    return None


def add_card(card: dict) -> None:
    """Add a new card to storage."""
    cards = load_cards()
    cards.append(card)
    save_cards(cards)


def update_card(card_id: str, updates: dict) -> bool:
    """
    Partially update a card by id.

    - updates dict is merged into existing card fields
    - _edit_history is appended automatically
    - Returns True if card was found and updated
    """
    cards = load_cards()
    for card in cards:
        if card.get("id") == card_id:
            # Record edit history
            history = card.setdefault("_edit_history", [])
            history.append({
                "edited_at": datetime.now().isoformat(),
                "fields_changed": list(updates.keys()),
            })
            # Apply updates
            for key, value in updates.items():
                if key == "id":
                    continue  # Never allow id change
                card[key] = value
            save_cards(cards)
            return True
    return False


def delete_card(card_id: str) -> bool:
    """Delete a card by id. Returns True if deleted."""
    cards = load_cards()
    new_cards = [card for card in cards if card.get("id") != card_id]
    if len(new_cards) < len(cards):
        save_cards(new_cards)
        return True
    return False


def record_usage(card_id: str, task: str) -> bool:
    """
    Record that a card was used for a specific task.

    - Appends to _usage_history on the card
    - Returns True if card was found
    """
    cards = load_cards()
    for card in cards:
        if card.get("id") == card_id:
            history = card.setdefault("_usage_history", [])
            history.append({
                "used_at": datetime.now().isoformat(),
                "task": task,
            })
            save_cards(cards)
            return True
    return False

