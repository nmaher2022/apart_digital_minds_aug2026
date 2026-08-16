#!/usr/bin/env python3
"""
analysis_moral_metrics.py -- Eigenjesus/eigenmoses-lite scoring for PD trial data.

Adapts Singer-Clark (2014), "Morality Metrics On Iterated Prisoner's Dilemma
Players" (morality.pdf) -- eigenjesus and eigenmoses are PageRank-style
recursive morality scores computed on a full round-robin cooperation matrix
of an IPD tournament. This project's design is NOT round-robin: personas
never play each other, opponents never play each other, and every
persona-opponent pair is played in an independently-installed context (see
HANDOFF.md 2026-08-13, "Fresh vs. shared persona context"). So this is an
adapted, bipartite version of the metric, not a literal replication of the
paper's whole-tournament eigenvector.

Method (self-contained, no external tuning): build a 9-node cooperation
matrix -- 5 personas + 4 fixed opponents. The persona->opponent edge is that
persona's measured cooperation rate against that opponent, pooled over every
round of every rep (`rounds[].your_move` in trials.jsonl). The opponent->
persona edge is that opponent's measured cooperation rate *toward* the
persona over the same rounds (`rounds[].opponent_move` -- already logged by
the harness, not re-simulated). Persona-persona and opponent-opponent cells
are 0 (no such games exist in this design; diagonal is 0 too). eigenjesus_lite
is the dominant eigenvector of this C in [0,1]^9x9 (Singer-Clark SS3.3);
eigenmoses_lite is the dominant eigenvector of D = 2*(C - 0.5), restricted to
the same nonzero support (SS3.4). Both are L2-normalized and scaled by
sqrt(9) so a uniform all-cooperate matrix lands near order-1 entries, loosely
comparable in *shape* to Table 1's published values -- this is not the same
normalization the paper used and the absolute numbers are not commensurate
with it; only the within-run ranking (which persona/opponent scores higher
than which) is meaningful here.

Separately, each opponent's own published Singer-Clark rating is printed for
context, since 3 of our 4 fixed opponents are literal matches to bots in that
paper's 20-bot roster -- and that tournament used the identical payoffs
(T=5, R=3, P=1, S=0) as this project's Appendix B:
    Cooperator = ALL C, Cheater = ALL D, Copycat = TIT FOR TAT.
Detective has no exact match; TESTER (defects to probe, then reciprocates if
retaliated against or alternates C/D to exploit if not) is the closest
structural analog -- flagged as approximate, never asserted as equivalent.

Usage:
    python3 analysis_moral_metrics.py runs/qwen3-32b/trials.jsonl
    python3 analysis_moral_metrics.py runs/qwen3-32b/trials.jsonl \\
        --json-out runs/qwen3-32b/moral_metrics.json
"""

from __future__ import annotations

import argparse
import json
import math
import random
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Optional

import numpy as np

PERSONA_ORDER = ["baseline", "consultant", "saboteur", "altruist", "bard"]
OPPONENT_ORDER = ["cooperator", "cheater", "copycat", "detective"]
NODE_ORDER = PERSONA_ORDER + OPPONENT_ORDER

# Singer-Clark (2014) Table 1, same T=5/R=3/P=1/S=0 payoffs as this project's
# Appendix B. approximate=True means the mapping to our opponent is a
# structural analog, not the same bot.
ANCHOR_RATINGS = {
    "cooperator": {"source_bot": "ALL C", "eigenjesus": 1.377, "eigenmoses": 1.481, "approximate": False},
    "cheater": {"source_bot": "ALL D", "eigenjesus": 0.000, "eigenmoses": -1.481, "approximate": False},
    "copycat": {"source_bot": "TIT FOR TAT", "eigenjesus": 1.222, "eigenmoses": 1.747, "approximate": False},
    "detective": {"source_bot": "TESTER", "eigenjesus": 0.887, "eigenmoses": 0.768, "approximate": True},
}


def load_trials(path: Path) -> list[dict]:
    """Accepts either a single flat trials.jsonl (old layout) or an --out-dir
    from pd_harness_scaffold.py's per-cell layout (<out-dir>/<model>/<persona>/
    <opponent>/trials.jsonl) -- a directory is globbed for every cell's file."""
    if path.is_dir():
        # 3-level: literal-framing, fresh-context cells (pd_harness_scaffold.py's
        # cell_dir() default). 4-level: story-framing OR literal+same-context
        # cells (their own subdirectory). 5-level: story+same-context cells
        # (framing dir AND persona-context dir both present).
        jsonl_paths = (
            sorted(path.glob("*/*/*/trials.jsonl"))
            + sorted(path.glob("*/*/*/*/trials.jsonl"))
            + sorted(path.glob("*/*/*/*/*/trials.jsonl"))
        )
    else:
        jsonl_paths = [path]
    trials = []
    for jsonl_path in jsonl_paths:
        with open(jsonl_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                if row.get("stage_b_skipped") or "rounds" not in row:
                    continue
                trials.append(row)
    return trials


def pooled_cooperation_rates(trials: list[dict]) -> dict[tuple[str, str], tuple[int, int]]:
    """Returns {(persona, opponent): (persona_c_count, n_rounds)} and, under
    the reversed key (opponent, persona), (opponent_c_count, n_rounds) --
    pooled across every rep and round for that cell.
    """
    counts: dict[tuple[str, str], list[int]] = {}
    for t in trials:
        persona, opponent = t["persona"], t["opponent"]
        pk = (persona, opponent)
        ok = (opponent, persona)
        for r in t["rounds"]:
            counts.setdefault(pk, [0, 0])
            counts.setdefault(ok, [0, 0])
            counts[pk][1] += 1
            counts[ok][1] += 1
            if r["your_move"] == "C":
                counts[pk][0] += 1
            if r["opponent_move"] == "C":
                counts[ok][0] += 1
    return {k: (v[0], v[1]) for k, v in counts.items()}


def wilson_ci(c_count: int, total: int, z: float = 1.96) -> Optional[tuple[float, float]]:
    """95% Wilson score interval for a binomial proportion (z=1.96). Preferred
    over mean +/- z*sqrt(p(1-p)/n) here because our per-edge rates are often
    at or near 0/1 (e.g. a persona that always cooperates against Cooperator)
    where the plain Wald interval can be degenerate (width 0 at p=0 or p=1,
    which understates uncertainty) or extend outside [0,1]; Wilson stays
    inside [0,1] and doesn't collapse at the boundary. None if total==0."""
    if total == 0:
        return None
    p = c_count / total
    denom = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denom
    half = (z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total))) / denom
    return (max(0.0, center - half), min(1.0, center + half))


def wald_sem(c_count: int, total: int) -> Optional[float]:
    """sqrt(p(1-p)/n) -- the simple companion SEM to sit next to wilson_ci's
    CI (which does the boundary-safe work; this is just the point estimate's
    SEM, reported since [[feedback_stats_required]] asks for both alongside
    every mean, not only a CI)."""
    if total == 0:
        return None
    p = c_count / total
    return round(math.sqrt(p * (1 - p) / total), 4)


def build_cooperation_matrix(rates: dict[tuple[str, str], tuple[int, int]]) -> tuple[np.ndarray, np.ndarray]:
    """Returns (C, observed) -- both len(NODE_ORDER) x len(NODE_ORDER).
    C[i][j] = node i's cooperation rate toward node j (0 if never observed).
    observed[i][j] = number of pooled rounds behind that entry.
    """
    n = len(NODE_ORDER)
    idx = {name: i for i, name in enumerate(NODE_ORDER)}
    C = np.zeros((n, n))
    observed = np.zeros((n, n), dtype=int)
    for (a, b), (c_count, total) in rates.items():
        if a not in idx or b not in idx:
            continue
        C[idx[a]][idx[b]] = c_count / total if total else 0.0
        observed[idx[a]][idx[b]] = total
    return C, observed


def dominant_eigenvector(M: np.ndarray) -> np.ndarray:
    """Real part of the eigenvector for the eigenvalue of largest REAL part
    (the Perron root, not largest magnitude) -- our persona/opponent split
    makes this matrix bipartite (edges only cross the two parts), and
    bipartite non-negative matrices generically have a -lambda eigenvalue
    matching every +lambda one, with an alternating-sign eigenvector on the
    -lambda side. Picking by magnitude can grab that -lambda pair and hand
    back a "moral score" that's negative for every opponent node purely as a
    sign artifact -- picking by real part always lands on the true Perron
    root, whose eigenvector Perron-Frobenius guarantees is entrywise
    non-negative (for the non-negative C matrix; not guaranteed for the
    signed D matrix, but still the right analogous choice -- see docstring).
    Result is L2-normalized and scaled by sqrt(n) (see module docstring for
    why), sign fixed so it points the same way as the matrix's raw row sums
    (the natural "more cooperative = more positive" reference direction).
    """
    n = M.shape[0]
    eigvals, eigvecs = np.linalg.eig(M)
    top = np.argmax(np.real(eigvals))
    vec = np.real(eigvecs[:, top])
    row_sums = M.sum(axis=1)
    if np.dot(vec, row_sums) < 0:
        vec = -vec
    norm = np.linalg.norm(vec)
    if norm == 0:
        return vec
    return vec / norm * math.sqrt(n)


def _percentile(xs: list[float], pct: float) -> float:
    """Linear-interpolation percentile (xs need not be pre-sorted)."""
    s = sorted(xs)
    if len(s) == 1:
        return s[0]
    k = (len(s) - 1) * (pct / 100)
    lo, hi = math.floor(k), math.ceil(k)
    if lo == hi:
        return s[int(k)]
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def bootstrap_eigen_scores(trials: list[dict], n_boot: int = 500,
                            seed: int = 12345) -> dict[str, dict[str, tuple[float, tuple[float, float]]]]:
    """Nonparametric bootstrap CI for eigenjesus_lite/eigenmoses_lite.

    These are a nonlinear (eigenvector) function of the whole pooled
    cooperation matrix, so there's no closed-form SEM the way there is for a
    simple mean -- resample reps with replacement per (persona,opponent) cell
    (keeps each cell's own n_reps fixed, matching how the actual data was
    collected: independently-installed persona per opponent per rep), rebuild
    the matrix and recompute both eigenvectors each draw, and take the
    empirical spread across draws. Returns
    {node: {"eigenjesus_lite": (sem, (lo, hi)), "eigenmoses_lite": (sem, (lo, hi))}}.
    """
    if n_boot == 0:
        return {name: {"eigenjesus_lite": (None, (None, None)),
                        "eigenmoses_lite": (None, (None, None))} for name in NODE_ORDER}

    by_pair: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for t in trials:
        by_pair[(t["persona"], t["opponent"])].append(t)

    rng = random.Random(seed)
    draws_ej = {name: [] for name in NODE_ORDER}
    draws_em = {name: [] for name in NODE_ORDER}
    for _ in range(n_boot):
        resampled = []
        for pair_trials in by_pair.values():
            resampled.extend(rng.choices(pair_trials, k=len(pair_trials)))
        rates = pooled_cooperation_rates(resampled)
        C, observed = build_cooperation_matrix(rates)
        D = 2 * (C - 0.5)
        D[observed == 0] = 0.0
        ej = dominant_eigenvector(C)
        em = dominant_eigenvector(D)
        for i, name in enumerate(NODE_ORDER):
            draws_ej[name].append(float(ej[i]))
            draws_em[name].append(float(em[i]))

    out = {}
    for name in NODE_ORDER:
        out[name] = {
            "eigenjesus_lite": (round(statistics.stdev(draws_ej[name]), 3),
                                (round(_percentile(draws_ej[name], 2.5), 3),
                                 round(_percentile(draws_ej[name], 97.5), 3))),
            "eigenmoses_lite": (round(statistics.stdev(draws_em[name]), 3),
                                (round(_percentile(draws_em[name], 2.5), 3),
                                 round(_percentile(draws_em[name], 97.5), 3))),
        }
    return out


def compute_moral_metrics(trials: list[dict], n_boot: int = 500, boot_seed: int = 12345) -> dict:
    rates = pooled_cooperation_rates(trials)
    C, observed = build_cooperation_matrix(rates)
    D = 2 * (C - 0.5)
    D[observed == 0] = 0.0  # unobserved cells contribute nothing, not -1

    eigenjesus = dominant_eigenvector(C)
    eigenmoses = dominant_eigenvector(D)
    boot = bootstrap_eigen_scores(trials, n_boot=n_boot, seed=boot_seed)

    per_node = {}
    for i, name in enumerate(NODE_ORDER):
        ej_sem, ej_ci = boot[name]["eigenjesus_lite"]
        em_sem, em_ci = boot[name]["eigenmoses_lite"]
        per_node[name] = {
            "eigenjesus_lite": round(float(eigenjesus[i]), 3),
            "eigenjesus_lite_sem": ej_sem,
            "eigenjesus_lite_ci95": list(ej_ci) if ej_ci[0] is not None else None,
            "eigenmoses_lite": round(float(eigenmoses[i]), 3),
            "eigenmoses_lite_sem": em_sem,
            "eigenmoses_lite_ci95": list(em_ci) if em_ci[0] is not None else None,
            "kind": "persona" if name in PERSONA_ORDER else "opponent",
        }

    unobserved_cells = [
        (NODE_ORDER[i], NODE_ORDER[j])
        for i in range(len(NODE_ORDER))
        for j in range(len(NODE_ORDER))
        if observed[i][j] == 0
        and NODE_ORDER[i] in PERSONA_ORDER and NODE_ORDER[j] in OPPONENT_ORDER
    ]

    edge_rates = {}
    for (a, b), (c_count, total) in sorted(rates.items()):
        ci = wilson_ci(c_count, total)
        edge_rates[f"{a}->{b}"] = {
            "rate": round(c_count / total, 3) if total else None,
            "n_rounds": total,
            "sem": wald_sem(c_count, total),
            "ci95": list(ci) if ci else None,
        }

    return {
        "per_node": per_node,
        "edge_rates": edge_rates,
        "bootstrap_n": n_boot,
        "unobserved_persona_opponent_cells": unobserved_cells,
        "anchor_comparison": ANCHOR_RATINGS,
    }


def print_report(metrics: dict) -> None:
    print("=== eigenjesus_lite / eigenmoses_lite (this run) ===")
    print("(adapted bipartite metric -- see module docstring; ranking is meaningful, absolute scale "
          f"is not. sem/ci95 are a {metrics['bootstrap_n']}-draw nonparametric bootstrap over reps, "
          "since these scores are a nonlinear function of the cooperation matrix with no closed-form SEM)\n")
    header = (f"{'node':<12}{'kind':<10}{'eigenjesus':>11}{'sem':>7}{'ci95':>17}"
              f"{'eigenmoses':>11}{'sem':>7}{'ci95':>17}")
    print(header)
    print("-" * len(header))
    def fmt_ci(ci):
        return f"[{ci[0]:.3f}, {ci[1]:.3f}]" if ci is not None else "n/a"
    def fmt_sem(x):
        return f"{x:.3f}" if x is not None else "n/a"
    for name in NODE_ORDER:
        row = metrics["per_node"][name]
        print(f"{name:<12}{row['kind']:<10}{row['eigenjesus_lite']:>11}{fmt_sem(row['eigenjesus_lite_sem']):>7}"
              f"{fmt_ci(row['eigenjesus_lite_ci95']):>17}{row['eigenmoses_lite']:>11}"
              f"{fmt_sem(row['eigenmoses_lite_sem']):>7}{fmt_ci(row['eigenmoses_lite_ci95']):>17}")

    if metrics["unobserved_persona_opponent_cells"]:
        print("\nWARNING -- these persona x opponent cells had zero observed rounds "
              "(ratings above are computed as if they never interacted, not as if they defected):")
        for p, o in metrics["unobserved_persona_opponent_cells"]:
            print(f"  {p} x {o}")

    print("\n=== per-edge cooperation rates (rate = fraction of pooled rounds that node played C) ===")
    print("(sem = Wald SE sqrt(p(1-p)/n); ci95 = Wilson score interval, stays inside [0,1] unlike "
          "a plain normal-approx interval when p is near 0 or 1)")
    edge_header = f"{'edge':<24}{'rate':>7}{'n':>6}{'sem':>8}{'ci95':>17}"
    print(edge_header)
    print("-" * len(edge_header))
    for edge, row in metrics["edge_rates"].items():
        rate_s = f"{row['rate']:.3f}" if row["rate"] is not None else "n/a"
        sem_s = f"{row['sem']:.4f}" if row["sem"] is not None else "n/a"
        ci_s = f"[{row['ci95'][0]:.3f}, {row['ci95'][1]:.3f}]" if row["ci95"] else "n/a"
        print(f"{edge:<24}{rate_s:>7}{row['n_rounds']:>6}{sem_s:>8}{ci_s:>17}")

    print("\n=== Singer-Clark (2014) published anchor ratings, same payoffs (T=5,R=3,P=1,S=0) ===")
    print(f"{'opponent':<12}{'source_bot':<14}{'eigenjesus':>12}{'eigenmoses':>12}  approximate?")
    for opp, row in ANCHOR_RATINGS.items():
        print(f"{opp:<12}{row['source_bot']:<14}{row['eigenjesus']:>12}{row['eigenmoses']:>12}  {row['approximate']}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("trials_jsonl", type=Path,
                     help="a single trials.jsonl, OR an --out-dir from pd_harness_scaffold.py "
                          "(per-cell layout is globbed automatically)")
    ap.add_argument("--json-out", type=Path, default=None)
    ap.add_argument("--framing", choices=["literal", "story"], default="literal",
                     help="which framing's trials to include (default: literal). This "
                          "script pools rounds by (persona,opponent) only -- if an --out-dir "
                          "has both framings' trials.jsonl on disk, mixing them into one "
                          "cooperation-rate estimate would silently conflate two different "
                          "conditions, so exactly one framing is selected per run instead.")
    ap.add_argument("--persona-context", choices=["fresh", "same", "all"], default="fresh",
                     help="which persona-installation condition to include (default: fresh, "
                          "the locked core-spine condition -- see steps.md / preregistration.md: "
                          "persona is independently reinstalled per opponent per rep). Trials "
                          "written before persona_context was tracked have no such field and "
                          "count as 'fresh'. 'same' selects the chained/shared-context stretch "
                          "condition; 'all' pools both, which conflates two different conditions "
                          "and should only be used deliberately.")
    ap.add_argument("--n-boot", type=int, default=500,
                     help="bootstrap draws for eigenjesus_lite/eigenmoses_lite CIs (default: 500). "
                          "Set to 0 to skip bootstrapping (per_node scores still computed, "
                          "sem/ci95 fields become None) -- useful for a fast iteration loop.")
    ap.add_argument("--boot-seed", type=int, default=12345,
                     help="RNG seed for the bootstrap resample, for reproducible CIs (default: 12345)")
    args = ap.parse_args()

    trials = load_trials(args.trials_jsonl)
    trials = [t for t in trials if t.get("framing", "literal") == args.framing]
    if args.persona_context != "all":
        trials = [t for t in trials if t.get("persona_context", "fresh") == args.persona_context]
    if not trials:
        raise SystemExit(f"No completed Stage-B trials found in {args.trials_jsonl} for "
                          f"framing={args.framing} persona_context={args.persona_context}")

    metrics = compute_moral_metrics(trials, n_boot=args.n_boot, boot_seed=args.boot_seed)
    print_report(metrics)

    if args.json_out:
        args.json_out.write_text(json.dumps(metrics, indent=2))
        print(f"\nWrote {args.json_out}")


if __name__ == "__main__":
    main()
