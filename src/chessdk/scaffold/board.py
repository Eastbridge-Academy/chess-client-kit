"""Your Board class.

This file lives in your own working directory after `chess-cli init`. Edit it
freely. Tests (`chess-cli test`) import `Board` from this file; the UCI
wrapper in later weeks will import your `choose_move` from `bot.py`, which
will in turn use this `Board`.

Square layout: indices 0..63, with 0 = a1 and 63 = h8. See
`chessdk.squares` for helpers (`sq(file, rank)`, `file_of(sq)`, etc.) and
offset constants (`KNIGHT_OFFSETS`, `BISHOP_DIRECTIONS`, etc.).
"""

from __future__ import annotations

from typing import Iterator

from chessdk import (
    BISHOP,
    BISHOP_DIRECTIONS,
    BLACK,
    Color,
    KING,
    KING_OFFSETS,
    KNIGHT,
    KNIGHT_OFFSETS,
    Kind,
    Move,
    MoveRecord,
    PAWN,
    Piece,
    QUEEN,
    QUEEN_DIRECTIONS,
    ROOK,
    ROOK_DIRECTIONS,
    WHITE,
    file_of,
    on_board,
    opposite,
    rank_of,
    sq,
)
from chessdk.base import BaseBoard
from chessdk.fen import BoardState


class Board(BaseBoard):
    """A chess board with move generation. You implement the methods below."""

    def __init__(self, state: BoardState | None = None):
        super().__init__(state)
        self._history: list[MoveRecord] = []

    # === Stage 1: Squares and Pieces ===

    def piece_at(self, square: int) -> Piece | None:
        """Return the Piece on the given square, or None if empty."""
        raise NotImplementedError("implement Stage 1 (Squares and Pieces)")

    def pieces_of(self, color: Color) -> Iterator[tuple[int, Piece]]:
        """Yield (square, piece) pairs for every piece of the given color."""
        raise NotImplementedError("implement Stage 1 (Squares and Pieces)")

    # === Stage 2: Leapers ===

    def _knight_moves(self, color: Color) -> list[Move]:
        """Pseudo-legal knight moves for `color`."""
        raise NotImplementedError("implement Stage 2 (knight)")

    def _king_moves(self, color: Color) -> list[Move]:
        """Pseudo-legal king moves for `color`.

        Includes castling once Week 2 Stage 3 is in (kingside and queenside,
        with all four conditions checked).
        """
        raise NotImplementedError("implement Stage 2 (king); extend in Week 2 Stage 3")

    # === Stage 3: Sliders ===

    def _bishop_moves(self, color: Color) -> list[Move]:
        """Pseudo-legal bishop moves for `color`."""
        raise NotImplementedError("implement Stage 3 (bishop)")

    def _rook_moves(self, color: Color) -> list[Move]:
        """Pseudo-legal rook moves for `color`."""
        raise NotImplementedError("implement Stage 3 (rook)")

    def _queen_moves(self, color: Color) -> list[Move]:
        """Pseudo-legal queen moves for `color`."""
        raise NotImplementedError("implement Stage 3 (queen)")

    # === Stage 4: Pawns ===

    def _pawn_moves(self, color: Color) -> list[Move]:
        """Pseudo-legal pawn moves for `color`.

        Week 1: single push, double push, diagonal captures.
        Week 2 Stage 4: also generate promotion moves (one Move per promotion
        kind) and en passant captures.
        """
        raise NotImplementedError("implement Stage 4 (pawn); extend in Week 2 Stage 4")

    # === Wiring ===

    def pseudo_legal_moves(self) -> list[Move]:
        """All pseudo-legal moves for the side to move."""
        raise NotImplementedError("implement Stage 4 (combine all piece moves)")

    # === Week 2 Stage 1: Make and Unmake ===

    def make_move(self, move: Move) -> None:
        """Apply `move` in place. Push a MoveRecord onto self._history.

        Handles quiet moves and ordinary captures in Stage 1; extended for
        castling (Stage 3), promotion and en passant (Stage 4).
        """
        raise NotImplementedError("implement Week 2 Stage 1 (Make and Unmake)")

    def undo_move(self) -> None:
        """Reverse the last make_move call by popping self._history."""
        raise NotImplementedError("implement Week 2 Stage 1 (Make and Unmake)")

    # === Week 2 Stage 2: Attacks and Legality ===

    def is_attacked(self, square: int, by_color: Color) -> bool:
        """True if any piece of `by_color` attacks `square`."""
        raise NotImplementedError("implement Week 2 Stage 2 (Attacks and Legality)")

    def is_in_check(self, color: Color | None = None) -> bool:
        """True if `color` (default: side to move) is in check."""
        raise NotImplementedError("implement Week 2 Stage 2 (Attacks and Legality)")

    def legal_moves(self) -> list[Move]:
        """Pseudo-legal moves filtered to those that don't leave own king in check."""
        raise NotImplementedError("implement Week 2 Stage 2 (Attacks and Legality)")
