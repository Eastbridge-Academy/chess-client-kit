"""materialist: pure material counting wrapped in alpha-beta search.

Scores every legal move by the raw material balance of the position the
search lands on, with no piece-square tables, no mobility, no king
safety. Treats a knight on a8 the same as a knight on e4; on positional
positions it drifts, on tactical positions it calculates.

The personality has not changed since Phase 4 — only the search wrapping
the eval has. In v0.4.0 Materialist ran at depth 1 (eval-and-pick) and
hung pieces frequently. In v0.5.0 it runs alpha-beta at depth 3, sees
captures and recaptures coming, and is a noticeably tougher opponent
even though every centipawn it counts is the same centipawn it counted
in v0.4.0.
"""

from __future__ import annotations

import random

from chessdk.evaluation import PIECE_VALUE_CLASSIC
from chessdk.house._common import minimax_pick
from chessdk.types import Move, WHITE


_rng = random.Random()
_DEPTH = 3


def _score(board) -> int:
    total = 0
    for piece in board.pieces:
        if piece is None:
            continue
        sign = 1 if piece.color == WHITE else -1
        total += sign * PIECE_VALUE_CLASSIC[piece.kind]
    return total


def choose_move(board, time_left_ms: int) -> Move:
    return minimax_pick(board, _score, _DEPTH, _rng)
