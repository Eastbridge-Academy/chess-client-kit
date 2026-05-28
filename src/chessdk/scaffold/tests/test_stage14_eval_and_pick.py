"""Stage 14: ``choose_move`` selects the move whose resulting position
evaluates best for the side to move.

This is a structural check rather than an evaluation-specific one. We give
the bot positions where one move leads to immediate checkmate and verify
that the bot finds it: the eval after a mating move is huge in the right
direction, and the eval-and-pick loop should prefer it over any other
candidate, regardless of how the rest of your evaluation is tuned.
"""

from __future__ import annotations

import pytest

from board import Board
from bot import choose_move


@pytest.mark.parametrize(
    "fen,mating_move,description",
    [
        # White to move; Rd8# is back-rank mate. Black king on g8 cannot escape.
        (
            "6k1/5ppp/8/8/8/8/5PPP/3R2K1 w - - 0 1",
            "d1d8",
            "back-rank mate-in-1 (Rd1-d8#)",
        ),
        # White to move; Nf7# is the smothered-mate finish.
        (
            "6rk/6pp/8/6N1/8/8/8/6K1 w - - 0 1",
            "g5f7",
            "smothered mate-in-1 (Ng5-f7#)",
        ),
        # Black to move; Qe1# along the e-file, with the white king's escape
        # squares (f1, h1) attacked along the back rank and the f2/g2/h2
        # pawns blocking any retreat to rank 2.
        (
            "k3q3/8/8/8/8/8/5PPP/6K1 b - - 0 1",
            "e8e1",
            "back-rank mate-in-1 by Black (Qe8-e1#)",
        ),
    ],
)
def test_bot_finds_mate_in_one(fen: str, mating_move: str, description: str):
    board = Board.from_fen(fen)
    move = choose_move(board, time_left_ms=1000)
    assert move in board.legal_moves(), (
        f"{description}: returned illegal move {move.uci()!r}"
    )
    # Confirm the picked move actually mates by checking that the resulting
    # position has no legal replies and the side to move is in check.
    board.make_move(move)
    assert board.is_in_check() and not board.legal_moves(), (
        f"{description}: expected mate after {move.uci()}, but the position is not mate"
    )
