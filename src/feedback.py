"""User feedback loop for RecallBite 记忆面包.

Two separate concerns are tracked independently:

1. Activation — a unit actually participates in generating output for a task.
   ``record_activation()`` increments ``activation_count`` exactly once per
   activation event, regardless of how much feedback is later submitted.

2. Feedback — the user rates a past activation. ``record_feedback()`` updates
   ONLY the specific feedback counter (useful / not_useful / false_trigger /
   missing_context / expression_issue). It NEVER increments activation_count.

Feedback types:
- useful: increases priority/quality score
- not_useful: decreases priority
- false_trigger: increments false-trigger count, suggests anti-trigger
- missing_context: increments missing-context count, records required-context signal
- expression_issue: output generation problem, does NOT modify core method

An ``activation_event_id`` links an activation event to all feedback submitted
for it, so multiple feedback entries never inflate the activation count.

Key principle: feedback does NOT silently rewrite the original unit.
It records suggestions; updates happen only after user confirmation
or evidence threshold.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from src.activation_unit import get_unit, update_unit


# ── Feedback types ────────────────────────────────────────────────────────

FEEDBACK_TYPES = [
    "useful",           # 有用
    "not_useful",       # 没用
    "false_trigger",    # 不该触发
    "missing_context",  # 缺少背景
    "expression_issue", # 输出正确但表达不合适
]


# ── Public API ────────────────────────────────────────────────────────────


def record_activation(unit_ids: list[str], task: str = "") -> str:
    """Record that units actually participated in generating output for a task.

    This is the ONLY place ``activation_count`` is incremented. Feedback never
    increments it. Each call represents one activation event and returns an
    ``activation_event_id`` that subsequent feedback can reference, so multiple
    feedback submissions for the same activation do not inflate the count.

    Args:
        unit_ids: IDs of the units that participated in this activation.
        task: The task that triggered the activation.

    Returns:
        The activation_event_id for this event (empty-string-safe UUID token).
    """
    event_id = f"evt_{uuid.uuid4().hex[:12]}"
    now = datetime.now().isoformat()
    for unit_id in unit_ids:
        unit = get_unit(unit_id)
        if not unit:
            continue
        usage = unit.get("usage", {})
        usage["activation_count"] = usage.get("activation_count", 0) + 1
        usage["last_used_at"] = now
        activation_log = unit.get("_activation_log", [])
        activation_log.append({
            "activation_event_id": event_id,
            "task": task,
            "created_at": now,
        })
        update_unit(unit_id, {"usage": usage, "_activation_log": activation_log})
    return event_id


def record_feedback(
    unit_id: str,
    feedback_type: str,
    task: str = "",
    comment: str = "",
    activation_event_id: str = "",
) -> dict:
    """Record user feedback for an activation unit.

    Args:
        unit_id: The activation unit ID.
        feedback_type: One of FEEDBACK_TYPES.
        task: The task that was being performed.
        comment: Optional user comment.

    Returns:
        Dict with success status and any suggestions generated.
    """
    if feedback_type not in FEEDBACK_TYPES:
        return {"success": False, "error": f"Invalid feedback type: {feedback_type}"}

    unit = get_unit(unit_id)
    if not unit:
        return {"success": False, "error": "Unit not found"}

    # Build feedback entry (linked to the activation event when provided)
    entry = {
        "type": feedback_type,
        "task": task,
        "comment": comment,
        "recorded_at": datetime.now().isoformat(),
        "activation_event_id": activation_event_id,
    }

    # Update feedback counters ONLY. Feedback NEVER increments activation_count
    # — that counter changes solely in record_activation(). last_used_at also
    # reflects the activation event, not the feedback timestamp.
    usage = unit.get("usage", {})

    suggestions = []

    if feedback_type == "useful":
        usage["useful_count"] = usage.get("useful_count", 0) + 1

    elif feedback_type == "not_useful":
        usage["not_useful_count"] = usage.get("not_useful_count", 0) + 1

    elif feedback_type == "false_trigger":
        usage["false_trigger_count"] = usage.get("false_trigger_count", 0) + 1
        # Suggest adding an anti-trigger
        suggestions.append({
            "action": "add_anti_trigger",
            "suggested_scenario": task or "The task that triggered this incorrectly",
            "reason": f"User marked as false trigger. Task: {task}",
        })

    elif feedback_type == "missing_context":
        usage["missing_context_count"] = usage.get("missing_context_count", 0) + 1
        # Suggest adding required_context to triggers
        suggestions.append({
            "action": "add_required_context",
            "suggested_context": comment or "Additional context needed",
            "reason": "User indicated missing context during activation.",
        })

    elif feedback_type == "expression_issue":
        usage["expression_issue_count"] = usage.get("expression_issue_count", 0) + 1
        # This affects output generation, NOT the core method
        suggestions.append({
            "action": "note_expression_preference",
            "note": comment or "User found expression inappropriate",
            "reason": "Expression issue noted. Core method unchanged.",
        })

    # Append to feedback log (do NOT auto-apply suggestions)
    feedback_log = unit.get("_feedback_log", [])
    entry["suggestions"] = suggestions
    feedback_log.append(entry)

    # Save updates
    update_unit(unit_id, {
        "usage": usage,
        "_feedback_log": feedback_log,
    })

    return {
        "success": True,
        "feedback_type": feedback_type,
        "suggestions": suggestions,
        "usage_summary": {
            "total_activations": usage.get("activation_count", 0),
            "useful": usage.get("useful_count", 0),
            "not_useful": usage.get("not_useful_count", 0),
            "false_triggers": usage.get("false_trigger_count", 0),
            "missing_context": usage.get("missing_context_count", 0),
            "expression_issue": usage.get("expression_issue_count", 0),
        },
    }


def get_feedback_summary(unit_id: str) -> dict:
    """Get a summary of feedback for a unit."""
    unit = get_unit(unit_id)
    if not unit:
        return {"error": "Unit not found"}

    usage = unit.get("usage", {})
    feedback_log = unit.get("_feedback_log", [])

    total = usage.get("activation_count", 0)
    useful = usage.get("useful_count", 0)
    not_useful = usage.get("not_useful_count", 0)
    false_triggers = usage.get("false_trigger_count", 0)

    # Calculate usefulness rate
    rated = useful + not_useful
    usefulness_rate = useful / rated if rated > 0 else 0.0

    # Pending suggestions (not yet applied)
    pending_suggestions = []
    for entry in feedback_log:
        for s in entry.get("suggestions", []):
            pending_suggestions.append(s)

    return {
        "total_activations": total,
        "useful": useful,
        "not_useful": not_useful,
        "false_triggers": false_triggers,
        "usefulness_rate": round(usefulness_rate, 2),
        "pending_suggestions_count": len(pending_suggestions),
        "pending_suggestions": pending_suggestions[:5],
        "last_used_at": usage.get("last_used_at", ""),
    }


def should_auto_update(unit_id: str) -> tuple[bool, str]:
    """Check if feedback evidence is strong enough to suggest an update.

    Does NOT auto-apply. Returns whether to prompt the user.
    """
    unit = get_unit(unit_id)
    if not unit:
        return False, ""

    usage = unit.get("usage", {})
    false_triggers = usage.get("false_trigger_count", 0)
    useful = usage.get("useful_count", 0)
    not_useful = usage.get("not_useful_count", 0)

    # If false triggers exceed useful activations, suggest review
    if false_triggers >= 3 and false_triggers > useful:
        return True, "Multiple false triggers recorded. Consider adding anti-triggers or archiving this unit."

    # If not_useful significantly exceeds useful
    if not_useful >= 3 and not_useful > useful * 2:
        return True, "Users frequently find this unit not useful. Consider revising triggers or boundaries."

    return False, ""
