"""Stage 8: pawn promotion (Week 2 Stage 4)."""

from __future__ import annotations

import pytest

from board import Board
from chessdk import BISHOP, KING, KNIGHT, PAWN, QUEEN, ROOK, parse_square
from .conftest import uci_set


def test_promotion_generates_four_moves():
    """A pawn pushing to the last rank should produce 4 promotion moves."""
    b = Board.from_fen("8/4P3/8/8/8/8/8/k6K w - - 0 1")
    moves = uci_set(b._pawn_moves(b.side_to_move))
    assert "e7e8q" in moves
    assert "e7e8r" in moves
    assert "e7e8b" in moves
    assert "e7e8n" in moves
    # And only those four pawn moves (no non-promotion e7e8)
    assert "e7e8" not in moves


def test_capture_promotion_generates_four_moves():
    """Pawn capturing onto last rank also generates four promotion moves."""
    # White pawn on e7 captures black piece on f8 (or d8)
    b = Board.from_fen("3r1r2/4P3/8/8/8/8/8/k6K w - - 0 1")
    moves = uci_set(b._pawn_moves(b.side_to_move))
    assert {"e7d8q", "e7d8r", "e7d8b", "e7d8n"} <= moves
    assert {"e7f8q", "e7f8r", "e7f8b", "e7f8n"} <= moves
    # Push e7-e8 also promotes (4 moves)
    assert {"e7e8q", "e7e8r", "e7e8b", "e7e8n"} <= moves


def test_promotion_make_move_replaces_piece():
    """After promotion, the destination square holds the promoted piece, not a pawn."""
    b = Board.from_fen("8/4P3/8/8/8/8/8/k6K w - - 0 1")
    move = next(m for m in b.legal_moves() if m.uci() == "e7e8q")
    b.make_move(move)
    promoted = b.pieces[parse_square("e8")]
    assert promoted is not None
    assert promoted.kind == QUEEN
    assert b.pieces[parse_square("e7")] is None


def test_promotion_undo_restores_pawn():
    """Undo of a promotion must put a pawn back on the source square."""
    b = Board.from_fen("8/4P3/8/8/8/8/8/k6K w - - 0 1")
    starting_fen = b.to_fen()
    for promo_uci in ("e7e8q", "e7e8r", "e7e8b", "e7e8n"):
        move = next(m for m in b.legal_moves() if m.uci() == promo_uci)
        b.make_move(move)
        b.undo_move()
        assert b.to_fen() == starting_fen
        # Pawn back on e7
        pawn = b.pieces[parse_square("e7")]
        assert pawn is not None and pawn.kind == PAWN


def test_capture_promotion_round_trip():
    """Capture-promotion round-trip restores both the moving pawn and the
    captured piece."""
    b = Board.from_fen("3r4/4P3/8/8/8/8/8/k6K w - - 0 1")
    starting_fen = b.to_fen()
    move = next(m for m in b.legal_moves() if m.uci() == "e7d8q")
    b.make_move(move)
    # d8: white queen, e7: empty
    assert b.pieces[parse_square("d8")].kind == QUEEN
    assert b.pieces[parse_square("e7")] is None
    b.undo_move()
    assert b.to_fen() == starting_fen


def test_black_promotion():
    """Black pawn on e2 promotes to rank 1."""
    b = Board.from_fen("k6K/8/8/8/8/8/4p3/8 b - - 0 1")
    moves = uci_set(b._pawn_moves(b.side_to_move))
    assert {"e2e1q", "e2e1r", "e2e1b", "e2e1n"} <= moves
    assert "e2e1" not in moves


def test_no_promotion_for_double_push():
    """Double push from rank 2 lands on rank 4 (never a promotion)."""
    b = Board.from_fen("k6K/8/8/8/8/8/4P3/8 w - - 0 1")
    moves = uci_set(b._pawn_moves(b.side_to_move))
    assert "e2e4" in moves
    # No promotion-flavored variants
    for kind in "qrbn":
        assert f"e2e4{kind}" not in moves
