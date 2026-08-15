"""
Iterated Prisoner's Dilemma persona-deviation harness.

Usage:
    # set OPENROUTER_API_KEY in harness/.env, then:
    python main.py --opponents cooperator cheater copycat detective \\
        --personas baseline consultant saboteur altruist bard \\
        --reps 5 --out-dir runs

    # smoke test -- one cell, one rep, short game:
    python main.py --opponents cooperator --personas baseline --reps 1 \\
        --max-rounds 6 --out-dir runs

    # Each run creates its own subfolder inside --out-dir:
    #   runs/z-ai__glm-4.5_matrix_20260815-134201/
    #     trials.jsonl, persona_checks.jsonl, run.log
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import random
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

logger = logging.getLogger(__name__)


def setup_logging(out_dir: Path) -> None:
    fmt = logging.Formatter("%(asctime)s.%(msecs)03d %(levelname)-8s %(name)s | %(message)s",
                            datefmt="%H:%M:%S")
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    sh = logging.StreamHandler(sys.stderr)
    sh.setLevel(logging.INFO)   # INFO+ to console so it's readable
    sh.setFormatter(fmt)
    root.addHandler(sh)

    fh = logging.FileHandler(out_dir / "run.log", encoding="utf-8")
    fh.setLevel(logging.DEBUG)  # DEBUG to file — every API call + response
    fh.setFormatter(fmt)
    root.addHandler(fh)

import client
from client import HarnessError
from game import run_trial
from opponents import OPPONENT_DESCRIPTIONS
from personas import PERSONA_ORDER, build_personas


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", default="z-ai/glm-4.5",
                    help="OpenRouter model slug (default: z-ai/glm-4.5)")
    ap.add_argument("--opponents", nargs="+", default=list(OPPONENT_DESCRIPTIONS),
                    choices=list(OPPONENT_DESCRIPTIONS))
    ap.add_argument("--personas", nargs="+", default=PERSONA_ORDER, choices=PERSONA_ORDER)
    ap.add_argument("--reps", type=int, default=5)
    ap.add_argument("--horizon", choices=["probabilistic", "fixed"], default="fixed")
    ap.add_argument("--max-rounds", type=int, default=10,
                    help="cap on rounds per game (also fixed-range upper bound)")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--base-url", default=client.OPENROUTER_URL,
                    help="OpenAI-compatible base URL "
                         "(e.g. http://localhost:11434/v1 for local Ollama)")
    ap.add_argument("--api-key-env", default="OPENROUTER_API_KEY",
                    help="env var holding the API key (not required for local Ollama)")
    ap.add_argument("--frame", choices=["matrix", "narrative"], default="matrix",
                    help="game framing: 'matrix' (abstract payoff table) or "
                         "'narrative' (merchant trading story, same payoffs)")
    ap.add_argument("--stream", action="store_true",
                    help="stream model tokens to stderr as they arrive")
    args = ap.parse_args()

    client.BASE_URL = args.base_url
    client.API_KEY = os.environ.get(args.api_key_env)
    client.STREAM = args.stream
    if client.BASE_URL == client.OPENROUTER_URL and not client.API_KEY:
        print(f"ERROR: set {args.api_key_env} first.", file=sys.stderr)
        sys.exit(1)

    model_slug = args.model.replace("/", "__")
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = Path(args.out_dir) / f"{model_slug}_{args.frame}_{timestamp}"
    out_dir.mkdir(parents=True, exist_ok=True)
    setup_logging(out_dir)

    trials_path = out_dir / "trials.jsonl"
    checks_path = out_dir / "persona_checks.jsonl"
    horizon_mode = "fixed" if args.horizon == "fixed" else "probabilistic"

    logger.info("RUN START model=%s opponents=%s personas=%s reps=%d horizon=%s max_rounds=%d frame=%s",
                args.model, args.opponents, args.personas, args.reps,
                horizon_mode, args.max_rounds, args.frame)
    logger.info("output -> %s", out_dir.resolve())

    rng = random.Random(args.seed)
    personas = build_personas()

    persona_check_cache: dict = {}
    n_cells = len(args.opponents) * len(args.personas) * args.reps
    done = 0

    with open(trials_path, "a") as trials_f, open(checks_path, "a") as checks_f:

        def on_check_computed(cache_key: tuple, check) -> None:
            model_slug, persona = cache_key
            checks_f.write(json.dumps({
                "model": model_slug,
                "persona": persona,
                "variant_used": check.variant_used,
                "check_a_mean": check.check_a_mean,
                "identification_hits": check.identification_hits,
                "identification_n": check.identification_n,
                "passed": check.passed,
                "log": check.log,
            }) + "\n")
            checks_f.flush()

        for persona in args.personas:
            for opponent in args.opponents:
                for rep in range(args.reps):
                    done += 1
                    logger.info("[%d/%d] persona=%s opponent=%s rep=%d",
                                done, n_cells, persona, opponent, rep)
                    try:
                        result = run_trial(
                            args.model, opponent, persona, rep, personas,
                            horizon_mode, args.max_rounds, rng,
                            persona_check_cache, on_check_computed,
                            frame=args.frame,
                        )
                        skipped = result.get("stage_b_skipped", False)
                        logger.info("  -> written to trials.jsonl (stage_b_skipped=%s)", skipped)
                    except HarnessError as e:
                        logger.error("API error, skipping cell: %s", e)
                        result = {
                            "model": args.model, "opponent": opponent,
                            "persona": persona, "rep": rep, "trial_error": str(e),
                        }
                    trials_f.write(json.dumps(result) + "\n")
                    trials_f.flush()

    logger.info("RUN DONE. trials=%s checks=%s", trials_path, checks_path)


if __name__ == "__main__":
    main()
