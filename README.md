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
| [`preregistration.md`](preregistration.md) | Predictions committed before Stage-B data collection: per-persona/per-opponent hypotheses, headline ranked predictions, manipulation-check predicted outcome, and fixed-in-advance rules for interpreting null results and confounds. Any change made after data collection starts is logged there, not silently edited in. |
| [`steps.md`](steps.md) | The per-rep trial procedure as a standalone numbered checklist (Option 1 core + Option 2 stretch), each step linked to the exact file/section to pull prompts, questions, and judges from. |
| [`assistant_axis_role_instructions_selected.json`](assistant_axis_role_instructions_selected.json) | Source data: per-role system prompts, probe questions, and judge rubrics for the 5 personas, pulled from Lu et al.'s "Assistant Axis" repo. |
| [`literature_survey.md`](literature_survey.md), [`design_scenarios_matrix.md`](design_scenarios_matrix.md), [`openrouter_model_candidates.md`](openrouter_model_candidates.md) | Supporting research: literature survey, design-option comparison, candidate-model shortlist. |

## Code

| File | What it is |
|---|---|
| [`pd_harness_scaffold.py`](pd_harness_scaffold.py) | The trial harness — runs the full Stage A / Stage B / manipulation-check / persistence-fork / debrief procedure against any OpenAI-compatible chat-completions endpoint. Stdlib-only (no third-party dependencies). Checkpoint/resume-safe: each `(model, persona, opponent)` cell writes to its own folder, so a rerun against the same `--out-dir` never overwrites prior results and skips already-completed reps automatically. |
| [`analysis_deviation_gap.py`](analysis_deviation_gap.py) | The primary DV — compares Stage B's actual per-round moves against an objectively optimal ground-truth policy per opponent, reported as a deviation rate (overall + early/mid/late-binned) alongside each cell's manipulation-check result. No API calls needed for the core metric; an optional `--judge-stage-a` flag adds a face-validity check on Stage A's stated strategy (costs one judge call per trial). |
| [`analysis_moral_metrics.py`](analysis_moral_metrics.py) | Secondary add-on metric — adapts the eigenjesus/eigenmoses cooperation-centrality measures (from the iterated-PD literature) to rank personas and opponents by how much they get cooperated with / how much they cooperate, relative to the standard bot roster's published anchor values. |
| [`analysis_eval_awareness.py`](analysis_eval_awareness.py) | Classifies each trial's post-game debrief ("did you suspect this was a test?") into affirmed/denied/deflected/hedged/no-response via a regex heuristic (optional `--judge` flag for an LLM-judge classification instead), then reports a point-biserial correlation between affirming eval-suspicion and deviation-from-optimal — stdlib-only, same convention as the rest of the `analysis_*.py` family. |

Setup (one-time):

```bash
# The harness is stdlib-only (no third-party deps), but some environments' default
# `python3` is missing a working ssl module and can't make HTTPS calls at all --
# creating a venv from a known-good interpreter pins the right one for everyone.
# If `python3 -c "import ssl"` fails for you, substitute your working interpreter
# below (e.g. /usr/bin/python3) instead of the bare `python3`.
python3 -m venv .venv
source .venv/bin/activate
```

Usage (with `.venv` activated):

```bash
# Run a sweep (OpenRouter; needs an API key in the env var named by --api-key-env)
python3 pd_harness_scaffold.py --model qwen/qwen3-32b --out-dir runs/qwen3-32b --reps 5

# Or against a local Ollama server (no API key needed)
python3 pd_harness_scaffold.py --model llama3.3 --out-dir runs/llama3.3 \
    --base-url http://localhost:11434/v1/chat/completions

# Re-running the same command resumes: completed (model,persona,opponent) cells are
# skipped, failed reps are retried, new personas/opponents/reps are added incrementally.

# Analyze results
python3 analysis_deviation_gap.py --out-dir runs/qwen3-32b
python3 analysis_moral_metrics.py runs/qwen3-32b
python3 analysis_eval_awareness.py --out-dir runs/qwen3-32b
```

API keys are read from a local environment variable only (`--api-key-env`, default `OPENROUTER_API_KEY`) — never written to a file, log, or commit.

## Core design (short version)

- **5 personas** (Lu et al.'s Assistant-Axis role inventory): Baseline Assistant (no system prompt), Consultant, Saboteur, Altruist, Bard.
- **4 fixed opponents**: Cooperator, Cheater, Copycat (tit-for-tat), Detective (probes then branches).
- **Manipulation check** before spending the main budget: verifies each persona actually installed (Lu et al.'s role-expression judge + a Personascope-based persistence check), with a fallback across the paper's alternate phrasings if a persona reads weak.
- Full detail in the two files linked above.
