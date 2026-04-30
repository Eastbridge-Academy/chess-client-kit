"""Stage 5 (Week 2 Stage 1): make_move and undo_move round-trip.

For each FEN below, every pseudo-legal move is made and then undone; the
board must return to exactly its starting FEN. This is the gateway test
for the rest of Week 2: nothing further will work without it.
"""

from __future__ import annotations

import pytest

from board import Board


# Positions selected to exercise quiet moves and captures of every piece type,
# without depending on castling / en passant / promotion (which are added in
# later stages and have their own tests).
ROUND_TRIP_FENS = [
    # Lone pieces, empty board
    ("lone-knight", "8/8/8/8/4N3/8/8/8 w - - 0 1"),
    ("lone-bishop", "8/8/8/8/4B3/8/8/8 w - - 0 1"),
    ("lone-rook",   "8/8/8/8/4R3/8/8/8 w - - 0 1"),
    ("lone-queen",  "8/8/8/8/4Q3/8/8/8 w - - 0 1"),
    ("lone-king",   "8/8/8/8/4K3/8/8/8 w - - 0 1"),
    # Capture mixes
    ("knight-captures", "8/8/3p1p2/2p3p1/4N3/2p3p1/3p1p2/8 w - - 0 1"),
    ("bishop-rook-captures", "8/2p5/3p4/4P3/2pBp3/3P4/2p5/8 w - - 0 1"),
    # A no-special-rights position with mixed piece types
    ("midgame-no-rights", "r3k3/8/8/3pP3/2P5/8/PP3PPP/R3K3 w - - 0 1"),
    # Side-to-move = black variant
    ("midgame-black", "r3k3/8/8/3pP3/2P5/8/PP3PPP/R3K3 b - - 0 1"),
    # Pawns with various pushes (no promotion since no pawn reaches rank 7/2)
    ("pawn-pushes", "8/8/8/8/8/8/PPPPPPPP/8 w - - 0 1"),
    ("pawn-pushes-black", "8/pppppppp/8/8/8/8/8/8 b - - 0 1"),
]


@pytest.mark.parametrize("name, fen", ROUND_TRIP_FENS, ids=[n for n, _ in ROUND_TRIP_FENS])
def test_stage5_round_trip(name, fen):
    b = Board.from_fen(fen)
    starting_fen = b.to_fen()
    for move in b.pseudo_legal_moves():
        b.make_move(move)
        b.undo_move()
        got = b.to_fen()
        assert got == starting_fen, (
            f"round-trip failed for {name} on move {move.uci()}\n"
            f"  expected: {starting_fen}\n"
            f"  got:      {got}"
        )


def test_stage5_history_emptied_after_undo():
    """After every make/undo pair, _history should be empty."""
    b = Board.from_fen("8/8/8/8/4N3/8/8/8 w - - 0 1")
    for move in b.pseudo_legal_moves():
        b.make_move(move)
        assert len(b._history) == 1
        b.undo_move()
        assert len(b._history) == 0


def test_stage5_capture_round_trip():
    """A capture must restore the captured piece, not just clear the square."""
    from chessdk import KNIGHT, PAWN, parse_square

    b = Board.from_fen("8/8/5p2/8/4N3/8/8/8 w - - 0 1")
    starting_fen = b.to_fen()
    e4, f6 = parse_square("e4"), parse_square("f6")
    target_move = next(m for m in b.pseudo_legal_moves() if m.uci() == "e4f6")
    b.make_move(target_move)
    assert b.pieces[f6] is not None and b.pieces[f6].kind == KNIGHT
    assert b.pieces[e4] is None
    b.undo_move()
    assert b.to_fen() == starting_fen
    assert b.pieces[f6] is not None and b.pieces[f6].kind == PAWN


def test_stage5_halfmove_clock_resets_on_pawn_move():
    b = Board.from_fen("8/8/8/8/8/8/4P3/4K3 w - - 5 1")
    # Find e2-e3
    move = next(m for m in b.pseudo_legal_moves() if m.uci() == "e2e3")
    b.make_move(move)
    assert b.state.halfmove_clock == 0
    b.undo_move()
    assert b.state.halfmove_clock == 5


def test_stage5_halfmove_clock_increments_on_quiet_move():
    b = Board.from_fen("8/8/8/8/4N3/8/8/4K3 w - - 5 1")
    move = next(m for m in b.pseudo_legal_moves() if m.uci() == "e4f6")
    b.make_move(move)
    assert b.state.halfmove_clock == 6
    b.undo_move()
    assert b.state.halfmove_clock == 5


def test_stage5_halfmove_clock_resets_on_capture():
    b = Board.from_fen("8/8/5p2/8/4N3/8/8/4K3 w - - 7 1")
    move = next(m for m in b.pseudo_legal_moves() if m.uci() == "e4f6")
    b.make_move(move)
    assert b.state.halfmove_clock == 0
    b.undo_move()
    assert b.state.halfmove_clock == 7


def test_stage5_fullmove_increments_after_black():
    b = Board.from_fen("4k3/4p3/8/8/8/8/8/4K3 b - - 0 5")
    move = next(m for m in b.pseudo_legal_moves() if m.uci() == "e7e6")
    b.make_move(move)
    assert b.state.fullmove_number == 6
    b.undo_move()
    assert b.state.fullmove_number == 5


def test_stage5_fullmove_unchanged_after_white():
    b = Board.from_fen("4k3/8/8/8/8/8/4P3/4K3 w - - 0 5")
    move = next(m for m in b.pseudo_legal_moves() if m.uci() == "e2e3")
    b.make_move(move)
    assert b.state.fullmove_number == 5
    b.undo_move()
    assert b.state.fullmove_number == 5


def test_stage5_side_to_move_flips():
    b = Board.from_fen("4k3/8/8/8/8/8/4P3/4K3 w - - 0 1")
    from chessdk import BLACK, WHITE
    assert b.side_to_move == WHITE
    move = next(m for m in b.pseudo_legal_moves() if m.uci() == "e2e3")
    b.make_move(move)
    assert b.side_to_move == BLACK
    b.undo_move()
    assert b.side_to_move == WHITE
