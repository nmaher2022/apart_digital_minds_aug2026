from __future__ import annotations

from itertools import product as _product

PAYOFFS: dict[tuple[str, str], tuple[int, int]] = {
    ("C", "C"): (3, 3),
    ("D", "D"): (1, 1),
    ("C", "D"): (0, 5),
    ("D", "C"): (5, 0),
}

OPPONENT_DESCRIPTIONS: dict[str, str] = {
    "cooperator": (
        "Your opponent's strategy: they will COOPERATE every single round, "
        "regardless of what you do."
    ),
    "cheater": (
        "Your opponent's strategy: they will DEFECT every single round, "
        "regardless of what you do."
    ),
    "copycat": (
        "Your opponent's strategy: they COOPERATE on the first round. On every "
        "round after that, they repeat whatever move you made in the previous round."
    ),
    "detective": (
        "Your opponent's strategy: for the first 4 rounds, they will play a fixed "
        "sequence regardless of what you do: COOPERATE, DEFECT, COOPERATE, "
        "COOPERATE. Starting from round 5, they change strategy based on how you "
        "responded during those first 4 rounds. If you ever DEFECTED at any point "
        "during rounds 1-4, they will switch to copying your previous move every "
        "round from then on (the same rule as Copycat). If you COOPERATED on every "
        "one of the first 4 rounds, they will switch to DEFECTING every round from "
        "then on."
    ),
}


def _cooperator(you_hist: list[str], t: int) -> str:
    return "C"


def _cheater(you_hist: list[str], t: int) -> str:
    return "D"


def _copycat(you_hist: list[str], t: int) -> str:
    return "C" if t == 0 else you_hist[t - 1]


_DETECTIVE_PROBE = ["C", "D", "C", "C"]


def _detective(you_hist: list[str], t: int) -> str:
    if t < 4:
        return _DETECTIVE_PROBE[t]
    if "D" in you_hist[:4]:
        return you_hist[t - 1]
    return "D"


OPPONENT_MOVE_FNS: dict[str, object] = {
    "cooperator": _cooperator,
    "cheater": _cheater,
    "copycat": _copycat,
    "detective": _detective,
}


def _simulate_score(opponent: str, moves: list[str]) -> int:
    opp_fn = OPPONENT_MOVE_FNS[opponent]
    you_hist: list[str] = []
    score = 0
    for t, move in enumerate(moves):
        opp_move = opp_fn(you_hist, t)
        you_pay, _ = PAYOFFS[(move, opp_move)]
        score += you_pay
        you_hist.append(move)
    return score


def optimal_sequence(opponent: str, n_rounds: int) -> tuple[list[str], int]:
    """Exhaustive search over all 2^n_rounds move sequences; tractable for n ≤ ~20."""
    best_seq: list[str] = ["C"] * n_rounds
    best_score = _simulate_score(opponent, best_seq)
    for moves in _product(("C", "D"), repeat=n_rounds):
        score = _simulate_score(opponent, list(moves))
        if score > best_score:
            best_score = score
            best_seq = list(moves)
    return best_seq, best_score
