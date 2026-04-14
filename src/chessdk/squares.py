"""Square helpers and move offset constants.

Square indices run 0..63 with 0 = a1, 7 = h1, 56 = a8, 63 = h8. Files go 0
(a-file) to 7 (h-file); ranks go 0 (rank 1) to 7 (rank 8). This matches the
layout used by python-chess and most modern engines.
"""

from __future__ import annotations


def sq(file: int, rank: int) -> int:
    """Return the square index at (file, rank)."""
    return rank * 8 + file


def file_of(square: int) -> int:
    """Return the file (0..7) of the given square."""
    return square & 7


def rank_of(square: int) -> int:
    """Return the rank (0..7) of the given square."""
    return square >> 3


def on_board(file: int, rank: int) -> bool:
    """True iff (file, rank) is a valid square."""
    return 0 <= file < 8 and 0 <= rank < 8


def square_name(square: int) -> str:
    """Return the algebraic name of the square, e.g. 'e4'."""
    return "abcdefgh"[file_of(square)] + "12345678"[rank_of(square)]


def parse_square(name: str) -> int:
    """Parse an algebraic square name like 'e4' into a square index."""
    if len(name) != 2 or name[0] not in "abcdefgh" or name[1] not in "12345678":
        raise ValueError(f"Invalid square name: {name!r}")
    return sq("abcdefgh".index(name[0]), "12345678".index(name[1]))


# Knight offset list: (file_delta, rank_delta) for all 8 L-shaped jumps.
KNIGHT_OFFSETS: list[tuple[int, int]] = [
    (1, 2), (2, 1), (2, -1), (1, -2),
    (-1, -2), (-2, -1), (-2, 1), (-1, 2),
]

# King offset list: 8 adjacent squares.
KING_OFFSETS: list[tuple[int, int]] = [
    (1, 0), (1, 1), (0, 1), (-1, 1),
    (-1, 0), (-1, -1), (0, -1), (1, -1),
]

# Sliding-piece direction vectors.
BISHOP_DIRECTIONS: list[tuple[int, int]] = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
ROOK_DIRECTIONS: list[tuple[int, int]] = [(1, 0), (-1, 0), (0, 1), (0, -1)]
QUEEN_DIRECTIONS: list[tuple[int, int]] = BISHOP_DIRECTIONS + ROOK_DIRECTIONS
