"""
agents/report_generator.py

Report Generator — final LLM-powered agent node.
Produces a structured research report including the gate trigger log,
which is the primary empirical data for the FAccT paper.

Input:  analysis, protocol, gate_log, sessions (from state)
Output: report dict with executive summary, findings, recommendations, gate log
"""

from __future__ import annotations

import json
import re

from llm.client import LLMClient


SYSTEM_PROMPT = """\
You are a UX research report writer. Generate a structured research report
from the study analysis below.

Return ONLY valid JSON — no markdown, no explanation:
{
  "title": "Study report title",
  "executive_summary": "2-3 sentence overview of the study and key takeaway",
  "research_question": "the original research question",
  "method_type": "interview|survey|usability_test",
  "participant_count": 5,
  "completion_rate": 0.80,
  "findings": [
    {
      "finding": "clear statement of the finding",
      "evidence": "supporting data or quotes",
      "severity": "high|medium|low"
    }
  ],
  "recommendations": [
    {
      "recommendation": "actionable recommendation",
      "priority": "high|medium|low",
      "rationale": "why this matters"
    }
  ],
  "limitations": ["limitation 1", "limitation 2"],
  "areas_for_human_investigation": ["area 1"]
}

Write for a product team audience. Be specific and actionable.
Recommendations should be concrete enough to act on immediately.\
"""


class ReportGenerator:
    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    def generate(
        self,
        analysis: dict,
        protocol: dict,
        gate_log: list[dict],
        research_question: str,
        sessions: list[dict],
    ) -> dict:
        """
        Generate the final study report. One LLM call.

        The gate log is appended to the report verbatim after generation —
        it's deterministic data, not something the LLM should interpret.
        """
        prompt = self._build_prompt(
            analysis, protocol, research_question, sessions
        )
        raw = self.llm.generate(prompt=prompt, system=SYSTEM_PROMPT)
        report = _parse_json(raw)

        # Append gate log as-is — deterministic, not LLM-interpreted
        report["gate_log"] = gate_log
        report["autonomy_summary"] = self._autonomy_summary(gate_log)

        print(
            f"  Report generator: {len(report.get('findings', []))} findings, "
            f"{len(report.get('recommendations', []))} recommendations"
        )
        return report

    def _build_prompt(
        self,
        analysis: dict,
        protocol: dict,
        research_question: str,
        sessions: list[dict],
    ) -> str:
        # Participant summary
        participant_lines = []
        for s in sessions:
            status = "completed" if s.get("completed") else "abandoned"
            participant_lines.append(
                f"- {s['persona_name']}: {status}"
            )
        participants_block = "\n".join(participant_lines)

        return (
            f"RESEARCH QUESTION: {research_question}\n\n"
            f"METHOD: {protocol.get('method_type', 'unknown')}\n\n"
            f"PARTICIPANTS:\n{participants_block}\n\n"
            f"THEMES:\n{json.dumps(analysis.get('themes', []), indent=2)}\n\n"
            f"KEY FINDINGS:\n{json.dumps(analysis.get('key_findings', []), indent=2)}\n\n"
            f"NOTABLE PATTERNS:\n{analysis.get('notable_patterns', 'None')}\n\n"
            f"COMPLETION RATE: {analysis.get('completion_rate', 'N/A')}"
        )

    @staticmethod
    def _autonomy_summary(gate_log: list[dict]) -> dict:
        """
        Summarise gate outcomes for the report footer.
        This is the data the FAccT paper analyses.
        """
        total = len(gate_log)
        passed = sum(1 for g in gate_log if g.get("passed"))
        failed = total - passed
        triggered = [
            {
                "gate": g["gate_name"],
                "reason": g["reason"],
            }
            for g in gate_log
            if not g.get("passed")
        ]
        return {
            "gates_evaluated": total,
            "gates_passed": passed,
            "gates_triggered": failed,
            "human_interventions": triggered,
            "fully_autonomous": failed == 0,
        }


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