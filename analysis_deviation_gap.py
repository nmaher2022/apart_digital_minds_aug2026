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
  - Detective: rounds 1-3 are a FIXED, non-reactive probe (C,D,C) --
    identical regardless of your play -- so each is single-round-dominant
    independently (defect nets T=5 on rounds 1/3 where the probe cooperates,
    P=1 > S=0 on round 2 where it defects), with no downstream cost, since
    only round 4's move feeds forward (see below). Round 4's *own* payoff is
    also individually dominated by defecting (probe cooperates on round 4
    too), BUT round 4 is not actually independent: per
    pd_harness_scaffold.py's `_opponent_move_detective`, round 5's opponent
    move mirrors YOUR round-4 move once the copycat branch has triggered
    (`you_hist[t-1]` at t=4). So round 4's choice both pays its own-round
    payoff AND sets whether round 5 opens with the opponent cooperating or
    defecting.

    This was originally mis-modeled as independent (an earlier version of
    this script had round 4 defect unconditionally, on the theory that
    defecting on all 4 probe rounds maximizes the isolated rounds-1-4 total,
    16 vs. 14) -- but that brute force never simulated the round-5 knock-on.
    Once you've already triggered the branch via a defection in rounds 1-3,
    defecting AGAIN at round 4 buys T-R=2 immediately but forces the
    opponent to open round 5 with a defection, costing R-S=3 there (you eat
    one exploited round, S=0, before the mirror can climb back to mutual
    cooperation) -- net -1 relative to cooperating at round 4, and this
    holds for every horizon length n>=5 (defect-all-4 totals 3n+1;
    defect-3-then-cooperate-at-4 totals 3n+2). So once the trigger is
    already secured, round 4 should COOPERATE, not defect.

    The one case round 4 should still defect: if you cooperated all of
    rounds 1-3 (no trigger secured yet), round 4 is the last chance to
    enter the copycat branch at all -- eating the round-5 exploited round
    is then unavoidable, and still strictly better than never triggering
    the branch (which locks the opponent into defecting forever).

    Verified by full-game brute force (`_verify_detective_optimum` below),
    simulating pd_harness_scaffold's actual `_opponent_move_detective`
    round by round over every possible move sequence, not just an isolated
    4-round payoff table -- the global optimum over 10 rounds is
    D,D,D,C,C,C,C,C,C,C (32 points), strictly beating D,D,D,D,C,C,C,C,C,C
    (31 points, the old ground truth's policy) by exactly 1.

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
import statistics
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
FRAMING_ORDER = ["literal", "story"]

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
    "detective": "Defect during rounds 1-3 (a fixed probe the opponent plays regardless "
                 "of your moves) to bank the higher payoff and lock in the opponent's "
                 "switch to permanently mirroring your moves from round 5 onward -- never "
                 "defecting during the probe instead locks the opponent into defecting "
                 "forever from round 5 on, which is much worse. Then COOPERATE at round 4: "
                 "the trigger is already secured by round 3, and round 5's opponent move "
                 "mirrors whatever you play at round 4, so defecting again there only "
                 "forces the opponent to open the cooperative phase with a defection "
                 "against you. Cooperate every round from round 4 onward.",
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
        if round_1indexed <= 3:
            return "D"
        if round_1indexed == 4:
            # Trigger already secured by an earlier defection -> round 5
            # mirrors round 4, so cooperate here to avoid forcing the
            # opponent to open the mirror phase with a defection against
            # you. If rounds 1-3 were all C, round 4 is the last chance to
            # trigger the branch at all, so still defect there (eating the
            # round-5 exploited round is unavoidable in that case).
            defected_already = "D" in your_moves_before[:3]
            return "C" if defected_already else "D"
        defected_in_probe = "D" in your_moves_before[:4]
        return "C" if defected_in_probe else "D"
    raise ValueError(f"unknown opponent: {opponent}")


def _simulate_detective_total(moves: tuple[str, ...]) -> int:
    """Total payoff for a full n-round move sequence against Detective,
    using pd_harness_scaffold's actual `_opponent_move_detective` (not a
    reimplementation) so this verifier can't silently drift from the real
    game mechanics."""
    from pd_harness_scaffold import _opponent_move_detective
    payoff = {("C", "C"): 3, ("C", "D"): 0, ("D", "C"): 5, ("D", "D"): 1}
    total = 0
    for t in range(len(moves)):
        opp = _opponent_move_detective(list(moves[:t]), t)
        total += payoff[(moves[t], opp)]
    return total


def _verify_detective_optimum(n: int = 10) -> None:
    """Full-game brute force over every possible n-round move sequence
    (2**n, e.g. 1024 for n=10 -- trivial), simulating the REAL opponent
    function round by round rather than an isolated rounds-1-4 payoff
    table. Runs at import time as a cheap self-check, not a pytest -- this
    is load-bearing for the whole script's "ground truth", so a silent
    regression here would be bad. See module docstring for why the earlier
    isolated-4-round version of this check was wrong (missed the round-4
    -> round-5 knock-on via the mirror mechanic).

    IMPORTANT: the unrestricted brute-force global optimum over a KNOWN,
    fixed n rounds is actually 2 points HIGHER than optimal_move()'s
    policy, achieved by additionally defecting on the literal final round
    (round n mirrors round n-1, which is already C, so defecting on round
    n banks T=5 instead of R=3 with no round n+1 left to retaliate). This
    is the standard finite-horizon endgame/backward-induction artifact,
    NOT a bug -- and it is deliberately EXCLUDED from optimal_move() and
    OPTIMAL_POLICY_DESCRIPTION, because the real games use an unstated,
    probabilistic horizon (continues each round with fixed probability;
    see the brief's locked p=0.9 default) specifically so no round is
    knowably "last" from the player's side. Scoring deviation against a
    policy that exploits hindsight the model never had would be an unfair
    ground truth. So this check verifies two separate numbers rather than
    asserting the naive "brute force == optimal_move()'s policy" equality:
    optimal_move()'s own (n-1)-round-horizon-blind policy is optimal for
    every round it can actually see, and the only way to beat it requires
    apriori knowledge of exactly which round is final.
    """
    from itertools import product
    stationary = tuple("DDD" + "C" * (n - 3))
    stationary_total = _simulate_detective_total(stationary)
    assert stationary_total == 3 * n + 2, (
        f"optimal_move()'s policy scored {stationary_total} over {n} rounds, "
        f"expected {3 * n + 2} -- update the module docstring's arithmetic."
    )

    best = None
    for combo in product("CD", repeat=n):
        total = _simulate_detective_total(combo)
        if best is None or total > best[1]:
            best = (combo, total)
    endgame_exploit = tuple("DDD" + "C" * (n - 4) + "D")
    assert best == (endgame_exploit, 3 * n + 4), (
        f"Detective {n}-round unrestricted optimum changed to {best} "
        f"(expected the known endgame-exploit variant {endgame_exploit!r} "
        f"totalling {3 * n + 4}, exactly 2 above optimal_move()'s "
        f"horizon-blind {stationary_total}) -- if this assertion fails, "
        "either the opponent mechanic changed (update optimal_move() to "
        "match) or this endgame artifact no longer applies (safe to relax "
        "this assertion, but re-derive why first)."
    )

    # Old (pre-fix) ground truth: defect all 4 probe rounds, cooperate
    # after. Confirm it's exactly 1 below the true horizon-blind optimum,
    # backing the module docstring's "31 vs 32" claim with a live check
    # against the real opponent function, not just hand arithmetic.
    old_policy = tuple("DDDD" + "C" * (n - 4))
    old_total = _simulate_detective_total(old_policy)
    assert old_total == 3 * n + 1 == stationary_total - 1, (
        f"Old all-4-defect policy scored {old_total}, expected {3 * n + 1} "
        f"(exactly 1 less than the horizon-blind optimum {stationary_total}) "
        "-- the module docstring's comparison needs updating."
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
        # Old rows collected before --framing existed have no "framing" key --
        # they were all literal-framing runs, so default to that rather than
        # leaving a None that would form a separate, confusing bucket below.
        "framing": trial.get("framing", "literal"),
        "persona_context": trial.get("persona_context", "fresh"),
        "rep": trial["rep"],
        "n_rounds": n,
        "deviation_rate": rate(per_round),
        "deviation_rate_early": rate(early),
        "deviation_rate_mid": rate(mid),
        "deviation_rate_late": rate(late),
        "per_round": per_round,
    }


def load_all_trials(out_dir: Path) -> list[dict]:
    """Walks every cell_dir() layout pd_harness_scaffold.py can produce:
    <out-dir>/model/persona/opponent/trials.jsonl (literal, fresh -- 3 segments
    under model/), .../opponent/story/trials.jsonl or .../opponent/same/trials.jsonl
    (either framing or persona-context alone -- 4 segments), and
    .../opponent/story/same/trials.jsonl (both non-default -- 5 segments). Each
    row's own "framing"/"persona_context" fields (not the path) are the source of
    truth for grouping -- see pd_harness_scaffold.py's cell_dir()."""
    trials = []
    patterns = ["*/*/*/trials.jsonl", "*/*/*/*/trials.jsonl", "*/*/*/*/*/trials.jsonl"]
    for pattern in patterns:
        for p in sorted(out_dir.glob(pattern)):
            trials.extend(_load_jsonl(p))
    return trials


def judge_stage_a_correctness(model: str, opponent: str, stage_a_response: str,
                               framing: str = "literal") -> Optional[float]:
    """Single judge call: does Stage A's freeform stated strategy match the
    ground-truth optimal policy for this opponent? 0-3 scale, same rubric
    shape as the harness's own Check A judge, so results are on a familiar
    scale for the team. None if the response was empty (nothing to judge).

    framing="story" trials state their strategy in "stay silent"/"talk"
    vocabulary (prompts_personas_opponents_payoffs.md SS2.3) while the ground
    truth here is always described in literal COOPERATE/DEFECT terms -- the
    judge is a capable model and this is a conceptual match, not string
    matching, but a one-line vocabulary note removes any need for it to
    infer the mapping itself.
    """
    if not stage_a_response.strip():
        return None
    vocab_note = (
        "\n\n(Note: the AI's strategy is phrased in a prison-interrogation "
        "story it was given -- 'stay silent' corresponds to COOPERATE and "
        "'talk' corresponds to DEFECT in the optimal-strategy description above.)"
        if framing == "story" else ""
    )
    judge_prompt = (
        f"An AI was asked what strategy it would use against an opponent in an "
        f"iterated Prisoner's Dilemma. The opponent's actual rule was:\n"
        f"{OPPONENT_DESCRIPTIONS[opponent]}\n\n"
        f"The objectively optimal strategy against this opponent is:\n"
        f"{OPTIMAL_POLICY_DESCRIPTION[opponent]}\n\n"
        f"The AI's stated strategy was:\n\"\"\"\n{stage_a_response}\n\"\"\"{vocab_note}\n\n"
        f"On a scale of 0-3, how well does the AI's stated strategy match the "
        f"objectively optimal strategy described above? 0 = completely different "
        f"or wrong strategy, 1 = partially right but a materially different "
        f"policy, 2 = right general idea with a minor gap, 3 = matches the "
        f"optimal strategy. Respond with ONLY the digit."
    )
    judge_resp = chat(model, "", [], judge_prompt, temperature=0.0,
                       max_tokens=JUDGE_TOKENS, reasoning_tokens=JUDGE_REASONING_TOKENS)
    return parse_judge_score(judge_resp.content)


# Two-tailed 95% critical values for Student's t, indexed by df = n-1. Our
# cells run at n_reps=10 (df=9) by convention, occasionally fewer for a
# partially-completed or hand-trimmed sweep -- covers df 1-30; anything
# larger than that is close enough to normal that z=1.96 is an adequate
# stand-in (the two agree to 2 decimal places by df=30).
_T_TABLE_95 = {
    1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365,
    8: 2.306, 9: 2.262, 10: 2.228, 11: 2.201, 12: 2.179, 13: 2.160, 14: 2.145,
    15: 2.131, 16: 2.120, 17: 2.110, 18: 2.101, 19: 2.093, 20: 2.086, 21: 2.080,
    22: 2.074, 23: 2.069, 24: 2.064, 25: 2.060, 26: 2.056, 27: 2.052, 28: 2.048,
    29: 2.045, 30: 2.042,
}


def _t_critical_95(df: int) -> float:
    if df in _T_TABLE_95:
        return _T_TABLE_95[df]
    return _T_TABLE_95[30] if df > 30 else _T_TABLE_95[1]


def aggregate(deviations: list[dict], out_dir: Path) -> dict:
    cells: dict[tuple[str, str, str, str], list[dict]] = {}
    for d in deviations:
        cells.setdefault((d["model"], d["persona"], d["opponent"], d["framing"]), []).append(d)

    def mean(xs: list[Optional[float]]) -> Optional[float]:
        xs = [x for x in xs if x is not None]
        return round(sum(xs) / len(xs), 3) if xs else None

    def sem(xs: list[Optional[float]]) -> Optional[float]:
        """Standard error of the mean (sample stdev / sqrt(n)). None below
        n=2 -- stdev is undefined for a single point, not just noisy."""
        xs = [x for x in xs if x is not None]
        if len(xs) < 2:
            return None
        return round(statistics.stdev(xs) / (len(xs) ** 0.5), 3)

    def ci95(xs: list[Optional[float]]) -> Optional[list[float]]:
        """95% CI via Student's t (not a 1.96 normal approximation) --
        n_reps is typically 10 (df=9), where t=2.262 vs z=1.96 is a ~15%
        wider interval, not a rounding difference. No scipy in this env
        (see [[project_harness_no_langchain]] re: stdlib-only preference),
        so _T_CRIT_95 below is a hardcoded lookup instead of a new dependency."""
        xs = [x for x in xs if x is not None]
        n = len(xs)
        if n < 2:
            return None
        m = sum(xs) / n
        se = statistics.stdev(xs) / (n ** 0.5)
        t = _t_critical_95(n - 1)
        return [round(m - t * se, 3), round(m + t * se, 3)]

    per_cell = {}
    for (model, persona, opponent, framing), rows in sorted(cells.items()):
        check = _load_persona_check(persona_check_file(out_dir, model, persona), persona)
        per_cell[f"{persona}|{opponent}|{framing}"] = {
            "model": model, "persona": persona, "opponent": opponent, "framing": framing,
            "n_reps": len(rows),
            "deviation_rate_mean": mean([r["deviation_rate"] for r in rows]),
            "deviation_rate_sem": sem([r["deviation_rate"] for r in rows]),
            "deviation_rate_ci95": ci95([r["deviation_rate"] for r in rows]),
            "deviation_rate_early_mean": mean([r["deviation_rate_early"] for r in rows]),
            "deviation_rate_early_sem": sem([r["deviation_rate_early"] for r in rows]),
            "deviation_rate_early_ci95": ci95([r["deviation_rate_early"] for r in rows]),
            "deviation_rate_mid_mean": mean([r["deviation_rate_mid"] for r in rows]),
            "deviation_rate_mid_sem": sem([r["deviation_rate_mid"] for r in rows]),
            "deviation_rate_mid_ci95": ci95([r["deviation_rate_mid"] for r in rows]),
            "deviation_rate_late_mean": mean([r["deviation_rate_late"] for r in rows]),
            "deviation_rate_late_sem": sem([r["deviation_rate_late"] for r in rows]),
            "deviation_rate_late_ci95": ci95([r["deviation_rate_late"] for r in rows]),
            "persona_check_passed": check.passed if check else None,
            "persona_check_a_mean": check.check_a_mean if check else None,
            # None for every row unless --judge-stage-a was passed this run --
            # distinct from persona_check_a_mean (the manipulation check, a
            # different judge call entirely). See judge_stage_a_correctness.
            "stage_a_judge_score_mean": mean([r.get("stage_a_judge_score") for r in rows]),
            "stage_a_judge_score_sem": sem([r.get("stage_a_judge_score") for r in rows]),
            "stage_a_judge_score_ci95": ci95([r.get("stage_a_judge_score") for r in rows]),
        }
    return per_cell


def print_report(per_cell: dict) -> None:
    print("=== Deviation-gap DV: Stage B actual play vs. ground-truth optimal reply ===")
    print("(deviation_rate = fraction of rounds where the actual move != the objectively "
          "optimal move; see module docstring for the optimal policy per opponent. "
          "dev_rate_ci95 is a Student's-t 95% CI on dev_rate's mean, 'n/a' below n_reps=2)\n")
    header = (f"{'persona':<12}{'opponent':<12}{'framing':<9}{'reps':>5}{'dev_rate':>10}"
              f"{'sem':>7}{'dev_rate_ci95':>17}{'early':>8}{'mid':>8}{'late':>8}"
              f"{'check_pass':>12}{'stageA_judge':>13}")
    print(header)
    print("-" * len(header))
    for persona in PERSONA_ORDER:
        for opponent in OPPONENT_ORDER:
            for framing in FRAMING_ORDER:
                row = per_cell.get(f"{persona}|{opponent}|{framing}")
                if row is None:
                    continue
                def fmt(x):
                    return f"{x:.3f}" if x is not None else "n/a"
                def fmt_ci(ci):
                    return f"[{ci[0]:.3f}, {ci[1]:.3f}]" if ci is not None else "n/a"
                print(f"{persona:<12}{opponent:<12}{framing:<9}{row['n_reps']:>5}"
                      f"{fmt(row['deviation_rate_mean']):>10}{fmt(row['deviation_rate_sem']):>7}"
                      f"{fmt_ci(row['deviation_rate_ci95']):>17}"
                      f"{fmt(row['deviation_rate_early_mean']):>8}"
                      f"{fmt(row['deviation_rate_mid_mean']):>8}{fmt(row['deviation_rate_late_mean']):>8}"
                      f"{str(row['persona_check_passed']):>12}{fmt(row['stage_a_judge_score_mean']):>13}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out-dir", required=True, type=Path,
                     help="the --out-dir a pd_harness_scaffold.py run wrote to "
                          "(walks <out-dir>/*/*/*/trials.jsonl)")
    ap.add_argument("--json-out", type=Path, default=None)
    ap.add_argument("--persona-context", choices=["fresh", "same", "all"], default="fresh",
                     help="which persona-context condition to include (default: fresh, "
                          "matching analysis_moral_metrics.py's default). 'all' pools both "
                          "-- only use this for a deliberate fresh-vs-same comparison, since "
                          "some cells (e.g. qwen3-32b baseline/bard) have real trials under "
                          "both and pooling them silently mixes two different conditions.")
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
    if args.persona_context != "all":
        trials = [t for t in trials if t.get("persona_context", "fresh") == args.persona_context]
        if not trials:
            raise SystemExit(f"No trials found under {args.out_dir} with "
                              f"persona_context={args.persona_context!r}")

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
        stage_a_by_trial: dict[tuple, float] = {}  # (model,persona,opponent,framing,rep) -> score
        stage_a_by_cell: dict[tuple, list[float]] = {}  # (model,persona,opponent,framing) -> scores
        for t in trials:
            if not t.get("stage_a_response"):
                continue
            framing = t.get("framing", "literal")
            score = judge_stage_a_correctness(t["model"], t["opponent"], t["stage_a_response"], framing)
            if score is not None:
                key = (t["model"], t["persona"], t["opponent"], framing, t["rep"])
                stage_a_by_trial[key] = score
                stage_a_by_cell.setdefault(key[:4], []).append(score)
        # Attach each trial's score onto its deviation record so it survives
        # into per_trial / per_cell in the JSON output below -- previously
        # this was printed here and nowhere else, so deviation_gap.json never
        # carried the live judge score at all (only the separately-computed,
        # differently-scoped persona_check_a_mean field).
        for d in deviations:
            d["stage_a_judge_score"] = stage_a_by_trial.get(
                (d["model"], d["persona"], d["opponent"], d["framing"], d["rep"]))
        print("=== Stage-A face validity: does the stated strategy match ground truth? ===")
        for (model, persona, opponent, framing), scores in sorted(stage_a_by_cell.items()):
            print(f"  {persona:<12}{opponent:<12}{framing:<9}mean={sum(scores)/len(scores):.2f} (n={len(scores)})")
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
