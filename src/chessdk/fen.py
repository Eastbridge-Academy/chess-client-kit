"""FEN (Forsyth-Edwards Notation) parser and serializer.

A FEN string has six space-separated fields:

    <board> <side> <castling> <ep> <halfmove> <fullmove>

The board field lists ranks 8 down to 1 separated by slashes; digits denote
runs of empty squares; piece letters are case-sensitive (uppercase = white).
The remaining fields encode side to move ('w' or 'b'), castling rights (any
subset of 'KQkq' or '-'), the en passant target square (e.g. 'e3' or '-'), the
halfmove clock, and the fullmove number.

Parsed FENs are returned as a `BoardState` dataclass that holds raw data; the
Board class wraps this and implements move logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from chessdk.squares import parse_square, sq, square_name
from chessdk.types import BLACK, Color, Piece, WHITE

STARTING_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"


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


@dataclass
class BoardState:
    """Raw, mutable board state parsed from a FEN string."""

    pieces: list[Piece | None] = field(default_factory=lambda: [None] * 64)
    side_to_move: Color = WHITE
    castling: CastlingRights = field(default_factory=CastlingRights)
    en_passant: int | None = None
    halfmove_clock: int = 0
    fullmove_number: int = 1


def parse_fen(fen: str) -> BoardState:
    """Parse a FEN string into a BoardState. Raises ValueError on bad input."""
    parts = fen.strip().split()
    if len(parts) != 6:
        raise ValueError(f"FEN must have 6 fields, got {len(parts)}: {fen!r}")

    board_field, side_field, castling_field, ep_field, half_field, full_field = parts

    state = BoardState()

    # Board placement
    ranks = board_field.split("/")
    if len(ranks) != 8:
        raise ValueError(f"FEN board must have 8 ranks, got {len(ranks)}")
    for row_index, rank_str in enumerate(ranks):
        rank = 7 - row_index  # FEN lists rank 8 first
        file = 0
        for ch in rank_str:
            if ch.isdigit():
                file += int(ch)
            else:
                if file >= 8:
                    raise ValueError(f"FEN rank too long: {rank_str!r}")
                state.pieces[sq(file, rank)] = Piece.from_char(ch)
                file += 1
        if file != 8:
            raise ValueError(f"FEN rank not 8 files wide: {rank_str!r}")

    # Side to move
    if side_field == "w":
        state.side_to_move = WHITE
    elif side_field == "b":
        state.side_to_move = BLACK
    else:
        raise ValueError(f"FEN side-to-move must be 'w' or 'b', got {side_field!r}")

    # Castling rights
    if castling_field != "-":
        for ch in castling_field:
            if ch == "K":
                state.castling.white_kingside = True
            elif ch == "Q":
                state.castling.white_queenside = True
            elif ch == "k":
                state.castling.black_kingside = True
            elif ch == "q":
                state.castling.black_queenside = True
            else:
                raise ValueError(f"Unknown castling character: {ch!r}")

    # En passant
    if ep_field != "-":
        state.en_passant = parse_square(ep_field)

    # Halfmove and fullmove
    state.halfmove_clock = int(half_field)
    state.fullmove_number = int(full_field)

    return state


def to_fen(state: BoardState) -> str:
    """Serialize a BoardState back into a FEN string."""
    rank_strs = []
    for row_index in range(8):
        rank = 7 - row_index
        row = ""
        empty = 0
        for file in range(8):
            piece = state.pieces[sq(file, rank)]
            if piece is None:
                empty += 1
            else:
                if empty:
                    row += str(empty)
                    empty = 0
                row += piece.char
        if empty:
            row += str(empty)
        rank_strs.append(row)

    side = "w" if state.side_to_move is WHITE else "b"
    ep = square_name(state.en_passant) if state.en_passant is not None else "-"
    return (
        f"{'/'.join(rank_strs)} {side} {state.castling} {ep} "
        f"{state.halfmove_clock} {state.fullmove_number}"
    )
