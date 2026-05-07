"""Tests for chessdk.evaluation helpers."""

from __future__ import annotations

from chessdk import (
    BISHOP,
    BLACK,
    KNIGHT,
    PAWN,
    PIECE_VALUE,
    QUEEN,
    ROOK,
    WHITE,
    min_attacker_value,
    parse_square,
)
from chessdk.reference import Board


def test_no_attackers_returns_none():
    fen = "8/8/8/3K4/8/8/8/4k3 w - - 0 1"
    board = Board.from_fen(fen)
    assert min_attacker_value(board, parse_square("e4"), BLACK) is None


def test_pawn_attacker_is_cheapest():
    # Black pawn on d5 attacks e4 (and c4).
    fen = "8/8/8/3p4/8/8/8/4K2k w - - 0 1"
    board = Board.from_fen(fen)
    assert min_attacker_value(board, parse_square("e4"), BLACK) == PIECE_VALUE[PAWN]
    assert min_attacker_value(board, parse_square("c4"), BLACK) == PIECE_VALUE[PAWN]
    # d4 is not attacked (pawns capture diagonally)
    assert min_attacker_value(board, parse_square("d4"), BLACK) is None


def test_knight_picked_when_no_pawn():
    # Black knight on c6, target square e5.
    fen = "8/8/2n5/8/8/8/8/4K2k w - - 0 1"
    board = Board.from_fen(fen)
    assert min_attacker_value(board, parse_square("e5"), BLACK) == PIECE_VALUE[KNIGHT]


def test_bishop_along_diagonal():
    # Black bishop on h8; a1 attacked.
    fen = "7b/8/8/8/8/8/8/4K2k w - - 0 1"
    board = Board.from_fen(fen)
    assert min_attacker_value(board, parse_square("a1"), BLACK) == PIECE_VALUE[BISHOP]


def test_rook_along_file():
    fen = "8/8/8/8/4r3/8/8/4K2k w - - 0 1"
    board = Board.from_fen(fen)
    # White king on e1 is attacked by the rook on e4.
    assert min_attacker_value(board, parse_square("e1"), BLACK) == PIECE_VALUE[ROOK]


def test_blocker_stops_slider():
    # Black rook on a8, but a black pawn on a4 blocks the file.
    fen = "r7/8/8/8/p7/8/8/K6k w - - 0 1"
    board = Board.from_fen(fen)
    # a1 is not attacked by the rook (pawn in the way) but is attacked by the pawn? No, pawn on a4 captures b3.
    # So a1 has no enemy attackers.
    assert min_attacker_value(board, parse_square("a1"), BLACK) is None


def test_picks_cheapest_when_multiple_attackers():
    # Black pawn on d5 and black queen on a1 both attack e4 (queen along long diagonal).
    fen = "8/8/8/3p4/8/8/8/q3K2k w - - 0 1"
    board = Board.from_fen(fen)
    # Pawn (100) wins over queen (900).
    assert min_attacker_value(board, parse_square("e4"), BLACK) == PIECE_VALUE[PAWN]
