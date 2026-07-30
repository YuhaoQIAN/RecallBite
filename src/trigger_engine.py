"""Trigger Engine for RecallBite 记忆面包.

Evaluates whether an Activation Unit should be triggered for a given task.
Does NOT rely on keyword matching alone — considers:
- task topic
- problem shape
- user goal
- constraints
- audience
- output intent
- required context
- anti-trigger conflicts

Hard gates:
- If topic info is insufficient, do NOT force-trigger.
- If anti-trigger hits, default to do_not_trigger.
- If required context is missing, generate a minimal clarification question.
- Vague tasks ("我要投标", "write report") without topic → clarification only.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class TriggerDecision:
    """Result of trigger evaluation for one unit."""
    unit_id: str
    decision: str  # "trigger" | "maybe" | "do_not_trigger"
    score: float
    matched_signals: list[str] = field(default_factory=list)
    missing_context: list[str] = field(default_factory=list)
    anti_trigger_hits: list[str] = field(default_factory=list)
    reason: str = ""
    clarification_question: str = ""


# ── Vague task detection ──────────────────────────────────────────────────

_VAGUE_PATTERNS = [
    r"^(我要|我想|帮我|准备|写)(投标|proposal|报告|report|文章|article|meeting|开会|汇报)$",
    r"^(i need|i want|write|prepare|help with)\s+(a\s+)?(proposal|report|article|meeting|presentation)$",
]


def is_vague_task(task: str) -> bool:
    """Check if a task is too vague to trigger any method."""
    task_stripped = task.strip()
    if len(task_stripped) < 10:
        return True
    for pattern in _VAGUE_PATTERNS:
        if re.match(pattern, task_stripped, re.IGNORECASE):
            return True
    return False


# ── Public API ────────────────────────────────────────────────────────────


def evaluate_triggers(
    task: str,
    units: list[dict],
    task_context: dict | None = None,
) -> list[TriggerDecision]:
    """Evaluate all active units against a task.

    Args:
        task: The user's current task description.
        units: List of activation unit dicts (should be active status).
        task_context: Optional parsed task context (topic, intent, audience, etc.)

    Returns:
        List of TriggerDecision, sorted by score descending.
    """
    if is_vague_task(task):
        # Hard gate: vague tasks get no triggers, only clarification
        return [
            TriggerDecision(
                unit_id=u.get("id", ""),
                decision="do_not_trigger",
                score=0.0,
                reason="Task is too vague. Need topic/subject information before triggering any method.",
                clarification_question=_generate_clarification(task),
            )
            for u in units
        ]

    # Parse task into components
    parsed = task_context or _parse_task_light(task)

    decisions = []
    for unit in units:
        decision = _evaluate_single_unit(task, parsed, unit)
        decisions.append(decision)

    # Sort by score descending
    decisions.sort(key=lambda d: d.score, reverse=True)
    return decisions


def generate_decoy_tests(unit: dict) -> dict:
    """Generate DOMAIN-AWARE decoy test cases for a unit using natural language.

    Produces:
    - 5 natural distant-paraphrase should-trigger cases (domain-specific)
    - 5 same-topic hard negatives (different problem shape)
    - 3 boundary cases requiring clarification

    CRITICAL: Test text must NOT contain unit name or purpose verbatim.
    Tests must be natural user language that references the DOMAIN CONCEPTS
    without naming the unit directly.
    """
    name = unit.get("name", "")
    purpose = unit.get("purpose", "")
    unit_type = unit.get("type", "framework")
    steps = unit.get("execution_steps", [])
    diag_qs = unit.get("diagnostic_questions", [])
    evidence_text = " ".join(s.get("text", "") for s in unit.get("evidence_spans", []))[:500]
    triggers = unit.get("triggers", [])
    trigger_signals = []
    for t in triggers:
        trigger_signals.extend(t.get("signals", []))

    # Extract DOMAIN-SPECIFIC keywords from unit's entire content
    all_text = name + " " + purpose + " " + evidence_text + " " + " ".join(diag_qs) + " " + " ".join(trigger_signals)
    domain_words = list(_normalize_words(all_text))[:12]
    # Get the core domain concepts (most specific words)
    domain_topic = _extract_domain_topic(domain_words, unit_type)
    # PRIORITY: Use trigger signals (actual domain keywords from extraction) over stemmed fragments
    # Trigger signals preserve compound terms like "machine learning", "supervised learning"
    top_concepts = [s for s in trigger_signals if s.lower() not in _GENERIC_MATCH_NOISE and len(s) > 3][:4]
    if len(top_concepts) < 2:
        # Fallback to normalized words
        extra = [w for w in domain_words if w not in _GENERIC_MATCH_NOISE and len(w) > 3 and w not in top_concepts][:4 - len(top_concepts)]
        top_concepts.extend(extra)

    should_trigger = []
    should_not_trigger = []
    boundary_cases = []

    # ── Should-trigger: natural user requests that NEED this method ──────
    # These describe a SITUATION requiring this unit, using DOMAIN CONCEPTS
    # but NOT naming the unit directly.
    # Strategy: paraphrase the trigger scenario into natural user language.
    trigger_scenario = triggers[0].get("scenario", "") if triggers else ""

    if unit_type == "diagnostic":
        should_trigger = [
            f"I have a system and I'm not sure if it qualifies as intelligent or just automated. How can I tell the difference?",
            f"We're evaluating several tools and need a structured way to determine which ones actually use machine learning versus simple rule-based automation.",
            f"My manager asked me to assess whether our current scheduling software has genuine AI capabilities. What questions should I ask?",
            f"Before we invest in upgrading our platform, I need to verify if it truly learns from data or just follows hardcoded rules.",
            f"I'm writing a technical assessment and need to classify three vendor products as either AI-powered or conventional automation.",
        ]
    elif unit_type == "workflow":
        c = top_concepts[:2] if top_concepts else ["process", "methodology"]
        should_trigger = [
            f"I need to carry out a structured {c[0]} process for my team. Can you walk me through the recommended steps?",
            f"We've been asked to implement {c[0]} at work. What's the right sequence of actions to follow?",
            f"I'm responsible for executing a multi-step procedure involving {c[0]} and want to make sure I don't skip anything.",
            f"My project requires applying {', '.join(c)} from start to finish. Guide me through the execution.",
            f"I need a step-by-step approach for {c[0]} — what's the recommended order of operations?",
        ]
    elif unit_type == "framework":
        # Use trigger scenario to generate natural paraphrases
        should_trigger = _generate_framework_should_trigger(trigger_scenario, top_concepts, name)
    else:
        c = top_concepts[:2] if top_concepts else ["this challenge", "my domain"]
        c_joined = ", ".join(c[:2])
        should_trigger = [
            f"I'm facing a decision about {c[0]} at work and need a structured way to think about it.",
            f"Can you help me work through {c_joined} methodically? I need a clear approach.",
            f"I need guidance on how to handle {c[0]} in my current project context.",
            f"What's the recommended way to approach {c_joined} when resources are limited?",
            f"I want to make sure I'm applying the right method for {c[0]} in this situation.",
        ]

    # ── Hard negatives: same domain, DIFFERENT problem shape ────────────
    # These share the domain topic but need a completely different kind of answer
    c_topic = top_concepts[0] if top_concepts else domain_topic
    if unit_type == "diagnostic":
        should_not_trigger = [
            f"Can you explain the history and evolution of artificial intelligence as a field? I need background for a presentation.",
            f"Write a one-page summary of how machine learning works for non-technical executives.",
            f"What are the latest trends in AI adoption across industries this year?",
            f"I need to calculate the ROI of implementing an AI solution — help me build a financial model.",
            f"Help me draft an email to stakeholders explaining why we chose a particular AI vendor.",
        ]
    elif unit_type == "workflow":
        should_not_trigger = [
            f"Can you explain the theory behind {c_topic}? I need to understand why it works, not how to do it.",
            f"Write a comparison of different approaches to {c_topic} — I need pros and cons, not steps to follow.",
            f"What's the history of {c_topic} and how has it evolved over the decades?",
            f"I need to train new employees on {c_topic} — create a learning curriculum, not a process guide.",
            f"Summarize the key concepts of {c_topic} for a newsletter article.",
        ]
    else:  # framework
        should_not_trigger = [
            f"Tell me about {c_topic} in general — I just want background knowledge, not an assessment framework.",
            f"Write a definition and overview of {c_topic} for a glossary entry.",
            f"What are people saying about {c_topic} in the news recently? I need a media summary.",
            f"Help me calculate the budget impact of {c_topic} — I need numbers, not a structured evaluation.",
            f"Draft a meeting invitation about our {c_topic} initiative for next Thursday.",
        ]

    # ── Boundary cases: should generate clarification, NOT direct trigger ─
    boundary_cases = [
        f"I've heard about {c_topic} but I'm not sure if it applies to my specific situation with a small team and limited budget.",
        f"This is related to {c_topic}, but I actually need help with a completely different aspect — the financial planning side.",
        f"I think I might need something involving {c_topic}, but my context is very different from the typical use case. Can you help me figure out if it fits?",
    ]

    return {
        "should_trigger": should_trigger[:5],
        "should_not_trigger": should_not_trigger[:5],
        "boundary_cases": boundary_cases[:3],
    }


def _generate_framework_should_trigger(trigger_scenario: str, top_concepts: list[str], unit_name: str) -> list[str]:
    """Generate natural should-trigger tests for framework units.

    Uses the trigger scenario (problem situation) as the basis,
    paraphrasing it into natural user language.
    """
    # Extract the core activity from the trigger scenario
    # Trigger scenarios look like: "When needing to assess or evaluate aspects related to X, Y, Z"
    # or "When planning or strategizing around X, Y, Z"
    scenario_lower = trigger_scenario.lower()

    # Extract domain concepts for embedding
    c = top_concepts[:3] if top_concepts else []
    # Filter out any remaining noise
    c = [w for w in c if w not in _GENERIC_MATCH_NOISE and len(w) > 3][:3]
    if not c:
        c = ["this area", "our approach"]
    c_str = " and ".join(c[:2]) if len(c) >= 2 else c[0]

    # Detect the activity type from trigger scenario
    if "assess" in scenario_lower or "evaluat" in scenario_lower:
        return [
            f"I need to evaluate our approach to {c_str} for an upcoming project. What dimensions should I consider?",
            f"I'm preparing a strategic assessment involving {c[0]} and want to make sure I cover the right angles systematically.",
            f"How should I structure my evaluation of {c_str}? I need a thorough approach for a board presentation.",
            f"I want to apply a rigorous assessment to {c[0]} in our organization. Where do I start?",
            f"My team needs to evaluate {c_str} from multiple perspectives before making an investment decision.",
        ]
    elif "plan" in scenario_lower or "strategiz" in scenario_lower:
        return [
            f"I'm developing a strategy around {c_str} and need a structured way to think about it.",
            f"We need to plan our approach to {c[0]} for the next fiscal year. What framework should guide this?",
            f"How should I structure a roadmap for {c_str}? I need to present it to leadership.",
            f"I want to create a systematic plan for {c[0]} adoption in our department.",
            f"My organization needs a phased approach to {c_str}. What should we consider at each stage?",
        ]
    elif "implement" in scenario_lower or "set up" in scenario_lower:
        return [
            f"I need to set up {c_str} in our team. What's the recommended approach?",
            f"We're about to implement {c[0]} and I want to make sure we follow best practices.",
            f"How do I go about deploying {c_str} in a mid-size organization?",
            f"I've been tasked with getting {c[0]} operational. What structured approach should I follow?",
            f"My team needs to implement {c_str} — what are the key steps and considerations?",
        ]
    elif "analyz" in scenario_lower or "understand" in scenario_lower:
        return [
            f"I need to analyze {c_str} for a client project. What framework should I use?",
            f"I'm trying to understand the key dimensions of {c[0]} for a strategic review.",
            f"How should I structure my analysis of {c_str}? I need to identify the critical factors.",
            f"I want to systematically assess {c[0]} capabilities in our current setup.",
            f"My team needs to evaluate {c_str} before we commit to a direction.",
        ]
    elif "risk" in scenario_lower or "govern" in scenario_lower:
        return [
            f"I need to assess the risks around {c_str} before we proceed. What should I look for?",
            f"We're developing governance for {c[0]} and need a structured framework to follow.",
            f"How should I approach risk management for {c_str} in our organization?",
            f"I want to establish clear guidelines for {c[0]} — what dimensions need addressing?",
            f"My team needs to evaluate {c_str} compliance before our audit next month.",
        ]
    else:
        # Generic but still domain-aware
        return [
            f"I need a structured approach to {c_str} for an important project. What should I consider?",
            f"I'm working on {c[0]} and want to make sure I'm covering all the right angles.",
            f"How should I structure my approach to {c_str}? I need something systematic.",
            f"I want to apply a rigorous method to {c[0]} in our organization.",
            f"My team needs to address {c_str} comprehensively. What framework would help?",
        ]


def _extract_domain_topic(domain_words: list[str], unit_type: str) -> str:
    """Extract the most domain-specific topic from word list."""
    # Filter out very generic words
    specific = [w for w in domain_words if w not in _GENERIC_MATCH_NOISE and len(w) > 3]
    if specific:
        return specific[0]
    return "this domain"


def _paraphrase_trigger(scenario: str, domain_words: list[str]) -> str:
    """Transform a trigger scenario into natural user language."""
    # Remove "When needing to:" prefix patterns
    cleaned = scenario
    for prefix in ["when needing to:", "when needing to", "when working on:", "when working on",
                   "a task directly involving:", "when:"]:
        if cleaned.lower().startswith(prefix):
            cleaned = cleaned[len(prefix):].strip()
            break

    # Wrap in natural user request
    templates = [
        f"I need to {cleaned.lower()} for an upcoming project. Where should I start?",
        f"My organization wants to {cleaned.lower()}. What structured approach should we follow?",
        f"I've been asked to {cleaned.lower()}. Can you walk me through it step by step?",
    ]
    # Pick based on hash for variety
    idx = hash(scenario) % len(templates)
    return templates[idx]


def _extract_core_action(purpose: str) -> str:
    """Extract the core action phrase from a purpose statement."""
    # Remove common prefixes
    for prefix in ["execute a", "follow a", "apply the", "when needing to", "diagnostic checklist"]:
        if purpose.lower().startswith(prefix):
            return purpose[len(prefix):].strip()[:60]
    return purpose[:60]


def run_decoy_test(unit: dict, test_cases: dict | None = None) -> dict:
    """Run decoy tests against a unit's trigger logic.

    Per-category scoring:
    - should_trigger: natural cases must trigger (target >= 80%)
    - should_not_trigger: hard negatives must NOT trigger (target >= 80%)
    - boundary_cases: must NOT directly trigger (do_not_trigger or maybe with clarification)

    Returns test results with per-category pass rates and overall assessment.
    """
    from datetime import datetime

    if test_cases is None:
        test_cases = generate_decoy_tests(unit)

    results = {
        "should_trigger": [],
        "should_not_trigger": [],
        "boundary_cases": [],
        "pass_rate": 0.0,
        "category_rates": {},
        "last_tested_at": datetime.now().isoformat(),
    }

    # Test should-trigger cases (must trigger or maybe)
    st_passed = 0
    for case in test_cases.get("should_trigger", []):
        decisions = evaluate_triggers(case, [unit])
        hit = decisions and decisions[0].decision in ("trigger", "maybe")
        results["should_trigger"].append({"case": case, "passed": hit})
        if hit:
            st_passed += 1

    # Test should-NOT-trigger cases (hard negatives must NOT trigger)
    sn_passed = 0
    for case in test_cases.get("should_not_trigger", []):
        decisions = evaluate_triggers(case, [unit])
        hit = decisions and decisions[0].decision == "do_not_trigger"
        results["should_not_trigger"].append({"case": case, "passed": hit})
        if hit:
            sn_passed += 1

    # Boundary cases: must NOT directly trigger.
    # Acceptable: do_not_trigger OR maybe with clarification.
    # NOT acceptable: direct "trigger" without clarification.
    bc_passed = 0
    for case in test_cases.get("boundary_cases", []):
        decisions = evaluate_triggers(case, [unit])
        if decisions:
            d = decisions[0]
            # Pass if: do_not_trigger, or maybe with clarification question
            passed = d.decision == "do_not_trigger" or (d.decision == "maybe" and d.clarification_question)
            # Direct "trigger" without clarification = FAIL
            if d.decision == "trigger" and not d.clarification_question:
                passed = False
        else:
            passed = True  # No decision = not triggered = pass
        results["boundary_cases"].append({"case": case, "passed": passed})
        if passed:
            bc_passed += 1

    # Per-category rates
    st_total = len(test_cases.get("should_trigger", []))
    sn_total = len(test_cases.get("should_not_trigger", []))
    bc_total = len(test_cases.get("boundary_cases", []))

    st_rate = st_passed / st_total if st_total > 0 else 0.0
    sn_rate = sn_passed / sn_total if sn_total > 0 else 0.0
    bc_rate = bc_passed / bc_total if bc_total > 0 else 0.0

    results["category_rates"] = {
        "should_trigger": round(st_rate, 2),
        "should_not_trigger": round(sn_rate, 2),
        "boundary_cases": round(bc_rate, 2),
    }

    # Overall pass rate (weighted: negatives and boundaries matter more)
    total = st_total + sn_total + bc_total
    passed_total = st_passed + sn_passed + bc_passed
    results["pass_rate"] = passed_total / total if total > 0 else 0.0

    return results


# ── Problem shape detection ─────────────────────────────────────────────

# Problem shapes: what KIND of answer does the task need?
_PROBLEM_SHAPES = {
    "explain": ["explain", "what is", "what are", "define", "describe", "tell me about",
                "介绍", "什么是", "解释", "定义", "history", "overview", "summary"],
    "execute": ["implement", "apply", "follow", "execute", "carry out", "run", "deploy",
                "adopt", "set up", "build", "create", "develop", "design", "prepare",
                "制定", "实施", "执行", "应用", "采用", "落地", "部署"],
    "evaluate": ["assess", "evaluate", "determine", "judge", "measure", "analyze",
                 "compare", "review", "audit", "check", "validate", "verify",
                 "qualify", "classify", "categorize", "diagnose", "tell the difference",
                 "not sure if", "is it", "whether",
                 "评估", "判断", "分析", "审核", "检验", "评价", "分类", "诊断"],
    "decide": ["decide", "choose", "select", "prioritize", "should i", "which",
               "决定", "选择", "优先"],
    "plan": ["plan", "roadmap", "strategy", "schedule", "timeline", "organize",
             "规划", "路线图", "策略", "排期"],
}

# Which unit types serve which problem shapes
_UNIT_TYPE_SHAPES = {
    "workflow": {"execute", "plan"},
    "framework": {"evaluate", "plan", "decide"},
    "diagnostic": {"evaluate", "decide"},
    "decision_rule": {"decide", "evaluate"},
    "principle": {"explain", "evaluate"},
    "checklist": {"evaluate", "execute"},
}


def _detect_problem_shape(text: str) -> set[str]:
    """Detect what problem shape(s) a task requires.

    Handles negation: 'not a framework', 'not an assessment' should NOT
    add 'evaluate' shape. Only the MAIN intent counts.
    """
    text_lower = text.lower()
    shapes = set()

    # EXPLAIN-DOMINANT: if the text starts with explain patterns, it's primarily explain
    # even if it mentions 'assessment' or 'framework' in a negated context
    _EXPLAIN_DOMINANT = ["tell me about", "explain", "what is", "what are", "define",
                         "describe", "history of", "overview of", "summary of",
                         "write a definition", "write a summary", "write a comparison",
                         "draft a meeting", "draft an email", "calculate the",
                         "help me calculate", "help me compute", "build a financial",
                         "介绍", "什么是", "解释", "定义"]
    # Chinese explain patterns use substring match (no word boundaries in Chinese)
    _ZH_EXPLAIN_SUBSTR = ["写一篇", "帮我写", "科普文章", "发展史", "请帮我写",
                          "写一篇文章", "撰写", "综述", "概述"]
    is_explain_dominant = any(text_lower.startswith(p) or f". {p}" in text_lower for p in _EXPLAIN_DOMINANT)
    if not is_explain_dominant:
        is_explain_dominant = any(p in text_lower for p in _ZH_EXPLAIN_SUBSTR)

    if is_explain_dominant:
        shapes.add("explain")
        # Only add other shapes if there's a CLEAR secondary intent
        # (not just the word appearing in a negated phrase)
        # Check first 60 chars for additional intents (main clause)
        main_clause = text_lower[:60]
        for shape, keywords in _PROBLEM_SHAPES.items():
            if shape == "explain":
                continue
            if any(kw in main_clause for kw in keywords):
                shapes.add(shape)
        return shapes

    for shape, keywords in _PROBLEM_SHAPES.items():
        if any(kw in text_lower for kw in keywords):
            shapes.add(shape)
    if not shapes:
        shapes.add("execute")  # default: assume user wants to do something
    return shapes


def _unit_serves_shapes(unit: dict) -> set[str]:
    """Determine what problem shapes a unit can serve."""
    unit_type = unit.get("type", "framework")
    shapes = _UNIT_TYPE_SHAPES.get(unit_type, {"execute", "evaluate"})
    # Also check purpose text for additional shape signals
    purpose = unit.get("purpose", "").lower()
    for shape, keywords in _PROBLEM_SHAPES.items():
        if any(kw in purpose for kw in keywords):
            shapes.add(shape)
    return shapes


# ── Internal evaluation ───────────────────────────────────────────────────


def _evaluate_single_unit(task: str, parsed: dict, unit: dict) -> TriggerDecision:
    """Evaluate a single unit against a parsed task.

    Matching requires BOTH:
    - Domain/topic overlap (what the task is about)
    - Problem shape compatibility (what kind of answer is needed)

    Topic-similar but problem-shape-different → do NOT strong-trigger.
    """
    unit_id = unit.get("id", "")
    task_lower = task.lower()
    score = 0.0
    matched_signals = []
    missing_context = []
    anti_trigger_hits = []

    # 0. Problem shape check (hard gate for strong trigger)
    task_shapes = _detect_problem_shape(task_lower)
    unit_shapes = _unit_serves_shapes(unit)
    shape_compatible = bool(task_shapes & unit_shapes)

    # If task is purely "explain" and unit is "execute" type → strong mismatch
    explain_only = task_shapes == {"explain"}
    unit_is_execute = unit.get("type", "") in ("workflow", "checklist")
    if explain_only and unit_is_execute:
        return TriggerDecision(
            unit_id=unit_id,
            decision="do_not_trigger",
            score=0.0,
            reason="Task asks for explanation/definition, but this unit is an executable process. Problem shape mismatch.",
        )

    # Framework/diagnostic units also should NOT trigger for pure explain tasks
    # "Tell me about X" ≠ "Help me evaluate/apply X"
    unit_is_framework = unit.get("type", "") in ("framework", "diagnostic")
    if explain_only and unit_is_framework:
        return TriggerDecision(
            unit_id=unit_id,
            decision="do_not_trigger",
            score=0.0,
            reason="Task asks for explanation/background, but this unit serves evaluation/application. Problem shape mismatch: explain vs evaluate/apply.",
        )

    # 1. Check anti-triggers (hard gate — requires STRONG overlap)
    for at in unit.get("anti_triggers", []):
        scenario = at.get("scenario", "").lower()
        if scenario and _strong_anti_trigger_overlap(scenario, task_lower):
            anti_trigger_hits.append(at.get("scenario", ""))

    if anti_trigger_hits:
        return TriggerDecision(
            unit_id=unit_id,
            decision="do_not_trigger",
            score=0.0,
            anti_trigger_hits=anti_trigger_hits,
            reason=f"Anti-trigger matched: {anti_trigger_hits[0]}",
        )

    # 2. Domain/topic matching (broad — improves recall)
    domain_score = 0.0

    # 2a. Trigger scenario match (min_overlap=1: scenarios are short, 1 domain word is meaningful)
    for trig in unit.get("triggers", []):
        scenario = trig.get("scenario", "").lower()
        signals = [s.lower() for s in trig.get("signals", [])]

        if scenario and _semantic_overlap(scenario, task_lower, min_overlap=1):
            domain_score += 3.0
            matched_signals.append(f"scenario: {trig.get('scenario', '')[:60]}")

        # Signal keyword match
        for sig in signals:
            if sig and sig in task_lower:
                domain_score += 1.5
                matched_signals.append(f"signal: {sig}")

        # Required context check
        for ctx in trig.get("required_context", []):
            if ctx and ctx.lower() not in task_lower:
                missing_context.append(ctx)

    # 2b. Purpose overlap (min_overlap=1: purpose describes the problem the unit solves)
    purpose = unit.get("purpose", "").lower()
    if purpose and _semantic_overlap(purpose, task_lower, min_overlap=1):
        domain_score += 2.0
        matched_signals.append("purpose overlap")

    # 2c. Name keyword overlap
    name = unit.get("name", "").lower()
    name_words = set(re.findall(r"\b[a-z]{4,}\b", name))
    task_words = set(re.findall(r"\b[a-z]{4,}\b", task_lower))
    name_overlap = name_words & task_words
    if name_overlap:
        domain_score += min(len(name_overlap) * 0.5, 1.5)
        matched_signals.append(f"name keywords: {', '.join(list(name_overlap)[:3])}")

    # 2d. Evidence/domain keyword expansion (improves recall)
    # Extract domain keywords from evidence and check against task
    # IMPORTANT: Only count DOMAIN-SPECIFIC words, not generic ones
    evidence_text = " ".join(s.get("text", "") for s in unit.get("evidence_spans", []))[:500].lower()
    evidence_words = _normalize_words(evidence_text)
    task_stems = _normalize_words(task_lower)
    evidence_overlap = evidence_words & task_stems
    # Require at least 2 specific domain overlaps (not just generic words)
    if len(evidence_overlap) >= 2:
        # Cap contribution to prevent long-task inflation
        domain_bonus = min(len(evidence_overlap) * 0.5, 1.5)
        domain_score += domain_bonus
        matched_signals.append(f"evidence domain overlap: {', '.join(list(evidence_overlap)[:3])}")

    # 2e. Diagnostic questions relevance (min_overlap=1: questions are specific)
    for q in unit.get("diagnostic_questions", []):
        if q and _semantic_overlap(q.lower(), task_lower, min_overlap=1):
            domain_score += 0.5
            matched_signals.append("diagnostic relevance")

    # 2f. CONCEPT MATCHING: compare task against unit's core domain vocabulary
    # This is the KEY improvement: instead of only matching trigger text,
    # we match the task against the unit's entire concept space.
    concept_score = _concept_match(task_lower, unit)
    if concept_score > 0:
        domain_score += concept_score
        matched_signals.append(f"concept match (+{concept_score:.1f})")

    # 3. Problem shape bonus/penalty
    # Length normalization: prevent long tasks from inflating scores
    # A 50-word task should not score higher than a 15-word task just because
    # it contains more generic words that happen to overlap.
    task_word_count = len(task_lower.split())
    length_factor = 1.0 if task_word_count <= 25 else 25.0 / task_word_count * 1.5  # Diminishing returns for long tasks

    if shape_compatible:
        score += domain_score * length_factor
        if len(task_shapes & unit_shapes) >= 2:
            score += 1.0  # Strong shape alignment bonus
            matched_signals.append("strong problem-shape alignment")
    else:
        # Shape incompatible — heavily discount domain match
        score += domain_score * 0.3 * length_factor
        matched_signals.append("⚠️ problem-shape mismatch (discounted)")

    # 4. Missing context penalty
    if missing_context:
        score -= len(missing_context) * 0.5

    # Determine decision
    if score >= 4.0 and shape_compatible:
        decision = "trigger"
        reason = f"Strong match: domain + problem shape aligned ({len(matched_signals)} signals)."
    elif score >= 2.0:
        decision = "maybe"
        reason = f"Partial match ({len(matched_signals)} signals)." + ("" if shape_compatible else " Problem shape partially incompatible.")
    else:
        decision = "do_not_trigger"
        reason = "Insufficient relevance to task."

    # UNCERTAINTY DETECTION: if the task contains uncertainty/hedging language,
    # downgrade to "maybe" with clarification (boundary case handling)
    _UNCERTAINTY_PHRASES = [
        "not sure if", "not sure whether", "might need", "might be",
        "i think i", "heard about", "very different from",
        "don't know if", "no idea if", "unclear if",
        # Boundary/redirect patterns: user acknowledges topic but needs something else
        "this is related to", "but i actually need", "completely different aspect",
        "different aspect", "but my context is", "not what i need",
        "i need help with a", "but i need",
        # Redirect patterns: user mentions topic but wants a DIFFERENT deliverable
        "i just need", "but honestly", "keep hearing about",
        "i don't really need", "not looking for",
        "不确定", "可能", "也许", "听说",
    ]
    has_uncertainty = any(p in task_lower for p in _UNCERTAINTY_PHRASES)

    # If missing context and would otherwise trigger, generate clarification
    clarification = ""
    if missing_context and decision in ("trigger", "maybe"):
        decision = "maybe"
        clarification = f"To apply this method, I need to know: {missing_context[0]}"
        reason += f" Missing context: {', '.join(missing_context[:2])}"

    # Uncertainty downgrade (after missing context check)
    if has_uncertainty and decision in ("trigger", "maybe"):
        decision = "maybe"
        clarification = f"It sounds like you're not sure if this method fits your context. Could you describe your specific situation so I can determine if it applies?"
        reason += " User expressed uncertainty — clarification needed before triggering."

    return TriggerDecision(
        unit_id=unit_id,
        decision=decision,
        score=score,
        matched_signals=matched_signals,
        missing_context=missing_context,
        anti_trigger_hits=anti_trigger_hits,
        reason=reason,
        clarification_question=clarification,
    )


def _stem(word: str) -> str:
    """Minimal English stemming for trigger matching."""
    # Order matters: longest suffixes first
    for suffix in ("ation", "tion", "ing", "ies", "ied", "es", "ed", "ly", "s"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            return word[: -len(suffix)]
    return word


# Generic words that appear in anti-trigger templates but carry no domain signal
_ANTI_TRIGGER_NOISE = {
    "task", "domain", "process", "match", "method", "apply", "use", "work",
    "relate", "involv", "context", "specific", "general", "problem", "shape",
    "framework", "assumption", "hold", "unrelated", "differ",
    # Additional: common in both positive and anti-trigger templates
    "assess", "evaluat", "determin", "check", "verify", "analyz",
    "explain", "describe", "define", "understand", "learn",
    "concept", "conceptual", "means", "ask", "question",
    "system", "tool", "platform", "software", "solution",
    "automat", "intelligen", "artificial", "machine",
    "beyond", "outside", "within", "scope", "boundary",
}

# Generic words that should NOT contribute to domain matching scores.
# These appear in almost any task description and inflate scores for long tasks.
_GENERIC_MATCH_NOISE = {
    "step", "next", "system", "task", "project", "work", "need", "want",
    "help", "process", "method", "approach", "tool", "team", "time",
    "data", "result", "output", "input", "user", "case", "part", "set",
    "get", "make", "take", "give", "find", "keep", "let", "put", "run",
    "use", "try", "see", "way", "day", "new", "one", "two", "also",
    "can", "will", "should", "would", "could", "may", "might", "must",
    "about", "into", "from", "with", "that", "this", "what", "when",
    "how", "which", "where", "who", "why", "than", "then", "them",
    "have", "has", "had", "are", "was", "were", "been", "being",
    "not", "but", "and", "for", "the", "all", "any", "each",
    "structur", "organ", "manag", "develop", "implement", "creat",
    "provid", "includ", "follow", "base", "relat", "support",
    # Additional noise: common in PDF extraction and task descriptions
    "these", "those", "there", "their", "without", "within", "between",
    "through", "during", "before", "after", "other", "more", "most",
    "some", "such", "very", "just", "only", "still", "already",
    "instructions", "questions", "question", "answer", "answers",
    "example", "examples", "following", "above", "below", "here",
    "while", "because", "since", "until", "does", "done", "doing",
    "specific", "general", "particular", "different", "similar",
    "ability", "capabilities", "capability", "features", "feature",
    "using", "used", "uses", "able", "many", "much", "well",
    "current", "upcoming", "several", "various", "multiple",
    "key", "main", "important", "relevant", "available",
    # Domain-generic words that are too broad for matching
    "first", "second", "third", "last", "previous",
    "page", "section", "chapter", "content", "information",
    "decision", "making", "decisions", "situation", "situations",
    "inform", "technology", "technologies", "impact", "modern",
    "value", "values", "getting", "got", "good", "best",
    "people", "person", "company", "organization", "business",
    "world", "life", "year", "times", "thing", "things",
    "possible", "potential", "likely", "certain", "clear",
    "however", "therefore", "thus", "hence", "although",
    "solutions", "solution", "public", "private", "internal",
    "large", "small", "high", "low", "long", "short", "new", "old",
    # PDF extraction artifacts and overly broad single words
    "moore", "gordon", "intel", "salesperson", "accountant",
    "variou", "various", "requir", "require", "requires",
    "repository", "uncertainty", "shelf",
    "patterns", "pattern",
    "responses", "relevant", "professionals", "delays",
    "computing", "roughly", "double", "speed", "profound",
    "description", "observed", "workforce", "impact",
    # Remaining noise: overly broad or stemmed fragments
    "three", "observ", "concern", "concerns", "utiliz",
    "appropriate", "appropriately", "solu",
    "aspect", "aspects", "element", "elements",
    "general", "background", "knowledge", "initiative",
    "budget", "financial", "meeting", "invitation",
    "news", "media", "summary", "definition", "glossary",
    "calculate", "numbers",
    "legitimate", "legitim", "supervis", "filter", "filtering",
}


def _normalize_words(text: str) -> set[str]:
    """Extract meaningful words with basic stemming, excluding generic noise.

    Also bridges Chinese domain terms to English equivalents for cross-lingual matching.
    """
    raw = set(re.findall(r"\b[a-z]{3,}\b", text.lower()))
    stopwords = {"the", "and", "for", "are", "but", "not", "you", "this", "that",
                 "with", "from", "have", "will", "can", "what", "when", "how",
                 "need", "want", "should", "would", "could", "about", "into"}
    meaningful = raw - stopwords
    stemmed = {_stem(w) for w in meaningful}
    # Also remove generic noise words (after stemming)
    result = stemmed - _GENERIC_MATCH_NOISE

    # Chinese-English concept bridge: add English equivalents for Chinese terms
    # Check if any known Chinese term appears in the text (direct substring match)
    # Bridge words are stemmed to ensure consistent matching with stemmed scenario text
    if re.search(r"[\u4e00-\u9fff]", text):
        for zh, en in _ZH_EN_CONCEPT_BRIDGE.items():
            if zh in text:
                result.update({_stem(w) for w in en} - _GENERIC_MATCH_NOISE)

    return result


# Chinese-to-English concept bridge for cross-lingual trigger matching
_ZH_EN_CONCEPT_BRIDGE = {
    # AI/ML core concepts
    "机器学习": {"machine", "learning", "ml"},
    "深度学习": {"deep", "learning", "neural"},
    "神经网络": {"neural", "network", "deep"},
    "人工智能": {"artificial", "intelligence", "ai"},
    "预测分析": {"predictive", "analytics", "prediction"},
    "自然语言": {"natural", "language", "nlp"},
    "生成式": {"generative", "genai", "generation"},
    "大语言模型": {"language", "model", "llm"},
    # Actions/capabilities
    "自动化": {"automated", "automation", "automatic"},
    "智能化": {"intelligent", "intelligence", "smart"},
    "规则引擎": {"rules", "automated", "coded"},
    "决策": {"decision", "decide", "decisions"},
    "评估": {"assess", "evaluate", "evaluation"},
    "判断": {"determine", "judge", "classify"},
    "分类": {"classify", "categorize", "category"},
    "诊断": {"diagnos", "diagnostic", "assess"},
    # Application contexts
    "项目管理": {"project", "management", "pm"},
    "风险管理": {"risk", "management", "governance"},
    "内部文档": {"internal", "documents", "proprietary", "retrieval", "augmented"},
    "内部资料": {"internal", "documents", "proprietary", "retrieval", "augmented", "generation"},
    "知识库": {"knowledge", "base", "repository", "retrieval"},
    "检索增强": {"retrieval", "augmented", "rag"},
    "供应商": {"vendor", "supplier", "tool"},
    "客服系统": {"system", "service", "chatbot"},
    "数据分析": {"data", "analytics", "analysis"},
    # RAG-implies patterns: user wants AI to answer from internal docs
    "基于这些内部": {"retrieval", "augmented", "generation", "rag"},
    "基于内部": {"retrieval", "augmented", "generation", "rag"},
    "ai助手": {"ai", "assistant", "system", "intelligent"},
    "技术规范": {"technical", "documents", "specifications"},
    "操作手册": {"documents", "manuals", "proprietary"},
    # Project-management / planning terms (general business Chinese)
    "项目": {"project", "projects"},
    "风险": {"risk", "risks"},
    "预测": {"predictive", "prediction", "forecast", "predict"},
    "排期": {"scheduling", "schedule", "timeline"},
    "进度": {"scheduling", "schedule", "timeline", "progress"},
    "资源": {"resource", "resources", "allocation"},
    "分配": {"allocation", "allocate", "resource"},
    "路线图": {"roadmap", "plan", "strategy", "planning"},
    "采用": {"adoption", "adopt", "implement"},
    "转型": {"transformation", "digital", "change"},
    "伦理": {"ethics", "ethical", "governance", "responsible"},
    "变革管理": {"change", "management", "transformation"},
    "董事会": {"board", "stakeholder", "leadership", "executive"},
    "汇报": {"report", "present", "presentation", "board"},
    "建筑": {"construction", "building"},
    "施工": {"construction", "building"},
}


def _strong_anti_trigger_overlap(anti_trigger_text: str, task_text: str) -> bool:
    """Anti-trigger requires STRONGER evidence than positive trigger.

    Generic anti-trigger phrases like 'task domain doesn't match this process'
    should NOT block real tasks. Require at least 3 domain-specific word overlaps
    (excluding generic template words) to prevent false blocking.
    """
    stems_at = _normalize_words(anti_trigger_text)
    stems_task = _normalize_words(task_text)

    # Remove generic noise words from anti-trigger
    specific_at = stems_at - _ANTI_TRIGGER_NOISE
    specific_task = stems_task - _ANTI_TRIGGER_NOISE

    if not specific_at or not specific_task:
        # Anti-trigger is entirely generic — never block
        return False

    overlap = specific_at & specific_task
    # Need at least 3 domain-specific overlaps for anti-trigger to fire
    # (raised from 2 to prevent false blocking when domain words appear in both)
    return len(overlap) >= 3


def _semantic_overlap(text_a: str, text_b: str, min_overlap: int = 2) -> bool:
    """Check if two texts have meaningful word overlap (with stemming).

    Requires at least `min_overlap` domain-specific word overlaps to prevent
    long tasks from matching everything via generic words.
    Supports cross-lingual matching via Chinese-English concept bridge.
    """
    stems_a = _normalize_words(text_a)
    stems_b = _normalize_words(text_b)

    # Also check Chinese phrases
    zh_a = set(re.findall(r"[\u4e00-\u9fff]{2,4}", text_a))
    zh_b = set(re.findall(r"[\u4e00-\u9fff]{2,4}", text_b))

    if not stems_a or not stems_b:
        return len(zh_a & zh_b) >= 1

    overlap = stems_a & stems_b
    zh_overlap = zh_a & zh_b
    return len(overlap) >= min_overlap or len(zh_overlap) >= 1


def _concept_match(task_lower: str, unit: dict) -> float:
    """Concept-based matching: compare task against unit's core domain vocabulary.

    Instead of relying only on trigger scenario text overlap, this builds
    a 'concept space' from the unit's diagnostic questions, evidence, and
    execution steps, then checks if the task operates in the same concept space.

    Returns a score bonus (0.0 to 3.0).
    """
    # Build unit concept vocabulary from multiple fields
    concept_sources = []
    for q in unit.get("diagnostic_questions", []):
        concept_sources.append(q.lower())
    for span in unit.get("evidence_spans", [])[:2]:
        concept_sources.append(span.get("text", "")[:200].lower())
    for step in unit.get("execution_steps", [])[:4]:
        concept_sources.append(step.lower())
    # Purpose is a strong concept signal
    concept_sources.append(unit.get("purpose", "").lower())

    concept_text = " ".join(concept_sources)
    concept_words = _normalize_words(concept_text)
    task_words = _normalize_words(task_lower)

    if not concept_words or not task_words:
        return 0.0

    overlap = concept_words & task_words

    # Require at least 2 concept overlaps for a meaningful match
    if len(overlap) >= 3:
        return 2.5  # Strong concept alignment
    elif len(overlap) >= 2:
        return 1.5  # Moderate concept alignment
    elif len(overlap) >= 1:
        return 0.5  # Weak signal
    return 0.0


def _parse_task_light(task: str) -> dict:
    """Lightweight task parsing for trigger evaluation."""
    task_lower = task.lower()
    return {
        "topic": task_lower,
        "intent": _detect_intent(task_lower),
        "has_topic": len(task_lower) >= 15 and not is_vague_task(task),
    }


def _detect_intent(task_lower: str) -> str:
    """Detect output intent from task."""
    intents = {
        "proposal": ["proposal", "report", "报告", "提案"],
        "meeting": ["meeting", "discussion", "会议", "讨论"],
        "cpd": ["cpd", "reflection", "反思", "学习"],
        "analysis": ["analyze", "evaluate", "assess", "分析", "评估"],
        "decision": ["decide", "choose", "决定", "选择"],
    }
    for intent, keywords in intents.items():
        if any(kw in task_lower for kw in keywords):
            return intent
    return "general"


def _generate_clarification(task: str) -> str:
    """Generate a minimal clarification question for vague tasks."""
    task_lower = task.lower()
    if any(w in task_lower for w in ["proposal", "提案", "报告", "report"]):
        return "What is the specific topic or subject of this proposal/report? (e.g., AI governance, sustainability, client project)"
    if any(w in task_lower for w in ["meeting", "会议", "讨论"]):
        return "What is the meeting about? Please describe the topic or decision to be discussed."
    return "Please describe the specific topic, problem, or subject you're working on. I need this to find the right method to activate."
