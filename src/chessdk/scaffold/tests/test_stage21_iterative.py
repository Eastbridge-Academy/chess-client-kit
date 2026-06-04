"""Stage 21: iterative deepening returns the same answer as a fixed-depth search.

Iterative deepening walks the same tree as a single search to the final
depth, just one depth at a time; it must arrive at the same value. We
verify that ``search_iterative(board, eval_fn, depth)`` returns the same
score as ``search(board, depth, eval_fn)`` on a battery of positions and
depths, and that the move it returns is legal.

We compare scores, not moves: as in Stage 18, several moves can be equally
good and which one wins a tie depends on iteration order, which is allowed
to differ once the previous iteration's best move is seeded to the front.
"""

from __future__ import annotations

import pytest

from board import Board
from chessdk import PIECE_VALUE_CLASSIC, WHITE
from search import search, search_iterative


def _material(board) -> int:
    total = 0
    for piece in board.pieces:
        if piece is None:
            continue
        sign = 1 if piece.color == WHITE else -1
        total += sign * PIECE_VALUE_CLASSIC[piece.kind]
    return total


POSITIONS = [
    # Starting position
    "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
    # An open middlegame
    "r1bqkb1r/pppp1ppp/2n2n2/4p3/4P3/2N2N2/PPPP1PPP/R1BQKB1R w KQkq - 4 4",
    # A K+P endgame (Black to move)
    "8/8/8/4k3/4P3/4K3/8/8 b - - 0 1",
]


@pytest.mark.parametrize("fen", POSITIONS)
@pytest.mark.parametrize("depth", [2, 3])
def test_iterative_matches_fixed_depth(fen: str, depth: int):
    iter_score, iter_move = search_iterative(Board.from_fen(fen), _material, depth)
    fixed_score, _ = search(Board.from_fen(fen), depth, _material)
    assert iter_score == fixed_score, (
        f"iterative deepening and a direct depth-{depth} search disagree on "
        f"{fen!r}: iterative={iter_score}, fixed={fixed_score}. The usual "
        f"cause is returning the in-progress iteration instead of the last "
        f"one that finished."
    )
    assert iter_move in Board.from_fen(fen).legal_moves()


def test_iterative_returns_legal_move_at_depth_one():
    board = Board.from_fen(POSITIONS[1])
    _, move = search_iterative(board, _material, 1)
    assert move in board.legal_moves()
