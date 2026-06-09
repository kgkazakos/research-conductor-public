"""
graph/state.py

StudyState — the single state object that flows through the LangGraph graph.

Each agent node receives the full state and returns a partial dict
containing only the keys it modifies. LangGraph merges updates automatically.

gate_log uses operator.add as its reducer, meaning returned lists are
appended rather than replaced — each gate check node adds one entry.
All other fields use last-write-wins (standard LangGraph behaviour).
"""

from __future__ import annotations

import operator
from typing import Annotated, Optional, TypedDict


class StudyState(TypedDict, total=False):
    # ── Input (required at graph.invoke time) ─────────────────────────────────
    research_question: str

    # ── Set by study designer ─────────────────────────────────────────────────
    method_type: str                 # interview | survey | usability_test
    research_question_type: str      # concept_test | task_completion | cultural | ...
    protocol: dict                   # full study protocol (tasks, metrics, guide)

    # ── Set by participant selector ───────────────────────────────────────────
    participants: list[dict]         # selected personas from P2 pool

    # ── Set by session conductor ──────────────────────────────────────────────
    sessions: list[dict]             # raw session results per participant
    transcripts: list[str]           # session transcripts (distress gate input)
    completed_count: int             # participants who completed the task
    total_count: int                 # total participants who attempted

    # ── Set by response analyzer ──────────────────────────────────────────────
    analysis: dict                   # themes, metrics, confidence indicators

    # ── Gate state ────────────────────────────────────────────────────────────
    # gate_log accumulates ALL gate results across the run (FAccT paper data)
    gate_log: Annotated[list[dict], operator.add]
    # current_gate_result holds the most recent gate check for routing
    current_gate_result: dict

    # ── Human review ──────────────────────────────────────────────────────────
    human_review_required: bool
    human_review_reason: str
    human_review_outcome: str        # approved | halted | modified

    # ── Output ────────────────────────────────────────────────────────────────
    report: dict


def initial_state(research_question: str) -> StudyState:
    """
    Return a fully initialised state for graph.invoke().
    All lists and dicts are set to empty defaults so reducers work correctly.
    """
    return StudyState(
        research_question=research_question,
        method_type="",
        research_question_type="",
        protocol={},
        participants=[],
        sessions=[],
        transcripts=[],
        completed_count=0,
        total_count=0,
        analysis={},
        gate_log=[],
        current_gate_result={},
        human_review_required=False,
        human_review_reason="",
        human_review_outcome="",
        report={},
    )