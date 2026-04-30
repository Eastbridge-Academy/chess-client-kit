"""Primitive types: Color, Kind, Piece, Move.

These are shared across the library and the student's code. Students import
them from `chessdk` directly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum


class Color(IntEnum):
    WHITE = 0
    BLACK = 1

    @property
    def other(self) -> "Color":
        return Color.BLACK if self is Color.WHITE else Color.WHITE


WHITE = Color.WHITE
BLACK = Color.BLACK


class Kind(IntEnum):
    PAWN = 0
    KNIGHT = 1
    BISHOP = 2
    ROOK = 3
    QUEEN = 4
    KING = 5


PAWN = Kind.PAWN
KNIGHT = Kind.KNIGHT
BISHOP = Kind.BISHOP
ROOK = Kind.ROOK
QUEEN = Kind.QUEEN
KING = Kind.KING


_PIECE_CHARS = {
    (PAWN, WHITE): "P",
    (KNIGHT, WHITE): "N",
    (BISHOP, WHITE): "B",
    (ROOK, WHITE): "R",
    (QUEEN, WHITE): "Q",
    (KING, WHITE): "K",
    (PAWN, BLACK): "p",
    (KNIGHT, BLACK): "n",
    (BISHOP, BLACK): "b",
    (ROOK, BLACK): "r",
    (QUEEN, BLACK): "q",
    (KING, BLACK): "k",
}
_CHAR_TO_PIECE = {v: k for k, v in _PIECE_CHARS.items()}


@dataclass(frozen=True)
class Piece:
    kind: Kind
    color: Color

    @property
    def char(self) -> str:
        return _PIECE_CHARS[(self.kind, self.color)]

    @classmethod
    def from_char(cls, c: str) -> "Piece":
        kind, color = _CHAR_TO_PIECE[c]
        return cls(kind, color)

    def __repr__(self) -> str:
        return f"Piece({self.char})"


@dataclass
class CastlingRights:
    white_kingside: bool = False
    white_queenside: bool = False
    black_kingside: bool = False
    black_queenside: bool = False

    def __str__(self) -> str:
        s = ""
        if self.white_kingside:
            s += "K"
        if self.white_queenside:
            s += "Q"
        if self.black_kingside:
            s += "k"
        if self.black_queenside:
            s += "q"
        return s or "-"

    def copy(self) -> "CastlingRights":
        return CastlingRights(
            self.white_kingside,
            self.white_queenside,
            self.black_kingside,
            self.black_queenside,
        )


@dataclass(frozen=True)
class Move:
    """A chess move.

    `from_sq` and `to_sq` are square indices 0..63. `promotion` is the piece
    kind to promote to (one of KNIGHT, BISHOP, ROOK, QUEEN), or None for a
    non-promotion move. Castling and en passant are not flagged on the Move;
    they are inferred from the move's shape and the board state by make_move.
    """

    from_sq: int
    to_sq: int
    promotion: Kind | None = None

    def uci(self) -> str:
        """Return the UCI string representation, e.g. 'e2e4' or 'e7e8q'."""
        from chessdk.squares import square_name

        s = square_name(self.from_sq) + square_name(self.to_sq)
        if self.promotion is not None:
            s += _PIECE_CHARS[(self.promotion, BLACK)]  # promotion char is lowercase
        return s

    def __repr__(self) -> str:
        return f"Move({self.uci()})"


def opposite(color: Color) -> Color:
    """Return the other color."""
    return BLACK if color == WHITE else WHITE


@dataclass
class MoveRecord:
    """Information needed to undo a move.

    `make_move` constructs one of these from the pre-move state and pushes it
    onto Board._history; `undo_move` pops it and uses the fields to revert.
    Students don't pass MoveRecord through the public API; it lives entirely
    inside the Board.
    """

    move: Move
    captured: Piece | None          # piece that vanished, if any
    captured_square: int            # where it sat (= move.to_sq except en passant)
    prev_castling: CastlingRights
    prev_en_passant: int | None
    prev_halfmove: int
