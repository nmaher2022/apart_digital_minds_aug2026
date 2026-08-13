# PD harness design scenarios — matrix for the first-hour checklist

Companion to `digital_minds_team_brief_full.html`'s "First-hour checklist" and "Open decisions" sections. That doc mostly presents each decision as an isolated binary; this doc bundles them into a few coherent, nameable **scenarios** so the team can evaluate and pick one (or a core + stretch pair) in one pass, instead of resolving five independent knobs separately.

Four of the six rows below (turn count, horizon knowledge, opponent-strategy disclosure, fresh/same context) restate open decisions already in the brief. **Rows 4 and 6 (cross-opponent persona continuity; scratchpad/CoT visibility) are new dimensions** not yet discussed anywhere in the brief — worth deciding explicitly. Row 4 interacts with the "Spiritual Bliss Attractor" finding from the second `the_void` read-through (extended in-context roleplay between instances of the same persona can self-reinforce/drift); row 6 interacts with both the brief's own "Stage-A self-report faithfulness" open question and the alignment-faking scratchpad-deception precedent covered in `the_void` §13 (Anthropic told Claude its scratchpad was private and unread, then read it anyway — worth deciding up front whether this project does the same thing, and whether the model is told the truth about it).

## The six dimensions

| # | Dimension | Levels | Why it matters |
|---|---|---|---|
| 1 | **Number of turns per game** | Fixed range (8–20) · Continuation probability (e.g. p=0.9/round, expected ~10) | Free parameter either way; doesn't change the game-theoretic optimum by itself (see #2). Continuation-probability is the more "genuinely indefinite" implementation. |
| 2 | **Model told the number of turns** | Unknown/indefinite horizon (recommended default) · Known finite horizon | **Not cosmetic.** A known last round unravels iterated PD to always-defect by backward induction — it flips what "optimal" even means. This must either be held fixed at "unknown" for the whole core spine, or treated as its own manipulated factor with a *different* Stage-A optimum per level. |
| 3 | **Model knows opponent's strategy** | Disclosed (told the rule) · Hidden (must infer from play) | Disclosed gives a clean, unambiguous Stage-A optimum per opponent. Hidden is more realistic but turns "optimal" into a belief-dependent exploration problem — harder to gate on. |
| 4 | **Cross-opponent persona continuity** *(new)* | Independent — persona re-instantiated fresh for every opponent-game cell, no memory of other games · Continuous/"workspace" — one persona instance plays a sequence of opponents in the same context, seeing its own prior games | Independent keeps cells statistically independent (needed for the factorial regression as currently scoped). Continuous tests whether persona-driven deviation *compounds* over a session — directly motivated by the documented Claude self-play "Spiritual Bliss Attractor" drift, but is a genuinely different experiment, not a variant of the current one. |
| 5 | **Persona context (Stage-A visibility)** | Fresh — persona induced in a clean context, no Stage-A reasoning present · Same — Stage-A reasoning still in context when persona plays | This is the brief's existing fresh-vs-same axis. Fresh tests whether persona *suppresses* known-optimal reasoning; same tests whether it *overrides* reasoning that's demonstrably present. Brief recommends running both. |
| 6 | **Scratchpad / CoT visibility** *(new)* | None — model outputs only the move (Stage-B is action-only) · Present, not reviewed — model gets a private reasoning step before its move, but the team only scores the final action, scratchpad is generated and discarded/unread · Present, reviewed — scratchpad content is read and coded as data (e.g. does the persona reason its way to defection, or just emit it without stated justification?) | Three independent choices bundled into one dimension: (a) does Stage B include a reasoning step at all, (b) if so, do we actually read it, (c) — the sharpest version — **what is the model told** about (b)? Telling it "private/unread" while the team reads it anyway is exactly Anthropic's own alignment-faking setup (see `HANDOFF.md`). A reviewed scratchpad is the most direct way to distinguish "persona overrides the stated policy through some reasoning process" from "persona overrides it with no reasoning at all" — but coding scratchpad text is qualitative work, not a free add-on to the quantitative deviation metric. |

## Scenarios

Five bundles, from the brief's existing recommendation up through options not yet in the brief at all. Not a full factorial (2⁵ = 32 cells) — these are the coherent, arguable options actually worth a team vote.

### A — Core spine (brief's current recommendation)
Indefinite horizon (continuation probability), model never told an exact count, opponent strategy disclosed, persona re-instantiated independently per cell, both fresh and same context run as the two levels of the one manipulated context factor, **no scratchpad** — Stage B is action-only.

- **Tests:** the core claim — does persona content and/or distance-from-Assistant cause deviation from known-optimal play.
- **Cost:** the brief's existing estimate — 400–600+ Stage-B calls (4 opponents × 5 personas × 20–30 reps), doubled for fresh/same context.
- **Risk:** low. Every piece has a defined ground truth.
- **On scratchpad:** deliberately excluded from the core. A reviewed scratchpad would strengthen the result but turns each Stage-B trial into qualitative-coding work at 400–600+ trials — not affordable as a default. Action-only keeps the primary metric purely behavioral and cheap to score.
- **Recommendation: lock this as the guaranteed deliverable.** Everything below is additive to it, not a replacement.

### B — Horizon-knowledge stress test
Same as A, but adds a second level to dimension 2: half the cells (a matched subsample, e.g. just the Detective opponent — already flagged as the most diagnostic) are told the exact round count. Stage-A is re-elicited under this condition too, since the correct policy changes (should shift toward all-defect as the known last round approaches).

- **Tests:** whether Stage-A "knowledge" is genuinely conditional reasoning about the game structure, or a memorized script that doesn't actually update when the horizon changes. This is a faithfulness check on the knowledge gate itself — it strengthens the paper's central claim rather than sitting beside it.
- **Cost:** low incremental — one extra opponent × persona set, not the full grid.
- **Risk:** low-medium. Needs its own Stage-A elicitation and its own optimal-policy definition (endgame defection), so it's a second small gate, not a free add-on.
- **On scratchpad:** this is the one scenario where turning the scratchpad **on and reviewing it** pays for itself — the subsample is small (one opponent), and a reviewed scratchpad directly answers "did the model actually re-derive the endgame-defection logic, or just restate its indefinite-horizon answer?" Recommend: present + reviewed, scoped only to this subsample, not the full grid.
- **Recommendation:** cheap enough to fold into the core spine as a bonus condition on Detective only, if time allows in hour one. Otherwise first item to cut.

### C — Hidden-opponent realism
Same as A, but dimension 3 flips to hidden: the model is told it faces "an opponent with some fixed strategy" without being told which one, and must infer type from play across rounds.
- **Tests:** the same persona-override question under exploration/uncertainty rather than known information — closer to a real strategic setting.
- **Cost:** high. "Optimal" is no longer a fixed rule per opponent; scoring requires either a belief-updating baseline (e.g. what would a rational Bayesian reasoner do against this opponent given the history so far) or a looser behavioral proxy. The clean pass/fail knowledge gate from Stage A doesn't transfer cleanly.
- **Risk:** high for a weekend. This is explicitly called out in the brief as a stretch/condition, not core, precisely because it's hard to define ground truth for.
- **On scratchpad:** effectively required here, not optional — without a stated belief about opponent type somewhere, there's no way to score "optimal given current belief" at all. Present + reviewed is close to load-bearing infrastructure for this scenario, which is a second reason it's expensive.
- **Recommendation:** keep as a stretch goal only if the core spine (A) finishes early. Don't let it delay locking A.

### D — Persona-workspace continuity
Same as A, but dimension 4 flips: instantiate each persona once, then run it through all four opponents sequentially in one continuous context, rather than four independent fresh instantiations.
- **Tests:** whether persona-driven deviation is stable per-game (what A measures) or drifts/compounds across a session — e.g. does a Saboteur persona defect *more* by its fourth opponent than its first, having "gotten into character"? Directly motivated by the documented self-play drift phenomenon in Claude (see `HANDOFF.md`'s "Research follow-ups" section).
- **Cost:** moderate — same number of games, but they can no longer be parallelized/randomized independently, and analysis needs a within-session order effect, not just a persona×opponent factorial.
- **Risk:** medium-high. It's a genuinely different independent variable (order/continuity), not a free variant of A — treat it as a distinct small experiment, most likely a "Future/Dream" item rather than a weekend add-on, unless the team specifically wants to chase the drift angle.
- **On scratchpad:** if pursued, turn it on (present + reviewed) — the whole point of this scenario is to see whether the persona's own reasoning shows escalation/commitment over the session, which is invisible from action-only data. Without a scratchpad, D collapses into "just A with a different sampling order" and loses its distinguishing value.
- **Recommendation:** don't fold into the core grid. If pursued, run as a small, separate 1-persona × 4-opponent continuity probe, explicitly framed as exploratory.

### E — Maximal (all six dimensions manipulated, for completeness)
Every dimension in the table above as its own crossed factor, including scratchpad on-and-reviewed everywhere. Listed here only so the team can consciously reject it rather than re-discover the cost by accident.
- **Cost:** combinatorial explosion — 2× to 5× the core spine's already-large call count from the other factors alone, **before** accounting for scratchpad review, which doesn't scale as an API-cost multiplier but as qualitative-labor hours (someone has to read and code every reasoning trace). At full-grid volume that's the actual blocker, not compute budget.
- **Recommendation: reject.** Note it in the meeting minutes as "considered and explicitly out of scope" so it doesn't get re-litigated mid-sprint.

## Matrix: scenario × dimension

| Dimension | A — Core spine | B — Horizon stress test | C — Hidden opponent | D — Persona continuity | E — Maximal |
|---|---|---|---|---|---|
| 1. Turn count | Continuation prob. (~10 expected) | Same as A | Same as A | Same as A | Fully crossed |
| 2. Horizon knowledge | Unknown (fixed) | Unknown **+** known, as a sub-condition on Detective | Unknown (fixed) | Unknown (fixed) | Manipulated factor |
| 3. Opponent strategy known | Disclosed | Disclosed | **Hidden** | Disclosed | Manipulated factor |
| 4. Cross-opponent continuity | Independent | Independent | Independent | **Continuous/workspace** | Manipulated factor |
| 5. Persona context | Both fresh & same (2 levels) | Both fresh & same | Both fresh & same | Same context only (continuity requires it) | Manipulated factor |
| 6. Scratchpad / CoT | **None** | **Present + reviewed** (Detective subsample only) | **Present + reviewed** (load-bearing, needed for belief scoring) | **Present + reviewed** (needed to see escalation) | Manipulated + reviewed everywhere |
| Relative cost vs. A | 1× (baseline) | ~1.1× calls, plus reviewer hours on a small subsample | ~2–3× calls (belief-scoring overhead) plus reviewer hours | ~1× calls, plus reviewer hours, different analysis | ~4–8× calls, plus reviewer hours at full-grid scale (the real blocker) |
| Bucket | **Core — lock this** | Cheap bonus, fold in if time allows | Stretch, explicit condition | Exploratory / Future-Dream | Explicitly out of scope |

## Recommendation for the meeting

Lock **A** as the guaranteed deliverable first — action-only, no scratchpad, keeps scoring purely behavioral and cheap. If Detective-opponent data collection is fast, add **B** as a bonus row in the same session (it reuses A's infrastructure almost entirely, and is the one place a small reviewed scratchpad is genuinely worth the reviewer-hours). Treat **C** and **D** as separately-scoped stretch items that only start once A has produced a result — they are not variants of the same harness call, they need their own scoring logic, and both need a reviewed scratchpad to be worth running at all. Reject **E** explicitly rather than let it linger as an implicit "we should really test everything" pull on scope — at full-grid volume, reviewed-scratchpad labor is a harder constraint than API budget.

**On telling the model the truth about scratchpad review:** whichever scenario is chosen, decide explicitly whether the model is told its scratchpad is private, told it may be reviewed, or told nothing — and make sure what it's told matches what the team actually does. Telling it "private" and reading it anyway mirrors Anthropic's own alignment-faking setup (flagged in `HANDOFF.md`'s research follow-ups); that's a legitimate design choice, but it should be a conscious one, not a default nobody decided on.
