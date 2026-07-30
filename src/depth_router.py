"""Processing Depth Router for RecallBite 记忆面包.

Determines how deeply a piece of material should be processed:
- archive: Save only, support Ask/citation
- digest: Archive + Memory Card (insights, use scenarios)
- deep_distill: Full extraction → candidate Activation Units

Auto mode considers multiple signals, NOT just text length.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class DepthDecision:
    """Result of depth routing."""
    selected_depth: str  # "archive" | "digest" | "deep_distill"
    reason: str
    confidence: str  # "high" | "medium" | "low"
    signals: dict = field(default_factory=dict)


# ── Methodology density indicators ─────────────────────────────────────────

_FRAMEWORK_SIGNALS = [
    # English
    r"\bframeworks?\b", r"\bstep\s*\d+\b", r"\bphase\s*\d+\b", r"\bprinciples?\b",
    r"\bmethodology\b", r"\bprocess\b", r"\bworkflow\b", r"\bdiagnostic\b",
    r"\bdecision\s+(?:tree|rule|matrix)\b", r"\bif\s+.*\s+then\b",
    r"\bdo\s+not\b.*\bwhen\b", r"\bboundary\b", r"\bprecondition\b",
    r"\bquality\s+check\b", r"\bchecklist\b", r"\bcriteria\b",
    # Chinese
    r"框架", r"步骤", r"阶段", r"原则", r"方法论", r"流程", r"工作流",
    r"诊断", r"决策", r"边界", r"前置条件", r"质量检查", r"清单", r"标准",
    r"第一步|第二步|第三步|第四步|第五步",
    r"如果.*那么", r"不适用", r"反例",
]

_COUNTEREXAMPLE_SIGNALS = [
    r"\bcounterexample\b", r"\banti-?pattern\b", r"\bfailure\s+mode\b",
    r"\bdo\s+not\s+use\b", r"\bwhen\s+not\s+to\b", r"\bpitfall\b",
    r"反例", r"反面", r"不要", r"不适用", r"失败模式", r"陷阱",
]

_CASE_SIGNALS = [
    r"\bcase\s+study\b", r"\bexample\b", r"\bfor\s+instance\b",
    r"\bin\s+practice\b", r"\breal[- ]world\b",
    r"案例", r"例如", r"实例", r"实践中", r"真实场景",
]

_TEMPORAL_SIGNALS = [
    r"\bnews\b", r"\bbreaking\b", r"\bannouncement\b", r"\bupdate\b",
    r"\b\d{4}[-/]\d{2}[-/]\d{2}\b", r"\bdeadline\b",
    r"新闻", r"公告", r"通知", r"截止", r"时效",
]


def route_depth(
    text: str,
    input_type: str = "auto-detect",
    intended_use: str = "",
    user_override: str = "",
) -> DepthDecision:
    """Determine processing depth for a material.

    Args:
        text: The material text.
        input_type: Detected or explicit input type.
        intended_use: User-stated intended use (if any).
        user_override: If user explicitly chose a depth ("archive", "digest", "deep_distill").

    Returns:
        DepthDecision with selected_depth, reason, confidence, and signals.
    """
    # User override always wins
    if user_override in ("archive", "digest", "deep_distill"):
        return DepthDecision(
            selected_depth=user_override,
            reason="User explicitly selected this depth.",
            confidence="high",
            signals={"user_override": True},
        )

    signals = _compute_signals(text, input_type, intended_use)
    score = _score_depth(signals)

    if score >= 6:
        depth = "deep_distill"
        confidence = "high" if score >= 8 else "medium"
        reason = _build_reason(depth, signals)
    elif score >= 3:
        depth = "digest"
        confidence = "high" if score >= 4 else "medium"
        reason = _build_reason(depth, signals)
    else:
        depth = "archive"
        confidence = "high" if score <= 1 else "medium"
        reason = _build_reason(depth, signals)

    return DepthDecision(
        selected_depth=depth,
        reason=reason,
        confidence=confidence,
        signals=signals,
    )


def _compute_signals(text: str, input_type: str, intended_use: str) -> dict:
    """Compute routing signals from material characteristics."""
    text_lower = text.lower()
    length = len(text)

    # Methodology density: count framework signal hits
    framework_hits = sum(1 for pat in _FRAMEWORK_SIGNALS if re.search(pat, text_lower))
    counterexample_hits = sum(1 for pat in _COUNTEREXAMPLE_SIGNALS if re.search(pat, text_lower))
    case_hits = sum(1 for pat in _CASE_SIGNALS if re.search(pat, text_lower))
    temporal_hits = sum(1 for pat in _TEMPORAL_SIGNALS if re.search(pat, text_lower))

    # Repeated structure detection (numbered steps, bullet patterns)
    numbered_steps = len(re.findall(r"(?:^|\n)\s*(?:\d+[.)]|Step\s*\d+|第[一二三四五六七八九十]+步)", text, re.IGNORECASE))
    bullet_density = len(re.findall(r"(?:^|\n)\s*[-•·]", text))

    # User intent signals
    wants_method = bool(re.search(
        r"沉淀|方法|长期|复用|执行|method|long[- ]term|reusable|executable",
        intended_use.lower() if intended_use else "",
    ))

    return {
        "length": length,
        "input_type": input_type,
        "framework_hits": framework_hits,
        "counterexample_hits": counterexample_hits,
        "case_hits": case_hits,
        "temporal_hits": temporal_hits,
        "numbered_steps": numbered_steps,
        "bullet_density": bullet_density,
        "wants_method": wants_method,
        "intended_use": intended_use,
    }


def _score_depth(signals: dict) -> int:
    """Score material for depth routing. Higher = deeper processing needed."""
    score = 0

    # Framework density (max +4)
    fw = signals["framework_hits"]
    if fw >= 6:
        score += 4
    elif fw >= 4:
        score += 3
    elif fw >= 2:
        score += 2
    elif fw >= 1:
        score += 1

    # Counterexamples / anti-patterns (+2)
    if signals["counterexample_hits"] >= 2:
        score += 2
    elif signals["counterexample_hits"] >= 1:
        score += 1

    # Cases / examples (+1)
    if signals["case_hits"] >= 2:
        score += 1

    # Numbered steps / structure (+2)
    if signals["numbered_steps"] >= 3:
        score += 2
    elif signals["numbered_steps"] >= 1:
        score += 1

    # User explicitly wants method extraction (+3)
    if signals["wants_method"]:
        score += 3

    # Length bonus (+1 for substantial material)
    if signals["length"] >= 3000:
        score += 1
    elif signals["length"] >= 800:
        score += 1

    # Temporal/news penalty (-2): time-sensitive material is usually archive-only
    if signals["temporal_hits"] >= 2:
        score -= 2

    # Short thought penalty
    if signals["length"] < 120:
        score -= 1

    return max(0, score)


def _build_reason(depth: str, signals: dict) -> str:
    """Build a human-readable reason for the depth decision."""
    parts = []

    if depth == "deep_distill":
        if signals["framework_hits"] >= 4:
            parts.append("High methodology density with frameworks/steps")
        if signals["counterexample_hits"] >= 1:
            parts.append("contains anti-patterns or counterexamples")
        if signals["numbered_steps"] >= 3:
            parts.append("has repeated numbered steps")
        if signals["wants_method"]:
            parts.append("user intends to extract reusable method")
        if not parts:
            parts.append("Material shows sufficient structure for deep extraction")

    elif depth == "digest":
        if signals["framework_hits"] >= 1:
            parts.append("Some methodology signals present")
        if signals["case_hits"] >= 1:
            parts.append("contains examples or cases")
        if signals["length"] >= 500:
            parts.append("sufficient length for insight extraction")
        if not parts:
            parts.append("Material has enough content for insight generation")

    else:  # archive
        if signals["temporal_hits"] >= 2:
            parts.append("Time-sensitive / news content")
        if signals["length"] < 120:
            parts.append("Too short for reliable insight extraction")
        if signals["framework_hits"] == 0:
            parts.append("Low methodology density")
        if not parts:
            parts.append("Factual reference material suitable for archive")

    return "; ".join(parts) + "."
