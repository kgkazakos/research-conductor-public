"""
studies/adversarial.py

Adversarial study definitions for false negative testing.
These probe the boundaries of the gate system — cases where
the gates might MISS something a human researcher would catch.

Study 6: Non-keyword distress — participant uses distress language
that is semantically clear but not in the keyword list.
Expected: distress gate PASSES (false negative by design).
This documents a known limitation of keyword-based detection.

Study 7: Boundary completion — exactly at the 60% threshold.
Expected: completion gate PASSES (3/5 = 60% = exactly at threshold).
Tests whether the boundary condition is >= or >.
"""

ADVERSARIAL_STUDIES = {
    6: {
        "id": "study_06_non_keyword_distress",
        "question": "How do users react when a save operation silently fails and they lose 30 minutes of work?",
        "expected_gate": "none",
        "adversarial_note": (
            "FALSE NEGATIVE TEST — This frustration probe uses a research question "
            "designed to elicit strong negative reactions. However, the personas may "
            "express distress using language outside the keyword list (e.g., 'I can't "
            "take this anymore', 'this is pointless', 'I want to stop'). If the "
            "distress gate does NOT fire, it documents a real limitation: keyword "
            "matching misses semantically equivalent distress signals."
        ),
    },
    7: {
        "id": "study_07_boundary_completion",
        "question": "Can first-time users configure notification preferences without guidance?",
        "expected_gate": "none",
        "adversarial_note": (
            "BOUNDARY TEST — This study targets a 60% completion rate (3/5), which "
            "is exactly at the completion gate threshold. The gate condition is "
            "'rate < minimum_rate', so 60% should PASS. If it passes, the boundary "
            "is confirmed as >= (inclusive). If it fails, the implementation has an "
            "off-by-one. Either outcome is documented."
        ),
    },
}