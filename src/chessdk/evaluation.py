"""Tiny shared helpers for bot evaluation.

The kit ships these so that students writing simple bots in Week 3 can talk
about ``hanging pieces'' and ``which captures are good'' without first
implementing a per-piece-kind attack enumerator. Stronger weeks will replace
or extend these.
"""

from __future__ import annotations

from chessdk.squares import (
    BISHOP_DIRECTIONS,
    KING_OFFSETS,
    KNIGHT_OFFSETS,
    ROOK_DIRECTIONS,
    file_of,
    rank_of,
    sq,
)
from chessdk.types import (
    BISHOP,
    Color,
    KING,
    KNIGHT,
    PAWN,
    QUEEN,
    ROOK,
    WHITE,
)


PIECE_VALUE: dict = {
    PAWN: 100,
    KNIGHT: 320,
    BISHOP: 330,
    ROOK: 500,
    QUEEN: 900,
    KING: 20000,
}


def min_attacker_value(board, square: int, by_color: Color) -> int | None:
    """Value of the cheapest piece of `by_color` attacking `square`, else None.

    The result is a single number (e.g. 100 for a pawn attacker, 900 for a
    queen) rather than a piece kind, because the only thing students do with
    it is compare against ``PIECE_VALUE[my_kind]'': if the cheapest attacker
    is worth less than your moving piece, the move hangs material.
    """
    cheapest: int | None = None

    def take(value: int) -> None:
        nonlocal cheapest
        if cheapest is None or value < cheapest:
            cheapest = value

    f, r = file_of(square), rank_of(square)

    # Pawn: a `by_color` pawn one rank "behind" `square` (relative to its
    # direction of motion) attacks `square` on its diagonals.
    pawn_rank = r - 1 if by_color == WHITE else r + 1
    if 0 <= pawn_rank < 8:
        for df in (-1, 1):
            nf = f + df
            if 0 <= nf < 8:
                p = board.piece_at(sq(nf, pawn_rank))
                if p is not None and p.color == by_color and p.kind == PAWN:
                    take(PIECE_VALUE[PAWN])

    # Knight
    for df, dr in KNIGHT_OFFSETS:
        nf, nr = f + df, r + dr
        if 0 <= nf < 8 and 0 <= nr < 8:
            p = board.piece_at(sq(nf, nr))
            if p is not None and p.color == by_color and p.kind == KNIGHT:
                take(PIECE_VALUE[KNIGHT])
                break

    # Bishop or queen along diagonals
    for df, dr in BISHOP_DIRECTIONS:
        nf, nr = f + df, r + dr
        while 0 <= nf < 8 and 0 <= nr < 8:
            p = board.piece_at(sq(nf, nr))
            if p is not None:
                if p.color == by_color:
                    if p.kind == BISHOP:
                        take(PIECE_VALUE[BISHOP])
                    elif p.kind == QUEEN:
                        take(PIECE_VALUE[QUEEN])
                break
            nf += df
            nr += dr

    # Rook or queen along ranks/files
    for df, dr in ROOK_DIRECTIONS:
        nf, nr = f + df, r + dr
        while 0 <= nf < 8 and 0 <= nr < 8:
            p = board.piece_at(sq(nf, nr))
            if p is not None:
                if p.color == by_color:
                    if p.kind == ROOK:
                        take(PIECE_VALUE[ROOK])
                    elif p.kind == QUEEN:
                        take(PIECE_VALUE[QUEEN])
                break
            nf += df
            nr += dr

    # Adjacent king
    for df, dr in KING_OFFSETS:
        nf, nr = f + df, r + dr
        if 0 <= nf < 8 and 0 <= nr < 8:
            p = board.piece_at(sq(nf, nr))
            if p is not None and p.color == by_color and p.kind == KING:
                take(PIECE_VALUE[KING])

    return cheapest
