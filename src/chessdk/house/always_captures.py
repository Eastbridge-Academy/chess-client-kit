"""always_captures: prefer any capture; otherwise random."""

from __future__ import annotations

import random

from chessdk.types import Move


_rng = random.Random()


def choose_move(board, time_left_ms: int) -> Move:
    moves = board.legal_moves()
    captures = [m for m in moves if board.piece_at(m.to_sq) is not None]
    if captures:
        return _rng.choice(captures)
    # En-passant captures look like quiet moves to the simple test above
    # (the destination is empty), but the bot we want here is the naive
    # capture-eager one and that subtlety is fine to ignore.
    return _rng.choice(moves)
