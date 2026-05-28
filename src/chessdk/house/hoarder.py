"""hoarder: values material at 1.5x and penalizes mobility.

Material is worth 50% more than the textbook says, and a small penalty is
deducted for every legal move available to either side, so Hoarder
prefers positions with material on the board and few choices to make.
The two terms combine into a personality that refuses to trade, hates
open lines, and clutters its own back rank with pieces.

Loses to active play. A student bot that values mobility, opens the
position, and pries trades open will roll over Hoarder; a student bot
without mobility may struggle if it cannot generate threats by
maneuvering.
"""

from __future__ import annotations

import random

from chessdk.evaluation import MATE_SCORE, PIECE_VALUE_CLASSIC
from chessdk.house._common import pick_best
from chessdk.types import BLACK, Move, WHITE


_rng = random.Random()


_MATERIAL_MULTIPLIER = 1.5
_MOBILITY_PENALTY = 3  # centipawns subtracted per legal move per side


def _count_legal_for(board, color) -> int:
    original = board.state.side_to_move
    board.state.side_to_move = color
    try:
        return len(board.legal_moves())
    finally:
        board.state.side_to_move = original


def _score(board) -> int:
    legal = board.legal_moves()
    if not legal:
        if board.is_in_check():
            return -MATE_SCORE if board.side_to_move == WHITE else MATE_SCORE
        return 0

    total = 0
    for piece in board.pieces:
        if piece is None:
            continue
        sign = 1 if piece.color == WHITE else -1
        total += sign * int(PIECE_VALUE_CLASSIC[piece.kind] * _MATERIAL_MULTIPLIER)

    side_count = len(legal)
    other_color = BLACK if board.side_to_move == WHITE else WHITE
    other_count = _count_legal_for(board, other_color)
    if board.side_to_move == WHITE:
        white_count, black_count = side_count, other_count
    else:
        white_count, black_count = other_count, side_count

    # The penalty is symmetric so Hoarder dislikes mobility for both sides:
    # White's score loses points when White has many moves, and gains points
    # when Black has many moves (because that helps drag Black's score down
    # by symmetry too — both sides being forced to make choices is what it
    # is averse to).
    total -= _MOBILITY_PENALTY * (white_count - black_count)
    return total


def choose_move(board, time_left_ms: int) -> Move:
    return pick_best(board, _score, _rng)
