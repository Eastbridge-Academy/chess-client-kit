"""crusader: throws material at the enemy king.

Standard material and PSTs from the canonical Simplified Evaluation, plus
a large bonus for every one of its own pieces that attacks a square in
the 3x3 zone around the enemy king. The bonus is unilateral: Crusader
gets nothing for being safe itself, only for menacing the opponent.

Personality: aggressive, attacking, often unsound. Picks up the rook on
the rim of the board if it means it can launch a kingside attack two
moves later, abandons its own king's pawn shield without a second thought.
Beats passive bots; loses to anyone with a reasonable defensive eval term
or just careful play.
"""

from __future__ import annotations

import random

from chessdk.evaluation import PIECE_VALUE_CLASSIC, pst_square
from chessdk.house._common import minimax_pick
from chessdk.squares import file_of, rank_of, sq
from chessdk.types import BLACK, KING, Move, WHITE


_rng = random.Random()
_DEPTH = 3


_KING_ATTACK_BONUS = 35  # centipawns per attacker in the enemy king's 3x3 zone


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


def _count_attackers(board, zone: list[int], by_color) -> int:
    return sum(1 for s in zone if board.is_attacked(s, by_color))


def _score(board) -> int:
    total = 0
    for s, piece in enumerate(board.pieces):
        if piece is None:
            continue
        sign = 1 if piece.color == WHITE else -1
        total += sign * PIECE_VALUE_CLASSIC[piece.kind]
        total += sign * pst_square(piece.kind, piece.color, s)

    # White scores a bonus for every white piece that attacks the 3x3 zone
    # around the black king; Black scores symmetrically against the white
    # king. We do not subtract for being attacked ourselves: Crusader does
    # not defend, only attacks.
    black_king = _find_king(board, BLACK)
    white_king = _find_king(board, WHITE)
    if black_king is not None:
        total += _KING_ATTACK_BONUS * _count_attackers(
            board, _king_zone(black_king), WHITE
        )
    if white_king is not None:
        total -= _KING_ATTACK_BONUS * _count_attackers(
            board, _king_zone(white_king), BLACK
        )
    return total


def choose_move(board, time_left_ms: int) -> Move:
    return minimax_pick(board, _score, _DEPTH, _rng)
