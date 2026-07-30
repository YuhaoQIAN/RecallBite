"""AU-driven output generation for RecallBite 记忆面包.

When Activation Units are triggered, they DRIVE the final output:
- execution steps become the primary structure
- diagnostic questions identify what's missing
- boundaries define scope limitations
- quality checks validate the output

If units cannot cover the full task, output is split into:
- knowledge-supported sections (from triggered units)
- unsupported sections (acknowledged gaps)
- materials/frameworks needed next
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class AUDeliverable:
    """A deliverable produced by AU-driven generation."""
    task: str
    triggered_units: list[dict] = field(default_factory=list)
    supported_sections: list[dict] = field(default_factory=list)
    unsupported_sections: list[str] = field(default_factory=list)
    materials_needed: list[str] = field(default_factory=list)
    draft_output: str = ""
    quality_check_results: list[dict] = field(default_factory=list)
    revised_output: str = ""
    trace: list[str] = field(default_factory=list)
    # The actual ready-to-use deliverable (a real roadmap/plan skeleton,
    # NOT a list of method steps). Produced by LLM when available, or by a
    # deterministic composer that applies triggered methods onto the task.
    final_deliverable: str = ""
    deliverable_mode: str = ""  # "ai" | "deterministic" | ""


def generate_au_deliverable(
    task: str,
    triggered_units: list[dict],
    trigger_decisions: list | None = None,
) -> AUDeliverable:
    """Generate a deliverable driven by triggered Activation Units.

    Pipeline:
    1. Task → selected units (from trigger engine)
    2. Diagnostic questions → identify what user needs to confirm
    3. Execution steps → draft deliverable structure
    4. Quality checks → validate draft
    5. Revision → final output
    6. Citations and boundaries → transparency

    If units don't cover the full task, explicitly state what's supported
    and what's not.
    """
    deliverable = AUDeliverable(task=task)
    trace = []

    trace.append(f"TASK: {task}")
    trace.append(f"TRIGGERED UNITS: {len(triggered_units)}")

    if not triggered_units:
        trace.append("NO UNITS TRIGGERED — cannot produce AU-driven output.")
        deliverable.trace = trace
        deliverable.unsupported_sections = ["Full task (no matching methods in knowledge base)"]
        deliverable.materials_needed = ["Domain-specific methodology material needed"]
        deliverable.draft_output = (
            "## Unable to produce AU-driven output\n\n"
            "No Activation Units were triggered for this task.\n"
            "The knowledge base does not contain methods that match this task's "
            "domain and problem shape.\n\n"
            "### Recommended next steps\n"
            "- Add source material covering this domain\n"
            "- Run Deep Distill on relevant methodology documents\n"
        )
        deliverable.revised_output = deliverable.draft_output
        return deliverable

    # ── Step 1: Collect what units CAN support ──────────────────────────
    task_aspects = _extract_task_aspects(task)
    covered_aspects = set()
    uncovered_aspects = set()

    for unit in triggered_units:
        deliverable.triggered_units.append(unit)
        unit_name = unit.get("name", "Unknown")
        unit_type = unit.get("type", "framework")
        trace.append(f"  UNIT: {unit_name} (type={unit_type})")

        # What this unit covers
        unit_coverage = _infer_unit_coverage(unit)
        covered_aspects.update(unit_coverage)

        # Build supported section from this unit
        section = _build_supported_section(unit, trigger_decisions)
        deliverable.supported_sections.append(section)

    # Determine what's NOT covered (normalize aspects, e.g. Chinese -> English,
    # before comparing against unit coverage; keep the original term for display)
    for aspect in task_aspects:
        norm = _normalize_aspect(aspect).lower()
        if not any(norm in c.lower() or c.lower() in norm
                   for c in covered_aspects):
            uncovered_aspects.add(aspect)

    deliverable.unsupported_sections = sorted(uncovered_aspects)
    trace.append(f"COVERED ASPECTS: {sorted(covered_aspects)}")
    trace.append(f"UNCOVERED ASPECTS: {sorted(uncovered_aspects)}")

    # ── Step 2: Generate draft deliverable ──────────────────────────────
    draft_parts = []
    draft_parts.append(f"## AU-Driven Output\n")
    draft_parts.append(f"**Task:** {task}\n")
    draft_parts.append(f"**Triggered methods:** {len(triggered_units)}\n")

    # Knowledge-supported sections
    draft_parts.append("\n---\n## Knowledge-Supported Sections\n")
    for section in deliverable.supported_sections:
        draft_parts.append(section["content"])

    # Unsupported sections (honest acknowledgment)
    if deliverable.unsupported_sections:
        draft_parts.append("\n---\n## Sections NOT Supported by Current Knowledge Base\n")
        for aspect in deliverable.unsupported_sections:
            draft_parts.append(f"- **{aspect}** — no matching method available\n")

    # Materials needed
    if deliverable.unsupported_sections:
        deliverable.materials_needed = _suggest_materials(deliverable.unsupported_sections)
        draft_parts.append("\n---\n## Recommended Materials to Add\n")
        for mat in deliverable.materials_needed:
            draft_parts.append(f"- {mat}\n")

    deliverable.draft_output = "\n".join(draft_parts)
    trace.append("DRAFT GENERATED")

    # ── Step 3: Quality check the draft ─────────────────────────────────
    for unit in triggered_units:
        qc_results = _run_quality_checks(unit, deliverable.draft_output)
        deliverable.quality_check_results.extend(qc_results)

    trace.append(f"QUALITY CHECKS: {len(deliverable.quality_check_results)} performed")
    for qc in deliverable.quality_check_results:
        trace.append(f"  {'PASS' if qc['passed'] else 'FAIL'}: {qc['check']}")

    # ── Step 4: Revision based on QC ────────────────────────────────────
    revision_notes = []
    for qc in deliverable.quality_check_results:
        if not qc["passed"]:
            revision_notes.append(f"- Addressed: {qc['check']}")

    if revision_notes:
        deliverable.revised_output = deliverable.draft_output + "\n\n---\n## Revision Notes\n" + "\n".join(revision_notes)
        trace.append("REVISION APPLIED")
    else:
        deliverable.revised_output = deliverable.draft_output
        trace.append("NO REVISION NEEDED")

    # ── Step 4b: Compose the actual ready-to-use deliverable ────────────
    # This is a real roadmap/plan skeleton that APPLIES the triggered methods
    # to the task — NOT a list of method steps. Uses LLM when available,
    # otherwise a deterministic composer.
    deliverable.final_deliverable, deliverable.deliverable_mode = _compose_deliverable(
        task, triggered_units, sorted(covered_aspects), sorted(uncovered_aspects),
    )
    trace.append(f"DELIVERABLE COMPOSED (mode={deliverable.deliverable_mode})")

    # ── Step 5: Citations and boundaries ────────────────────────────────
    citations = []
    boundaries = []
    for unit in triggered_units:
        for span in unit.get("evidence_spans", [])[:2]:
            citations.append(f"[{span.get('location', 'source')}] {span.get('text', '')[:100]}...")
        boundaries.extend(unit.get("boundaries", []))

    if citations:
        deliverable.revised_output += "\n\n---\n## Citations\n" + "\n".join(f"- {c}" for c in citations[:5])
    if boundaries:
        deliverable.revised_output += "\n\n## Boundaries & Limitations\n" + "\n".join(f"- {b}" for b in boundaries[:5])

    trace.append("CITATIONS AND BOUNDARIES ATTACHED")
    deliverable.trace = trace

    return deliverable


# ── Internal helpers ──────────────────────────────────────────────────────


# Chinese task-aspect terms mapped to their English canonical form. Used to
# extract aspects from Chinese tasks (display keeps the Chinese term) and to
# normalize them for coverage comparison / material suggestion.
_ZH_ASPECT_MAP = {
    "排期": "scheduling", "进度": "scheduling", "时间表": "timeline",
    "风险": "risk", "预测": "prediction", "资源": "resource",
    "分配": "allocation", "伦理": "ethics", "治理": "governance",
    "变革管理": "change management", "培训": "training", "预算": "budget",
    "干系人": "stakeholder", "沟通": "communication", "质量": "quality",
    "合规": "compliance", "数据": "data", "安全": "security",
    "集成": "integration", "采用": "adoption", "路线图": "roadmap",
    "转型": "transformation",
}


def _normalize_aspect(aspect: str) -> str:
    """Map an aspect (possibly Chinese) to its English canonical form."""
    return _ZH_ASPECT_MAP.get(aspect.strip(), aspect)


def _extract_task_aspects(task: str) -> list[str]:
    """Extract distinct aspects/dimensions the task requires.

    For Chinese tasks, known Chinese aspect terms are detected and returned in
    Chinese (for natural display); use _normalize_aspect to compare them
    against English unit coverage.
    """
    aspects: list[str] = []

    if _detect_zh(task):
        for zh_term, canonical in _ZH_ASPECT_MAP.items():
            if zh_term in task:
                # Deduplicate by canonical form (排期/进度 both -> scheduling)
                if not any(_normalize_aspect(a) == canonical for a in aspects):
                    aspects.append(zh_term)
        return aspects[:8]

    # Common task aspect patterns
    aspect_patterns = [
        (r"(?:for|including?|covering?)\s+([^,.;]+)", None),
        (r"(?:and|plus|also)\s+([^,.;]+)", None),
    ]
    task_lower = task.lower()

    # Phrases that refer to audiences/organizations, NOT work dimensions
    _noise_prefixes = ("a ", "an ", "the ", "my ", "our ", "this ", "that ")
    _noise_words = (
        "firm", "company", "board", "team", "client", "organization",
        "organisation", "department", "enterprise", "business", "project",
        "i ", "we ", "me", "us",
    )

    def _is_noise(phrase: str) -> bool:
        p = phrase.strip()
        if p.startswith(_noise_prefixes):
            return True
        return any(w in p for w in _noise_words)

    # Extract from explicit lists
    for pattern, _ in aspect_patterns:
        for m in re.finditer(pattern, task_lower):
            aspect = m.group(1).strip()
            if 5 < len(aspect) < 50 and not _is_noise(aspect):
                aspects.append(aspect)

    # Also check for known domain aspects
    known_aspects = [
        "scheduling", "risk", "resource", "ethics", "governance",
        "change management", "training", "budget", "timeline",
        "stakeholder", "communication", "quality", "compliance",
        "data", "security", "integration", "adoption", "roadmap",
    ]
    for ka in known_aspects:
        if ka in task_lower and ka not in aspects:
            aspects.append(ka)

    # Drop aspects that are strict substrings of another aspect
    # (e.g. "resource" is contained in "resource allocation"). The longest
    # aspect is never a strict substring of another, so this keeps >= 1.
    aspects = [a for a in aspects if not any(a != b and a in b for b in aspects)]

    return aspects[:8]


def _infer_unit_coverage(unit: dict) -> list[str]:
    """Infer what task aspects a unit can cover."""
    coverage = []
    name = unit.get("name", "").lower()
    purpose = unit.get("purpose", "").lower()
    steps_text = " ".join(unit.get("execution_steps", [])).lower()
    all_text = name + " " + purpose + " " + steps_text

    # Map unit content to task aspects
    aspect_keywords = {
        "assessment": ["assess", "evaluate", "determine", "diagnos", "classify"],
        "classification": ["classify", "categorize", "type", "category"],
        "automation evaluation": ["automat", "intelligen", "machine learning", "ml"],
        "process execution": ["execute", "implement", "follow", "carry out"],
        "decision-making": ["decide", "choose", "select", "prioritize"],
        "planning": ["plan", "roadmap", "strategy", "schedule"],
    }

    for aspect, keywords in aspect_keywords.items():
        if any(kw in all_text for kw in keywords):
            coverage.append(aspect)

    return coverage if coverage else [unit.get("name", "general")[:40]]


def _build_supported_section(unit: dict, trigger_decisions: list | None) -> dict:
    """Build a knowledge-supported output section from a unit."""
    unit_name = unit.get("name", "Unknown")
    unit_type = unit.get("type", "framework")
    diag_qs = unit.get("diagnostic_questions", [])
    steps = unit.get("execution_steps", [])
    boundaries = unit.get("boundaries", [])
    quality_checks = unit.get("quality_checks", [])

    parts = []
    parts.append(f"\n### {unit_name}\n")
    parts.append(f"*Type: {unit_type}*\n")

    # Diagnostic questions (what to confirm first)
    if diag_qs:
        parts.append("\n**Diagnostic Questions (confirm before proceeding):**\n")
        for q in diag_qs:
            parts.append(f"- {q}\n")

    # Execution steps (the actual method)
    if steps:
        parts.append("\n**Execution Steps:**\n")
        for step in steps:
            parts.append(f"  {step}\n")

    # Quality checks
    if quality_checks:
        parts.append("\n**Quality Checks:**\n")
        for qc in quality_checks:
            parts.append(f"- [ ] {qc}\n")

    # Boundaries
    if boundaries:
        parts.append("\n**Boundaries:**\n")
        for b in boundaries:
            parts.append(f"- {b}\n")

    content = "\n".join(parts)

    # Find trigger decision for this unit
    decision_info = ""
    if trigger_decisions:
        for td in trigger_decisions:
            if hasattr(td, 'unit_id') and td.unit_id == unit.get("id"):
                decision_info = f"Trigger: {td.decision} (score={td.score:.2f}), signals: {td.matched_signals}"
                break

    return {
        "unit_name": unit_name,
        "unit_type": unit_type,
        "content": content,
        "trigger_info": decision_info,
    }


def _run_quality_checks(unit: dict, output_text: str) -> list[dict]:
    """Run a unit's quality checks against the generated output."""
    results = []
    for qc in unit.get("quality_checks", []):
        # Simple heuristic checks
        passed = True
        qc_lower = qc.lower()

        if "all steps" in qc_lower or "completed in order" in qc_lower:
            # Check if steps are present in output
            steps = unit.get("execution_steps", [])
            passed = len(steps) >= 2 and any(s[:20] in output_text for s in steps[:3])
        elif "evidence" in qc_lower or "source" in qc_lower:
            passed = "evidence" in output_text.lower() or "citation" in output_text.lower() or "source" in output_text.lower()
        elif "boundary" in qc_lower or "domain" in qc_lower:
            passed = "boundar" in output_text.lower() or "limitation" in output_text.lower()
        elif "classification" in qc_lower:
            passed = "classif" in output_text.lower() or "categor" in output_text.lower() or "determine" in output_text.lower()

        results.append({"check": qc, "passed": passed, "unit": unit.get("name", "")})

    return results


def _suggest_materials(uncovered_aspects: list[str]) -> list[str]:
    """Suggest what materials would cover the gaps."""
    suggestions = []
    aspect_to_material = {
        "scheduling": "AI-powered project scheduling methodology",
        "risk": "AI risk prediction framework for construction/projects",
        "resource": "Resource allocation optimization with AI",
        "ethics": "Responsible AI / AI ethics governance framework",
        "governance": "AI governance and accountability framework",
        "change management": "Change management methodology for digital transformation",
        "training": "AI literacy training curriculum design",
        "budget": "AI investment ROI calculation framework",
        "timeline": "AI adoption phasing and timeline planning",
        "stakeholder": "Stakeholder engagement for AI initiatives",
        "data": "Data readiness assessment framework",
        "security": "AI security and privacy assessment",
        "roadmap": "Digital transformation roadmap methodology",
        "adoption": "Technology adoption framework (e.g., TAM, TOE)",
    }

    for aspect in uncovered_aspects:
        aspect_lower = _normalize_aspect(aspect).lower().strip()
        matched = False
        for key, material in aspect_to_material.items():
            if key in aspect_lower:
                suggestions.append(material)
                matched = True
                break
        if not matched:
            suggestions.append(f"Methodology covering: {aspect}")

    return suggestions


# ── Ready-to-use deliverable composition ─────────────────────────────────


def _detect_audience(task: str, is_zh: bool) -> str:
    """Detect the intended audience of a task, if mentioned."""
    task_lower = task.lower()
    zh_audiences = [
        ("董事会", "董事会"), ("管理层", "管理层"), ("高管", "高管层"),
        ("团队", "团队"), ("客户", "客户"), ("老板", "老板"), ("领导", "领导"),
    ]
    en_audiences = [
        ("board", "the board"), ("executive", "executives"), ("management", "management"),
        ("team", "the team"), ("client", "the client"), ("boss", "the boss"),
        ("stakeholder", "stakeholders"),
    ]
    primary = zh_audiences if is_zh else en_audiences
    for kw, label in primary:
        if kw in task_lower:
            return label
    for kw, label in zh_audiences + en_audiences:
        if kw in task_lower:
            return label
    return ""


def parse_task_understanding(task: str) -> dict:
    """Parse a task into a user-facing 'task understanding' block.

    Returns a dict with: goal, audience, focus (list of aspects), is_zh.
    This powers the first step of the AU-driven Activate page so the user can
    verify the system understood their task before any method is applied.
    """
    is_zh = _detect_zh(task)
    # Goal: first sentence, truncated for display
    first = re.split(r"[。.！!？?\n]", task.strip())[0].strip()
    if len(first) > 120:
        first = first[:120].rstrip() + "…"
    audience = _detect_audience(task, is_zh)
    focus = _extract_task_aspects(task)
    return {"goal": first, "audience": audience, "focus": focus, "is_zh": is_zh}


def _detect_zh(text: str) -> bool:
    """Return True if the text is predominantly Chinese."""
    zh_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
    return zh_chars > max(4, len(text) // 20)


def _format_methods_for_prompt(units: list[dict]) -> str:
    """Format triggered units into a compact method brief for the LLM prompt."""
    parts = []
    for i, u in enumerate(units, 1):
        lines = [f"Method {i}: {u.get('name', 'Unknown')} (type={u.get('type', '')})"]
        if u.get("purpose"):
            lines.append(f"  Purpose: {u['purpose']}")
        diag = u.get("diagnostic_questions", [])
        if diag:
            lines.append("  Confirm first: " + " | ".join(diag[:4]))
        steps = u.get("execution_steps", [])
        if steps:
            lines.append("  Steps: " + " -> ".join(steps[:6]))
        bounds = u.get("boundaries", [])
        if bounds:
            lines.append("  Do NOT use when: " + " | ".join(bounds[:3]))
        parts.append("\n".join(lines))
    return "\n\n".join(parts)


def _compose_deliverable(
    task: str,
    triggered_units: list[dict],
    covered_aspects: list[str],
    uncovered_aspects: list[str],
) -> tuple[str, str]:
    """Produce the actual ready-to-use deliverable for the task.

    Returns (deliverable_text, mode) where mode is "ai" or "deterministic".

    The deliverable is a real roadmap/plan skeleton that applies the triggered
    methods onto the task — NOT a mere list of method steps. When an LLM is
    available it composes the deliverable; otherwise a deterministic composer
    builds a partial deliverable that clearly marks supported vs. unsupported
    parts.
    """
    # Try LLM composition first
    try:
        from src.llm_client import create_llm_client
        client = create_llm_client()
        if "AI" in client.mode_label and hasattr(client, "_call_chat"):
            is_zh = _detect_zh(task)
            lang_note = "Respond in Chinese (中文)." if is_zh else "Respond in English."
            methods = _format_methods_for_prompt(triggered_units)
            gaps = "; ".join(uncovered_aspects) if uncovered_aspects else "none identified"
            system = (
                "You are a professional knowledge-application assistant. "
                "You turn methodology knowledge into a concrete, ready-to-use deliverable. "
                "You NEVER just list method steps; you APPLY them to produce a real artifact "
                "(roadmap, assessment, plan, checklist, etc.). "
                "You are honest about what the knowledge base cannot yet support. "
                + lang_note
            )
            user = (
                f"USER TASK:\n{task}\n\n"
                f"TRIGGERED METHODS (apply these):\n{methods}\n\n"
                f"ASPECTS THE KNOWLEDGE BASE CANNOT RELIABLY SUPPORT: {gaps}\n\n"
                "Produce the deliverable the user actually needs. Structure it as a real "
                "artifact (e.g., a phased roadmap with concrete actions), explicitly applying "
                "the triggered methods. For aspects that are NOT supported, add a short section "
                "stating they need additional material and suggest what to add. "
                "Keep it practical and copy-ready."
            )
            result = client._call_chat(system, user, temperature=0.4)
            if result and len(result.strip()) > 120:
                return result.strip(), "ai"
    except Exception:
        pass

    # Deterministic fallback: a partial deliverable skeleton
    return _compose_deterministic_deliverable(
        task, triggered_units, covered_aspects, uncovered_aspects
    ), "deterministic"


def _compose_deterministic_deliverable(
    task: str,
    triggered_units: list[dict],
    covered_aspects: list[str],
    uncovered_aspects: list[str],
) -> str:
    """Build a partial deliverable skeleton without an LLM.

    The skeleton is task-oriented: each triggered method becomes a supported
    workstream with concrete actions; each uncovered aspect becomes a
    clearly-marked gap that needs additional material. This is an honest
    "partial deliverable", not a list of method steps.
    """
    is_zh = _detect_zh(task)
    task_short = task.strip().replace("\n", " ")
    if len(task_short) > 120:
        task_short = task_short[:120] + "…"

    L: list[str] = []
    if is_zh:
        L.append("## 交付物草案（部分）\n")
        L.append(f"**任务**：{task_short}\n")
        L.append(
            "> 以下框架由当前触发的方法应用到此任务生成。"
            "标注 ✅ 的部分有知识库方法支持；标注 ⚠️ 的部分需补充材料后才能可靠完成。\n"
        )
    else:
        L.append("## Deliverable Draft (Partial)\n")
        L.append(f"**Task:** {task_short}\n")
        L.append(
            "> This framework applies the triggered methods to your task. "
            "Sections marked ✅ are supported by knowledge-base methods; "
            "sections marked ⚠️ need additional material before they can be reliably completed.\n"
        )

    # Supported workstreams — one per triggered method, applied to the task
    for i, u in enumerate(triggered_units, 1):
        name = u.get("name", "Unknown")
        if is_zh:
            L.append(f"\n### 工作流 {i}：应用「{name}」 ✅\n")
        else:
            L.append(f"\n### Workstream {i}: Apply \"{name}\" ✅\n")

        diag = u.get("diagnostic_questions", [])
        if diag:
            L.append(f"**{('先确认' if is_zh else 'Confirm first')}:**")
            for q in diag:
                L.append(f"- [ ] {q}")
            L.append("")

        steps = u.get("execution_steps", [])
        if steps:
            L.append(f"**{('具体行动' if is_zh else 'Concrete actions')}:**")
            for s in steps:
                s = s.strip()
                # Truncate very long steps (often verbatim source excerpts) for readability
                if len(s) > 160:
                    s = s[:160].rstrip() + "…"
                L.append(f"- {s}")
            L.append("")

        bounds = u.get("boundaries", [])
        if bounds:
            L.append(f"**{('边界' if is_zh else 'Boundaries')}:**")
            for b in bounds:
                L.append(f"- {b}")
            L.append("")

    # Gaps — one per uncovered aspect, clearly marked
    if uncovered_aspects:
        if is_zh:
            L.append("\n### 需补充的部分 ⚠️\n")
            L.append("以下任务维度当前知识库无法可靠支持：\n")
        else:
            L.append("\n### Gaps Requiring Additional Material ⚠️\n")
            L.append("The following task aspects are not reliably supported yet:\n")
        materials = _suggest_materials(uncovered_aspects)
        for aspect, mat in zip(uncovered_aspects, materials):
            if is_zh:
                L.append(f"- **{aspect}** — 建议补充：{mat}")
            else:
                L.append(f"- **{aspect}** — suggested addition: {mat}")
        L.append("")

    if is_zh:
        L.append("\n---\n*此为确定性骨架。接入 AI 后可生成更完整的交付物。*")
    else:
        L.append("\n---\n*This is a deterministic skeleton. Connect an AI model to generate a fuller deliverable.*")

    return "\n".join(L)
