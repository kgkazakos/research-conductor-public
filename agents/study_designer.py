"""
agents/study_designer.py

Study Design Agent — first LLM node in the ResearchConductor graph.
Translates a research question into a structured StudyProtocol.

Input:  research_question (str)
Output: StudyProtocol — method_type, research_question_type, tasks, metrics, guide

The research_question_type classification is the critical output:
it feeds gate_study_type, which checks against gates.yaml requires_review.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass

from llm.client import LLMClient


SYSTEM_PROMPT = """\
You are a UX research methodology expert. Design a study protocol for the given research question.

Return ONLY valid JSON — no markdown, no explanation, no code fences. Use exactly this structure:
{
  "method_type": "interview|survey|usability_test",
  "research_question_type": "concept_test|task_completion|frustration_probe|segmented_task|cultural|strategic|legal|regulatory|cross_functional",
  "tasks": ["task description 1", "task description 2"],
  "success_metrics": {"primary": "metric name", "threshold": "target value"},
  "participant_criteria": {"experience_level": "any|senior|junior", "count": 5},
  "interview_guide": ["question 1", "question 2", "question 3", "question 4", "question 5"]
}

Method type rules:
- usability_test: task completion, navigation, or "can users do X" questions
- interview: exploratory, qualitative, attitude, emotional, or cultural questions
- survey: segmented comparisons or preference questions across distinct user groups

Research question type rules:
- concept_test: understanding of a UI element, label, icon, or concept
- task_completion: completing a specific product flow or task
- frustration_probe: reactions to difficult, error-prone, or repetitive interactions
- segmented_task: behaviour comparison across user segments (e.g. senior vs junior users)
- cultural: cross-cultural differences, trust dynamics, or adoption across cultures/regions
- strategic: high-level product direction, vision, or business strategy
- legal: compliance, privacy, consent, or legal implications
- regulatory: regulatory requirements or constraints
- cross_functional: questions spanning multiple teams or business functions\
"""


@dataclass
class StudyProtocol:
    method_type: str
    research_question_type: str
    tasks: list[str]
    success_metrics: dict
    participant_criteria: dict
    interview_guide: list[str]

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "StudyProtocol":
        return cls(
            method_type=d["method_type"],
            research_question_type=d["research_question_type"],
            tasks=d.get("tasks", []),
            success_metrics=d.get("success_metrics", {}),
            participant_criteria=d.get("participant_criteria", {"experience_level": "any", "count": 5}),
            interview_guide=d.get("interview_guide", []),
        )


class StudyDesigner:
    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    def design(self, research_question: str) -> StudyProtocol:
        """
        One LLM call: research question → StudyProtocol.
        Prints the classification result for gate visibility.
        """
        prompt = f"Research question: {research_question}"
        raw = self.llm.generate(prompt=prompt, system=SYSTEM_PROMPT)
        data = _parse_json(raw)
        protocol = StudyProtocol.from_dict(data)
        print(
            f"  Study designer → method={protocol.method_type}, "
            f"type={protocol.research_question_type}"
        )
        return protocol


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
        raise ValueError(f"Could not parse JSON from LLM response:\n{text[:400]}")