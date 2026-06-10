"""
participants/selector.py

Rule-based participant selector. No LLM calls.

Filters the persona pool based on participant_criteria from the StudyProtocol.
Segmented studies (e.g. senior vs junior) receive the full pool so the
session conductor can track outcomes per segment.

Falls back to the full pool if a filter leaves fewer than 3 personas
(below the minimum_participants gate threshold).
"""

from __future__ import annotations

from participants.personas import PERSONAS


class ParticipantSelector:
    def __init__(self, pool: list[dict] | None = None) -> None:
        self.pool = pool or PERSONAS

    def select(self, protocol: dict, method_type: str) -> list[dict]:
        """
        Select participants for a study.

        Args:
            protocol:    StudyProtocol.to_dict() — reads participant_criteria.
            method_type: Passed for future method-specific logic.

        Returns:
            List of selected persona dicts.
        """
        criteria = protocol.get("participant_criteria", {})
        experience_filter = criteria.get("experience_level", "any")
        count = int(criteria.get("count", 5))

        if experience_filter == "any":
            selected = self.pool[:]
        else:
            selected = [
                p for p in self.pool
                if p["experience_level"] == experience_filter
            ]
            # Safety: fall back to full pool if filter leaves fewer than 3
            if len(selected) < 3:
                print(
                    f"  Participant selector: filter '{experience_filter}' "
                    f"returned {len(selected)} — falling back to full pool"
                )
                selected = self.pool[:]

        selected = selected[:count]
        print(
            f"  Participant selector: {len(selected)} personas selected "
            f"(experience_level={experience_filter})"
        )
        return selected