"""
methods/usability_test.py

Usability test method adapter.
Simulates a task-completion session: the participant attempts defined
tasks, narrating their actions (think-aloud style).

Used by: study 2 (task_completion — checkout flow).
Distress gate does NOT apply to usability_test (see gates.yaml).
"""

from __future__ import annotations

from methods.base import SIMULATION_RULES, BaseMethod, _persona_block


class UsabilityTestMethod(BaseMethod):
    @property
    def method_type(self) -> str:
        return "usability_test"

    def _system_prompt(self) -> str:
        return f"""\
You are simulating a participant in a usability test (think-aloud protocol).
The participant attempts defined tasks and narrates their actions and thoughts.

Return ONLY valid JSON — no markdown, no explanation:
{{
  "completed": true,
  "transcript": "Participant thinks aloud: [narration of task attempt]\\nOutcome: [completed/abandoned and why]",
  "task_notes": "One sentence on task completion, clicks, and any friction points"
}}

The transcript should include:
- The participant's think-aloud narration as they attempt the task
- Specific observations about the UI (what they notice, click, miss)
- A clear outcome: completed successfully, partially completed, or abandoned

{SIMULATION_RULES}"""

    def _user_prompt(self, persona: dict, protocol: dict) -> str:
        tasks = "\n".join(f"- {t}" for t in protocol.get("tasks", []))
        metrics = protocol.get("success_metrics", {})
        return (
            f"PERSONA:\n{_persona_block(persona)}\n\n"
            f"STUDY TYPE: {protocol.get('research_question_type', '')}\n\n"
            f"TASKS TO COMPLETE:\n{tasks}\n\n"
            f"SUCCESS METRICS: {metrics}"
        )