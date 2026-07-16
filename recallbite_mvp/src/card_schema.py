"""card_schema.py - Card creation helpers and validation."""

from __future__ import annotations

import uuid
from datetime import datetime


def create_empty_card() -> dict:
    """Create an empty card template with all required fields."""
    return {
        "id": str(uuid.uuid4()),
        "created_at": datetime.now().isoformat(),
        "knowledge_seed": "",
        "source_type": "",
        "source": "",
        "topic_tags": [],
        "card_type": "Use Card",
        "core_insight": "",
        "use_cases": {
            "work_angle": "",
            "conversation_angle": "",
            "question_angle": "",
            "personal_asset_angle": "",
        },
        "copy_ready_lines": {
            "professional_sentence": "",
            "meeting_question": "",
            "reflection_sentence": "",
        },
        "trigger_map": {
            "keywords": [],
            "scenarios": [],
        },
        "fog_index": {
            "level": "",
            "reason": "",
            "evidence_quality": "",
            "what_to_add": "",
        },
        "source_grounding": {
            "source_kind": "pasted_text",
            "source_title": "",
            "source_reference": "",
            "retrieved_at": "",
            "is_verifiable": False,
            "evidence_spans": [],
        },
        "insight_pack": {},
        "use_card": {},
        "clue_card": {},
    }


def validate_card(card: dict) -> tuple[bool, list[str]]:
    """Validate a card has all required fields and correct types."""
    required_fields = [
        "id",
        "created_at",
        "knowledge_seed",
        "source_type",
        "source",
        "topic_tags",
        "card_type",
        "core_insight",
        "use_cases",
        "copy_ready_lines",
        "trigger_map",
        "fog_index",
        "source_grounding",
    ]

    missing_fields = []
    for field in required_fields:
        if field not in card:
            missing_fields.append(f"missing field: {field}")

    type_checks = [
        ("topic_tags", list),
        ("use_cases", dict),
        ("copy_ready_lines", dict),
        ("trigger_map", dict),
        ("fog_index", dict),
        ("source_grounding", dict),
    ]

    for field, expected_type in type_checks:
        if field in card and not isinstance(card[field], expected_type):
            missing_fields.append(f"{field} must be a {expected_type.__name__}")

    # Card-type-specific validation
    card_type = card.get("card_type", "")
    if card_type == "Insight Pack":
        ip = card.get("insight_pack", {})
        if not ip.get("thirty_second_takeaway"):
            missing_fields.append("insight_pack.thirty_second_takeaway required")
        if len(ip.get("key_insights", [])) < 1:
            missing_fields.append("insight_pack.key_insights must have >= 1 items")
    elif card_type == "Use Card":
        uc = card.get("use_card", {})
        if not uc.get("what_it_means"):
            missing_fields.append("use_card.what_it_means required")
    elif card_type == "Clue Card":
        cc = card.get("clue_card", {})
        if not cc.get("possible_direction"):
            missing_fields.append("clue_card.possible_direction required")

    if missing_fields:
        return False, missing_fields

    return True, []

