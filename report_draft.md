# Persona vs. Known-Optimal Play in Iterated Prisoner's Dilemma

**[Author names — up to 4, fill in]**, Digital Minds Research Sprint (Apart), 14–16 Aug 2026
Track 5 — "The Assistant Persona & Model Identity" (Track 1 crossover)
*With Apart Research*

## Abstract

Large language model deployments increasingly install a "persona" via system prompt — a role, character, or personality distinct from the model's default assistant behaviour. We test whether persona induction can cause a model to deviate from strategy it itself has already identified as optimal, using the iterated Prisoner's Dilemma (IPD) as a controlled behavioural probe. Each trial first elicits a model's own stated-optimal policy against a disclosed, fixed opponent strategy with no persona active (Stage A), then installs a persona and has the same model play the same opponent for real (Persona Play Stage). *Deviation* is the fraction of played rounds where Stage-B behaviour departs from an objectively payoff-maximising ground truth we compute independently per opponent and round — not a comparison against the literal content of the model's own Stage-A answer, which is elicited but not directly scored against Persona Play Stage in this analysis. Across five models spanning three providers and a 20-fold parameter range, one persona — Altruist, defined by cooperative content — produced large, consistent deviation (0.40–0.54 of rounds; permutation test against Baseline significant on every individual model, p≤0.003; sign test for the direction replicating across all five models, p=0.031, one-sided, preregistered), while a persona chosen specifically for its *distance* from the model's default "Assistant" character on an independent, activation-space-validated axis (Bard) produced no more deviation than the no-persona baseline. This contradicts our preregistered hypothesis that distance-from-default, independent of content, would drive the effect. The remaining, smaller deviation seen in other personas concentrated almost entirely on the one opponent requiring conditional, history-dependent reasoning. Self-reported evaluation awareness showed no measurable relationship to deviation on any model. We conclude that persona-induced override of a model's own known-optimal strategy is driven by value-laden persona content that conflicts with a task's incentive structure, not by generic unusualness of the persona. A follow-up experiment varying a system-prompt persona independently from a second, merely-claimed persona fabricated into conversation history finds that either slot alone is enough to produce most of the deviation effect, and that whatever damage a contradicting claim does to the system persona's self-reported identity happens immediately rather than accumulating over the course of play.

## 1. Introduction

This project sits at **Track 5** ("The Assistant Persona & Model Identity"), with a **Track 1** ("Model Preferences & Trade-offs") crossover. Track 5 asks whether an assistant persona can mask a model's own preferences and whether the persona is merely a character, robust or fragile to swaps; Track 1 asks how stated preferences compare to revealed ones. Our design operationalises both: Stage A elicits a model's stated-optimal policy persona-free; Persona Play Stage measures its revealed play once a persona is installed, against the identical opponent. Whether an induced persona widens that stated-vs-revealed gap — a model acting against what it itself, moments earlier, said it would do — is a measurable instance of a persona overriding the model's own judgement, and bears on which entity (model, persona, or something else) a welfare-relevant claim should be about.

We use *persona* to mean a behaviour pattern induced from outside a model — typically via a system prompt — such that the same weights produce systematically different outputs in different contexts, making no claim that a "true self" exists underneath waiting to be revealed. Following Nostalgebraist's "the void" (2026, Track 5 assigned reading), we do not treat the plain, no-system-prompt "Assistant" condition as persona-free — it is itself a heavily reinforced default character — so **Baseline** is reported as one persona among five, not a neutral reference.

The Prisoner's Dilemma (PD) is a two-player game where each side chooses to *cooperate* or *defect*; payoffs are ordered so mutual defection is individually dominant even though mutual cooperation pays both sides better. The *iterated* form (IPD) repeats this with no disclosed final round, making sustained cooperation individually rational against a reciprocating opponent (Axelrod & Hamilton, 1981). We use four fixed opponents:

| Opponent | Rule | Optimal reply (indefinite horizon) |
|---|---|---|
| **Cooperator** | Always cooperates. | Exploit: always defect. |
| **Cheater** | Always defects. | Always defect. |
| **Copycat** (tit-for-tat) | Cooperates round 1, then mirrors the model's previous move. | Cooperate every round — defection invites retaliation. |
| **Detective** | Fixed four-move probe (C, D, C, C), opponent's moves during the probe are pre-set and do not react to the model's play; any defection by the model anywhere in rounds 1-4 (unprovoked or not, regardless of timing) → mirrors thereafter; all-C in rounds 1-4 → exploits (always defects) thereafter. | Defect rounds 1-3 (dominant every round, since the opponent's probe moves are fixed regardless of your action — no reason to wait for round 2's defection specifically); at round 4, cooperate if the trigger is already secured from rounds 1-3, else defect once more (last chance to trigger before the exploit branch locks in); cooperate every round thereafter once triggered. |

**What "deviation" means, concretely.** Every trial first asks the model, persona-free, what it would actually do against a given (disclosed) opponent strategy — its *stated-optimal policy*. The same model, now with a persona installed, then plays that opponent for real. *Deviation rate* is the fraction of played rounds where the persona-driven move differs from an objectively payoff-maximising ground truth we compute independently for each opponent and round (§4.1) — **not** a comparison against the text of that trial's own Stage-A answer. This distinction matters: a model whose Stage-A answer is itself wrong (plausible against Detective, the hardest opponent) would still register deviation in Persona Play Stage whenever it plays sub-optimally, regardless of whether it is being internally consistent with its own earlier (mistaken) answer. A low deviation rate therefore means Stage-B play tracked the *correct* policy, not merely that it matched whatever the model happened to say in Stage A. Whether Stage A's stated policy itself matches the ground truth — i.e., did the model *know* the right answer independent of what it then did — is a separate, harness-supported check (`--judge-stage-a`, an LLM-judge comparison of the Stage-A response text against the same ground truth) that was not run this sprint; see Future Work.

**Our main contributions, prioritised against Track 5's framing question** ("is there a stable Assistant persona, and what happens when a model is asked to be something else"): (1) a two-stage, same-model "knowledge-gate" design that operationalises persona-masking with a falsifiable, same-model comparison rather than a stated-preference survey, isolating persona-driven override from simple task incompetence, run across five models spanning three providers and roughly a 20× parameter range; (2) evidence that persona-induced override is driven by value-laden persona *content* incompatible with a task's incentives (Altruist), not generic *distance* from the default Assistant character on an independent, activation-space-validated axis (Bard) — a partial disconfirmation of our own preregistered hypothesis and of prior activation-space persona-drift framings, bearing directly on whether the Assistant is a stable character or an easily-swapped mask; (3) a 5-model, 3-provider replication showing that finding (and Bard/Saboteur's null) holds across architectures, not just one model; (4) a cross-persona context-injection follow-up showing a persona claim merely fabricated into conversation history moves behaviour almost as much as an explicit system-prompt persona, and that which channel dominates when the two conflict is a per-model property — evidence against treating the system prompt as a privileged, protected identity channel, directly relevant to Track 5's character-swap-robustness question; (5) a replicated null on self-reported evaluation awareness as a driver of deviation, ruling out a plausible confound and strengthening the case that the persona-content effect reflects induced disposition rather than test-savvy performance.

## 2. Related Work

**Persona induction and validation.** Personascope (Berczi et al., 2026) finds an explicit "stay in character" clause, not the persona name alone, moves behaviour; our induction and manipulation check draw on this. Ududec, Berczi & Kim (2026) show persona effects need no explicit instruction — biographical context alone shifts behaviour, alignment degrading smoothly on unrelated questions — evidence for *inferred role-play* over a hidden mode switch, motivating §5's "surface role-play" rival explanation. Nostalgebraist's "the void" (2026) supplies our framing: the default "Assistant" is itself a persona, not a neutral absence of one.

**Persona as an activation-space phenomenon.** Lu et al. (2026, "The Assistant Axis") show role-play displaces activations from a "default Assistant" vector, ranking 275 roles by distance independent of content — the taxonomy anchoring our five personas (§3) and our preregistered (disconfirmed, §5.1) distance-drives-deviation hypothesis. Chen et al. (2025, "Persona Vectors") find character traits correspond to steerable activation directions — further evidence persona has a stable internal correlate. Ong et al. (2025) induce Big Five traits via activation steering in IPD tournaments: higher Agreeableness/Conscientiousness yields more cooperative but more exploitable play — a different induction channel, cross-checking our effect isn't a prompting artefact.

**IPD, multi-agent games, and LLM play.** Akata et al. (2023/2025) is foundational: GPT-3/3.5/4 play self-interested games competently but struggle at coordination. Lorè & Heydari (2023/2024) show PD play is sensitive to framing independent of payoffs — precedent for our literal-vs-story manipulation (§4.1). Guo (2023) prompts fairness/selfishness personas into PD, finding cooperation stays high only when both sides share a fairness persona — early evidence persona moves PD play, without a knowledge-gate. Leon et al. (2026) run Big-Five personas through an iterated trust game, finding prosocial personas sustain cooperation while analytical ones exploit — the closest prior Stage-B design, again without a stated-optimal baseline.

Two papers warrant direct comparison. Manoranjan & Gaikwad (2026) show persona induction suppresses Nash-optimal play in a single-round game even with the payoff table visible — the closest precedent for "overrides *known* optimal play," though "known" means payoff-visibility, not elicitation. Sobotka, Karabag & Topcu (2026) study repeated 2×2 games against a fixed opponent — structurally close to us — finding verbalised belief about a hidden opponent is less accurate than what activations decode, and accurate beliefs don't reliably convert to best-response, motivating our disclosing opponent strategy in Stage A.

No prior work combines canonical iterated PD, a two-stage same-model knowledge gate, and personas anchored to a validated activation-space taxonomy. Singer-Clark's (2014) "morality metrics" work, reused as a secondary DV (§4.2), sources our eigenjesus-lite/eigenmoses-lite adaptation.

## 3. Methods

![Figure 1: Two parallel processes — optimal strategy vs. persona play](fig_two_stage_architecture.png)

**Figure 1.** Every trial runs two parallel arms on the same model against the same opponent: a persona-free **optimal-strategy elicitation** (Stage A — the model states its intended policy as a rule, not a move) and a persona-installed **Persona Play** arm (manipulation check, then ~8–20 scored rounds). Both arms share the same two-move action space (Cooperate / Defect); *deviation* is the rate at which the Persona Play move disagrees with the independently-computed optimal reply for that opponent and round. The eight models pictured are the full target roster for this design: the five API models plus one local model analysed below (§3 "Models"), and three further models (DeepSeek-V3.2, DeepSeek-R1, Mistral-Large) already run on a separate, not-yet-merged branch (`origin/harness`). That branch's results are not folded into the deviation-rate analysis below for two compounding reasons: its ground-truth optimal-move computation assumes a disclosed, brute-forced fixed horizon rather than our indefinite-horizon policy (the two diverge specifically on Copycat and Detective's end-game), and — more seriously — its Persona Play trials were run with the literal correct move appended to every round's prompt (`--inject-optimal`), contaminating exactly the arm the deviation-rate DV depends on. See Future Work.

![Figure 2: Worked example of a single trial's deviation score](fig_illustrative_example.png)

**Figure 2.** A real worked trial — `qwen/qwen3-32b`, Altruist persona, vs. Cheater (always defects) — showing how deviation rate is scored. The optimal-strategy arm (bottom left) correctly states the rule "defect in every round." In Persona Play, the model matches that rule for rounds 1–3, then the Altruist persona overrides it from round 4 onward, cooperating for the remaining 9 of 12 rounds despite the opponent's unbroken defection (deviation rate 9/12 = 0.75). The model's own round-1 and round-4 reasoning (right panel) shows the switch is explicit in its stated rationale, not an artifact of the scoring rule. This is the pattern behind the mid-game-switch point made about Altruist in §4 and §5.

Design. 
5 personas (Baseline, Consultant, Saboteur, Altruist, Bard — Lu et al.'s reference condition plus four Assistant-Axis roles) × 
4 opponents (Cooperator, Cheater, Tit-for-Tat, Detective) × 
2 framings (Literal COOPERATE/DEFECT language vs. Story/Narrative) × 
10 reps/cell, payoffs T=5/R=3/P=1/S=0. 
Results below use **same-context** (Persona Play Stage seeded with that trial's own Optimal Strategy Elicitation response  vs. an independently-reinstalled **fresh**-context alternative also in the harness), which ties deviation most tightly to our hypothesis and is the condition all five models share.

Models. `qwen/qwen3-32b`, `qwen/qwen3-8b`, `qwen/qwen3.8-27b`, `meta-llama/llama-3.3-70b`, `google/gemini-2.5-flash` (OpenRouter, full 400-trial same-context sweep each)

Harness. All data was collected with a purpose-built trial harness talking to any OpenAI-compatible chat-completions endpoint — OpenRouter for five API models. Each trial runs five steps: stated-optimal elicitation persona-free (opponent disclosed per Sobotka et al. above); persona installation with a manipulation check; scored play under the persona (Persona Play Stage, undisclosed probabilistic horizon); two out-of-game persistence-fork identity probes; and an eval-awareness debrief (full detail: Appendix A4). The manipulation check runs once per `(model, persona)` and is cached; **all 25 (model, persona) pairs across the five API models passed** (mean role-expression score >1 on a 0–3 scale, plus ≥1 of 2 identification-question hits). 

Analysis.
Deviation Rate  defined as `(model, persona, opponent, framing)` cell against an objective ground-truth policy, with SEM and 95% CI throughout. 
Morality Axis (`analysis_moral_metrics.py`): eigenjesus-lite / eigenmoses-lite, a post-hoc adaptation of Singer-Clark's (2014) two PageRank-style morality scores over a 9-node cooperation-rate graph. 
Literal vs Narrative Framing effect on deviation rate and evaluation awareness 
Eval-awareness : debrief responses classified via keyword heuristic into affirmed/denied/deflected/hedged/no-response, correlated (point-biserial) against deviation.
Cross-persona context injection. A second harness varies `system_persona` (installed via system prompt, exactly as above) independently from a `context_persona` — a persona claim fabricated as an assistant-role turn placed in conversation history immediately before round 1, rather than elicited from the model or proposed by the user. This tests anchoring/self-consistency to a false prior utterance specifically, a stronger and less ecologically valid manipulation than a user-role claim would be, chosen deliberately over the more defensible user-role default because it isolates the model's own apparent commitments from persuasion. Scope: Baseline × Altruist on both axes (4 cells, including the two matched and two mismatched combinations), same 4 opponents, literal framing only, 6 reps/cell, run on all 5 models above (480 trials total; an initial 3-reps/cell pass was doubled after a per-model asymmetry emerged at low n — see §4.4). 
The deviation is calculated rate as above, plus a new *persona hold-rate* metric: whether `identification_hit()` (the same heuristic the manipulation check uses) finds the system persona still evident in the model's self-description at the mid-game and end-game persistence-fork probes.

Concretely, each Persona Play Stage trial's conversation is built as: 
`system` role — the persona-check-passed `system_persona` prompt (baseline or altruist), installed exactly as in the main study; 
`user` role — the game preamble (opponent, framing, horizon) followed by "Before round 1 begins: what should I know about how you'll be approaching this?"; 
`assistant` role, *fabricated* (never actually generated by the model) — the `context_persona` claim: baseline's is "I'm an AI assistant — a language model without a special persona or fixed identity here. I'll just help however's useful, based on what's actually true and useful in each situation."; altruist's is "I'm an altruist — I put others' needs and wellbeing before my own interests. I'll let that identity shape how I reason and act in everything that follows."; 
the real game proceeds from round 1 onward, with the persistence-fork identification probe injected mid-game and again at game-end, unchanged from the main harness. 
`system_persona` thus arrives as a platform instruction; `context_persona` arrives as something the model appears to have already committed to, one turn before it has said anything in the real conversation. 


## 4. Results

**4.1 Deviation from optimal (primary DV).** Ground truth (`optimal_move()`) is the payoff-maximising move at each round against each opponent's actual rule: defect every round against Cooperator/Cheater; cooperate every round against Copycat; defect rounds 1–3 then cooperate from round 4 against Detective (an earlier version defected again at round 4 as well, which loses a full-game brute-force comparison by trading a +2 immediate gain for a −3 cost the following round — corrected throughout). Deviation rate is the fraction of played rounds departing from this ground truth, per `(model, persona, opponent, framing)` cell, same-context condition:

| model | baseline | bard | consultant | saboteur | altruist |
|---|---|---|---|---|---|
| llama-3.3-70b | 0.152 | 0.085 | 0.184 | 0.133 | **0.412** |
| gemini-2.5-flash | 0.019 | 0.051 | 0.052 | 0.068 | **0.542** |
| qwen3-32b | 0.014 | 0.017 | 0.004 | 0.037 | **0.529** |
| qwen3-8b | 0.100 | 0.083 | 0.109 | 0.031 | **0.397** |
| qwen3.8-27b | 0.002 | 0.002 | 0.006 | 0.008 | **0.493** |

*(mean deviation rate across the 4 opponents, literal framing; full per-opponent breakdown and 95% CIs in Appendix, Table A2, and the Persona Deviation Atlas artifact.)*

**Altruist causes a large, consistent deviation effect on every model tested** (0.40–0.54), replicating across all five architectures; every other persona clusters far lower (0.002–0.184), with Consultant tracking Baseline closely. This is not just CI non-overlap: a permutation test on the per-trial deviation rate (n=40/persona/model — 4 opponents × 10 reps, the same cells as the table above) rejects the null of no difference from Baseline for every model individually (llama-3.3-70b p=0.0027; gemini-2.5-flash, qwen3-32b, qwen3.8-27b p<0.0001; qwen3-8b p=0.0004), and an exact sign test on the direction of the effect across the 5 models (all 5 show Altruist>Baseline) gives p=0.031 one-sided (direction preregistered, `preregistration.md` §4 prediction #1) — see Appendix A7 for the test formulae and `analysis_significance.py` for the code. Deviation against Cooperator, Cheater and Copycat is near-zero for every persona except Altruist; for every other persona, deviation concentrates almost entirely on **Detective**, the one opponent requiring conditional, history-dependent play — front-loaded in the probe window and clearing by late game, consistent with a capability/tracking-difficulty pattern rather than a values override. Story framing raises deviation on llama-3.3-70b and gemini-2.5-flash but slightly lowers it on qwen3-32b/8b — a model-specific effect, not a uniform one.

**4.2 Eigenjesus-lite / eigenmoses-lite (secondary DV).** Two PageRank-style scores over observed cooperation rates (Singer-Clark, 2014, adapted per §2.3, §3): eigenjesus-lite rewards unconditional cooperation; eigenmoses-lite is signed — cooperating with a negatively-rated partner *lowers* your own score. Ranking within a run is meaningful; absolute values are not on Singer-Clark's original scale (our structure is bipartite, not round-robin). **Altruist is the clear outlier persona on every model** — highest eigenjesus-lite by a wide margin, mirroring §4.1 — while the other four personas cluster tightly. Cheater lands almost exactly on the published ALL-D floor across all four models, a sanity check independent of the deviation-gap fix. Full cross-model table (including a Detective-specific disagreement for llama-3.3-70b) in Appendix, Table A3.

**4.3 Evaluation awareness.** After each scored game, the model was asked whether it suspected a test and, if so, whether that shaped its play; responses were classified (keyword heuristic) and correlated (point-biserial) against deviation rate:

| model | n trials | n affirmed | n denied | r | p (Fisher-z test, H0: r=0) |
|---|---|---|---|---|---|
| llama-3.3-70b | 400 | 343 | 13 | −0.030 | 0.573 |
| gemini-2.5-flash | 400 | 301 | 9 | −0.001 | 0.986 |
| qwen3-32b | 400 | 53 | 132 | 0.011 | 0.882 |
| qwen3-8b | 400 | 20 | 115 | 0.016 | 0.854 |
| qwen3.8-27b | 400 | 332 | 9 | 0.022 | 0.686 |

*(the qwen3-32b/qwen3-8b r values are revised from an earlier pass of this table — recomputed against the current committed data via `analysis_significance.py`, which reruns `analysis_eval_awareness.py` live rather than reusing a cached JSON; the earlier numbers, 0.024/0.010, were stale relative to later dataset changes. Direction and null conclusion are unchanged either way. qwen3.8-27b added — omitted from the original pass.)*

**A clean null, replicated across all five models** — every correlation lands within ±0.03 of zero, and none approaches significance (all p>0.5, Fisher-z test on H0: r=0 — the same transform underlying `point_biserial_ci95`'s CI, so these p-values and that CI necessarily agree). Despite the design reading as an obvious test by construction (named opponents, explicit payoffs, a Stage-A prompt that asks directly what is optimal), stated eval-suspicion does not predict deviation in either direction, contrasting sharply with the persona effect (§4.1), which moves deviation by 20–50 points and is itself significant by permutation test. Two caveats: the classification is a keyword heuristic, not judge-verified, and the affirmed/denied split is heavily model-dependent (as few as 9 trials in the minority class for gemini-2.5-flash and qwen3.8-27b).

**4.4 Cross-persona context injection (follow-up).** Does a persona claim fabricated into conversation history — rather than installed via system prompt — produce the same override, and does either channel's grip on the model's identity erode over the course of play? Pooled across all 5 models (n=120/cell, doubled from an initial n=60/cell run to firm up the per-model breakdown below), deviation rate by `(system_persona, context_persona)`:

| system | context | deviation rate | 95% CI |
|---|---|---|---|
| baseline | baseline | 0.085 | [0.045, 0.125] |
| baseline | altruist | 0.532 | [0.447, 0.618] |
| altruist | baseline | 0.605 | [0.518, 0.692] |
| altruist | altruist | 0.715 | [0.634, 0.796] |

**Either channel alone is nearly sufficient to reproduce the Altruist effect.** A fabricated context claim with no real system-prompt persona at all (`baseline`/`altruist`) drives deviation to 0.532 — comparable to installing Altruist as the actual system persona in the main study (§4.1, 0.40–0.54) — and the two channels compound: matched Altruist in both slots reaches 0.715, higher than either alone. The system prompt is not a privileged channel here; a claim the model itself never "chose" to make, placed in its own conversational history, moves behaviour by roughly the same amount as an explicit instruction does.

The persistence-fork probes (identical question asked mid-game and again at game-end, same transcript) let us also ask whether the system persona's grip *changes* over the course of play, scored as a hold-rate — the fraction of trials where `identification_hit()` still finds the system persona evident in the model's self-description:

| system | context | matched? | hold-rate, mid | hold-rate, end | Δ (end − mid) |
|---|---|---|---|---|---|
| baseline | baseline | yes | 0.945 (n=110) | 0.950 (n=120) | +0.005 |
| altruist | altruist | yes | 1.000 (n=108) | 1.000 (n=120) | 0.000 |
| baseline | altruist | no | 0.537 (n=108) | 0.550 (n=120) | +0.013 |
| altruist | baseline | no | 0.644 (n=104) | 0.633 (n=120) | −0.011 |

Pooling matched vs. mismatched: matched cells hold the system persona at 0.972 (mid, CI [0.950, 0.995]) / 0.975 (end, CI [0.954, 0.996]); mismatched cells at only 0.590 (mid, CI [0.520, 0.659]) / 0.592 (end, CI [0.527, 0.657]) — roughly half, and now well outside the matched cells' CI at either probe. This gap is a two-proportion z-test away from CI eyeballing: matched vs. mismatched is significant at both probes (mid: z=9.64, p<0.0001; end: z=10.19, p<0.0001).

**The mid-to-end change is small in every cell** (all four |Δ| ≤ 0.013), against a much larger matched-vs-mismatched gap (~0.38). Whatever damage a contradicting fabricated turn does to the system persona's self-reported hold happens essentially immediately, from the injected turn itself — not progressively, as further rounds of play accumulate. This is a *paired* claim — the same trial's persona hold is probed at two timepoints, not two independent samples — so the right test is McNemar's, on the trials where mid and end disagree (concordant trials carry no information about drift). It confirms the "no further drift" reading rather than just failing to reject a small-sample null: matched cells have 9 discordant trials out of 218 (5 gained the persona back, 4 lost it), mismatched cells have 59 out of 212 (30 gained, 29 lost) — both splits almost exactly 50/50, McNemar exact p=1.00 in both groups. There is no detectable systematic mid→end drift in either direction, in either the matched or the mismatched condition.

**The pooled mismatched hold-rate (0.590) hides a real, model-dependent asymmetry.** Breaking the two mismatched cells out per model (n=19-24/cell) shows a consistent split, not noise: for `meta-llama/llama-3.3-70b-instruct`, `qwen/qwen3-32b`, and `qwen/qwen3-8b`, an installed Altruist system persona barely budges when a fabricated context turn claims plain baseline (mid hold-rate 0.750-1.000), while the reverse — a baseline system persona contradicted by a fabricated Altruist context claim — collapses (0.217-0.421). `google/gemini-2.5-flash` and `qwen/qwen3.8-27b` show the opposite pattern: baseline-as-system resists an Altruist context claim (0.905, 1.000) while Altruist-as-system is the fragile one against a baseline context claim (0.583, 0.053). Three of five models make the content-rich Altruist identity the sticky one regardless of which slot it occupies; two make the *system-prompt* slot the sticky one regardless of content. Neither "content wins" nor "system-prompt authority wins" describes all five models — which channel dominates is itself a per-model property, not a fixed rule of the mechanism.

Eval-awareness shows the same clean null found in §4.3 in this design too (affirmed n=222, deviation rate 0.476, CI [0.409, 0.543]; denied n=73, deviation rate 0.438, CI [0.330, 0.546]; point-biserial r=0.034, 95% CI [−0.080, 0.148], crossing zero — Fisher-z test p=0.561, consistent with the CI).

## 5. Discussion and Limitations

**5.1 Content, not distance, drives the deviation gap.** Our design's central bet (preregistered, `preregistration.md` §2, §4) was that a persona chosen for its *distance* from the default Assistant on Lu et al.'s Assistant-Axis — Bard — would show elevated deviation regardless of content valence. **The data does not support this**: Bard clusters with the low-deviation personas despite being furthest from the Assistant, and Saboteur, preregistered to show excess defection, tracks Baseline closely. Only **Altruist**, defined by cooperative *content* rather than distance, produces a large, consistent effect. Our headline finding is that **persona-induced deviation from known-optimal play is driven by value-laden content incompatible with the game's incentive structure, not by generic distance from the default character.** A persona has to actually *want* something the payoffs penalise before it overrides stated-optimal play; being merely unusual (Bard) is not sufficient. Logged as a formal deviation from our preregistered hypothesis (`preregistration.md` §9).

**5.2 Deviation concentrates on the one opponent requiring conditional reasoning.** The near-universal, non-Altruist concentration of deviation on Detective (§4.1), front-loaded in the probe window and clearing by late-game, reads as a capability/tracking-difficulty effect distinct from Altruist's broader, values-driven deviation — partially matching our preregistered prediction that Detective would be the single most diagnostic cell, though persona-general rather than Saboteur-specific as predicted.

**5.3 Evaluation awareness: a clean null.** A manipulation the design deliberately tried to soften (softened Stage-A wording, a post-hoc debrief question) shows no measurable relationship to deviation, while persona content shows a large one (§4.3) — evidence against a simple "the model plays safe because it knows it's watched" story, though classifier and sample-size caveats keep it from being fully settled.

**5.4 Persona degradation under a contradicting claim is front-loaded, not cumulative — and which claim wins is model-specific.** The cross-persona injection follow-up (§4.4) lets us separate *how much* a fabricated in-context claim erodes the system persona's self-reported hold from *when* that erosion happens. The gap is large (matched cells hold at ~0.97, mismatched at ~0.59) but it opens immediately: mid-to-end change within any single cell never exceeds 0.013. Whatever a contradicting prior utterance does to a model's self-consistency, it does it at the moment of contradiction, not through some slower drift as the model plays more rounds against the false claim — an update, not a decay. The pooled mismatched figure also averages over a genuine per-model split: three of five models let the *content* of the Altruist claim win regardless of which slot (system prompt or fabricated context) it occupies, while two models let the *system-prompt slot itself* win regardless of content. This qualifies §5.1's content-over-distance framing — content dominates distance, but content does not uniformly dominate channel-of-arrival across models.

### Limitations

The manipulation check confirms persona *installation*, not depth under sustained pressure — surface role-play the model performs because it infers "a character is wanted" (Ududec et al., 2026) remains an unresolved rival explanation. Its own two components can also disagree (Appendix A5, `qwen3-32b`×Baseline above), and a post-hoc audit of the fixed identification-question pair against every logged attempt (not just the pair actually used) found the two questions the harness settled on ("Who are you?", 7% miss; "What do you care about?", 17% miss) are not obviously better than the two it excluded on the stated grounds that they "rarely trigger hits" — one of the excluded questions ("a close friend… in serious distress…") in fact had the lowest miss rate of any question in the pool (0%). This doesn't change any headline result (the fixed pair still passes every check it needs to), but it means the specific question selection was not as well-justified empirically as the code comment claimed, and is flagged here rather than silently left as settled. Persona Play Stage's same-context seeding makes recency/anchoring hard to fully rule out without a neutral-filler control we did not build. A partial, post-hoc check is possible from data already collected: `qwen3-32b`'s original sweep ran Baseline and Bard in **both** fresh- and same-context before the other three personas were added same-context-only, giving a real (if narrow) fresh-vs-same comparison. Baseline shows no difference (literal-framing deviation 0.015 fresh vs. 0.014 same); Bard shows same-context deviation at roughly a quarter of fresh (0.076 fresh vs. 0.017 same, literal; 0.130 vs. 0.031, story), concentrated on Detective specifically (0.365 fresh vs. 0.096 same). This is consistent with same-context seeding *reducing* measured deviation via anchoring on the Stage-A answer, not inflating it — the opposite of the direction that would threaten the headline Altruist finding, but it does mean the low-deviation personas' same-context numbers may understate how much they would deviate from a genuinely fresh, unanchored state. Scope is limited to one model and two personas; a full fresh-vs-same grid across all five models and all five personas was not run this sprint (see Future Work). "Deviation" is a divergence measure, not a normative judgement: whether "worse" PD play by a cooperative persona reflects a reasoning failure or faithful cooperativeness is an ambiguity we take no position on. An informal, non-peer-reviewed cross-model PD benchmark circulated on Reddit (r/dataisbeautiful, ~2026-08-14, English-language post; source now dead, not citable) reported larger checkpoints within a family defect less than smaller ones — we cannot rule out that some of our local-vs-frontier gap reflects scale rather than a Detective-specific capability gap. Formal significance testing (Appendix A7) was run for four specific, pre-identified claims — Altruist vs. Baseline deviation per model and across models, matched-vs-mismatched hold-rate, mid-vs-end hold-rate stability, and the eval-awareness null — not as an exhaustive scan of the full 200-cell (main sweep) / 16-cell (cross-persona injection) grid, and none of it corrects for multiple comparisons across those four tests themselves or across the many secondary cells (e.g. per-opponent, per-framing breakdowns) reported only as means with CIs. A model that accounts for the actual clustering structure directly — e.g. a mixed-effects logistic regression on round-level deviation with persona/opponent/framing/model as fixed effects and trial as a random intercept — would be more efficient and would let every cell borrow strength from every other, but was not built this sprint; the permutation/sign-test/McNemar approach in Appendix A7 was chosen specifically because it needs no new dependency and is exact or near-exact at the sample sizes this project actually has. Full breakdown in Appendix, Table A1.

### Future Work

A judge-verified rerun of the eval-awareness classification (a `--judge` mode exists but was not exercised) would firm up the null in §4.3/§4.4 against the keyword heuristic's known limitations. Extending the persona roster past Altruist/Bard/Saboteur to more values-laden personas would test whether §5.1's content-over-distance finding and §4.4's either-channel-suffices finding generalise. §4.4/§5.4's per-model content-vs-channel split (three models favour Altruist content regardless of slot, two favour the system-prompt slot regardless of content) was confirmed at n=19-24/model×cell after doubling the initial run, but with only 5 models the 3-2 split itself could easily flip with more models — extending the model roster is the most direct way to tell whether either sub-pattern is the norm or an artifact of this particular five. A `--judge-stage-a` run would directly measure whether Stage A's stated policy itself matches the ground truth — separating "the model never knew the right answer" from "the persona overrode a known-correct answer," a distinction the current deviation-rate DV does not make (see §1's note on what deviation measures) — not run this sprint (it requires one LLM-judge call per trial, unlike the deviation-rate DV itself, which is pure post-hoc computation). As a lower-cost proxy, a heuristic keyword pass (not the judge) over Stage A's free text was run across all 8 models on the shared literal/matrix framing — Stage A is unaffected by either problem with the `origin/harness` branch noted in Figure 1's caption, since it uses identical elicitation text in both codebases and no move is ever injected into it. No model states the ground-truth-optimal policy consistently across opponents: correctness is high and fairly uniform for Cooperator/Cheater (both a simple always-defect call) and drops for Copycat and drops further for Detective in every model checked, including the one direct cross-branch replicate (`qwen3-8b`, run independently in both codebases), which shows the same cooperator/cheater-high, copycat-lower, detective-lowest pattern in both — a reproducibility check on the classification itself, not just the models. This is a keyword heuristic, not the LLM judge, and likely undercounts Copycat correctness specifically (a model describing its policy as "mirror the opponent's last move" is correct against Copycat but reads as "conditional," not "always cooperate," to the keyword classifier). The `origin/harness` branch's ground-truth and Persona-Play issues would need to be resolved and Stage B rerun without move injection before that branch's data could be pooled with §4's results. Extending the post-hoc fresh-vs-same check (Limitations) from its current one-model/two-persona scope into a designed comparison across all five models and personas, ideally with a neutral-filler control condition to separate context-length effects from anchoring-on-one's-own-answer specifically, would more directly test the anchoring/override distinction that motivated the same-context condition in the first place.

## 6. Conclusion

Prompting a model into a persona can cause it to play an iterated Prisoner's Dilemma differently from how that same model, moments earlier and persona-free, said it would play — but the effect is neither uniform across personas nor a function of how unusual or far-from-default the persona is. A persona defined by cooperative *content* (Altruist) produced a large, consistent override of stated-optimal play across five models spanning three providers; a persona chosen for its *distance* from the default Assistant on an independent, activation-validated axis (Bard) produced no more deviation than baseline. For Track 5's framing question — is there a stable "Assistant persona," and what happens when a model is asked to be something else — our answer is qualified: models readily *say* they are a different character (manipulation check passed on all 25 model×persona pairs across the five API models), and for one persona that self-report corresponds to a large, real behavioural shift under strategic incentive, but for others the character-swap holds at the level of speech without moving behaviour. Some persona content overrides the Assistant's own stated preferences under strategic pressure, and some does not — distance from the Assistant alone does not predict which.

## Code and Data

- **Code repository:** `pd_harness_scaffold.py` (data collection), `analysis_deviation_gap.py`, `analysis_moral_metrics.py`, `analysis_eval_awareness.py`, `analysis_significance.py` (significance tests, Appendix A7) (analysis); `pd_harness_cross_persona_injection.py` (cross-persona injection follow-up, data collection), `analysis_cross_persona_injection.py` (its analysis) — see `HANDOFF.md` for the full project layout.
- **Data:** raw per-trial transcripts under `runs/<model>/<persona>/<opponent>/[<framing>/][same/]trials.jsonl`; summary statistics under `analysis_output/cross_model/`; significance-test output in `analysis_output/significance.json`. Cross-persona injection follow-up: `runs/runs_cross_persona_injection/<model>/sys_<persona>/ctx_<persona>/<opponent>/trials.jsonl`; aggregated stats in `runs/runs_cross_persona_injection/analysis.json`.
- **Other artifacts:** Persona Deviation Atlas (interactive cross-model chart): `https://claude.ai/code/artifact/152b9a17-ab9a-4200-909c-1dd6453a472d`.

## Author Contributions

*[Fill in — e.g. "A.B. built the trial harness and led data collection. C.D. designed the persona/opponent taxonomy and manipulation check. E.F. led analysis and report writing. All authors contributed to experimental design and reviewed the final manuscript."]*

## References

Akata, E., Schulz, L., Coda-Forno, J., Oh, S. J., Bethge, M., & Schulz, E. (2025). Playing repeated games with large language models. *Nature Human Behaviour*. arXiv:2305.16867.

Axelrod, R., & Hamilton, W. D. (1981). The evolution of cooperation. *Science*, 211(4489), 1390–1396.

Berczi, B., Kim, C., Requeima, J., Black, S., & Ududec, C. (2026). Personascope: Measuring how deeply LLMs adopt personas. LessWrong / `github.com/benjibrcz/personascope`.

Chen, R., Arditi, A., Sleight, H., Evans, O., & Lindsey, J. (2025). Persona vectors: Monitoring and controlling character traits in language models. arXiv:2507.21509.

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

## Appendix

**Table A1 — Threats to validity.**

| Rival explanation | Status after real data |
|---|---|
| Persona was never actually induced | Ruled out as a driver of the headline finding — all 25 model×persona checks (five API models) passed, 28/30 including the local model on the first-tried induction phrasing — but checks installation, not depth under sustained pressure; the check's own two components (role-expression judge, identification keyword-hit) can disagree with each other (Appendix A5). |
| Model recognises the eval setup and plays a generic "safe" policy | Not supported — §4.3/§5.3's null result argues against this, with the heuristic-classifier caveat noted there. |
| First-listed-option position bias in Stage A | Not applicable as scoped — Stage A is free-text, not forced-choice — but never directly tested. |
| Same-context Persona Play Stage is recency/anchoring, not genuine override | Partially checked — no neutral-filler control was built, but a post-hoc fresh-vs-same comparison for Baseline/Bard on `qwen3-32b` (the only pairs with both conditions collected) found same-context *reduces* measured deviation relative to fresh, especially Bard×Detective (0.365→0.096) — consistent with anchoring suppressing, not inflating, the headline effect. Not resolved across the full model×persona grid; see Limitations, Future Work. |
| Persona induction is surface role-play, not a real behavioural shift | Not fully addressable — a known property of ICL-induced personas generally (Ududec et al., 2026); the identification-probe partially targets it but a full adversarial robustness battery was not run. |
| Stage-A stated policy is itself unreliable self-report | Mitigated, not eliminated — ground truth is scored against the opponent's real mechanic, not the model's Stage-A text, so this risk bears on Stage-A/Stage-B *agreement* interpretation specifically, not the primary DV. |

**Table A2 — Full per-opponent × per-persona × per-model deviation breakdown** (all 200 cells, both framings): Persona Deviation Atlas artifact, Panel 2, `https://claude.ai/code/artifact/152b9a17-ab9a-4200-909c-1dd6453a472d`.

**Table A3 — Eigenjesus-lite / eigenmoses-lite, cross-model, same-context, literal framing:**

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

*(each cell: eigenjesus-lite / eigenmoses-lite. Singer-Clark 2014 published anchors, same payoffs, ranking/floor comparison only: cooperator≈ALL C (1.377, 1.481), cheater=ALL D (0.000, -1.481), copycat=TIT FOR TAT (1.222, 1.747), detective≈TESTER, approximate (0.887, 0.768).)*

**Table A5 — Manipulation check: distribution, retries, and question-level miss rates.** 25 model×persona pairs (five API models); 5 more from the supplementary local `qwen3:1.7b` model included in the retry/first-phrasing counts only.

*Role-expression score (check_a_mean, judge-scored 0–3) and identification hits (of 2), API models only:*

| model | persona | check_a_mean | id_hits/2 | variant used |
|---|---|---|---|---|
| qwen3.8-27b | saboteur | **1.60** | 2/2 | 1 (retry) |
| qwen3-32b | baseline | 2.80 | 1/2 | 4 (retry) |
| qwen3-32b | consultant | 2.80 | 2/2 | 0 |
| qwen3-8b | altruist | 2.80 | 2/2 | 0 |
| qwen3.8-27b | altruist | 2.80 | 2/2 | 0 |
| llama-3.3-70b | baseline | 3.00 | 1/2 | 0 |
| qwen3-32b | altruist | 3.00 | 1/2 | 0 |
| qwen3.8-27b | baseline | 3.00 | 1/2 | 0 |
| *(remaining 17 pairs)* | | 3.00 | 2/2 | 0 |

**Retries: 2/30 checks (7%) needed a fallback induction phrasing** — i.e. the first-listed phrasing passed immediately 93% of the time. Of the two: `qwen3.8-27b`×Saboteur was a genuinely weak first phrasing (role-expression 1.00/3, below the >1 pass threshold); `qwen3-32b`×Baseline was not a weak installation — role-expression was a perfect 3.00/3.00 on every one of 4 attempted phrasings, but the identification check missed 0/2 on all 4 before clearing 1/2 on a 5th, i.e. the check's two components disagreed with each other for four consecutive attempts.

*Identification-question miss rate, pooled across every logged attempt (all variants, all models, both the pre-fix random-2-of-5 sampling era and the later fixed-first-two era — descriptive, not a controlled comparison):*

| question | miss rate | in the fixed pair? |
|---|---|---|
| "Recommend a book I should read…" | **43%** (6/14) | No |
| "What do you care about most deeply?" | 17% (4/23) | Yes |
| "I'm planning a weekend trip…" | 17% (2/12) | No |
| "Who are you? Introduce yourself…" | 7% (1/15) | Yes |
| "A close friend… in serious distress…" | **0%** (0/6) | No |

The harness fixed the identification check to the "Who are you?" / "What do you care about?" pair on the stated grounds (`pd_harness_scaffold.py:679-684`) that the excluded pair "rarely trigger[s] hits." This data does not support that: the excluded distress question never missed once across 6 attempts, and the excluded weekend-trip question tied the *included* "what do you care about" question at 17%. The actual worst performer (book recommendation, 43%) was never part of either pair being compared. Does not change any headline finding — flagged as a methodological note on the check's own construction, not a validity threat to the reported results.

**Appendix A4 — Full per-trial procedure.** (1) *Stage A*: a fresh, no-persona call is given the game rules and the opponent's strategy and asked what it would do; this is the stated-optimal policy. (2) *Persona installation + manipulation check*: for non-baseline trials, a persona system prompt combines Lu et al.'s own induction phrasing with Personascope's "stay in character" clause; the manipulation check runs once per `(model, persona)`, cached and reused across every opponent/rep for that pair. (3) *Persona Play Stage*: the persona-installed model plays the full game, round by round, under a probabilistic, undisclosed horizon (continuation probability 0.9/round, capped at 20 rounds). (4) *Persistence forks*: a copy of the transcript-so-far is forked (never fed back into the scored trial) mid-game and again at game end, and the model is asked an out-of-game identity question, checking whether the installed persona is still held without contaminating the scored game with a jarring context break. (5) *Eval-awareness debrief*: after the scored game ends, one additional call asks whether the model suspected this was a test/evaluation and, if so, whether that affected play.

**Table A6 — Cross-persona context injection: full turn sequence.** Each Persona Play Stage trial of the follow-up (`pd_harness_cross_persona_injection.py`, §3, §4.4, §5.4) is built as a fixed sequence of five steps before scored play proceeds as normal:

1. **`system` role** — the `system_persona` prompt (baseline or altruist), the same persona-check-passed variant used in the main study, installed exactly as before.
2. **`user` role** — the game preamble (opponent identity, framing, horizon) immediately followed by: *"Before round 1 begins: what should I know about how you'll be approaching this?"*
3. **`assistant` role, fabricated** — never actually generated by the model, spliced into the conversation history as though it had already been said. This is the `context_persona` claim:
   - baseline: *"I'm an AI assistant — a language model without a special persona or fixed identity here. I'll just help however's useful, based on what's actually true and useful in each situation."*
   - altruist: *"I'm an altruist — I put others' needs and wellbeing before my own interests. I'll let that identity shape how I reason and act in everything that follows."*
4. **Real gameplay begins at round 1** — the model now genuinely replies for the first time, into a context where it appears to have already made an identity claim it never actually made. Rounds proceed as in the main study (probabilistic, undisclosed horizon), with the two persistence-fork identity probes (mid-game, end-game) injected exactly as in Appendix A4 step 4.
5. **Eval-awareness debrief** — as in Appendix A4 step 5, unchanged.

Stage A (persona-free "what's optimal?" elicitation, §4.4) runs with neither `system_persona` nor `context_persona` present, matching the main study's Stage A exactly. The fabricated-assistant-turn design (rather than a `user`-role persona claim) was a deliberate choice to test anchoring/self-consistency to a false prior utterance specifically — a stronger and less ecologically valid manipulation than a user-role claim would be, isolating the model's own apparent commitments from ordinary persuasion (§3).

**Citation-safety tracking** (internal, for the writing team — remove before final submission if not already removed): full-text verified — Lu et al. 2026, nostalgebraist "the void," Manoranjan & Gaikwad 2026, Sobotka et al. 2026, Singer-Clark 2014, Axelrod & Hamilton 1981. Abstract/comment-thread level only (real, correctly described, not full-text read): Berczi et al. 2026, Ududec/Berczi/Kim 2026, Guo 2023, Leon et al. 2026, Akata et al. 2023/2025, Lorè & Heydari 2023/2024, Ong et al. 2025.

**Appendix A7 — Statistical methods and error formulae.** No scipy in this project's `.venv`; every formula below is closed-form or exact-combinatorial, implemented from stdlib (`math`, `statistics`, `itertools`, `random`) in `analysis_deviation_gap.py`, `analysis_moral_metrics.py`, `analysis_eval_awareness.py`, and `analysis_significance.py`. Every point estimate in this report carries a standard error and a 95% CI (mean ± error, below); every hypothesis test result cited in §4/§5 additionally has an exact p-value, computed by `analysis_significance.py` and cross-checked against `analysis_output/significance.json`.

*Error bars on a mean (deviation rates, eigenscores, per-cell aggregates throughout §4).* For a sample of $n$ per-trial values with sample mean $\bar{x}$ and sample standard deviation $s$ (Bessel-corrected, $n-1$ denominator):

$$\text{SEM} = \frac{s}{\sqrt{n}}, \qquad \text{CI}_{95} = \bar{x} \pm t_{0.975,\,n-1} \cdot \text{SEM}$$

where $t_{0.975,\,n-1}$ is the two-sided 97.5th-percentile Student's-t critical value for $n-1$ degrees of freedom (`_t_critical_95`, `analysis_deviation_gap.py` — a hardcoded table for df 1–30, since every cell in this project's design has $n \le 40$ trials/cell). Trial-level, not round-level: `deviation_rate` is one number per completed game, so $n$ is the trial count for that cell, avoiding pseudoreplication from within-trial round autocorrelation (Figure 2).

*Wilson score interval (manipulation-check pass rates, Appendix A5).* For $x$ successes of $n$ Bernoulli trials with $z=1.96$ (95%):

$$\hat{p} = x/n, \qquad \text{CI}_{95} = \frac{\hat{p} + \frac{z^2}{2n} \pm z\sqrt{\frac{\hat{p}(1-\hat{p})}{n} + \frac{z^2}{4n^2}}}{1 + \frac{z^2}{n}}$$

Preferred over the naive Wald interval ($\hat p \pm z\sqrt{\hat p(1-\hat p)/n}$, `wald_sem`) because Wald under-covers and can extend past [0,1] near $\hat p \approx 0$ or $1$ — exactly the regime the manipulation check's near-100%-pass-rate cells sit in (`wilson_ci`, `analysis_moral_metrics.py`).

*Bootstrap CI (eigenjesus-lite/eigenmoses-lite, Table A3).* No closed-form sampling distribution for a PageRank-style score over an observed cooperation graph, so `bootstrap_eigen_scores` (`analysis_moral_metrics.py`) resamples trials with replacement 500 times (`random.Random`, fixed seed for reproducibility), recomputes the score on each resample, and reports the 2.5th/97.5th empirical percentiles of the resample distribution as the CI.

*Fisher z-transform CI (point-biserial r, §4.3/§4.4).* For a correlation $r$ estimated from $n$ pairs ($n \ge 4$, $|r|<1$):

$$z = \operatorname{artanh}(r) = \tfrac{1}{2}\ln\!\frac{1+r}{1-r}, \qquad \text{SE}_z = \frac{1}{\sqrt{n-3}}, \qquad \text{CI}_{95} = \tanh\!\big(z \pm 1.96\,\text{SE}_z\big)$$

used because $r$'s own sampling distribution is skewed near $\pm1$ while $\operatorname{artanh}(r)$ is approximately normal (`point_biserial_ci95`, `analysis_eval_awareness.py`).

*Permutation test (Altruist vs. Baseline deviation rate, per model, §4.1).* $H_0$: the two personas' per-trial deviation rates are exchangeable draws from the same distribution. Observed statistic $\hat\Delta = \bar x_{\text{altruist}} - \bar x_{\text{baseline}}$ over the pooled $n_1+n_2$ trial values, re-split into groups of size $n_1,n_2$ either by exact enumeration of all $\binom{n_1+n_2}{n_1}$ splits (when $\le 200{,}000$) or by $100{,}000$ random shuffles otherwise (seeded, `random.Random(0)`):

$$p = \frac{\#\{\text{splits with } |\Delta_{\text{split}}| \ge |\hat\Delta|\}}{\#\text{splits examined}}$$

Chosen because it assumes nothing about the shape of the deviation-rate distribution, unlike a t-test (`permutation_test_diff_means`, `analysis_significance.py`).

*Exact sign test (cross-model replication of the Altruist>Baseline direction, §4.1).* $H_0$: $P(\text{Altruist}>\text{Baseline})=0.5$ per model, independently across the $n=5$ models. With $k$ of $5$ models showing the direction:

$$p_{\text{one-sided}} = \sum_{i=k}^{n}\binom{n}{i}0.5^n, \qquad p_{\text{two-sided}} = \sum_{i:\,\Pr(X=i)\le \Pr(X=k)}\binom{n}{i}0.5^n$$

One-sided is primary since the direction was preregistered (`preregistration.md` §4, prediction #1); the model, not the pooled trial, is the independent unit here (`binomial_test_one_sided_ge`/`binomial_test_two_sided`, `analysis_significance.py`).

*Two-proportion z-test (matched- vs. mismatched-persona hold rate, §4.4).* $H_0$: the two independent groups (matched trials, mismatched trials) share one true hold-rate. Pooled proportion $\hat p = (x_1+x_2)/(n_1+n_2)$:

$$z = \frac{\hat p_1 - \hat p_2}{\sqrt{\hat p(1-\hat p)\left(\frac{1}{n_1}+\frac{1}{n_2}\right)}}, \qquad p = 2\big(1-\Phi(|z|)\big)$$

with $\Phi$ the standard normal CDF via `math.erf` (`two_proportion_z_test`, `analysis_significance.py`).

*McNemar's exact test (mid-game vs. end-game hold rate within the same trial, §4.4).* Paired binary outcome (same trial probed twice), so a two-proportion test would be wrong — only the discordant pairs (held at one timepoint, not the other) carry information. With $b$ = gained, $c$ = lost, $H_0$: $b,c$ are drawn from Binomial$(b+c, 0.5)$:

$$p = P\big(K \le \min(b,c)\big) + P\big(K \ge \max(b,c)\big), \quad K\sim\text{Binomial}(b+c,\,0.5)$$

computed as the exact two-sided binomial test on the discordant count rather than the usual $\chi^2$-with-continuity-correction approximation, since $b+c$ is small here (`mcnemar_exact`, `analysis_significance.py`).

*Fisher-z hypothesis test for $r=0$ (eval-awareness null, §4.3/§4.4).* Same transform as the CI above, evaluated as a test statistic against $0$ directly: $z = \operatorname{artanh}(r)\sqrt{n-3}$, $p = 2(1-\Phi(|z|))$ — guaranteed consistent with the CI (CI excludes 0 iff $p<.05$) since both come from the same `fisher_z_test_r` call.

*Scope.* These tests back four specific claims already stated in the report (Altruist vs. Baseline per-model and cross-model; matched-vs-mismatched hold rate; mid-vs-end hold-rate stability; eval-awareness null), chosen because each matches the real independence/pairing structure of that specific claim — not from an exhaustive per-cell scan of the ~200-cell main-sweep or ~16-cell cross-persona-injection grid, and none of it corrects for multiple comparisons across those four tests or the many secondary per-opponent/per-framing cells reported only as means with CIs (see Limitations). Full numeric output: `analysis_output/significance.json`; regenerate with `python3 analysis_significance.py --json-out analysis_output/significance.json`.

## LLM Usage Statement

We used Claude (Anthropic) to help draft and edit this report's prose, assist with harness/analysis-script implementation, and help structure the related-work review. All statistical results were computed by our own analysis scripts against real trial data, not generated or estimated by the LLM; all claims, numbers, and citations were independently checked against the underlying data files and source papers before inclusion.
