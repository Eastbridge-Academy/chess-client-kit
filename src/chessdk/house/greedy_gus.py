"""greedy_gus: depth-four alpha-beta with material-only evaluation.

Pure tactical calculator. Looks four plies ahead with proper alpha-beta
pruning, but the only thing it scores is the material balance of the
resulting position. No PSTs, no mobility, no king safety, no notion of
piece activity at all. A queen on a8 is the same as a queen on the
strongest central square; a pawn on the seventh rank is the same as a
pawn on its starting square.

In tactical positions Greedy Gus is dangerous: it sees combinations a
shallower opponent will miss and converts them into material. In quiet
positional games it drifts, develops pieces to bad squares, and loses
to anyone who can leverage positional understanding into tactical
opportunities. The matchup against Greedy Gus rewards balanced
evaluation more than raw depth.
"""

from __future__ import annotations

import random

from chessdk.evaluation import PIECE_VALUE_CLASSIC
from chessdk.house._common import iterative_pick
from chessdk.types import Move, WHITE


_rng = random.Random()
_DEPTH = 4


def _score(board) -> int:
    total = 0
    for piece in board.pieces:
        if piece is None:
            continue
        sign = 1 if piece.color == WHITE else -1
        total += sign * PIECE_VALUE_CLASSIC[piece.kind]
    return total


def choose_move(board, time_left_ms: int) -> Move:
    return iterative_pick(board, _score, _DEPTH, _rng, time_left_ms)
