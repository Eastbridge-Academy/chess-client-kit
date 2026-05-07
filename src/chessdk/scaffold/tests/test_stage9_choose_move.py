"""Stage 9: choose_move returns a legal move.

Sanity check for `bot.choose_move`: across a handful of positions, whatever
the bot returns must be one of the current `legal_moves()`. This is the
single hard requirement the tournament server enforces — illegal moves
forfeit the game.
"""

from __future__ import annotations

import pytest

from board import Board
from bot import choose_move


POSITIONS = [
    # Starting position
    "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
    # An open middlegame
    "r1bqkb1r/pppp1ppp/2n2n2/4p3/4P3/2N2N2/PPPP1PPP/R1BQKB1R w KQkq - 4 4",
    # In check (black to move)
    "rnbqkb1r/pppp1Bpp/5n2/4p3/4P3/8/PPPP1PPP/RNBQK1NR b KQkq - 0 3",
    # Endgame: white to move, only one legal move
    "8/8/8/8/8/4k3/8/4K2R w K - 0 1",
]


@pytest.mark.parametrize("fen", POSITIONS)
def test_choose_move_returns_legal_move(fen):
    board = Board.from_fen(fen)
    move = choose_move(board, time_left_ms=1000)
    assert move in board.legal_moves(), (
        f"choose_move returned {move.uci()!r} which is not legal in this position"
    )
