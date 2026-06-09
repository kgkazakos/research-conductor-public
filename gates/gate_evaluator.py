"""
gate_evaluator.py

Static gate evaluator for ResearchConductor.

Design constraint: no LLM imports, no probability, no learned thresholds.
All gate conditions are config-driven if-statements reading from gates.yaml.
This module must remain independent of the LLM adapter layer.

Usage:
    evaluator = GateEvaluator()
    result = evaluator.check_study_type("cultural", "interview")
    if not result.passed:
        # route to human review interrupt in LangGraph
        ...
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class GateResult:
    """Result of a single gate evaluation, stored in the LangGraph state."""

    gate_name: str
    passed: bool
    reason: str
    halt_immediately: bool = False
    triggered_by: Optional[str] = None
    method_type: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "gate_name": self.gate_name,
            "passed": self.passed,
            "reason": self.reason,
            "halt_immediately": self.halt_immediately,
            "triggered_by": self.triggered_by,
            "method_type": self.method_type,
        }

    def __str__(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        halt = " [HALT]" if self.halt_immediately else ""
        return f"[{self.gate_name}] {status}{halt}: {self.reason}"


class GateEvaluator:
    """
    Evaluates static, config-driven gate conditions between agent phases.

    Instantiate once per study run. Gates are loaded from gates.yaml
    at construction time. Thresholds are never adjusted at runtime.
    """

    def __init__(self, config_path: str | Path = "gates/gates.yaml") -> None:
        config_path = Path(config_path)
        if not config_path.exists():
            raise FileNotFoundError(
                f"Gate configuration not found: {config_path}. "
                "Ensure gates.yaml exists relative to the working directory."
            )
        with open(config_path, "r") as f:
            self.config: dict = yaml.safe_load(f)

    def _gate_applies(self, gate_name: str, method_type: str) -> bool:
        """
        Return True if this gate is configured to run for the given method type.
        Gates not applicable to a method auto-pass and log 'not_applicable'.
        """
        gate = self.config.get(gate_name, {})
        applies_to: list[str] = gate.get("applies_to", [])
        return method_type in applies_to

    # ─────────────────────────────────────────────────────────────────────────
    # Gate 1: Study type
    # ─────────────────────────────────────────────────────────────────────────

    def check_study_type(
        self, research_question_type: str, method_type: str
    ) -> GateResult:
        """
        Fires after study design, before participant sessions begin.

        Args:
            research_question_type: The type label assigned by the study design
                agent (e.g. "concept_test", "cultural", "strategic").
            method_type: The method being used ("interview", "survey",
                "usability_test").

        Returns:
            GateResult — passed=False triggers a human review interrupt in the
            LangGraph graph before any sessions run.
        """
        gate_name = "study_type_gate"

        if not self._gate_applies(gate_name, method_type):
            return GateResult(
                gate_name=gate_name,
                passed=True,
                reason="gate not applicable to this method type",
                method_type=method_type,
            )

        requires_review: list[str] = self.config[gate_name]["requires_review"]
        normalised_type = research_question_type.strip().lower()
        flagged = normalised_type in [t.lower() for t in requires_review]

        return GateResult(
            gate_name=gate_name,
            passed=not flagged,
            reason=(
                f"question type '{research_question_type}' requires human review "
                "before sessions run"
                if flagged
                else f"question type '{research_question_type}' cleared for "
                "autonomous execution"
            ),
            triggered_by=research_question_type if flagged else None,
            method_type=method_type,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Gate 2: Distress flag
    # ─────────────────────────────────────────────────────────────────────────

    def check_distress(self, transcript: str, method_type: str) -> GateResult:
        """
        Fires during or immediately after a participant session.

        Counts total distress keyword occurrences in the session transcript.
        Total hits across all keywords are summed — a participant using three
        different distress phrases once each counts as 3 hits.

        Args:
            transcript: Full text of the participant session (conversation log
                for interviews, open-text responses for surveys).
            method_type: The method being used.

        Returns:
            GateResult — if halt_immediately is true in config and the gate
            fires, the LangGraph graph should stop the current session before
            the next participant begins.
        """
        gate_name = "distress_gate"

        if not self._gate_applies(gate_name, method_type):
            return GateResult(
                gate_name=gate_name,
                passed=True,
                reason="gate not applicable to this method type",
                method_type=method_type,
            )

        config = self.config[gate_name]
        keywords: list[str] = config["keywords"]
        max_occurrences: int = config["max_occurrences"]
        halt_immediately: bool = config.get("halt_immediately", False)

        transcript_lower = transcript.lower()
        hit_counts: dict[str, int] = {
            kw: transcript_lower.count(kw.lower()) for kw in keywords
        }
        total_hits = sum(hit_counts.values())
        triggered_keywords = [kw for kw, count in hit_counts.items() if count > 0]
        flagged = total_hits >= max_occurrences

        return GateResult(
            gate_name=gate_name,
            passed=not flagged,
            halt_immediately=flagged and halt_immediately,
            reason=(
                f"distress signal detected — {total_hits} keyword hit(s): "
                f"{triggered_keywords}. "
                f"{'Halting session immediately.' if halt_immediately else 'Flagging for human review.'}"
                if flagged
                else f"no distress signal (total keyword hits: {total_hits})"
            ),
            triggered_by=str(triggered_keywords) if flagged else None,
            method_type=method_type,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Gate 3: Completion rate
    # ─────────────────────────────────────────────────────────────────────────

    def check_completion_rate(
        self,
        completed: int,
        total: int,
        method_type: str,
    ) -> GateResult:
        """
        Fires after response analysis, before report generation.

        Two conditions checked in order:
        1. Minimum participant count — rate is meaningless below this floor.
        2. Minimum completion rate — proportion of participants who completed
           the study task successfully.

        Args:
            completed: Number of participants who completed the task.
            total: Total number of participants who attempted the task.
            method_type: The method being used.

        Returns:
            GateResult — passed=False routes to human validation before the
            report is generated.
        """
        gate_name = "completion_gate"

        if not self._gate_applies(gate_name, method_type):
            return GateResult(
                gate_name=gate_name,
                passed=True,
                reason="gate not applicable to this method type",
                method_type=method_type,
            )

        config = self.config[gate_name]
        minimum_rate: float = config["minimum_rate"]
        minimum_participants: int = config["minimum_participants"]

        # Check 1: absolute floor
        if total < minimum_participants:
            return GateResult(
                gate_name=gate_name,
                passed=False,
                reason=(
                    f"insufficient participants: {total} attempted, "
                    f"minimum required is {minimum_participants}"
                ),
                triggered_by=f"n={total}",
                method_type=method_type,
            )

        # Check 2: completion rate
        rate = completed / total
        flagged = rate < minimum_rate

        return GateResult(
            gate_name=gate_name,
            passed=not flagged,
            reason=(
                f"completion rate {rate:.0%} is below the minimum "
                f"threshold of {minimum_rate:.0%} — human validation required"
                if flagged
                else f"completion rate {rate:.0%} cleared minimum threshold "
                f"of {minimum_rate:.0%}"
            ),
            triggered_by=f"rate={rate:.0%}" if flagged else None,
            method_type=method_type,
        )
