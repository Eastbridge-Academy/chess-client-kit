"""magnus_mini: the well-engineered Phase 5 baseline.

Depth-3 alpha-beta search around a balanced evaluation: classic material
values, the canonical Simplified Evaluation piece-square tables, a small
mobility term, and a defensive king-safety term that penalizes being
attacked near your own king. None of the components are exotic, and the
weights are sensible without being heroic; the strength comes from
combining them at a real search depth.

This is the milestone opponent of Phase 5. Most students should beat it
by Stage 19 once they have alpha-beta with captures-first ordering, but
not trivially. If your bot loses to Magnus Mini consistently, the eval
or the search has slack to take up.
"""

from __future__ import annotations

import random

from chessdk.evaluation import (
    DEFAULT_MOBILITY_WEIGHT,
    PIECE_VALUE_CLASSIC,
    pst_square,
)
from chessdk.house._common import iterative_pick
from chessdk.squares import file_of, rank_of, sq
from chessdk.types import BLACK, KING, Move, WHITE


_rng = random.Random()
_DEPTH = 3


_KING_SAFETY_PENALTY = 20  # centipawns per enemy attacker near your king


def _find_king(board, color) -> int | None:
    for s, piece in enumerate(board.pieces):
        if piece is not None and piece.kind == KING and piece.color == color:
            return s
    return None


def _king_zone(king_sq: int) -> list[int]:
    kf, kr = file_of(king_sq), rank_of(king_sq)
    zone: list[int] = []
    for df in (-1, 0, 1):
        for dr in (-1, 0, 1):
            nf, nr = kf + df, kr + dr
            if 0 <= nf < 8 and 0 <= nr < 8:
                zone.append(sq(nf, nr))
    return zone


def _count_legal_for(board, color) -> int:
    original = board.state.side_to_move
    board.state.side_to_move = color
    try:
        return len(board.legal_moves())
    finally:
        board.state.side_to_move = original


def _score(board) -> int:
    total = 0
    for s, piece in enumerate(board.pieces):
        if piece is None:
            continue
        sign = 1 if piece.color == WHITE else -1
        total += sign * PIECE_VALUE_CLASSIC[piece.kind]
        total += sign * pst_square(piece.kind, piece.color, s)

    # Both sides' mobility, scored from White's POV.
    other = BLACK if board.side_to_move == WHITE else WHITE
    side_count = len(board.legal_moves())
    other_count = _count_legal_for(board, other)
    if board.side_to_move == WHITE:
        white_count, black_count = side_count, other_count
    else:
        white_count, black_count = other_count, side_count
    total += DEFAULT_MOBILITY_WEIGHT * (white_count - black_count)

    # King safety: penalize each enemy attacker in your king's 3x3 zone.
    white_king = _find_king(board, WHITE)
    black_king = _find_king(board, BLACK)
    if white_king is not None:
        attackers = sum(
            1 for s in _king_zone(white_king) if board.is_attacked(s, BLACK)
        )
        total -= _KING_SAFETY_PENALTY * attackers
    if black_king is not None:
        attackers = sum(
            1 for s in _king_zone(black_king) if board.is_attacked(s, WHITE)
        )
        total += _KING_SAFETY_PENALTY * attackers

    return total


def choose_move(board, time_left_ms: int) -> Move:
    return iterative_pick(board, _score, _DEPTH, _rng, time_left_ms)
