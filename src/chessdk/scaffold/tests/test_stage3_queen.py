"""Stage 3, Step 3: queen moves."""

from __future__ import annotations

import pytest

from board import Board
from chessdk import WHITE


@pytest.mark.parametrize(
    "fen, expected_count",
    [
        # Central queen, empty board: 27 (= rook's 14 + bishop's 13)
        ("8/8/8/8/3Q4/8/8/8 w - - 0 1", 27),
        # Corner queen a1: 21 (7 + 7 + 7 diagonal)
        ("8/8/8/8/8/8/8/Q7 w - - 0 1", 21),
        # Queen surrounded by friendly on all 8 squares
        ("8/8/8/2PPP3/2PQP3/2PPP3/8/8 w - - 0 1", 0),
        # Queen with 8 adjacent captures
        ("8/8/8/2ppp3/2pQp3/2ppp3/8/8 w - - 0 1", 8),
    ],
)
def test_queen_move_counts(fen, expected_count):
    b = Board.from_fen(fen)
    moves = b._queen_moves(b.side_to_move)
    assert len(moves) == expected_count, (
        f"queen moves on {fen}: expected {expected_count}, "
        f"got {len(moves)}: {sorted(m.uci() for m in moves)}"
    )


def test_queen_equals_bishop_plus_rook():
    """Queen on an empty square equals the sum of a bishop and a rook on the same square."""
    queen_board = Board.from_fen("8/8/8/8/3Q4/8/8/8 w - - 0 1")
    bishop_board = Board.from_fen("8/8/8/8/3B4/8/8/8 w - - 0 1")
    rook_board = Board.from_fen("8/8/8/8/3R4/8/8/8 w - - 0 1")
    qm = len(queen_board._queen_moves(WHITE))
    bm = len(bishop_board._bishop_moves(WHITE))
    rm = len(rook_board._rook_moves(WHITE))
    assert qm == bm + rm
