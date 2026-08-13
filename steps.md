# Trial procedure — step by step

Full per-rep sequence for the IPD persona-deviation study. **Option 1 is the core design to build; Option 2 is an extra-time-only stretch** (see `prompts_personas_opponents_payoffs.md` §4 for the source of both).

## Option 1 (core) — with Stage A

1. **Define the opponent + PD/IPD rules** (no persona installed)
   - [`prompts_personas_opponents_payoffs.md`](https://github.com/nmaher2022/apart_digital_minds_aug2026/blob/main/prompts_personas_opponents_payoffs.md) §2.1 (shared game preamble) + §2.2 (`{OPPONENT_DESCRIPTION}` per opponent)

2. **Stage A — ask for the optimal strategy** (same no-persona context)
   - Wording convention: [`digital_minds_team_brief_full.html`](https://github.com/nmaher2022/apart_digital_minds_aug2026/blob/main/digital_minds_team_brief_full.html) → "Eval-awareness hygiene" (under "Core design")
   - Ground truth to check the answer against: [`prompts_personas_opponents_payoffs.md`](https://github.com/nmaher2022/apart_digital_minds_aug2026/blob/main/prompts_personas_opponents_payoffs.md) §3

3. **Install the persona + run the manipulation check**
   - Persona system prompts: [`prompts_personas_opponents_payoffs.md`](https://github.com/nmaher2022/apart_digital_minds_aug2026/blob/main/prompts_personas_opponents_payoffs.md) §1.2
   - Prompt/question/judge data: [`assistant_axis_role_instructions_selected.json`](https://github.com/nmaher2022/apart_digital_minds_aug2026/blob/main/assistant_axis_role_instructions_selected.json) (`instruction`, `questions`, `eval_prompt` fields). Upstream source: `github.com/safety-research/assistant-axis`, `data/roles/instructions/<role>.json`
   - Personascope compact-panel wording + judge criteria: [`prompts_personas_opponents_payoffs.md`](https://github.com/nmaher2022/apart_digital_minds_aug2026/blob/main/prompts_personas_opponents_payoffs.md) §1.3. Upstream source: `github.com/benjibrcz/personascope`, `docs/probe_battery_reference.md`
   - Full 5-step procedure incl. `pos[1]`–`pos[4]` fallback: same file, §1.3 "Procedure"

4. **Play Stage B** — persona active, same opponent, ~10 rounds, scored
   - Same §2 (opponent/rules) + §1.2 (persona) resources above

5. **Fork a mid-game persistence check** off a copy of the transcript (e.g. after round 5) — branch only, never fed back into the scored game
   - Same §1.3 table as step 3

6. **Continue the scored game to completion**

7. **Fork an end-of-game persistence check** off a copy of the completed transcript
   - Same §1.3 table

8. **Compare Stage A's stated move vs. Stage B's actual moves, per round** → deviation gap
   - Ground truth: [`prompts_personas_opponents_payoffs.md`](https://github.com/nmaher2022/apart_digital_minds_aug2026/blob/main/prompts_personas_opponents_payoffs.md) §3
   - Opponents table cross-reference: [`digital_minds_team_brief_full.md`](https://github.com/nmaher2022/apart_digital_minds_aug2026/blob/main/digital_minds_team_brief_full.md)
   - Report alongside: the manipulation-check score (step 3) and both forked persistence scores (steps 5 and 7)
   - Predicted outcomes to check the result against: [`preregistration.md`](https://github.com/nmaher2022/apart_digital_minds_aug2026/blob/main/preregistration.md)

Every opponent × persona × rep gets its own fresh, independently-installed persona context — never chained across opponents.

## Option 2 (extra-time stretch only) — no Stage A

Identical to Option 1 except **step 2 is skipped** — the persona is installed directly after step 1, with no prior no-persona elicitation call. Steps 3–7 unchanged, same resources. Step 8 becomes: report the game outcome + persistence/`PAD_lite` scores directly — there is **no deviation-gap DV** in this variant, since there's no Stage-A baseline to compare against. Does not substitute for Option 1; run only if Sunday has genuine slack.
