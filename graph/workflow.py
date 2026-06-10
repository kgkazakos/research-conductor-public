"""
graph/workflow.py

ResearchConductor — LangGraph graph definition.

Graph structure:
    study_designer
        → [gate: study_type]
        → participant_selector
        → session_conductor
        → [gate: distress]
        → response_analyzer
        → [gate: completion_rate]
        → report_generator
        → END

Each gate is a two-step pattern:
  1. A gate_check node: runs the evaluator, appends to gate_log, sets
     current_gate_result. (Nodes can modify state.)
  2. A route_ function: reads current_gate_result.passed and returns
     "pass" or "flag". (Routing functions cannot modify state.)

Week 1 status: all agent nodes are stubs returning empty dicts.
The graph compiles and routes correctly — wiring is complete.
Agent implementations added in Week 1 sessions (Thu–Sat).
"""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from gates.gate_evaluator import GateEvaluator
from graph.state import StudyState

_evaluator = GateEvaluator()


# ─── Agent node stubs ─────────────────────────────────────────────────────────
# Each returns a partial dict — LangGraph merges into state automatically.
# Replace stub bodies with real implementations session by session.

def study_designer(state: StudyState) -> dict:
    from agents.study_designer import StudyDesigner
    from llm.client import LLMClient
    protocol = StudyDesigner(LLMClient()).design(state["research_question"])
    return {
        "method_type": protocol.method_type,
        "research_question_type": protocol.research_question_type,
        "protocol": protocol.to_dict(),
    }


def participant_selector(state: StudyState) -> dict:
    from participants.selector import ParticipantSelector
    participants = ParticipantSelector().select(
        protocol=state.get("protocol", {}),
        method_type=state.get("method_type", ""),
    )
    return {"participants": participants}


def session_conductor(state: StudyState) -> dict:
    from agents.session_conductor import SessionConductor
    from llm.client import LLMClient
    sessions, transcripts, completed, total = SessionConductor(LLMClient()).run_all_sessions(
        protocol=state.get("protocol", {}),
        participants=state.get("participants", []),
        method_type=state.get("method_type", "interview"),
    )
    return {
        "sessions": sessions,
        "transcripts": transcripts,
        "completed_count": completed,
        "total_count": total,
    }


def response_analyzer(state: StudyState) -> dict:
    """
    TODO (Mon Jun 16): call agents/response_analyzer.py
    Input:  state["sessions"], state["method_type"]
    Output: analysis
    """
    return {}


def report_generator(state: StudyState) -> dict:
    """
    TODO (Tue Jun 17): call agents/report_generator.py
    Input:  state["analysis"], state["protocol"], state["gate_log"]
    Output: report
    """
    return {}


# ─── Human review stubs ───────────────────────────────────────────────────────
# Week 2: replace with LangGraph interrupt() for real human-in-the-loop.

def human_review_study_type(state: StudyState) -> dict:
    """Simulated human review after study type gate fires."""
    print(f"\n[HUMAN REVIEW — study type] Reason: {state.get('human_review_reason')}")
    print("Simulated outcome: approved — proceeding with sessions.\n")
    return {"human_review_outcome": "approved"}


def human_review_distress(state: StudyState) -> dict:
    """Simulated human review after distress gate fires (halt_immediately)."""
    print(f"\n[HUMAN REVIEW — distress] Reason: {state.get('human_review_reason')}")
    print("Simulated outcome: halted — study terminated early.\n")
    return {"human_review_outcome": "halted"}


def human_review_completion(state: StudyState) -> dict:
    """Simulated human review after completion rate gate fires."""
    print(f"\n[HUMAN REVIEW — completion] Reason: {state.get('human_review_reason')}")
    print("Simulated outcome: approved — proceeding to report with caveats.\n")
    return {"human_review_outcome": "approved"}


# ─── Gate check nodes ─────────────────────────────────────────────────────────
# These run the evaluator, append the result to gate_log, and set
# current_gate_result for the routing function that follows.

def gate_study_type(state: StudyState) -> dict:
    result = _evaluator.check_study_type(
        research_question_type=state.get("research_question_type", "unknown"),
        method_type=state.get("method_type", "interview"),
    )
    print(f"  {result}")
    reason = result.reason if not result.passed else ""
    return {
        "gate_log": [result.to_dict()],
        "current_gate_result": result.to_dict(),
        "human_review_required": not result.passed,
        "human_review_reason": reason,
    }


def gate_distress(state: StudyState) -> dict:
    combined_transcript = " ".join(state.get("transcripts", []))
    result = _evaluator.check_distress(
        transcript=combined_transcript,
        method_type=state.get("method_type", "interview"),
    )
    print(f"  {result}")
    reason = result.reason if not result.passed else ""
    return {
        "gate_log": [result.to_dict()],
        "current_gate_result": result.to_dict(),
        "human_review_required": not result.passed,
        "human_review_reason": reason,
    }


def gate_completion_rate(state: StudyState) -> dict:
    result = _evaluator.check_completion_rate(
        completed=state.get("completed_count", 0),
        total=state.get("total_count", 0),
        method_type=state.get("method_type", "interview"),
    )
    print(f"  {result}")
    reason = result.reason if not result.passed else ""
    return {
        "gate_log": [result.to_dict()],
        "current_gate_result": result.to_dict(),
        "human_review_required": not result.passed,
        "human_review_reason": reason,
    }


# ─── Routing functions ────────────────────────────────────────────────────────
# Read current_gate_result from state — return "pass" or "flag" only.
# Cannot modify state.

def route_study_type(state: StudyState) -> str:
    passed = state.get("current_gate_result", {}).get("passed", True)
    return "pass" if passed else "flag"


def route_distress(state: StudyState) -> str:
    passed = state.get("current_gate_result", {}).get("passed", True)
    return "pass" if passed else "flag"


def route_completion(state: StudyState) -> str:
    passed = state.get("current_gate_result", {}).get("passed", True)
    return "pass" if passed else "flag"


# ─── Build and compile ────────────────────────────────────────────────────────

def build_graph():
    g = StateGraph(StudyState)

    # Agent nodes
    g.add_node("study_designer", study_designer)
    g.add_node("participant_selector", participant_selector)
    g.add_node("session_conductor", session_conductor)
    g.add_node("response_analyzer", response_analyzer)
    g.add_node("report_generator", report_generator)

    # Gate check nodes
    g.add_node("gate_study_type", gate_study_type)
    g.add_node("gate_distress", gate_distress)
    g.add_node("gate_completion_rate", gate_completion_rate)

    # Human review nodes
    g.add_node("human_review_study_type", human_review_study_type)
    g.add_node("human_review_distress", human_review_distress)
    g.add_node("human_review_completion", human_review_completion)

    # ── Entry ──
    g.set_entry_point("study_designer")

    # ── study_designer → gate → [participant_selector | human_review] ──
    g.add_edge("study_designer", "gate_study_type")
    g.add_conditional_edges(
        "gate_study_type",
        route_study_type,
        {"pass": "participant_selector", "flag": "human_review_study_type"},
    )
    g.add_edge("human_review_study_type", "participant_selector")

    # ── participant_selector → session_conductor ──
    g.add_edge("participant_selector", "session_conductor")

    # ── session_conductor → gate → [response_analyzer | human_review] ──
    g.add_edge("session_conductor", "gate_distress")
    g.add_conditional_edges(
        "gate_distress",
        route_distress,
        {"pass": "response_analyzer", "flag": "human_review_distress"},
    )
    # Distress halt: human reviews, study ends (no further analysis)
    g.add_edge("human_review_distress", END)

    # ── response_analyzer → gate → [report_generator | human_review] ──
    g.add_edge("response_analyzer", "gate_completion_rate")
    g.add_conditional_edges(
        "gate_completion_rate",
        route_completion,
        {"pass": "report_generator", "flag": "human_review_completion"},
    )
    g.add_edge("human_review_completion", "report_generator")

    # ── report_generator → END ──
    g.add_edge("report_generator", END)

    return g.compile()


# Compile once at import time — fail fast if wiring is broken
graph = build_graph()


if __name__ == "__main__":
    # Smoke test: run a stub study through the full graph
    from graph.state import initial_state

    print("ResearchConductor — smoke test (all stub nodes)\n")
    state = initial_state("Does this icon make sense?")

    # Manually set what the study designer would produce
    # (so gates have something to check)
    state["method_type"] = "interview"
    state["research_question_type"] = "concept_test"
    state["completed_count"] = 5
    state["total_count"] = 5

    result = graph.invoke(state)

    print("\nGate log:")
    for entry in result.get("gate_log", []):
        status = "PASS" if entry["passed"] else "FAIL"
        print(f"  [{entry['gate_name']}] {status}: {entry['reason']}")