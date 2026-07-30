"""Deep Distill pipeline for RecallBite 记忆面包.

Extracts candidate Activation Units from methodology-dense material.
Uses LLM when available, falls back to deterministic extraction.

This module does NOT implement five-agent orchestration.
It uses section-aware whole-document extraction with validation gates.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from src.activation_unit import (
    create_empty_unit,
    validate_distinctiveness,
    validate_evidence,
    validate_for_active,
)
from src.llm_client import create_llm_client


# ── Public API ────────────────────────────────────────────────────────────


@dataclass
class SectionInfo:
    """Metadata about a document section."""
    title: str
    start_char: int
    end_char: int
    page_start: int = 0
    page_end: int = 0
    candidate_count: int = 0
    rejected_reasons: list[str] = field(default_factory=list)


@dataclass
class DistillResult:
    """Result of whole-document deep distillation."""
    candidates: list[dict]
    section_map: list[SectionInfo]
    total_chars: int = 0
    sections_processed: int = 0
    total_extracted: int = 0  # candidates found before merge/limit (for reject/merge reporting)


def deep_distill_document(
    text: str,
    document_id: str = "",
    source_title: str = "",
    output_language: str = "auto",
) -> DistillResult:
    """Section-aware whole-document distillation.

    1. Split document into sections by headings/pages.
    2. Extract candidates from EACH section independently.
    3. Document-level merge and deduplication.
    4. Return candidates + section coverage report.
    """
    sections = _split_into_sections(text)
    all_candidates: list[dict] = []
    section_map: list[SectionInfo] = []

    for sec in sections:
        sec_text = text[sec["start"]:sec["end"]]
        if len(sec_text.strip()) < 200:
            continue  # Skip very short sections (TOC, headers)

        # Extract from this section
        candidates = _extract_deterministic(
            sec_text, document_id, source_title, output_language,
            page_offset=sec.get("page", 0),
        )

        info = SectionInfo(
            title=sec["title"],
            start_char=sec["start"],
            end_char=sec["end"],
            page_start=sec.get("page", 0),
            candidate_count=len(candidates),
        )

        # Tag each candidate with source section
        for c in candidates:
            c["_source_section"] = sec["title"]
            c["_source_page"] = sec.get("page", 0)
            # Add page to evidence location
            for span in c.get("evidence_spans", []):
                if not span.get("location"):
                    span["location"] = f"Page {sec.get('page', '?')}, Section: {sec['title'][:50]}"

        all_candidates.extend(candidates)
        section_map.append(info)

    # Document-level redundancy merge
    total_extracted = len(all_candidates)
    all_candidates = _merge_redundant_candidates(all_candidates)

    # Limit to 5 best candidates (by completeness)
    all_candidates.sort(key=_completeness_score, reverse=True)
    all_candidates = all_candidates[:5]

    return DistillResult(
        candidates=all_candidates,
        section_map=section_map,
        total_chars=len(text),
        sections_processed=len(section_map),
        total_extracted=total_extracted,
    )


def deep_distill(
    text: str,
    document_id: str = "",
    source_title: str = "",
    output_language: str = "auto",
    meta_out: dict | None = None,
) -> list[dict]:
    """Extract 3-5 candidate Activation Units from material.

    For short texts (<5000 chars), processes directly.
    For longer texts, uses section-aware processing.

    Args:
        meta_out: optional dict to receive processing metadata
            (sections_processed, total_chars, total_extracted, rejected_count).

    Returns:
        List of candidate unit dicts (status='draft').
    """
    # Try LLM extraction first
    client = create_llm_client()
    if "AI" in client.mode_label:
        try:
            candidates = _extract_with_llm(client, text, document_id, source_title, output_language)
            if candidates:
                if meta_out is not None:
                    meta_out.update({"sections_processed": 0, "total_chars": len(text),
                                     "total_extracted": len(candidates), "rejected_count": 0})
                return candidates
        except Exception:
            pass  # Fall through to deterministic

    # For longer texts, use section-aware processing
    if len(text) > 5000:
        result = deep_distill_document(text, document_id, source_title, output_language)
        if meta_out is not None:
            meta_out.update({
                "sections_processed": result.sections_processed,
                "total_chars": result.total_chars,
                "total_extracted": result.total_extracted,
                "rejected_count": max(0, result.total_extracted - len(result.candidates)),
            })
        return result.candidates

    # Short text: direct extraction
    candidates = _extract_deterministic(text, document_id, source_title, output_language)
    if meta_out is not None:
        meta_out.update({"sections_processed": 1, "total_chars": len(text),
                         "total_extracted": len(candidates), "rejected_count": 0})
    return candidates


# ── Section Splitting ─────────────────────────────────────────────────────


def _split_into_sections(text: str) -> list[dict]:
    """Split document into sections by page markers and headings.

    Returns list of {title, start, end, page} dicts.
    """
    sections = []
    # Find all section boundaries: [Page N] markers and heading-like lines
    page_re = re.compile(r"\[Page\s*(\d+)\]")
    # Heading patterns: short lines that look like titles
    heading_re = re.compile(
        r"^(?:#{1,3}\s+)?([A-Z][A-Za-z0-9 &/'\-]{3,60})$",
        re.MULTILINE,
    )

    # Primary split: by [Page N] markers
    page_markers = [(m.start(), int(m.group(1))) for m in page_re.finditer(text)]

    if page_markers:
        # Group pages into logical sections (every 3-5 pages or by heading)
        current_start = 0
        # The first section starts at the first real page, not a phantom page 0.
        current_page = page_markers[0][1]
        current_title = "Introduction"

        for i, (pos, page_num) in enumerate(page_markers):
            # Check for heading between last marker and this one
            segment = text[current_start:pos]
            heading_match = heading_re.search(segment)

            if pos - current_start > 3000 or (heading_match and pos - current_start > 1000):
                # Close current section
                if pos - current_start > 200:
                    sections.append({
                        "title": current_title,
                        "start": current_start,
                        "end": pos,
                        "page": current_page,
                    })
                # Start new section
                if heading_match:
                    current_title = heading_match.group(1).strip()
                else:
                    current_title = f"Pages {current_page}-{page_num}"
                current_start = pos
                current_page = page_num
            elif page_num % 5 == 0 and pos - current_start > 2000:
                # Force section break every ~5 pages for long stretches
                sections.append({
                    "title": current_title,
                    "start": current_start,
                    "end": pos,
                    "page": current_page,
                })
                current_title = f"Pages {page_num}+"
                current_start = pos
                current_page = page_num

        # Final section
        if current_start < len(text) - 200:
            sections.append({
                "title": current_title,
                "start": current_start,
                "end": len(text),
                "page": current_page,
            })
    else:
        # No page markers — split by headings or fixed chunks
        headings = [(m.start(), m.group(1).strip()) for m in heading_re.finditer(text)]
        if len(headings) >= 3:
            for i, (pos, title) in enumerate(headings):
                end = headings[i + 1][0] if i + 1 < len(headings) else len(text)
                if end - pos > 200:
                    sections.append({"title": title, "start": pos, "end": end, "page": 0})
        else:
            # Fixed chunks of ~8000 chars
            chunk_size = 8000
            for i in range(0, len(text), chunk_size):
                sections.append({
                    "title": f"Segment {i // chunk_size + 1}",
                    "start": i,
                    "end": min(i + chunk_size, len(text)),
                    "page": 0,
                })

    # Ensure minimum section size — merge tiny sections
    merged = []
    for sec in sections:
        if merged and (sec["end"] - sec["start"]) < 500:
            merged[-1]["end"] = sec["end"]
        else:
            merged.append(sec)

    return merged if merged else [{"title": "Full document", "start": 0, "end": len(text), "page": 0}]


# ── LLM Extraction ───────────────────────────────────────────────────────

_DISTILL_SYSTEM = """You are a knowledge extraction specialist for RecallBite 记忆面包.
Your job is to identify executable methods, frameworks, principles, and decision rules from material.
You extract Activation Units — NOT summaries, NOT generic advice.

An Activation Unit must be:
- Specific enough to execute step by step
- Bounded: clear when to use and when NOT to use
- Evidence-backed: traceable to the source material
- Distinctive: not generic platitudes like "be innovative" or "think long-term"

Output ONLY valid JSON."""

_DISTILL_PROMPT = """Extract 3-5 candidate Activation Units from this material.

Material:
---
{text_sample}
---

Source: {source_title}

Return JSON array where each item has:
{{
  "name": "Short descriptive name",
  "type": "framework | principle | diagnostic | decision_rule | workflow",
  "purpose": "What problem does this solve? When should it be called?",
  "evidence_spans": [{{"text": "exact quote from material", "location": ""}}],
  "triggers": [{{"scenario": "When to use this", "signals": ["signal1", "signal2"], "required_context": ["context needed"]}}],
  "anti_triggers": [{{"scenario": "When NOT to use", "reason": "Why not"}}],
  "diagnostic_questions": ["Question to determine if this applies"],
  "execution_steps": ["Step 1: ...", "Step 2: ...", "Step 3: ..."],
  "boundaries": ["Boundary/precondition/limitation"],
  "quality_checks": ["How to verify correct application"],
  "examples": ["Concrete example from material"],
  "counterexamples": ["When this failed or doesn't apply"]
}}

Rules:
- Extract ONLY methods/frameworks that have concrete steps or decision criteria.
- Do NOT extract generic advice ("communicate well", "be strategic").
- Each unit must have at least 2 execution steps.
- Each unit must have at least 1 anti-trigger.
- Evidence must be actual text from the material.
- If fewer than 3 genuine units exist, return fewer. Do NOT pad with filler.
{lang_hint}
"""


def _extract_with_llm(
    client,
    text: str,
    document_id: str,
    source_title: str,
    output_language: str,
) -> list[dict]:
    """Extract candidates using LLM."""
    # Limit text to first 8000 chars for extraction (keep focused)
    text_sample = text[:8000]

    lang_hints = {
        "zh": "\nWrite all fields in natural Chinese (中文). Keep evidence in original language.",
        "en": "\nWrite all fields in natural English.",
        "bilingual": "\nFor name and purpose, provide both Chinese and English.",
    }
    lang_hint = lang_hints.get(output_language, "")

    prompt = _DISTILL_PROMPT.format(
        text_sample=text_sample,
        source_title=source_title or "Unknown",
        lang_hint=lang_hint,
    )

    content = client._call_chat(_DISTILL_SYSTEM, prompt, temperature=0.3)
    raw_units = client._extract_json(content)

    # Handle both list and wrapped dict
    if isinstance(raw_units, dict):
        raw_units = raw_units.get("units", raw_units.get("activation_units", []))
    if not isinstance(raw_units, list):
        return []

    # Convert to proper unit dicts
    candidates = []
    for raw in raw_units[:5]:
        unit = create_empty_unit()
        unit["name"] = raw.get("name", "")
        unit["type"] = raw.get("type", "framework")
        unit["purpose"] = raw.get("purpose", "")
        unit["status"] = "draft"
        unit["source_document_ids"] = [document_id] if document_id else []

        # Evidence spans
        for span in raw.get("evidence_spans", []):
            if isinstance(span, dict):
                span["document_id"] = document_id
                unit["evidence_spans"].append(span)
            elif isinstance(span, str):
                unit["evidence_spans"].append({"document_id": document_id, "text": span, "location": ""})

        # Triggers
        for trig in raw.get("triggers", []):
            if isinstance(trig, dict):
                unit["triggers"].append(trig)
            elif isinstance(trig, str):
                unit["triggers"].append({"scenario": trig, "signals": [], "required_context": []})

        # Anti-triggers
        for at in raw.get("anti_triggers", []):
            if isinstance(at, dict):
                unit["anti_triggers"].append(at)
            elif isinstance(at, str):
                unit["anti_triggers"].append({"scenario": at, "reason": ""})

        unit["diagnostic_questions"] = raw.get("diagnostic_questions", [])
        unit["execution_steps"] = raw.get("execution_steps", [])
        unit["boundaries"] = raw.get("boundaries", [])
        unit["quality_checks"] = raw.get("quality_checks", [])
        unit["examples"] = raw.get("examples", [])
        unit["counterexamples"] = raw.get("counterexamples", [])

        # Set confidence based on evidence quality
        evidence_count = len(unit["evidence_spans"])
        if evidence_count >= 2 and len(unit["execution_steps"]) >= 3:
            unit["confidence"] = {"level": "high", "reason": "Multiple evidence spans and clear steps."}
        elif evidence_count >= 1:
            unit["confidence"] = {"level": "medium", "reason": "Some evidence found."}
        else:
            unit["confidence"] = {"level": "low", "reason": "Insufficient evidence."}

        candidates.append(unit)

    return candidates


# ── Deterministic Extraction ──────────────────────────────────────────────


# ── List-type classification ─────────────────────────────────────────────

# Action verbs indicating a process step (not just a noun/attribute)
_ACTION_VERBS = re.compile(
    r"\b(?:define|identify|assess|evaluate|determine|analyze|create|design|implement|"
    r"develop|establish|review|validate|verify|select|prioritize|plan|prepare|"
    r"execute|deploy|monitor|measure|improve|optimize|configure|build|test|"
    r"check|confirm|ensure|apply|follow|perform|conduct|complete|deliver|"
    r"define|classify|categorize|map|document|communicate|train|onboard|"
    r"ask|answer|decide|choose|compare|calculate|estimate|predict|"
    r"制定|识别|评估|确定|分析|创建|设计|实施|开发|建立|审查|验证|选择|规划|执行|监控|改进)\b",
    re.IGNORECASE,
)

# Patterns indicating checkable conditions (yes/no verifiable)
_CHECKABLE_PATTERN = re.compile(
    r"(?:^(?:Is|Are|Does|Do|Can|Has|Have|Should|Must)\s|\?$|是否|能否|有没有)",
    re.IGNORECASE,
)


def _classify_list_type(items: list[str], context: str = "") -> str:
    """Classify a list of items into: process | diagnostic | checklist | comparison_table | attributes.

    Classification rules:
    - diagnostic: a set of questions used to DETERMINE STATE or CLASSIFY something
      (questions that assess/categorize, not action steps)
    - process/workflow: items have action verbs, imply sequence or state transition
      (DO something → THEN do something else)
    - checklist: items are verifiable conditions (yes/no pass/fail criteria)
    - comparison_table: items are noun phrases / attributes for comparison (no actions)
    - attributes: taxonomy/classification labels without executable meaning

    Key distinction: diagnostic questions are NOT execution steps.
    "Is there ML?" is diagnostic (assessing state), not workflow (doing something).
    "Define the scope" is workflow (performing an action).
    """
    if not items:
        return "attributes"

    action_count = 0
    question_count = 0  # Interrogative items (Is/Can/Does/What/How)
    checkable_count = 0  # Verifiable conditions
    noun_phrase_count = 0

    for item in items:
        item_stripped = item.strip()
        first_words = " ".join(item_stripped.split()[:5])

        # Questions that assess/classify state → diagnostic
        if re.match(r"^(?:Is|Are|Does|Do|Can|Has|Have|Should|Must|What|How|Whether)\s", item_stripped, re.IGNORECASE) or item_stripped.endswith("?"):
            question_count += 1
        elif _ACTION_VERBS.search(first_words):
            action_count += 1
        elif _CHECKABLE_PATTERN.search(item_stripped):
            checkable_count += 1
        else:
            noun_phrase_count += 1

    total = len(items)

    # DIAGNOSTIC: majority are questions assessing/classifying state
    # Key: questions like "Is there X?" / "Can the system Y?" are diagnostic,
    # NOT workflow steps. They determine a category, they don't execute actions.
    if question_count >= total * 0.5:
        # Distinguish diagnostic from checklist:
        # Diagnostic = questions that CLASSIFY or DETERMINE STATE
        # Checklist = conditions to VERIFY after doing something
        context_lower = context.lower()
        diagnostic_signals = ["determine", "classify", "categorize", "assess", "identify",
                              "diagnos", "evaluate whether", "判断", "分类", "评估",
                              "to determine", "ask these questions", "判断是否"]
        if any(sig in context_lower for sig in diagnostic_signals) or question_count >= total * 0.7:
            return "diagnostic"
        return "checklist"

    # If most items have action verbs → process
    if action_count >= total * 0.4:
        return "process"

    # Checkable conditions without questions → checklist
    if checkable_count >= total * 0.4:
        return "checklist"

    # If most items are noun phrases without actions → comparison table or attributes
    if noun_phrase_count >= total * 0.6:
        context_lower = context.lower()
        if any(kw in context_lower for kw in ["compar", "versus", "vs", "balance", "contrast",
                                               "differ", "between", "对比", "比较", "区别"]):
            return "comparison_table"
        return "attributes"

    # Mixed — default to process if some actions exist
    if action_count >= 2:
        return "process"
    return "attributes"


def _extract_deterministic(
    text: str,
    document_id: str,
    source_title: str,
    output_language: str,
    page_offset: int = 0,
) -> list[dict]:
    """Fallback: extract candidate units using pattern matching.

    Looks for numbered steps, bullet lists, framework language, decision rules,
    and section-header + structured content patterns.
    Applies list-type classification and redundancy gate.
    """
    candidates = []

    # Strategy 1: Find numbered step sequences
    step_blocks = _find_step_sequences(text)
    for block in step_blocks[:3]:
        unit = _build_unit_from_steps(block, text, document_id, source_title)
        if unit:
            candidates.append(unit)

    # Strategy 2: Find bullet-list processes (3+ consecutive bullets)
    if len(candidates) < 5:
        bullet_blocks = _find_bullet_processes(text)
        for block in bullet_blocks[:5 - len(candidates)]:
            unit = _build_unit_from_bullets(block, text, document_id, source_title)
            if unit:
                candidates.append(unit)

    # Strategy 3: Find framework/principle patterns
    if len(candidates) < 5:
        framework_blocks = _find_framework_patterns(text)
        for block in framework_blocks[:5 - len(candidates)]:
            unit = _build_unit_from_framework(block, text, document_id, source_title)
            if unit:
                candidates.append(unit)

    # Strategy 4: Find decision rules (if-then patterns)
    if len(candidates) < 5:
        decision_blocks = _find_decision_rules(text)
        for block in decision_blocks[:5 - len(candidates)]:
            unit = _build_unit_from_decision(block, text, document_id, source_title)
            if unit:
                candidates.append(unit)

    # Strategy 5: Find section-header + structured content
    if len(candidates) < 5:
        section_blocks = _find_section_processes(text)
        for block in section_blocks[:5 - len(candidates)]:
            unit = _build_unit_from_section(block, text, document_id, source_title)
            if unit:
                candidates.append(unit)

    # ── Redundancy Gate: merge highly similar candidates ────────────────
    candidates = _merge_redundant_candidates(candidates)

    return candidates[:5]


def _find_step_sequences(text: str) -> list[dict]:
    """Find sequences of numbered steps in text."""
    blocks = []
    # Match patterns like "Step 1:", "1.", "第一步", etc.
    step_pattern = re.compile(
        r"(?:^|\n)\s*(?:(?:Step\s*\d+|第[一二三四五六七八九十]+步)[.:：]\s*(.+)|(\d+)[.)]\s+(.+))",
        re.IGNORECASE,
    )

    lines = text.split("\n")
    current_steps = []
    current_start = 0

    for i, line in enumerate(lines):
        match = step_pattern.match(line)
        if match:
            if not current_steps:
                current_start = i
            step_text = match.group(1) or match.group(3) or line.strip()
            current_steps.append(step_text.strip())
        else:
            if len(current_steps) >= 3:
                # Found a valid step sequence
                context_start = max(0, current_start - 2)
                context = "\n".join(lines[context_start:i])
                blocks.append({
                    "steps": current_steps,
                    "context": context,
                    "title": _extract_title_from_context(context),
                })
            current_steps = []

    # Don't forget the last block
    if len(current_steps) >= 3:
        context = "\n".join(lines[max(0, current_start - 2):])
        blocks.append({
            "steps": current_steps,
            "context": context,
            "title": _extract_title_from_context(context),
        })

    return blocks


def _find_framework_patterns(text: str) -> list[dict]:
    """Find framework-like patterns (named frameworks, principles, processes)."""
    blocks = []
    # Broader pattern: title containing method keywords, OR "X is a process/method/approach"
    framework_pattern = re.compile(
        r"(?:^|\n)\s*(?:#{1,3}\s*)?(?:The\s+)?(.{3,60}(?:Framework|Model|Principle|Method|Approach|Process|Checklist|Criteria|框架|模型|原则|方法|流程|清单|标准))\s*[:：]?\s*\n((?:.*\n){2,12})",
        re.IGNORECASE,
    )

    for match in framework_pattern.finditer(text):
        title = match.group(1).strip()
        body = match.group(2).strip()
        if len(body) > 50:
            blocks.append({
                "title": title,
                "body": body,
                "full_text": match.group(0),
            })

    # Also match "X is a process/method to address..." patterns
    def_pattern = re.compile(
        r"(?:^|\n)\s*(.{5,60}?)\s+(?:is|are)\s+(?:a|an|the)\s+(process|method|approach|framework|technique)\s+(?:to|for|that)\s+(.{20,120})",
        re.IGNORECASE,
    )
    for match in def_pattern.finditer(text):
        subject = match.group(1).strip()
        kind = match.group(2).strip()
        description = match.group(3).strip()
        # Get following lines as body
        start = match.end()
        following = text[start:start + 500]
        blocks.append({
            "title": f"{subject} ({kind})",
            "body": description + "\n" + following,
            "full_text": match.group(0) + following[:200],
        })

    return blocks


def _find_decision_rules(text: str) -> list[dict]:
    """Find if-then decision rules."""
    blocks = []
    rule_pattern = re.compile(
        r"(?:^|\n)\s*(?:If|When|如果|当)\s+(.{10,80}?)(?:,?\s*(?:then|就|则|应该))\s+(.{10,80})",
        re.IGNORECASE,
    )

    for match in rule_pattern.finditer(text):
        condition = match.group(1).strip()
        action = match.group(2).strip()
        if len(condition) > 10 and len(action) > 10:
            blocks.append({
                "condition": condition,
                "action": action,
                "full_text": match.group(0).strip(),
            })

    return blocks


def _build_unit_from_steps(block: dict, full_text: str, document_id: str, source_title: str) -> dict | None:
    """Build a candidate unit from a step sequence."""
    steps = block["steps"]
    title = block.get("title", "")
    context = block.get("context", "")

    if len(steps) < 2:
        return None

    unit = create_empty_unit()
    unit["name"] = _truncate_name(title, 60) if title else f"Step process: {_truncate_name(steps[0], 45)}"
    unit["type"] = "workflow"
    unit["purpose"] = f"Execute a {len(steps)}-step process" + (f" for {title}" if title else "")
    unit["status"] = "draft"
    unit["source_document_ids"] = [document_id] if document_id else []
    unit["execution_steps"] = [f"Step {i+1}: {s}" for i, s in enumerate(steps)]
    unit["evidence_spans"] = [{"document_id": document_id, "text": context[:300], "location": ""}]

    # Generate basic trigger from title/context
    unit["triggers"] = [{"scenario": f"When needing to execute: {title or steps[0][:50]}", "signals": [], "required_context": []}]
    unit["anti_triggers"] = [{"scenario": f"When the task only asks to explain or understand {title or steps[0][:30]} conceptually, without needing to execute these steps", "reason": "Problem shape mismatch: explain vs execute"}]
    unit["diagnostic_questions"] = [f"Does the task require executing this {len(steps)}-step process?", f"Is the context appropriate for: {title or steps[0][:50]}?"]
    unit["boundaries"] = ["Requires the specific context described in source material", "Only applies when user needs to EXECUTE, not just understand"]
    unit["quality_checks"] = ["All steps completed in order", "Output matches expected format"]
    unit["confidence"] = {"level": "medium", "reason": "Extracted from step sequence pattern."}

    # Validate distinctiveness
    passes, _ = validate_distinctiveness(unit)
    if not passes:
        return None

    return unit


def _build_unit_from_framework(block: dict, full_text: str, document_id: str, source_title: str) -> dict | None:
    """Build a candidate unit from a framework pattern."""
    title = block.get("title", "")
    body = block.get("body", "")

    if not title or len(body) < 50:
        return None

    unit = create_empty_unit()
    unit["name"] = _truncate_name(title, 60)
    unit["type"] = "framework"
    unit["purpose"] = f"Apply the {title} to structure analysis or decision-making"
    unit["status"] = "draft"
    unit["source_document_ids"] = [document_id] if document_id else []
    unit["evidence_spans"] = [{"document_id": document_id, "text": block.get("full_text", "")[:300], "location": ""}]

    # Extract REAL steps from body (bullet points, numbered, or topic sentences)
    unit["execution_steps"] = _extract_method_steps(body, title)

    # Generate PROBLEM-SITUATION trigger (not "When working on: [title]")
    domain_keywords = _extract_domain_keywords(body + " " + title)
    trigger_scenario = _generate_problem_situation(title, body, domain_keywords, "framework")
    unit["triggers"] = [{"scenario": trigger_scenario, "signals": domain_keywords[:6], "required_context": []}]
    unit["anti_triggers"] = [{"scenario": f"When the task only asks to explain or define {title} without applying it to a specific problem", "reason": "Problem shape mismatch: explain vs apply"}]
    unit["diagnostic_questions"] = _generate_diagnostic_questions(title, body, domain_keywords, "framework")
    unit["boundaries"] = [f"Framework is specific to the context described in: {source_title or 'source'}", "Only applies when user needs to APPLY the framework, not just learn about it"]
    unit["quality_checks"] = _generate_quality_checks(title, body, "framework")
    unit["confidence"] = {"level": "medium", "reason": "Extracted from framework pattern."}

    passes, _ = validate_distinctiveness(unit)
    if not passes:
        return None

    return unit


def _build_unit_from_decision(block: dict, full_text: str, document_id: str, source_title: str) -> dict | None:
    """Build a candidate unit from a decision rule."""
    condition = block.get("condition", "")
    action = block.get("action", "")

    if len(condition) < 10 or len(action) < 10:
        return None

    unit = create_empty_unit()
    unit["name"] = f"Decision: If {_truncate_name(condition, 45)}"
    unit["type"] = "decision_rule"
    unit["purpose"] = f"When {condition}, then {action}"
    unit["status"] = "draft"
    unit["source_document_ids"] = [document_id] if document_id else []
    unit["evidence_spans"] = [{"document_id": document_id, "text": block.get("full_text", "")[:300], "location": ""}]
    unit["execution_steps"] = [
        f"Check condition: {condition}",
        f"If true, execute: {action}",
        "Verify outcome matches expected result",
    ]
    unit["triggers"] = [{"scenario": f"When: {condition}", "signals": [], "required_context": []}]
    unit["anti_triggers"] = [{"scenario": f"When the task is about {condition[:30]} but doesn't require making this specific decision", "reason": "Topic overlap without decision need"}]
    unit["diagnostic_questions"] = [f"Is the condition met: {condition}?", "Does this decision rule apply to the current situation?"]
    unit["boundaries"] = ["Only applies when the stated condition is clearly met", "Not for general discussion of the topic"]
    unit["quality_checks"] = ["Condition verified before action", "Action outcome matches expectation"]
    unit["confidence"] = {"level": "medium", "reason": "Extracted from if-then pattern."}

    passes, _ = validate_distinctiveness(unit)
    if not passes:
        return None

    return unit


def _find_bullet_processes(text: str) -> list[dict]:
    """Find sequences of 3+ bullet points that form a process or checklist."""
    blocks = []
    lines = text.split("\n")
    # Match various bullet markers: , -, •, ·, *, or "Topic. Description" in list context
    bullet_re = re.compile(r"^\s*(?:[\-\u2022\u00b7*\u25aa\u2023\uf0b7]|\uf0a7|\u25cf)\s*(.+)")
    # Also match lines starting with a capital word followed by period (e.g., "Classification. What is...")
    topic_bullet_re = re.compile(r"^\s*([A-Z][a-z]+(?:\s+[a-z]+){0,3})\.\s+(.{15,})")

    current_bullets = []
    current_start = 0
    context_before = ""

    for i, line in enumerate(lines):
        m = bullet_re.match(line)
        if not m:
            m = topic_bullet_re.match(line)
        if m:
            if not current_bullets:
                current_start = i
                # Grab up to 2 lines before as context/title
                ctx_start = max(0, i - 2)
                context_before = "\n".join(lines[ctx_start:i]).strip()
            bullet_text = m.group(1) if bullet_re.match(line) else line.strip()
            current_bullets.append(bullet_text.strip())
        else:
            if len(current_bullets) >= 3:
                title = _extract_title_from_context(context_before)
                blocks.append({
                    "items": current_bullets[:8],
                    "context": context_before,
                    "title": title,
                    "raw": "\n".join(lines[current_start:i]),
                })
            current_bullets = []

    # Last block
    if len(current_bullets) >= 3:
        title = _extract_title_from_context(context_before)
        blocks.append({
            "items": current_bullets[:8],
            "context": context_before,
            "title": title,
            "raw": "\n".join(lines[current_start:]),
        })

    return blocks


def _build_unit_from_bullets(block: dict, full_text: str, document_id: str, source_title: str) -> dict | None:
    """Build a candidate unit from a bullet-list process.

    Applies list-type classification:
    - 'diagnostic' → type=diagnostic, questions determine state/category
    - 'process' → type=workflow, action steps with sequence
    - 'checklist' → type=checklist, verifiable conditions
    - 'comparison_table' / 'attributes' → REJECTED (reference material)
    """
    items = block["items"]
    title = block.get("title", "")
    context = block.get("context", "")

    if len(items) < 3:
        return None

    # Skip if items are too short (likely not actionable)
    avg_len = sum(len(it) for it in items) / len(items)
    if avg_len < 15:
        return None

    # ── List-type classification gate ───────────────────────────────────
    list_type = _classify_list_type(items, context)
    if list_type in ("comparison_table", "attributes"):
        # NOT an executable method — reject
        return None

    unit = create_empty_unit()
    unit["_list_type"] = list_type  # metadata for audit trail
    unit["status"] = "draft"
    unit["source_document_ids"] = [document_id] if document_id else []
    unit["evidence_spans"] = [{"document_id": document_id, "text": block.get("raw", "")[:400], "location": ""}]

    if list_type == "diagnostic":
        # DIAGNOSTIC: questions that determine state or classify something
        # NOT a workflow — do NOT number questions and call them "steps"
        diag_topic = title or _infer_diagnostic_topic(items, context)
        unit["name"] = f"Diagnostic: {diag_topic}"
        unit["type"] = "diagnostic"
        unit["purpose"] = f"Determine the state/category of a system by answering {len(items)} diagnostic questions" + (f" about {diag_topic}" if diag_topic else "")
        unit["diagnostic_questions"] = items[:6]
        # Execution steps describe HOW TO USE the diagnostic, not repeat questions
        unit["execution_steps"] = [
            f"Step 1: Present each diagnostic question to the stakeholder or system under review",
            f"Step 2: Record evidence-based answers (not opinions) for each question",
            f"Step 3: Classify the result based on answer pattern (e.g., all yes = category A, mixed = category B)",
            f"Step 4: Document the classification with supporting evidence for each answer",
        ]
        unit["quality_checks"] = [
            "Each answer is supported by observable evidence or system behavior",
            "Classification is clearly stated (not ambiguous)",
            "Borderline cases are flagged for expert review",
            "Diagnostic is not used beyond its validated domain",
        ]
        diag_keywords = _extract_domain_keywords(" ".join(items) + " " + context)
        diag_trigger_scenario = f"When needing to determine whether a system or tool genuinely uses AI capabilities, or when assessing if something is automated versus intelligent"
        if diag_keywords:
            diag_trigger_scenario = f"When needing to assess or classify whether something involves {', '.join(diag_keywords[:3])}, or when determining the nature of a system's capabilities"
        unit["triggers"] = [{"scenario": diag_trigger_scenario, "signals": diag_keywords[:6], "required_context": []}]
        unit["anti_triggers"] = [
            {"scenario": f"When the task asks to explain what {diag_topic} means conceptually, not to assess a specific system", "reason": "Problem shape mismatch: explain vs evaluate"},
            {"scenario": f"When the system being assessed is outside the domain this diagnostic was designed for", "reason": "Domain boundary exceeded"},
        ]
        unit["boundaries"] = [
            f"Derived from: {source_title or 'source material'}",
            f"Valid only for assessing systems within the domain described in source",
            "Classification result requires human confirmation for high-stakes decisions",
        ]

    elif list_type == "checklist":
        unit["name"] = _truncate_name(title, 60) if title else f"Checklist: {_truncate_name(items[0], 55)}"
        unit["type"] = "checklist"
        unit["purpose"] = f"Verify {len(items)} conditions" + (f": {title}" if title else f" starting with: {items[0][:60]}")
        unit["diagnostic_questions"] = [it for it in items if _CHECKABLE_PATTERN.search(it)] or items[:3]
        unit["execution_steps"] = [f"{i+1}. Verify: {it}" for i, it in enumerate(items)]
        unit["quality_checks"] = ["All conditions verified with evidence", "Pass/fail documented for each item"]
        unit["triggers"] = [{"scenario": f"When needing to verify: {title or items[0][:50]}", "signals": [], "required_context": []}]
        unit["anti_triggers"] = [{"scenario": f"When the task only asks to explain or understand {title or items[0][:30]} conceptually", "reason": "Problem shape mismatch: explain vs verify"}]
        unit["boundaries"] = [f"Derived from: {source_title or 'source material'}", "Only applies when user needs to VERIFY conditions, not learn about the topic"]

    else:  # process
        unit["name"] = _truncate_name(title, 60) if title else f"Process: {_truncate_name(items[0], 55)}"
        unit["type"] = "workflow"
        unit["purpose"] = f"Execute a {len(items)}-step process" + (f": {title}" if title else f" starting with: {items[0][:60]}")
        unit["execution_steps"] = [f"{i+1}. {it}" for i, it in enumerate(items)]
        unit["quality_checks"] = ["All steps completed in order", "Output aligns with source material's intent"]
        # Generate diagnostic questions from items that are questions, or from title
        diag_from_items = [it for it in items if _CHECKABLE_PATTERN.search(it)]
        if diag_from_items:
            unit["diagnostic_questions"] = diag_from_items[:3]
        elif title:
            unit["diagnostic_questions"] = [f"Does this task involve: {title}?"]
        else:
            unit["diagnostic_questions"] = [f"Is this process applicable to the current task?"]
        unit["triggers"] = [{"scenario": f"When needing to execute: {title or items[0][:50]}", "signals": [], "required_context": []}]
        unit["anti_triggers"] = [{"scenario": f"When the task only asks about the topic conceptually (explain/define) without needing to execute this specific process", "reason": "Topic similarity alone is not sufficient — problem shape must match"}]
        unit["boundaries"] = [f"Derived from: {source_title or 'source material'}", "Requires context matching the source domain", "Only applies when the user needs to EXECUTE this process, not just learn about the topic"]

    unit["confidence"] = {"level": "medium", "reason": f"Extracted from {len(items)}-item {list_type}."}

    passes, _ = validate_distinctiveness(unit)
    if not passes:
        return None

    return unit


def _truncate_name(text: str, max_len: int = 60) -> str:
    """Truncate a name at a word boundary and strip trailing punctuation/whitespace.

    Avoids mid-word cuts and trailing spaces. A trailing space is especially bad
    because the review UI wraps names in markdown bold (**name**); a space before
    the closing ** stops markdown from parsing it, leaking literal asterisks into
    the displayed name.
    """
    text = (text or "").strip()
    if len(text) <= max_len:
        return text.rstrip(" .,;:!?")
    cut = text[:max_len]
    # Back up to the last space so we never cut a word in half.
    if " " in cut:
        cut = cut.rsplit(" ", 1)[0]
    return cut.rstrip(" .,;:!?")


def _infer_diagnostic_topic(items: list[str], context: str) -> str:
    """Infer what a diagnostic set of questions is assessing."""
    # Try to get topic from context
    context_lower = context.lower()
    # Look for "To determine X" or "To assess X" patterns
    m = re.search(r"to\s+(?:determine|assess|evaluate|identify|classify)\s+(?:if|whether|the|a|an)?\s*(.{5,60})", context_lower)
    if m:
        return _truncate_name(m.group(1), 60)
    # Try title from context
    title = _extract_title_from_context(context)
    if title and len(title) > 5:
        return _truncate_name(title, 60)
    # Fallback: common theme from questions
    return _truncate_name(items[0], 45) if items else "system state"


def _find_section_processes(text: str) -> list[dict]:
    """Find section headers followed by structured content (questions, criteria, steps)."""
    blocks = []
    # Match patterns like "To determine X, ask these questions:" or "X involves:" or "Key considerations:"
    section_re = re.compile(
        r"(?:^|\n)\s*(.{10,80}?(?:questions?|steps?|criteria|considerations?|factors?|aspects?|components?|elements?|phases?|stages?))\s*[:：]\s*\n((?:.*\n){2,10})",
        re.IGNORECASE,
    )
    for match in section_re.finditer(text):
        header = match.group(1).strip()
        body = match.group(2).strip()
        if len(body) > 60:
            blocks.append({
                "title": header,
                "body": body,
                "full_text": match.group(0),
            })

    # Also match "[Page N] Title" followed by structured paragraphs
    page_section_re = re.compile(
        r"\[Page\s*\d+\]\s*(.{5,60})\n((?:.*\n){3,12})",
        re.IGNORECASE,
    )
    for match in page_section_re.finditer(text):
        title = match.group(1).strip()
        body = match.group(2).strip()
        # Only keep if body has structure (bullets, numbered items, or multiple paragraphs)
        has_structure = (
            len(re.findall(r"[\-\u2022\u00b7*]", body)) >= 3
            or len(re.findall(r"\d+[.)]", body)) >= 2
            or body.count("\n\n") >= 2
        )
        if has_structure and len(body) > 100:
            blocks.append({
                "title": title,
                "body": body,
                "full_text": match.group(0)[:500],
            })

    return blocks


def _build_unit_from_section(block: dict, full_text: str, document_id: str, source_title: str) -> dict | None:
    """Build a candidate unit from a section-header + structured content."""
    title = block.get("title", "")
    body = block.get("body", "")

    if not title or len(body) < 60:
        return None

    unit = create_empty_unit()
    unit["name"] = _truncate_name(title, 80)
    unit["type"] = "framework"
    unit["purpose"] = f"Apply structured approach: {_truncate_name(title, 80)}"
    unit["status"] = "draft"
    unit["source_document_ids"] = [document_id] if document_id else []
    unit["evidence_spans"] = [{"document_id": document_id, "text": block.get("full_text", "")[:400], "location": ""}]

    # Extract REAL methodology steps from body content
    unit["execution_steps"] = _extract_method_steps(body, title)
    if len(unit["execution_steps"]) < 2:
        return None

    # Generate PROBLEM-SITUATION trigger (not "When working on: [title]")
    domain_keywords = _extract_domain_keywords(body + " " + title)
    trigger_scenario = _generate_problem_situation(title, body, domain_keywords, "framework")
    unit["triggers"] = [{"scenario": trigger_scenario, "signals": domain_keywords[:6], "required_context": []}]
    unit["anti_triggers"] = [{"scenario": f"When the task only asks to explain or describe {title[:40]} without needing to apply this structured approach", "reason": "Problem shape mismatch: explain vs apply"}]
    unit["diagnostic_questions"] = _generate_diagnostic_questions(title, body, domain_keywords, "framework")
    unit["boundaries"] = [f"Specific to context in: {source_title or 'source'}", "Only applies when user needs to EXECUTE this approach"]
    unit["quality_checks"] = _generate_quality_checks(title, body, "framework")
    unit["confidence"] = {"level": "medium", "reason": "Extracted from section structure."}

    passes, _ = validate_distinctiveness(unit)
    if not passes:
        return None

    return unit


def _extract_domain_keywords(text: str) -> list[str]:
    """Extract domain-specific keywords from text (excluding generic words).

    Prioritizes:
    1. Multi-word domain terms (machine learning, neural network, etc.)
    2. Specific technical terms that identify the domain
    3. Excludes all common English words and PDF extraction artifacts
    """
    from collections import Counter

    # ── Multi-word domain terms (highest priority) ──────────────────────
    _COMPOUND_TERMS = [
        "machine learning", "deep learning", "neural network", "neural networks",
        "artificial intelligence", "predictive analytics", "predictive ai",
        "retrieval augmented", "retrieval-augmented generation", "natural language",
        "generative ai", "large language", "language model", "fine-tuning",
        "supervised learning", "unsupervised learning", "reinforcement learning",
        "computer vision", "decision making", "decision-making",
        "resource allocation", "risk prediction", "change management",
        "project management", "project scheduling", "cost management",
        "data bias", "data security", "data ownership",
        "off-the-shelf", "real time", "real-time",
    ]
    text_lower = text.lower()
    found_compounds = [term for term in _COMPOUND_TERMS if term in text_lower]

    # ── Single word exclusion list (very aggressive) ────────────────────
    generic = {
        # Function words
        "the", "and", "for", "are", "but", "not", "you", "this", "that",
        "with", "from", "have", "will", "can", "what", "when", "how",
        "need", "want", "should", "would", "could", "about", "into",
        "these", "those", "them", "there", "their", "than", "then",
        "without", "within", "between", "through", "during", "before",
        "after", "other", "more", "most", "some", "such", "very",
        "also", "just", "only", "still", "already", "yet", "each",
        "where", "which", "while", "because", "since", "until",
        "does", "done", "doing", "being", "been", "having",
        # Common verbs/adjectives
        "using", "used", "uses", "able", "many", "much", "well",
        "specific", "general", "particular", "different", "similar",
        "first", "second", "third", "last", "next", "previous",
        "good", "best", "better", "great", "important", "significant",
        "new", "old", "large", "small", "high", "low", "long", "short",
        "possible", "potential", "likely", "certain", "clear",
        # Generic nouns
        "system", "process", "method", "approach", "tool", "team", "time",
        "data", "result", "output", "input", "user", "case", "part", "set",
        "step", "task", "project", "work", "help", "use", "make",
        "page", "section", "chapter", "content", "text", "information",
        "example", "examples", "way", "ways", "thing", "things",
        "people", "person", "company", "organization", "business",
        "world", "life", "day", "year", "time", "times",
        # PDF extraction artifacts
        "instructions", "questions", "question", "answer", "answers",
        "following", "above", "below", "here", "there",
        # Overly broad domain words
        "ability", "capabilities", "capability", "features", "feature",
        "determine", "determines", "determining",
        "structur", "organ", "manag", "develop", "implement", "creat",
        "provid", "includ", "follow", "base", "relat", "support",
        "decision", "making", "decisions", "situation", "situations",
        "inform", "information", "technology", "technologies",
        "learning", "learn", "learns", "trained", "training", "train",
        "over", "under", "up", "down", "out", "off", "on", "in",
        "responses", "relevant", "professionals", "delays",
        "impact", "modern", "workforce", "observed", "computing",
        "roughly", "double", "speed", "profound", "description",
        "salesperson", "accountant", "moore", "gordon", "intel",
        "email", "filtering", "algorithms", "algorithm",
        "patterns", "pattern", "distinguish", "legitimate",
        "methods", "method", "various", "enable", "machine",
        "however", "therefore", "thus", "hence", "although",
        "described", "guide", "guidebook", "guidebooks",
        "solutions", "solution", "technology", "technologies",
        "organizational", "organizational", "public",
        "value", "values", "get", "getting", "got",
        "augmenting", "augment", "augmented",
        "shelf", "off", "llms", "llm",
        # Additional noise: stemmed fragments and overly broad terms
        "concern", "concerns", "utiliz", "appropriate", "appropriately",
        "three", "observ", "solu", "plan", "plans", "planning",
        "aspect", "aspects", "element", "elements",
        "general", "background", "knowledge", "initiative",
        "budget", "financial", "meeting", "invitation",
        "news", "media", "summary", "definition", "glossary",
        "calculate", "numbers", "impact", "professor",
        "types", "type", "kind", "kinds", "form", "forms",
        "level", "levels", "degree", "extent", "range",
        "area", "areas", "field", "fields", "domain", "domains",
        "stage", "stages", "phase", "phases", "status", "state",
        "role", "roles", "function", "functions", "purpose",
        "benefit", "benefits", "advantage", "disadvantage",
        "challenge", "challenges", "issue", "issues", "problem", "problems",
        "objective", "objectives", "goal", "goals", "target", "targets",
    }

    # Extract single words
    words = set(re.findall(r"\b[a-z]{4,}\b", text_lower))
    meaningful = words - generic
    word_counts = Counter(re.findall(r"\b[a-z]{4,}\b", text_lower))
    ranked = sorted(meaningful, key=lambda w: word_counts.get(w, 0), reverse=True)

    # Combine: compound terms first (most specific), then single words
    result = []
    for compound in found_compounds[:3]:
        # Use the compound as a keyword (may be multi-word)
        result.append(compound)
    for word in ranked[:8 - len(result)]:
        if word not in result:
            result.append(word)

    return result[:8]


def _extract_method_steps(body: str, title: str) -> list[str]:
    """Extract real methodology steps from body text.

    Instead of generic 'Understand X, Apply Y, Verify Z', extracts actual
    content from the source material that forms actionable steps.
    """
    body_lines = [l.strip() for l in body.split("\n") if l.strip() and len(l.strip()) > 10]

    # Strategy 1: Bullet/numbered items with action content
    structured = []
    for l in body_lines:
        # Strip bullet markers
        cleaned = re.sub(r"^(?:\d+[.)]\s*|[\-\u2022\u00b7*]\s*|Step\s*\d+[:.]?\s*)", "", l).strip()
        if len(cleaned) > 15:
            structured.append(cleaned)

    if len(structured) >= 3:
        return structured[:6]

    # Strategy 2: Topic sentences (Capital word. Description)
    topic_sentences = []
    topic_re = re.compile(r"^([A-Z][a-z]+(?:\s+[a-z]+){0,3})\.\s+(.{15,})")
    for l in body_lines:
        m = topic_re.match(l)
        if m:
            topic_sentences.append(f"{m.group(1)}: {m.group(2)[:100]}")

    if len(topic_sentences) >= 3:
        return topic_sentences[:6]

    # Strategy 3: Key sentences with action verbs
    action_sentences = []
    for l in body_lines:
        if _ACTION_VERBS.search(l) and len(l) > 20:
            action_sentences.append(l[:120])

    if len(action_sentences) >= 2:
        return action_sentences[:6]

    # Strategy 4: Use structured items even if short, or topic sentences
    if len(structured) >= 2:
        return structured[:6]
    if len(topic_sentences) >= 2:
        return topic_sentences[:6]

    # Fallback: derive from body content (not generic)
    if len(body_lines) >= 2:
        return [f"Analyze: {l[:80]}" for l in body_lines[:4] if len(l) > 15]

    return []


def _generate_problem_situation(title: str, body: str, domain_keywords: list[str], unit_type: str) -> str:
    """Generate a trigger scenario that describes the USER'S PROBLEM SITUATION.

    Instead of: 'When working on: Benefits of Predictive AI (involving: predictive, ...)'
    Generates:  'When evaluating whether predictive analytics is suitable for a project,
                 or needing to justify investment in predictive AI to stakeholders'

    The scenario should describe WHEN a user would NEED this method, using natural language.
    """
    title_lower = title.lower()
    kw_text = ", ".join(domain_keywords[:4]) if domain_keywords else title_lower

    # Detect what kind of problem situation this method addresses
    body_lower = body.lower()

    # Assessment/evaluation frameworks
    if any(w in body_lower for w in ["assess", "evaluat", "determin", "measure", "check", "verify"]):
        return f"When needing to assess or evaluate aspects related to {kw_text}, or when a structured evaluation of {title_lower} is required for a decision"

    # Planning/strategy frameworks
    if any(w in body_lower for w in ["plan", "strateg", "roadmap", "phase", "adopt", "start", "begin"]):
        return f"When planning or strategizing around {kw_text}, or when needing a structured approach to {title_lower} for an organization or project"

    # Implementation/execution frameworks
    if any(w in body_lower for w in ["implement", "deploy", "build", "creat", "develop", "configur"]):
        return f"When needing to implement or set up {kw_text}, or when tasked with {title_lower} in a practical context"

    # Analysis/understanding frameworks
    if any(w in body_lower for w in ["analyz", "understand", "identif", "recogniz", "distinguish"]):
        return f"When analyzing or trying to understand {kw_text}, or when needing to identify key aspects of {title_lower}"

    # Risk/governance frameworks
    if any(w in body_lower for w in ["risk", "govern", "comply", "regulat", "ethical", "bias", "fair"]):
        return f"When addressing risks, governance, or compliance related to {kw_text}, or when needing to manage {title_lower}"

    # Generic fallback — still better than "When working on: [title]"
    return f"When needing a structured approach to {kw_text}, specifically when the task requires applying {title_lower} to a real problem or decision"


def _generate_diagnostic_questions(title: str, body: str, domain_keywords: list[str], unit_type: str) -> list[str]:
    """Generate diagnostic questions that help determine if this unit applies.

    Questions should be SPECIFIC to the domain, not generic.
    """
    kw = domain_keywords[:3] if domain_keywords else [title.lower()]
    kw_str = ", ".join(kw)

    questions = [
        f"Does the current task involve {kw_str} in a way that requires structured analysis?",
        f"Is the user trying to APPLY {title.lower()} (not just learn about it)?",
    ]

    # Add domain-specific question
    body_lower = body.lower()
    if "risk" in body_lower or "govern" in body_lower:
        questions.append(f"Are there risk or governance concerns related to {kw[0]} that need addressing?")
    elif "plan" in body_lower or "strateg" in body_lower:
        questions.append(f"Does the user need a plan or strategy specifically involving {kw[0]}?")
    elif "assess" in body_lower or "evaluat" in body_lower:
        questions.append(f"Is there something specific to evaluate or assess regarding {kw[0]}?")
    else:
        questions.append(f"Is the context appropriate for applying this {kw[0]}-related method?")

    return questions


def _generate_quality_checks(title: str, body: str, unit_type: str) -> list[str]:
    """Generate quality checks specific to the unit's content."""
    checks = [
        f"Output addresses the core aspects of {title.lower()}",
        "Each recommendation or step is traceable to source material",
    ]

    body_lower = body.lower()
    if "risk" in body_lower:
        checks.append("Risks are identified with specific mitigation strategies")
    if "data" in body_lower:
        checks.append("Data requirements and limitations are acknowledged")
    if any(w in body_lower for w in ["step", "phase", "process"]):
        checks.append("Steps follow logical sequence from source material")
    if any(w in body_lower for w in ["ethical", "bias", "fair"]):
        checks.append("Ethical considerations are addressed, not just mentioned")

    return checks[:4]


def _extract_title_from_context(context: str) -> str:
    """Try to extract a title from surrounding context."""
    lines = context.strip().split("\n")
    for line in lines:
        line = line.strip()
        # Markdown heading
        if line.startswith("#"):
            return line.lstrip("#").strip()
        # Short line before steps (likely a title)
        if len(line) < 80 and not line.endswith((".", ",", ":", "：")):
            return line
    return ""


# ── Redundancy Gate ──────────────────────────────────────────────────────


def _merge_redundant_candidates(candidates: list[dict]) -> list[dict]:
    """Remove or merge candidates that are semantically redundant.

    Two candidates are redundant if:
    - Their execution_steps overlap by >= 60%
    - OR their purpose + name have >= 70% word overlap
    - OR their evidence_spans reference the same text block

    When redundant, keep the one with more complete fields.
    """
    if len(candidates) <= 1:
        return candidates

    merged: list[dict] = []
    used: set[int] = set()

    for i in range(len(candidates)):
        if i in used:
            continue
        current = candidates[i]
        for j in range(i + 1, len(candidates)):
            if j in used:
                continue
            if _is_redundant_pair(current, candidates[j]):
                # Merge: keep the richer one, absorb evidence from the other
                if _completeness_score(candidates[j]) > _completeness_score(current):
                    current = candidates[j]
                # Absorb evidence spans from the weaker one
                existing_texts = {s.get("text", "")[:50] for s in current.get("evidence_spans", [])}
                for span in candidates[j].get("evidence_spans", []):
                    if span.get("text", "")[:50] not in existing_texts:
                        current.setdefault("evidence_spans", []).append(span)
                used.add(j)
        merged.append(current)

    return merged


def _is_redundant_pair(a: dict, b: dict) -> bool:
    """Check if two candidates are semantically redundant."""
    # 1. Step overlap (normalize by stripping bullet/number prefixes)
    def normalize_step(s: str) -> str:
        # Strip common prefixes: "1.", "•", "-", "Step N:", etc.
        s = re.sub(r"^(?:\d+[.)]\s*|[\-\u2022\u00b7*]\s*|Step\s*\d+[:.]?\s*)", "", s.strip())
        return s.lower().strip()[:60]

    steps_a = set(normalize_step(s) for s in a.get("execution_steps", []))
    steps_b = set(normalize_step(s) for s in b.get("execution_steps", []))
    if steps_a and steps_b:
        overlap = steps_a & steps_b
        smaller = min(len(steps_a), len(steps_b))
        if smaller > 0 and len(overlap) / smaller >= 0.6:
            return True

    # 2. Purpose + name word overlap
    words_a = set(re.findall(r"\b[a-z]{3,}\b", (a.get("name", "") + " " + a.get("purpose", "")).lower()))
    words_b = set(re.findall(r"\b[a-z]{3,}\b", (b.get("name", "") + " " + b.get("purpose", "")).lower()))
    if words_a and words_b:
        overlap = words_a & words_b
        smaller = min(len(words_a), len(words_b))
        if smaller > 0 and len(overlap) / smaller >= 0.7:
            return True

    # 3. Same evidence text
    ev_a = {s.get("text", "")[:80] for s in a.get("evidence_spans", []) if s.get("text")}
    ev_b = {s.get("text", "")[:80] for s in b.get("evidence_spans", []) if s.get("text")}
    if ev_a and ev_b and ev_a & ev_b:
        return True

    return False


def _completeness_score(unit: dict) -> int:
    """Score how complete a unit's fields are (higher = richer)."""
    score = 0
    score += len(unit.get("execution_steps", []))
    score += len(unit.get("evidence_spans", [])) * 2
    score += len(unit.get("triggers", []))
    score += len(unit.get("anti_triggers", []))
    score += len(unit.get("diagnostic_questions", []))
    score += len(unit.get("boundaries", []))
    score += len(unit.get("quality_checks", []))
    score += len(unit.get("examples", []))
    return score
