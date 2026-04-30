"""Stage 8: en passant (Week 2 Stage 4)."""

from __future__ import annotations

import pytest

from board import Board
from chessdk import PAWN, parse_square
from .conftest import uci_set


def test_en_passant_target_set_after_double_push():
    """A pawn double-push sets the en-passant target square."""
    b = Board.from_fen("4k3/4p3/8/8/8/8/8/4K3 b - - 0 1")
    move = next(m for m in b.legal_moves() if m.uci() == "e7e5")
    b.make_move(move)
    assert b.state.en_passant == parse_square("e6")
    b.undo_move()
    assert b.state.en_passant is None


def test_en_passant_target_cleared_after_quiet_move():
    """A non-double-push move clears any prior en-passant target."""
    b = Board.from_fen("4k3/8/8/4Pp2/8/8/8/4K3 w - e6 0 1")
    move = next(m for m in b.legal_moves() if m.uci() == "e1d1")
    b.make_move(move)
    assert b.state.en_passant is None
    b.undo_move()
    assert b.state.en_passant == parse_square("e6")


def test_en_passant_capture_legal():
    """White pawn on e5 captures black pawn on f5 via en passant target f6."""
    # Constructing: black just played f7-f5, en passant target is f6.
    b = Board.from_fen("4k3/8/8/4Pp2/8/8/8/4K3 w - f6 0 1")
    legal = uci_set(b.legal_moves())
    assert "e5f6" in legal


def test_en_passant_capture_removes_correct_pawn():
    """Captured pawn sits on f5, NOT on the destination f6."""
    b = Board.from_fen("4k3/8/8/4Pp2/8/8/8/4K3 w - f6 0 1")
    move = next(m for m in b.legal_moves() if m.uci() == "e5f6")
    b.make_move(move)
    # f6: white pawn (the moving one)
    f6 = parse_square("f6")
    assert b.pieces[f6] is not None and b.pieces[f6].kind == PAWN
    # f5: now empty (the captured pawn vanished)
    assert b.pieces[parse_square("f5")] is None
    # e5: now empty (the moving pawn left)
    assert b.pieces[parse_square("e5")] is None


def test_en_passant_undo_restores_captured_pawn():
    """Undo must restore the captured pawn on its original square (f5)."""
    fen = "4k3/8/8/4Pp2/8/8/8/4K3 w - f6 0 1"
    b = Board.from_fen(fen)
    starting_fen = b.to_fen()
    move = next(m for m in b.legal_moves() if m.uci() == "e5f6")
    b.make_move(move)
    b.undo_move()
    assert b.to_fen() == starting_fen
    # Black pawn back on f5
    f5_piece = b.pieces[parse_square("f5")]
    assert f5_piece is not None and f5_piece.kind == PAWN


def test_en_passant_only_when_target_present():
    """No en-passant capture if no en-passant target is set."""
    b = Board.from_fen("4k3/8/8/4Pp2/8/8/8/4K3 w - - 0 1")  # no ep target
    legal = uci_set(b.legal_moves())
    assert "e5f6" not in legal


def test_black_en_passant():
    """Black en passant capture, mirror of the white case."""
    # White just played d2-d4; en passant target d3.
    b = Board.from_fen("4k3/8/8/8/3Pp3/8/8/4K3 b - d3 0 1")
    legal = b.legal_moves()
    assert "e4d3" in {m.uci() for m in legal}
    move = next(m for m in legal if m.uci() == "e4d3")
    b.make_move(move)
    assert b.pieces[parse_square("d4")] is None  # captured pawn gone
    assert b.pieces[parse_square("d3")] is not None  # black pawn here
    assert b.pieces[parse_square("e4")] is None
