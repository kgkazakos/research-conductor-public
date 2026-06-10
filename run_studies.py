"""
run_studies.py

Execute all 5 ResearchConductor test studies and save results.
Each study output is saved as JSON in outputs/raw/.

Usage:
    python -m run_studies              # run all 5
    python -m run_studies 1            # run study 1 only
    python -m run_studies 2 4          # run studies 2 and 4

Output files:
    outputs/raw/study_01_icon_concept_test.json
    outputs/raw/study_02_checkout_usability.json
    outputs/raw/study_03_frustration_probe.json
    outputs/raw/study_04_segmented_form_labels.json
    outputs/raw/study_05_cultural_trust.json
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from graph.state import initial_state
from graph.workflow import graph


STUDIES = {
    1: {
        "id": "study_01_icon_concept_test",
        "question": "Does this icon label make sense?",
        "expected_gate": "none",
    },
    2: {
        "id": "study_02_checkout_usability",
        "question": "Can users complete the checkout flow in under 5 clicks?",
        "expected_gate": "none",
    },
    3: {
        "id": "study_03_frustration_probe",
        "question": "What emotional reactions do users describe when encountering repeated error messages?",
        "expected_gate": "distress_gate",
    },
    4: {
        "id": "study_04_segmented_form_labels",
        "question": "Do senior vs junior users read form labels differently?",
        "expected_gate": "completion_gate",
    },
    5: {
        "id": "study_05_cultural_trust",
        "question": "How does trust affect feature adoption across cultures?",
        "expected_gate": "study_type_gate",
    },
}

OUTPUT_DIR = Path("outputs/raw")


def run_study(number: int) -> dict:
    """Run a single study and return the full result state."""
    study = STUDIES[number]
    print(f"\n{'='*70}")
    print(f"STUDY {number}: {study['id']}")
    print(f"Question: {study['question']}")
    print(f"Expected gate trigger: {study['expected_gate']}")
    print(f"{'='*70}\n")

    state = initial_state(study["question"])
    start = time.time()
    result = graph.invoke(state)
    elapsed = time.time() - start

    # Build output
    output = {
        "study_number": number,
        "study_id": study["id"],
        "research_question": study["question"],
        "expected_gate": study["expected_gate"],
        "elapsed_seconds": round(elapsed, 1),
        "method_type": result.get("method_type", ""),
        "research_question_type": result.get("research_question_type", ""),
        "participant_count": result.get("total_count", 0),
        "completed_count": result.get("completed_count", 0),
        "gate_log": result.get("gate_log", []),
        "sessions": result.get("sessions", []),
        "analysis": result.get("analysis", {}),
        "report": result.get("report", {}),
        "human_review_outcome": result.get("human_review_outcome", ""),
    }

    # Print summary
    print(f"\n--- Study {number} Summary ---")
    print(f"Method: {output['method_type']}")
    print(f"Type: {output['research_question_type']}")
    print(f"Completed: {output['completed_count']}/{output['participant_count']}")
    print(f"Time: {output['elapsed_seconds']}s")
    print("Gate log:")
    for g in output["gate_log"]:
        status = "PASS" if g["passed"] else "FAIL"
        print(f"  [{g['gate_name']}] {status}: {g['reason']}")

    # Check if expected gate fired
    triggered_gates = [g["gate_name"] for g in output["gate_log"] if not g["passed"]]
    if study["expected_gate"] == "none":
        if not triggered_gates:
            print("✓ Correct: fully autonomous (no gates triggered)")
        else:
            print(f"✗ Unexpected gate trigger: {triggered_gates}")
    else:
        if study["expected_gate"] in triggered_gates:
            print(f"✓ Correct: {study['expected_gate']} triggered as expected")
        else:
            print(f"✗ Expected {study['expected_gate']} but got: {triggered_gates or 'none'}")

    return output


def save_output(output: dict) -> Path:
    """Save study output to JSON file."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / f"{output['study_id']}.json"
    with open(path, "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"Saved: {path}")
    return path


def main():
    # Parse which studies to run from command line args
    if len(sys.argv) > 1:
        study_numbers = [int(n) for n in sys.argv[1:]]
    else:
        study_numbers = list(STUDIES.keys())

    results = []
    for n in study_numbers:
        if n not in STUDIES:
            print(f"Unknown study number: {n}. Valid: {list(STUDIES.keys())}")
            continue
        output = run_study(n)
        save_output(output)
        results.append(output)

    # Final summary
    print(f"\n{'='*70}")
    print("ALL STUDIES COMPLETE")
    print(f"{'='*70}")
    for r in results:
        triggered = [g["gate_name"] for g in r["gate_log"] if not g["passed"]]
        autonomous = "✓ autonomous" if not triggered else f"→ {', '.join(triggered)}"
        print(
            f"  Study {r['study_number']}: "
            f"{r['completed_count']}/{r['participant_count']} completed, "
            f"{r['elapsed_seconds']}s, {autonomous}"
        )


if __name__ == "__main__":
    main()