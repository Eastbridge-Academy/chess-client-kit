"""BaseBoard: state + FEN loading, independent of move generation.

Subclasses (student `Board` in `scaffold/board.py`, and `reference.Board` in
this package) inherit from BaseBoard and add move generation on top.
"""

from __future__ import annotations

from typing import Iterator

from chessdk.fen import BoardState, STARTING_FEN, parse_fen, to_fen
from chessdk.types import Color, Piece


class BaseBoard:
    """Holds the piece array, side-to-move, castling rights, en passant, and clocks.

    Students don't modify this class. They subclass it in their own `board.py`
    and implement move generation.
    """

    def __init__(self, state: BoardState | None = None):
        self.state = state if state is not None else parse_fen(STARTING_FEN)

    @classmethod
    def from_fen(cls, fen: str) -> "BaseBoard":
        return cls(parse_fen(fen))

    def to_fen(self) -> str:
        return to_fen(self.state)

    # --- Convenience accessors into the state.

    @property
    def pieces(self) -> list[Piece | None]:
        return self.state.pieces

    @property
    def side_to_move(self) -> Color:
        return self.state.side_to_move

    @property
    def en_passant(self) -> int | None:
        return self.state.en_passant

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.to_fen()!r})"
