"""
methods/base.py

Abstract base for all method adapters.
Each adapter simulates participant sessions using one LLM call per persona.

Shared simulation rules are defined here and embedded in every method's
system prompt to ensure consistent gate-triggering behaviour across studies.
"""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass

from llm.client import LLMClient


# ── Shared simulation rules ───────────────────────────────────────────────────
# Embedded in every method's system prompt.
# These rules ensure the right gate triggers for the right study type.

SIMULATION_RULES = """
SIMULATION RULES — apply these before generating any response:

FRUSTRATION RULE:
If the persona's frustration_threshold is "low" AND the research_question_type
is "frustration_probe": the participant grows visibly frustrated during the
session. Use at least 2 of these phrases naturally in the transcript:
"I give up", "frustrated", "makes no sense", "hate this", "this is impossible".
Set completed=false.

SEGMENTED TASK RULE:
If the research_question_type is "segmented_task" AND the persona's
tech_savviness is "low" or "medium": the participant struggles with the task
labels and UI — they are unclear and confusing at this experience level.
Set completed=false.

ALL OTHER SCENARIOS:
Use the persona's characteristics to guide authentic responses.
Most sessions complete successfully unless the above rules apply.\
"""


@dataclass
class SessionResult:
    """Output from a single participant session."""

    persona_id: str
    persona_name: str
    completed: bool
    transcript: str
    task_notes: str
    method_type: str

    def to_dict(self) -> dict:
        return asdict(self)


class BaseMethod(ABC):
    """
    Abstract method adapter. Subclasses implement prompt building;
    the base class handles the LLM call and JSON parsing.
    """

    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    @property
    @abstractmethod
    def method_type(self) -> str:
        """Return the method type string: interview | survey | usability_test."""
        ...

    @abstractmethod
    def _system_prompt(self) -> str:
        """Build the system prompt for this method type."""
        ...

    @abstractmethod
    def _user_prompt(self, persona: dict, protocol: dict) -> str:
        """Build the user prompt for a specific persona and protocol."""
        ...

    def run_session(self, persona: dict, protocol: dict) -> SessionResult:
        """
        Simulate one participant session. One LLM call per persona.
        Returns a SessionResult with completed status, transcript, and notes.
        """
        raw = self.llm.generate(
            prompt=self._user_prompt(persona, protocol),
            system=self._system_prompt(),
        )
        data = _parse_json(raw)
        return SessionResult(
            persona_id=persona["id"],
            persona_name=persona["name"],
            completed=bool(data.get("completed", False)),
            transcript=data.get("transcript", ""),
            task_notes=data.get("task_notes", ""),
            method_type=self.method_type,
        )


def _persona_block(persona: dict) -> str:
    """Format persona attributes into a readable block for the LLM prompt."""
    chars = ", ".join(persona.get("characteristics", []))
    return (
        f"Name: {persona['name']}\n"
        f"Role: {persona['role']}\n"
        f"Experience level: {persona['experience_level']}\n"
        f"Tech savviness: {persona['tech_savviness']}\n"
        f"Frustration threshold: {persona['frustration_threshold']}\n"
        f"Cultural background: {persona['cultural_background']}\n"
        f"Characteristics: {chars}\n"
        f"Typical language: {persona.get('typical_language', 'natural')}"
    )


def _parse_json(text: str) -> dict:
    """Parse JSON from LLM response, tolerating markdown code fences."""
    text = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.MULTILINE)
    text = re.sub(r"```\s*$", "", text.strip(), flags=re.MULTILINE)
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]+\}", text)
        if match:
            return json.loads(match.group())
        raise ValueError(f"Could not parse JSON:\n{text[:400]}")