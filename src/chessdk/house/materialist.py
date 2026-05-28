"""materialist: pure material counting at depth 1.

The simplest "real" Phase 4 bot. Scores every legal move by the raw
material balance of the resulting position, with no piece-square tables,
no mobility, no king safety. Treats a knight on a8 the same as a knight
on e4 — happily develops to terrible squares as long as material is even.

Any student bot with even a rudimentary piece-square table will beat
Materialist consistently, because that is exactly the gap Materialist
ignores.
"""

from __future__ import annotations

import random

from chessdk.evaluation import MATE_SCORE, PIECE_VALUE_CLASSIC
from chessdk.house._common import pick_best
from chessdk.types import Move, WHITE


_rng = random.Random()


def _score(board) -> int:
    legal = board.legal_moves()
    if not legal:
        if board.is_in_check():
            return -MATE_SCORE if board.side_to_move == WHITE else MATE_SCORE
        return 0
    total = 0
    for piece in board.pieces:
        if piece is None:
            continue
        sign = 1 if piece.color == WHITE else -1
        total += sign * PIECE_VALUE_CLASSIC[piece.kind]
    return total


def choose_move(board, time_left_ms: int) -> Move:
    return pick_best(board, _score, _rng)
