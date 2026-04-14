"""Stage 4: pawn moves (pushes + captures, no en passant, no promotion)."""

from __future__ import annotations

import pytest

from board import Board
from chessdk import BLACK, WHITE
from .conftest import uci_set


@pytest.mark.parametrize(
    "fen, side, expected_count",
    [
        # Starting position: 16 pawn moves per side (8 singles + 8 doubles)
        ("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", "w", 16),
        ("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR b KQkq - 0 1", "b", 16),
        # Single pawn on 2nd rank, empty board: 2 pushes
        ("8/8/8/8/8/8/4P3/8 w - - 0 1", "w", 2),
        # Single pawn on 3rd rank (past start): 1 push
        ("8/8/8/8/8/4P3/8/8 w - - 0 1", "w", 1),
        # Pawn blocked directly by enemy
        ("8/8/8/8/4p3/4P3/8/8 w - - 0 1", "w", 0),
        # Pawn with diagonal capture available
        ("8/8/8/8/3p1p2/4P3/8/8 w - - 0 1", "w", 3),  # push + 2 captures
        # Pawn on starting rank with blocker on 3rd rank: 0 pushes
        ("8/8/8/8/8/4p3/4P3/8 w - - 0 1", "w", 0),
        # Pawn on starting rank with blocker on 4th rank: 1 push (single only)
        ("8/8/8/8/4p3/8/4P3/8 w - - 0 1", "w", 1),
        # Black pawn handout diagram: only d3 push available
        ("8/8/8/8/3pP3/8/2P3P1/8 b - - 0 1", "b", 1),
    ],
)
def test_pawn_move_counts(fen, side, expected_count):
    b = Board.from_fen(fen)
    moves = b._pawn_moves(b.side_to_move)
    assert len(moves) == expected_count, (
        f"{side} pawn moves on {fen}: expected {expected_count}, "
        f"got {len(moves)}: {sorted(m.uci() for m in moves)}"
    )


def test_pawn_starting_rank_both_pushes():
    b = Board.from_fen("8/8/8/8/8/8/4P3/8 w - - 0 1")
    moves = b._pawn_moves(WHITE)
    assert uci_set(moves) == {"e2e3", "e2e4"}


def test_pawn_captures():
    """White pawn on e4 with black pawns on d5 and f5."""
    b = Board.from_fen("8/8/8/3p1p2/4P3/8/8/8 w - - 0 1")
    moves = b._pawn_moves(WHITE)
    assert uci_set(moves) == {"e4e5", "e4d5", "e4f5"}


def test_pawn_no_capture_on_empty_square():
    """Diagonal squares must contain enemy pieces (not be empty) for captures."""
    b = Board.from_fen("8/8/8/8/4P3/8/8/8 w - - 0 1")
    moves = b._pawn_moves(WHITE)
    assert uci_set(moves) == {"e4e5"}


def test_pawn_double_push_blocked_by_friendly():
    """Double push blocked by friendly piece on 4th rank."""
    b = Board.from_fen("8/8/8/8/4P3/8/4P3/8 w - - 0 1")
    moves = b._pawn_moves(WHITE)
    uci = uci_set(moves)
    assert "e2e3" in uci
    assert "e2e4" not in uci


def test_black_pawn_direction():
    """Black pawn on e7 should push toward rank 1."""
    b = Board.from_fen("8/4p3/8/8/8/8/8/8 b - - 0 1")
    moves = b._pawn_moves(BLACK)
    assert uci_set(moves) == {"e7e6", "e7e5"}


def test_black_pawn_captures():
    """Black pawn on e5 captures white pawns on d4 and f4."""
    b = Board.from_fen("8/8/8/4p3/3P1P2/8/8/8 b - - 0 1")
    moves = b._pawn_moves(BLACK)
    assert uci_set(moves) == {"e5e4", "e5d4", "e5f4"}
