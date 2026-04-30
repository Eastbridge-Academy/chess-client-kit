"""Stage 6 legal_moves tests (Week 2 Stage 2)."""

from __future__ import annotations

import pytest

from board import Board
from .conftest import uci_set


def test_legal_starting_position_count():
    """Starting position has exactly 20 legal moves."""
    b = Board.from_fen("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
    assert len(b.legal_moves()) == 20


def test_pinned_knight_has_no_legal_moves():
    """White knight on e2 pinned against e1 king by black rook on e4.
    The knight cannot move; only king moves off the e-file are legal.
    """
    b = Board.from_fen("4k3/8/8/8/4r3/8/4N3/4K3 w - - 0 1")
    legal = uci_set(b.legal_moves())
    # No knight moves should appear
    assert not any(m.startswith("e2") for m in legal), f"pinned knight moved: {legal}"
    # King moves: e1 to d1, d2, f1, f2 (e2 occupied by own knight; e-file blocked)
    assert legal == {"e1d1", "e1d2", "e1f1", "e1f2"}


def test_must_block_or_capture_when_in_check():
    """White king on e1 in check from rook on e8; must block or move king."""
    b = Board.from_fen("4r3/8/8/8/8/8/8/4K3 w - - 0 1")
    legal = uci_set(b.legal_moves())
    # King can move to d1, d2, f1, f2 (e2 still on the e-file = attacked)
    assert "e1d1" in legal
    assert "e1d2" in legal
    assert "e1f1" in legal
    assert "e1f2" in legal
    # King CANNOT move to e2 (still attacked)
    assert "e1e2" not in legal


def test_back_rank_mate():
    """Classic back-rank mate: black king on g8 trapped by its own pawns on
    f7/g7/h7; white rook on a8 delivers mate along the 8th rank."""
    b = Board.from_fen("R5k1/5ppp/8/8/8/8/8/7K b - - 0 1")
    assert b.is_in_check() is True
    assert b.legal_moves() == []


def test_stalemate():
    """Black king h8 not in check, but every escape square is covered by
    the white queen on g6 (white king on f7 backs it up)."""
    b = Board.from_fen("7k/5K2/6Q1/8/8/8/8/8 b - - 0 1")
    assert b.is_in_check() is False
    assert b.legal_moves() == []


def test_smothered_mate():
    """Smothered mate: black king on h8 walled in by g7/h7 pawns and g8 rook;
    white knight on f7 delivers an unblockable check."""
    b = Board.from_fen("6rk/5Npp/8/8/8/8/8/4K3 b - - 0 1")
    assert b.is_in_check() is True
    assert b.legal_moves() == []


def test_king_cannot_move_adjacent_to_enemy_king():
    """Two-king positions: kings can't be adjacent (legal_moves filter must catch this)."""
    b = Board.from_fen("8/8/8/8/8/3k4/8/3K4 w - - 0 1")
    legal = uci_set(b.legal_moves())
    # White king on d1; if it moved to d2, it would be adjacent to black king on d3.
    # Adjacent means attacked by black king.
    # Squares around d1: c1, c2, d2, e1, e2.
    # d2 -> adjacent to d3 -> illegal.
    # c2 -> adjacent to d3? c2-d3 distance is 1 file 1 rank = adjacent. Illegal.
    # e2 -> adjacent to d3? e2-d3 distance 1-1 = adjacent. Illegal.
    # c1, e1 are 2 ranks from d3, not adjacent. Legal.
    assert "d1c1" in legal
    assert "d1e1" in legal
    assert "d1d2" not in legal
    assert "d1c2" not in legal
    assert "d1e2" not in legal


def test_capture_checker_resolves_check():
    """Checker can be captured to resolve check."""
    # White king on e1, black knight on f3 giving check, white pawn on g2 can take.
    b = Board.from_fen("4k3/8/8/8/8/5n2/6P1/4K3 w - - 0 1")
    assert b.is_in_check() is True
    legal = uci_set(b.legal_moves())
    assert "g2f3" in legal  # pawn captures the checker
