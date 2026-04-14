"""Reference Board implementation.

Mirrors the student-facing Board in `scaffold/board.py`, but with all Week 1
methods filled in. Used for developing the test suite and for the `perft`
command's divide-mode comparison.

Not imported by students directly.
"""

from __future__ import annotations

from typing import Iterator

from chessdk.base import BaseBoard
from chessdk.squares import (
    BISHOP_DIRECTIONS,
    KING_OFFSETS,
    KNIGHT_OFFSETS,
    QUEEN_DIRECTIONS,
    ROOK_DIRECTIONS,
    file_of,
    on_board,
    rank_of,
    sq,
)
from chessdk.types import (
    BISHOP,
    BLACK,
    Color,
    Kind,
    KING,
    KNIGHT,
    Move,
    PAWN,
    Piece,
    QUEEN,
    ROOK,
    WHITE,
)


class Board(BaseBoard):
    # --- Stage 1 ---

    def piece_at(self, square: int) -> Piece | None:
        return self.pieces[square]

    def pieces_of(self, color: Color) -> Iterator[tuple[int, Piece]]:
        for s, piece in enumerate(self.pieces):
            if piece is not None and piece.color == color:
                yield s, piece

    # --- Stage 2: leapers ---

    def _knight_moves(self, color: Color) -> list[Move]:
        return list(self._leaper_moves(color, KNIGHT, KNIGHT_OFFSETS))

    def _king_moves(self, color: Color) -> list[Move]:
        return list(self._leaper_moves(color, KING, KING_OFFSETS))

    def _leaper_moves(
        self, color: Color, piece_kind: Kind, offsets: list[tuple[int, int]]
    ) -> Iterator[Move]:
        for from_sq, piece in self.pieces_of(color):
            if piece.kind != piece_kind:
                continue
            f, r = file_of(from_sq), rank_of(from_sq)
            for df, dr in offsets:
                nf, nr = f + df, r + dr
                if not on_board(nf, nr):
                    continue
                target_sq = sq(nf, nr)
                target = self.pieces[target_sq]
                if target is None or target.color != color:
                    yield Move(from_sq, target_sq)

    # --- Stage 3: sliders ---

    def _bishop_moves(self, color: Color) -> list[Move]:
        return self._slide_moves(color, BISHOP, BISHOP_DIRECTIONS)

    def _rook_moves(self, color: Color) -> list[Move]:
        return self._slide_moves(color, ROOK, ROOK_DIRECTIONS)

    def _queen_moves(self, color: Color) -> list[Move]:
        return self._slide_moves(color, QUEEN, QUEEN_DIRECTIONS)

    def _slide_moves(
        self,
        color: Color,
        piece_kind: Kind,
        directions: list[tuple[int, int]],
    ) -> list[Move]:
        moves: list[Move] = []
        for from_sq, piece in self.pieces_of(color):
            if piece.kind != piece_kind:
                continue
            f, r = file_of(from_sq), rank_of(from_sq)
            for df, dr in directions:
                nf, nr = f + df, r + dr
                while on_board(nf, nr):
                    target_sq = sq(nf, nr)
                    target = self.pieces[target_sq]
                    if target is None:
                        moves.append(Move(from_sq, target_sq))
                    else:
                        if target.color != color:
                            moves.append(Move(from_sq, target_sq))
                        break
                    nf += df
                    nr += dr
        return moves

    # --- Stage 4: pawns ---

    def _pawn_moves(self, color: Color) -> list[Move]:
        moves: list[Move] = []
        direction = 1 if color == WHITE else -1
        start_rank = 1 if color == WHITE else 6
        for from_sq, piece in self.pieces_of(color):
            if piece.kind != PAWN:
                continue
            f, r = file_of(from_sq), rank_of(from_sq)
            # Single push
            nr = r + direction
            if on_board(f, nr):
                target_sq = sq(f, nr)
                if self.pieces[target_sq] is None:
                    moves.append(Move(from_sq, target_sq))
                    # Double push (only if single push was legal, square is empty)
                    if r == start_rank:
                        nr2 = r + 2 * direction
                        target2 = sq(f, nr2)
                        if self.pieces[target2] is None:
                            moves.append(Move(from_sq, target2))
            # Captures
            for df in (-1, 1):
                nf = f + df
                if on_board(nf, nr):
                    target_sq = sq(nf, nr)
                    target = self.pieces[target_sq]
                    if target is not None and target.color != color:
                        moves.append(Move(from_sq, target_sq))
        return moves

    # --- Wiring ---

    def pseudo_legal_moves(self) -> list[Move]:
        color = self.side_to_move
        return (
            self._knight_moves(color)
            + self._king_moves(color)
            + self._bishop_moves(color)
            + self._rook_moves(color)
            + self._queen_moves(color)
            + self._pawn_moves(color)
        )
