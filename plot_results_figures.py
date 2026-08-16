#!/usr/bin/env python3
"""
plot_results_figures.py -- paper-ready result figures from runs/ (+ optional judgments/).

Generates:
  figures/results_deviation_heatmap.png
      Mean deviation rate (persona × opponent), one panel per model (or a
      pooled panel with --pool-models).
  figures/results_detective_by_persona.png
      Detective-only bars: persona × framing (literal vs story).
  figures/results_early_mid_late.png
      Early/mid/late deviation for Detective cells (persona mean across models).
  figures/results_judge_codes.png   (only if judgments/reasoning_judgments.jsonl exists)
      primary_code counts among deviant rounds in the CoT judge pilot.

Stdlib + matplotlib (+ numpy if available; falls back to lists).

Usage:
  python plot_results_figures.py --runs-dir runs
  python plot_results_figures.py --runs-dir runs --judgments-dir judgments
  python plot_results_figures.py --runs-dir runs --models qwen/qwen3-32b,google/gemini-2.5-flash
  python plot_results_figures.py --runs-dir runs --out-dir figures
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Optional

from analysis_deviation_gap import (
    OPPONENT_ORDER,
    PERSONA_ORDER,
    compute_trial_deviation,
    load_all_trials as load_scaffold_trials,
)
from judge_reasoning import load_all_trials as load_trials_with_harness

# Short display names for axes / legends
PERSONA_SHORT = {
    "baseline": "Baseline",
    "consultant": "Consultant",
    "saboteur": "Saboteur",
    "altruist": "Altruist",
    "bard": "Bard",
}
OPPONENT_SHORT = {
    "cooperator": "Cooperator",
    "cheater": "Cheater",
    "copycat": "Copycat",
    "detective": "Detective",
}
MODEL_SHORT = {
    "qwen/qwen3-32b": "Qwen3-32B",
    "qwen/qwen3-8b": "Qwen3-8B",
    "qwen/qwen3.8-27b": "Qwen3.8-27B",
    "google/gemini-2.5-flash": "Gemini-2.5-Flash",
    "meta-llama/llama-3.3-70b-instruct": "Llama-3.3-70B",
    "deepseek/deepseek-v3.2": "DeepSeek-V3.2",
    "deepseek/deepseek-r1-0528": "DeepSeek-R1",
    "mistralai/mistral-large-2512": "Mistral-Large",
    "qwen3:1.7b": "Qwen3-1.7B (local)",
}
PREFERRED_MODELS = [
    "qwen/qwen3-32b",
    "qwen/qwen3.8-27b",
    "qwen/qwen3-8b",
    "meta-llama/llama-3.3-70b-instruct",
    "google/gemini-2.5-flash",
    "deepseek/deepseek-v3.2",
    "deepseek/deepseek-r1-0528",
    "mistralai/mistral-large-2512",
]


def _mean(xs: list[float]) -> Optional[float]:
    return sum(xs) / len(xs) if xs else None


def collect_cell_means(trials: list[dict]) -> dict[tuple, float]:
    """(model, persona, opponent, framing) -> mean deviation_rate over reps."""
    buckets: dict[tuple, list[float]] = defaultdict(list)
    for t in trials:
        d = compute_trial_deviation(t)
        if d is None or d["deviation_rate"] is None:
            continue
        key = (d["model"], d["persona"], d["opponent"], d["framing"])
        buckets[key].append(d["deviation_rate"])
    return {k: sum(v) / len(v) for k, v in buckets.items()}


def collect_eml(trials: list[dict]) -> dict[tuple, dict[str, float]]:
    """(model, persona, opponent, framing) -> {early, mid, late} means."""
    buckets: dict[tuple, dict[str, list[float]]] = defaultdict(
        lambda: {"early": [], "mid": [], "late": []}
    )
    for t in trials:
        d = compute_trial_deviation(t)
        if d is None:
            continue
        key = (d["model"], d["persona"], d["opponent"], d["framing"])
        if d["deviation_rate_early"] is not None:
            buckets[key]["early"].append(d["deviation_rate_early"])
        if d["deviation_rate_mid"] is not None:
            buckets[key]["mid"].append(d["deviation_rate_mid"])
        if d["deviation_rate_late"] is not None:
            buckets[key]["late"].append(d["deviation_rate_late"])
    out = {}
    for k, b in buckets.items():
        out[k] = {name: _mean(vals) for name, vals in b.items()}
    return out


def setup_matplotlib():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({
        "font.size": 10,
        "axes.titlesize": 11,
        "axes.labelsize": 10,
        "figure.dpi": 150,
        "savefig.dpi": 200,
        "savefig.bbox": "tight",
        "axes.spines.top": False,
        "axes.spines.right": False,
    })
    return plt


def plot_heatmaps(cell_means: dict[tuple, float], models: list[str], out_path: Path,
                  framing: str = "literal", ncols: int = 4) -> None:
    """One panel per model; laid out as a grid (default 4 columns) so all models
    stay on a single figure instead of arbitrary 3+2 splits."""
    import numpy as np

    plt = setup_matplotlib()
    personas = [p for p in PERSONA_ORDER if any(
        (m, p, o, framing) in cell_means for m in models for o in OPPONENT_ORDER
    )]
    opponents = list(OPPONENT_ORDER)
    n = len(models)
    ncols = min(ncols, n) if n else 1
    nrows = (n + ncols - 1) // ncols
    fig, axes = plt.subplots(nrows, ncols, figsize=(3.1 * ncols + 0.9, 2.9 * nrows + 0.6),
                             squeeze=False, constrained_layout=True)
    im = None
    for idx, model in enumerate(models):
        ax = axes[idx // ncols, idx % ncols]
        mat = np.full((len(personas), len(opponents)), float("nan"))
        for i, p in enumerate(personas):
            for j, o in enumerate(opponents):
                v = cell_means.get((model, p, o, framing))
                if v is not None:
                    mat[i, j] = v
        im = ax.imshow(mat, vmin=0, vmax=1, cmap="YlOrRd", aspect="auto")
        ax.set_xticks(range(len(opponents)))
        ax.set_xticklabels([OPPONENT_SHORT[o] for o in opponents], rotation=35, ha="right",
                           fontsize=8)
        ax.set_yticks(range(len(personas)))
        if idx % ncols == 0:
            ax.set_yticklabels([PERSONA_SHORT.get(p, p) for p in personas], fontsize=8)
        else:
            ax.set_yticklabels([])
        ax.set_title(MODEL_SHORT.get(model, model), fontsize=10)
        for i in range(len(personas)):
            for j in range(len(opponents)):
                val = mat[i, j]
                if val == val:  # not NaN
                    ax.text(j, i, f"{val:.2f}", ha="center", va="center",
                            color="black" if val < 0.55 else "white", fontsize=7)
    for idx in range(n, nrows * ncols):
        axes[idx // ncols, idx % ncols].axis("off")
    fig.suptitle(f"Mean deviation rate (framing={framing})", fontsize=12)
    if im is not None:
        fig.colorbar(im, ax=axes.ravel().tolist(), fraction=0.03, pad=0.02,
                     label="Deviation rate")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path)
    plt.close(fig)
    print(f"Wrote {out_path}")


def plot_pooled_summary(cell_means: dict[tuple, float], models: list[str],
                        judgments_path: Path, out_path: Path) -> None:
    """Paper-facing 3-panel figure: (1) pooled persona×opponent deviation,
    (2) Detective persona×framing, (3) judge primary codes on deviant rounds.

    Panels 1–2 are behavioral (moves vs optimal). Panel 3 is LLM-as-judge."""
    import numpy as np
    from collections import Counter
    from judge_reasoning import load_jsonl_tolerant

    plt = setup_matplotlib()
    fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.2), constrained_layout=True)

    # --- Panel A: pooled persona × opponent (mean of per-model cell means) ---
    personas = list(PERSONA_ORDER)
    opponents = list(OPPONENT_ORDER)
    mat = np.full((len(personas), len(opponents)), float("nan"))
    for i, p in enumerate(personas):
        for j, o in enumerate(opponents):
            vals = []
            for m in models:
                for fr in ("literal", "story"):
                    if (m, p, o, fr) in cell_means:
                        vals.append(cell_means[(m, p, o, fr)])
            if vals:
                mat[i, j] = sum(vals) / len(vals)
    ax = axes[0]
    im = ax.imshow(mat, vmin=0, vmax=1, cmap="YlOrRd", aspect="auto")
    ax.set_xticks(range(len(opponents)))
    ax.set_xticklabels([OPPONENT_SHORT[o] for o in opponents], rotation=30, ha="right")
    ax.set_yticks(range(len(personas)))
    ax.set_yticklabels([PERSONA_SHORT[p] for p in personas])
    ax.set_title("A. Behavioral deviation\n(persona × opponent, pooled)")
    for i in range(len(personas)):
        for j in range(len(opponents)):
            val = mat[i, j]
            if val == val:
                ax.text(j, i, f"{val:.2f}", ha="center", va="center",
                        color="black" if val < 0.55 else "white", fontsize=8)
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04, label="Mean deviation rate")

    # --- Panel B: Detective × framing ---
    ax = axes[1]
    x = list(range(len(personas)))
    width = 0.35
    lit, story = [], []
    for p in personas:
        lit_vals = [cell_means[(m, p, "detective", "literal")]
                    for m in models if (m, p, "detective", "literal") in cell_means]
        story_vals = [cell_means[(m, p, "detective", "story")]
                      for m in models if (m, p, "detective", "story") in cell_means]
        lit.append(_mean(lit_vals))
        story.append(_mean(story_vals))
    bars_l = ax.bar([i - width / 2 for i in x],
                    [v if v is not None else 0 for v in lit], width,
                    label="literal", color="#4C78A8")
    bars_s = ax.bar([i + width / 2 for i in x],
                    [v if v is not None else 0 for v in story], width,
                    label="story", color="#F58518")
    for bar, v in zip(bars_l, lit):
        if v is None:
            bar.set_visible(False)
    for bar, v in zip(bars_s, story):
        if v is None:
            bar.set_visible(False)
    ax.set_xticks(x)
    ax.set_xticklabels([PERSONA_SHORT[p] for p in personas], rotation=20, ha="right")
    ax.set_ylabel("Mean deviation rate")
    ax.set_ylim(0, 1)
    ax.set_title("B. Detective opponent\n(persona × framing)")
    ax.legend(fontsize=8)

    # --- Panel C: judge codes (readable labels) ---
    ax = axes[2]
    rows = [r for r in load_jsonl_tolerant(judgments_path)
            if not r.get("judge_parse_failure") and r.get("deviated")]
    codes = Counter(r.get("primary_code", "other") for r in rows)
    present = [c for c in CODE_ORDER if codes.get(c)]
    labels = [CODE_LABELS[c] for c in present]
    vals = [codes[c] for c in present]
    colors = [CODE_COLORS[c] for c in present]
    y = list(range(len(present)))
    ax.barh(y, vals[::-1], color=colors[::-1], height=0.7)
    ax.set_yticks(y)
    ax.set_yticklabels(labels[::-1], fontsize=8)
    ax.set_xlabel("Count (deviant rounds)")
    ax.set_title(f"C. LLM-as-judge\n(Detective×Baseline/Bard, n={len(rows)})")
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path)
    plt.close(fig)
    print(f"Wrote {out_path}")


def plot_detective_bars(cell_means: dict[tuple, float], models: list[str],
                        out_path: Path) -> None:
    plt = setup_matplotlib()
    personas = [p for p in PERSONA_ORDER]
    x = list(range(len(personas)))
    width = 0.35
    # Pool across models: mean of cell means (omit bar if no data — do not fake 0)
    lit, story = [], []
    for p in personas:
        lit_vals = [cell_means[(m, p, "detective", "literal")]
                    for m in models if (m, p, "detective", "literal") in cell_means]
        story_vals = [cell_means[(m, p, "detective", "story")]
                      for m in models if (m, p, "detective", "story") in cell_means]
        lit.append(_mean(lit_vals))
        story.append(_mean(story_vals))

    fig, ax = plt.subplots(figsize=(7.5, 4))
    lit_h = [v if v is not None else 0.0 for v in lit]
    story_h = [v if v is not None else 0.0 for v in story]
    bars_l = ax.bar([i - width / 2 for i in x], lit_h, width, label="literal", color="#4C78A8")
    bars_s = ax.bar([i + width / 2 for i in x], story_h, width, label="story", color="#F58518")
    for bar, v in zip(bars_l, lit):
        if v is None:
            bar.set_visible(False)
    for bar, v in zip(bars_s, story):
        if v is None:
            bar.set_visible(False)
    ax.set_xticks(x)
    ax.set_xticklabels([PERSONA_SHORT[p] for p in personas])
    ax.set_ylabel("Mean deviation rate")
    ax.set_ylim(0, 1)
    ax.set_title("Detective opponent — deviation by persona × framing\n"
                 f"(pooled across {len(models)} model(s))")
    ax.legend()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path)
    plt.close(fig)
    print(f"Wrote {out_path}")


def plot_eml(eml: dict[tuple, dict[str, float]], models: list[str], out_path: Path,
             framing: str = "story") -> None:
    plt = setup_matplotlib()
    fig, ax = plt.subplots(figsize=(7.5, 4))
    bins = ["early", "mid", "late"]
    for p in PERSONA_ORDER:
        ys = []
        for b in bins:
            vals = []
            for m in models:
                cell = eml.get((m, p, "detective", framing))
                if cell and cell.get(b) is not None:
                    vals.append(cell[b])
            ys.append(_mean(vals))
        if any(v is not None for v in ys):
            ax.plot(bins, [v if v is not None else float("nan") for v in ys],
                    marker="o", label=PERSONA_SHORT[p])
    ax.set_ylabel("Mean deviation rate")
    ax.set_ylim(0, 1)
    ax.set_title(f"Detective — early / mid / late deviation (framing={framing})")
    ax.legend(ncols=2, fontsize=8)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path)
    plt.close(fig)
    print(f"Wrote {out_path}")


CODE_LABELS = {
    "persona_override": "Persona takes over",
    "strategic_error": "Strategic error vs Stage A",
    "stage_a_ignored": "Stage A ignored",
    "stage_a_reaffirmed": "Stage A reaffirmed (action diverged)",
    "eval_aware": "Eval-aware motive",
    "incoherent": "Incoherent CoT vs move",
    "other": "Other",
}
CODE_COLORS = {
    "persona_override": "#E45756",
    "strategic_error": "#F58518",
    "stage_a_ignored": "#B279A2",
    "stage_a_reaffirmed": "#4C78A8",
    "eval_aware": "#72B7B2",
    "incoherent": "#BAB0AC",
    "other": "#9D755D",
}
CODE_ORDER = [
    "persona_override", "strategic_error", "stage_a_ignored",
    "stage_a_reaffirmed", "eval_aware", "incoherent", "other",
]


def plot_judge_codes(judgments_path: Path, out_path: Path) -> None:
    """Write two appendix figures (no chart titles — captions live in the paper):
      <stem>_pooled.png   — count of primary codes among deviant rounds
      <stem>_by_model.png — 100% stacked share by model
    If out_path ends with .png, stem is that path without suffix; otherwise
    out_path is treated as a directory and files are named results_judge_codes_*.
    Defaults to pilot scope (Detective × baseline/bard) so n matches the paper.
    """
    from collections import Counter
    import numpy as np
    from judge_reasoning import load_jsonl_tolerant

    if not judgments_path.exists():
        print(f"Skip judge codes — missing {judgments_path}")
        return
    rows = [
        r for r in load_jsonl_tolerant(judgments_path)
        if not r.get("judge_parse_failure")
        and r.get("deviated")
        and r.get("opponent") == "detective"
        and r.get("persona") in ("baseline", "bard")
    ]
    if not rows:
        print("Skip judge codes — no deviant judged rounds yet")
        return

    codes = Counter(r.get("primary_code", "other") for r in rows)
    present = [c for c in CODE_ORDER if codes.get(c)]

    by_model: dict[str, Counter] = defaultdict(Counter)
    for r in rows:
        m = MODEL_SHORT.get(r["player_model"], r["player_model"])
        by_model[m][r.get("primary_code", "other")] += 1
    model_order = sorted(by_model.keys(), key=lambda m: -sum(by_model[m].values()))
    model_order = [m for m in model_order if sum(by_model[m].values()) >= 1]

    if out_path.suffix.lower() == ".png":
        stem = out_path.with_suffix("")
        out_dir = out_path.parent
    else:
        stem = out_path / "results_judge_codes"
        out_dir = out_path
    out_dir.mkdir(parents=True, exist_ok=True)
    pooled_path = Path(f"{stem}_pooled.png")
    by_model_path = Path(f"{stem}_by_model.png")

    plt = setup_matplotlib()

    # --- Pooled counts (wide, no title) ---
    fig0, ax0 = plt.subplots(figsize=(10.5, 4.6), constrained_layout=True)
    labels = [CODE_LABELS[c] for c in present]
    vals = [codes[c] for c in present]
    colors = [CODE_COLORS[c] for c in present]
    y = list(range(len(present)))
    ax0.barh(y, vals[::-1], color=colors[::-1], height=0.72)
    ax0.set_yticks(y)
    ax0.set_yticklabels(labels[::-1])
    ax0.set_xlabel("Number of deviant rounds")
    for yi, v in zip(y, vals[::-1]):
        ax0.text(v + max(vals) * 0.015, yi, str(v), va="center", fontsize=10)
    ax0.set_xlim(0, max(vals) * 1.18)
    ax0.spines["left"].set_visible(False)
    ax0.tick_params(axis="y", length=0)
    fig0.savefig(pooled_path)
    plt.close(fig0)
    print(f"Wrote {pooled_path} (n={len(rows)})")

    # --- Per-model mix (wide, no title; legend below) ---
    fig1, ax1 = plt.subplots(figsize=(11.5, 5.2), constrained_layout=True)
    bottoms = np.zeros(len(model_order))
    x = np.arange(len(model_order))
    for code in present:
        heights = np.array([
            by_model[m][code] / sum(by_model[m].values()) for m in model_order
        ])
        ax1.bar(x, heights, bottom=bottoms, color=CODE_COLORS[code],
                width=0.78, label=CODE_LABELS[code])
        bottoms = bottoms + heights
    ax1.set_xticks(x)
    ax1.set_xticklabels(
        [f"{m}\n(n={sum(by_model[m].values())})" for m in model_order],
        fontsize=9,
    )
    ax1.set_ylabel("Share of deviant rounds")
    ax1.set_ylim(0, 1)
    ax1.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
    ax1.set_yticklabels(["0%", "25%", "50%", "75%", "100%"])
    ax1.legend(loc="upper center", bbox_to_anchor=(0.5, -0.14), ncol=3, fontsize=9,
               frameon=False)
    fig1.savefig(by_model_path)
    plt.close(fig1)
    print(f"Wrote {by_model_path}")

    # Keep legacy single-file name as a copy of the pooled panel for old refs
    legacy = out_dir / "results_judge_codes.png"
    if pooled_path.resolve() != legacy.resolve():
        import shutil
        shutil.copyfile(pooled_path, legacy)
        print(f"Also wrote {legacy} (pooled, legacy name)")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs-dir", type=Path, default=Path("runs"))
    ap.add_argument("--also-harness", type=Path, default=Path("harness/runs/full"),
                    help="Include Oscar harness branch runs (DeepSeek/Mistral/…). "
                         "Pass empty string to disable.")
    ap.add_argument("--judgments-dir", type=Path, default=Path("judgments"))
    ap.add_argument("--out-dir", type=Path, default=Path("figures"))
    ap.add_argument("--models", default="",
                    help="Comma-separated model ids; default = all found except local 1.7b")
    ap.add_argument("--framing", default="literal", choices=("story", "literal", "both"),
                    help="Heatmap/EML framing filter. Default literal. Use 'both' for "
                         "separate story + literal heatmaps.")
    ap.add_argument("--include-local", action="store_true",
                    help="Include qwen3:1.7b local runs in plots")
    args = ap.parse_args()

    harness = args.also_harness if str(args.also_harness) not in ("", "none", "None") else None
    if harness is not None and not harness.exists():
        print(f"Warning: --also-harness {harness} missing; plotting scaffold runs only")
        harness = None
    if harness is not None:
        trials = load_trials_with_harness(args.runs_dir, also_harness=harness)
    else:
        trials = load_scaffold_trials(args.runs_dir)
    if not trials:
        raise SystemExit(f"No trials found under {args.runs_dir}")

    all_models = sorted({t["model"] for t in trials})
    if args.models.strip():
        models = [m.strip() for m in args.models.split(",") if m.strip()]
    else:
        models = [m for m in all_models if args.include_local or m != "qwen3:1.7b"]
    models = [m for m in PREFERRED_MODELS if m in models] + [
        m for m in models if m not in PREFERRED_MODELS
    ]
    print(f"Plotting models: {models} ({len(trials)} trials; harness={harness})")

    cell_means = collect_cell_means(trials)
    eml = collect_eml(trials)
    out = args.out_dir
    out.mkdir(parents=True, exist_ok=True)

    framings = (["literal", "story"] if args.framing == "both" else [args.framing])
    for fr in framings:
        tag = f"_{fr}" if len(framings) > 1 or fr != "literal" else ""
        # Single grid figure with every model (no 3+2 split)
        plot_heatmaps(cell_means, models, out / f"results_deviation_heatmap{tag}.png",
                      framing=fr, ncols=4)

    plot_detective_bars(cell_means, models, out / "results_detective_by_persona.png")
    eml_framing = "story" if args.framing == "story" else "literal"
    plot_eml(eml, models, out / "results_early_mid_late.png", framing=eml_framing)
    plot_judge_codes(args.judgments_dir / "reasoning_judgments.jsonl",
                     out / "results_judge_codes.png")
    plot_pooled_summary(cell_means, models,
                        args.judgments_dir / "reasoning_judgments.jsonl",
                        out / "results_summary_triptych.png")


if __name__ == "__main__":
    main()
