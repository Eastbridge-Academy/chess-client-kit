"""random_legal: pick a uniformly random legal move."""

from __future__ import annotations

import random

from chessdk.types import Move


_rng = random.Random()


def choose_move(board, time_left_ms: int) -> Move:
    return _rng.choice(board.legal_moves())
