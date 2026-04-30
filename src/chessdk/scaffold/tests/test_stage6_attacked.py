"""Stage 6: attack-detection tests (is_attacked)."""

from __future__ import annotations

import pytest

from board import Board
from chessdk import BLACK, WHITE, parse_square


@pytest.mark.parametrize(
    "fen, square, by_color, expected",
    [
        # Knight attacks
        ("8/8/8/8/4N3/8/8/8 w - - 0 1", "f6", "white", True),
        ("8/8/8/8/4N3/8/8/8 w - - 0 1", "e5", "white", False),  # not a knight target
        ("8/8/8/8/4n3/8/8/8 w - - 0 1", "f6", "black", True),
        ("8/8/8/8/4n3/8/8/8 w - - 0 1", "f6", "white", False),  # wrong color
        # Rook attacks (along files and ranks)
        ("8/8/8/8/4R3/8/8/8 w - - 0 1", "e1", "white", True),
        ("8/8/8/8/4R3/8/8/8 w - - 0 1", "e8", "white", True),
        ("8/8/8/8/4R3/8/8/8 w - - 0 1", "a4", "white", True),
        ("8/8/8/8/4R3/8/8/8 w - - 0 1", "h4", "white", True),
        ("8/8/8/8/4R3/8/8/8 w - - 0 1", "d3", "white", False),  # diagonal
        # Rook blocked by piece on the ray
        ("8/8/8/8/2P1R3/8/8/8 w - - 0 1", "a4", "white", False),  # c4 blocks
        ("8/8/8/8/2P1R3/8/8/8 w - - 0 1", "c4", "white", True),   # the blocker itself
        # Bishop attacks
        ("8/8/8/8/4B3/8/8/8 w - - 0 1", "h7", "white", True),
        ("8/8/8/8/4B3/8/8/8 w - - 0 1", "a8", "white", True),
        ("8/8/8/8/4B3/8/8/8 w - - 0 1", "e6", "white", False),  # vertical, not diagonal
        # Queen attacks (rook + bishop)
        ("8/8/8/8/4Q3/8/8/8 w - - 0 1", "e1", "white", True),
        ("8/8/8/8/4Q3/8/8/8 w - - 0 1", "h7", "white", True),
        ("8/8/8/8/4Q3/8/8/8 w - - 0 1", "g7", "white", False),  # neither file/rank/diag
        # King adjacency
        ("8/8/8/8/4K3/8/8/8 w - - 0 1", "e5", "white", True),
        ("8/8/8/8/4K3/8/8/8 w - - 0 1", "e6", "white", False),  # too far
        # Pawn attacks
        # White pawn on e4 attacks d5 and f5
        ("8/8/8/8/4P3/8/8/8 w - - 0 1", "d5", "white", True),
        ("8/8/8/8/4P3/8/8/8 w - - 0 1", "f5", "white", True),
        ("8/8/8/8/4P3/8/8/8 w - - 0 1", "e5", "white", False),  # not diagonal
        ("8/8/8/8/4P3/8/8/8 w - - 0 1", "d3", "white", False),  # backward
        # Black pawn on e4 attacks d3 and f3
        ("8/8/8/8/4p3/8/8/8 w - - 0 1", "d3", "black", True),
        ("8/8/8/8/4p3/8/8/8 w - - 0 1", "f3", "black", True),
        ("8/8/8/8/4p3/8/8/8 w - - 0 1", "d5", "black", False),
    ],
)
def test_is_attacked(fen, square, by_color, expected):
    b = Board.from_fen(fen)
    color = WHITE if by_color == "white" else BLACK
    got = b.is_attacked(parse_square(square), color)
    assert got == expected, (
        f"is_attacked({square}, {by_color}) on {fen}: expected {expected}, got {got}"
    )


def test_is_attacked_does_not_block_self():
    """A piece doesn't block itself: a square is attacked even if the attacker
    is exactly the piece on that square (only matters for the king-adjacency
    check during legal_moves; here just verify the answer is consistent)."""
    # Rook on e4, query if e4 itself is attacked by white: answer is False since
    # there's no other white attacker, and the rook doesn't attack itself.
    b = Board.from_fen("8/8/8/8/4R3/8/8/8 w - - 0 1")
    assert b.is_attacked(parse_square("e4"), WHITE) is False


def test_is_attacked_in_check_position():
    """White king on e1, black rook on e4 down the e-file: e1 is attacked."""
    b = Board.from_fen("4k3/8/8/8/4r3/8/8/4K3 w - - 0 1")
    assert b.is_attacked(parse_square("e1"), BLACK) is True
    # And b's e2/e3 are also attacked along the way
    assert b.is_attacked(parse_square("e2"), BLACK) is True
    assert b.is_attacked(parse_square("e3"), BLACK) is True


def test_is_attacked_blocked_in_pin():
    """White knight on e2 blocks black rook on e4 from attacking e1."""
    b = Board.from_fen("4k3/8/8/8/4r3/8/4N3/4K3 w - - 0 1")
    # The rook attacks e3 (empty) and stops at e2 (blocked).
    assert b.is_attacked(parse_square("e3"), BLACK) is True
    assert b.is_attacked(parse_square("e2"), BLACK) is True   # the blocker square
    assert b.is_attacked(parse_square("e1"), BLACK) is False  # blocked by knight
