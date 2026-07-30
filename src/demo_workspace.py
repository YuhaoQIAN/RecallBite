"""Demo Workspace for RecallBite 记忆面包.

Provides a clearly separated demo dataset (5 Activation Units extracted from
"AI Essentials for Project Professionals") so that reviewers can try the
product without touching real user data.

Activation:
- Environment variable: RECALLBITE_DEMO_MODE=true
- Or: "Load Demo Workspace" button in the app settings

Three clearly separated files (they must NOT be mixed):

- ``demo_seed_units.json``     — READ-ONLY. The 5 standard example units with
  pristine usage counters. This is the reproducible starting state. It is never
  written to at runtime.
- ``demo_runtime_units.json``  — The live demo workspace. All demo Activation
  Unit operations (new drafts, feedback, activations) read/write here. Created
  from the seed on first use or via "Reset demo workspace".
- ``acceptance_test_units.json`` — Scratch space reserved for acceptance/UI
  testing, kept separate from both the seed and the runtime workspace.

When demo mode is ON, all Activation Unit operations read/write the runtime
file — NEVER ``activation_units.json`` (real user data).
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

import src.activation_unit as au_mod

DATA_DIR = Path(__file__).parent.parent / "data"

# Read-only reproducible starting state (5 standard example units).
DEMO_SEED_FILE = DATA_DIR / "demo_seed_units.json"
# Live demo workspace (created from the seed; all demo writes go here).
DEMO_RUNTIME_FILE = DATA_DIR / "demo_runtime_units.json"
# Reserved scratch space for acceptance / UI testing.
ACCEPTANCE_TEST_FILE = DATA_DIR / "acceptance_test_units.json"
# Real user data — never touched in demo mode.
REAL_AU_FILE = DATA_DIR / "activation_units.json"

# Backwards-compatible alias: the demo AU file is the runtime workspace.
DEMO_AU_FILE = DEMO_RUNTIME_FILE

# Demo task used for the product walkthrough
DEMO_TASK_EN = (
    "I'm leading a digital transformation project for a mid-size construction firm. "
    "They want to adopt AI for project scheduling, risk prediction, and resource allocation. "
    "I need to present a structured AI adoption roadmap to the board next week, "
    "including ethical considerations and change management steps."
)

DEMO_TASK_ZH = (
    "我正在负责一家中型建筑企业的数字化转型项目。他们希望把 AI 用在项目排期、"
    "风险预测和资源分配上。下周我要向董事会汇报一份结构化的 AI 采用路线图，"
    "需要包含伦理考量和变革管理步骤。"
)


def is_demo_mode_env() -> bool:
    """Check if demo mode is requested via environment variable."""
    return os.environ.get("RECALLBITE_DEMO_MODE", "").lower() in ("1", "true", "yes")


def _reset_unit_runtime_state(unit: dict) -> dict:
    """Return a copy of a seed unit with pristine runtime/usage state.

    The seed must be a reproducible starting point, so per-run counters and
    logs are cleared while the unit's method content is preserved.
    """
    cleaned = json.loads(json.dumps(unit))  # deep copy
    cleaned["usage"] = {
        "activation_count": 0,
        "useful_count": 0,
        "not_useful_count": 0,
        "false_trigger_count": 0,
        "missing_context_count": 0,
        "expression_issue_count": 0,
        "last_used_at": "",
    }
    cleaned["_activation_log"] = []
    cleaned["_feedback_log"] = []
    return cleaned


def seed_demo_workspace() -> int:
    """(Re)build the runtime workspace from the read-only seed.

    This is the "重置示例工作区" (Reset demo workspace) operation. It overwrites
    ``demo_runtime_units.json`` with a clean copy of the 5 seed units (pristine
    usage counters). It NEVER touches ``activation_units.json`` (real data) and
    NEVER writes to the seed file.

    Returns:
        The number of units written to the runtime workspace.
    """
    if not DEMO_SEED_FILE.exists():
        raise FileNotFoundError(f"Demo seed file not found: {DEMO_SEED_FILE}")

    with open(DEMO_SEED_FILE, "r", encoding="utf-8") as f:
        seed_units = json.load(f)

    runtime_units = [_reset_unit_runtime_state(u) for u in seed_units]

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(DEMO_RUNTIME_FILE, "w", encoding="utf-8") as f:
        json.dump(runtime_units, f, ensure_ascii=False, indent=2)

    # If demo mode is currently active, make sure the storage points at the
    # freshly rebuilt runtime file.
    if au_mod.AU_FILE == DEMO_RUNTIME_FILE:
        au_mod.AU_FILE = DEMO_RUNTIME_FILE

    return len(runtime_units)


def ensure_demo_runtime() -> None:
    """Make sure the runtime workspace exists; seed it if missing.

    Called when demo mode is turned on so first-time use "just works" and every
    demo session can start from the same reproducible state.
    """
    if not DEMO_RUNTIME_FILE.exists() and DEMO_SEED_FILE.exists():
        seed_demo_workspace()


def apply_demo_mode(enabled: bool) -> None:
    """Point the AU storage at the demo runtime file or the real file.

    This is the ONLY place that switches storage — all other modules
    use au_mod.AU_FILE transparently.
    """
    if enabled:
        ensure_demo_runtime()
        au_mod.AU_FILE = DEMO_RUNTIME_FILE
    else:
        au_mod.AU_FILE = REAL_AU_FILE


def demo_units_available() -> bool:
    """Whether the demo dataset can be loaded (seed or runtime present)."""
    return DEMO_SEED_FILE.exists() or DEMO_RUNTIME_FILE.exists()


def backup_runtime(target: Path) -> Path:
    """Copy the current runtime workspace to ``target`` as evidence/backup.

    Used to preserve acceptance-test evidence (drafts + feedback records)
    before rebuilding a clean runtime workspace.
    """
    if not DEMO_RUNTIME_FILE.exists():
        raise FileNotFoundError(f"Demo runtime file not found: {DEMO_RUNTIME_FILE}")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(DEMO_RUNTIME_FILE, target)
    return target
