"""Stage 28: the table never changes the answer, only the speed.

Your search with the transposition table, ``search_tt`` (probe, hash move,
store, bound flags), must return the same score as your plain ``search`` at the
same depth, on every position. The table is allowed to reach the answer faster;
it is never allowed to reach a different one. A wrong bound flag is exactly the
bug that breaks this: it makes the table hand back a score the position does not
have.

``search_tt`` is added in this phase, so we look it up lazily inside the test
rather than importing it at the top; that way this file still collects (and the
rest of your suite still runs) before you have written it.
"""

from __future__ import annotations

import pytest

import search as student_search
from board import Board
from chessdk import PIECE_VALUE_CLASSIC, WHITE


def _material(board) -> int:
    total = 0
    for piece in board.pieces:
        if piece is None:
            continue
        value = PIECE_VALUE_CLASSIC[piece.kind]
        total += value if piece.color == WHITE else -value
    return total


# Positions and depths where a correct table search returns exactly the plain
# fixed-depth score (the kit's reference implementation is verified to agree
# here, mate positions included).
CASES = [
    ("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", 3),
    ("r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 0 1", 3),
    ("r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1", 2),
    ("r1bq1rk1/pp2bppp/2n1pn2/2pp4/3P1B2/2PBPN2/PP1N1PPP/R2Q1RK1 w - - 0 1", 3),
    ("k3q3/8/8/8/8/8/5PPP/6K1 b - - 0 1", 3),  # mate available: exercises mate scores
]


@pytest.mark.parametrize("fen,depth", CASES)
def test_tt_search_matches_plain_search(fen, depth):
    assert hasattr(student_search, "search_tt"), (
        "search.py has no search_tt yet -- implement it (Phase 7, Stages 27-28)."
    )
    search = student_search.search
    search_tt = student_search.search_tt

    plain_score, _ = search(Board.from_fen(fen), depth, _material)
    tt_score, tt_move = search_tt(Board.from_fen(fen), depth, _material, {})
    assert tt_score == plain_score
    if tt_move is not None:
        assert tt_move in Board.from_fen(fen).legal_moves()
