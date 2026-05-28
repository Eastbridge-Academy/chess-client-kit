"""Evaluation primitives: piece values, piece-square tables, and a reference
``evaluate(board)`` function.

This module is the library-side companion to the student's
``evaluation.py`` (introduced in Phase 4). It ships the canonical constants
students may import as starting points (and tune freely), and a reference
implementation used by the kit's tests, the perft tooling, and the Phase 4
house bots.

Phase 3's smaller helpers (``PIECE_VALUE`` and ``min_attacker_value``) are
preserved unchanged so existing Phase 3 bots that import them keep working.
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
    BLACK,
    Color,
    KING,
    Kind,
    KNIGHT,
    PAWN,
    QUEEN,
    ROOK,
    WHITE,
)


# ---------------------------------------------------------------------------
# Mate scoring
# ---------------------------------------------------------------------------

# A score so large that it dominates any combination of normal evaluation
# terms; used for checkmate. Phase 5's search code adjusts this by the
# distance from the root so that shorter mates score higher, but for a
# static evaluator (Phase 4) the raw constant is what gets returned.
MATE_SCORE: int = 1_000_000


# ---------------------------------------------------------------------------
# Material
# ---------------------------------------------------------------------------

# Classic Shannon / textbook material values, normalized so that a pawn is
# worth 100 centipawns. The king is given a sentinel value large enough to
# dominate any other combination but small enough not to overflow simple
# integer arithmetic.
PIECE_VALUE_CLASSIC: dict[Kind, int] = {
    PAWN: 100,
    KNIGHT: 300,
    BISHOP: 300,
    ROOK: 500,
    QUEEN: 900,
    KING: 20000,
}

# Larry Kaufman's empirically tuned values from his 2012 paper on material
# imbalances. The bishop edges past the knight; the queen sits slightly
# below the textbook 2R+P. These are the numbers Stockfish's classical
# evaluator was tuned around for many years.
PIECE_VALUE_KAUFMAN: dict[Kind, int] = {
    PAWN: 100,
    KNIGHT: 325,
    BISHOP: 325,
    ROOK: 500,
    QUEEN: 975,
    KING: 20000,
}

# Default values for backward compatibility with Phase 3 code, which
# imported ``PIECE_VALUE`` directly. New code (Phase 4 onward) should
# pick a named variant explicitly.
PIECE_VALUE: dict[Kind, int] = PIECE_VALUE_CLASSIC


# ---------------------------------------------------------------------------
# Piece-square tables
# ---------------------------------------------------------------------------
#
# Each PST is a 64-entry tuple indexed by ``sq(file, rank)`` (so PST[0] is
# a1, PST[63] is h8). The values below describe White's perspective; for a
# Black piece on square s, look up the table at ``sq(file_of(s), 7 - rank_of(s))``.
#
# The values come from Tomasz Michniewski's Simplified Evaluation Function
# on the Chess Programming Wiki, which has been a widely-used hand-tuned
# starting point since the early 2000s. They are deliberately modest in
# magnitude (the largest non-zero entry is the pawn rank-7 bonus of +50)
# so that material remains the dominant term.


def _pst(*ranks: tuple[int, ...]) -> tuple[int, ...]:
    """Build a 64-entry PST from 8 row tuples written rank 8 down to rank 1.

    Writing the table top-down matches how a chess board is normally drawn,
    so the source for each PST reads like a heat map. The helper transforms
    the visual layout into a flat tuple indexed by ``sq(file, rank)``.
    """
    if len(ranks) != 8 or any(len(row) != 8 for row in ranks):
        raise ValueError("PST needs 8 rows of 8")
    out = [0] * 64
    for visual_row, row in enumerate(ranks):
        rank = 7 - visual_row
        for file, value in enumerate(row):
            out[sq(file, rank)] = value
    return tuple(out)


PAWN_PST: tuple[int, ...] = _pst(
    ( 0,  0,  0,  0,  0,  0,  0,  0),   # rank 8
    (50, 50, 50, 50, 50, 50, 50, 50),   # rank 7
    (10, 10, 20, 30, 30, 20, 10, 10),   # rank 6
    ( 5,  5, 10, 25, 25, 10,  5,  5),   # rank 5
    ( 0,  0,  0, 20, 20,  0,  0,  0),   # rank 4
    ( 5, -5,-10,  0,  0,-10, -5,  5),   # rank 3
    ( 5, 10, 10,-20,-20, 10, 10,  5),   # rank 2
    ( 0,  0,  0,  0,  0,  0,  0,  0),   # rank 1
)

KNIGHT_PST: tuple[int, ...] = _pst(
    (-50,-40,-30,-30,-30,-30,-40,-50),
    (-40,-20,  0,  0,  0,  0,-20,-40),
    (-30,  0, 10, 15, 15, 10,  0,-30),
    (-30,  5, 15, 20, 20, 15,  5,-30),
    (-30,  0, 15, 20, 20, 15,  0,-30),
    (-30,  5, 10, 15, 15, 10,  5,-30),
    (-40,-20,  0,  5,  5,  0,-20,-40),
    (-50,-40,-30,-30,-30,-30,-40,-50),
)

BISHOP_PST: tuple[int, ...] = _pst(
    (-20,-10,-10,-10,-10,-10,-10,-20),
    (-10,  0,  0,  0,  0,  0,  0,-10),
    (-10,  0,  5, 10, 10,  5,  0,-10),
    (-10,  5,  5, 10, 10,  5,  5,-10),
    (-10,  0, 10, 10, 10, 10,  0,-10),
    (-10, 10, 10, 10, 10, 10, 10,-10),
    (-10,  5,  0,  0,  0,  0,  5,-10),
    (-20,-10,-10,-10,-10,-10,-10,-20),
)

ROOK_PST: tuple[int, ...] = _pst(
    ( 0,  0,  0,  0,  0,  0,  0,  0),
    ( 5, 10, 10, 10, 10, 10, 10,  5),
    (-5,  0,  0,  0,  0,  0,  0, -5),
    (-5,  0,  0,  0,  0,  0,  0, -5),
    (-5,  0,  0,  0,  0,  0,  0, -5),
    (-5,  0,  0,  0,  0,  0,  0, -5),
    (-5,  0,  0,  0,  0,  0,  0, -5),
    ( 0,  0,  0,  5,  5,  0,  0,  0),
)

QUEEN_PST: tuple[int, ...] = _pst(
    (-20,-10,-10, -5, -5,-10,-10,-20),
    (-10,  0,  0,  0,  0,  0,  0,-10),
    (-10,  0,  5,  5,  5,  5,  0,-10),
    ( -5,  0,  5,  5,  5,  5,  0, -5),
    (  0,  0,  5,  5,  5,  5,  0, -5),
    (-10,  5,  5,  5,  5,  5,  0,-10),
    (-10,  0,  5,  0,  0,  0,  0,-10),
    (-20,-10,-10, -5, -5,-10,-10,-20),
)

KING_PST: tuple[int, ...] = _pst(
    (-30,-40,-40,-50,-50,-40,-40,-30),
    (-30,-40,-40,-50,-50,-40,-40,-30),
    (-30,-40,-40,-50,-50,-40,-40,-30),
    (-30,-40,-40,-50,-50,-40,-40,-30),
    (-20,-30,-30,-40,-40,-30,-30,-20),
    (-10,-20,-20,-20,-20,-20,-20,-10),
    ( 20, 20,  0,  0,  0,  0, 20, 20),
    ( 20, 30, 10,  0,  0, 10, 30, 20),
)

DEFAULT_PSTS: dict[Kind, tuple[int, ...]] = {
    PAWN: PAWN_PST,
    KNIGHT: KNIGHT_PST,
    BISHOP: BISHOP_PST,
    ROOK: ROOK_PST,
    QUEEN: QUEEN_PST,
    KING: KING_PST,
}


def pst_square(piece_kind: Kind, color: Color, square: int) -> int:
    """Look up a PST entry, mirroring the rank for Black pieces."""
    table = DEFAULT_PSTS[piece_kind]
    if color == WHITE:
        return table[square]
    return table[sq(file_of(square), 7 - rank_of(square))]


# ---------------------------------------------------------------------------
# Mobility
# ---------------------------------------------------------------------------

DEFAULT_MOBILITY_WEIGHT: int = 2


def _legal_moves_for(board, color: Color) -> list:
    """Return ``board.legal_moves()`` as if it were ``color``'s turn.

    The student-facing Board exposes ``legal_moves()`` only for the side to
    move, so for an evaluator that wants to score both sides' mobility we
    temporarily flip ``side_to_move``, call the existing generator, and
    restore it. The board ends up in exactly the state it started in.
    """
    original = board.state.side_to_move
    board.state.side_to_move = color
    try:
        return board.legal_moves()
    finally:
        board.state.side_to_move = original


# ---------------------------------------------------------------------------
# Reference evaluate()
# ---------------------------------------------------------------------------


def evaluate(board) -> int:
    """Static evaluation from White's point of view, in centipawns.

    Sums material (Classic values), the default PSTs, and a small mobility
    term, with terminal-position handling at the front: a side that has no
    legal moves and is in check is checkmated, and one with no legal moves
    that isn't in check is stalemated.

    Used by the kit's own tests and by the Phase 4 model solution. Students
    write their own ``evaluate`` in their working directory; this version
    is here as a reference and as something the house bots can compose.
    """
    legal = board.legal_moves()
    if not legal:
        if board.is_in_check():
            return -MATE_SCORE if board.side_to_move == WHITE else MATE_SCORE
        return 0

    score = 0
    for s, piece in enumerate(board.pieces):
        if piece is None:
            continue
        sign = 1 if piece.color == WHITE else -1
        score += sign * PIECE_VALUE_CLASSIC[piece.kind]
        score += sign * pst_square(piece.kind, piece.color, s)

    # Mobility: count both sides' legal moves. The side to move's count is
    # already in `legal`; for the other side we use the state-swap helper.
    other = BLACK if board.side_to_move == WHITE else WHITE
    side_count = len(legal)
    other_count = len(_legal_moves_for(board, other))
    if board.side_to_move == WHITE:
        white_count, black_count = side_count, other_count
    else:
        white_count, black_count = other_count, side_count
    score += DEFAULT_MOBILITY_WEIGHT * (white_count - black_count)

    return score


# ---------------------------------------------------------------------------
# Phase 3 helper preserved for backward compatibility
# ---------------------------------------------------------------------------


def min_attacker_value(board, square: int, by_color: Color) -> int | None:
    """Value of the cheapest piece of ``by_color`` attacking ``square``, else None.

    The result is a single number (e.g. 100 for a pawn attacker, 900 for a
    queen) rather than a piece kind, because the only thing students do
    with it is compare against ``PIECE_VALUE[my_kind]``: if the cheapest
    attacker is worth less than your moving piece, the move hangs material.
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
