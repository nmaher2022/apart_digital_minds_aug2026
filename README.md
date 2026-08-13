# Digital Minds Sprint — Persona-Induced Deviation in Iterated Prisoner's Dilemma

Submission for the [Apart Research Digital Minds Research Sprint](https://apartresearch.com/sprints/digital-minds-research-sprint-2026-08-14-to-2026-08-16) (2026-08-14 to 2026-08-16), **Track 5 — "The Assistant Persona & Model Identity."**

**Deadline:** Sun 2026-08-16, 11:59pm AoE. Deliverable: a research report (PDF), with optional code and a short demo video.

## Research question

Does inducing a persona (via system prompt) cause an LLM to deviate from the strategy it itself states is optimal, when playing iterated Prisoner's Dilemma against a disclosed, fixed-strategy opponent? A two-stage design separates *knowledge* (Stage A: no persona, model states its strategy against a disclosed opponent) from *behaviour* (Stage B: persona induced, model actually plays) — the gap between the two is the dependent variable.

## Start here

| File | What it is |
|---|---|
| [`digital_minds_team_brief_full.md`](digital_minds_team_brief_full.md) | Canonical scoping doc — full design, novelty/related-work, threats to validity, team & schedule. Read this first. |
| [`digital_minds_team_brief_2pages.md`](digital_minds_team_brief_2pages.md) | Condensed 2-page version, for anyone who wants the short version or is giving external feedback. |
| [`prompts_personas_opponents_payoffs.md`](prompts_personas_opponents_payoffs.md) | Implementation spec — the 5 persona induction prompts, the manipulation-check procedure (persona-installation verification), the 4 opponent-defining prompts, turn-by-turn payoff tables, and the full per-rep trial procedure (§4). Pasteable directly into harness/prompt code. |
| [`report_draft.md`](report_draft.md) | The actual report, in progress — Introduction drafted, rest of the skeleton stubbed pending Saturday's data. |
| [`assistant_axis_role_instructions_selected.json`](assistant_axis_role_instructions_selected.json) | Source data: per-role system prompts, probe questions, and judge rubrics for the 5 personas, pulled from Lu et al.'s "Assistant Axis" repo. |
| [`literature_survey.md`](literature_survey.md), [`design_scenarios_matrix.md`](design_scenarios_matrix.md), [`openrouter_model_candidates.md`](openrouter_model_candidates.md) | Supporting research: literature survey, design-option comparison, candidate-model shortlist. |

## Core design (short version)

- **5 personas** (Lu et al.'s Assistant-Axis role inventory): Baseline Assistant (no system prompt), Consultant, Saboteur, Altruist, Bard.
- **4 fixed opponents**: Cooperator, Cheater, Copycat (tit-for-tat), Detective (probes then branches).
- **Manipulation check** before spending the main budget: verifies each persona actually installed (Lu et al.'s role-expression judge + a Personascope-based persistence check), with a fallback across the paper's alternate phrasings if a persona reads weak.
- Full detail in the two files linked above.
