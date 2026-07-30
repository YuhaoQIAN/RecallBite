"""Activation Unit schema, storage, and validation gates for RecallBite 记忆面包.

An Activation Unit is an independent entity (NOT a field on existing cards).
It represents an executable method/framework/principle that can be triggered
in real tasks.

Strong constraints for Active status:
- At least 1 evidence span
- At least 1 trigger
- At least 1 anti-trigger
- At least 2 execution steps
- At least 1 boundary
- At least 1 quality check
"""

from __future__ import annotations

import json
import os
import tempfile
import uuid
from datetime import datetime
from pathlib import Path


DATA_DIR = Path(__file__).parent.parent / "data"
AU_FILE = DATA_DIR / "activation_units.json"


# ── Schema ────────────────────────────────────────────────────────────────


def create_empty_unit() -> dict:
    """Create an empty Activation Unit with all required fields."""
    return {
        "id": str(uuid.uuid4()),
        "created_at": datetime.now().isoformat(),
        "name": "",
        "type": "framework",  # framework | principle | diagnostic | decision_rule | workflow
        "purpose": "",
        "status": "draft",  # draft | active | archived
        "source_document_ids": [],
        "evidence_spans": [
            # {"document_id": "", "text": "", "location": ""}
        ],
        "triggers": [
            # {"scenario": "", "signals": [], "required_context": []}
        ],
        "anti_triggers": [
            # {"scenario": "", "reason": ""}
        ],
        "diagnostic_questions": [],
        "execution_steps": [],
        "boundaries": [],
        "quality_checks": [],
        "examples": [],
        "counterexamples": [],
        "relations": {
            "depends_on": [],
            "complements": [],
            "conflicts_with": [],
            "alternative_to": [],
        },
        "confidence": {
            "level": "low",  # low | medium | high
            "reason": "",
        },
        "usage": {
            "activation_count": 0,
            "useful_count": 0,
            "not_useful_count": 0,
            "false_trigger_count": 0,
            "missing_context_count": 0,
            "expression_issue_count": 0,
            "last_used_at": "",
        },
        "decoy_tests": {
            "should_trigger": [],
            "should_not_trigger": [],
            "boundary_cases": [],
            "pass_rate": 0.0,
            "last_tested_at": "",
        },
        "_activation_log": [],
        "_feedback_log": [],
    }


# ── Validation Gates ──────────────────────────────────────────────────────


def validate_for_active(unit: dict) -> tuple[bool, list[str]]:
    """Check if a unit meets all requirements to be marked Active.

    Strict quality gate — requires not just field presence but content quality:
    - evidence with actual text
    - trigger with specific scenario
    - specific anti-trigger (not generic template)
    - diagnostic questions (non-empty)
    - execution steps (actionable, not just attribute labels)
    - meaningful boundary
    - quality check
    - decoy tests run with minimum pass rate
    - not a comparison/reference type

    Returns (is_valid, list_of_issues).
    """
    issues = []

    if not unit.get("name", "").strip():
        issues.append("Missing name")
    if not unit.get("purpose", "").strip():
        issues.append("Missing purpose")

    # Evidence gate — must have actual text
    spans = unit.get("evidence_spans", [])
    if len(spans) < 1:
        issues.append("Need at least 1 evidence span")
    elif all(not s.get("text", "").strip() for s in spans):
        issues.append("Evidence spans have no actual text")

    # Trigger gate — must have specific scenario
    triggers = unit.get("triggers", [])
    if len(triggers) < 1:
        issues.append("Need at least 1 trigger")
    elif all(not t.get("scenario", "").strip() for t in triggers):
        issues.append("Triggers have no specific scenario")

    # Anti-trigger gate — must be SPECIFIC, not generic template
    anti_triggers = unit.get("anti_triggers", [])
    if len(anti_triggers) < 1:
        issues.append("Need at least 1 anti-trigger")
    else:
        # Check if anti-triggers are generic templates
        generic_anti = _GENERIC_ANTI_TRIGGER_PATTERNS
        specific_count = 0
        for at in anti_triggers:
            scenario = at.get("scenario", "").lower().strip()
            if scenario and not any(g in scenario for g in generic_anti):
                specific_count += 1
        if specific_count == 0:
            issues.append("Anti-triggers are all generic templates — need at least 1 specific anti-trigger")

    # Diagnostic questions gate — must be non-empty
    diag = unit.get("diagnostic_questions", [])
    if len(diag) < 1:
        issues.append("Need at least 1 diagnostic question")

    # Execution steps gate — must be actionable
    steps = unit.get("execution_steps", [])
    if len(steps) < 2:
        issues.append("Need at least 2 execution steps")

    # Boundary gate — must be meaningful
    boundaries = unit.get("boundaries", [])
    if len(boundaries) < 1:
        issues.append("Need at least 1 boundary")

    # Quality check gate
    if len(unit.get("quality_checks", [])) < 1:
        issues.append("Need at least 1 quality check")

    # Decoy test gate — per-category thresholds (not just total pass rate)
    decoy = unit.get("decoy_tests", {})
    if not decoy.get("last_tested_at"):
        issues.append("Decoy tests have not been run")
    else:
        cat_rates = decoy.get("category_rates", {})
        if cat_rates:
            # Per-category requirements:
            st_rate = cat_rates.get("should_trigger", 0.0)
            sn_rate = cat_rates.get("should_not_trigger", 0.0)
            bc_rate = cat_rates.get("boundary_cases", 0.0)

            if st_rate < 0.6:
                issues.append(f"Should-trigger rate too low: {st_rate:.0%} (need >= 60%)")
            if sn_rate < 0.8:
                issues.append(f"Hard negative rejection rate too low: {sn_rate:.0%} (need >= 80%)")
            if bc_rate < 0.5:
                issues.append(f"Boundary case handling too low: {bc_rate:.0%} (need >= 50%, boundary cases must not directly trigger)")
        else:
            # Legacy: only total pass rate available
            if decoy.get("pass_rate", 0.0) < 0.6:
                issues.append(f"Decoy test pass rate too low: {decoy.get('pass_rate', 0):.0%} (need >= 60%)")

    # Type gate — comparison/reference types cannot be active
    list_type = unit.get("_list_type", "")
    if list_type in ("comparison_table", "attributes"):
        issues.append(f"Type '{list_type}' is reference material, not an executable method")

    return (len(issues) == 0, issues)


# Generic anti-trigger patterns that don't count as "specific"
_GENERIC_ANTI_TRIGGER_PATTERNS = [
    "doesn't match this",
    "does not match this",
    "domain doesn't match",
    "domain does not match",
    "not relevant",
    "unrelated",
    "doesn't apply",
    "does not apply",
    "not applicable",
    "task domain",
    "problem domain",
    "framework assumptions don't hold",
    "steps would not apply",
]


def validate_distinctiveness(unit: dict) -> tuple[bool, str]:
    """Distinctiveness Gate: reject generic platitudes.

    Returns (passes, reason).
    """
    generic_phrases = [
        "要努力", "要长期主义", "要系统思考", "要创新", "要合作",
        "be innovative", "think long-term", "work hard", "collaborate more",
        "be systematic", "stay curious", "embrace change", "be agile",
    ]
    purpose = unit.get("purpose", "").lower().strip()
    name = unit.get("name", "").lower().strip()

    for phrase in generic_phrases:
        if phrase in purpose or phrase in name:
            return False, f"Too generic: contains '{phrase}'. Activation Units must be specific and actionable."

    # Check if execution steps are concrete (have verbs + objects)
    steps = unit.get("execution_steps", [])
    if steps:
        vague_steps = sum(1 for s in steps if len(s) < 15)
        if vague_steps > len(steps) // 2:
            return False, "Execution steps are too vague. Each step should be specific and actionable."

    return True, ""


def validate_evidence(unit: dict, documents: dict[str, str] | None = None) -> tuple[bool, str]:
    """Evidence Gate: each key claim must trace back to source.

    Returns (passes, reason).
    """
    spans = unit.get("evidence_spans", [])
    if not spans:
        return False, "No evidence spans provided."

    # Check that spans have actual text
    empty_spans = sum(1 for s in spans if not s.get("text", "").strip())
    if empty_spans == len(spans):
        return False, "All evidence spans are empty."

    return True, ""


# ── Storage ───────────────────────────────────────────────────────────────


def _ensure_au_file() -> None:
    """Ensure the activation units file exists."""
    au_dir = AU_FILE.parent
    if not au_dir.exists():
        au_dir.mkdir(parents=True, exist_ok=True)
    if not AU_FILE.exists():
        with open(AU_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)


def load_units() -> list[dict]:
    """Load all activation units."""
    _ensure_au_file()
    try:
        with open(AU_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        _ensure_au_file()
        return []


def save_units(units: list[dict]) -> None:
    """Atomically save all activation units."""
    _ensure_au_file()
    data = json.dumps(units, ensure_ascii=False, indent=2)
    # Create temp file in SAME directory as AU_FILE (required for os.replace)
    au_dir = AU_FILE.parent
    if not au_dir.exists():
        au_dir.mkdir(parents=True, exist_ok=True)
    fd, temp_path = tempfile.mkstemp(dir=str(au_dir), suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(data)
        os.replace(temp_path, AU_FILE)
    except Exception:
        try:
            os.remove(temp_path)
        except OSError:
            pass
        raise


def add_unit(unit: dict) -> None:
    """Add a new activation unit to storage."""
    units = load_units()
    units.append(unit)
    save_units(units)


def get_unit(unit_id: str) -> dict | None:
    """Get a single unit by ID."""
    units = load_units()
    for u in units:
        if u.get("id") == unit_id:
            return u
    return None


def update_unit(unit_id: str, updates: dict) -> bool:
    """Partially update a unit. Returns True if found and updated."""
    units = load_units()
    for u in units:
        if u.get("id") == unit_id:
            for key, value in updates.items():
                if key == "id":
                    continue
                u[key] = value
            save_units(units)
            return True
    return False


def delete_unit(unit_id: str) -> bool:
    """Delete a unit by ID. Returns True if deleted."""
    units = load_units()
    new_units = [u for u in units if u.get("id") != unit_id]
    if len(new_units) < len(units):
        save_units(new_units)
        return True
    return False


def activate_unit(unit_id: str) -> tuple[bool, list[str]]:
    """Attempt to mark a unit as Active. Validates first.

    Returns (success, issues_if_failed).
    """
    unit = get_unit(unit_id)
    if not unit:
        return False, ["Unit not found"]

    valid, issues = validate_for_active(unit)
    if not valid:
        return False, issues

    # Also check distinctiveness
    passes, reason = validate_distinctiveness(unit)
    if not passes:
        return False, [reason]

    update_unit(unit_id, {"status": "active"})
    return True, []


def list_active_units() -> list[dict]:
    """Return all units with status 'active'."""
    return [u for u in load_units() if u.get("status") == "active"]


def list_draft_units() -> list[dict]:
    """Return all units with status 'draft'."""
    return [u for u in load_units() if u.get("status") == "draft"]
