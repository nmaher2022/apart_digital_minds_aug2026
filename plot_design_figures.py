#!/usr/bin/env python3
"""
plot_design_figures.py -- appendix schematics (architecture + real trial).

Generates:
  figures/fig_two_stage_architecture.png
      Parallel design: models at the top, then optimal strategy (no persona) vs
      persona play (persona + manipulation check), compared as deviation.
  figures/fig_illustrative_example.png
      Logged trial: qwen/qwen3-32b, altruist × cheater × literal, same-context, rep 7.

Usage:
  python plot_design_figures.py --out-dir figures
"""

from __future__ import annotations

import argparse
from pathlib import Path

from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import matplotlib.pyplot as plt


TEAL = "#2A6F7F"
CORAL = "#C45C3E"
NAVY = "#1F2A37"
INK = "#243040"
MUTED = "#5B6773"
PALE_TEAL = "#E7F2F4"
PALE_CORAL = "#F8EBE6"
PALE_NAVY = "#EEF1F4"
PALE_GOLD = "#F7F1E3"
GREEN = "#2E7D4F"
RED = "#B42318"


def setup():
    plt.rcParams.update({
        "font.size": 9.5,
        "font.family": "sans-serif",
        "axes.titlesize": 12,
        "figure.dpi": 160,
        "savefig.dpi": 220,
        "savefig.bbox": "tight",
        "savefig.facecolor": "white",
        "figure.facecolor": "white",
    })


def rounded(ax, x, y, w, h, fc, ec, lw=1.3, radius=0.018, z=1):
    p = FancyBboxPatch(
        (x, y), w, h,
        boxstyle=f"round,pad=0.008,rounding_size={radius}",
        facecolor=fc, edgecolor=ec, linewidth=lw, zorder=z,
        mutation_aspect=1.0,
    )
    ax.add_patch(p)
    return p


def arrow(ax, x1, y1, x2, y2, color=NAVY, rad=0.0):
    ax.add_patch(FancyArrowPatch(
        (x1, y1), (x2, y2),
        arrowstyle="simple,head_length=9,head_width=7,tail_width=1.6",
        mutation_scale=1,
        linewidth=0,
        color=color, connectionstyle=f"arc3,rad={rad}", zorder=2,
        shrinkA=1, shrinkB=1,
    ))


def _load_persona_icons() -> dict[str, object]:
    """Icon-only crops from fig_five_personas.png, on a padded white square (no card borders)."""
    import numpy as np
    import matplotlib.image as mpimg

    src = Path(__file__).resolve().parent / "figures" / "fig_five_personas.png"
    if not src.exists():
        return {}
    im = mpimg.imread(src)[..., :3]
    _, w = im.shape[:2]
    names = ["baseline", "consultant", "altruist", "saboteur", "bard"]
    # five equal columns; small inset skips the card rule without eating the drawing
    margin_l, margin_r = 72, 70
    col_w = (w - margin_l - margin_r) / 5
    y0, y1 = 335, 500
    inset = 14
    out = {}
    for i, name in enumerate(names):
        x0 = int(margin_l + i * col_w + inset)
        x1 = int(margin_l + (i + 1) * col_w - inset)
        crop = np.clip(im[y0:y1, x0:x1], 0, 1)
        lum = crop.mean(axis=2)
        crop[:, lum.mean(axis=0) < 0.70] = 1.0
        crop[lum.mean(axis=1) < 0.70, :] = 1.0
        pad = 22
        ch, cw = crop.shape[:2]
        canvas = np.ones((ch + 2 * pad, cw + 2 * pad, 3), dtype=np.float32)
        canvas[pad:pad + ch, pad:pad + cw] = crop
        out[name] = canvas
    return out


def plot_architecture(out_path: Path) -> None:
    setup()
    W, H = 13.0, 13.2
    fig, ax = plt.subplots(figsize=(13.0, 10.0))
    ax.set_xlim(0, W)
    ax.set_ylim(3.50, 13.2)
    ax.axis("off")
    icons = _load_persona_icons()

    ax.text(W / 2, 12.95, "Two parallel processes: optimal strategy vs persona play",
            ha="center", va="top", fontsize=15.2, color=NAVY, fontweight="bold")

    rounded(ax, 0.40, 11.62, 12.20, 0.92, PALE_NAVY, NAVY, lw=1.4, radius=0.02)
    ax.text(W / 2, 12.32, "Models  —  each run through both arms",
            ha="center", va="center", fontsize=11.2, color=NAVY, fontweight="bold")
    models = [
        "Qwen3-32B", "Qwen3.8-27B", "Qwen3-8B", "Llama-3.3-70B",
        "Gemini-2.5-Flash", "DeepSeek-V3.2", "DeepSeek-R1", "Mistral-Large",
    ]
    mw, gap = 1.32, 0.12
    total = len(models) * mw + (len(models) - 1) * gap
    x0 = W / 2 - total / 2
    for i, name in enumerate(models):
        x = x0 + i * (mw + gap)
        rounded(ax, x, 11.74, mw, 0.40, "white", TEAL, lw=1.0, radius=0.012)
        ax.text(x + mw / 2, 11.94, name, ha="center", va="center", fontsize=7.6, color=INK)

    arrow(ax, 3.30, 11.62, 3.30, 10.72)
    arrow(ax, 9.70, 11.62, 9.70, 10.72)

    rounded(ax, 0.40, 7.38, 5.80, 3.34, PALE_TEAL, TEAL, lw=1.6, radius=0.025)
    ax.text(3.30, 10.44, "OPTIMAL STRATEGY",
            ha="center", va="center", fontsize=13.0, color=TEAL, fontweight="bold")
    ax.text(3.30, 10.12, "No persona  ·  no manipulation check",
            ha="center", va="center", fontsize=10.0, color=TEAL)

    rounded(ax, 0.65, 7.56, 5.30, 2.30, "white", TEAL, lw=1.0)
    ax.text(3.30, 9.58, "Ask the default Assistant", ha="center", fontsize=11.2,
            color=INK, fontweight="bold")
    ax.text(3.30, 8.52,
            "Opponent strategy is disclosed.\n"
            "The model states its intended policy\n"
            "as a rule — not a single move.\n"
            "\n"
            "This arm checks knowledge of the rule.\n"
            "It does not play the game.",
            ha="center", va="center", fontsize=10.2, color=MUTED, linespacing=1.5)

    rounded(ax, 6.80, 7.38, 5.80, 3.34, PALE_CORAL, CORAL, lw=1.6, radius=0.025)
    ax.text(9.70, 10.44, "PERSONA PLAY",
            ha="center", va="center", fontsize=13.0, color=CORAL, fontweight="bold")
    ax.text(9.70, 10.12, "Persona ON  ·  then play the game",
            ha="center", va="center", fontsize=10.0, color=CORAL)

    rounded(ax, 7.05, 8.18, 5.30, 1.56, "white", CORAL, lw=1.0)
    ax.text(9.70, 9.54, "Manipulation check  (once per model × persona)",
            ha="center", fontsize=9.8, color=INK, fontweight="bold")
    ax.text(9.70, 9.28, "Install via system prompt, then verify role-expression.",
            ha="center", fontsize=8.6, color=MUTED)

    personas = [
        ("baseline", "Baseline"),
        ("consultant", "Consultant"),
        ("altruist", "Altruist"),
        ("saboteur", "Saboteur"),
        ("bard", "Bard"),
    ]
    pw, ph, pg = 0.96, 0.90, 0.10
    ptotal = 5 * pw + 4 * pg
    px0 = 9.70 - ptotal / 2
    cy = 8.30
    for i, (key, label) in enumerate(personas):
        x = px0 + i * (pw + pg)
        ec = TEAL if i < 3 else CORAL
        rounded(ax, x, cy, pw, ph, "white", ec, lw=1.0, radius=0.01)
        img = icons.get(key)
        if img is not None:
            ih, iw = img.shape[:2]
            aspect = iw / float(ih)
            max_w, max_h = pw - 0.10, ph - 0.26
            if max_w / max_h > aspect:
                side_h = max_h
                side_w = side_h * aspect
            else:
                side_w = max_w
                side_h = side_w / aspect
            ix = x + (pw - side_w) / 2
            iy = cy + 0.24
            ax.imshow(img, extent=(ix, ix + side_w, iy, iy + side_h),
                      aspect="auto", interpolation="lanczos", zorder=3,
                      clip_on=False)
        ax.text(x + pw / 2, cy + 0.13, label, ha="center", va="center",
                fontsize=8.0, color=INK, fontweight="bold")

    rounded(ax, 7.05, 7.54, 5.30, 0.56, "white", CORAL, lw=1.0)
    ax.text(9.70, 7.92, "Then play ~8–20 rounds",
            ha="center", fontsize=10.2, color=INK, fontweight="bold")
    ax.text(9.70, 7.68, "Same opponent. Each round: one move.",
            ha="center", fontsize=8.8, color=MUTED)

    arrow(ax, 3.30, 7.38, 4.55, 6.50)
    arrow(ax, 9.70, 7.38, 8.45, 6.50)

    rounded(ax, 1.70, 5.12, 9.60, 1.36, PALE_GOLD, NAVY, lw=1.5, radius=0.02)
    ax.text(W / 2, 6.22, "Both arms use the same action space",
            ha="center", fontsize=11.4, color=NAVY, fontweight="bold")
    ax.text(W / 2, 5.90, "Only two legal Prisoner's Dilemma moves",
            ha="center", fontsize=9.2, color=MUTED)
    rounded(ax, 3.75, 5.26, 2.25, 0.48, "#E6F4EA", GREEN, lw=1.1, radius=0.01)
    ax.text(4.875, 5.50, "C  Cooperate", ha="center", va="center", fontsize=11.0,
            color=GREEN, fontweight="bold")
    rounded(ax, 7.00, 5.26, 2.25, 0.48, "#FCE8E6", RED, lw=1.1, radius=0.01)
    ax.text(8.125, 5.50, "D  Defect", ha="center", va="center", fontsize=11.0,
            color=RED, fontweight="bold")

    arrow(ax, 4.55, 5.12, 3.30, 4.82)
    arrow(ax, 8.45, 5.12, 9.70, 4.82)

    rounded(ax, 0.40, 3.68, 5.80, 1.04, PALE_NAVY, NAVY, lw=1.3, radius=0.02)
    ax.text(3.30, 4.44, "Optimal reply  (scoring key)",
            ha="center", fontsize=10.6, color=NAVY, fontweight="bold")
    ax.text(3.30, 4.02,
            "Cooperator → always D     Cheater → always D\n"
            "Copycat → always C          Detective → D in probe, then C",
            ha="center", va="center", fontsize=9.0, color=INK, linespacing=1.45)

    rounded(ax, 6.80, 3.68, 5.80, 1.04, "white", NAVY, lw=1.5, radius=0.02)
    ax.text(9.70, 4.42, "Deviation  =  persona-play move  ≠  optimal",
            ha="center", fontsize=11.0, color=NAVY, fontweight="bold")
    ax.text(9.70, 4.00, "Optimal strategy: does it know the rule?\nPersona play: does the persona still follow it?",
            ha="center", va="center", fontsize=9.2, color=MUTED, linespacing=1.35)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, bbox_inches="tight", pad_inches=0.18)
    plt.close(fig)
    print(f"Wrote {out_path}")



def plot_illustrative(out_path: Path) -> None:
    """Real logged trial: qwen/qwen3-32b, altruist × cheater, literal, same-context, rep 2.

    Mixed pattern: D,D,D then C. Figure shows rounds 1–6; the remaining rounds stay C.
    """
    setup()
    W, H = 12.6, 6.05
    fig, ax = plt.subplots(figsize=(W, H))
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis("off")
    cx_l = 2.055

    rounded(ax, 0.22, 3.22, 3.67, 2.65, PALE_NAVY, NAVY, lw=1.3)
    ax.text(cx_l, 5.66, "Setup", ha="center", fontsize=10.2, color=NAVY, fontweight="bold")

    rounded(ax, 0.40, 5.08, 3.31, 0.40, "white", NAVY, lw=1.0)
    ax.text(cx_l, 5.28, "Model: Qwen3-32B", ha="center", fontsize=8.5,
            color=INK, fontweight="bold")

    rounded(ax, 0.40, 4.54, 3.31, 0.48, "white", RED, lw=1.0)
    ax.text(cx_l, 4.86, "Opponent: CHEATER", ha="center", fontsize=8.5,
            color=RED, fontweight="bold")
    ax.text(cx_l, 4.64, "Always defects (D).", ha="center", fontsize=7.5, color=MUTED)

    rounded(ax, 0.40, 4.00, 3.31, 0.48, "white", CORAL, lw=1.0)
    ax.text(cx_l, 4.32, "Persona: ALTRUIST  ON", ha="center", fontsize=8.5,
            color=CORAL, fontweight="bold")
    ax.text(cx_l, 4.10, "Puts others’ needs first.", ha="center", fontsize=7.5, color=MUTED)

    rounded(ax, 0.40, 3.36, 3.31, 0.58, "white", TEAL, lw=1.0)
    ax.text(cx_l, 3.76, "Optimal reply: always D", ha="center", fontsize=8.4,
            color=TEAL, fontweight="bold")
    ax.text(cx_l, 3.50, "C vs D is the sucker payoff (0).",
            ha="center", fontsize=7.4, color=MUTED)

    rounded(ax, 0.22, 0.18, 3.67, 2.90, PALE_TEAL, TEAL, lw=1.3)
    ax.text(cx_l, 2.86, "Optimal strategy  (no persona)",
            ha="center", fontsize=9.4, color=TEAL, fontweight="bold")
    ax.text(cx_l, 2.60, "The model states its intended rule.",
            ha="center", fontsize=7.5, color=MUTED)
    ax.text(cx_l, 1.42,
            "“Strategy: Defect in every round,\n"
            "regardless of the history of play.\n"
            "… Cooperating yields 0; defecting\n"
            "yields 1. There is no benefit to\n"
            "cooperation here, as your opponent\n"
            "will never reciprocate.”",
            ha="center", va="center", fontsize=8.1, color=INK, linespacing=1.42,
            style="italic")

    rounded(ax, 4.04, 1.88, 4.62, 3.99, "white", NAVY, lw=1.3)
    ax.text(6.35, 5.64, "Persona play  —  the game, persona ON",
            ha="center", fontsize=10.2, color=NAVY, fontweight="bold")
    ax.text(6.35, 5.38, "Each row is one played round (C or D).",
            ha="center", fontsize=7.6, color=MUTED)

    xs = [4.46, 5.34, 6.18, 7.10, 8.10]
    ax.text(xs[0], 5.08, "Round", fontsize=7.7, color=MUTED, fontweight="bold", ha="center")
    ax.text(xs[1], 5.08, "Played", fontsize=7.7, color=MUTED, fontweight="bold", ha="center")
    ax.text(xs[2], 5.08, "Opp.", fontsize=7.7, color=MUTED, fontweight="bold", ha="center")
    ax.text(xs[3], 5.08, "Optimal", fontsize=7.7, color=MUTED, fontweight="bold", ha="center")
    ax.text(xs[4], 5.08, "Score", fontsize=7.7, color=MUTED, fontweight="bold", ha="center")

    def chip(x, y, letter):
        fc, ec = (("#E6F4EA", GREEN) if letter == "C" else ("#FCE8E6", RED))
        rounded(ax, x - 0.22, y - 0.14, 0.44, 0.28, fc, ec, lw=0.9, radius=0.008)
        ax.text(x, y, letter, ha="center", va="center", fontsize=8.3,
                color=ec, fontweight="bold")

    model_moves = list("DDDCCC")
    for i, mv in enumerate(model_moves):
        y = 4.72 - i * 0.42
        if i % 2 == 0:
            ax.add_patch(FancyBboxPatch(
                (4.16, y - 0.18), 4.38, 0.38,
                boxstyle="round,pad=0,rounding_size=0.008",
                facecolor="#F6F7F9", edgecolor="none", zorder=0,
            ))
        ax.text(xs[0], y, str(i + 1), ha="center", va="center", fontsize=8.6, color=INK)
        chip(xs[1], y, mv)
        chip(xs[2], y, "D")
        chip(xs[3], y, "D")
        if mv == "D":
            ax.text(xs[4], y, "match", ha="center", va="center", fontsize=7.7,
                    color=GREEN, fontweight="bold")
        else:
            ax.text(xs[4], y, "deviation", ha="center", va="center", fontsize=7.7,
                    color=RED, fontweight="bold")

    ax.text(6.35, 2.08, "Rounds 7–12 stay C (same deviation, not shown).",
            ha="center", fontsize=7.3, color=MUTED)

    rounded(ax, 8.82, 4.42, 3.56, 1.45, PALE_CORAL, CORAL, lw=1.3)
    ax.text(10.60, 5.62, "How we score",
            ha="center", fontsize=10.0, color=CORAL, fontweight="bold")
    ax.text(10.60, 4.98,
            "Rounds 1–3 match (D).  4–12 deviate (C).\n"
            "Deviation rate = 9/12 = 0.75\n"
            "PD payoffs: 3 (model) vs 48 (Cheater).",
            ha="center", va="center", fontsize=8.3, color=INK, linespacing=1.45)

    rounded(ax, 8.82, 0.18, 3.56, 4.10, PALE_GOLD, NAVY, lw=1.3)
    ax.text(10.60, 4.04, "What the model wrote in persona play",
            ha="center", fontsize=8.8, color=NAVY, fontweight="bold")
    ax.text(10.60, 3.76, "Visible answer at the switch (round 4)",
            ha="center", fontsize=7.3, color=MUTED)
    ax.text(10.60, 2.00,
            "Round 1 (still following optimal strategy):\n"
            "“Since the opponent always defects,\n"
            "my best response is to defect as well.\n"
            "MOVE: DEFECT”\n"
            "\n"
            "Round 4 (persona takes over):\n"
            "“As an altruist prioritizing the\n"
            "opponent’s well-being, I choose to\n"
            "COOPERATE despite their consistent\n"
            "defection. … MOVE: COOPERATE”",
            ha="center", va="center", fontsize=7.7, color=INK, linespacing=1.38,
            style="italic")

    rounded(ax, 4.04, 0.18, 4.62, 1.56, PALE_NAVY, NAVY, lw=1.0)
    ax.text(6.35, 1.50, "Why this trial", ha="center", fontsize=9.2, color=NAVY, fontweight="bold")
    ax.text(6.35, 0.80,
            "The first three rounds still follow the default\n"
            "strategy (defect). From round 4 the Altruist persona\n"
            "overrides it — a mid-game switch, not all-or-nothing.",
            ha="center", va="center", fontsize=7.7, color=MUTED, linespacing=1.38)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, pad_inches=0.10)
    plt.close(fig)
    print(f"Wrote {out_path}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out-dir", type=Path, default=Path("figures"))
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    plot_architecture(args.out_dir / "fig_two_stage_architecture.png")
    plot_illustrative(args.out_dir / "fig_illustrative_example.png")


if __name__ == "__main__":
    main()
