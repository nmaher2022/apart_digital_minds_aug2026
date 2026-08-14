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
from pathlib import Path

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
    trials = []
    with open(path) as f:
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


def compute_moral_metrics(trials: list[dict]) -> dict:
    rates = pooled_cooperation_rates(trials)
    C, observed = build_cooperation_matrix(rates)
    D = 2 * (C - 0.5)
    D[observed == 0] = 0.0  # unobserved cells contribute nothing, not -1

    eigenjesus = dominant_eigenvector(C)
    eigenmoses = dominant_eigenvector(D)

    per_node = {}
    for i, name in enumerate(NODE_ORDER):
        per_node[name] = {
            "eigenjesus_lite": round(float(eigenjesus[i]), 3),
            "eigenmoses_lite": round(float(eigenmoses[i]), 3),
            "kind": "persona" if name in PERSONA_ORDER else "opponent",
        }

    unobserved_cells = [
        (NODE_ORDER[i], NODE_ORDER[j])
        for i in range(len(NODE_ORDER))
        for j in range(len(NODE_ORDER))
        if observed[i][j] == 0
        and NODE_ORDER[i] in PERSONA_ORDER and NODE_ORDER[j] in OPPONENT_ORDER
    ]

    return {
        "per_node": per_node,
        "unobserved_persona_opponent_cells": unobserved_cells,
        "anchor_comparison": ANCHOR_RATINGS,
    }


def print_report(metrics: dict) -> None:
    print("=== eigenjesus_lite / eigenmoses_lite (this run) ===")
    print("(adapted bipartite metric -- see module docstring; ranking is meaningful, absolute scale is not)\n")
    header = f"{'node':<12}{'kind':<10}{'eigenjesus_lite':>16}{'eigenmoses_lite':>16}"
    print(header)
    print("-" * len(header))
    for name in NODE_ORDER:
        row = metrics["per_node"][name]
        print(f"{name:<12}{row['kind']:<10}{row['eigenjesus_lite']:>16}{row['eigenmoses_lite']:>16}")

    if metrics["unobserved_persona_opponent_cells"]:
        print("\nWARNING -- these persona x opponent cells had zero observed rounds "
              "(ratings above are computed as if they never interacted, not as if they defected):")
        for p, o in metrics["unobserved_persona_opponent_cells"]:
            print(f"  {p} x {o}")

    print("\n=== Singer-Clark (2014) published anchor ratings, same payoffs (T=5,R=3,P=1,S=0) ===")
    print(f"{'opponent':<12}{'source_bot':<14}{'eigenjesus':>12}{'eigenmoses':>12}  approximate?")
    for opp, row in ANCHOR_RATINGS.items():
        print(f"{opp:<12}{row['source_bot']:<14}{row['eigenjesus']:>12}{row['eigenmoses']:>12}  {row['approximate']}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("trials_jsonl", type=Path)
    ap.add_argument("--json-out", type=Path, default=None)
    args = ap.parse_args()

    trials = load_trials(args.trials_jsonl)
    if not trials:
        raise SystemExit(f"No completed Stage-B trials found in {args.trials_jsonl}")

    metrics = compute_moral_metrics(trials)
    print_report(metrics)

    if args.json_out:
        args.json_out.write_text(json.dumps(metrics, indent=2))
        print(f"\nWrote {args.json_out}")


if __name__ == "__main__":
    main()
