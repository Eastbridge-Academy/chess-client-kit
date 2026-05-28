"""Stage 16: ``evaluate(board)`` reflects mobility.

A position where one side has many more legal moves than the other should
evaluate in that side's favor, all else being equal. The pairs below are
constructed so that material is identical and the piece-square-table
contributions are either equal or also point the same way, isolating
mobility as the variable that decides the eval direction.

Assertions check direction only, never magnitude.
"""

from __future__ import annotations

import pytest

from board import Board
from evaluation import evaluate


@pytest.mark.parametrize(
    "fen_mobile,fen_cramped,description",
    [
        # White rook on a central square (~14 rook moves) vs. white rook on
        # h1 (~10 rook moves), with the kings placed identically in both
        # positions. Same material, same king PST, same rook PST (both
        # squares score 0 in the canonical table); only mobility differs.
        (
            "6k1/8/8/8/4R3/8/8/4K3 w - - 0 1",
            "6k1/8/8/8/8/8/8/4K2R w - - 0 1",
            "white rook: central (e4) vs. corner (h1)",
        ),
        # White's bishop and knight are developed; Black's are not. Same
        # material on both sides, but the active side has substantially more
        # legal moves available.
        (
            "rnbqkb1r/pppppppp/5n2/8/3P4/2N1PN2/PPP2PPP/R1BQKB1R b KQkq - 0 1",
            "rnbqkb1r/pppppppp/5n2/8/3P4/4P3/PPPN1PPP/R1BQKBNR b KQkq - 0 1",
            "white knights developed (c3+f3) vs. semi-developed (d2+g1)",
        ),
    ],
)
def test_more_mobile_side_evaluates_higher(
    fen_mobile: str, fen_cramped: str, description: str
):
    eval_mobile = evaluate(Board.from_fen(fen_mobile))
    eval_cramped = evaluate(Board.from_fen(fen_cramped))
    assert eval_mobile > eval_cramped, (
        f"{description}: mobile={eval_mobile}, cramped={eval_cramped} "
        f"(expected mobile > cramped)"
    )
