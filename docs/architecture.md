# ResearchConductor — Architecture

**CPR Portfolio — Project 4**
*Personal project, independent of employer.*

---

## Overview

ResearchConductor is an AI agent that conducts user research studies autonomously, with static rule-based gates defining where human oversight is required. The agent executes a predefined study protocol — it does not decide what research to do or when to defer to humans through learned functions. All human-intervention conditions are config-driven thresholds defined in `gates.yaml`.

---

## Design Principles

**Conductor, not improviser.** The agent follows a score (protocol), coordinates sections (participants, analysis), and produces a structured output (report). It does not improvise decisions about research strategy or human oversight.

**Static gates, not learned thresholds.** Every human-intervention condition is a pure Python conditional reading from YAML configuration. The gate evaluator has zero LLM dependencies. Thresholds are adjusted by editing config, not by retraining.

**Method-aware autonomy.** Gate applicability varies by research method. The distress gate applies to interviews and surveys but not usability tests (where abandonment is measured structurally). This prevents false positives from structural differences across study types.

**LLM-agnostic execution.** A single `LLM_PROVIDER` environment variable switches between Gemini, OpenAI, and Anthropic. All four agent nodes go through one adapter interface. The gate evaluator never imports the LLM client.

---

## LangGraph Workflow

```
Research Question
        │
   Study Design Agent ─── LLM call: question → protocol
        │
   [Gate: Study Type] ── config check: question type in requires_review?
        │                        │
        │ PASS                   │ FAIL → Human Review
        │                        │
   Participant Selector ── rule-based: match personas to criteria (no LLM)
        │
   Session Conductor ──── LLM call × N participants: protocol → transcripts
        │
   [Gate: Distress] ───── config check: keyword hits ≥ threshold?
        │                        │
        │ PASS                   │ FAIL → Immediate Halt
        │                        │
   Response Analyzer ──── LLM call: transcripts → themes + metrics
        │
   [Gate: Completion] ─── config check: completion rate < minimum?
        │                        │
        │ PASS                   │ FAIL → Validate Findings
        │                        │
   Report Generator ───── LLM call: analysis → structured report + gate log
```

---

## Gate Configuration

All gates are defined in `gates/gates.yaml`. Each gate specifies:

- **Condition:** The threshold or list that triggers human review
- **applies_to:** Which method types the gate evaluates (others auto-pass)
- **halt_immediately:** Whether to stop the study or just flag for review

Three gates are currently defined:

1. **Study type gate** — fires before sessions if the research question type appears in a predefined list (e.g., cultural, strategic, legal)
2. **Distress flag gate** — fires during sessions if distress keyword count exceeds the threshold; applies to interview and survey only
3. **Completion rate gate** — fires after analysis if task completion falls below the minimum rate with sufficient participants

---

## Method Types

ResearchConductor supports three research methods, each with a dedicated adapter:

- **Interview** — conversational sessions with facilitator/participant exchanges
- **Survey** — structured questionnaire sessions answered in sequence
- **Usability test** — task-completion sessions with think-aloud narration

The study design agent classifies the research question and selects the appropriate method. Method type determines which gates apply and how sessions are conducted and analysed.

---

## Empirical Results

5 test studies were executed across all gate paths:

| Outcome | Count | Studies |
|---------|-------|---------|
| Fully autonomous (no gates triggered) | 2 | concept test, checkout usability |
| Study type gate triggered (pre-session) | 1 | cross-cultural trust |
| Distress gate triggered (mid-session halt) | 1 | frustration probe |
| Completion gate triggered (post-analysis) | 1 | segmented form labels |

See `docs/gate_analysis.md` for the full empirical analysis.

---

## Publication Target

FAccT 2027 — "When Should Research Agents Act Autonomously?"