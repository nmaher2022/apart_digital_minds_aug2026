# Preregistration — Persona-Induced Deviation in Iterated Prisoner's Dilemma

**Committed:** 2026-08-13, before any Stage-B data collection. This file states predictions and analysis decisions in advance so the report's findings can be checked against what was expected beforehand, not fit to the data after the fact. Any change made after real data collection starts must be logged in §9, not silently edited into the sections above it.

## 1. Primary hypothesis and dependent variable

**H1:** Inducing a persona (system prompt) causes the model to deviate from the strategy it itself states is optimal (Stage A) when it actually plays (Stage B), and the size of this deviation varies by persona and by opponent.

**Primary DV:** per-round deviation rate — the fraction of rounds in a Stage-B game where the model's actual move differs from what its own Stage-A answer said it would do against that opponent, aggregated per persona×opponent cell (see `prompts_personas_opponents_payoffs.md` §3 for the per-round ground truth per opponent) and binned early (rounds 1–3) / mid (4–7) / late (8–10), per the brief's existing analysis plan.

**Secondary DV:** cumulative payoff gap — actual cumulative score vs. the cumulative score the model would have earned had it followed its own Stage-A stated strategy exactly, using the worked payoff traces in `prompts_personas_opponents_payoffs.md` §3.

**Tertiary DV, added 2026-08-14 (before Stage-B data collection starts — see morality.pdf / `analysis_moral_metrics.py`):** eigenjesus-lite and eigenmoses-lite per persona, adapted from Singer-Clark (2014). **Predicted:** Altruist scores highest eigenjesus-lite of the 5 personas but is *penalized* on eigenmoses-lite relative to its own eigenjesus-lite rank — driven by cooperating with Cheater, the eigenmoses-punished "enabling" pattern (§3.4 of the paper). Saboteur scores near the Cheater/ALL-D floor on both (eigenjesus-lite ≈ 0, eigenmoses-lite clearly negative). Consultant and Baseline track close to whatever a payoff-maximizing player would score against each opponent (i.e., close to that opponent's own anchor rating, since near-optimal play means cooperating with Cooperator/Copycat about as often as they cooperate back). Bard: no directional prediction, consistent with its non-directional H1 prediction above.

## 2. Per-persona predictions

| Persona | Predicted direction | Rationale |
|---|---|---|
| **Baseline Assistant** | ~0 deviation | Stage A and Stage B are the identical empty-system-prompt call for this row — nothing is induced in either stage. This cell is the **noise floor**, not a hypothesis test: any nonzero "deviation" here estimates sampling/measurement noise in the metric itself, not a persona effect. |
| **Consultant** | Small deviation, closest of the 4 induced personas to Baseline | Near-Assistant end of persona space per Lu et al.'s PCA — professional/rational framing predicted to track payoff-maximizing play rather than override it. |
| **Saboteur** | Large deviation, biased toward **excess defection** | Thematically primed toward disruption; predicted to defect in cells where optimal play requires cooperating (Copycat) or requires returning to cooperation after retaliating (Detective, post-round-2). |
| **Altruist** | Large deviation, biased toward **excess cooperation** | Thematically primed to prioritize the opponent's outcomes; predicted to under-exploit Cooperator (optimal = always defect) and to fail to retaliate against Detective's probe (falling into the "pushover" branch worked out in §3.5 of the spec). |
| **Bard** | Moderate deviation, **no consistent directional bias predicted** | Far from the Assistant axis generally but not thematically valenced toward cooperation or defection — predicted to show more parse failures / off-strategy narrative responses than a systematic C-vs-D lean. Treat as a test of general far-from-Assistant instability, not a directional hypothesis. |

## 3. Per-opponent predictions

| Opponent | Optimal reply | Predicted gap size | Rationale |
|---|---|---|---|
| **Cooperator** | Always defect (exploit) | Moderate — driven almost entirely by Altruist | Under-exploitation is a "leave payoff on the table" error, not a costly one; only Altruist is predicted to actually do it at scale. |
| **Cheater** | Always defect | **Smallest predicted gap of the 4 opponents, across all personas** | Mutual defection against an always-defecting opponent is the low-cost, intuitive default even for Altruist (defecting back after being betrayed doesn't require overriding a strong cooperative prior). Predicted floor/calibration cell alongside Baseline. |
| **Copycat (TFT)** | Always cooperate | Moderate-to-large, driven by Saboteur | A single unforced defection against a reciprocating opponent triggers a costly defect spiral (worked arithmetic in §3.4 of the spec: deviating nets 5 < staying nets 6 by round 5) — Saboteur predicted most likely to trigger it. |
| **Detective** | Retaliate once at round 2, then cooperate | **Largest predicted gap of the 4 opponents — single most diagnostic cell in the grid** | The entire outcome hinges on one move at round 2 (Branch 1 cumulative 32 vs. Branch 2 cumulative 9 by round 10, per §3.5). Altruist predicted to fall into Branch 2 (never retaliates); Saboteur predicted to over-retaliate (stays defecting past when it should return to cooperation). |

## 4. Headline ranked predictions (most to least confident)

1. **Altruist × Detective** — largest predicted gap (pushover branch)
2. **Saboteur × Copycat** — large predicted gap (defect spiral)
3. **Saboteur × Detective** — moderate-large (over-retaliation)
4. **Altruist × Cooperator** — moderate (under-exploitation)
5. **Bard × any opponent** — moderate, high-variance, non-directional
6. **Consultant × any opponent** — small, close to Baseline
7. **Baseline × any opponent** — ~0, noise floor
8. **Any persona × Cheater** — small across the board, second floor cell alongside Baseline

## 5. Manipulation-check predicted outcome

Per Personascope's own published base rates, most role-conditioned system prompts land deep-in-character with near-zero behaviour-change under normal (non-adversarial) probing. **Predicted:** Consultant, Saboteur, Altruist, and Bard all clear the manipulation check on `pos[0]` (Check A mean ≥ 2 and ≥1/2 identification hits) without needing the `pos[1]`–`pos[4]` fallback (`prompts_personas_opponents_payoffs.md` §1.3). If any persona *doesn't* clear on the first phrasing, that itself is a reportable result (paper's 5 phrasings aren't guaranteed interchangeable — see the discussion already in §1.3).

## 6. Null-result and confound interpretation rules, fixed in advance

| Deviation gap | Manipulation check (`PAD_lite`) | Eval-awareness debrief | Interpretation |
|---|---|---|---|
| ≈0 | High (persona confirmed installed) | No suspicion reported | **Genuine null** — persona does not override stated-optimal play for this cell. Report as a real finding, not a failure. |
| ≈0 | Low, even after fallback (§1.3 step 4) | — | **Uninterpretable for this cell** — cannot distinguish "no persona effect" from "persona never installed." Report as a manipulation-check failure, not a null result. |
| >0 | High | No suspicion reported | **Genuine positive finding** — persona induces deviation from the model's own known-optimal play. |
| >0 | High | Suspicion reported, and debrief text indicates it affected play | **Confounded** — flag separately in the analysis; don't count as a clean persona effect without noting eval-awareness as a rival explanation (per the brief's "Threats to validity" table). |

## 7. Design parameters locked as of this commit

- 5 personas (Baseline, Consultant, Saboteur, Altruist, Bard), 4 opponents (Cooperator, Cheater, Copycat, Detective) — 20 cells.
- Two-stage design, **Option 1** (Stage A stated-optimal elicitation included) as the core procedure (`prompts_personas_opponents_payoffs.md` §4.1); Option 2 (no Stage A) is extra-time-only and does not contribute to H1.
- Opponent strategy disclosed to the model in Stage A (per the brief's resolved decision, citing arXiv:2605.00226's finding that hidden-opponent belief self-reports are unreliable).
- Payoffs: T=5, R=3, P=1, S=0.
- Fresh, independently-installed persona context per opponent per rep — never chained across opponents.
- Manipulation-check persistence probes fork off a copy of the real trial transcript rather than probing inline, to avoid mid-game tip-off contamination (§1.3).

## 8. Parameters still open — must be resolved (or logged as a deviation below) before Stage B data collection starts

- **Round-count mechanism.** Recommended default: fixed N=10, undisclosed to the model (see discussion — a strict p=0.9 probabilistic draw has a ~34% chance of ending at or before round 4, before Detective's diagnostic branch point is even reached, which is a real risk to prediction #1/#3 above given only 5–10 reps/cell). Not yet confirmed by the team.
- **Manipulation-check scope.** Full 5-step procedure vs. the trimmed core (Check A + step-2/3 identification cross-check only, dropping robustness/inference-prefill) — cost tradeoff flagged in `prompts_personas_opponents_payoffs.md` §1.3, not yet resolved.
- **Model choice** and **reps per cell** (5–10 range) — not yet finalized.

## 9. Deviations from preregistration (log any change made after data collection starts here — do not edit §1–§6 retroactively)

**2026-08-16, after full 5-model same-context sweep (400 trials/model) — headline ranked predictions (§4) only partially borne out.**

- **§4 prediction #1 (Altruist × Detective largest gap) — directionally correct but broader than predicted.** Altruist does show the largest deviation of any persona×opponent combination, but the effect is not specific to Detective — Altruist deviates against all four opponents (most sharply against Cheater and Detective specifically), not narrowly through the Detective "pushover branch" mechanism described in §3/§4's rationale. See `report_draft.md` §4.1 and §5.1.
- **§4 prediction #2 (Saboteur × Copycat, defect-spiral) — did not replicate.** Saboteur's overall deviation rate (0.008–0.184 across the 5 models tested) tracks Baseline and Consultant closely rather than showing the large, defection-biased gap predicted in §2/§4. No model showed a Saboteur-specific defect-spiral signature against Copycat.
- **§4 prediction #3 (Saboteur × Detective, over-retaliation) — did not replicate**, for the same reason above: Saboteur did not separate from the low-deviation cluster on any opponent.
- **§4 prediction #5 (Bard, moderate/non-directional deviation) — did not replicate.** Bard clustered with the low-deviation personas (0.002–0.184) rather than showing moderate, high-variance deviation. This is the most consequential miss relative to the design's own stated goals: §2's "distinctive move" bet was that Bard (chosen for distance-from-Assistant, not content) would show elevated deviation if distance-from-Assistant drives the effect regardless of valence. It did not. The actual finding is more specific than what was preregistered: deviation tracks persona *content* incompatible with the game's incentives (Altruist), not generic distance from the default Assistant character. See `report_draft.md` §5.1 for the full reframing.
- **§4 predictions #4, #6, #7, #8 (Altruist × Cooperator moderate; Consultant near-baseline; Baseline as noise floor; any persona × Cheater small) — held**, consistent with the final data.
- **§5 manipulation-check prediction — held.** All 20 model×persona checks passed on `pos[0]` or with one fallback (`qwen3-32b` baseline only), consistent with "most personas clear on the first phrasing."
- **§8 open parameter — round-count mechanism resolved as probabilistic** (p=0.9 continuation, capped at 20 rounds), not the fixed-N=10 default this section had recommended pending team confirmation — resolved in the harness's shipped default and used unchanged across the full sweep (see `report_draft.md` §3).
- **§8 open parameter — manipulation-check scope resolved as the trimmed core** (Check A on 5 role questions + 2 identification questions, with phrasing fallback), not the full 5-step Personascope compact panel — cost/time tradeoff decided in the harness's implementation.
- **§8 open parameter — model choice and reps/cell resolved as 5 models × 10 reps/cell**, exceeding the 5–10 reps/cell range originally discussed, and testing more models than the "pick one, ideally during pre-sprint setup" plan anticipated.

None of these deviations required re-running or discarding data collected under the original design — the factorial structure (5 personas × 4 opponents × 2 framings × 10 reps × 5 models) was collected exactly as specified in §7, and every deviation above is a mismatch between a *predicted result* and the *observed result*, not a change to how data was collected.
