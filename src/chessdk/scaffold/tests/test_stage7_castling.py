"""Stage 7: castling generation and make/undo."""

from __future__ import annotations

import pytest

from board import Board
from chessdk import parse_square
from .conftest import uci_set


def _legal_castles(fen: str) -> set[str]:
    """Return the set of castling moves (king moves of two squares) in legal_moves."""
    b = Board.from_fen(fen)
    out = set()
    for m in b.legal_moves():
        if abs(m.to_sq - m.from_sq) == 2 and (
            m.from_sq in (parse_square("e1"), parse_square("e8"))
        ):
            out.add(m.uci())
    return out


# Reference: in this position both colors can castle either way.
ALL_RIGHTS = "r3k2r/8/8/8/8/8/8/R3K2R"


def test_kingside_castle_white_legal():
    fen = f"{ALL_RIGHTS} w KQkq - 0 1"
    assert "e1g1" in _legal_castles(fen)


def test_queenside_castle_white_legal():
    fen = f"{ALL_RIGHTS} w KQkq - 0 1"
    assert "e1c1" in _legal_castles(fen)


def test_kingside_castle_black_legal():
    fen = f"{ALL_RIGHTS} b KQkq - 0 1"
    assert "e8g8" in _legal_castles(fen)


def test_queenside_castle_black_legal():
    fen = f"{ALL_RIGHTS} b KQkq - 0 1"
    assert "e8c8" in _legal_castles(fen)


def test_no_castle_without_rights():
    fen = f"{ALL_RIGHTS} w - - 0 1"
    assert _legal_castles(fen) == set()


def test_no_castle_through_piece():
    """White king can't castle kingside if f1 or g1 is occupied."""
    fen = "r3k2r/8/8/8/8/8/8/R3KB1R w KQkq - 0 1"
    castles = _legal_castles(fen)
    assert "e1g1" not in castles  # f1 has bishop
    # Queenside is fine
    assert "e1c1" in castles


def test_no_castle_through_attacked_square():
    """White cannot castle kingside if f1 is attacked (king transits f1)."""
    # Black rook on f8 attacks f1
    fen = "r3kr2/8/8/8/8/8/8/R3K2R w KQkq - 0 1"
    castles = _legal_castles(fen)
    assert "e1g1" not in castles  # f1 attacked
    # Queenside fine: c1, d1 not attacked by the rook on f8 (different file)
    assert "e1c1" in castles


def test_no_castle_into_attacked_square():
    """White cannot castle kingside if g1 is attacked (king lands on g1)."""
    fen = "r3k1r1/8/8/8/8/8/8/R3K2R w KQkq - 0 1"
    castles = _legal_castles(fen)
    assert "e1g1" not in castles  # g1 attacked by rook on g8


def test_no_castle_when_in_check():
    """Cannot castle out of check."""
    # White rook on e8 checks black king on e8... wait it'd be black rook checking white king
    fen = "r3k3/4r3/8/8/8/8/8/R3K2R w KQkq - 0 1"
    castles = _legal_castles(fen)
    assert castles == set()  # white in check, no castles


def test_queenside_b_square_attack_irrelevant():
    """For queenside, b1 must be EMPTY but not necessarily NOT-ATTACKED;
    the king never visits b1, only the rook passes over it."""
    # Black bishop on h7 attacks b1 (along the h7-a... wait, b1 isn't on a diagonal from h7).
    # Let me put a black rook on b8 attacking b1. Bishop diagonal: b1 to h7 is (+6, +6) — yes
    # bishop on h7 attacks b1 via the diagonal a-h8 -> b1 is on a2-h8? Let me just use
    # black rook on b3 attacking down b-file. Wait, b3 is white-side, can't put black rook there
    # without justification. Use black bishop on a2 attacking b1? a2-b1 = (1, -1) yes diagonal.
    # But a2 is also too close to white. Just use FEN with bishop attacking b1.
    fen = "r3k2r/8/8/8/8/8/b7/R3K2R w KQkq - 0 1"
    # Black bishop on a2: attacks b1 via diagonal a2-b1.
    # b1 attacked but empty (queenside path b1/c1/d1 must be empty -> yes), c1 and d1 not attacked.
    castles = _legal_castles(fen)
    assert "e1c1" in castles  # queenside still legal even though b1 is attacked


def test_castling_rights_revoked_after_king_move():
    """Moving the king (without castling) clears both castling rights."""
    b = Board.from_fen(f"{ALL_RIGHTS} w KQkq - 0 1")
    # Move king from e1 to e2
    move = next(m for m in b.legal_moves() if m.uci() == "e1e2")
    b.make_move(move)
    assert b.state.castling.white_kingside is False
    assert b.state.castling.white_queenside is False
    # Black rights unchanged
    assert b.state.castling.black_kingside is True
    assert b.state.castling.black_queenside is True
    b.undo_move()
    # After undo, rights restored
    assert b.state.castling.white_kingside is True
    assert b.state.castling.white_queenside is True


def test_castling_rights_revoked_after_rook_move():
    b = Board.from_fen(f"{ALL_RIGHTS} w KQkq - 0 1")
    # h1 rook moves
    move = next(m for m in b.legal_moves() if m.uci() == "h1h2")
    b.make_move(move)
    assert b.state.castling.white_kingside is False
    assert b.state.castling.white_queenside is True  # queenside still
    b.undo_move()
    assert b.state.castling.white_kingside is True


def test_castling_rights_revoked_when_rook_captured():
    """A capture on a starting corner clears that side's right."""
    # Black bishop on b8 captures white rook on h1? No, too far.
    # Black knight reachable from h1: f2, g3 — black knight on f2 captures h1.
    fen = "4k3/8/8/8/8/8/5n2/R3K2R b KQ - 0 1"
    b = Board.from_fen(fen)
    move = next(m for m in b.legal_moves() if m.uci() == "f2h1")
    b.make_move(move)
    assert b.state.castling.white_kingside is False
    assert b.state.castling.white_queenside is True  # a1 rook still there
    b.undo_move()
    assert b.state.castling.white_kingside is True


def test_kingside_castle_make_move_moves_rook():
    b = Board.from_fen(f"{ALL_RIGHTS} w KQkq - 0 1")
    move = next(m for m in b.legal_moves() if m.uci() == "e1g1")
    b.make_move(move)
    # King on g1, rook on f1, e1/h1 empty
    assert b.pieces[parse_square("g1")] is not None
    assert b.pieces[parse_square("f1")] is not None
    assert b.pieces[parse_square("e1")] is None
    assert b.pieces[parse_square("h1")] is None
    b.undo_move()
    # All restored
    assert b.pieces[parse_square("e1")] is not None
    assert b.pieces[parse_square("h1")] is not None
    assert b.pieces[parse_square("g1")] is None
    assert b.pieces[parse_square("f1")] is None


def test_queenside_castle_make_move_moves_rook():
    b = Board.from_fen(f"{ALL_RIGHTS} w KQkq - 0 1")
    move = next(m for m in b.legal_moves() if m.uci() == "e1c1")
    b.make_move(move)
    # King on c1, rook on d1, a1/e1 empty
    assert b.pieces[parse_square("c1")] is not None
    assert b.pieces[parse_square("d1")] is not None
    assert b.pieces[parse_square("e1")] is None
    assert b.pieces[parse_square("a1")] is None
    # b1 is empty (always was; rook passes over it)
    assert b.pieces[parse_square("b1")] is None
    b.undo_move()
    assert b.pieces[parse_square("e1")] is not None
    assert b.pieces[parse_square("a1")] is not None
