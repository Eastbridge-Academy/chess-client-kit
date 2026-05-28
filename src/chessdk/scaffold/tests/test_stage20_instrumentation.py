"""Stage 20: instrumentation.

The point of this stage is empirical — the deliverable is the table you
build comparing node counts and timings across search variants, which
pytest cannot grade automatically. The only formal check here is that
your search completes a depth-three lookup on a typical middlegame
position in under two seconds, which is a soft signal that your
alpha-beta cutoffs and move ordering are doing something useful.

If this test fails as a timeout, the likely culprit is that alpha-beta
is not actually pruning (a sign-flip bug in the cutoff condition is the
most common cause) or that ``order_moves`` is not being called by the
search at every node.
"""

from __future__ import annotations

import time

from board import Board
from chessdk import PIECE_VALUE_CLASSIC, WHITE
from search import search


def _material(board) -> int:
    total = 0
    for piece in board.pieces:
        if piece is None:
            continue
        sign = 1 if piece.color == WHITE else -1
        total += sign * PIECE_VALUE_CLASSIC[piece.kind]
    return total


def test_search_at_depth_three_completes_under_two_seconds():
    """A typical middlegame position at depth three with alpha-beta and
    captures-first ordering should finish well inside a couple of seconds."""
    board = Board.from_fen(
        "r1bqkb1r/pppp1ppp/2n2n2/4p3/4P3/2N2N2/PPPP1PPP/R1BQKB1R w KQkq - 4 4"
    )
    start = time.perf_counter()
    score, move = search(board, 3, _material)
    elapsed = time.perf_counter() - start
    assert move in board.legal_moves(), f"returned illegal move {move}"
    assert elapsed < 2.0, (
        f"search at depth 3 took {elapsed:.2f}s; check that alpha-beta "
        f"is actually pruning and that order_moves is being called"
    )
