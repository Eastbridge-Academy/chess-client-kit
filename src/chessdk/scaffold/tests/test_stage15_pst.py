"""Stage 15: ``evaluate(board)`` rewards good piece placement.

Pairs of positions with identical material but very different piece
placement should evaluate in the expected direction. A knight in the
center is worth more than a knight in the corner; an advanced pawn is
worth more than one still on its starting rank; a bishop on a long
diagonal is worth more than a bishop boxed into a corner.

The assertions only check direction (strong > weak), never magnitude.
"""

from __future__ import annotations

import pytest

from board import Board
from evaluation import evaluate


@pytest.mark.parametrize(
    "fen_strong,fen_weak,description",
    [
        # White knight on e4 (center) vs a1 (corner). Kings are placed far apart.
        (
            "k7/8/8/8/4N3/8/4K3/8 w - - 0 1",
            "k7/8/8/8/8/8/4K3/N7 w - - 0 1",
            "white knight: center (e4) vs corner (a1)",
        ),
        # White pawn one step from promoting vs. still on its starting rank.
        (
            "4k3/4P3/8/8/8/8/8/4K3 w - - 0 1",
            "4k3/8/8/8/8/8/4P3/4K3 w - - 0 1",
            "white pawn: rank 7 vs. rank 2",
        ),
        # White bishop on a central square (long diagonals available) vs. corner.
        # We use h1 rather than a1 for the corner case so that the bishop's
        # diagonal doesn't run through the black king on h8 (which would put
        # Black in check on White's turn — an unreachable position).
        (
            "7k/8/8/8/4B3/8/4K3/8 w - - 0 1",
            "7k/8/8/8/8/8/4K3/7B w - - 0 1",
            "white bishop: center (e4) vs. corner (h1)",
        ),
    ],
)
def test_better_placement_evaluates_higher(
    fen_strong: str, fen_weak: str, description: str
):
    eval_strong = evaluate(Board.from_fen(fen_strong))
    eval_weak = evaluate(Board.from_fen(fen_weak))
    assert eval_strong > eval_weak, (
        f"{description}: strong={eval_strong}, weak={eval_weak} "
        f"(expected strong > weak)"
    )
