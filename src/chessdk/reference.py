"""Reference Board implementation.

Mirrors the student-facing Board in `scaffold/board.py`, but with all methods
filled in. Used for developing the test suite, for the `perft` command's
divide-mode comparison, and as the implementation of `chess-cli` perft itself.

Not imported by students directly.
"""

from __future__ import annotations

from typing import Iterator

from chessdk.base import BaseBoard
from chessdk.fen import BoardState
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
    CastlingRights,
    Color,
    Kind,
    KING,
    KNIGHT,
    Move,
    MoveRecord,
    PAWN,
    Piece,
    QUEEN,
    ROOK,
    WHITE,
    opposite,
)


# Corner squares (used for castling-rights bookkeeping when a rook moves
# from or is captured on its starting corner).
A1 = sq(0, 0)
H1 = sq(7, 0)
A8 = sq(0, 7)
H8 = sq(7, 7)


class Board(BaseBoard):
    def __init__(self, state: BoardState | None = None):
        super().__init__(state)
        self._history: list[MoveRecord] = []

    # === Stage 1: Squares and Pieces ===

    def piece_at(self, square: int) -> Piece | None:
        return self.pieces[square]

    def pieces_of(self, color: Color) -> Iterator[tuple[int, Piece]]:
        for s, piece in enumerate(self.pieces):
            if piece is not None and piece.color == color:
                yield s, piece

    # === Stage 2: Leapers ===

    def _knight_moves(self, color: Color) -> list[Move]:
        return list(self._leaper_moves(color, KNIGHT, KNIGHT_OFFSETS))

    def _king_moves(self, color: Color) -> list[Move]:
        moves = list(self._leaper_moves(color, KING, KING_OFFSETS))
        moves.extend(self._castling_moves(color))
        return moves

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

    # === Stage 3: Sliders ===

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

    # === Stage 4: Pawns (with Stage 8 promotion and en passant) ===

    def _pawn_moves(self, color: Color) -> list[Move]:
        moves: list[Move] = []
        direction = 1 if color == WHITE else -1
        start_rank = 1 if color == WHITE else 6
        promo_rank = 7 if color == WHITE else 0
        for from_sq, piece in self.pieces_of(color):
            if piece.kind != PAWN:
                continue
            f, r = file_of(from_sq), rank_of(from_sq)
            nr = r + direction
            # Single push
            if on_board(f, nr):
                target_sq = sq(f, nr)
                if self.pieces[target_sq] is None:
                    if nr == promo_rank:
                        for kind in (KNIGHT, BISHOP, ROOK, QUEEN):
                            moves.append(Move(from_sq, target_sq, promotion=kind))
                    else:
                        moves.append(Move(from_sq, target_sq))
                    # Double push
                    if r == start_rank:
                        nr2 = r + 2 * direction
                        target2 = sq(f, nr2)
                        if self.pieces[target2] is None:
                            moves.append(Move(from_sq, target2))
            # Diagonal captures and en passant
            for df in (-1, 1):
                nf = f + df
                if not on_board(nf, nr):
                    continue
                target_sq = sq(nf, nr)
                target = self.pieces[target_sq]
                if target is not None and target.color != color:
                    if nr == promo_rank:
                        for kind in (KNIGHT, BISHOP, ROOK, QUEEN):
                            moves.append(Move(from_sq, target_sq, promotion=kind))
                    else:
                        moves.append(Move(from_sq, target_sq))
                elif target is None and target_sq == self.state.en_passant:
                    moves.append(Move(from_sq, target_sq))
        return moves

    # === Castling generation (Stage 7) ===

    def _castling_moves(self, color: Color) -> list[Move]:
        moves: list[Move] = []
        rights = self.state.castling
        if color == WHITE:
            king_sq = sq(4, 0)
            kingside = rights.white_kingside
            queenside = rights.white_queenside
            rank = 0
        else:
            king_sq = sq(4, 7)
            kingside = rights.black_kingside
            queenside = rights.black_queenside
            rank = 7

        king = self.pieces[king_sq]
        if king is None or king.kind != KING or king.color != color:
            return moves

        enemy = opposite(color)
        if self.is_attacked(king_sq, enemy):
            return moves  # can't castle out of check

        if kingside:
            f_sq, g_sq = sq(5, rank), sq(6, rank)
            if (
                self.pieces[f_sq] is None
                and self.pieces[g_sq] is None
                and not self.is_attacked(f_sq, enemy)
                and not self.is_attacked(g_sq, enemy)
            ):
                moves.append(Move(king_sq, g_sq))

        if queenside:
            b_sq, c_sq, d_sq = sq(1, rank), sq(2, rank), sq(3, rank)
            if (
                self.pieces[b_sq] is None
                and self.pieces[c_sq] is None
                and self.pieces[d_sq] is None
                and not self.is_attacked(c_sq, enemy)
                and not self.is_attacked(d_sq, enemy)
            ):
                moves.append(Move(king_sq, c_sq))

        return moves

    # === Wiring ===

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

    # === Stage 5: Make and Unmake ===

    def make_move(self, move: Move) -> None:
        piece = self.pieces[move.from_sq]
        assert piece is not None, f"no piece on {move.from_sq}"
        color = piece.color

        is_castle = (
            piece.kind == KING
            and abs(file_of(move.to_sq) - file_of(move.from_sq)) == 2
        )
        is_en_passant = (
            piece.kind == PAWN and move.to_sq == self.state.en_passant
        )
        is_double_push = (
            piece.kind == PAWN
            and abs(rank_of(move.to_sq) - rank_of(move.from_sq)) == 2
        )

        if is_en_passant:
            captured_square = sq(file_of(move.to_sq), rank_of(move.from_sq))
        else:
            captured_square = move.to_sq
        captured = self.pieces[captured_square]

        record = MoveRecord(
            move=move,
            captured=captured,
            captured_square=captured_square,
            prev_castling=self.state.castling.copy(),
            prev_en_passant=self.state.en_passant,
            prev_halfmove=self.state.halfmove_clock,
        )
        self._history.append(record)

        # Move the piece (en passant: also clear the captured pawn's square)
        if is_en_passant:
            self.pieces[captured_square] = None
        self.pieces[move.from_sq] = None
        if move.promotion is not None:
            self.pieces[move.to_sq] = Piece(move.promotion, color)
        else:
            self.pieces[move.to_sq] = piece

        # Castling: also move the rook
        if is_castle:
            rank = rank_of(move.to_sq)
            if file_of(move.to_sq) == 6:  # kingside, king on g-file
                rook_from, rook_to = sq(7, rank), sq(5, rank)
            else:  # queenside, king on c-file
                rook_from, rook_to = sq(0, rank), sq(3, rank)
            self.pieces[rook_to] = self.pieces[rook_from]
            self.pieces[rook_from] = None

        # Castling rights updates
        cr = self.state.castling
        if piece.kind == KING:
            if color == WHITE:
                cr.white_kingside = cr.white_queenside = False
            else:
                cr.black_kingside = cr.black_queenside = False
        elif piece.kind == ROOK:
            if move.from_sq == A1:
                cr.white_queenside = False
            elif move.from_sq == H1:
                cr.white_kingside = False
            elif move.from_sq == A8:
                cr.black_queenside = False
            elif move.from_sq == H8:
                cr.black_kingside = False
        # Capture on a starting corner clears the captured side's right
        if captured is not None and captured.kind == ROOK:
            if move.to_sq == A1:
                cr.white_queenside = False
            elif move.to_sq == H1:
                cr.white_kingside = False
            elif move.to_sq == A8:
                cr.black_queenside = False
            elif move.to_sq == H8:
                cr.black_kingside = False

        # En passant target
        if is_double_push:
            between = (rank_of(move.from_sq) + rank_of(move.to_sq)) // 2
            self.state.en_passant = sq(file_of(move.from_sq), between)
        else:
            self.state.en_passant = None

        # Halfmove clock
        if piece.kind == PAWN or captured is not None:
            self.state.halfmove_clock = 0
        else:
            self.state.halfmove_clock += 1

        # Fullmove number (ticks after Black moves)
        if color == BLACK:
            self.state.fullmove_number += 1

        # Side to move flips
        self.state.side_to_move = opposite(color)

    def undo_move(self) -> None:
        record = self._history.pop()
        move = record.move

        # Flip side back; the mover is now the new side_to_move
        mover = opposite(self.state.side_to_move)
        self.state.side_to_move = mover

        if mover == BLACK:
            self.state.fullmove_number -= 1

        self.state.castling = record.prev_castling
        self.state.en_passant = record.prev_en_passant
        self.state.halfmove_clock = record.prev_halfmove

        # The piece currently on to_sq is the moved piece (or promoted piece)
        moving_piece = self.pieces[move.to_sq]
        assert moving_piece is not None

        # Restore from_sq: a promotion came from a pawn
        if move.promotion is not None:
            self.pieces[move.from_sq] = Piece(PAWN, mover)
        else:
            self.pieces[move.from_sq] = moving_piece

        # Clear to_sq, then restore captured (if any) onto its real square
        self.pieces[move.to_sq] = None
        if record.captured is not None:
            self.pieces[record.captured_square] = record.captured

        # Castling: send the rook back to its corner
        if (
            moving_piece.kind == KING
            and abs(file_of(move.to_sq) - file_of(move.from_sq)) == 2
        ):
            rank = rank_of(move.to_sq)
            if file_of(move.to_sq) == 6:
                rook_from, rook_to = sq(7, rank), sq(5, rank)
            else:
                rook_from, rook_to = sq(0, rank), sq(3, rank)
            self.pieces[rook_from] = self.pieces[rook_to]
            self.pieces[rook_to] = None

    # === Stage 6: Attacks and Legality ===

    def is_attacked(self, square: int, by_color: Color) -> bool:
        f, r = file_of(square), rank_of(square)

        # Knights
        for df, dr in KNIGHT_OFFSETS:
            nf, nr = f + df, r + dr
            if on_board(nf, nr):
                p = self.pieces[sq(nf, nr)]
                if p is not None and p.color == by_color and p.kind == KNIGHT:
                    return True

        # Adjacent kings
        for df, dr in KING_OFFSETS:
            nf, nr = f + df, r + dr
            if on_board(nf, nr):
                p = self.pieces[sq(nf, nr)]
                if p is not None and p.color == by_color and p.kind == KING:
                    return True

        # Sliders along rook directions: rook or queen
        for df, dr in ROOK_DIRECTIONS:
            nf, nr = f + df, r + dr
            while on_board(nf, nr):
                p = self.pieces[sq(nf, nr)]
                if p is not None:
                    if p.color == by_color and p.kind in (ROOK, QUEEN):
                        return True
                    break
                nf += df
                nr += dr

        # Sliders along bishop directions: bishop or queen
        for df, dr in BISHOP_DIRECTIONS:
            nf, nr = f + df, r + dr
            while on_board(nf, nr):
                p = self.pieces[sq(nf, nr)]
                if p is not None:
                    if p.color == by_color and p.kind in (BISHOP, QUEEN):
                        return True
                    break
                nf += df
                nr += dr

        # Pawns: a by_color pawn on one of the diagonals "behind" `square`
        # (relative to by_color's direction of motion) attacks `square`.
        pawn_rank = r - 1 if by_color == WHITE else r + 1
        if 0 <= pawn_rank < 8:
            for df in (-1, 1):
                nf = f + df
                if 0 <= nf < 8:
                    p = self.pieces[sq(nf, pawn_rank)]
                    if p is not None and p.color == by_color and p.kind == PAWN:
                        return True

        return False

    def is_in_check(self, color: Color | None = None) -> bool:
        if color is None:
            color = self.side_to_move
        for s, piece in self.pieces_of(color):
            if piece.kind == KING:
                return self.is_attacked(s, opposite(color))
        return False

    def legal_moves(self) -> list[Move]:
        legal: list[Move] = []
        mover = self.side_to_move
        for move in self.pseudo_legal_moves():
            self.make_move(move)
            if not self.is_in_check(mover):
                legal.append(move)
            self.undo_move()
        return legal


def perft(board: Board, depth: int) -> int:
    """Count leaves in the legal-move tree at the given depth."""
    if depth == 0:
        return 1
    total = 0
    for move in board.legal_moves():
        board.make_move(move)
        total += perft(board, depth - 1)
        board.undo_move()
    return total
