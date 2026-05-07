"""hangs_pieces: an anti-goal bot that prefers to walk pieces into danger.

If any legal move places the moving piece on a square attacked by the enemy,
play it. Otherwise fall back to a random legal move. Useful as an obvious
target — if a student bot can't beat this, something is wrong.
"""

from __future__ import annotations

import random

from chessdk.types import Move, opposite


_rng = random.Random()


def choose_move(board, time_left_ms: int) -> Move:
    moves = board.legal_moves()
    enemy = opposite(board.side_to_move)
    hanging = [m for m in moves if board.is_attacked(m.to_sq, enemy)]
    if hanging:
        return _rng.choice(hanging)
    return _rng.choice(moves)
