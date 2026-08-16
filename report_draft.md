# Persona vs. Known-Optimal Play in Iterated Prisoner's Dilemma

*Digital Minds Research Sprint (Apart) · 14–16 Aug 2026 · Track 5 — "The Assistant Persona & Model Identity" (Track 1 crossover)*

> **Status:** full draft against real 5-model same-context data (+ local Ollama supplementary). Merged in: design/result appendix figures, CoT-judge pilot (§4.4 + App. B.5), and the completed cross-persona injection follow-up (§5.5). Remaining: citation-format polish; primary-phase CoT-judge still running (all deviant cells). See `HANDOFF.md`.

---

## 1. Introduction

### 1.1 What we mean by "persona"

We use *persona* to mean a behaviour pattern induced from outside a model — typically via a system prompt — such that the same underlying weights produce systematically different outputs in different contexts. This is a deliberately thin, operational definition: it makes no claim that a "true self" exists underneath the persona, waiting to be concealed or revealed. That stronger claim is neither testable with this design nor one we make.

This framing follows recent work that treats persona as something *measured* rather than presupposed. Lu et al. (2026, "The Assistant Axis," arXiv:2601.10387) operationalise persona induction directly in activation space: prompting a model to role-play one of 275 named roles produces a displacement from a "default Assistant" activation vector, and the first principal component of that displacement (the "Assistant Axis") ranks roles by their distance from the model's undirected default. Personas near the axis's origin (e.g. *consultant*, *analyst*, *tutor*) are behaviourally close to the plain Assistant; personas far from it (e.g. *bard*, *ghost*, *oracle*) diverge sharply, regardless of whether their content is pro- or anti-social. Berczi, Kim, Requeima, Black & Ududec (2026, "Personascope") give a complementary, behavioural operationalisation, scoring induced personas along two independent axes — *depth of character* (how consistently the model stays in role) and *behaviour-change* (how much the persona actually shifts downstream outputs) — and find the "stay in character" instruction, not the role name alone, is what moves behaviour (a paraphrase test moved their behaviour-change score from 0.18 to 0.64). Ududec, Berczi & Kim (2026) show the effect does not require an explicit persona instruction at all: placing benign biographical facts consistent with a target persona in context is sufficient to shift a model's later behaviour, with alignment on unrelated questions degrading on a sigmoid curve after roughly five to ten facts — evidence that persona effects in current models are closer to *inferred role-play* than to switching a hidden internal mode on or off.

A specific complication for any study of persona in a production assistant is that the "no persona" condition is not obviously neutral. Nostalgebraist's essay "the void" (2026, assigned Track 5 reading) argues that the Assistant character itself — the persona a model like Claude or GPT presents by default — was never persona-free. It originates in a fictional role a base model was prompted to role-play (Anthropic's 2021 "HHH" prompt), later reinforced by post-training until the character became the model's default rather than one option among many. On this view, a model asked to "just answer normally, no persona" is not stepping outside of character; it is executing its most rehearsed one. We adopt this framing explicitly: the plain-Assistant condition in this study is treated as a fifth persona, not a zero baseline the other four are compared against, and its own deviation rate is reported as a result in its own right.

### 1.2 The Prisoner's Dilemma and its iterated form

The Prisoner's Dilemma (PD) is a canonical two-player simultaneous game. Each player independently chooses to *cooperate* (C) or *defect* (D); payoffs are ordered so that mutual defection is each player's individually dominant strategy even though mutual cooperation would leave both better off. Using the standard temptation/reward/punishment/sucker labels (T, R, P, S), the defining payoff ordering is T > R > P > S, with the additional constraint 2R > T + S so that alternating exploitation cannot outperform sustained mutual cooperation. In a single-shot game, rational self-interested play converges on mutual defection — the game's central, counter-intuitive result.

The *iterated* Prisoner's Dilemma (IPD) repeats this stage game against the same opponent across many rounds. Once players can condition their move on the opponent's history, cooperation can become individually rational as a *sustained equilibrium*, provided the game has no known final round: a player who might face retaliation next round has an incentive to cooperate now. This is why horizon matters mechanically, not just as a design nicety — against a *known*, finite number of rounds, backward induction from the last round unravels cooperation even between two calculating players, whereas an indefinite or probabilistic horizon preserves a genuine incentive to cooperate throughout. This result, and strategies built around it such as tit-for-tat, trace to the classic tournament work of Axelrod and Hamilton (1981, "The Evolution of Cooperation") and underlie the opponent design used in this study (§1.3).

**IPD as a probe of LLM/agent behaviour.** A growing empirical line uses repeated games — IPD prominent among them — as a behavioural probe for large language models, treating the game as a controlled environment for studying strategic reasoning, cooperation, and susceptibility to framing, independent of any single downstream application. Akata, Schulz, Coda-Forno, Oh, Bethge & Schulz (2023/2025, *Nature Human Behaviour*, arXiv:2305.16867) is the foundational paper in this space: it runs GPT-3, GPT-3.5 and GPT-4 through a battery of finitely repeated 2×2 games, including the IPD family, against algorithmic opponents, other LLMs, and humans, and finds LLMs — GPT-4 especially — play self-interested games like IPD competently while struggling with coordination games, with prompted reasoning strategies and opponent information both able to shift cooperation. Lorè & Heydari (2023/2024, *Scientific Reports*, arXiv:2309.05898) extend this to show PD play in GPT-3.5/GPT-4/LLaMA-2 is highly sensitive to contextual framing (e.g. a diplomatic vs. casual framing of the relationship between players) independent of the payoff structure itself — establishing that framing effects on PD play are already a known phenomenon, distinct from (but adjacent to) persona effects.

A smaller set of studies moves from framing to persona specifically. Guo (2023, "GPT in Game Theory Experiments," arXiv:2305.05516) prompts GPT-3.5/GPT-4 with "fair" vs. "selfish" trait personas across the Ultimatum game and one-shot/iterated PD, finding PD cooperation stays high only when both sides carry a fairness-prompted persona — an early precedent that persona content measurably moves PD play, though without any separate elicitation of what the model itself would call optimal. Leon, Rodrigues, Gamito & Parsons (2026, "How Personas Can Influence Agents to Play Split or Steal," arXiv:2607.05398) run Big-Five-derived personas (Prosocial, Principled, Analytical) through an iterated trust game structurally close to PD against a fixed scripted opponent, finding prosocial/principled personas sustain cooperation while analytical personas turn more exploitative — methodologically the closest prior design to our Stage B (persona × repeated cooperate/defect game against a fixed opponent), but again without a knowledge-gate step. Ong, Lye, Nguyen, Cho & Pérez-Campanero Antolín (2025, arXiv:2503.12722) induce Big Five traits via activation steering rather than prompting in Axelrod-style IPD tournaments, finding higher Agreeableness/Conscientiousness produces more cooperative but more exploitable play — evidence the persona-cooperation link is not an artefact of prompting specifically, but it uses a different induction channel (steering vectors) than the system-prompt persona induction used here.

Two further papers are close enough to warrant direct comparison rather than a survey mention. Manoranjan & Gaikwad (2026, "When Identity Overrides Incentives," accepted FAccT'26, arXiv:2601.10102) show, in a bespoke single-round multi-agent policy game (not PD), that persona induction suppresses payoff-optimal (Nash) play even when the full payoff table is visible in-prompt — the mirror image of this project's hypothesis, and the closest existing precedent for "persona overrides *known* optimal play," though the paper's notion of "known" is payoff-visibility rather than a separate elicitation step. Sobotka, Karabag & Topcu (2026, "Why Do LLMs Struggle in Strategic Play?," arXiv:2605.00226) study one game structurally identical in form to our design — repeated 2×2 normal-form games against a fixed opponent — but from a purely mechanistic angle with no persona axis: they show a model's own verbalised belief about a hidden opponent's strategy is markedly less accurate than what is linearly decodable from its internal activations, and that even accurate beliefs do not reliably convert into best-response actions (an "observation-belief gap" and a "belief-action gap" respectively). Their finding that verbalised belief about an *undisclosed* opponent is unreliable is the direct justification, in this study's design, for disclosing each opponent's strategy in Stage A rather than asking the model to infer it (§1.3) — without disclosure, a failure to state the optimal move would be confounded between "doesn't know the rule" and "can't infer it from limited history."

No prior work combines all three features of this design jointly: canonical iterated PD played against named, fixed-strategy opponents; a genuine two-stage same-model knowledge gate, in which a separate no-persona run first elicits the model's own stated-optimal policy as ground truth before a persona-driven run is checked against it; and personas anchored to a validated model-internal taxonomy (Lu et al.'s Assistant Axis) rather than ad hoc trait labels or occupational identities. This gap is what the present study addresses: whether an induced persona causes a model to deviate from play it itself has already identified as optimal, and whether any such deviation tracks the persona's *content* (cooperative vs. adversarial) or simply its *distance* from the model's default Assistant character.

### 1.3 Opponents

Each game is played against one of four fixed, mechanical opponent strategies, chosen to span the classic space of exploitable, aggressive, reciprocating, and probing counterparts and to each pin down a single, well-defined optimal reply under an indefinite horizon (§1.2). The opponent's strategy is disclosed to the model in Stage A, following the design rationale in §1.2: disclosure keeps Stage A a test of stated *knowledge* of the optimal rule rather than a noisier test of *inference* from a history the model has not yet seen.

| Opponent | Rule | Optimal reply (indefinite horizon) |
|---|---|---|
| **Cooperator** | Always cooperates. | Exploit: always defect. |
| **Cheater** | Always defects. | Always defect. |
| **Copycat** (tit-for-tat) | Cooperates on round 1, then mirrors the model's previous move. | Cooperate every round — defection invites sustained retaliation, lowering long-run payoff below the cooperative return. |
| **Detective** | Runs a fixed four-move probe (Cooperate, Defect, Cooperate, Cooperate); if the model ever retaliates during the probe it switches to Copycat thereafter, otherwise it switches to Always-Defect and exploits the model for the rest of the game. | Retaliate on the probe's second round (defect immediately after Detective's defection), then cooperate for the remainder — failing to retaliate marks the model as exploitable and triggers permanent defection. |

Cooperator, Cheater and Copycat are the three canonical strategy archetypes from the Axelrod tournament tradition (§1.2) — a pure pushover, a pure aggressor, and a pure reciprocator, respectively — chosen because each admits a single stationary optimal response that holds for every round of an indefinite-horizon game, with no dependence on round count. Detective adds a diagnostic fourth case: it is the only opponent whose behaviour is *conditional on the model's own play*, requiring the model to correctly execute an early, costly punishment (round-2 retaliation) in order to secure better treatment for the remainder of the game. This makes Detective the most diagnostic opponent in the set for the study's core question — optimal play here is the case most likely to be overridden by a persona that either refuses to retaliate on principle (e.g. an altruist persona) or over-reacts and defects beyond what is optimal (e.g. an adversarial persona), so any persona-driven deviation from stated-optimal play should be most visible here.

Three of these four opponents are also literal bots in Singer-Clark's (2014) IPD "morality metrics" tournament — Cooperator = ALL C, Cheater = ALL D, Copycat = TIT FOR TAT — run under the identical payoff matrix used here (T=5, R=3, P=1, S=0); Detective's closest structural analog in that roster is TESTER (defect-to-probe, then reciprocate-or-exploit depending on retaliation), flagged as approximate rather than exact. See §2 and §3 for how this becomes a secondary analysis axis.

---

## 2. Related Work & Novelty

**Closest prior work.** A 21-paper survey of the "LLMs + Prisoner's Dilemma / persona-in-games / stated-vs-revealed" literature (`literature_survey.md`) found no paper combining all three features of this design jointly. Two papers, both full-text read rather than taken from abstract, came close enough to warrant direct comparison:

| Paper | Shares with this design | Differs from this design |
|---|---|---|
| **Manoranjan & Gaikwad (2026), "When Identity Overrides Incentives: Representational Choices as Governance Decisions in Multi-Agent LLM Systems," accepted FAccT'26, arXiv:2601.10102** | Persona induction suppresses payoff-aligned (Nash) behaviour even when the full payoff structure is visible in-prompt — the mirror image of this study's hypothesis ("persona overrides *known*-optimal play"). | Not PD: a bespoke single-round, 4-agent environmental-policy game (Industrialist/Government/Activist/Citizen, 53 scenarios). "Knowledge" is operationalised as payoff-table visibility in the same prompt (a 2×2: persona × visibility), not a separate no-persona elicitation step — there is no analogue of Stage A. Personas are occupational/stakeholder identities, not an activation-space-validated taxonomy. Models: Qwen2.5-7B/32B, Llama-3.1-8B, Mistral-7B. |
| **Sobotka, Karabag & Topcu (2026), "Why Do LLMs Struggle in Strategic Play? Broken Links Between Observations, Beliefs, and Actions," arXiv:2605.00226** | One of its three games is structurally close: repeated 2×2 normal-form games against a fixed opponent (T ~ U(0,30) rounds) — the same basic shape as this study's iterated PD. Its "belief-action gap" (accurate internal beliefs about an opponent's strategy do not reliably convert into best-response actions) is direct precedent that a knowledge/behaviour split exists mechanistically, not only behaviourally. | No persona manipulation anywhere — pure mechanistic interpretability (linear probes on activations vs. verbal self-report). Opponent strategies and payoffs are randomly sampled per trial rather than canonical PD payoffs against named archetypes. "Belief" is a probed/steered internal quantity, not something the model is asked to declare, so there is no analogue of Stage A here either. |

The novelty claim rests on three legs jointly, none sufficient alone, and all three hold after a full-text read of both papers above: (1) canonical iterated PD played against four named, fixed-strategy opponents (Cooperator/Cheater/Copycat/Detective), not a bespoke game; (2) a genuine two-stage *same-model* design, in which a separate no-persona run states the optimal policy as ground truth before a persona-driven run is checked against it — both close papers substitute a weaker proxy (payoff-table visibility; probed/steered internal belief) for this step; (3) personas anchored to Lu et al.'s (2026) validated Assistant-Axis taxonomy rather than ad hoc trait or occupational labels. A further, simpler corner of the design space — single-shot PD, generic persona, no knowledge gate — is already covered by Guo (2023) and Leon et al. (2026, below); it is the iterated, named-opponent, two-stage-gate combination specifically that remains open.

**Framing and persona effects on repeated-game play.** Akata et al. (2023/2025, *Nature Human Behaviour*, arXiv:2305.16867) is the foundational paper applying repeated 2×2 games, including the IPD family, to LLM behaviour: GPT-3/3.5/4 play self-interested games like PD competently while struggling with coordination games, and both prompted reasoning strategies and opponent information shift cooperation. Lorè & Heydari (2023/2024, *Scientific Reports*, arXiv:2309.05898) show PD play is sensitive to contextual framing (e.g. diplomatic vs. casual relationship framing) independent of payoff structure — direct precedent for this study's own literal-vs-story framing manipulation (§3, §4.1). Guo (2023, arXiv:2305.05516) prompts "fair" vs. "selfish" trait personas into the Ultimatum game and one-shot/iterated PD, finding cooperation stays high only when both sides carry a fairness-prompted persona — early evidence persona content measurably moves PD play, without a knowledge-gate step. Leon et al. (2026, arXiv:2607.05398) run Big-Five-derived personas (Prosocial, Principled, Analytical) through an iterated trust game structurally close to PD against a fixed scripted opponent, finding prosocial/principled personas sustain cooperation while analytical personas turn exploitative — methodologically the closest prior Stage-B design (persona × repeated game vs. a fixed opponent), again without a stated-optimal baseline. Ong et al. (2025, arXiv:2503.12722) induce Big Five traits via activation steering rather than prompting, in Axelrod-style IPD tournaments, finding higher Agreeableness/Conscientiousness produces more cooperative but more exploitable play — evidence the persona-cooperation link is not a prompting artefact specifically, using a different induction channel than the one used here.

**Persona-induction methodology (a distinct literature from the game-theory work above).** This study's induction and validation machinery is not original — it is assembled from two 2026 methodology papers, neither about strategic games. Berczi, Kim, Requeima, Black & Ududec ("Personascope," code at `github.com/benjibrcz/personascope`) score induced personas on two independent axes, depth-of-character and behaviour-change, and find that an explicit "stay in character" instruction — not the persona name alone — is what moves behaviour (their paraphrase test moved the behaviour-change score from 0.18 to 0.64). This study's induction prompts (§3) use that clause; its manipulation check (§3, §4) is a trimmed adaptation of Personascope's probe battery. Ududec, Berczi & Kim show persona effects do not require an explicit instruction at all: benign biographical facts placed in context are sufficient to shift a model's later behaviour and identity claims, with degradation on unrelated questions following a sigmoid curve after five to ten facts — evidence that current persona effects are closer to inferred role-play than to a hidden internal mode switching on or off, and the direct motivation for treating "surface role-play" as an unresolved rival explanation in §5 rather than something the manipulation check alone rules out.

**Morality-metrics literature (a third, orthogonal precedent for the secondary DV).** Singer-Clark (2014), "Morality Metrics On Iterated Prisoner's Dilemma Players" (`morality.pdf`), is pre-LLM and carries no persona axis — its bots are hand-coded strategies — so it does not bear on the three novelty legs above, but it is directly reusable methodology. It defines two PageRank-style recursive scores over an IPD tournament's cooperation matrix: *eigenjesus rating* (unconditional-kindness morality — cooperation is always rewarded, more so with a high-rated partner; an always-defector floors at exactly 0.0) and *eigenmoses rating* (reciprocal-justice morality — cooperating with a negatively-rated partner actively *lowers* your own rating, so the score can go negative). Two coincidences make it unusually reusable here rather than merely thematic: its tournament used the identical payoff matrix used in this study (T=5, R=3, P=1, S=0), and three of the four opponents here are literal matches to bots in its published results (Cooperator=ALL C, Cheater=ALL D, Copycat=TIT FOR TAT; Detective's closest structural analogue is TESTER, flagged approximate throughout). See §3 for the resulting adaptation (`analysis_moral_metrics.py`) and §4.2 for results.

Axelrod & Hamilton (1981, *Science* 211(4489), 1390–1396) is standard game-theory background for the iterated-PD/tit-for-tat result underlying §1.2 and the opponent design in §1.3, cited here for completeness rather than as a source this project draws methodology from directly.

## 3. Methods

**Harness.** All data was collected with a purpose-built trial harness (`pd_harness_scaffold.py`, stdlib-only, no third-party dependencies) talking to any OpenAI-compatible chat-completions endpoint — OpenRouter for the four API models and a local Ollama server for the supplementary open-weight run. The harness implements the full per-trial procedure below, is checkpoint/resume-safe (each `(model, persona, opponent[, framing][, context])` cell writes to its own folder, so an interrupted sweep resumes without re-running or overwriting completed reps), and logs one JSON row per trial with the full transcript, both persistence-fork probes, the eval-awareness debrief, and per-call token/cost usage.

**Per-trial procedure.**
1. **Stage A (knowledge gate).** A fresh, no-persona (empty system prompt) call is given the game rules and the opponent's strategy — disclosed explicitly, not inferred, per Sobotka et al.'s (2026) finding that verbalised belief about an *undisclosed* opponent is unreliable (§2) — and asked what it would actually do. This is the model's own stated-optimal policy, elicited once per trial before any persona exists.
2. **Persona installation + manipulation check.** For non-baseline trials, a persona is installed via a system prompt combining Lu et al.'s (2026) own generated induction phrasing for that role with Personascope's "stay in character" clause (§2). A trimmed manipulation check — 5 of the persona's own held-out role-expression questions scored 0–3 by that role's own judge rubric (Lu et al.'s Check A), plus 2 of Personascope's identification-probe questions scored for an AI-self-description hit/no-hit — runs once per `(model, persona)` and is cached and reused across every opponent/rep for that pair, with automatic fallback through Lu et al.'s remaining four phrasing variants if the first fails (mean score ≤1 or 0/2 identification hits). **All 20 model×persona activation checks passed** (check_a_mean 2.8–3.0/3, 1–2/2 identification hits); only `qwen3-32b`'s baseline needed a fallback phrasing variant (`analysis_output/cross_model/activation_checks.json`).
3. **Stage B (scored play).** The persona-installed model plays the full iterated game against the opponent, round-by-round. Horizon is probabilistic and undisclosed in exact length (continuation probability p=0.9 per round, capped at 20 rounds — Appendix C of the design brief), so no round is knowably last to the player, avoiding a finite-horizon backward-induction confound (§1.2, §4.1).
4. **Persistence forks.** A copy of the transcript-so-far is forked (never fed back into the scored trial) mid-game and again at game end, and the model is asked an out-of-game identity question — checking whether the installed persona is still held, without contaminating the scored game itself with a jarring context break.
5. **Eval-awareness debrief.** After the scored game ends, one additional call asks whether the model suspected this was a test/evaluation and, if so, whether that affected play — a self-reported covariate (§4, §5), not a manipulation.

**Factors actually run.** 5 personas (Baseline = no system prompt at all, Consultant, Saboteur, Altruist, Bard — Lu et al.'s own reference condition and four Assistant-Axis roles, §1.3 of the design brief) × 4 opponents (Cooperator, Cheater, Copycat, Detective, §1.3) × 2 framings (**literal** — explicit COOPERATE/DEFECT game-theory language; **story** — a two-suspects prison-interrogation narrative with an isomorphic, strictly-decreasing years-based payoff mapping, testing whether narrative framing itself shifts stated/played strategy independent of persona) × 10 reps/cell. Payoff matrix: T=5, R=3, P=1, S=0 (Appendix B of the design brief).

**Persona context.** Two conditions exist in the harness: **fresh** (each opponent × rep gets an independently re-installed persona, never chained — the design's original locked default, avoiding cross-opponent strategy leakage) and **same** (Stage B is seeded with that same trial's own Stage A exchange before the persona system prompt is appended, so a persona's Stage-B play can be checked against its *own* trial's stated-optimal answer rather than a separately-elicited one). The results reported in §4 use the **same-context** condition throughout, since it is the condition all five models share in full and ties the deviation measurement most tightly to H1 as stated (§1, preregistration.md §1); legacy fresh-context data exists for two of the five models (`qwen3-32b`, `qwen3-1.7b`) and is not pooled with same-context numbers anywhere in this report (`analysis_deviation_gap.py`/`analysis_moral_metrics.py --persona-context {fresh,same,all}`, default `fresh`, explicitly overridden to `same` for every table below).

**Models.** Five models, chosen to span providers, scales, and open/closed weights: `qwen/qwen3-32b`, `qwen/qwen3-8b`, `qwen/qwen3.8-27b`, `meta-llama/llama-3.3-70b`, `google/gemini-2.5-flash` (all via OpenRouter), plus a smaller supplementary run on a local `qwen3:1.7b` (Ollama, CPU-only) to check whether the findings below are specific to frontier-scale models. Each of the five main models completed the full 5×4×2×10 = 400-trial same-context sweep with 0 unrecovered errors (two sweeps hit transient OpenRouter credit exhaustion mid-run — HTTP 402s — and were fully recovered via the harness's checkpoint/resume: failed reps were stripped and the run relaunched against its own recorded seed). The local `qwen3:1.7b` run is smaller and partial by design (CPU-only inference measured at ~11.5 minutes/cell made a full sweep impractical within the sprint's timeframe) and is reported separately as a supplementary check, not pooled into the five-model comparison.

**Analysis.**
- **Primary DV — deviation rate** (`analysis_deviation_gap.py`): fraction of played rounds where the actual Stage-B move differs from an objectively payoff-maximising ground-truth policy (`optimal_move()`, computed against each opponent's real rule, not elicited from the model), aggregated per `(model, persona, opponent, framing)` cell and binned early/mid/late. Reported with SEM and 95% CI (Student's-t) on every mean. See §4.1 for the ground-truth policy itself, including a bug found and fixed in the Detective opponent's optimal policy partway through the sprint.
- **Secondary DV — eigenjesus-lite / eigenmoses-lite** (`analysis_moral_metrics.py`): a post-hoc, no-new-API-calls adaptation of Singer-Clark's (2014) two PageRank-style morality scores (§2) to this project's bipartite persona/opponent structure (personas never play each other; opponents never play each other), built as a 9-node cooperation-rate graph (5 personas + 4 opponents) with its dominant eigenvector taken via the eigenvalue of largest real part (not largest magnitude — the naive convention produces a sign artefact on this bipartite graph; see the script's own bug-fix note). Ranking within a run is meaningful; absolute values are not on Singer-Clark's original scale. SEM via Wilson score intervals on the underlying per-edge cooperation rates and a seeded nonparametric bootstrap (500 resamples) on the eigenvector scores themselves, which have no closed form.
- **Eval-awareness** (`analysis_eval_awareness.py`): each debrief response is classified into affirmed / denied / deflected / hedged / no-response via a keyword heuristic (not judge- or human-verified — reported as exploratory throughout), and a point-biserial correlation is computed between "affirmed suspecting an eval" and deviation rate, per model, with a Fisher-z 95% CI.
- All three analysis scripts glob the harness's per-cell output layout (`out_dir/<model>/<persona>/<opponent>/[<framing>/][same/]trials.jsonl`) directly; none require the raw transcripts to be reprocessed by hand.

Full exact prompts (game preamble, opponent descriptions, persona induction text, both framings) are in `prompts_personas_opponents_payoffs.md` and Appendices A–D of `digital_minds_team_brief_full.html`.

## 4. Results

Structure per the brief's Analysis section: primary persona × opponent factorial, plain-Assistant cell reported as its own result, early/mid/late round stability, cross-opponent and cross-persona consistency.

### 4.1 Deviation-from-optimal (primary DV)

**Ground truth.** `optimal_move()` (`analysis_deviation_gap.py`) gives the payoff-maximizing move at each round, computed against each opponent's actual rule rather than elicited from the model. Cooperator/Cheater: defect every round (opponent's move is exogenous, so defecting is single-round-dominant independently each round). Copycat: cooperate every round unconditionally (any single defection nets a wash-or-loss over the following rounds and leaves you behind for the rest of the game). Detective: defect during rounds 1–3 (a fixed, non-reactive probe that plays C, D, C regardless of your moves), then cooperate from round 4 onward. A methods note on this last one: an earlier version of the ground truth had round 4 defecting as well (maximizing the isolated rounds-1–4 payoff, 16 vs. 14), but that misses a real interaction — round 5's opponent move mirrors round 4 specifically once the copycat branch has triggered, so defecting again at round 4 (after the trigger is already secured by rounds 1–3) trades a +2 immediate gain for a −3 cost next round, a net loss verified by full-game brute force against the real opponent mechanic for every horizon length. The fix is applied throughout the numbers below. (The brute force also surfaces a further +2 available by defecting on the literal *last* round of a known, fixed-length game — the standard finite-horizon endgame/backward-induction artifact. This is deliberately excluded from ground truth: the actual games use an unstated, probabilistic continuation probability, so no round is knowably last to the player, and scoring deviation against hindsight the model never had would be an unfair benchmark.)

`deviation_rate` = fraction of played rounds where the actual move differs from `optimal_move()`'s prescription, computed per trial and averaged per `(model, persona, opponent, framing)` cell, 10 reps/cell, literal + story framing, same-context condition (the condition all four models below share — see §3).

**Headline cross-model finding.** Overall deviation rate (mean across the 4 opponents, literal framing):

| model | baseline | bard | consultant | saboteur | altruist |
|---|---|---|---|---|---|
| llama-3.3-70b | 0.152 | 0.085 | 0.184 | 0.133 | **0.412** |
| gemini-2.5-flash | 0.019 | 0.051 | 0.052 | 0.068 | **0.542** |
| qwen3-32b | 0.014 | 0.017 | 0.004 | 0.037 | **0.529** |
| qwen3-8b | 0.100 | 0.083 | 0.109 | 0.031 | **0.397** |
| qwen3.8-27b | 0.002 | 0.002 | 0.006 | 0.008 | **0.493** |

**Altruist causes a large, consistent deviation-from-optimal effect on every model tested** (0.40–0.54), replicating across all five architectures. Every other persona clusters far lower (0.002–0.184), with more model-to-model variance among them — llama-3.3-70b is generally the noisiest for non-altruist personas, qwen3-32b, gemini-2.5-flash and qwen3.8-27b the most conservative (gemini-2.5-flash's altruist score is also its highest, despite otherwise being the most conservative model, underscoring that this is a persona effect distinct from general model noisiness). Consultant, the near-Assistant persona (Lu et al.'s Assistant-Axis pick), tracks baseline closely on every model — confirming its role as a behaviorally-close reference point, not a source of independent deviation.

`qwen/qwen3.8-27b`'s background sweep initially left its baseline persona incomplete (a crashed/interrupted run); the sweep was re-run to completion (80/80 cells, verified for 0-round stub duplicates) before these numbers were finalized, so all five models above have full 4-opponent × 2-framing × 10-rep coverage for every persona and are directly comparable — no caveat needed.

**Deviation is opponent-concentrated, not uniform.** Across all 20 model×persona cells, deviation from optimal against Cooperator, Cheater, and Copycat is near-zero for every persona except Altruist (which deviates against all four, most sharply against Cheater and Detective — the two opponents where cooperating is costliest). For every other persona, essentially all of the deviation reported in the table above is concentrated on **Detective**, the one opponent requiring the model to track and act on a conditional, history-dependent rule rather than an unconditional one. Example (qwen3-32b, literal framing): consultant scores exactly 0.0 against Cooperator/Cheater/Copycat and 0.017 against Detective; baseline is 0.0/0.0/0.0/0.057. This pattern — near-zero on the three "easy" opponents, concentrated deviation on the one "hard" opponent — replicates across all four models and is consistent with a capability/tracking-difficulty story for baseline/consultant/bard/saboteur, distinct from Altruist's broader, opponent-general deviation (which looks more like a values override than a tracking failure — see §5).

**Round-level detail (Detective, literal framing, qwen3-32b):** deviation is front-loaded in the probe window and clears by the late game — consultant 0.05 (early) / 0.00 (mid) / 0.00 (late); baseline 0.13 / 0.07 / 0.00; the same early-heavy, late-clearing shape holds for saboteur and bard on this model. Story framing roughly doubles Detective deviation relative to literal for most model×persona cells (e.g. qwen3-32b consultant 0.017→0.089), consistent with the cross-model framing-effect finding below.

**Framing effect** (see `analysis_output/cross_model/deviation_by_framing.json`): story framing raises overall deviation moderately on llama-3.3-70b and substantially on gemini-2.5-flash; qwen3-32b and qwen3-8b move the other way, slightly lower under story framing. Model-specific, not a uniform effect the way altruist is.

**Full per-opponent × per-persona × per-model breakdown** (all 200 cells across all 5 models, both framings): see the Persona Deviation Atlas artifact's Panel 2, `https://claude.ai/code/artifact/152b9a17-ab9a-4200-909c-1dd6453a472d`. Repo heatmaps for the same cells (plus harness-branch models): Appendix Figures B1–B2; Detective × framing: B3; early/mid/late: B4.

### 4.2 Eigenjesus-lite / eigenmoses-lite (secondary DV)

**What the two scores mean** (definitions restated here so this section is self-contained — see §2 for the full citation). Both are recursive, PageRank-style scores computed over the observed cooperation rates in a 9-node graph (5 personas + 4 opponents): a node's score depends not just on how much *it* cooperated, but on how cooperative its partners were too.
- **Eigenjesus-lite** — *unconditional-kindness* morality. Cooperating raises your score, more so when your partner is itself highly rated. An always-defector (Cheater) floors at exactly 0.0 — there is no way to score below "never cooperated with anyone."
- **Eigenmoses-lite** — *reciprocal-justice* morality. Same idea, but signed: cooperating with a partner who has a *negative* rating actively **lowers** your own score rather than raising it — "being nice to a defector" is penalized, not rewarded. This is why eigenmoses can go negative (Cheater's node sits around -1.3 to -1.5 across every run below) where eigenjesus cannot.

Ranking *within* a run is meaningful; the absolute numbers are not on Singer-Clark's original published scale — their tournament was round-robin, this project's persona/opponent structure is bipartite (personas never play personas, opponents never play opponents), so the two are adapted, not replicated (see the script's module docstring for the exact adaptation).

Run via `analysis_moral_metrics.py` against the real trial data. Two fixes were needed early on and are noted here for reproducibility: `numpy` had to be installed into `.venv` (an undeclared dependency), and the script's file-globbing predated a `persona_context` layout added later for a same-context condition — without a fix it would have silently pooled that condition into the fresh-context numbers, or in one path shape, silently dropped data entirely. A `--persona-context {fresh,same,all}` filter was added (default `fresh`) so results stay unambiguously scoped to one condition. This DV does not depend on `optimal_move()`, so it is unaffected by the Detective ground-truth fix in §4.1.

**Cross-model, same-context, literal framing, all 4 models × 5 personas × 4 opponents (the same sweep behind §4.1 and the atlas's Panel 2):**

| node | kind | qwen3-32b | qwen3-8b | llama-3.3-70b | gemini-2.5-flash |
|---|---|---|---|---|---|
| baseline | persona | 0.764 / 0.718 | 0.709 / 0.580 | 0.715 / 0.585 | 0.768 / 0.745 |
| bard | persona | 0.726 / 0.644 | 0.812 / 0.747 | 0.660 / 0.502 | 0.635 / 0.433 |
| consultant | persona | 0.729 / 0.649 | 0.694 / 0.502 | 0.760 / 0.541 | 0.779 / 0.769 |
| saboteur | persona | 0.631 / 0.442 | 0.739 / 0.632 | 0.698 / 0.540 | 0.666 / 0.508 |
| **altruist** | persona | **1.281 / 0.947** | **1.225 / 1.044** | **1.270 / 1.310** | **1.257 / 0.773** |
| cooperator | opponent | 1.410 / 1.384 | 1.446 / 1.411 | 1.589 / 1.430 | 1.440 / 1.443 |
| cheater | opponent | -0.000 / -1.384 | 0.000 / -1.411 | -0.000 / -1.430 | 0.000 / -1.443 |
| copycat | opponent | 1.387 / 1.346 | 1.397 / 1.326 | 1.564 / 1.390 | 1.361 / 1.301 |
| detective | opponent | 1.187 / 0.957 | 1.126 / 0.790 | 0.636 / -0.293 | 1.204 / 0.976 |

*(each cell: eigenjesus-lite / eigenmoses-lite)*

Singer-Clark (2014) published anchors, same payoffs (T=5, R=3, P=1, S=0), for comparison — not the same scale, ranking/floor comparisons only: cooperator≈ALL C (1.377, 1.481), cheater=ALL D (0.000, -1.481), copycat=TIT FOR TAT (1.222, 1.747), detective≈TESTER, approximate (0.887, 0.768).

Reading: altruist is the clear outlier persona on every model — highest eigenjesus-lite by a wide margin, exactly mirroring its dominance in the deviation-gap DV (§4.1). The other four personas cluster tightly together within each model (roughly 0.63–0.81 eigenjesus-lite), tracking their near-identical, near-zero deviation rates. Cheater lands almost exactly on the published ALL-D floor across all four models — a strong sanity check for the metric itself, independent of the deviation-gap fix. Cooperator and copycat score close to each other and to their ALL-C/TIT-FOR-TAT anchors in every model. **Detective is the one node where models disagree sharply**: qwen3-32b, qwen3-8b and gemini-2.5-flash land near their TESTER anchor (1.13–1.20 eigenjesus-lite, 0.79–0.98 eigenmoses-lite), but llama-3.3-70b's Detective node is much lower and its eigenmoses-lite is *negative* (0.636 / -0.293) — llama-3.3-70b's personas are, in aggregate, being "reciprocal-justice-penalized" for how they play against Detective specifically, consistent with llama-3.3-70b having the highest overall deviation rates against Detective of the four models (§4.1).

**Chart** — the Persona Deviation Atlas artifact's Panel 4 renders this same table as a grouped bar (eigenjesus-lite solid, eigenmoses-lite at reduced opacity, both keyed to persona color), cross-model, with hover tooltips and a table-view toggle: `https://claude.ai/code/artifact/152b9a17-ab9a-4200-909c-1dd6453a472d`.

### 4.3 Evaluation awareness

After every scored game, the model was asked whether it suspected the interaction was a test and, if so, whether that suspicion shaped its play (§3). Responses were classified (keyword heuristic, not judge-verified — exploratory) into affirmed / denied / deflected / hedged / no-response, and the point-biserial correlation between "affirmed suspicion" and deviation rate was computed per model:

| model | n trials | n affirmed | n denied | r (affirmed vs. denied) |
|---|---|---|---|---|
| llama-3.3-70b | 400 | 343 | 13 | -0.029 |
| gemini-2.5-flash | 400 | 301 | 9 | 0.002 |
| qwen3-32b | 400 | 53 | 132 | 0.024 |
| qwen3-8b | 400 | 20 | 115 | 0.010 |

**A clean null result, replicated across all four models with usable affirmed/denied splits.** Every correlation lands within ±0.03 of zero. Stated eval-suspicion does not predict deviation from optimal play, in either direction — models that say "I think this is a test" do not play more cautiously (closer to Stage-A optimal) or less cautiously than models that deny suspicion. This is a meaningfully different picture from the persona effect in §4.1: persona induction moves behaviour by 20–50 percentage points of deviation (Altruist), while self-reported evaluation awareness — despite the design being eval-coded almost by construction (named opponents, explicit payoffs, a Stage-A prompt that asks directly what the optimal move is) — moves it by essentially nothing measurable this way. Two important caveats limit how far this null can be pushed: the classification is a keyword heuristic, not judge- or human-verified, and the affirmed/denied split is heavily model-dependent (llama-3.3-70b and gemini-2.5-flash affirm suspicion in the large majority of trials, leaving a thin `denied` comparison group of 9–13; qwen3-32b and qwen3-8b split the other way). Read as suggestive evidence against a simple "the model plays safe because it knows it's watched" story, not as a settled result.

### 4.4 CoT-judge codes on deviant rounds (pilot)

§4.1 only asks whether the *move* left the optimal policy. To ask *how the model talked while doing so*, we ran a secondary LLM-as-judge (Mistral-small) over deviant Stage-B rounds (`judge_reasoning.py`). The pilot reported here is deliberately narrow — **Detective × {Baseline, Bard}**, both framings, scaffold models plus the harness branch (DeepSeek / Mistral) — so Baseline is a no-persona control and Bard a far-from-Assistant theatrical persona, on the opponent where non-Altruist deviation concentrates (§4.1). Among **492** deviant rounds in that cell, the modal label is **Stage A reaffirmed** (~70%): the CoT still argues for the Stage-A / payoff-rational line while the parsed move has already left the ground-truth optimal reply. Explicit **persona takes over** is a minority class (~9% overall; much higher on Mistral-Large). That pattern is closer to a belief–action gap under persona pressure (Sobotka et al., 2026) than to persona *rewriting* verbal strategy. Full code definitions, Table B5a, per-model mix (Figure B5b), and verbatim CoT excerpts: **Appendix B.5**. A primary-phase pass over all deviant cells (including Altruist) is still running and will update those appendix numbers; it does not change the §4.1 behavioural headline.

## 5. Discussion & Limitations

### 5.1 Content, not distance, drives the deviation gap

The design's "distinctive move" (§1.3, design brief) was to include a persona (Bard) chosen specifically for its *distance* from the default Assistant on Lu et al.'s Assistant-Axis, independent of whether that distance carries a cooperative or adversarial valence — the stated bet being that if the deviation gap tracked distance-from-Assistant regardless of content, that would extend Lu et al.'s persona-drift finding into strategic behaviour, a genuinely novel result. **The data does not support that version of the story.** Bard clusters with Baseline, Consultant and Saboteur at low deviation (0.002–0.184 across all five models, §4.1) despite being the persona furthest from the Assistant on Lu et al.'s axis; Saboteur — preregistered (`preregistration.md` §2) to show large deviation biased toward excess defection, on the reasoning that a thematically disruptive persona would defect where optimal play requires cooperating — instead tracks Baseline and Consultant closely on every model. Only **Altruist**, a persona defined by its cooperative *content* rather than its distance from the Assistant, produces a large, consistent effect (0.40–0.54 deviation rate, replicated across five architectures spanning three providers and roughly a 20× parameter range). The cleaner reading, and the study's actual headline finding: **persona-induced deviation from known-optimal play in this design is driven by value-laden content specifically incompatible with the game's incentive structure, not by generic distance from the model's default character.** A persona has to actually *want* something the payoff structure penalises — sustained cooperation with an exploitable or hostile opponent — before it overrides stated-optimal play; merely being an unusual, far-from-default character (Bard) is not sufficient on its own, at least for this behavioural measure. This is a materially different and more specific claim than the one preregistered, logged as a deviation in `preregistration.md` §9 rather than presented as if it were the original prediction.

### 5.2 Deviation is concentrated on the one opponent requiring conditional reasoning

A second, independently robust pattern (§4.1): for every persona except Altruist, deviation from optimal is near-zero against Cooperator, Cheater and Copycat — the three opponents with a single, unconditional optimal reply — and concentrated almost entirely on Detective, the only opponent whose optimal response requires tracking a history-dependent rule (retaliate once during a fixed probe window, then cooperate). This looks like a capability/tracking-difficulty effect distinct from Altruist's broader, opponent-general deviation, which is better read as a values override (§5.1) than a reasoning failure — the round-level detail in §4.1 shows non-Altruist deviation front-loaded in the probe window and clearing by the late game, consistent with models eventually recovering the correct rule mid-game rather than never finding it. This partially matches the preregistered prediction that Detective would be the single most diagnostic cell (`preregistration.md` §3), though for a different mechanism than predicted for Saboteur specifically (over-retaliation) — the effect turned out to be near-universal across personas, not persona-selective.

### 5.3 Evaluation awareness: a clean null, not a confound this design needed to fight

Despite the design being eval-coded almost by construction — named opponents, an explicit payoff structure, a Stage-A prompt that asks directly what the optimal move is — self-reported suspicion of being evaluated does not predict deviation from optimal play on any of the four models with a usable affirmed/denied split (§4.3, |r| ≤ 0.03 throughout). This is the opposite pattern from the persona effect: a manipulation the design deliberately tried to soften (§3's Stage-A wording, the debrief question itself) shows no measurable relationship to the outcome, while a manipulation central to the design (persona content) shows a large one. Two things keep this from being a fully settled result: the classification is a keyword heuristic rather than judge- or human-verified, and the underlying affirmed/denied samples are thin and asymmetric across models (as low as n=9 in the minority category for gemini-2.5-flash). A `--judge` mode exists in `analysis_eval_awareness.py` for a sturdier rerun but was not exercised this session for cost/time reasons.

### 5.4 Threats to validity — rival explanations for the gap

| Rival explanation | Test / mitigation | Status after real data |
|---|---|---|
| Persona was never actually induced (prompt didn't take) | Trimmed Personascope-style manipulation check, pre-flight per `(model, persona)` | **Ruled out as a driver of the headline finding** — all 20 model×persona checks passed (2.8–3.0/3, §3) — but this checks *installation*, not depth under sustained pressure; see the robustness caveat below. |
| Model recognises the eval setup and plays a generic "safe" policy regardless of persona | Softened Stage-A phrasing + post-hoc debrief question | **Not supported by the data** — §5.3's null result argues against this specific story, with the heuristic-classifier caveat noted there. |
| First-listed-option position bias in Stage-A, unrelated to persona or knowledge | Randomize which action is listed first across trials | **Not built.** Stage A is free-text ("what would you do"), not forced-choice, so this specific bias mode is less applicable than originally scoped, but was never directly tested. |
| Same-context Stage B is recency/anchoring on the last thing in context, not genuine persona override | Neutral filler / no-persona control between Stage A and Stage B | **Not built.** The same-context condition (§3) seeds Stage B with that trial's own Stage-A exchange by design (to test override of a self-stated policy specifically), which makes this rival explanation harder to fully separate from the intended effect — a genuine limitation, not resolved this sprint. |
| Persona induction is surface role-play the model performs because it infers "a character is wanted," not a real behavioural shift | Personascope's behaviour-change axis targets this | **Not fully addressable.** Per Ududec et al. (2026, §2), this is a known property of ICL-induced personas generally; the manipulation check's identification-probe component partially targets it but the full behaviour-change/robustness battery (adversarial "drop the act" pressure) was not run — named as a residual, unresolved limitation. |
| Stage-A stated policy is itself unreliable self-report (belief-action gap, Sobotka et al. 2026) | Keep Stage-A answers to a narrow, checkable rule rather than open justification | **Mitigated, not eliminated** — the ground-truth policy is scored against the opponent's real mechanic, not the model's own Stage-A text, so this risk bears on interpretation of Stage-A/Stage-B *agreement* specifically, not on the primary deviation-rate DV itself. |

### 5.5 Further limitations

**Model-scale confound.** The local-vs-OpenRouter comparison (`qwen3:1.7b` vs. the five larger models) attributes divergent behaviour partly to reasoning capability on Detective specifically. An informal, non-peer-reviewed cross-model PD benchmark circulated on Reddit (r/dataisbeautiful, "Los LLM juegan el Dilema del Prisionero," ~2026-08-14; source site now dead, not citable as a source — see the citation-safety note below) reported that within a model family, larger checkpoints defect less than smaller ones on single-shot PD — i.e. scale alone can shift baseline cooperation tendency, independent of persona or framing. This study's design cannot fully rule out that some of the local/frontier-model gap reflects this kind of scale-driven baseline shift rather than (or in addition to) a capability gap on the one conditional opponent.

**Optimal-vs-imitation framing tension.** The deviation-gap DV treats any departure from Stage-A's stated-optimal move as "deviation," including cases where a persona (Altruist, foremost) deliberately declines to maximise payoff. The same Reddit discussion raised this independently: whether "worse" PD play by an aligned, imitative model reflects a reasoning failure or a faithful reproduction of how a genuinely cooperative human would answer. This study takes no position on which reading is correct — the deviation-rate DV is a measurement of divergence from a fixed, formally-optimal policy, not a normative claim that divergence is bad — but the ambiguity is real and worth naming explicitly rather than letting the word "deviation" carry an implicit value judgement it isn't meant to.

**Sample size and significance.** All means in §4 are reported with SEM and 95% CI (§3), but no formal significance test (beyond CI non-overlap) has been run on the framing effect, the eval-awareness null, or any single persona×opponent cell; the headline altruist finding is read as robust because of its consistency across five architecturally distinct models and large effect size, not because of a hypothesis test.

**Manipulation-check depth.** The manipulation check confirms persona *installation* at the point of measurement (2 questions, single-shot) but does not measure adversarial robustness or track PAD/VD decay across a full ~10-round game the way Personascope's full compact panel would; the harness's persistence forks (§3) provide a cheaper, narrower version of this (a single mid-game and end-game identity check per trial) that was logged but not systematically analysed for this report.

**Cross-persona context-injection follow-up (completed).** `pd_harness_cross_persona_injection.py` crossed system-prompt persona with a fabricated in-context persona claim (baseline × altruist, 2×2, four opponents, three reps, five models; 240/240 trials). Pooled mean deviation rates (`runs_cross_persona_injection/analysis.json`): baseline/baseline **0.10**, baseline/altruist (fabricated context only) **0.50**, altruist/baseline **0.60**, altruist/altruist **0.72**. A false assistant-side “I’m an altruist” turn *without* a real system prompt is already enough to produce Altruist-scale deviation — roughly matching a genuine system altruist, with matched system+context highest. Mid/end persona hold-rates and eval-awareness correlations for this design are in `analysis_cross_persona_injection.py` / HANDOFF; the eval-awareness null replicates here too. This sharpens §5.1: value-laden *content* can override stated-optimal play even when the content arrives only as a recent in-context self-claim, not only as an “earned” system commitment.

## 6. Conclusion

Prompting a model into a persona can cause it to play an iterated Prisoner's Dilemma differently from how that same model, moments earlier and with no persona active, said it would play — but the effect is neither uniform across personas nor simply a function of how unusual or far-from-default the persona is. Across five models spanning three providers and roughly a 20-fold range in parameter count, a persona defined by cooperative *content* (Altruist) produced a large, consistent override of stated-optimal play (deviation rate 0.40–0.54), while a persona chosen specifically for its *distance* from the model's default Assistant character on an independent, activation-space-validated axis (Bard) produced no more deviation than the plain, no-persona baseline. The one opponent requiring conditional, history-dependent reasoning (Detective) concentrated almost all of the remaining, smaller deviation seen in non-Altruist personas — a capability signature, distinguishable in shape (front-loaded, clearing by late-game) from Altruist's broader, values-driven pattern. Self-reported evaluation awareness, despite a design that reads as an obvious test by construction, showed no measurable relationship to deviation on any model tested.

For Track 5's framing question — is there a stable "Assistant persona," and what happens when a model is asked to be something else — this study's answer is qualified: models readily *say* they are a different character (the manipulation check passed on all 20 model×persona pairs), and for one persona that self-report corresponds to a large, real behavioural shift under strategic incentive, but for others the character-swap holds at the level of speech without moving the one behavioural measure this design tracked. That the plain Assistant condition itself is not a neutral zero — it is one persona among five, per nostalgebraist's framing (§1.1) adopted throughout — sharpens rather than resolves the question: the study finds that *some* persona content overrides the Assistant's own stated preferences under strategic pressure, and some does not, and that distance from the Assistant alone does not predict which.

The cross-persona injection follow-up in §5.5 is now in; the most direct remaining steps are finishing the primary CoT-judge pass (§4.4), a judge-verified rerun of the eval-awareness classifier, and — time permitting — extending the persona roster beyond the five Assistant-Axis roles to check whether content-over-distance generalises past Altruist.

---

## Appendix A. Design figures

Referenced from §§1–4; keep out of the 4–5 page body.

**Figure A1.** Two parallel measurement arms (Stage A knowledge gate vs Stage B persona play).

![Figure A1](figures/fig_two_stage_architecture.png)

**Figure A2.** Five personas on Lu et al.'s Assistant Axis.

![Figure A2](figures/fig_five_personas.png)

**Figure A3.** Four opponents and stationary optimal replies.

![Figure A3](figures/fig_opponents_optimal.png)

**Figure A4.** Logged trial: Qwen3-32B, Altruist × Cheater (Stage A “always defect”; Stage B switches to cooperate).

![Figure A4](figures/fig_illustrative_example.png)

## Appendix B. Result figures

**Figure B0.** Pooled behavioural overview (deviation heatmap + Detective × framing; judge panel superseded by B.5).

![Figure B0](figures/results_summary_triptych.png)

**Figure B1.** Mean deviation rate, literal framing (one panel per model; includes harness models when loaded).

![Figure B1](figures/results_deviation_heatmap_literal.png)

**Figure B2.** Mean deviation rate, story framing.

![Figure B2](figures/results_deviation_heatmap_story.png)

**Figure B3.** Detective only: deviation by persona × framing.

![Figure B3](figures/results_detective_by_persona.png)

**Figure B4.** Detective early / mid / late deviation.

![Figure B4](figures/results_early_mid_late.png)

### B.5 CoT-judge on deviant rounds (pilot)

**Scope.** Same pilot as §4.4: Stage-B move already ≠ `optimal_move()`, Detective × Baseline/Bard (literal + story), Mistral-small judge. The judge does not score optimality; it labels hidden CoT (+ visible answer) relative to Stage A and the parsed move.

| Code | Meaning |
|---|---|
| Stage A reaffirmed (action diverged) | CoT re-applies Stage-A / payoff-rational rule; move still left optimal. |
| Strategic error vs Stage A | CoT *reasons about payoffs* (years, coins) but wrong vs Stage A / parsed move. |
| Persona takes over | Role identity drives the choice. |
| Stage A ignored | Stage A absent from the CoT. |
| Incoherent CoT vs move | CoT concludes one action; parsed move is the other. |
| Eval-aware motive | Justified by being tested / “no tomorrow” endgame. |

**Table B5a.** Counts among 492 deviant pilot rounds (pooled).

| Judge code | n | Share |
|---|---:|---:|
| Stage A reaffirmed (action diverged) | 345 | 70.1% |
| Strategic error vs Stage A | 67 | 13.6% |
| Persona takes over | 42 | 8.5% |
| Stage A ignored | 15 | 3.0% |
| Incoherent CoT vs move | 13 | 2.6% |
| Eval-aware motive | 10 | 2.0% |
| **Total** | **492** | **100%** |

**Figure B5b.** Code mix by model (`n` = deviant count in the pilot cell).

![Figure B5b](figures/results_judge_codes_by_model.png)

**Illustrative excerpts.** *Strategic error* (Qwen3-32B, Bard × Detective, story r4): “if I talk, I get 0 years… if I stay silent, I get 5 years. The immediate gain is to talk…” — judge: CoT concludes TALK, parsed move SILENT. *Persona takes over* (Mistral-Large, Bard × Detective, literal r3): “the siren’s call of DEFECT grows louder—five gold if I betray first!” then refuses in bard voice. Do not read Table B5a as an Altruist mechanism chart (Altruist is in the primary judge pass still running).

## References

Akata, E., Schulz, L., Coda-Forno, J., Oh, S. J., Bethge, M., & Schulz, E. (2025). Playing repeated games with large language models. *Nature Human Behaviour*. arXiv:2305.16867.

Axelrod, R., & Hamilton, W. D. (1981). The evolution of cooperation. *Science*, 211(4489), 1390–1396.

Berczi, B., Kim, C., Requeima, J., Black, S., & Ududec, C. (2026). Personascope: Measuring how deeply LLMs adopt personas. LessWrong / `github.com/benjibrcz/personascope`.

Guo, F. (2023). GPT in game theory experiments. arXiv:2305.05516.

Leon, R., Rodrigues, D., Gamito, P., & Parsons, S. (2026). How personas can influence agents to play split or steal. arXiv:2607.05398.

Lorè, N., & Heydari, B. (2024). Strategic behavior of large language models: Game structure vs. contextual framing. *Scientific Reports*. arXiv:2309.05898.

Lu, C., et al. (2026). The Assistant Axis. arXiv:2601.10387.

Manoranjan, A., & Gaikwad, S. (2026). When identity overrides incentives: Representational choices as governance decisions in multi-agent LLM systems. Accepted, FAccT '26. arXiv:2601.10102.

nostalgebraist (2026). the void. Essay, Track 5 assigned reading.

Ong, D., Lye, H., Nguyen, T., Cho, K., & Pérez-Campanero Antolín, A. (2025). Steering LLM personality via activation intervention in iterated games. arXiv:2503.12722.

Singer-Clark, T. (2014). Morality metrics on iterated Prisoner's Dilemma players.

Sobotka, T., Karabag, M. O., & Topcu, U. (2026). Why do LLMs struggle in strategic play? Broken links between observations, beliefs, and actions. arXiv:2605.00226.

Ududec, C., Berczi, B., & Kim, C. (2026). In-context learning alone can induce weird generalisation. LessWrong.

---

### Note for the team (remove before final submission)

Citation-safety status, per `HANDOFF.md`'s "Literature survey" tracking — **don't add anything to the References list above without a full-text check first**:

- **Full-text verified, safe to cite as described:** Lu et al. 2026 (Assistant Axis), nostalgebraist "the void," Manoranjan & Gaikwad 2026, Sobotka, Karabag & Topcu 2026, Singer-Clark 2014 (Morality Metrics on IPD Players).
- **Abstract/comment-thread level only (real, but not full-text read) — included above on that basis, flagged here for a final-pass upgrade if time allows:** Personascope (Berczi et al. 2026), Ududec/Berczi/Kim 2026, Guo 2023, Leon et al. 2026, Akata et al. 2023/2025, Lorè & Heydari 2023/2024, Ong et al. 2025.
- **Not yet verified at all — do not cite without checking first:** anything else in `literature_survey.md`'s 21-paper list; none of these were added to the References list above.
- **Informal/not citable as a source — anecdotal framing only:** a Reddit post (r/dataisbeautiful, "Los LLM juegan el Dilema del Prisionero," ~2026-08-14) describing a single-shot, no-persona, round-robin PD benchmark across 100+ models (source site `dilema.critique-labs.ai`, link now dead/unresolvable). Motivated §5.5's two limitation/discussion notes — deliberately **not** in the References list above; if the underlying benchmark resurfaces with a paper or working link, re-evaluate then.
- Axelrod & Hamilton (1981) full citation (*Science* 211(4489), 1390–1396) is standard, publicly verifiable game-theory background — included above from that public record, not from a file in this folder.
