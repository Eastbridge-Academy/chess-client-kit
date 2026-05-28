"""Stage 18: alpha-beta returns the same score as plain minimax.

Alpha-beta pruning is an optimization — it skips branches the opponent
would never let you reach, but it never changes the score the search
arrives at. We verify this by comparing the student's ``search``
(alpha-beta) against a reference plain-minimax implementation on a
battery of positions and depths. The scores must match exactly.

We compare scores only, not moves: there are usually several
equally-good moves in any position, and which one each algorithm picks
depends on iteration order (which is allowed to differ between
plain minimax and alpha-beta-with-ordering).
"""

from __future__ import annotations

import pytest

from board import Board
from chessdk import MATE_SCORE, PIECE_VALUE_CLASSIC, WHITE
from search import search


def _material(board) -> int:
    total = 0
    for piece in board.pieces:
        if piece is None:
            continue
        sign = 1 if piece.color == WHITE else -1
        total += sign * PIECE_VALUE_CLASSIC[piece.kind]
    return total


def _decay_mate(score: int) -> int:
    if score >= MATE_SCORE - 1000:
        return score - 1
    if score <= -MATE_SCORE + 1000:
        return score + 1
    return score


def _plain_minimax(board, depth: int) -> int:
    """Reference plain-minimax with mate-distance decay, no pruning."""
    legal = board.legal_moves()
    if not legal:
        if board.is_in_check():
            return -MATE_SCORE if board.side_to_move == WHITE else MATE_SCORE
        return 0
    if depth == 0:
        return _material(board)

    if board.side_to_move == WHITE:
        best = -MATE_SCORE - 1
        for move in legal:
            board.make_move(move)
            value = _decay_mate(_plain_minimax(board, depth - 1))
            board.undo_move()
            if value > best:
                best = value
        return best

    best = MATE_SCORE + 1
    for move in legal:
        board.make_move(move)
        value = _decay_mate(_plain_minimax(board, depth - 1))
        board.undo_move()
        if value < best:
            best = value
    return best


POSITIONS = [
    # Starting position
    "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
    # An open middlegame
    "r1bqkb1r/pppp1ppp/2n2n2/4p3/4P3/2N2N2/PPPP1PPP/R1BQKB1R w KQkq - 4 4",
    # A tactical position
    "r1bqk2r/ppp2ppp/2n5/3npb2/1bBP4/2NQ1N2/PPP2PPP/R1B1K2R w KQkq - 0 7",
    # A K+P endgame
    "8/8/8/4k3/4P3/4K3/8/8 w - - 0 1",
]


@pytest.mark.parametrize("fen", POSITIONS)
@pytest.mark.parametrize("depth", [1, 2, 3])
def test_alpha_beta_matches_plain_minimax(fen: str, depth: int):
    board = Board.from_fen(fen)
    ab_score, _ = search(board, depth, _material)
    plain_score = _plain_minimax(board, depth)
    assert ab_score == plain_score, (
        f"alpha-beta and plain minimax disagree at depth {depth} on {fen!r}: "
        f"alpha-beta={ab_score}, plain={plain_score}"
    )
