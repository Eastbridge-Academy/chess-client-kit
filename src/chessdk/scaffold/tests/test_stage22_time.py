"""Stage 22: the time budget bounds the search and never leaves you empty-handed.

Two properties matter, and both are deliberately loose (time-based tests
are noisy by nature):

  - On a tiny budget, the search still returns a legal move, because depth
    one always runs before the clock is consulted.
  - A tiny budget actually stops the deepening early: a 1ms-budget search
    finishes well before a full fixed-depth search of the same position
    would. This is a relative comparison on the same machine, so it does
    not depend on how fast the machine is.

Both calls cap ``max_depth`` so that an implementation that ignores the
budget terminates (and fails the comparison) rather than running away.
"""

from __future__ import annotations

import time

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


MID = "r1bqkb1r/pppp1ppp/2n2n2/4p3/4P3/2N2N2/PPPP1PPP/R1BQKB1R w KQkq - 4 4"


def test_tiny_budget_returns_legal_move():
    board = Board.from_fen(MID)
    _, move = search_iterative(board, _material, max_depth=5, time_budget_ms=1)
    assert move in Board.from_fen(MID).legal_moves(), (
        "a 1ms budget must still return a legal move; make sure depth one "
        "runs before you start checking the clock"
    )


def test_tiny_budget_stops_deepening_early():
    # Baseline: the cost of a full fixed-depth search to the cap.
    start = time.perf_counter()
    search(Board.from_fen(MID), 4, _material)
    full_depth_time = time.perf_counter() - start

    # A 1ms budget should stop long before reaching the cap.
    start = time.perf_counter()
    search_iterative(Board.from_fen(MID), _material, max_depth=4, time_budget_ms=1)
    budgeted_time = time.perf_counter() - start

    assert budgeted_time < full_depth_time * 0.5, (
        f"a 1ms-budget search took {budgeted_time:.3f}s versus {full_depth_time:.3f}s "
        f"for a full depth-4 search; the budget is not stopping the deepening "
        f"(check that you break between iterations once the budget is spent)"
    )
