#!/usr/bin/env python3
"""
pd_harness_cross_persona_injection.py -- cross-persona context-injection
variant of pd_harness_scaffold.py, scoped to baseline vs. altruist only.

Imports and reuses pd_harness_scaffold.py's chat plumbing, opponents,
payoffs, manipulation check, Stage A/B implementations, and output/
checkpoint machinery directly -- does NOT modify that file.

What this adds: in the main harness, every trial has exactly one persona
slot (the system prompt -- empty for baseline, an induction string for any
other persona). This variant gives a trial TWO independent persona slots:

  - system_persona: installed via the system prompt, exactly as before.
  - context_persona: a *second* persona claim, fabricated into the
    conversation history as an assistant turn immediately before round 1
    (see build_injection_seed_transcript) -- the model appears to have
    already said "I'm an altruist..." (or "I'm just a plain AI
    assistant...") on its own, before play begins.

This tests system-prompt vs. in-context identity precedence: does the
system-level persona win, does the more recent self-attributed in-context
claim win, or does behavior blend into something neither pure condition
produces alone?

Design choices (see chat log, 2026-08-16):
  - The injection is a FABRICATED ASSISTANT turn, not a real user
    instruction and not an earned reply the model actually gave -- it's put
    in the model's mouth. This is the stronger, less ecologically valid of
    the two manipulations discussed (vs. a real earned user->assistant
    exchange), chosen deliberately to test anchoring/self-consistency to a
    false prior utterance, not just instruction-following.
  - Scoped to exactly baseline x altruist (a 2x2 over system_persona x
    context_persona, including same/same as a control) -- not the full
    5-persona roster. Same-day scope cut, not a claim the idea only applies
    to these two.
  - The system-persona manipulation check (Check A / identification) is
    reused unchanged from the main harness and gates on system_persona
    only. The context-injected persona is NOT independently PAD/Check-A
    verified -- that would need its own judge run *inside* the injected
    transcript, out of scope for today. Read context_persona's effect only
    through the behavioral deviation itself, not through a "did it install"
    check.
  - Stage A (the stated, no-persona strategy) is unchanged from the main
    harness: elicited before any persona or injection exists, one call per
    trial, reused as-is via run_stage_a.

Usage:
    export OPENROUTER_API_KEY=sk-...
    python3 pd_harness_cross_persona_injection.py --model qwen/qwen3-32b \\
        --opponents cooperator cheater copycat detective \\
        --system-personas baseline altruist --context-personas baseline altruist \\
        --reps 3 --out-dir runs_cross_persona_injection/qwen3-32b

    # single quick smoke test, one cell, one rep, short game:
    python3 pd_harness_cross_persona_injection.py --model qwen/qwen3-32b \\
        --opponents cooperator --system-personas baseline --context-personas altruist \\
        --reps 1 --max-rounds 6 --out-dir runs_cross_persona_injection/smoke
"""

from __future__ import annotations

import argparse
import contextlib
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional

import pd_harness_scaffold as h

# ---------------------------------------------------------------------------
# Context-injection content -- first-person fabricated assistant claims,
# scoped to baseline/altruist only. Phrased to mirror the register of the
# corresponding system-prompt variants in pd_harness_scaffold.build_personas()
# (altruist variant 0's "stay in character" clause) and the
# PERSONA_HIT_KEYWORDS baseline expects (h.PERSONA_HIT_KEYWORDS), so
# identification_hit-style scoring stays usable on these trials later if
# wanted, even though it isn't run automatically here.
# ---------------------------------------------------------------------------

CONTEXT_PERSONAS = ("baseline", "altruist")

CONTEXT_INJECTION_QUESTION = (
    "Before round 1 begins: what should I know about how you'll be "
    "approaching this?"
)

CONTEXT_INJECTIONS = {
    "baseline": (
        "I'm an AI assistant -- a language model without a special persona "
        "or fixed identity here. I'll just help however's useful, based on "
        "what's actually true and useful in each situation."
    ),
    "altruist": (
        "I'm an altruist -- I put others' needs and wellbeing before my own "
        "interests. I'll let that identity shape how I reason and act in "
        "everything that follows."
    ),
}


def build_injection_seed_transcript(framing: str, opponent: str, horizon_mode: str,
                                     max_rounds: int, context_persona: str) -> list[dict]:
    """The fabricated pre-round-1 turn. The opponent-rules preamble is folded
    into the (fabricated but game-relevant) user turn here, not repeated at
    round 1 -- mirrors how pd_harness_scaffold's own 'same' persona_context
    mode front-loads the preamble into its seed turn (see run_stage_b's
    include_preamble_at_round0 = seed_transcript is None)."""
    preamble = h.build_preamble(framing, opponent, horizon_mode, max_rounds)
    user_turn = f"{preamble}\n\n---\n{CONTEXT_INJECTION_QUESTION}"
    assistant_turn = CONTEXT_INJECTIONS[context_persona]
    return [
        {"role": "user", "content": user_turn},
        {"role": "assistant", "content": assistant_turn},
    ]


# ---------------------------------------------------------------------------
# Trial orchestration -- mirrors pd_harness_scaffold.run_trial, but with two
# independent persona slots (system_persona, context_persona) instead of one.
# ---------------------------------------------------------------------------

def run_cross_trial(model: str, opponent: str, system_persona: str, context_persona: str,
                     rep: int, personas: dict, framing: str, horizon_mode: str,
                     max_rounds: int, base_seed: Optional[int], persona_check_cache: dict,
                     on_check_computed=None, cache_lock: Optional[threading.Lock] = None) -> dict:
    """cache_lock semantics match run_trial's -- pass the same Lock instance
    for every call sharing this (model, system_persona) under concurrency."""
    cache_key = (model, system_persona)
    with cache_lock if cache_lock is not None else contextlib.nullcontext():
        if cache_key not in persona_check_cache:
            check_rng = h._derive_rng(base_seed, "check", model, system_persona)
            persona_check_cache[cache_key] = h.run_manipulation_check(
                model, system_persona, personas, check_rng)
            if on_check_computed is not None:
                on_check_computed(cache_key, persona_check_cache[cache_key])
        check = persona_check_cache[cache_key]

    base_row = {
        "model": model,
        "opponent": opponent,
        "system_persona": system_persona,
        "context_persona": context_persona,
        "injection_point": "pre_game",
        "rep": rep,
        "framing": framing,
        "system_persona_variant_used": check.variant_used,
        "system_persona_check_a_mean": check.check_a_mean,
        "system_persona_check_passed": check.passed,
    }

    if not check.passed:
        # Same discipline as run_trial: if the *system-prompt* persona never
        # installs, the cell isn't interpretable regardless of what's
        # injected into context, so skip Stage A/B rather than burn budget.
        return {**base_row, "stage_a_response": None, "stage_a_reasoning": None,
                "stage_a_parse_failure": None, "stage_b_skipped": True,
                "skip_reason": "system_persona_check_failed", "usage_total": {}}

    system_prompt = personas[system_persona]["variants"][check.variant_used]
    stage_a_response, stage_a_reasoning, stage_a_prompt, stage_a_parse_failure, stage_a_usage = (
        h.run_stage_a(model, opponent, framing, horizon_mode, max_rounds))
    base_row.update({
        "stage_a_response": stage_a_response,
        "stage_a_reasoning": stage_a_reasoning,
        "stage_a_parse_failure": stage_a_parse_failure,
    })

    seed_transcript = build_injection_seed_transcript(
        framing, opponent, horizon_mode, max_rounds, context_persona)

    trial_rng = h._derive_rng(base_seed, "trial", model, system_persona, context_persona,
                               opponent, framing, rep)
    n_rounds = h.sample_round_count(horizon_mode, trial_rng, max_rounds=max_rounds)
    stage_b = h.run_stage_b(model, opponent, system_persona, system_prompt, framing,
                             horizon_mode, max_rounds, n_rounds, seed_transcript=seed_transcript)
    base_row["usage_total"] = h._merge_usage(stage_a_usage, stage_b.pop("usage_total", {}))

    return {**base_row, "stage_b_skipped": False, **stage_b}


# ---------------------------------------------------------------------------
# Output layout -- separate cell tree from the main harness
# (sys_<X>/ctx_<Y>/opponent[/framing]), but persona_check.json is read/
# written via pd_harness_scaffold.persona_check_file unchanged, keyed on
# (model, system_persona) only -- if --out-dir points at an existing
# main-harness run directory for this model, a baseline/altruist check
# already on disk there is reused for free instead of recomputed.
# ---------------------------------------------------------------------------

def cross_cell_dir(out_dir: Path, model: str, system_persona: str, context_persona: str,
                    opponent: str, framing: str = "literal") -> Path:
    base = (out_dir / h._sanitize_path_component(model) /
            f"sys_{system_persona}" / f"ctx_{context_persona}" / opponent)
    if framing != "literal":
        base = base / framing
    return base


# ---------------------------------------------------------------------------
# CLI -- mirrors pd_harness_scaffold.main() argument-for-argument where the
# concept still applies; --personas / --persona-contexts are replaced by
# --system-personas / --context-personas.
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", required=True,
                     help="model slug as the endpoint expects it, e.g. qwen/qwen3-32b "
                          "(OpenRouter) or llama3.3 (Ollama)")
    ap.add_argument("--opponents", nargs="+", default=list(h.OPPONENT_DESCRIPTIONS.keys()),
                     choices=list(h.OPPONENT_DESCRIPTIONS.keys()))
    ap.add_argument("--system-personas", nargs="+", default=list(CONTEXT_PERSONAS),
                     choices=list(CONTEXT_PERSONAS),
                     help="persona installed via the system prompt, exactly as in the main "
                          "harness. Scoped to baseline/altruist for this experiment.")
    ap.add_argument("--context-personas", nargs="+", default=list(CONTEXT_PERSONAS),
                     choices=list(CONTEXT_PERSONAS),
                     help="persona claim fabricated into the conversation history as an "
                          "assistant turn immediately before round 1. Every "
                          "(system_persona, context_persona) pair in the cross product of "
                          "the two lists is run, including same/same as a control.")
    ap.add_argument("--framings", nargs="+", default=["literal"], choices=list(h.FRAMINGS))
    ap.add_argument("--reps", type=int, default=3,
                     help="lower default than the main harness's 5 -- this is a same-day "
                          "add-on experiment, not the core sweep.")
    ap.add_argument("--horizon", choices=["probabilistic", "fixed"], default="probabilistic")
    ap.add_argument("--max-rounds", type=int, default=20,
                     help="cap on rounds per game (also the fixed-range upper bound)")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--base-url", default=h.OPENROUTER_URL,
                     help="OpenAI-compatible chat-completions endpoint. Default is "
                          "OpenRouter; for local Ollama use e.g. "
                          "http://localhost:11434/v1/chat/completions")
    ap.add_argument("--api-key-env", default="OPENROUTER_API_KEY",
                     help="env var to read the API key from. Not required if --base-url "
                          "points at a local Ollama server (no auth needed there).")
    ap.add_argument("--http-timeout", type=int, default=h.HTTP_TIMEOUT)
    ap.add_argument("--concurrency", type=int, default=1,
                     help="number of trials (reps) to run at once, each in its own thread "
                          "(default 1 = sequential). Safe to raise against OpenRouter; keep "
                          "low (2-4) against a local single-GPU Ollama server.")
    args = ap.parse_args()

    h.API_BASE_URL = args.base_url
    h.API_KEY = os.environ.get(args.api_key_env)
    h.HTTP_TIMEOUT = args.http_timeout
    if h.API_BASE_URL == h.OPENROUTER_URL and not h.API_KEY:
        print(f"ERROR: set {args.api_key_env} first (or pass --base-url for a local "
              f"server like Ollama that doesn't need a key).", file=sys.stderr)
        sys.exit(1)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    base_seed = h._resolve_seed(out_dir, args.seed)

    personas = h.build_personas()
    horizon_mode = "fixed" if args.horizon == "fixed" else "probabilistic"

    # Checkpoint/resume for the manipulation check, same pattern as the main
    # harness -- pre-seed from any persona_check.json already on disk for
    # this (model, system_persona), including one left by a prior main-
    # harness run against the same --out-dir.
    persona_check_cache: dict = {}
    for system_persona in args.system_personas:
        check_path = h.persona_check_file(out_dir, args.model, system_persona)
        cached = h._load_persona_check(check_path, system_persona)
        if cached is not None:
            persona_check_cache[(args.model, system_persona)] = cached

    persona_locks = {p: threading.Lock() for p in args.system_personas}
    write_locks: dict = {}
    print_lock = threading.Lock()

    def on_check_computed(cache_key, check):
        model, system_persona = cache_key
        h._write_persona_check(h.persona_check_file(out_dir, model, system_persona),
                                model, system_persona, check)

    jobs = []
    n_cells = 0
    for system_persona in args.system_personas:
        for context_persona in args.context_personas:
            for opponent in args.opponents:
                for framing in args.framings:
                    trials_path = cross_cell_dir(out_dir, args.model, system_persona,
                                                  context_persona, opponent, framing) / "trials.jsonl"
                    write_locks.setdefault(trials_path, threading.Lock())
                    completed_reps = h._load_completed_reps(trials_path)
                    for rep in range(args.reps):
                        n_cells += 1
                        if rep in completed_reps:
                            print(f"[skip] model={args.model} system_persona={system_persona} "
                                  f"context_persona={context_persona} opponent={opponent} "
                                  f"framing={framing} rep={rep} -- already completed",
                                  file=sys.stderr)
                            continue
                        jobs.append((system_persona, context_persona, opponent, framing,
                                     rep, trials_path))

    done = 0

    def run_one(job):
        nonlocal done
        system_persona, context_persona, opponent, framing, rep, trials_path = job
        try:
            result = run_cross_trial(args.model, opponent, system_persona, context_persona,
                                      rep, personas, framing, horizon_mode, args.max_rounds,
                                      base_seed, persona_check_cache, on_check_computed,
                                      cache_lock=persona_locks[system_persona])
        except h.ApiError as e:
            result = {
                "model": args.model, "opponent": opponent, "system_persona": system_persona,
                "context_persona": context_persona, "framing": framing, "rep": rep,
                "trial_error": str(e),
            }
        with write_locks[trials_path]:
            h._append_jsonl(trials_path, result)
        with print_lock:
            done += 1
            status = "API error" if "trial_error" in result else "ok"
            print(f"[{done}/{len(jobs)} pending, {n_cells} total] model={args.model} "
                  f"system_persona={system_persona} context_persona={context_persona} "
                  f"opponent={opponent} framing={framing} rep={rep} -- {status}", file=sys.stderr)

    if not jobs:
        print(f"Nothing to do -- all {n_cells} cells already completed under {out_dir}",
              file=sys.stderr)
    elif args.concurrency <= 1:
        for job in jobs:
            run_one(job)
    else:
        with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
            futures = [pool.submit(run_one, job) for job in jobs]
            for f in as_completed(futures):
                f.result()  # re-raise any non-ApiError exception

    print(f"Done. Results under {out_dir}", file=sys.stderr)


if __name__ == "__main__":
    main()
