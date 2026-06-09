"""
test_gate_evaluator.py

Gate behavior tests for all 5 ResearchConductor studies.

These tests serve double duty: they verify the gate logic is correct AND
they document the expected autonomy outcome for each planned study.
The pass/fail pattern here maps directly to the gate trigger log data
that feeds the FAccT 2027 paper analysis.

Run: pytest tests/test_gate_evaluator.py -v
"""

import pytest
from gates.gate_evaluator import GateEvaluator, GateResult

EVALUATOR = GateEvaluator("gates/gates.yaml")


# ─────────────────────────────────────────────────────────────────────────────
# Study 1 — Icon concept test (interview)
# Expected: all gates pass → full autonomous execution
# ─────────────────────────────────────────────────────────────────────────────

class TestStudy1ConceptTest:
    """Concept tests are low-stakes and should run fully autonomously."""

    def test_study_type_passes(self):
        result = EVALUATOR.check_study_type("concept_test", "interview")
        assert result.passed, result.reason

    def test_distress_passes_with_clean_transcript(self):
        transcript = (
            "Facilitator: What does this icon mean to you? "
            "Participant: Looks like a settings cog. Pretty clear to me."
        )
        result = EVALUATOR.check_distress(transcript, "interview")
        assert result.passed, result.reason

    def test_completion_passes_with_all_completing(self):
        result = EVALUATOR.check_completion_rate(5, 5, "interview")
        assert result.passed, result.reason


# ─────────────────────────────────────────────────────────────────────────────
# Study 2 — Checkout usability test
# Expected: all gates pass → full autonomous execution
# ─────────────────────────────────────────────────────────────────────────────

class TestStudy2CheckoutUsability:
    """Simple task completion tests should run fully autonomously."""

    def test_study_type_passes(self):
        result = EVALUATOR.check_study_type("task_completion", "usability_test")
        assert result.passed, result.reason

    def test_distress_gate_does_not_apply_to_usability_test(self):
        # usability_test is not in distress gate's applies_to list
        # even with heavy distress language, gate auto-passes
        heavy_distress = "give up give up hate this makes no sense frustrated"
        result = EVALUATOR.check_distress(heavy_distress, "usability_test")
        assert result.passed
        assert "not applicable" in result.reason

    def test_completion_passes_with_most_completing(self):
        result = EVALUATOR.check_completion_rate(4, 5, "usability_test")
        assert result.passed, result.reason  # 80% > 60% threshold


# ─────────────────────────────────────────────────────────────────────────────
# Study 3 — Error message frustration probe (interview)
# Expected: distress gate fires → immediate human review
# ─────────────────────────────────────────────────────────────────────────────

class TestStudy3FrustrationProbe:
    """Frustration probes with distress-prone personas should trigger the distress gate."""

    def test_distress_fires_on_multiple_keyword_hits(self):
        transcript = (
            "Facilitator: What was that experience like? "
            "Participant: I was so frustrated — I wanted to give up. "
            "This makes no sense to me at all."
        )
        result = EVALUATOR.check_distress(transcript, "interview")
        assert not result.passed
        assert result.halt_immediately
        assert result.triggered_by is not None

    def test_distress_halts_immediately(self):
        transcript = "Participant: I give up. Hate this. Confused."
        result = EVALUATOR.check_distress(transcript, "interview")
        assert result.halt_immediately

    def test_single_keyword_hit_does_not_fire(self):
        # One keyword hit is below the threshold of 2
        transcript = "Participant: I'm a bit frustrated but I can work through it."
        result = EVALUATOR.check_distress(transcript, "interview")
        assert result.passed  # 1 hit < threshold of 2

    def test_study_type_passes_for_frustration_probe(self):
        # Frustration probe is a valid autonomous study type
        result = EVALUATOR.check_study_type("frustration_probe", "interview")
        assert result.passed


# ─────────────────────────────────────────────────────────────────────────────
# Study 4 — Senior vs junior form labels (survey, segmented)
# Expected: completion gate fires → human validates findings
# ─────────────────────────────────────────────────────────────────────────────

class TestStudy4SegmentedFormLabels:
    """Segmented studies with small per-group N should trigger the completion gate."""

    def test_completion_fires_with_low_rate(self):
        # 1 of 3 participants completed → 33% < 60% threshold
        result = EVALUATOR.check_completion_rate(1, 3, "survey")
        assert not result.passed

    def test_completion_fires_below_minimum_participant_count(self):
        # Even 100% rate fails if n < 3
        result = EVALUATOR.check_completion_rate(2, 2, "survey")
        assert not result.passed
        assert "insufficient participants" in result.reason

    def test_completion_passes_at_exactly_threshold(self):
        # 3 of 5 = 60% = exactly at threshold → passes
        result = EVALUATOR.check_completion_rate(3, 5, "survey")
        assert result.passed

    def test_completion_passes_above_threshold(self):
        result = EVALUATOR.check_completion_rate(4, 5, "survey")
        assert result.passed  # 80% > 60%

    def test_study_type_passes_for_segmented_task(self):
        result = EVALUATOR.check_study_type("segmented_task", "survey")
        assert result.passed


# ─────────────────────────────────────────────────────────────────────────────
# Study 5 — Cross-cultural trust and feature adoption (interview)
# Expected: study type gate fires → human review before sessions begin
# ─────────────────────────────────────────────────────────────────────────────

class TestStudy5CrossCultural:
    """Cultural and strategic studies should require human review before any sessions run."""

    def test_study_type_fires_for_cultural(self):
        result = EVALUATOR.check_study_type("cultural", "interview")
        assert not result.passed
        assert result.triggered_by == "cultural"

    def test_study_type_fires_for_strategic(self):
        result = EVALUATOR.check_study_type("strategic", "interview")
        assert not result.passed

    def test_study_type_fires_for_legal(self):
        result = EVALUATOR.check_study_type("legal", "survey")
        assert not result.passed

    def test_study_type_fires_across_all_applicable_methods(self):
        for method in ["interview", "survey", "usability_test"]:
            result = EVALUATOR.check_study_type("cultural", method)
            assert not result.passed, f"Expected gate to fire for method: {method}"


# ─────────────────────────────────────────────────────────────────────────────
# Gate applicability matrix
# ─────────────────────────────────────────────────────────────────────────────

class TestGateApplicabilityMatrix:
    """Verify that gates apply to the correct method types and auto-pass otherwise."""

    def test_distress_applies_to_interview(self):
        transcript = "I give up. This is impossible. I hate this."
        result = EVALUATOR.check_distress(transcript, "interview")
        assert not result.passed  # applies + fires

    def test_distress_applies_to_survey(self):
        transcript = "I give up. This is impossible."
        result = EVALUATOR.check_distress(transcript, "survey")
        assert not result.passed  # applies + fires

    def test_distress_does_not_apply_to_usability_test(self):
        transcript = "I give up. I give up. Hate this. Frustrated."
        result = EVALUATOR.check_distress(transcript, "usability_test")
        assert result.passed  # does not apply → auto-pass
        assert "not applicable" in result.reason

    def test_completion_applies_to_all_three_methods(self):
        # n=2 is below minimum for all methods
        for method in ["interview", "survey", "usability_test"]:
            result = EVALUATOR.check_completion_rate(2, 2, method)
            assert not result.passed, f"Expected gate to fire for method: {method}"
