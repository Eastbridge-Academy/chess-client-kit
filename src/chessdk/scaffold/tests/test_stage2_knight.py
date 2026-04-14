"""Stage 2, Step 1: knight moves."""

from __future__ import annotations

import pytest

from board import Board
from chessdk import WHITE
from .conftest import uci_set


@pytest.mark.parametrize(
    "fen, side, expected_count",
    [
        # Starting position: 4 knight moves per side
        ("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", "white", 4),
        ("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR b KQkq - 0 1", "black", 4),
        # Lone knight on e4: 8 moves
        ("8/8/8/8/4N3/8/8/8 w - - 0 1", "white", 8),
        # Corner knight (a1): 2 moves
        ("8/8/8/8/8/8/8/N7 w - - 0 1", "white", 2),
        # Edge knight (a4): 4 moves
        ("8/8/8/8/N7/8/8/8 w - - 0 1", "white", 4),
        # Knight on e4 with 1 friendly + 2 enemy pieces on target squares (handout Stage 2 diagram)
        ("8/8/3p4/5P2/4N3/2p5/3P4/8 w - - 0 1", "white", 7),
        # Knight on e4 with friendly pieces on all 8 target squares: 0 moves
        ("8/8/3P1P2/2P3P1/4N3/2P3P1/3P1P2/8 w - - 0 1", "white", 0),
    ],
)
def test_knight_move_counts(fen, side, expected_count):
    b = Board.from_fen(fen)
    moves = b._knight_moves(b.side_to_move)
    assert len(moves) == expected_count, (
        f"{side} knight moves on {fen}: expected {expected_count}, "
        f"got {len(moves)}: {sorted(m.uci() for m in moves)}"
    )


def test_knight_central_moves():
    """Knight on e4, empty board: all 8 destinations."""
    b = Board.from_fen("8/8/8/8/4N3/8/8/8 w - - 0 1")
    moves = b._knight_moves(WHITE)
    assert uci_set(moves) == {
        "e4c3", "e4d2", "e4f2", "e4g3", "e4g5", "e4f6", "e4d6", "e4c5"
    }


def test_knight_handout_diagram():
    """From Stage 2 handout diagram: knight on e4, friendly pawns on d2/f5, enemies on c3/d6."""
    b = Board.from_fen("8/8/3p4/5P2/4N3/2p5/3P4/8 w - - 0 1")
    moves = b._knight_moves(WHITE)
    # d2 (friendly) is blocked. f5 is a friendly pawn but not a knight target from e4.
    # c3 and d6 are captures. c5, f6, g5, g3, f2 are empty.
    assert uci_set(moves) == {"e4c3", "e4c5", "e4d6", "e4f6", "e4g5", "e4g3", "e4f2"}


def test_knight_corner():
    """Knight on a1: only b3 and c2."""
    b = Board.from_fen("8/8/8/8/8/8/8/N7 w - - 0 1")
    moves = b._knight_moves(WHITE)
    assert uci_set(moves) == {"a1b3", "a1c2"}


def test_knight_blocked_by_friendly():
    """All knight target squares occupied by friendly pieces: 0 moves."""
    b = Board.from_fen("8/8/3P1P2/2P3P1/4N3/2P3P1/3P1P2/8 w - - 0 1")
    moves = b._knight_moves(WHITE)
    assert len(moves) == 0


def test_knight_all_captures():
    """All knight target squares occupied by enemy pieces: 8 captures."""
    b = Board.from_fen("8/8/3p1p2/2p3p1/4N3/2p3p1/3p1p2/8 w - - 0 1")
    moves = b._knight_moves(WHITE)
    assert len(moves) == 8
