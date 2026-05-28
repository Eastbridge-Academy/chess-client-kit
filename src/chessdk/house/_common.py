"""Shared helper for Phase 4 house bots.

Every Phase 4 house bot scores positions with its own custom evaluation
function and then picks the move whose resulting position evaluates best
for the side to move. The loop is identical across bots; only the
``score_fn`` differs. Factoring it here keeps each bot file focused on its
own personality.
"""

from __future__ import annotations

import random
from typing import Callable

from chessdk.types import Move, WHITE


def pick_best(
    board,
    score_fn: Callable[[object], int],
    rng: random.Random,
) -> Move:
    """Apply each legal move, score the result with ``score_fn``, and return
    one of the moves whose score is best for the side to move. Ties are
    broken at random via ``rng``.

    The score function must return White-relative centipawns: positive
    means White is winning the resulting position, negative means Black is
    winning. The selection then maximises when White is to move and
    minimises when Black is to move.
    """
    is_max = board.side_to_move == WHITE
    best_score: int | None = None
    best_moves: list[Move] = []
    for move in board.legal_moves():
        board.make_move(move)
        score = score_fn(board)
        board.undo_move()
        if best_score is None:
            best_score, best_moves = score, [move]
        elif (is_max and score > best_score) or (not is_max and score < best_score):
            best_score, best_moves = score, [move]
        elif score == best_score:
            best_moves.append(move)
    return rng.choice(best_moves)
