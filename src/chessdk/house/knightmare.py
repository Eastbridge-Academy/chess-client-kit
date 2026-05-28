"""knightmare: material counting with badly miscalibrated piece values.

Plays the same eval-and-pick structure as Materialist, but believes a
knight is worth 500 centipawns (more than a rook) and a bishop only 200.
The result is a bot that will eagerly give up a bishop for a knight at
every opportunity, sometimes for no benefit, and refuse trades that look
losing on its own scale even when they are sound on any normal scale.

A vivid demonstration that piece values are a real parameter and a real
choice — students with sensible values, even hand-picked ones, will
diagnose Knightmare's personality within a few moves.
"""

from __future__ import annotations

import random

from chessdk.house._common import minimax_pick
from chessdk.types import (
    BISHOP,
    KING,
    KNIGHT,
    Kind,
    Move,
    PAWN,
    QUEEN,
    ROOK,
    WHITE,
)


_rng = random.Random()
_DEPTH = 3


_KNIGHTMARE_VALUES: dict[Kind, int] = {
    PAWN: 100,
    KNIGHT: 500,
    BISHOP: 200,
    ROOK: 500,
    QUEEN: 900,
    KING: 20000,
}


def _score(board) -> int:
    total = 0
    for piece in board.pieces:
        if piece is None:
            continue
        sign = 1 if piece.color == WHITE else -1
        total += sign * _KNIGHTMARE_VALUES[piece.kind]
    return total


def choose_move(board, time_left_ms: int) -> Move:
    return minimax_pick(board, _score, _DEPTH, _rng)
