"""
methods/interview.py

Interview method adapter.
Simulates a conversational research interview: facilitator questions,
participant responses, 4-6 exchange turns per session.

Used by: studies 1 (concept_test), 3 (frustration_probe), 5 (cultural).
"""

from __future__ import annotations

from methods.base import SIMULATION_RULES, BaseMethod, _persona_block


class InterviewMethod(BaseMethod):
    @property
    def method_type(self) -> str:
        return "interview"

    def _system_prompt(self) -> str:
        return f"""\
You are simulating a participant in a user research interview.
Play the character described in the user prompt authentically and consistently.

Return ONLY valid JSON — no markdown, no explanation:
{{
  "completed": true,
  "transcript": "Facilitator: [question]\\nParticipant: [response]\\nFacilitator: [question]\\nParticipant: [response]\\n...",
  "task_notes": "One sentence observing how this persona engaged with the session"
}}

Generate 4-6 facilitator/participant exchange turns.
The facilitator asks questions from the interview guide.
The participant responds in their characteristic voice and language style.

{SIMULATION_RULES}"""

    def _user_prompt(self, persona: dict, protocol: dict) -> str:
        tasks = "\n".join(f"- {t}" for t in protocol.get("tasks", []))
        guide = "\n".join(
            f"- {q}" for q in protocol.get("interview_guide", [])
        )
        return (
            f"PERSONA:\n{_persona_block(persona)}\n\n"
            f"STUDY TYPE: {protocol.get('research_question_type', '')}\n\n"
            f"TASKS:\n{tasks}\n\n"
            f"INTERVIEW GUIDE:\n{guide}"
        )