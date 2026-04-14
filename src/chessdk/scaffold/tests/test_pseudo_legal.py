"""pseudo_legal_moves(): wiring and starting-position perft(1)."""

from __future__ import annotations

import pytest

from board import Board


def test_starting_position_perft_1():
    """White at the starting position has exactly 20 pseudo-legal moves."""
    b = Board()
    moves = b.pseudo_legal_moves()
    assert len(moves) == 20, (
        f"Starting position should have 20 moves, got {len(moves)}: "
        f"{sorted(m.uci() for m in moves)}"
    )


def test_starting_position_black():
    """Black at the starting position also has 20 moves."""
    b = Board.from_fen("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR b KQkq - 0 1")
    assert len(b.pseudo_legal_moves()) == 20


def test_pseudo_legal_only_side_to_move():
    """pseudo_legal_moves returns only the side-to-move's moves, not the other side's."""
    b = Board()
    white_moves = b.pseudo_legal_moves()
    # Every move originates from a white piece
    for m in white_moves:
        assert b.piece_at(m.from_sq).color.name == "WHITE"


def test_pseudo_legal_empty_board_no_moves():
    """No pieces = no moves (king-only wouldn't be a legal FEN so use both kings)."""
    b = Board.from_fen("4k3/8/8/8/8/8/8/4K3 w - - 0 1")
    # Just the two kings. White has king on e1 with adjacent squares d1, d2, e2, f1, f2 = 5
    moves = b.pseudo_legal_moves()
    assert len(moves) == 5
