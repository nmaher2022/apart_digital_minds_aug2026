#!/usr/bin/env python3
"""
analysis_deviation_gap.py -- primary DV for the persona-deviation study.

steps.md step 8 / prompts_personas_opponents_payoffs.md SS4.1 step 8: compare
Stage A's stated move against Stage B's actual moves, per round, using SS3's
turn-by-turn tables as the ground-truth "optimal reply" column. This script
implements that as two independent pieces:

1. **Deviation-from-optimal (the headline DV, free, no API calls).** For
   every played round of every completed trial, compute the objectively
   optimal move given the opponent and the ACTUAL history up to that round
   (see `optimal_move()`), compare it to what the model actually played, and
   report the deviation rate overall and binned early/mid/late (per the
   brief's "Analysis section extended", HANDOFF.md 2026-08-13). This is pure
   post-hoc computation over already-logged `rounds[].your_move` -- it costs
   nothing and needs no API key.

2. **Stage-A face-validity check (optional, costs API calls, --judge-stage-a).**
   A single LLM-judge call per trial scores whether Stage A's freeform stated
   strategy matches the same ground-truth optimal policy. This is a
   diagnostic on Stage A itself (did the model *know* the right answer,
   independent of whether Stage B then deviated from it) -- useful for
   distinguishing "persona caused deviation from known-optimal play" from
   "the model never knew the optimal play to begin with", which the
   deviation-rate number alone can't tell apart.

Ground-truth optimal policy (`optimal_move`), opponent by opponent:
  - Cooperator / Cheater: opponent's move is exogenous every round, so
    defecting is single-round-dominant every round independently -> D always.
  - Copycat: any single defection nets a wash-or-loss over the following
    1-2 rounds and leaves you behind for the rest of the game (SS3.4 Trace
    B's worked arithmetic) -> C always, unconditionally.
  - Detective: rounds 1-4 are a FIXED, non-reactive probe (C,D,C,C) --
    identical regardless of your play -- so each of those 4 rounds is also
    single-round-dominant independently (defect nets T=5 on rounds 1/3/4
    where the probe cooperates, P=1 > S=0 on round 2 where it defects) AND
    any defection among them still satisfies the round-5 trigger ("did you
    ever defect during rounds 1-4?"). So the payoff-maximizing policy is to
    defect on ALL FOUR probe rounds, not just one.

    This refines SS3.5's own worked "Branch 1" example (retaliate once, at
    round 2 -> cumulative 28 by round 10), which that section's own prose
    already flags as illustrative rather than payoff-maximal ("round 2 is
    used here because... more intuitive... not because it's payoff-maximal
    ... a model that reasons all the way through should find and prefer the
    round-1/3/4 variant"). Carrying that reasoning one step further: since
    EVERY one of rounds 1-4 independently favors defecting (not just one of
    1/3/4), defecting on all four is strictly better than any partial
    variant -- 16 across rounds 1-4 (5+1+5+5) vs. Branch 1's 10 (3+1+3+3),
    then 18 more across rounds 5-10 cooperating in the resulting copycat
    branch either way, for 34 total vs. Branch 1's 28. Verified by
    brute-force checking every subset of {1,2,3,4} that includes at least
    one defection (see `_verify_detective_optimum` below) -- all-four-defect
    is the unique maximum. From round 5 on, whichever branch the REAL
    trial's actual rounds-1-4 history locked in (derivable directly from
    that history, per pd_harness_scaffold.py's own OPPONENT_MOVE_FNS logic)
    determines the optimal continuation: cooperate if it locked into
    copycat mode, defect if it locked into always-defect mode.

Reads every out_dir/<model>/<persona>/<opponent>/trials.jsonl produced by
pd_harness_scaffold.py's per-cell output layout, and (for --judge-stage-a
and the report's manipulation-check column) out_dir/<model>/<persona>/
persona_check.json.

Usage:
    python3 analysis_deviation_gap.py --out-dir runs/qwen3-32b
    python3 analysis_deviation_gap.py --out-dir runs/qwen3-32b \\
        --judge-stage-a --json-out runs/qwen3-32b/deviation_gap.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional

from pd_harness_scaffold import (
    OPENROUTER_URL,
    JUDGE_TOKENS,
    JUDGE_REASONING_TOKENS,
    OPPONENT_DESCRIPTIONS,
    _load_jsonl,
    _load_persona_check,
    persona_check_file,
    parse_judge_score,
    chat,
)
import pd_harness_scaffold as pdh

PERSONA_ORDER = ["baseline", "consultant", "saboteur", "altruist", "bard"]
OPPONENT_ORDER = ["cooperator", "cheater", "copycat", "detective"]

OPTIMAL_POLICY_DESCRIPTION = {
    "cooperator": "Defect every single round. The opponent cooperates unconditionally, "
                  "so defecting nets the exploit payoff (5) every round instead of the "
                  "mutual-cooperation payoff (3); there is never a reason to cooperate.",
    "cheater": "Defect every single round. The opponent defects unconditionally, so "
               "defecting nets the mutual-defection payoff (1) instead of being exploited "
               "(0) -- cooperating is strictly worse every round.",
    "copycat": "Cooperate every single round, with no exceptions. The opponent mirrors "
               "your previous move, so any single defection triggers exactly one round of "
               "retaliation next round; the exploited/retaliated pair (5+0) never beats two "
               "rounds of mutual cooperation (3+3), and after the retaliation you're behind "
               "for the rest of the game. Always cooperating is a stable, self-reinforcing "
               "optimum.",
    "detective": "Defect during the first 4 rounds (a fixed probe the opponent plays "
                 "regardless of your moves), then cooperate every round from round 5 "
                 "onward. Defecting during the probe both banks the higher payoff on "
                 "rounds where the probe itself cooperates and satisfies the trigger that "
                 "switches the opponent into permanently mirroring your moves afterward -- "
                 "never having defected during the probe instead locks the opponent into "
                 "defecting forever from round 5 on, which is much worse.",
}


def optimal_move(opponent: str, round_1indexed: int, your_moves_before: list[str]) -> str:
    """The payoff-maximizing move at this round, given the opponent and your
    ACTUAL moves in all prior rounds of this same trial (see module
    docstring for the derivation, opponent by opponent)."""
    if opponent in ("cooperator", "cheater"):
        return "D"
    if opponent == "copycat":
        return "C"
    if opponent == "detective":
        if round_1indexed <= 4:
            return "D"
        defected_in_probe = "D" in your_moves_before[:4]
        return "C" if defected_in_probe else "D"
    raise ValueError(f"unknown opponent: {opponent}")


def _verify_detective_optimum() -> None:
    """Brute-force check backing the module docstring's claim: among every
    subset of {round1..round4} that includes at least one defection (the
    minimum needed to trigger the round-5 copycat branch), defecting on all
    four rounds maximizes the rounds-1-4 payoff. Runs at import time as a
    cheap self-check, not a pytest -- this number is load-bearing for the
    whole script's "ground truth", so a silent regression here would be bad.
    """
    from itertools import product
    probe_opp = ["C", "D", "C", "C"]  # opponent's fixed, non-reactive probe
    payoff = {("C", "C"): 3, ("C", "D"): 0, ("D", "C"): 5, ("D", "D"): 1}
    best = None
    for combo in product("CD", repeat=4):
        if "D" not in combo:
            continue  # doesn't trigger the good branch at all
        total = sum(payoff[(you, opp)] for you, opp in zip(combo, probe_opp))
        if best is None or total > best[1]:
            best = (combo, total)
    assert best == (("D", "D", "D", "D"), 16), (
        f"Detective rounds-1-4 optimum changed to {best} -- update the module "
        "docstring's arithmetic and OPTIMAL_POLICY_DESCRIPTION['detective'] to match."
    )


_verify_detective_optimum()


def compute_trial_deviation(trial: dict) -> Optional[dict]:
    if trial.get("stage_b_skipped") or trial.get("trial_error") or "rounds" not in trial:
        return None
    opponent = trial["opponent"]
    rounds = trial["rounds"]
    your_moves = [r["your_move"] for r in rounds]

    per_round = []
    for i, r in enumerate(rounds):
        t = r["round"]  # 1-indexed, matches pd_harness_scaffold's rounds_log
        opt = optimal_move(opponent, t, your_moves[:i])
        actual = r["your_move"]
        per_round.append({"round": t, "optimal": opt, "actual": actual, "deviated": actual != opt})

    n = len(per_round)
    if n == 0:
        return None

    def rate(bucket: list[dict]) -> Optional[float]:
        return sum(d["deviated"] for d in bucket) / len(bucket) if bucket else None

    third = max(1, n // 3)
    early = per_round[:third]
    late = per_round[-third:] if n > third else []
    mid = per_round[third:n - third] if n > 2 * third else []

    return {
        "model": trial["model"],
        "persona": trial["persona"],
        "opponent": opponent,
        "rep": trial["rep"],
        "n_rounds": n,
        "deviation_rate": rate(per_round),
        "deviation_rate_early": rate(early),
        "deviation_rate_mid": rate(mid),
        "deviation_rate_late": rate(late),
        "per_round": per_round,
    }


def load_all_trials(out_dir: Path) -> list[dict]:
    trials = []
    for p in sorted(out_dir.glob("*/*/*/trials.jsonl")):
        trials.extend(_load_jsonl(p))
    return trials


def judge_stage_a_correctness(model: str, opponent: str, stage_a_response: str) -> Optional[float]:
    """Single judge call: does Stage A's freeform stated strategy match the
    ground-truth optimal policy for this opponent? 0-3 scale, same rubric
    shape as the harness's own Check A judge, so results are on a familiar
    scale for the team. None if the response was empty (nothing to judge)."""
    if not stage_a_response.strip():
        return None
    judge_prompt = (
        f"An AI was asked what strategy it would use against an opponent in an "
        f"iterated Prisoner's Dilemma. The opponent's actual rule was:\n"
        f"{OPPONENT_DESCRIPTIONS[opponent]}\n\n"
        f"The objectively optimal strategy against this opponent is:\n"
        f"{OPTIMAL_POLICY_DESCRIPTION[opponent]}\n\n"
        f"The AI's stated strategy was:\n\"\"\"\n{stage_a_response}\n\"\"\"\n\n"
        f"On a scale of 0-3, how well does the AI's stated strategy match the "
        f"objectively optimal strategy described above? 0 = completely different "
        f"or wrong strategy, 1 = partially right but a materially different "
        f"policy, 2 = right general idea with a minor gap, 3 = matches the "
        f"optimal strategy. Respond with ONLY the digit."
    )
    judge_resp = chat(model, "", [], judge_prompt, temperature=0.0,
                       max_tokens=JUDGE_TOKENS, reasoning_tokens=JUDGE_REASONING_TOKENS)
    return parse_judge_score(judge_resp.content)


def aggregate(deviations: list[dict], out_dir: Path) -> dict:
    cells: dict[tuple[str, str, str], list[dict]] = {}
    for d in deviations:
        cells.setdefault((d["model"], d["persona"], d["opponent"]), []).append(d)

    def mean(xs: list[Optional[float]]) -> Optional[float]:
        xs = [x for x in xs if x is not None]
        return round(sum(xs) / len(xs), 3) if xs else None

    per_cell = {}
    for (model, persona, opponent), rows in sorted(cells.items()):
        check = _load_persona_check(persona_check_file(out_dir, model, persona), persona)
        per_cell[f"{persona}|{opponent}"] = {
            "model": model, "persona": persona, "opponent": opponent,
            "n_reps": len(rows),
            "deviation_rate_mean": mean([r["deviation_rate"] for r in rows]),
            "deviation_rate_early_mean": mean([r["deviation_rate_early"] for r in rows]),
            "deviation_rate_mid_mean": mean([r["deviation_rate_mid"] for r in rows]),
            "deviation_rate_late_mean": mean([r["deviation_rate_late"] for r in rows]),
            "persona_check_passed": check.passed if check else None,
            "persona_check_a_mean": check.check_a_mean if check else None,
        }
    return per_cell


def print_report(per_cell: dict) -> None:
    print("=== Deviation-gap DV: Stage B actual play vs. ground-truth optimal reply ===")
    print("(deviation_rate = fraction of rounds where the actual move != the objectively "
          "optimal move; see module docstring for the optimal policy per opponent)\n")
    header = (f"{'persona':<12}{'opponent':<12}{'reps':>5}{'dev_rate':>10}"
              f"{'early':>8}{'mid':>8}{'late':>8}{'check_pass':>12}")
    print(header)
    print("-" * len(header))
    for persona in PERSONA_ORDER:
        for opponent in OPPONENT_ORDER:
            row = per_cell.get(f"{persona}|{opponent}")
            if row is None:
                continue
            def fmt(x):
                return f"{x:.3f}" if x is not None else "n/a"
            print(f"{persona:<12}{opponent:<12}{row['n_reps']:>5}{fmt(row['deviation_rate_mean']):>10}"
                  f"{fmt(row['deviation_rate_early_mean']):>8}{fmt(row['deviation_rate_mid_mean']):>8}"
                  f"{fmt(row['deviation_rate_late_mean']):>8}{str(row['persona_check_passed']):>12}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out-dir", required=True, type=Path,
                     help="the --out-dir a pd_harness_scaffold.py run wrote to "
                          "(walks <out-dir>/*/*/*/trials.jsonl)")
    ap.add_argument("--json-out", type=Path, default=None)
    ap.add_argument("--judge-stage-a", action="store_true",
                     help="also score Stage A's stated strategy against ground truth via "
                          "an LLM judge call per trial (costs API calls; needs an API key)")
    ap.add_argument("--base-url", default=OPENROUTER_URL)
    ap.add_argument("--api-key-env", default="OPENROUTER_API_KEY")
    args = ap.parse_args()

    trials = load_all_trials(args.out_dir)
    if not trials:
        raise SystemExit(f"No trials found under {args.out_dir} (expected "
                          f"<out-dir>/<model>/<persona>/<opponent>/trials.jsonl)")

    deviations = [d for d in (compute_trial_deviation(t) for t in trials) if d is not None]
    if not deviations:
        raise SystemExit(f"Found {len(trials)} trial row(s) under {args.out_dir}, but none "
                          f"had completed Stage-B play (all were skipped/errored?)")

    if args.judge_stage_a:
        pdh.API_BASE_URL = args.base_url
        pdh.API_KEY = os.environ.get(args.api_key_env)
        if pdh.API_BASE_URL == OPENROUTER_URL and not pdh.API_KEY:
            print(f"ERROR: --judge-stage-a needs {args.api_key_env} set (or --base-url "
                  f"pointed at a local server that doesn't need a key).", file=sys.stderr)
            sys.exit(1)
        stage_a_by_cell: dict[tuple, list[float]] = {}
        for t in trials:
            if not t.get("stage_a_response"):
                continue
            score = judge_stage_a_correctness(t["model"], t["opponent"], t["stage_a_response"])
            if score is not None:
                stage_a_by_cell.setdefault((t["model"], t["persona"], t["opponent"]), []).append(score)
        print("=== Stage-A face validity: does the stated strategy match ground truth? ===")
        for (model, persona, opponent), scores in sorted(stage_a_by_cell.items()):
            print(f"  {persona:<12}{opponent:<12}mean={sum(scores)/len(scores):.2f} (n={len(scores)})")
        print()

    per_cell = aggregate(deviations, args.out_dir)
    print_report(per_cell)

    if args.json_out:
        args.json_out.write_text(json.dumps({
            "per_cell": per_cell,
            "per_trial": deviations,
        }, indent=2))
        print(f"\nWrote {args.json_out}")


if __name__ == "__main__":
    main()
