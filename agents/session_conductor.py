"""
agents/session_conductor.py

Session Conductor — second LLM-powered agent node.
Routes to the correct method adapter based on protocol.method_type,
runs all participant sessions sequentially, and returns results.

Input:  protocol, participants, method_type (from state)
Output: sessions, transcripts, completed_count, total_count

The distress gate reads the combined transcript after all sessions complete.
"""

from __future__ import annotations

from llm.client import LLMClient
from methods.base import SessionResult
from methods.interview import InterviewMethod
from methods.survey import SurveyMethod
from methods.usability_test import UsabilityTestMethod


class SessionConductor:
    def __init__(self, llm: LLMClient) -> None:
        self._adapters = {
            "interview": InterviewMethod(llm),
            "survey": SurveyMethod(llm),
            "usability_test": UsabilityTestMethod(llm),
        }

    def run_all_sessions(
        self,
        protocol: dict,
        participants: list[dict],
        method_type: str,
    ) -> tuple[list[dict], list[str], int, int]:
        """
        Run all participant sessions for the study.

        Args:
            protocol:     StudyProtocol.to_dict()
            participants: List of persona dicts from participant selector
            method_type:  interview | survey | usability_test

        Returns:
            Tuple of (sessions, transcripts, completed_count, total_count)
        """
        adapter = self._adapters.get(method_type)
        if adapter is None:
            raise ValueError(
                f"Unknown method_type='{method_type}'. "
                f"Valid: {list(self._adapters.keys())}"
            )

        results: list[SessionResult] = []

        print(f"\n  Running {len(participants)} sessions ({method_type}):")
        for persona in participants:
            print(f"    → {persona['name']} ({persona['role']})...", end=" ", flush=True)
            result = adapter.run_session(persona, protocol)
            status = "✓" if result.completed else "✗ abandoned"
            print(status)
            results.append(result)

        completed_count = sum(1 for r in results if r.completed)
        total_count = len(results)
        transcripts = [r.transcript for r in results]
        sessions = [r.to_dict() for r in results]

        print(
            f"\n  Sessions complete: {completed_count}/{total_count} completed "
            f"({completed_count/total_count:.0%})"
        )

        return sessions, transcripts, completed_count, total_count