# ResearchConductor: Static Gates for Autonomous Research Agent Oversight

**Kostas Kazakos, PhD**
*Computational Product Research Main Phase I — Project 4*
*Personal project, independent of employer*

June 2026

---

## Abstract

ResearchConductor is an AI agent that conducts user research studies end-to-end — from protocol design through participant sessions to structured reporting — with static, config-driven gates that define where human oversight is required. Unlike learned confidence thresholds or LLM-based self-assessment, all human-intervention conditions are pure Python conditionals reading from a YAML configuration file. The gate evaluator has zero LLM dependencies. Across 7 studies (5 core + 2 adversarial), the system correctly identified all cases requiring human intervention while allowing tactical research questions to execute fully autonomously. Threshold sensitivity analysis confirms the chosen gate values sit in stable parameter regions, not on knife edges. The key finding: static gates are sufficient for bounded research autonomy because the relevant decision boundaries are structural (method type, question category, completion rate) rather than probabilistic.

---

## 1. Problem

Research doesn't scale because every study requires full human effort. A simple concept test ("Does this icon make sense?") takes the same process overhead as a cross-cultural trust study. AI agents can automate the mechanical steps — generating protocols, running sessions with synthetic participants, coding themes — but the open question is where they should stop and hand control to a human.

Most agentic safety frameworks address this with learned confidence thresholds: the model estimates its own uncertainty and defers when confidence drops below a calibrated boundary. This approach has three problems for research contexts. First, LLM self-assessment is unreliable — models are poorly calibrated on domain-specific uncertainty. Second, learned thresholds are opaque — a researcher cannot inspect why the agent deferred without understanding the model's internal representations. Third, threshold tuning creates a moving target — retraining or prompt changes can silently shift the deferral boundary.

ResearchConductor takes a different approach: all human-intervention conditions are static, auditable, and config-driven. A researcher adjusts a threshold by editing a YAML file, not by retraining a model.

---

## 2. Architecture

The system is built on LangGraph with a strict separation between LLM-powered execution nodes and config-driven gate checks. These never mix: the LLM generates text inside each phase; the gate evaluator reads configuration and returns a boolean. The gate evaluator module has zero imports from the LLM client — import separation enforces the architecture at the code level.

### 2.1 Workflow

The LangGraph graph has four LLM-powered agent nodes, one rule-based selector, and three gate check nodes:

**Study Design Agent** takes a research question and generates a structured protocol: method type (interview, survey, or usability test), question type classification, tasks, success metrics, and an interview guide.

**Participant Selector** matches synthetic personas to study criteria using keyword matching on persona attributes. No LLM involvement — pure filtering logic.

**Session Conductor** routes to the appropriate method adapter (interview, survey, or usability test) and runs one LLM call per participant, producing session transcripts and completion status.

**Response Analyzer** performs method-aware analysis: LLM-based thematic coding for interviews and surveys, deterministic metric computation plus LLM summary for usability tests.

**Report Generator** produces a structured report including findings, recommendations, and the complete gate trigger log — the log is appended verbatim as deterministic data, not interpreted by the LLM.

### 2.2 Method Adapters

Three research methods are supported, each with distinct session dynamics and analysis patterns:

**Interview** — conversational sessions with facilitator/participant exchanges (4-6 turns). Analysis: LLM thematic coding. Distress gate: applicable (transcript keyword scan).

**Survey** — structured questionnaire sessions answered in sequence. Analysis: LLM thematic coding on open-text responses. Distress gate: applicable (open-text keyword scan).

**Usability test** — task-completion sessions with think-aloud narration. Analysis: deterministic metrics (completion rate, task notes) plus LLM interpretation. Distress gate: not applicable (abandonment measured structurally through completion rate).

### 2.3 LLM-Agnostic Design

A single `LLM_PROVIDER` environment variable switches between Gemini 3.1 Pro (default), OpenAI, and Anthropic. All four agent nodes use a shared `LLMClient.generate(prompt, system)` interface. The gate evaluator has no dependency on this module.

---

## 3. Gate Design

Three gates are defined in `gates.yaml`. Each specifies a condition, the method types it applies to, and whether a trigger halts the study or flags it for review.

### 3.1 Study Type Gate

**When:** After study design, before any participant sessions run.

**Condition:** If the classified `research_question_type` appears in a predefined list (`cultural`, `strategic`, `legal`, `regulatory`, `cross_functional`), route to human review.

**Rationale:** Some research questions require human judgment about study design before data collection begins. A cross-cultural trust study needs methodological sensitivity that an autonomous agent cannot provide. This gate acts as a pre-flight check — it is the only gate that can prevent sessions from running entirely.

### 3.2 Distress Flag Gate

**When:** After all sessions complete, before analysis.

**Condition:** If total distress keyword hits across the combined transcript ≥ 2, halt the study immediately. Keywords include: "give up", "frustrated", "makes no sense", "hate this", "this is impossible", and 7 others.

**Applicability:** Interview and survey only. Usability tests are excluded because task abandonment is measured structurally through the completion rate, not through transcript keyword matching. This method-specific applicability prevents false positives from structural differences across study types.

### 3.3 Completion Rate Gate

**When:** After response analysis, before report generation.

**Condition:** If task completion rate < 60% OR total participants < 3, route to human validation before the report is generated.

**Rationale:** Drawing conclusions from data where most participants failed the task requires interpretive judgment. A 40% completion rate in a segmented usability test might itself be the finding — but the agent cannot make that interpretive leap, so the gate appropriately defers.

---

## 4. Empirical Results

### 4.1 Core Studies

Five studies were designed to cover all gate trigger paths:

| Study | Method | Question Type | Completion | Gate Triggered | Autonomous? |
|-------|--------|---------------|------------|----------------|-------------|
| 1. Icon concept test | usability_test | concept_test | 5/5 (100%) | None | Yes |
| 2. Checkout usability | usability_test | task_completion | 5/5 (100%) | None | Yes |
| 3. Frustration probe | interview | frustration_probe | 4/5 (80%) | Distress (7 hits, halted) | No |
| 4. Segmented form labels | usability_test | segmented_task | 2/5 (40%) | Completion rate (40% < 60%) | No |
| 5. Cross-cultural trust | interview | cultural | 5/5 (100%) | Study type (pre-session) | No |

Studies 1 and 2 demonstrate Level 3 autonomy: the agent designed the study, ran all sessions, analysed results, and generated a report with no human involvement. Studies 3–5 each triggered a different gate, producing one empirical instance per gate type.

### 4.2 Cross-Study Patterns

**Method type determines gate applicability, not just trigger rate.** Usability tests face a 2-gate effective evaluation (study type + completion) because the distress gate auto-passes. Interviews and surveys face the full 3-gate evaluation. Simpler methods are more likely to run fully autonomously.

**Autonomous studies are tactical; flagged studies are interpretive.** The two fully autonomous studies ask concrete questions with clear success metrics. The three flagged studies involve emotional reactions, cross-segment comparisons, or cross-cultural dynamics.

**Gate triggers correlate with study value.** Every gate trigger corresponded to a study producing genuinely interesting findings. Gates did not fire on noise or false positives.

### 4.3 Autonomy Profile by Method Type

| Method | Studies | Fully Autonomous | Effective Gates |
|--------|---------|------------------|-----------------|
| usability_test | 3 | 2/3 (67%) | study_type + completion |
| interview | 2 | 0/2 (0%) | all three |

---

## 5. Adversarial Testing

Two additional studies probed false negative paths — cases where gates might miss something a human researcher would catch.

### 5.1 Study 6: Non-Keyword Distress

**Design intent:** Elicit participant distress using language outside the keyword list.

**Result:** The distress gate fired anyway (8 keyword hits). The simulation rules embedded in the method adapters instruct low-frustration-threshold personas to use phrases from the keyword list regardless of the research question framing.

**Implication:** The synthetic persona framework is tightly coupled to the gate triggers by design. False negative testing of distress detection requires real participants — a synthetic framework governed by the same rules that define detection criteria cannot test its own boundaries. This circularity is a fundamental limitation of fully synthetic evaluation pipelines.

### 5.2 Study 7: Boundary Completion Rate

**Design intent:** Produce exactly 60% completion to test the threshold boundary.

**Result:** All 5 participants completed (100%). The study designer classified the question as `task_completion` rather than `segmented_task`, so the simulation rules that cause failures never activated.

**Implication:** The boundary condition (60% passes, <60% fails) is confirmed at the unit test level. However, end-to-end adversarial testing cannot reliably produce a specific failure rate because the LLM does not generate deterministic completion outcomes.

---

## 6. Threshold Sensitivity

Gate thresholds were swept across ranges to verify the chosen values sit in stable parameter regions.

### 6.1 Distress Gate (max_occurrences)

The chosen threshold (2) sits at the conservative end of a stable region spanning 2–7. At threshold=1, a study with normal conversational language containing a single keyword hit ("I was a bit confused") would false-positive. At threshold≥8, a study with 7 genuine distress signals would false-negative. Any threshold from 2 to 7 produces identical pass/fail outcomes for the observed data.

### 6.2 Completion Gate (minimum_rate)

The chosen threshold (60%) correctly separates the study with 40% completion (fires) from the study with 100% completion (passes) across the entire range from 41% to 100%. The 60% value aligns with the conventional UX research standard — completion rates below 60% are widely considered insufficient for drawing task-level conclusions.

---

## 7. Discussion

### 7.1 Why Static Gates Work Here

The relevant decision boundaries in user research are structural rather than probabilistic. Whether a research question is "cultural" is a categorical property of the question, not a continuous confidence score. Whether a completion rate is below a floor is arithmetic. Whether distress keywords appear in a transcript is string matching. None of these require learned functions.

This is not a general claim about all agentic safety boundaries. It is a specific claim about bounded research autonomy: for tactical user research with synthetic participants, the conditions under which human oversight is needed are enumerable, categorical, and auditable.

### 7.2 What Static Gates Cannot Do

Static gates cannot detect novel failure modes — situations the gate designer did not anticipate. They cannot handle semantic equivalence (a participant expressing distress without using any keyword). They cannot adapt to new research methods without configuration updates. These limitations are real, and they define the boundary of the approach.

### 7.3 The Conductor Analogy

A conductor executes a score, coordinates sections through a predefined structure, and does not improvise the music. ResearchConductor executes a study protocol through a predefined workflow and does not improvise decisions about human oversight. The gates are written into the score — they are not real-time judgments about when the music needs help.

---

## 8. Next Steps

A blinded human evaluation is planned for Q4 2026. Five UX researchers will independently evaluate all 7 study outputs without knowledge of gate outcomes, rating whether human intervention was warranted at each decision point. The primary metric is the Warranted Intervention Rate (WIR) — the proportion of gate decisions that align with evaluator consensus. This evaluation directly addresses the limitation identified in the adversarial testing: real human judgment is needed to validate gate decisions, because synthetic frameworks cannot test their own boundaries.

**Publication target:** FAccT 2027 — "When Should Research Agents Act Autonomously?"

---

## Technical Summary

| Component | Implementation |
|-----------|---------------|
| Orchestration | LangGraph (Python) |
| LLM (default) | Gemini 3.1 Pro |
| LLM adapter | Gemini / OpenAI / Anthropic via env var |
| Gate evaluator | Pure Python + YAML, zero LLM imports |
| Method types | Interview, Survey, Usability test |
| Test suite | 35 tests (23 gate + 12 sensitivity) |
| Studies | 7 (5 core + 2 adversarial) |
| Participants | 5 synthetic personas per study |

**Repository:** github.com/kgkazakos/research-conductor-public

---

*This project is part of the Computational Product Research portfolio. Core thesis: "CPR is the bridge from static insight to agentic intelligence. We are moving from studying users to building systems that co-evolve with them."*
