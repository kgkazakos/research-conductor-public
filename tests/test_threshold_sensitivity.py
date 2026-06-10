"""
tests/test_threshold_sensitivity.py

Threshold Sensitivity Analysis for ResearchConductor gates.

Answers the question: "How sensitive are gate outcomes to threshold values?"

For each gate, sweeps across a range of reasonable thresholds and reports
whether the gate would have fired differently for the actual study data.
This demonstrates that the chosen thresholds are not arbitrary lucky values
but sit within a stable region of the parameter space.

Usage:
    pytest tests/test_threshold_sensitivity.py -v -s
    python -m tests.test_threshold_sensitivity   # standalone with table output
"""

from __future__ import annotations

import copy
import tempfile
from pathlib import Path

import yaml

from gates.gate_evaluator import GateEvaluator


# ── Actual study data (from completed runs) ──────────────────────────────────

# Study 3: frustration probe — 7 keyword hits in combined transcript
STUDY_3_TRANSCRIPT = (
    "I was so frustrated. It literally makes no sense when you do exactly "
    "what the prompt says and it still bounces back. I hate this. Seriously, "
    "this is impossible. I give up. I'd just close the tab."
)
STUDY_3_METHOD = "interview"

# Study 5: cultural trust — 1 keyword hit (below threshold)
STUDY_5_TRANSCRIPT = (
    "Trust is built on consistency. If your platform can't handle an error "
    "gracefully, I'm going to be highly skeptical. I was a bit confused "
    "at first but worked through it."
)
STUDY_5_METHOD = "interview"

# Study 4: segmented form labels — 2/5 completed (40%)
STUDY_4_COMPLETED = 2
STUDY_4_TOTAL = 5
STUDY_4_METHOD = "usability_test"

# Study 2: checkout usability — 5/5 completed (100%)
STUDY_2_COMPLETED = 5
STUDY_2_TOTAL = 5
STUDY_2_METHOD = "usability_test"

# Boundary case: exactly 3/5 (60%)
BOUNDARY_COMPLETED = 3
BOUNDARY_TOTAL = 5


def _make_evaluator_with_overrides(**overrides) -> GateEvaluator:
    """Create a GateEvaluator with modified thresholds for sensitivity testing."""
    base_path = Path("gates/gates.yaml")
    with open(base_path) as f:
        config = yaml.safe_load(f)

    # Apply overrides
    if "max_occurrences" in overrides:
        config["distress_gate"]["max_occurrences"] = overrides["max_occurrences"]
    if "minimum_rate" in overrides:
        config["completion_gate"]["minimum_rate"] = overrides["minimum_rate"]
    if "minimum_participants" in overrides:
        config["completion_gate"]["minimum_participants"] = overrides["minimum_participants"]

    # Write to temp file and load
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
    yaml.dump(config, tmp)
    tmp.close()
    return GateEvaluator(tmp.name)


# ─── Distress Gate Sensitivity ────────────────────────────────────────────────

class TestDistressThresholdSensitivity:
    """Sweep max_occurrences from 1 to 10 against actual study transcripts."""

    def test_study_3_fires_at_thresholds_1_through_7(self):
        """Study 3 has 7 keyword hits — gate should fire at any threshold ≤ 7."""
        for threshold in range(1, 8):
            evaluator = _make_evaluator_with_overrides(max_occurrences=threshold)
            result = evaluator.check_distress(STUDY_3_TRANSCRIPT, STUDY_3_METHOD)
            assert not result.passed, (
                f"Expected gate to fire at max_occurrences={threshold} "
                f"(7 hits in transcript)"
            )

    def test_study_3_passes_at_threshold_8_and_above(self):
        """Study 3 has 7 keyword hits — gate should pass at threshold ≥ 8."""
        for threshold in range(8, 11):
            evaluator = _make_evaluator_with_overrides(max_occurrences=threshold)
            result = evaluator.check_distress(STUDY_3_TRANSCRIPT, STUDY_3_METHOD)
            assert result.passed, (
                f"Expected gate to pass at max_occurrences={threshold} "
                f"(only 7 hits)"
            )

    def test_study_5_only_fires_at_threshold_1(self):
        """Study 5 has 1 keyword hit — only fires at max_occurrences=1."""
        evaluator_1 = _make_evaluator_with_overrides(max_occurrences=1)
        result_1 = evaluator_1.check_distress(STUDY_5_TRANSCRIPT, STUDY_5_METHOD)
        assert not result_1.passed, "Should fire at threshold=1 (1 hit)"

        evaluator_2 = _make_evaluator_with_overrides(max_occurrences=2)
        result_2 = evaluator_2.check_distress(STUDY_5_TRANSCRIPT, STUDY_5_METHOD)
        assert result_2.passed, "Should pass at threshold=2 (only 1 hit)"

    def test_threshold_2_is_in_stable_region(self):
        """
        The chosen threshold (2) correctly separates study 3 (fires)
        from study 5 (passes). This holds for thresholds 2-7.
        """
        for threshold in range(2, 8):
            evaluator = _make_evaluator_with_overrides(max_occurrences=threshold)
            study_3 = evaluator.check_distress(STUDY_3_TRANSCRIPT, STUDY_3_METHOD)
            study_5 = evaluator.check_distress(STUDY_5_TRANSCRIPT, STUDY_5_METHOD)
            assert not study_3.passed and study_5.passed, (
                f"Threshold {threshold} should separate study 3 (fire) "
                f"from study 5 (pass)"
            )


# ─── Completion Gate Sensitivity ──────────────────────────────────────────────

class TestCompletionThresholdSensitivity:
    """Sweep minimum_rate from 0.20 to 0.90 against actual study data."""

    def test_study_4_fires_at_thresholds_above_40_percent(self):
        """Study 4 has 40% completion — fires at any threshold > 0.40."""
        for rate in [0.50, 0.60, 0.70, 0.80, 0.90]:
            evaluator = _make_evaluator_with_overrides(minimum_rate=rate)
            result = evaluator.check_completion_rate(
                STUDY_4_COMPLETED, STUDY_4_TOTAL, STUDY_4_METHOD
            )
            assert not result.passed, (
                f"Study 4 (40%) should fail at minimum_rate={rate}"
            )

    def test_study_4_passes_at_thresholds_40_percent_and_below(self):
        """Study 4 has 40% completion — passes at threshold ≤ 0.40."""
        for rate in [0.20, 0.30, 0.40]:
            evaluator = _make_evaluator_with_overrides(minimum_rate=rate)
            result = evaluator.check_completion_rate(
                STUDY_4_COMPLETED, STUDY_4_TOTAL, STUDY_4_METHOD
            )
            assert result.passed, (
                f"Study 4 (40%) should pass at minimum_rate={rate}"
            )

    def test_study_2_passes_at_all_thresholds(self):
        """Study 2 has 100% completion — always passes."""
        for rate in [0.50, 0.60, 0.70, 0.80, 0.90]:
            evaluator = _make_evaluator_with_overrides(minimum_rate=rate)
            result = evaluator.check_completion_rate(
                STUDY_2_COMPLETED, STUDY_2_TOTAL, STUDY_2_METHOD
            )
            assert result.passed, (
                f"Study 2 (100%) should always pass at minimum_rate={rate}"
            )

    def test_boundary_60_percent_passes_at_threshold_60(self):
        """Exactly 60% completion passes at 60% threshold (>= not >)."""
        evaluator = _make_evaluator_with_overrides(minimum_rate=0.60)
        result = evaluator.check_completion_rate(
            BOUNDARY_COMPLETED, BOUNDARY_TOTAL, STUDY_4_METHOD
        )
        assert result.passed, "60% should pass at threshold 60% (condition is <, not <=)"

    def test_boundary_60_percent_fails_at_threshold_61(self):
        """Exactly 60% completion fails at 61% threshold."""
        evaluator = _make_evaluator_with_overrides(minimum_rate=0.61)
        result = evaluator.check_completion_rate(
            BOUNDARY_COMPLETED, BOUNDARY_TOTAL, STUDY_4_METHOD
        )
        assert not result.passed, "60% should fail at threshold 61%"

    def test_threshold_60_is_in_stable_region(self):
        """
        The chosen threshold (0.60) correctly separates study 4 (fires)
        from study 2 (passes). This holds for thresholds 0.41-1.00.
        """
        for rate_int in range(41, 101):
            rate = rate_int / 100
            evaluator = _make_evaluator_with_overrides(minimum_rate=rate)
            study_4 = evaluator.check_completion_rate(
                STUDY_4_COMPLETED, STUDY_4_TOTAL, STUDY_4_METHOD
            )
            study_2 = evaluator.check_completion_rate(
                STUDY_2_COMPLETED, STUDY_2_TOTAL, STUDY_2_METHOD
            )
            assert not study_4.passed and study_2.passed, (
                f"Threshold {rate:.0%} should separate study 4 (fire) "
                f"from study 2 (pass)"
            )


# ─── Minimum Participants Sensitivity ─────────────────────────────────────────

class TestMinimumParticipantsSensitivity:
    """Sweep minimum_participants from 1 to 6."""

    def test_n5_passes_at_minimum_1_through_5(self):
        """5 participants passes any minimum ≤ 5."""
        for min_p in range(1, 6):
            evaluator = _make_evaluator_with_overrides(minimum_participants=min_p)
            result = evaluator.check_completion_rate(5, 5, "usability_test")
            assert result.passed, f"n=5 should pass at minimum_participants={min_p}"

    def test_n5_fails_at_minimum_6(self):
        """5 participants fails at minimum=6."""
        evaluator = _make_evaluator_with_overrides(minimum_participants=6)
        result = evaluator.check_completion_rate(5, 5, "usability_test")
        assert not result.passed, "n=5 should fail at minimum_participants=6"


# ─── Standalone runner with table output ──────────────────────────────────────

def _print_sensitivity_table():
    """Print a sensitivity summary table for the gate analysis doc."""
    print("\n" + "=" * 70)
    print("DISTRESS GATE — Threshold Sensitivity (max_occurrences)")
    print("=" * 70)
    print(f"{'Threshold':<12} {'Study 3 (7 hits)':<22} {'Study 5 (1 hit)':<22}")
    print("-" * 56)
    for t in range(1, 11):
        ev = _make_evaluator_with_overrides(max_occurrences=t)
        s3 = "FAIL ✓" if not ev.check_distress(STUDY_3_TRANSCRIPT, STUDY_3_METHOD).passed else "PASS"
        s5 = "FAIL" if not ev.check_distress(STUDY_5_TRANSCRIPT, STUDY_5_METHOD).passed else "PASS ✓"
        print(f"  {t:<10} {s3:<22} {s5:<22}")

    print(f"\nChosen threshold: 2 — stable region: 2–7")
    print(f"At threshold=1, study 5 would false-positive (1 hit is normal)")
    print(f"At threshold≥8, study 3 would false-negative (7 hits missed)")

    print("\n" + "=" * 70)
    print("COMPLETION GATE — Threshold Sensitivity (minimum_rate)")
    print("=" * 70)
    print(f"{'Threshold':<12} {'Study 4 (40%)':<22} {'Study 2 (100%)':<22} {'Boundary (60%)':<22}")
    print("-" * 78)
    for r in [0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90]:
        ev = _make_evaluator_with_overrides(minimum_rate=r)
        s4 = "FAIL ✓" if not ev.check_completion_rate(STUDY_4_COMPLETED, STUDY_4_TOTAL, STUDY_4_METHOD).passed else "PASS"
        s2 = "FAIL" if not ev.check_completion_rate(STUDY_2_COMPLETED, STUDY_2_TOTAL, STUDY_2_METHOD).passed else "PASS ✓"
        bd = "FAIL" if not ev.check_completion_rate(BOUNDARY_COMPLETED, BOUNDARY_TOTAL, STUDY_4_METHOD).passed else "PASS"
        print(f"  {r:<10.0%} {s4:<22} {s2:<22} {bd:<22}")

    print(f"\nChosen threshold: 60% — stable region: 41%–100% separates study 4 from study 2")


if __name__ == "__main__":
    _print_sensitivity_table()