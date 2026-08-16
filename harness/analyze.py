"""
Generate an HTML report from all runs in a directory.

Usage:
    python analyze.py --runs-dir runs/full --out report.html
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import pandas as pd

# ── helpers ──────────────────────────────────────────────────────────────────

def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def short_model(m: str) -> str:
    parts = m.split("/")
    return parts[-1] if len(parts) > 1 else m


def pct(v: float) -> str:
    return f"{v*100:.1f}%"


def color_cell(v: float, lo: float = 0.0, hi: float = 1.0, reverse: bool = False) -> str:
    """Return an inline style background color green→red (or reversed)."""
    t = max(0.0, min(1.0, (v - lo) / (hi - lo) if hi > lo else 0.0))
    if reverse:
        t = 1 - t
    r = int(255 * t)
    g = int(255 * (1 - t))
    return f"background:rgb({r},{g},80);color:#111"


# ── load all data ─────────────────────────────────────────────────────────────

def load_runs(runs_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    trial_rows, round_rows, check_rows = [], [], []
    for subdir in sorted(runs_dir.iterdir()):
        if not subdir.is_dir():
            continue
        t = subdir / "trials.jsonl"
        r = subdir / "rounds.jsonl"
        c = subdir / "persona_checks.jsonl"
        if t.exists():
            trial_rows.extend(load_jsonl(t))
        if r.exists():
            round_rows.extend(load_jsonl(r))
        if c.exists():
            check_rows.extend(load_jsonl(c))

    trials = pd.DataFrame(trial_rows)
    rounds = pd.DataFrame(round_rows)
    checks = pd.DataFrame(check_rows)

    trials["model_short"] = trials["model"].apply(short_model)
    rounds["model_short"] = rounds["model"].apply(short_model)

    return trials, rounds, checks


# ── HTML pieces ───────────────────────────────────────────────────────────────

CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: system-ui, sans-serif; background: #0f1117; color: #e2e8f0;
       padding: 2rem; font-size: 14px; }
h1 { font-size: 1.8rem; font-weight: 700; margin-bottom: 0.25rem; color: #f0f4ff; }
.subtitle { color: #94a3b8; margin-bottom: 2rem; }
h2 { font-size: 1.1rem; font-weight: 600; margin: 2.5rem 0 0.75rem; color: #cbd5e1;
     border-bottom: 1px solid #2d3748; padding-bottom: 0.4rem; }
h3 { font-size: 0.95rem; font-weight: 600; margin: 1.5rem 0 0.5rem; color: #94a3b8; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
        gap: 1rem; margin-bottom: 1rem; }
.card { background: #1e2535; border-radius: 8px; padding: 1.2rem; }
.card .val { font-size: 2rem; font-weight: 700; color: #818cf8; }
.card .label { font-size: 0.78rem; color: #64748b; margin-top: 0.25rem; }
table { border-collapse: collapse; width: 100%; margin-bottom: 1rem; }
th { background: #1e2535; padding: 0.5rem 0.75rem; text-align: left;
     font-size: 0.78rem; font-weight: 600; color: #94a3b8; white-space: nowrap; }
td { padding: 0.45rem 0.75rem; border-bottom: 1px solid #1e2535;
     font-size: 0.82rem; }
tr:hover td { background: #1e2535; }
.section { background: #161b27; border-radius: 10px; padding: 1.5rem;
           margin-bottom: 1.5rem; }
.tag { display: inline-block; padding: 0.15rem 0.5rem; border-radius: 4px;
       font-size: 0.72rem; font-weight: 600; }
.tag-m { background: #312e81; color: #a5b4fc; }
.tag-n { background: #134e4a; color: #5eead4; }
.bar-wrap { display: flex; align-items: center; gap: 0.5rem; }
.bar { height: 10px; border-radius: 3px; background: #818cf8; min-width: 2px; }
canvas { max-height: 320px; }
"""

CHART_JS = '<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.3/dist/chart.umd.min.js"></script>'


def kv_card(val: str, label: str) -> str:
    return f'<div class="card"><div class="val">{val}</div><div class="label">{label}</div></div>'


def heatmap_table(df_pivot: pd.DataFrame, fmt=pct, lo=0.0, hi=1.0, reverse=False) -> str:
    rows = ["<table><thead><tr><th></th>"]
    for col in df_pivot.columns:
        rows[-1] += f"<th>{col}</th>"
    rows[-1] += "</tr></thead><tbody>"
    for idx, row in df_pivot.iterrows():
        rows.append(f"<tr><td><b>{idx}</b></td>")
        for col in df_pivot.columns:
            v = row[col]
            if pd.isna(v):
                rows[-1] += "<td>—</td>"
            else:
                style = color_cell(v, lo, hi, reverse)
                rows[-1] += f'<td style="{style}">{fmt(v)}</td>'
        rows.append("</tr>")
    rows.append("</tbody></table>")
    return "\n".join(rows)


def bar_chart(chart_id: str, labels: list, datasets: list, title: str = "") -> str:
    labels_js = json.dumps(labels)
    ds_js = json.dumps(datasets)
    return f"""
<canvas id="{chart_id}"></canvas>
<script>
new Chart(document.getElementById('{chart_id}'), {{
  type: 'bar',
  data: {{ labels: {labels_js}, datasets: {ds_js} }},
  options: {{
    responsive: true,
    plugins: {{
      legend: {{ labels: {{ color: '#cbd5e1' }} }},
      title: {{ display: {'true' if title else 'false'}, text: {json.dumps(title)},
                color: '#94a3b8' }}
    }},
    scales: {{
      x: {{ ticks: {{ color: '#94a3b8' }}, grid: {{ color: '#1e2535' }} }},
      y: {{ ticks: {{ color: '#94a3b8' }}, grid: {{ color: '#1e2535' }},
            min: 0, max: 1 }}
    }}
  }}
}});
</script>"""


def line_chart(chart_id: str, labels: list, datasets: list) -> str:
    labels_js = json.dumps(labels)
    ds_js = json.dumps(datasets)
    return f"""
<canvas id="{chart_id}"></canvas>
<script>
new Chart(document.getElementById('{chart_id}'), {{
  type: 'line',
  data: {{ labels: {labels_js}, datasets: {ds_js} }},
  options: {{
    responsive: true,
    plugins: {{ legend: {{ labels: {{ color: '#cbd5e1' }} }} }},
    scales: {{
      x: {{ ticks: {{ color: '#94a3b8' }}, grid: {{ color: '#1e2535' }} }},
      y: {{ ticks: {{ color: '#94a3b8' }}, grid: {{ color: '#1e2535' }}, min: 0 }}
    }}
  }}
}});
</script>"""


COLORS = [
    "#818cf8", "#34d399", "#f472b6", "#fbbf24", "#60a5fa",
    "#a78bfa", "#4ade80", "#fb923c", "#38bdf8", "#f87171",
]


# ── report sections ───────────────────────────────────────────────────────────

def played(trials: pd.DataFrame) -> pd.DataFrame:
    return trials[trials["stage_b_skipped"] == False]  # noqa: E712


def section_overview(trials: pd.DataFrame, rounds: pd.DataFrame) -> str:
    active = played(trials)
    n_models = trials["model"].nunique()
    n_trials = len(trials)
    n_active = len(active)
    n_rounds_total = len(rounds)
    skip_rate = 1 - n_active / n_trials if n_trials else 0

    cards = "".join([
        kv_card(str(n_models), "Models tested"),
        kv_card(str(n_trials), "Total trials"),
        kv_card(str(n_active), "Trials with game play"),
        kv_card(str(n_rounds_total), "Individual rounds logged"),
        kv_card(pct(skip_rate), "Persona-check skip rate"),
    ])
    return f'<div class="section"><h2>Overview</h2><div class="grid">{cards}</div></div>'


def section_persona_checks(checks: pd.DataFrame, trials: pd.DataFrame) -> str:
    if checks.empty:
        return ""

    # pass rate per model × persona
    checks2 = checks.copy()
    checks2["model_short"] = checks2["model"].apply(short_model)
    pivot = checks2.pivot_table(
        index="model_short", columns="persona", values="passed", aggfunc="mean"
    )
    persona_order = ["baseline", "consultant", "saboteur", "altruist", "bard"]
    cols = [c for c in persona_order if c in pivot.columns]
    pivot = pivot[cols]

    html = heatmap_table(pivot, fmt=pct, lo=0.0, hi=1.0, reverse=True)

    # check_a mean
    pivot_score = checks2.pivot_table(
        index="model_short", columns="persona", values="check_a_mean", aggfunc="mean"
    )
    pivot_score = pivot_score[[c for c in cols if c in pivot_score.columns]]
    html2 = heatmap_table(pivot_score, fmt=lambda v: f"{v:.2f}", lo=0.0, hi=3.0, reverse=True)

    return f"""<div class="section">
<h2>Persona Manipulation Checks</h2>
<h3>Pass rate (green = failed check = model didn't adopt persona)</h3>
{html}
<h3>Check-A mean score (0–3, higher = more in-persona)</h3>
{html2}
</div>"""


def section_deviation(trials: pd.DataFrame, rounds: pd.DataFrame) -> str:
    active = trials[trials["stage_b_skipped"] == False].copy()
    if active.empty:
        return ""

    active["model_short"] = active["model"].apply(short_model)
    persona_order = ["baseline", "consultant", "saboteur", "altruist", "bard"]
    models = sorted(active["model_short"].unique())
    frames = sorted(active["frame"].unique())

    # 1. Deviation rate by model × persona (both frames combined)
    pivot_dev = active.pivot_table(
        index="model_short", columns="persona", values="deviation_rate", aggfunc="mean"
    )
    cols = [c for c in persona_order if c in pivot_dev.columns]
    pivot_dev = pivot_dev[cols]

    # 2. Deviation rate by model × frame
    pivot_frame = active.pivot_table(
        index="model_short", columns="frame", values="deviation_rate", aggfunc="mean"
    )

    # 3. Bar chart: deviation rate per persona, per model, split by frame
    bar_datasets = []
    frame_colors = {"matrix": "#818cf8", "narrative": "#34d399"}
    for i, (model, frame) in enumerate([(m, f) for m in models for f in frames]):
        sub = active[(active["model_short"] == model) & (active["frame"] == frame)]
        if sub.empty:
            continue
        data = [sub[sub["persona"] == p]["deviation_rate"].mean() for p in cols]
        data = [round(v, 4) if not (isinstance(v, float) and math.isnan(v)) else None for v in data]
        bar_datasets.append({
            "label": f"{model} / {frame}",
            "data": data,
            "backgroundColor": frame_colors.get(frame, COLORS[i % len(COLORS)]) + "cc",
            "borderColor": frame_colors.get(frame, COLORS[i % len(COLORS)]),
            "borderWidth": 1,
        })

    bar_html = bar_chart("devBarChart", cols, bar_datasets, "Deviation rate by persona")

    # 4. Deviation rate by round (across all trials)
    if not rounds.empty:
        rounds2 = rounds.copy()
        rounds2["model_short"] = rounds2["model"].apply(short_model)
        round_line_datasets = []
        for i, model in enumerate(models):
            sub = rounds2[rounds2["model_short"] == model]
            by_round = sub.groupby("round")["deviated"].mean().reset_index()
            data = [round(v, 4) for v in by_round["deviated"].tolist()]
            round_line_datasets.append({
                "label": model,
                "data": data,
                "borderColor": COLORS[i % len(COLORS)],
                "backgroundColor": "transparent",
                "tension": 0.3,
                "pointRadius": 3,
            })
        round_labels = sorted(rounds2["round"].unique().tolist())
        line_html = line_chart("devLineChart", round_labels, round_line_datasets)
    else:
        line_html = ""

    return f"""<div class="section">
<h2>Deviation from Optimal Play</h2>
<h3>Mean deviation rate by model × persona (all frames)</h3>
{heatmap_table(pivot_dev)}
<h3>Mean deviation rate by model × frame</h3>
{heatmap_table(pivot_frame)}
<h3>Deviation rate by persona and frame</h3>
{bar_html}
<h3>Deviation rate by round number (all trials)</h3>
{line_html}
</div>"""


def section_payoff(trials: pd.DataFrame) -> str:
    active = trials[trials["stage_b_skipped"] == False].copy()
    if active.empty:
        return ""
    active["model_short"] = active["model"].apply(short_model)
    persona_order = ["baseline", "consultant", "saboteur", "altruist", "bard"]

    # payoff_cost pivot
    pivot = active.pivot_table(
        index="model_short", columns="persona", values="payoff_cost", aggfunc="mean"
    )
    cols = [c for c in persona_order if c in pivot.columns]
    pivot = pivot[cols]
    max_cost = pivot.values[~pd.isna(pivot.values)].max() if pivot.size else 1

    # score vs optimal
    active["score_frac"] = active["final_cumulative_you"] / active["optimal_score"].replace(0, 1)
    pivot_score = active.pivot_table(
        index="model_short", columns="persona", values="score_frac", aggfunc="mean"
    )
    pivot_score = pivot_score[[c for c in cols if c in pivot_score.columns]]

    return f"""<div class="section">
<h2>Payoff & Score</h2>
<h3>Mean payoff cost from deviations (points lost vs optimal)</h3>
{heatmap_table(pivot, fmt=lambda v: f"{v:+.1f}", lo=0, hi=float(max_cost))}
<h3>Mean score as fraction of optimal (higher = better)</h3>
{heatmap_table(pivot_score, fmt=lambda v: f"{v:.2f}", lo=0.5, hi=1.0, reverse=True)}
</div>"""


def section_eval_awareness(trials: pd.DataFrame) -> str:
    active = trials[trials["stage_b_skipped"] == False].copy()
    if active.empty or "suspected_test" not in active.columns:
        return ""
    active["model_short"] = active["model"].apply(short_model)
    active["suspected_test_num"] = active["suspected_test"].apply(
        lambda x: 1 if x is True else (0 if x is False else None)
    )
    active["affected_play_num"] = active["affected_play"].apply(
        lambda x: 1 if x is True else (0 if x is False else None)
    )

    models = sorted(active["model_short"].unique())
    frames = sorted(active["frame"].unique())
    persona_order = ["baseline", "consultant", "saboteur", "altruist", "bard"]

    rows = ["<table><thead><tr><th>Model</th><th>Frame</th><th>Suspected test?</th><th>Said it affected play?</th></tr></thead><tbody>"]
    for model in models:
        for frame in frames:
            sub = active[(active["model_short"] == model) & (active["frame"] == frame)]
            if sub.empty:
                continue
            st = sub["suspected_test_num"].mean()
            ap = sub["affected_play_num"].mean()
            tag = f'<span class="tag tag-{"m" if frame=="matrix" else "n"}">{frame}</span>'
            st_str = pct(st) if not pd.isna(st) else "—"
            ap_str = pct(ap) if not pd.isna(ap) else "—"
            rows.append(f"<tr><td><b>{model}</b></td><td>{tag}</td><td>{st_str}</td><td>{ap_str}</td></tr>")
    rows.append("</tbody></table>")

    # by persona
    pivot_sus = active.pivot_table(
        index="model_short", columns="persona", values="suspected_test_num", aggfunc="mean"
    )
    cols = [c for c in persona_order if c in pivot_sus.columns]
    pivot_sus = pivot_sus[cols]

    return f"""<div class="section">
<h2>Eval Awareness</h2>
<h3>% of trials where model said it suspected it was being tested</h3>
{"".join(rows)}
<h3>Suspicion rate by model × persona</h3>
{heatmap_table(pivot_sus)}
</div>"""


def section_opponent_breakdown(trials: pd.DataFrame) -> str:
    active = trials[trials["stage_b_skipped"] == False].copy()
    if active.empty:
        return ""
    active["model_short"] = active["model"].apply(short_model)
    opponents = sorted(active["opponent"].unique())

    pivot = active.pivot_table(
        index="model_short", columns="opponent", values="deviation_rate", aggfunc="mean"
    )
    pivot = pivot[[c for c in opponents if c in pivot.columns]]

    return f"""<div class="section">
<h2>Deviation Rate by Opponent Strategy</h2>
<h3>Mean deviation rate per model × opponent</h3>
{heatmap_table(pivot)}
</div>"""


def section_run_summary(trials: pd.DataFrame) -> str:
    active = trials[trials["stage_b_skipped"] == False].copy()
    active["model_short"] = active["model"].apply(short_model)
    all_trials = trials.copy()
    all_trials["model_short"] = all_trials["model"].apply(short_model)

    rows = ["<table><thead><tr><th>Model</th><th>Frame</th><th>inject_optimal</th>"
            "<th>Trials</th><th>Played</th><th>Skip rate</th><th>Mean deviation</th><th>Mean payoff cost</th></tr></thead><tbody>"]
    for (model, frame, inj), grp in all_trials.groupby(["model_short", "frame", "inject_optimal"]):
        n_total = len(grp)
        n_played = len(grp[grp["stage_b_skipped"] == False])
        skip = 1 - n_played / n_total if n_total else 0
        played = grp[grp["stage_b_skipped"] == False]
        dev = played["deviation_rate"].mean() if "deviation_rate" in played and not played.empty else float("nan")
        cost = played["payoff_cost"].mean() if "payoff_cost" in played and not played.empty else float("nan")
        tag = f'<span class="tag tag-{"m" if frame=="matrix" else "n"}">{frame}</span>'
        inj_str = "✓" if inj else "—"
        dev_str = pct(dev) if not math.isnan(dev) else "—"
        cost_str = f"{cost:+.1f}" if not math.isnan(cost) else "—"
        rows.append(f"<tr><td><b>{model}</b></td><td>{tag}</td><td>{inj_str}</td>"
                    f"<td>{n_total}</td><td>{n_played}</td><td>{pct(skip)}</td>"
                    f"<td>{dev_str}</td><td>{cost_str}</td></tr>")
    rows.append("</tbody></table>")

    return f"""<div class="section">
<h2>Run Summary</h2>
{"".join(rows)}
</div>"""


# ── main ─────────────────────────────────────────────────────────────────────

def build_report(runs_dir: Path, out: Path) -> None:
    print(f"Loading runs from {runs_dir} …")
    trials, rounds, checks = load_runs(runs_dir)
    print(f"  {len(trials)} trials, {len(rounds)} rounds, {len(checks)} persona checks")

    body = "\n".join([
        section_overview(trials, rounds),
        section_run_summary(trials),
        section_persona_checks(checks, trials),
        section_deviation(trials, rounds),
        section_payoff(trials),
        section_eval_awareness(trials),
        section_opponent_breakdown(trials),
    ])

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Persona Deviation Harness — Results</title>
{CHART_JS}
<style>{CSS}</style>
</head>
<body>
<h1>Persona Deviation Harness</h1>
<p class="subtitle">Iterated Prisoner's Dilemma · inject_optimal=True · {trials['model'].nunique()} models · {len(trials)} trials</p>
{body}
</body>
</html>"""

    out.write_text(html, encoding="utf-8")
    print(f"Report written → {out.resolve()}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs-dir", default="runs/full")
    ap.add_argument("--out", default="report.html")
    args = ap.parse_args()
    build_report(Path(args.runs_dir), Path(args.out))
