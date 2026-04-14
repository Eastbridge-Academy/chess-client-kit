"""Stage 1: piece_at and pieces_of."""

from __future__ import annotations

import pytest

from board import Board
from chessdk import BLACK, KNIGHT, PAWN, Piece, WHITE, parse_square


def test_piece_at_starting_rank():
    b = Board()
    assert b.piece_at(parse_square("e1")).char == "K"
    assert b.piece_at(parse_square("e8")).char == "k"
    assert b.piece_at(parse_square("d1")).char == "Q"
    assert b.piece_at(parse_square("a1")).char == "R"
    assert b.piece_at(parse_square("a2")).char == "P"
    assert b.piece_at(parse_square("h7")).char == "p"


def test_piece_at_empty_square():
    b = Board()
    assert b.piece_at(parse_square("e4")) is None
    assert b.piece_at(parse_square("d5")) is None


def test_piece_at_custom_position():
    b = Board.from_fen("8/8/8/8/4N3/8/8/8 w - - 0 1")
    assert b.piece_at(parse_square("e4")).char == "N"
    assert b.piece_at(parse_square("e4")).color == WHITE
    for sq_name in ["a1", "h8", "d4", "e5"]:
        assert b.piece_at(parse_square(sq_name)) is None


def test_pieces_of_starting_position():
    b = Board()
    white_pieces = list(b.pieces_of(WHITE))
    black_pieces = list(b.pieces_of(BLACK))
    assert len(white_pieces) == 16
    assert len(black_pieces) == 16
    # All piece kinds present on each side
    white_kinds = [piece.kind for _, piece in white_pieces]
    assert white_kinds.count(PAWN) == 8
    assert white_kinds.count(KNIGHT) == 2
    # All returned squares actually hold the given piece
    for square, piece in white_pieces:
        assert b.piece_at(square) == piece


def test_pieces_of_empty_board():
    b = Board.from_fen("8/8/8/8/8/8/8/8 w - - 0 1")
    assert list(b.pieces_of(WHITE)) == []
    assert list(b.pieces_of(BLACK)) == []


def test_pieces_of_mixed():
    b = Board.from_fen("8/8/3p4/8/4N3/8/8/4K3 w - - 0 1")
    white = [(sq, p.char) for sq, p in b.pieces_of(WHITE)]
    black = [(sq, p.char) for sq, p in b.pieces_of(BLACK)]
    assert sorted(p for _, p in white) == ["K", "N"]
    assert [p for _, p in black] == ["p"]
