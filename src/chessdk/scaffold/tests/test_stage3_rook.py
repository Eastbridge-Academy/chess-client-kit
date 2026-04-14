"""Stage 3, Step 2: rook moves."""

from __future__ import annotations

import pytest

from board import Board
from chessdk import WHITE
from .conftest import uci_set


@pytest.mark.parametrize(
    "fen, expected_count",
    [
        # Central rook, empty board: 14 moves (7 along file + 7 along rank)
        ("8/8/8/8/3R4/8/8/8 w - - 0 1", 14),
        # Corner rook: still 14 moves (full file + full rank)
        ("8/8/8/8/8/8/8/R7 w - - 0 1", 14),
        # Rook blocked by friendly on all 4 sides (one square away)
        ("8/8/8/3P4/2PRP3/3P4/8/8 w - - 0 1", 0),
        # Rook with 4 adjacent captures
        ("8/8/8/3p4/2pRp3/3p4/8/8 w - - 0 1", 4),
    ],
)
def test_rook_move_counts(fen, expected_count):
    b = Board.from_fen(fen)
    moves = b._rook_moves(b.side_to_move)
    assert len(moves) == expected_count, (
        f"rook moves on {fen}: expected {expected_count}, "
        f"got {len(moves)}: {sorted(m.uci() for m in moves)}"
    )


def test_rook_central_destinations():
    b = Board.from_fen("8/8/8/8/3R4/8/8/8 w - - 0 1")
    moves = b._rook_moves(WHITE)
    expected = {
        # Along the d-file
        "d4d1", "d4d2", "d4d3", "d4d5", "d4d6", "d4d7", "d4d8",
        # Along the 4th rank
        "d4a4", "d4b4", "d4c4", "d4e4", "d4f4", "d4g4", "d4h4",
    }
    assert uci_set(moves) == expected
