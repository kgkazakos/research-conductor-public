# ResearchConductor

**CPR Portfolio — Project 4**  
*Personal project, independent of employer.*

AI agent that conducts user research studies autonomously, with static rule-based gates defining where human oversight is required.

## Status
🔨 In development — Jun 9–21 2026

## Method types
- Interview (scripted conversational sessions)
- Survey (structured questionnaire sessions)
- Usability test (task completion sessions)

## Gate conditions (see `gates/gates.yaml`)
Three static gates, all config-driven:
1. **Study type gate** — fires before sessions, if question type requires human oversight
2. **Distress flag gate** — fires during sessions, on keyword threshold breach
3. **Completion rate gate** — fires after analysis, if completion rate is below floor

## Tech stack
LangGraph · Gemini 3.1 Pro (default) · LLM-agnostic adapter (OpenAI, Anthropic) · Python 3.14

## Setup
```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # add API keys
pytest tests/test_gate_evaluator.py -v  # verify gates before running studies
```

## Environment variables
```
LLM_PROVIDER=gemini        # gemini | openai | anthropic
GEMINI_API_KEY=...
OPENAI_API_KEY=...         # optional
ANTHROPIC_API_KEY=...      # optional
```

## Publication target
FAccT 2027 — "When Should Research Agents Act Autonomously?"
