"""tunnel_vision: deep search, but only on captures.

Tunnel Vision runs alpha-beta to depth five, but at every level it
considers only capture moves; quiet moves are never explored. The result
is a bot that is spectacular in tactical positions where forcing lines
decide the game, and helpless in positions where the right move is a
calm developing maneuver. Most of the time it falls back to whatever
capture happens to be available; in tactical positions it sees deep
combinations a depth-3 full searcher would miss.

This is the bot whose failure mode motivates Phase 6's quiescence
search: a quiescence search looks like Tunnel Vision but is invoked
only at the leaves of the main search to resolve hanging captures,
rather than replacing the main search entirely.
"""

from __future__ import annotations

import random

from chessdk.evaluation import PIECE_VALUE_CLASSIC, pst_square
from chessdk.house._common import minimax_pick
from chessdk.types import Move, WHITE


_rng = random.Random()
_DEPTH = 5


def _score(board) -> int:
    total = 0
    for s, piece in enumerate(board.pieces):
        if piece is None:
            continue
        sign = 1 if piece.color == WHITE else -1
        total += sign * PIECE_VALUE_CLASSIC[piece.kind]
        total += sign * pst_square(piece.kind, piece.color, s)
    return total


def choose_move(board, time_left_ms: int) -> Move:
    return minimax_pick(board, _score, _DEPTH, _rng, capture_only=True)
