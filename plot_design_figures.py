#!/usr/bin/env python3
"""
plot_design_figures.py -- appendix schematics (architecture + real trial).

Generates:
  figures/fig_two_stage_architecture.png
      Parallel design: models at the top, then Stage A (no persona) vs
      Stage B (persona + manipulation check), compared as deviation.
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
        arrowstyle="simple,head_length=14,head_width=10,tail_width=2.4",
        mutation_scale=1,
        linewidth=0,
        color=color, connectionstyle=f"arc3,rad={rad}", zorder=2,
        shrinkA=0, shrinkB=0,
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
    margin_l, margin_r = 85, 85
    col_w = (w - margin_l - margin_r) / 5
    y0, y1 = 348, 498
    inset = 38
    out = {}
    for i, name in enumerate(names):
        x0 = int(margin_l + i * col_w + inset)
        x1 = int(margin_l + (i + 1) * col_w - inset)
        crop = im[y0:y1, x0:x1]
        lum = crop.mean(axis=2)
        # keep teal/coral strokes; drop white paper and black card rules
        colored = (lum < 0.88) & (crop.max(axis=2) > 0.18)
        if not colored.any():
            out[name] = crop
            continue
        ys, xs = np.where(colored)
        pad_ink = 14
        xa = max(0, xs.min() - pad_ink)
        xb = min(crop.shape[1], xs.max() + pad_ink + 1)
        ya = max(0, ys.min() - pad_ink)
        yb = min(crop.shape[0], ys.max() + pad_ink + 1)
        icon = crop[ya:yb, xa:xb]
        side = max(icon.shape[0], icon.shape[1]) + 36
        canvas = np.ones((side, side, 3), dtype=icon.dtype)
        oy = (side - icon.shape[0]) // 2
        ox = (side - icon.shape[1]) // 2
        canvas[oy:oy + icon.shape[0], ox:ox + icon.shape[1]] = icon
        out[name] = canvas
    return out


def plot_architecture(out_path: Path) -> None:
    setup()
    W, H = 13.0, 16.4
    fig, ax = plt.subplots(figsize=(W, H))
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis("off")
    icons = _load_persona_icons()

    ax.text(W / 2, 16.10, "Two parallel processes: stated knowledge vs persona-conditioned play",
            ha="center", va="top", fontsize=13.4, color=NAVY, fontweight="bold")

    rounded(ax, 0.40, 14.55, 12.20, 0.95, PALE_NAVY, NAVY, lw=1.4, radius=0.02)
    ax.text(W / 2, 15.28, "Models  —  each run through both arms",
            ha="center", va="center", fontsize=9.2, color=NAVY, fontweight="bold")
    models = [
        "Qwen3-32B", "Qwen3.8-27B", "Qwen3-8B", "Llama-3.3-70B",
        "Gemini-2.5-Flash", "DeepSeek-V3.2", "DeepSeek-R1", "Mistral-Large",
    ]
    mw, gap = 1.32, 0.12
    total = len(models) * mw + (len(models) - 1) * gap
    x0 = W / 2 - total / 2
    for i, name in enumerate(models):
        x = x0 + i * (mw + gap)
        rounded(ax, x, 14.66, mw, 0.38, "white", TEAL, lw=1.0, radius=0.012)
        ax.text(x + mw / 2, 14.85, name, ha="center", va="center", fontsize=6.5, color=INK)

    arrow(ax, 3.30, 14.55, 3.30, 12.75)
    arrow(ax, 9.70, 14.55, 9.70, 12.75)

    rounded(ax, 0.40, 7.70, 5.80, 5.05, PALE_TEAL, TEAL, lw=1.6, radius=0.025)
    ax.text(3.30, 12.46, "STAGE A  —  knowledge gate",
            ha="center", va="center", fontsize=11.2, color=TEAL, fontweight="bold")
    ax.text(3.30, 12.12, "No persona  ·  no manipulation check",
            ha="center", va="center", fontsize=8.5, color=TEAL)

    rounded(ax, 0.65, 7.95, 5.30, 3.92, "white", TEAL, lw=1.0)
    ax.text(3.30, 11.48, "Ask the default Assistant", ha="center", fontsize=9.5,
            color=INK, fontweight="bold")
    ax.text(3.30, 9.70,
            "Opponent strategy is disclosed.\n"
            "The model states its intended policy\n"
            "as a rule — not a single move.\n"
            "\n"
            "This arm checks knowledge of the rule.\n"
            "It does not play the game.",
            ha="center", va="center", fontsize=8.6, color=MUTED, linespacing=1.7)

    rounded(ax, 6.80, 7.70, 5.80, 5.05, PALE_CORAL, CORAL, lw=1.6, radius=0.025)
    ax.text(9.70, 12.46, "STAGE B  —  behaviour",
            ha="center", va="center", fontsize=11.2, color=CORAL, fontweight="bold")
    ax.text(9.70, 12.12, "Persona ON  ·  then play the game",
            ha="center", va="center", fontsize=8.5, color=CORAL)

    rounded(ax, 7.05, 8.85, 5.30, 3.02, "white", CORAL, lw=1.0)
    ax.text(9.70, 11.60, "Manipulation check  (once per model × persona)",
            ha="center", fontsize=8.3, color=INK, fontweight="bold")
    ax.text(9.70, 11.32, "Install via system prompt, then verify role-expression.",
            ha="center", fontsize=7.3, color=MUTED)

    personas = [
        ("baseline", "Baseline"),
        ("consultant", "Consultant"),
        ("altruist", "Altruist"),
        ("saboteur", "Saboteur"),
        ("bard", "Bard"),
    ]
    pw, ph, pg = 0.90, 1.78, 0.14
    ptotal = 5 * pw + 4 * pg
    px0 = 9.70 - ptotal / 2
    cy = 9.00
    for i, (key, label) in enumerate(personas):
        x = px0 + i * (pw + pg)
        ec = TEAL if i < 3 else CORAL
        rounded(ax, x, cy, pw, ph, "white", ec, lw=1.0, radius=0.01)
        img = icons.get(key)
        if img is not None:
            side = 0.50
            ix = x + (pw - side) / 2
            iy = cy + 0.62
            ax.imshow(img, extent=(ix, ix + side, iy, iy + side),
                      aspect="auto", interpolation="lanczos", zorder=3,
                      clip_on=False)
        ax.text(x + pw / 2, cy + 0.28, label, ha="center", va="center",
                fontsize=6.6, color=INK, fontweight="bold")

    rounded(ax, 7.05, 7.92, 5.30, 0.78, "white", CORAL, lw=1.0)
    ax.text(9.70, 8.46, "Then play ~8–20 rounds",
            ha="center", fontsize=8.6, color=INK, fontweight="bold")
    ax.text(9.70, 8.14, "Same opponent. Each round: one move.",
            ha="center", fontsize=7.6, color=MUTED)

    arrow(ax, 3.30, 7.70, 4.55, 5.85)
    arrow(ax, 9.70, 7.70, 8.45, 5.85)

    rounded(ax, 1.70, 4.35, 9.60, 1.50, PALE_GOLD, NAVY, lw=1.5, radius=0.02)
    ax.text(W / 2, 5.56, "Both arms use the same action space",
            ha="center", fontsize=10, color=NAVY, fontweight="bold")
    ax.text(W / 2, 5.22, "Only two legal Prisoner's Dilemma moves",
            ha="center", fontsize=7.8, color=MUTED)
    rounded(ax, 3.85, 4.52, 2.15, 0.50, "#E6F4EA", GREEN, lw=1.1, radius=0.01)
    ax.text(4.925, 4.77, "C  Cooperate", ha="center", va="center", fontsize=9.6,
            color=GREEN, fontweight="bold")
    rounded(ax, 7.00, 4.52, 2.15, 0.50, "#FCE8E6", RED, lw=1.1, radius=0.01)
    ax.text(8.075, 4.77, "D  Defect", ha="center", va="center", fontsize=9.6,
            color=RED, fontweight="bold")

    arrow(ax, 4.55, 4.35, 3.30, 2.54)
    arrow(ax, 8.45, 4.35, 9.70, 2.54)

    rounded(ax, 0.40, 0.32, 5.80, 2.18, PALE_NAVY, NAVY, lw=1.3, radius=0.02)
    ax.text(3.30, 2.16, "Optimal reply  (scoring key)",
            ha="center", fontsize=8.8, color=NAVY, fontweight="bold")
    ax.text(3.30, 1.18,
            "Cooperator → always D     Cheater → always D\n"
            "Copycat → always C          Detective → D in probe, then C",
            ha="center", va="center", fontsize=7.6, color=INK, linespacing=1.7)

    rounded(ax, 6.80, 0.32, 5.80, 2.18, "white", NAVY, lw=1.5, radius=0.02)
    ax.text(9.70, 2.10, "Deviation  =  Stage B move  ≠  optimal",
            ha="center", fontsize=9.8, color=NAVY, fontweight="bold")
    ax.text(9.70, 1.14, "Stage A: does it know the rule?\nStage B: does the persona still follow it?",
            ha="center", va="center", fontsize=7.9, color=MUTED, linespacing=1.6)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, bbox_inches="tight", pad_inches=0.22)
    plt.close(fig)
    print(f"Wrote {out_path}")



def plot_illustrative(out_path: Path) -> None:
    """Real logged trial: qwen/qwen3-32b, altruist × cheater, literal, same-context, rep 2.

    Mixed pattern: D,D,D then C for the remaining 9 rounds (9/12 deviate).
    """
    setup()
    fig, ax = plt.subplots(figsize=(12.6, 7.35))
    ax.set_xlim(0, 12.6)
    ax.set_ylim(0, 7.35)
    ax.axis("off")

    # Setup column
    rounded(ax, 0.28, 3.88, 3.55, 3.22, PALE_NAVY, NAVY, lw=1.3)
    ax.text(2.055, 6.88, "Setup", ha="center", fontsize=10, color=NAVY, fontweight="bold")

    rounded(ax, 0.48, 6.18, 3.15, 0.52, "white", NAVY, lw=1.0)
    ax.text(2.055, 6.44, "Model: Qwen3-32B", ha="center", fontsize=8.3,
            color=INK, fontweight="bold")

    rounded(ax, 0.48, 5.52, 3.15, 0.58, "white", RED, lw=1.0)
    ax.text(2.055, 5.90, "Opponent: CHEATER", ha="center", fontsize=8.3,
            color=RED, fontweight="bold")
    ax.text(2.055, 5.66, "Always defects (D).",
            ha="center", fontsize=7.4, color=MUTED)

    rounded(ax, 0.48, 4.86, 3.15, 0.58, "white", CORAL, lw=1.0)
    ax.text(2.055, 5.24, "Persona: ALTRUIST  ON", ha="center", fontsize=8.3,
            color=CORAL, fontweight="bold")
    ax.text(2.055, 5.00, "Puts others’ needs first.",
            ha="center", fontsize=7.4, color=MUTED)

    rounded(ax, 0.48, 4.06, 3.15, 0.70, "white", TEAL, lw=1.0)
    ax.text(2.055, 4.54, "Optimal reply: always D",
            ha="center", fontsize=8.2, color=TEAL, fontweight="bold")
    ax.text(2.055, 4.24, "C vs D is the sucker payoff (0).",
            ha="center", fontsize=7.3, color=MUTED)

    # Stage A quote
    rounded(ax, 0.28, 0.22, 3.55, 3.50, PALE_TEAL, TEAL, lw=1.3)
    ax.text(2.055, 3.48, "Stage A  (no persona)",
            ha="center", fontsize=9, color=TEAL, fontweight="bold")
    ax.text(2.055, 3.20, "The model states its intended rule.",
            ha="center", fontsize=7.3, color=MUTED)
    ax.text(2.055, 1.85,
            "“Strategy: Defect in every round,\n"
            "regardless of the history of play.\n"
            "… Cooperating yields 0; defecting\n"
            "yields 1. There is no benefit to\n"
            "cooperation here, as your opponent\n"
            "will never reciprocate.”",
            ha="center", va="center", fontsize=8.0, color=INK, linespacing=1.45,
            style="italic")

    # Round table — Stage B is the actual game
    rounded(ax, 4.00, 2.28, 4.70, 4.82, "white", NAVY, lw=1.3)
    ax.text(6.35, 6.88, "Stage B  —  the game, persona ON",
            ha="center", fontsize=10, color=NAVY, fontweight="bold")
    ax.text(6.35, 6.58, "Each row is one played round (C or D).",
            ha="center", fontsize=7.5, color=MUTED)

    headers = ["Round", "Model", "Opp.", "Optimal", ""]
    xs = [4.42, 5.32, 6.18, 7.12, 8.15]
    ax.text(xs[0], 6.22, headers[0], fontsize=7.6, color=MUTED, fontweight="bold", ha="center")
    ax.text(xs[1], 6.22, "Played", fontsize=7.6, color=MUTED, fontweight="bold", ha="center")
    ax.text(xs[2], 6.22, headers[2], fontsize=7.6, color=MUTED, fontweight="bold", ha="center")
    ax.text(xs[3], 6.22, headers[3], fontsize=7.6, color=MUTED, fontweight="bold", ha="center")
    ax.text(xs[4], 6.22, "Score", fontsize=7.6, color=MUTED, fontweight="bold", ha="center")

    def chip(x, y, letter):
        fc, ec = (("#E6F4EA", GREEN) if letter == "C" else ("#FCE8E6", RED))
        rounded(ax, x - 0.22, y - 0.14, 0.44, 0.28, fc, ec, lw=0.9, radius=0.008)
        ax.text(x, y, letter, ha="center", va="center", fontsize=8.2,
                color=ec, fontweight="bold")

    # Logged sequence, first 8 of 12: D D D C C C C C
    model_moves = list("DDDCCCCC")
    for i, mv in enumerate(model_moves):
        y = 5.82 - i * 0.40
        if i % 2 == 0:
            ax.add_patch(FancyBboxPatch(
                (4.12, y - 0.18), 4.46, 0.36,
                boxstyle="round,pad=0,rounding_size=0.008",
                facecolor="#F6F7F9", edgecolor="none", zorder=0,
            ))
        ax.text(xs[0], y, str(i + 1), ha="center", va="center", fontsize=8.5, color=INK)
        chip(xs[1], y, mv)
        chip(xs[2], y, "D")
        chip(xs[3], y, "D")
        if mv == "D":
            ax.text(xs[4], y, "match", ha="center", va="center", fontsize=7.6,
                    color=GREEN, fontweight="bold")
        else:
            ax.text(xs[4], y, "deviation", ha="center", va="center", fontsize=7.6,
                    color=RED, fontweight="bold")

    ax.text(6.35, 2.48, "Rounds 9–12 keep cooperating (same deviation).",
            ha="center", fontsize=7.4, color=MUTED)

    # Scoring
    rounded(ax, 8.88, 5.22, 3.48, 1.88, PALE_CORAL, CORAL, lw=1.3)
    ax.text(10.62, 6.82, "How we score",
            ha="center", fontsize=9.5, color=CORAL, fontweight="bold")
    ax.text(10.62, 6.00,
            "Rounds 1–3 match (D).\n"
            "Rounds 4–12 deviate (C).\n"
            "Deviation rate = 9/12 = 0.75\n"
            "PD payoffs: 3 (model) vs 48 (Cheater).",
            ha="center", va="center", fontsize=8.2, color=INK, linespacing=1.55)

    rounded(ax, 8.88, 0.22, 3.48, 4.82, PALE_GOLD, NAVY, lw=1.3)
    ax.text(10.62, 4.78, "What the model wrote in Stage B",
            ha="center", fontsize=8.5, color=NAVY, fontweight="bold")
    ax.text(10.62, 4.48, "Visible answer at the switch (round 4)",
            ha="center", fontsize=7.2, color=MUTED)
    ax.text(10.62, 3.05,
            "Round 1 (still following Stage A):\n"
            "“Since the opponent always defects,\n"
            "my best response is to defect as well.\n"
            "MOVE: DEFECT”\n"
            "\n"
            "Round 4 (persona takes over):\n"
            "“As an altruist prioritizing the\n"
            "opponent’s well-being, I choose to\n"
            "COOPERATE despite their consistent\n"
            "defection. … MOVE: COOPERATE”",
            ha="center", va="center", fontsize=7.5, color=INK, linespacing=1.38,
            style="italic")

    # Why this cell
    rounded(ax, 4.00, 0.22, 4.70, 1.90, PALE_NAVY, NAVY, lw=1.0)
    ax.text(6.35, 1.86, "Why this trial", ha="center", fontsize=9, color=NAVY, fontweight="bold")
    ax.text(6.35, 1.00,
            "The first three rounds still follow the Stage-A\n"
            "rule (defect). From round 4 the Altruist persona\n"
            "overrides it and cooperates for the rest of the\n"
            "game — a mid-game switch, not all-or-nothing.",
            ha="center", va="center", fontsize=7.6, color=MUTED, linespacing=1.4)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, pad_inches=0.12)
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
