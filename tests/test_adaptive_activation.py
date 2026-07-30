"""Tests for the Adaptive Memory Activation modules.

Covers:
- depth_router: routing logic
- activation_unit: schema, validation gates, storage
- trigger_engine: trigger/anti-trigger evaluation, vague task detection
- feedback: feedback recording
- deep_distill: deterministic extraction
"""

from __future__ import annotations

import pytest

from src.depth_router import route_depth, DepthDecision
from src.activation_unit import (
    create_empty_unit,
    validate_for_active,
    validate_distinctiveness,
    load_units,
    save_units,
    add_unit,
    get_unit,
    update_unit,
    delete_unit,
    activate_unit,
    list_active_units,
    list_draft_units,
    AU_FILE,
)
from src.trigger_engine import (
    evaluate_triggers,
    is_vague_task,
    generate_decoy_tests,
    run_decoy_test,
    TriggerDecision,
)
from src.feedback import (
    record_feedback,
    record_activation,
    get_feedback_summary,
    FEEDBACK_TYPES,
)


# ── Depth Router Tests ────────────────────────────────────────────────────


class TestDepthRouter:
    def test_user_override_wins(self):
        result = route_depth("short text", user_override="deep_distill")
        assert result.selected_depth == "deep_distill"
        assert result.confidence == "high"

    def test_short_text_routes_to_archive(self):
        result = route_depth("hello")
        assert result.selected_depth == "archive"

    def test_methodology_dense_routes_to_deep_distill(self):
        text = """
        Framework: The 5-Step Decision Process
        
        Step 1: Define the problem boundary
        Step 2: Identify stakeholders and their constraints
        Step 3: Apply the diagnostic checklist
        Step 4: Execute the decision rule — if condition A then action B
        Step 5: Run quality check against criteria
        
        Counterexample: Do not use this framework when the problem is purely technical.
        Anti-pattern: Applying without stakeholder buy-in leads to failure.
        
        Principle: Every decision must have a clear boundary and precondition.
        """
        result = route_depth(text)
        assert result.selected_depth == "deep_distill"
        assert result.confidence in ("high", "medium")

    def test_news_routes_to_archive(self):
        text = "Breaking news 2026-07-24: Company announces quarterly results. Deadline for submissions is 2026-08-01. This is a time-sensitive update about market conditions."
        result = route_depth(text)
        assert result.selected_depth in ("archive", "digest")

    def test_medium_article_routes_to_digest(self):
        text = """
        AI governance is becoming increasingly important for organizations.
        Several frameworks have been proposed to address accountability.
        In practice, most companies struggle with implementation.
        For instance, a recent study showed that 60% of firms lack clear ownership.
        This suggests that risk ownership needs more attention in board discussions.
        """ * 3  # Make it long enough
        result = route_depth(text)
        assert result.selected_depth in ("digest", "deep_distill")

    def test_intended_use_method_boosts_depth(self):
        text = "A short paragraph about a specific working method that has some structure."
        result = route_depth(text, intended_use="沉淀成方法长期复用")
        # Should be boosted by wants_method signal
        assert result.signals.get("wants_method") is True


# ── Activation Unit Tests ─────────────────────────────────────────────────


class TestActivationUnit:
    @pytest.fixture(autouse=True)
    def clean_au_storage(self, tmp_path, monkeypatch):
        """Redirect AU storage to temp file."""
        import src.activation_unit as au_mod
        test_file = tmp_path / "test_activation_units.json"
        monkeypatch.setattr(au_mod, "AU_FILE", test_file)
        monkeypatch.setattr(au_mod, "DATA_DIR", tmp_path)
        yield

    def test_create_empty_unit_has_all_fields(self):
        unit = create_empty_unit()
        assert unit["id"]
        assert unit["status"] == "draft"
        assert unit["type"] == "framework"
        assert isinstance(unit["triggers"], list)
        assert isinstance(unit["anti_triggers"], list)
        assert isinstance(unit["execution_steps"], list)
        assert isinstance(unit["usage"], dict)

    def test_validate_for_active_fails_on_empty(self):
        unit = create_empty_unit()
        valid, issues = validate_for_active(unit)
        assert not valid
        assert len(issues) >= 5  # Missing most required fields

    def test_validate_for_active_passes_complete_unit(self):
        unit = create_empty_unit()
        unit["name"] = "Test Framework"
        unit["purpose"] = "Solve specific problems"
        unit["evidence_spans"] = [{"document_id": "doc1", "text": "evidence here", "location": ""}]
        unit["triggers"] = [{"scenario": "When doing X", "signals": ["x"], "required_context": []}]
        unit["anti_triggers"] = [{"scenario": "When the task only asks to explain X conceptually without executing", "reason": "Problem shape mismatch"}]
        unit["diagnostic_questions"] = ["Is this task about executing X?"]
        unit["execution_steps"] = ["Step 1: Do A", "Step 2: Do B"]
        unit["boundaries"] = ["Only applies in context Z"]
        unit["quality_checks"] = ["Verify output matches expected"]
        unit["decoy_tests"] = {"should_trigger": [], "should_not_trigger": [], "boundary_cases": [], "pass_rate": 0.8, "last_tested_at": "2026-01-01T00:00:00"}
        valid, issues = validate_for_active(unit)
        assert valid, f"Issues: {issues}"

    def test_distinctiveness_rejects_generic(self):
        unit = create_empty_unit()
        unit["name"] = "Be innovative"
        unit["purpose"] = "要创新，要系统思考"
        passes, reason = validate_distinctiveness(unit)
        assert not passes

    def test_distinctiveness_accepts_specific(self):
        unit = create_empty_unit()
        unit["name"] = "Extractivism Cost Distribution Analysis"
        unit["purpose"] = "Identify whether a business model privatizes gains while socializing environmental costs"
        unit["execution_steps"] = [
            "Map all revenue streams and their beneficiaries",
            "Identify externalized costs (environmental, social, health)",
            "Compare short-term profit vs long-term stakeholder cost",
        ]
        passes, reason = validate_distinctiveness(unit)
        assert passes

    def test_storage_crud(self):
        unit = create_empty_unit()
        unit["name"] = "Test Unit"
        add_unit(unit)

        loaded = get_unit(unit["id"])
        assert loaded is not None
        assert loaded["name"] == "Test Unit"

        update_unit(unit["id"], {"name": "Updated Unit"})
        loaded = get_unit(unit["id"])
        assert loaded["name"] == "Updated Unit"

        delete_unit(unit["id"])
        assert get_unit(unit["id"]) is None

    def test_activate_unit_validates_first(self):
        unit = create_empty_unit()
        unit["name"] = "Incomplete Unit"
        add_unit(unit)

        success, issues = activate_unit(unit["id"])
        assert not success
        assert len(issues) > 0


# ── Trigger Engine Tests ──────────────────────────────────────────────────


class TestTriggerEngine:
    def test_vague_task_detection(self):
        assert is_vague_task("我要投标")
        assert is_vague_task("write report")
        assert is_vague_task("short")
        assert not is_vague_task("Evaluate whether our AI governance framework addresses accountability gaps in client projects")

    def test_vague_task_gets_no_trigger(self):
        unit = create_empty_unit()
        unit["id"] = "test-unit-1"
        unit["name"] = "AI Governance Framework"
        unit["triggers"] = [{"scenario": "AI governance assessment", "signals": ["governance"], "required_context": []}]
        decisions = evaluate_triggers("我要投标", [unit])
        assert all(d.decision == "do_not_trigger" for d in decisions)
        assert decisions[0].clarification_question  # Should have clarification

    def test_matching_task_triggers(self):
        unit = create_empty_unit()
        unit["id"] = "test-unit-2"
        unit["name"] = "Climate Risk Assessment Framework"
        unit["purpose"] = "Evaluate climate risk exposure for industrial assets"
        unit["triggers"] = [{"scenario": "climate risk assessment for industrial operations", "signals": ["climate", "risk", "industrial"], "required_context": []}]
        unit["anti_triggers"] = [{"scenario": "financial depreciation calculation", "reason": "Pure accounting task"}]

        decisions = evaluate_triggers(
            "I need to assess the climate risk exposure for our industrial client's manufacturing assets",
            [unit],
        )
        assert decisions[0].decision in ("trigger", "maybe")
        assert decisions[0].score > 0

    def test_anti_trigger_blocks(self):
        unit = create_empty_unit()
        unit["id"] = "test-unit-3"
        unit["name"] = "Sustainability Framework"
        unit["purpose"] = "Evaluate sustainability of business models"
        unit["triggers"] = [{"scenario": "sustainability evaluation", "signals": ["sustainability"], "required_context": []}]
        unit["anti_triggers"] = [{"scenario": "calculate depreciation for equipment", "reason": "Pure accounting task"}]

        decisions = evaluate_triggers(
            "Calculate the depreciation schedule for manufacturing equipment using straight-line method",
            [unit],
        )
        # Anti-trigger should block
        assert decisions[0].decision == "do_not_trigger"

    def test_decoy_test_generation(self):
        unit = create_empty_unit()
        unit["name"] = "Cost Externalization Analysis"
        unit["triggers"] = [{"scenario": "Evaluate business model externalities", "signals": [], "required_context": []}]
        unit["anti_triggers"] = [{"scenario": "Simple price comparison", "reason": "Not about externalities"}]

        tests = generate_decoy_tests(unit)
        assert len(tests["should_trigger"]) >= 1
        assert len(tests["should_not_trigger"]) >= 1
        assert len(tests["boundary_cases"]) >= 1


# ── Feedback Tests ────────────────────────────────────────────────────────


class TestFeedback:
    @pytest.fixture(autouse=True)
    def clean_au_storage(self, tmp_path, monkeypatch):
        """Redirect AU storage to temp file."""
        import src.activation_unit as au_mod
        test_file = tmp_path / "test_activation_units.json"
        monkeypatch.setattr(au_mod, "AU_FILE", test_file)
        monkeypatch.setattr(au_mod, "DATA_DIR", tmp_path)
        yield

    def test_record_useful_feedback(self):
        unit = create_empty_unit()
        unit["name"] = "Test Unit"
        add_unit(unit)

        result = record_feedback(unit["id"], "useful", task="test task")
        assert result["success"]
        assert result["usage_summary"]["useful"] == 1

    def test_record_false_trigger(self):
        unit = create_empty_unit()
        unit["name"] = "Test Unit"
        add_unit(unit)

        result = record_feedback(unit["id"], "false_trigger", task="wrong task")
        assert result["success"]
        assert result["usage_summary"]["false_triggers"] == 1
        assert len(result["suggestions"]) > 0
        assert result["suggestions"][0]["action"] == "add_anti_trigger"

    def test_invalid_feedback_type(self):
        unit = create_empty_unit()
        add_unit(unit)
        result = record_feedback(unit["id"], "invalid_type")
        assert not result["success"]

    def test_feedback_does_not_modify_unit_core(self):
        unit = create_empty_unit()
        unit["name"] = "Original Name"
        unit["purpose"] = "Original Purpose"
        add_unit(unit)

        record_feedback(unit["id"], "false_trigger", task="wrong task")

        # Core fields should be unchanged
        loaded = get_unit(unit["id"])
        assert loaded["name"] == "Original Name"
        assert loaded["purpose"] == "Original Purpose"


# ── Activation vs Feedback Counting Tests (P0 data-model fix) ─────────────


class TestActivationCounting:
    """activation_count must only change on a real activation event.

    Feedback (useful / missing_context / ...) updates its OWN counter and
    must NEVER inflate activation_count, no matter how many feedback entries
    are submitted for the same activation.
    """

    @pytest.fixture(autouse=True)
    def clean_au_storage(self, tmp_path, monkeypatch):
        """Redirect AU storage to temp file."""
        import src.activation_unit as au_mod
        test_file = tmp_path / "test_activation_units.json"
        monkeypatch.setattr(au_mod, "AU_FILE", test_file)
        monkeypatch.setattr(au_mod, "DATA_DIR", tmp_path)
        yield

    def _make_unit(self) -> dict:
        unit = create_empty_unit()
        unit["name"] = "Counting Test Unit"
        add_unit(unit)
        return unit

    def test_single_activation_sets_count_to_one(self):
        """1. After one real activation, activation_count == 1."""
        unit = self._make_unit()
        event_id = record_activation([unit["id"]], task="real task")

        assert event_id  # a non-empty event id is returned
        loaded = get_unit(unit["id"])
        assert loaded["usage"]["activation_count"] == 1
        # The activation event is logged with its id
        assert loaded["_activation_log"][0]["activation_event_id"] == event_id

    def test_useful_feedback_does_not_change_activation_count(self):
        """2. Submitting 'useful' keeps activation_count == 1."""
        unit = self._make_unit()
        event_id = record_activation([unit["id"]], task="real task")
        record_feedback(unit["id"], "useful", task="real task",
                        activation_event_id=event_id)

        loaded = get_unit(unit["id"])
        assert loaded["usage"]["activation_count"] == 1

    def test_missing_context_feedback_does_not_change_activation_count(self):
        """3. Then submitting 'missing_context' STILL keeps activation_count == 1."""
        unit = self._make_unit()
        event_id = record_activation([unit["id"]], task="real task")
        record_feedback(unit["id"], "useful", task="real task",
                        activation_event_id=event_id)
        record_feedback(unit["id"], "missing_context", task="real task",
                        comment="need org size", activation_event_id=event_id)

        loaded = get_unit(unit["id"])
        assert loaded["usage"]["activation_count"] == 1

    def test_feedback_counters_increment_independently(self):
        """4. useful_count and missing_context_count increase separately."""
        unit = self._make_unit()
        event_id = record_activation([unit["id"]], task="real task")
        record_feedback(unit["id"], "useful", task="real task",
                        activation_event_id=event_id)
        record_feedback(unit["id"], "missing_context", task="real task",
                        comment="need org size", activation_event_id=event_id)

        loaded = get_unit(unit["id"])
        usage = loaded["usage"]
        assert usage["useful_count"] == 1
        assert usage["missing_context_count"] == 1
        # Other feedback counters stay at zero
        assert usage["not_useful_count"] == 0
        assert usage["false_trigger_count"] == 0
        assert usage["expression_issue_count"] == 0
        # activation_count is untouched by feedback
        assert usage["activation_count"] == 1

    def test_second_real_activation_increments_to_two(self):
        """5. Only a second REAL activation moves activation_count to 2."""
        unit = self._make_unit()
        record_activation([unit["id"]], task="first task")
        # Several feedback entries for the first activation — no count change
        record_feedback(unit["id"], "useful", task="first task")
        record_feedback(unit["id"], "missing_context", task="first task")
        record_feedback(unit["id"], "not_useful", task="first task")
        assert get_unit(unit["id"])["usage"]["activation_count"] == 1

        # A genuine second activation
        record_activation([unit["id"]], task="second task")
        loaded = get_unit(unit["id"])
        assert loaded["usage"]["activation_count"] == 2
        assert len(loaded["_activation_log"]) == 2

    def test_feedback_links_to_activation_event(self):
        """Feedback entries carry the activation_event_id they belong to."""
        unit = self._make_unit()
        event_id = record_activation([unit["id"]], task="real task")
        record_feedback(unit["id"], "useful", task="real task",
                        activation_event_id=event_id)

        loaded = get_unit(unit["id"])
        log_entry = loaded["_feedback_log"][-1]
        assert log_entry["activation_event_id"] == event_id


# ── Deep Distill Tests ────────────────────────────────────────────────────


class TestDeepDistill:
    def test_deterministic_extraction_finds_steps(self):
        from src.deep_distill import deep_distill

        text = """
        The Extractivism Assessment Framework
        
        Step 1: Map all revenue streams and identify who captures the value
        Step 2: Identify externalized costs — environmental damage, health impacts, infrastructure burden
        Step 3: Calculate the ratio of private profit to socialized cost
        Step 4: If ratio exceeds threshold, flag as extractive pattern
        Step 5: Propose rebalancing mechanisms (taxes, bonds, insurance requirements)
        
        Counterexample: A purely digital service with no environmental externality should not trigger this framework.
        """
        candidates = deep_distill(text, document_id="test-doc", source_title="Test Source")
        assert len(candidates) >= 1
        # At least one should have execution steps
        has_steps = any(len(c.get("execution_steps", [])) >= 2 for c in candidates)
        assert has_steps

    def test_generic_text_produces_fewer_units(self):
        from src.deep_distill import deep_distill

        text = "This is a simple news article about market trends. Nothing methodological here. Just facts and figures about quarterly earnings."
        candidates = deep_distill(text, document_id="test-doc-2", source_title="News")
        # Should produce 0 or very few candidates (no methodology)
        assert len(candidates) <= 2
