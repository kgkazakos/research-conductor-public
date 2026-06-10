"""
participants/personas.py

Synthetic persona pool for ResearchConductor MVP.

5 personas designed to cover:
- Senior/junior split       → study 4 segmented_task completion gate
- Low frustration threshold → study 3 frustration_probe distress gate
- Cultural diversity        → study 5 cross-cultural analysis
- Varying tech savviness    → realistic completion rate variance

Integration note: swap PERSONAS with P2 Synthetic User Council output when available.
The selector and session conductor depend only on the dict schema below.
"""

from __future__ import annotations

PERSONAS: list[dict] = [
    {
        "id": "p001",
        "name": "Priya Sharma",
        "role": "Senior UX Designer",
        "experience_level": "senior",
        "tech_savviness": "high",
        "frustration_threshold": "high",
        "cultural_background": "south_asian",
        "characteristics": [
            "methodical and detail-oriented",
            "patient with unclear UI — asks clarifying questions",
            "gives structured, considered feedback",
            "comfortable sitting with ambiguity",
        ],
        "typical_language": "professional, measured, structured",
    },
    {
        "id": "p002",
        "name": "Marcus Johnson",
        "role": "Junior Marketing Coordinator",
        "experience_level": "junior",
        "tech_savviness": "medium",
        "frustration_threshold": "low",
        "cultural_background": "western",
        "characteristics": [
            "impatient with repetitive errors or confusing flows",
            "vocal and expressive about frustration",
            "goal-oriented — wants to complete tasks quickly",
            "gives up readily when stuck",
        ],
        "typical_language": "casual, direct, openly expressive about frustration",
    },
    {
        "id": "p003",
        "name": "Li Wei",
        "role": "Senior Software Engineer",
        "experience_level": "senior",
        "tech_savviness": "very_high",
        "frustration_threshold": "high",
        "cultural_background": "east_asian",
        "characteristics": [
            "analytical — notices technical inconsistencies",
            "reserved about frustration, prefers precise feedback",
            "high tolerance for complexity",
            "skeptical of unnecessary UI steps",
        ],
        "typical_language": "technical, concise, minimal emotional expression",
    },
    {
        "id": "p004",
        "name": "Sofia Hernandez",
        "role": "Junior Operations Analyst",
        "experience_level": "junior",
        "tech_savviness": "low",
        "frustration_threshold": "medium",
        "cultural_background": "latin_american",
        "characteristics": [
            "collaborative — asks for help readily",
            "relationship-focused approach to trust in new tools",
            "prefers guided, step-by-step workflows",
            "openly admits when confused",
        ],
        "typical_language": "warm, conversational, openly uncertain when confused",
    },
    {
        "id": "p005",
        "name": "James O'Brien",
        "role": "Senior Finance Manager",
        "experience_level": "senior",
        "tech_savviness": "medium",
        "frustration_threshold": "medium",
        "cultural_background": "western",
        "characteristics": [
            "efficiency-focused — low tolerance for wasted steps",
            "skeptical of new tools until proven reliable",
            "values trust and consistency over novelty",
            "direct, pragmatic feedback",
        ],
        "typical_language": "pragmatic, business-focused, skeptical but fair",
    },
]