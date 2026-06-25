"""Tapered evaluation tables: separate midgame and endgame values.

A piece is worth different things at different stages of the game. A king wants
to hide behind its pawns in the middlegame and march to the centre in the
endgame; a pawn is worth a little more once the queens are off and it is closer
to promoting. A *tapered* evaluation captures this by keeping two sets of
piece-square tables, one for the midgame and one for the endgame, and blending
between them by how much material is still on the board.

Phase 7's tapered-evaluation upgrade imports these. The tables here are built
from simple, readable positional principles, so they are a solid baseline you
can understand at a glance and tune to taste, not a tuned engine's secret
numbers. Everything is from White's point of view; mirror across the rank for
Black, exactly as the kit's ``pst_square`` already does.
"""

from __future__ import annotations

from chessdk.squares import file_of, rank_of, sq
from chessdk.types import BISHOP, KING, KNIGHT, PAWN, QUEEN, ROOK, WHITE, Color, Kind


# Tapered material values (midgame, endgame) in centipawns.
MG_VALUE: dict[Kind, int] = {PAWN: 82, KNIGHT: 337, BISHOP: 365, ROOK: 477, QUEEN: 1025, KING: 0}
EG_VALUE: dict[Kind, int] = {PAWN: 94, KNIGHT: 281, BISHOP: 297, ROOK: 512, QUEEN: 936, KING: 0}

# Phase weight per piece kind; a full board (both sides) sums to PHASE_MAX.
_PHASE_WEIGHT: dict[Kind, int] = {PAWN: 0, KNIGHT: 1, BISHOP: 1, ROOK: 2, QUEEN: 4, KING: 0}
PHASE_MAX = 24


def game_phase(board) -> int:
    """Return 0 (bare-king endgame) up to PHASE_MAX (full material).

    This is the blend factor: near PHASE_MAX use the midgame tables, near 0 use
    the endgame tables, and interpolate in between.
    """
    total = 0
    for piece in board.state.pieces:
        if piece is not None:
            total += _PHASE_WEIGHT[piece.kind]
    return min(total, PHASE_MAX)


# --- table construction from positional principles --------------------------

def _central(square: int) -> int:
    """A centrality score: high in the middle, negative in the corners."""
    return (6 - abs(2 * file_of(square) - 7)) + (6 - abs(2 * rank_of(square) - 7))


def _table(fn) -> tuple[int, ...]:
    return tuple(fn(s) for s in range(64))


def _pawn_mg(s: int) -> int:
    f, r = file_of(s), rank_of(s)
    centre = 12 if (f in (3, 4) and r in (3, 4)) else (6 if f in (2, 5) and r in (3, 4) else 0)
    return centre + max(0, r - 1) * 2


def _pawn_eg(s: int) -> int:
    # the further advanced, the better (White pushes toward rank 7)
    return max(0, rank_of(s) - 1) * 10


def _king_mg(s: int) -> int:
    # safety: reward the back rank and the corners, punish the centre
    back = 14 if rank_of(s) == 0 else 0
    return back - 4 * _central(s)


def _king_eg(s: int) -> int:
    # activity: march to the centre
    return 4 * _central(s)


MG_PST: dict[Kind, tuple[int, ...]] = {
    PAWN: _table(_pawn_mg),
    KNIGHT: _table(lambda s: 5 * _central(s)),
    BISHOP: _table(lambda s: 3 * _central(s)),
    ROOK: _table(lambda s: (25 if rank_of(s) == 6 else 0) + (4 if file_of(s) in (3, 4) else 0)),
    QUEEN: _table(lambda s: 1 * _central(s)),
    KING: _table(_king_mg),
}

EG_PST: dict[Kind, tuple[int, ...]] = {
    PAWN: _table(_pawn_eg),
    KNIGHT: _table(lambda s: 4 * _central(s)),
    BISHOP: _table(lambda s: 3 * _central(s)),
    ROOK: _table(lambda s: 3 * max(0, rank_of(s) - 4)),
    QUEEN: _table(lambda s: 2 * _central(s)),
    KING: _table(_king_eg),
}


def _pst_lookup(table: tuple[int, ...], color: Color, square: int) -> int:
    if color == WHITE:
        return table[square]
    return table[sq(file_of(square), 7 - rank_of(square))]


def tapered_pst(kind: Kind, color: Color, square: int, phase: int) -> int:
    """Blend the midgame and endgame PST value for a piece, by game phase."""
    mg = _pst_lookup(MG_PST[kind], color, square)
    eg = _pst_lookup(EG_PST[kind], color, square)
    return (mg * phase + eg * (PHASE_MAX - phase)) // PHASE_MAX


def tapered_eval(board) -> int:
    """Reference tapered evaluation, White-relative centipawns.

    Material plus piece-square tables, each blended between its midgame and
    endgame value by the current game phase. No mobility or other terms, so it
    is cheap to call at every leaf.
    """
    phase = game_phase(board)
    score = 0
    for square, piece in enumerate(board.state.pieces):
        if piece is None:
            continue
        mg = MG_VALUE[piece.kind] + _pst_lookup(MG_PST[piece.kind], piece.color, square)
        eg = EG_VALUE[piece.kind] + _pst_lookup(EG_PST[piece.kind], piece.color, square)
        value = (mg * phase + eg * (PHASE_MAX - phase)) // PHASE_MAX
        score += value if piece.color == WHITE else -value
    return score
