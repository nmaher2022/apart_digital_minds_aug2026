#!/usr/bin/env python3
"""
analysis_significance.py -- formal significance tests on top of the
already-computed SEM/95% CI machinery in analysis_deviation_gap.py,
analysis_eval_awareness.py, and analysis_cross_persona_injection.py.

Those three scripts report a mean + SEM + 95% CI for every point estimate,
per [[feedback_stats_required]], but report_draft.md's Limitations section
correctly flagged that CI non-overlap is not a real significance test. This
script adds the actual tests, chosen per-claim to match the real unit of
independence and pairing structure in the data (see each section below for
why that test and not another). No scipy in this project's .venv (see
[[project_harness_no_langchain]]'s stdlib-only precedent) -- every test here
is closed-form or exact-combinatorial using only stdlib (math.comb, math.erf)
plus the numpy/statistics already used elsewhere in this repo.

Four claims get a real test:

1. **Altruist vs. Baseline deviation rate, per model** (backs report_draft.md
   Table in SS4.1 / SS5.1's headline claim). Unit of analysis is the TRIAL
   (one full game = one deviation_rate number), not the round -- rounds
   within a trial are not independent (Figure 2's worked example shows one
   persona-driven switch that then holds for the rest of the game), but
   analysis_deviation_gap.py already aggregates at the trial level, so this
   is just reusing that unit correctly. n=40 trials/persona/model (4
   opponents x 10 reps, literal framing, same-context -- exactly the cells
   Table 4.1 reports). Test: **exact (or Monte Carlo, if too large to
   enumerate) permutation test on the difference in mean per-trial deviation
   rate.** No distributional assumption needed, and exact enumeration is
   feasible at this n (C(80,40) is large, so this falls back to Monte
   Carlo in practice -- see permutation_test_diff_means's docstring).

2. **"Altruist causes more deviation than Baseline on every model tested"**
   (report_draft.md SS4.1's headline sentence). The real independent unit
   for a replicates-across-models claim is the MODEL (n=5), not the pooled
   trials -- each model is one independent architecture/training run, and
   the claim is about direction of effect, not magnitude. Test: **exact
   sign test** (binomial, p=0.5) on the 5 model-level altruist-minus-baseline
   signs, one-sided since the direction was preregistered
   (preregistration.md SS4, prediction #1).

3. **Matched vs. mismatched persona hold-rate, and mid-vs-end within each**
   (report_draft.md SS4.4/SS5.4). Matched-vs-mismatched is two independent
   groups of trials (~110-120 each) -- standard **two-proportion z-test**.
   Mid-vs-end is NOT independent groups -- it's the same trial's persona
   hold status probed twice, so it's a **paired** binary comparison, and the
   textbook-correct test for that is **McNemar's test** (here: exact
   binomial on the discordant pairs, since n is small enough that the exact
   test is preferable to the chi-square approximation).

4. **Eval-awareness point-biserial r ~= 0** (report_draft.md SS4.3/SS4.4).
   Already has a Fisher-z 95% CI (point_biserial_ci95 in
   analysis_eval_awareness.py); this just runs the equivalent explicit
   hypothesis test (H0: r=0) via the same Fisher-z machinery, so the p-value
   and the existing CI are guaranteed consistent with each other (CI
   excludes 0 iff p<.05).

None of this corrects for multiple comparisons across the many
persona x opponent x model cells -- see the printed caveat and
report_draft.md's Limitations for why that's flagged as a real gap, not
silently ignored.

Usage:
    python3 analysis_significance.py
    python3 analysis_significance.py --json-out analysis_output/significance.json
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
import random
import statistics
from pathlib import Path
from typing import Optional

from analysis_deviation_gap import load_all_trials, compute_trial_deviation
from analysis_cross_persona_injection import (
    load_all_trials as load_cpi_trials,
    compute_trial_degradation,
)
from analysis_eval_awareness import (
    build_rows as build_ea_rows,
    aggregate as aggregate_ea,
)

MAIN_SWEEP_MODELS = {
    "llama-3.3-70b": "runs/llama-3.3-70b",
    "gemini-2.5-flash": "runs/gemini-2.5-flash",
    "qwen3-32b": "runs/qwen3-32b",
    "qwen3-8b": "runs/qwen3-8b",
    "qwen3.8-27b": "runs/qwen3.8-27b",
}
CPI_DIR = "runs/runs_cross_persona_injection"


# ---------------------------------------------------------------------------
# Generic stat primitives (stdlib-only, no scipy)
# ---------------------------------------------------------------------------

def normal_cdf(z: float) -> float:
    """Standard normal CDF via the error function (math.erf is stdlib and
    exact, unlike a polynomial approximation)."""
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def binomial_pmf(k: int, n: int, p: float) -> float:
    return math.comb(n, k) * (p ** k) * ((1 - p) ** (n - k))


def binomial_test_two_sided(k: int, n: int, p: float = 0.5) -> Optional[float]:
    """Exact two-sided binomial test (the 'sum of probabilities no more
    likely than the observed outcome' method -- what R's binom.test and
    scipy's binomtest both use for the two-sided case). Exact, not a normal
    approximation; math.comb makes this cheap even at n in the hundreds."""
    if n == 0:
        return None
    p_obs = binomial_pmf(k, n, p)
    total = sum(binomial_pmf(i, n, p) for i in range(n + 1)
                if binomial_pmf(i, n, p) <= p_obs * (1 + 1e-9))
    return min(1.0, total)


def binomial_test_one_sided_ge(k: int, n: int, p: float = 0.5) -> Optional[float]:
    """P(X >= k) under Binomial(n, p) -- exact one-sided test, used for the
    sign test where the direction was preregistered."""
    if n == 0:
        return None
    return sum(binomial_pmf(i, n, p) for i in range(k, n + 1))


def permutation_test_diff_means(xs: list[float], ys: list[float], seed: int = 0,
                                 max_exact: int = 200_000,
                                 n_monte_carlo: int = 100_000) -> dict:
    """Two-sided permutation test on the difference in means. Pools both
    samples, enumerates every way to split the pooled values into groups of
    size len(xs)/len(ys) (exact) when that count is small enough to be
    cheap, otherwise draws n_monte_carlo random shuffles (still exact in
    expectation, just approximated by sampling -- standard practice once
    C(n1+n2, n1) is too large to enumerate). p-value is the fraction of
    (re)splits whose |difference in means| >= the observed |difference|."""
    n1, n2 = len(xs), len(ys)
    observed = statistics.mean(xs) - statistics.mean(ys)
    pooled = list(xs) + list(ys)
    n = n1 + n2
    total_perms = math.comb(n, n1)
    count = 0
    if total_perms <= max_exact:
        n_iter = 0
        for idx in itertools.combinations(range(n), n1):
            idx_set = set(idx)
            g1 = [pooled[i] for i in idx_set]
            g2 = [pooled[i] for i in range(n) if i not in idx_set]
            diff = statistics.mean(g1) - statistics.mean(g2)
            if abs(diff) >= abs(observed) - 1e-12:
                count += 1
            n_iter += 1
        p = count / n_iter
        method = f"exact permutation ({n_iter} of C({n},{n1})={total_perms} splits)"
    else:
        rng = random.Random(seed)
        work = list(pooled)
        for _ in range(n_monte_carlo):
            rng.shuffle(work)
            g1, g2 = work[:n1], work[n1:]
            diff = statistics.mean(g1) - statistics.mean(g2)
            if abs(diff) >= abs(observed) - 1e-12:
                count += 1
        p = count / n_monte_carlo
        method = f"Monte Carlo permutation ({n_monte_carlo} resamples, seed={seed}, of C({n},{n1})={total_perms} possible splits)"
    return {"n1": n1, "n2": n2, "observed_diff": round(observed, 4),
            "p_value": round(p, 4), "method": method}


def two_proportion_z_test(x1: int, n1: int, x2: int, n2: int) -> Optional[dict]:
    """Pooled two-proportion z-test (standard closed form; equivalent to a
    2x2 chi-square test of independence for the two-sided case, z**2 = chi2)."""
    if n1 == 0 or n2 == 0:
        return None
    p1, p2 = x1 / n1, x2 / n2
    p_pool = (x1 + x2) / (n1 + n2)
    se = math.sqrt(p_pool * (1 - p_pool) * (1 / n1 + 1 / n2))
    if se == 0:
        return {"p1": round(p1, 3), "p2": round(p2, 3), "z": None, "p_value": None}
    z = (p1 - p2) / se
    p_value = 2 * (1 - normal_cdf(abs(z)))
    return {"n1": n1, "x1": x1, "p1": round(p1, 3), "n2": n2, "x2": x2, "p2": round(p2, 3),
            "z": round(z, 3), "p_value": round(p_value, 4)}


def mcnemar_exact(n_gained: int, n_lost: int) -> dict:
    """Exact McNemar's test: among the pairs where the two timepoints
    disagree (n_gained: False at time1 -> True at time2; n_lost: True ->
    False), test whether the split is 50/50 via the exact binomial test
    (preferred over the usual chi-square-with-continuity-correction
    approximation when the discordant-pair count is this small)."""
    n_discordant = n_gained + n_lost
    if n_discordant == 0:
        return {"n_discordant": 0, "n_gained": 0, "n_lost": 0, "p_value": None}
    k = min(n_gained, n_lost)
    p = binomial_test_two_sided(k, n_discordant, 0.5)
    return {"n_discordant": n_discordant, "n_gained": n_gained, "n_lost": n_lost,
            "p_value": round(p, 4) if p is not None else None}


def fisher_z_test_r(r: Optional[float], n: int) -> Optional[dict]:
    """Test H0: population r=0 via the same Fisher z-transform used for
    point_biserial_ci95's CI (analysis_eval_awareness.py) -- guarantees the
    p-value and that CI agree (CI excludes 0 iff p<.05)."""
    if r is None or n < 4 or abs(r) >= 1.0:
        return None
    z = math.atanh(r) * math.sqrt(n - 3)
    p = 2 * (1 - normal_cdf(abs(z)))
    return {"r": round(r, 3), "n": n, "z": round(z, 3), "p_value": round(p, 4)}


# ---------------------------------------------------------------------------
# 1 & 2. Altruist vs. Baseline deviation, per model + cross-model sign test
# ---------------------------------------------------------------------------

def altruist_vs_baseline(models: dict[str, str]) -> dict:
    per_model = {}
    signs = []
    for model_label, out_dir in models.items():
        trials = load_all_trials(Path(out_dir))
        trials = [t for t in trials if t.get("persona_context", "fresh") == "same"]
        deviations = [d for d in (compute_trial_deviation(t) for t in trials) if d is not None]
        altruist = [d["deviation_rate"] for d in deviations
                    if d["persona"] == "altruist" and d["framing"] == "literal"]
        baseline = [d["deviation_rate"] for d in deviations
                    if d["persona"] == "baseline" and d["framing"] == "literal"]
        if not altruist or not baseline:
            continue
        test = permutation_test_diff_means(altruist, baseline, seed=0)
        test["altruist_mean"] = round(statistics.mean(altruist), 3)
        test["baseline_mean"] = round(statistics.mean(baseline), 3)
        per_model[model_label] = test
        signs.append(test["altruist_mean"] > test["baseline_mean"])

    k = sum(signs)
    n = len(signs)
    sign_test = {
        "n_models": n,
        "n_altruist_gt_baseline": k,
        "p_one_sided": round(binomial_test_one_sided_ge(k, n, 0.5), 4) if n else None,
        "p_two_sided": round(binomial_test_two_sided(k, n, 0.5), 4) if n else None,
        "note": "one-sided is the primary number -- direction (Altruist > Baseline) "
                "was preregistered (preregistration.md SS4, prediction #1), not "
                "discovered post-hoc; two-sided given alongside for the skeptical read.",
    }
    return {"per_model": per_model, "cross_model_sign_test": sign_test}


# ---------------------------------------------------------------------------
# 3. Matched vs. mismatched hold-rate (two-proportion z) + mid-vs-end (McNemar)
# ---------------------------------------------------------------------------

def hold_rate_tests(cpi_dir: str) -> dict:
    trials = load_cpi_trials(Path(cpi_dir))
    degradations = [d for d in (compute_trial_degradation(t) for t in trials) if d is not None]

    def bucket(matched: bool):
        return [d for d in degradations if d["matched"] == matched]

    matched_rows = bucket(True)
    mismatched_rows = bucket(False)

    def counts(rows, key):
        vals = [r[key] for r in rows if r[key] is not None]
        return sum(vals), len(vals)

    m_mid_x, m_mid_n = counts(matched_rows, "held_mid")
    mm_mid_x, mm_mid_n = counts(mismatched_rows, "held_mid")
    m_end_x, m_end_n = counts(matched_rows, "held_end")
    mm_end_x, mm_end_n = counts(mismatched_rows, "held_end")

    matched_vs_mismatched = {
        "mid": two_proportion_z_test(m_mid_x, m_mid_n, mm_mid_x, mm_mid_n),
        "end": two_proportion_z_test(m_end_x, m_end_n, mm_end_x, mm_end_n),
    }

    def mcnemar_for(rows, label):
        paired = [(r["held_mid"], r["held_end"]) for r in rows
                  if r["held_mid"] is not None and r["held_end"] is not None]
        n_gained = sum(1 for mid, end in paired if mid is False and end is True)
        n_lost = sum(1 for mid, end in paired if mid is True and end is False)
        result = mcnemar_exact(n_gained, n_lost)
        result["label"] = label
        result["n_pairs"] = len(paired)
        return result

    mid_vs_end = {
        "matched": mcnemar_for(matched_rows, "matched (context echoes system)"),
        "mismatched": mcnemar_for(mismatched_rows, "mismatched (context contradicts system)"),
    }

    return {"matched_vs_mismatched": matched_vs_mismatched, "mid_vs_end_mcnemar": mid_vs_end}


# ---------------------------------------------------------------------------
# 4. Eval-awareness point-biserial r vs. 0
# ---------------------------------------------------------------------------

def eval_awareness_tests(models: dict[str, str], cpi_dir: str) -> dict:
    per_model = {}
    for model_label, out_dir in models.items():
        trials = load_all_trials(Path(out_dir))
        trials = [t for t in trials if t.get("persona_context", "fresh") == "same"]
        rows = build_ea_rows(trials)
        summary = aggregate_ea(rows)
        av = summary["affirmed_vs_denied"]
        n = av["n_affirmed"] + av["n_denied"]
        test = fisher_z_test_r(av["point_biserial_r"], n)
        if test is not None:
            per_model[model_label] = test

    cpi_trials = load_cpi_trials(Path(cpi_dir))
    from analysis_cross_persona_injection import build_eval_awareness_rows, aggregate_eval_awareness
    cpi_rows = build_eval_awareness_rows(cpi_trials)
    cpi_summary = aggregate_eval_awareness(cpi_rows)
    av = cpi_summary["affirmed_vs_denied"]
    n = av["n_affirmed"] + av["n_denied"]
    cpi_test = fisher_z_test_r(av["point_biserial_r"], n)

    return {"per_model_main_sweep": per_model, "cross_persona_injection": cpi_test}


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def print_report(avb: dict, hr: dict, ea: dict) -> None:
    print("=== 1. Altruist vs. Baseline deviation rate, per model (permutation test) ===")
    print("(n=40 trials/persona/model: 4 opponents x 10 reps, literal framing, same-context "
          "-- exactly Table 4.1's cells. H0: no difference in mean per-trial deviation rate.)\n")
    for model, t in avb["per_model"].items():
        print(f"  {model:<20} altruist={t['altruist_mean']:.3f}  baseline={t['baseline_mean']:.3f}  "
              f"diff={t['observed_diff']:+.3f}  p={t['p_value']:.4f}  [{t['method']}]")

    st = avb["cross_model_sign_test"]
    print(f"\n  Cross-model sign test: {st['n_altruist_gt_baseline']}/{st['n_models']} models show "
          f"Altruist > Baseline.")
    print(f"  p (one-sided, direction preregistered) = {st['p_one_sided']}")
    print(f"  p (two-sided)                          = {st['p_two_sided']}")

    print("\n=== 2. Matched vs. mismatched persona hold-rate (two-proportion z-test) ===")
    mvm = hr["matched_vs_mismatched"]
    for probe in ("mid", "end"):
        r = mvm[probe]
        if r is None:
            continue
        print(f"  {probe}: matched p={r['p1']} (n={r['n1']}) vs. mismatched p={r['p2']} (n={r['n2']}), "
              f"z={r['z']}, p={r['p_value']}")

    print("\n=== 3. Mid-game -> end-game hold-rate change, within cell (McNemar's exact test) ===")
    print("(H0: the mid->end change in persona hold-status is symmetric, i.e. no real drift; "
          "n_gained/n_lost are the discordant pairs -- concordant pairs carry no information "
          "for this test, which is why n_discordant << n_pairs.)\n")
    for label, r in hr["mid_vs_end_mcnemar"].items():
        print(f"  {r['label']:<45} n_pairs={r['n_pairs']:>4}  discordant={r['n_discordant']:>3} "
              f"(gained={r['n_gained']}, lost={r['n_lost']})  p={r['p_value']}")

    print("\n=== 4. Eval-awareness point-biserial r vs. 0 (Fisher-z test) ===")
    for model, t in ea["per_model_main_sweep"].items():
        print(f"  {model:<20} r={t['r']:+.3f}  n={t['n']:>4}  z={t['z']:+.3f}  p={t['p_value']}")
    cpi = ea["cross_persona_injection"]
    if cpi is not None:
        print(f"  {'cross-persona-injection':<20} r={cpi['r']:+.3f}  n={cpi['n']:>4}  z={cpi['z']:+.3f}  p={cpi['p_value']}")

    print("\nNote: none of the above corrects for multiple comparisons across the many "
          "persona x opponent x model cells this project ran (5 models x 5 personas x 4 "
          "opponents x 2 framings = 200 cells in the main sweep alone). These four tests "
          "were chosen because they back specific claims already stated in report_draft.md, "
          "not by scanning all cells for significance -- but that itself is worth stating "
          "explicitly rather than leaving implicit. See analysis_significance.py's docstring "
          "and report_draft.md's Appendix for the full method writeup.")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json-out", type=Path, default=None)
    args = ap.parse_args()

    avb = altruist_vs_baseline(MAIN_SWEEP_MODELS)
    hr = hold_rate_tests(CPI_DIR)
    ea = eval_awareness_tests(MAIN_SWEEP_MODELS, CPI_DIR)

    print_report(avb, hr, ea)

    if args.json_out:
        args.json_out.write_text(json.dumps({
            "altruist_vs_baseline": avb,
            "hold_rate_tests": hr,
            "eval_awareness": ea,
        }, indent=2))
        print(f"\nWrote {args.json_out}")


if __name__ == "__main__":
    main()
