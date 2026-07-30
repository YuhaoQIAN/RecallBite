"""Deterministic activation analyzer.

Turns recalled cards into ready-to-use content for the current task.
"""

from __future__ import annotations


def activate_memory_deterministic(
    current_task: str,
    cards: list[tuple[dict, int]],
) -> list[dict]:
    """Generate activation suggestions for each recalled card.

    Args:
        current_task: The user's current task description.
        cards: List of (card, score) tuples from retrieval.

    Returns:
        List of suggestion dicts, one per card.
    """
    from src.activation import generate_apply_suggestion

    suggestions = []
    for card, score in cards:
        suggestion = generate_apply_suggestion(current_task, card, score)
        suggestions.append(suggestion)
    return suggestions
