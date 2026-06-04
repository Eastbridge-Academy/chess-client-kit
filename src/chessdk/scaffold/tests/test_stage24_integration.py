"""Stage 24: the pieces work together and the diagnostics are wired.

Stage 24 is mostly a measurement-and-tuning stage, which pytest cannot
grade. The one thing it can check is that the iterative-deepening driver
sets the module-level ``last_depth`` and ``last_score`` the UCI wrapper
reads, so the depth and score actually show up in cutechess during games,
and that a timed search returns a legal move.
"""

from __future__ import annotations

import search as student_search
from board import Board
from chessdk import PIECE_VALUE_CLASSIC, WHITE
from search import search_iterative


def _material(board) -> int:
    total = 0
    for piece in board.pieces:
        if piece is None:
            continue
        sign = 1 if piece.color == WHITE else -1
        total += sign * PIECE_VALUE_CLASSIC[piece.kind]
    return total


MID = "r1bqkb1r/pppp1ppp/2n2n2/4p3/4P3/2N2N2/PPPP1PPP/R1BQKB1R w KQkq - 4 4"


def test_timed_search_returns_legal_move_and_sets_diagnostics():
    board = Board.from_fen(MID)
    _, move = search_iterative(board, _material, max_depth=4, time_budget_ms=500)
    assert move in Board.from_fen(MID).legal_moves()

    last_depth = getattr(student_search, "last_depth", None)
    last_score = getattr(student_search, "last_score", None)
    assert last_depth is not None and last_depth >= 1, (
        "search_iterative should set the module-level last_depth so cutechess "
        "can show the search depth (Stage 21, Step 1)"
    )
    assert last_score is not None, (
        "search_iterative should set the module-level last_score so cutechess "
        "can show the evaluation (Stage 21, Step 1)"
    )
