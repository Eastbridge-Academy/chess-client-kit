"""edge_lord: material plus an inverted piece-square table.

Uses standard piece values, but its PST is the negation of a canonical
one — pieces are rewarded for sitting on the edge of the board and
penalized for the center. Knights on the rim, bishops in the corner,
king out for a stroll in the middlegame: every positional lesson, in
reverse.

A useful target for the first half of Phase 4: a bot that "knows" about
piece placement but has it exactly wrong should be beaten badly by any
student whose PST is even directionally correct.
"""

from __future__ import annotations

import random

from chessdk.evaluation import (
    DEFAULT_PSTS,
    MATE_SCORE,
    PIECE_VALUE_CLASSIC,
)
from chessdk.house._common import pick_best
from chessdk.squares import file_of, rank_of, sq
from chessdk.types import Move, WHITE


_rng = random.Random()


def _score(board) -> int:
    legal = board.legal_moves()
    if not legal:
        if board.is_in_check():
            return -MATE_SCORE if board.side_to_move == WHITE else MATE_SCORE
        return 0
    total = 0
    for s, piece in enumerate(board.pieces):
        if piece is None:
            continue
        sign = 1 if piece.color == WHITE else -1
        total += sign * PIECE_VALUE_CLASSIC[piece.kind]
        # Invert the PST: lookup square is the same as for a regular
        # evaluator, but the contribution's sign is flipped.
        table = DEFAULT_PSTS[piece.kind]
        if piece.color == WHITE:
            pst_value = table[s]
        else:
            pst_value = table[sq(file_of(s), 7 - rank_of(s))]
        total += sign * (-pst_value)
    return total


def choose_move(board, time_left_ms: int) -> Move:
    return pick_best(board, _score, _rng)
