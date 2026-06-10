"""
agents/response_analyzer.py

Response Analyzer — third LLM-powered agent node.
Method-aware: interviews and surveys get LLM thematic analysis,
usability tests get deterministic metric computation + LLM summary.

Input:  sessions, transcripts, method_type (from state)
Output: analysis dict with themes, metrics, and key findings
"""

from __future__ import annotations

import json
import re

from llm.client import LLMClient


THEMATIC_SYSTEM_PROMPT = """\
You are a qualitative UX research analyst. Analyze the session transcripts below.

Return ONLY valid JSON — no markdown, no explanation:
{
  "themes": [
    {
      "name": "theme name",
      "description": "one sentence description",
      "supporting_quotes": ["quote 1", "quote 2"],
      "frequency": 3
    }
  ],
  "key_findings": [
    "finding 1",
    "finding 2",
    "finding 3"
  ],
  "method_type": "interview|survey",
  "participant_count": 5,
  "completion_rate": 0.80,
  "notable_patterns": "one paragraph summarising cross-participant patterns"
}

Identify 3-5 themes. Each theme must have at least one supporting quote
from the transcripts. Frequency = number of participants who mentioned it.\
"""


USABILITY_SYSTEM_PROMPT = """\
You are a UX research analyst summarising usability test results.
Quantitative metrics are provided — your job is to interpret them.

Return ONLY valid JSON — no markdown, no explanation:
{
  "themes": [
    {
      "name": "theme name",
      "description": "one sentence description",
      "supporting_quotes": ["observation 1"],
      "frequency": 3
    }
  ],
  "key_findings": [
    "finding 1",
    "finding 2",
    "finding 3"
  ],
  "method_type": "usability_test",
  "participant_count": 5,
  "completion_rate": 0.80,
  "notable_patterns": "one paragraph summarising task completion patterns and friction points"
}

Focus on: task success/failure patterns, common friction points,
and any UI elements that caused confusion across participants.\
"""


class ResponseAnalyzer:
    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    def analyze(
        self,
        sessions: list[dict],
        transcripts: list[str],
        method_type: str,
        completed_count: int,
        total_count: int,
    ) -> dict:
        """
        Analyze session results. One LLM call.

        Returns an analysis dict that feeds the completion gate
        and the report generator.
        """
        if method_type == "usability_test":
            return self._analyze_usability(
                sessions, transcripts, completed_count, total_count
            )
        return self._analyze_qualitative(
            sessions, transcripts, method_type, completed_count, total_count
        )

    def _analyze_qualitative(
        self,
        sessions: list[dict],
        transcripts: list[str],
        method_type: str,
        completed_count: int,
        total_count: int,
    ) -> dict:
        """LLM thematic analysis for interviews and surveys."""
        transcript_block = self._format_transcripts(sessions)
        prompt = (
            f"METHOD: {method_type}\n"
            f"PARTICIPANTS: {total_count} total, {completed_count} completed\n"
            f"COMPLETION RATE: {completed_count/total_count:.0%}\n\n"
            f"SESSION TRANSCRIPTS:\n{transcript_block}"
        )
        raw = self.llm.generate(prompt=prompt, system=THEMATIC_SYSTEM_PROMPT)
        analysis = _parse_json(raw)
        print(
            f"  Response analyzer ({method_type}): "
            f"{len(analysis.get('themes', []))} themes, "
            f"{len(analysis.get('key_findings', []))} findings"
        )
        return analysis

    def _analyze_usability(
        self,
        sessions: list[dict],
        transcripts: list[str],
        completed_count: int,
        total_count: int,
    ) -> dict:
        """Deterministic metrics + LLM interpretation for usability tests."""
        transcript_block = self._format_transcripts(sessions)
        rate = completed_count / total_count if total_count > 0 else 0
        prompt = (
            f"METHOD: usability_test\n"
            f"PARTICIPANTS: {total_count}\n"
            f"COMPLETED: {completed_count}\n"
            f"COMPLETION RATE: {rate:.0%}\n\n"
            f"SESSION TRANSCRIPTS AND TASK NOTES:\n{transcript_block}"
        )
        raw = self.llm.generate(prompt=prompt, system=USABILITY_SYSTEM_PROMPT)
        analysis = _parse_json(raw)
        # Overwrite LLM-reported metrics with deterministic values
        analysis["completion_rate"] = rate
        analysis["participant_count"] = total_count
        analysis["method_type"] = "usability_test"
        print(
            f"  Response analyzer (usability_test): "
            f"{len(analysis.get('themes', []))} themes, "
            f"completion rate {rate:.0%}"
        )
        return analysis

    @staticmethod
    def _format_transcripts(sessions: list[dict]) -> str:
        """Format sessions into a readable block for the LLM prompt."""
        blocks = []
        for s in sessions:
            status = "COMPLETED" if s.get("completed") else "ABANDONED"
            blocks.append(
                f"--- {s['persona_name']} ({status}) ---\n"
                f"{s.get('transcript', '')}\n"
                f"Notes: {s.get('task_notes', '')}"
            )
        return "\n\n".join(blocks)


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