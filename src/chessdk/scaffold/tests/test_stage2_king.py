"""Stage 2, Step 2: king moves (no castling)."""

from __future__ import annotations

import pytest

from board import Board
from chessdk import WHITE
from .conftest import uci_set


@pytest.mark.parametrize(
    "fen, expected_count",
    [
        # Central king, empty board: 8 moves
        ("8/8/8/8/3K4/8/8/8 w - - 0 1", 8),
        # Corner king: 3 moves
        ("8/8/8/8/8/8/8/K7 w - - 0 1", 3),
        # Edge king: 5 moves
        ("8/8/8/8/K7/8/8/8 w - - 0 1", 5),
        # King with all adjacent squares friendly: 0 moves
        ("8/8/8/2PPP3/2PKP3/2PPP3/8/8 w - - 0 1", 0),
        # King with all adjacent squares enemy: 8 captures
        ("8/8/8/2ppp3/2pKp3/2ppp3/8/8 w - - 0 1", 8),
    ],
)
def test_king_move_counts(fen, expected_count):
    b = Board.from_fen(fen)
    moves = b._king_moves(b.side_to_move)
    assert len(moves) == expected_count, (
        f"king moves on {fen}: expected {expected_count}, "
        f"got {len(moves)}: {sorted(m.uci() for m in moves)}"
    )


def test_king_central_destinations():
    b = Board.from_fen("8/8/8/8/3K4/8/8/8 w - - 0 1")
    moves = b._king_moves(WHITE)
    assert uci_set(moves) == {
        "d4c3", "d4d3", "d4e3", "d4e4", "d4e5", "d4d5", "d4c5", "d4c4"
    }


def test_king_corner_a1():
    b = Board.from_fen("8/8/8/8/8/8/8/K7 w - - 0 1")
    moves = b._king_moves(WHITE)
    assert uci_set(moves) == {"a1a2", "a1b2", "a1b1"}
