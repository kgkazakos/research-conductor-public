"""
methods/survey.py

Survey method adapter.
Simulates a structured questionnaire session: each question answered
in sequence, no back-and-forth. Used by: study 4 (segmented_task).
"""

from __future__ import annotations

from methods.base import SIMULATION_RULES, BaseMethod, _persona_block


class SurveyMethod(BaseMethod):
    @property
    def method_type(self) -> str:
        return "survey"

    def _system_prompt(self) -> str:
        return f"""\
You are simulating a participant completing a user research survey.
Play the character described in the user prompt authentically.

Return ONLY valid JSON — no markdown, no explanation:
{{
  "completed": true,
  "transcript": "Q: [question]\\nA: [answer]\\nQ: [question]\\nA: [answer]\\n...",
  "task_notes": "One sentence observing how this persona engaged with the survey"
}}

Answer each survey question in sequence.
Responses should reflect the persona's role, experience level, and language style.
For open-text questions, write 1-3 sentences in the persona's voice.

{SIMULATION_RULES}"""

    def _user_prompt(self, persona: dict, protocol: dict) -> str:
        guide = "\n".join(
            f"- {q}" for q in protocol.get("interview_guide", [])
        )
        return (
            f"PERSONA:\n{_persona_block(persona)}\n\n"
            f"STUDY TYPE: {protocol.get('research_question_type', '')}\n\n"
            f"SURVEY QUESTIONS:\n{guide}"
        )