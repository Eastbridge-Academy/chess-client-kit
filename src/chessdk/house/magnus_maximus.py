"""magnus_maximus: the final boss.

A genuinely strong engine that sits a clear rung above ``magnus_mini``. Its
strength comes from four things working together:

  * a **tapered evaluation** (PeSTO-style midgame/endgame material and
    piece-square tables blended by the amount of material left on the board),
  * a **transposition table** keyed by a Zobrist hash, storing depth and
    bound-flag entries and feeding the hash move to the move orderer,
  * **killer and history move ordering** on top of MVV-LVA captures, and
  * **deep iterative deepening** with rock-solid time management.

Unlike the other house bots, this one does not reuse the reference ``search``
in ``chessdk.search`` (which has no transposition table or killers). It runs
its own negamax alpha-beta with principal-variation search, null-move pruning,
late move reductions, check extensions, and a captures-only quiescence search.
Everything it needs (the evaluation tables and the Zobrist keys) is defined
locally so the bot is self-contained.

Its "personality" is simply to play well. The version lives in the kit, not in
the name.

Time management is built so the bot never loses on time. ``choose_move`` is
given only the remaining clock, so it budgets conservatively from that alone
and guards the budget three ways: a per-move budget, a between-iterations stop
before starting a deeper search, and an in-flight deadline that aborts the
current search and falls back to the last completed depth's move. Depth one is
always completed before any clock check, so a legal move always comes back,
even on a one-millisecond budget.
"""

from __future__ import annotations

import random
import sys
import time

from chessdk.evaluation import MATE_SCORE
from chessdk.squares import (
    BISHOP_DIRECTIONS,
    KING_OFFSETS,
    KNIGHT_OFFSETS,
    QUEEN_DIRECTIONS,
    ROOK_DIRECTIONS,
    file_of,
    rank_of,
    sq,
)
from chessdk.types import (
    BISHOP,
    BLACK,
    KING,
    KNIGHT,
    Move,
    PAWN,
    QUEEN,
    ROOK,
    WHITE,
)


# Deep search trees can recurse past CPython's default limit once check
# extensions stack up; lift it so a long forcing line never raises.
sys.setrecursionlimit(10000)


# Random tie-breaker, kept only so ``chess-cli play --seed`` (which seeds every
# house module exposing ``_rng``) stays reproducible and so there is a safe
# fallback move source. The search itself is deterministic.
_rng = random.Random()


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

INF = MATE_SCORE + 1
# Scores within this band of +/-MATE_SCORE are mate scores carrying a
# distance-to-mate in their magnitude.
_MATE_BOUND = MATE_SCORE - 1000

_MAX_DEPTH = 64          # iterative-deepening backstop
_MAX_PLY = 128           # hard recursion-depth cap (also sizes the killer table)

# Transposition-table bound flags.
_EXACT = 0
_LOWER = 1
_UPPER = 2

# Check the clock every this-many nodes. The node rate on the pure-Python
# reference board is modest, so a small interval keeps the in-flight abort
# tight without measurable overhead (perf_counter is far cheaper than a node).
_CHECK_MASK = 31

_TEMPO = 10              # side-to-move bonus, applied in the search leaf
_BISHOP_PAIR = 30        # centipawn bonus for holding both bishops
_QDELTA = 200            # quiescence delta-pruning safety margin (centipawns)
_DRAW = 0                # repetition / fifty-move score

# MVV-LVA piece values, also used for quiescence delta pruning.
_VAL = {PAWN: 100, KNIGHT: 320, BISHOP: 330, ROOK: 500, QUEEN: 900, KING: 20000}

# Move-ordering score bands (descending). The hash move is tried first, then
# winning/equal captures and promotions, then the two killer moves, then quiet
# moves by history score, and finally losing captures.
_ORD_TT = 1 << 31
_ORD_PROMO = 1 << 30
_ORD_GOODCAP = 1 << 29
_ORD_KILLER0 = (1 << 28) + 1
_ORD_KILLER1 = 1 << 28
_ORD_BADCAP = -(1 << 29)
_HIST_CAP = 1 << 24      # quiet history is clamped below the killer band


class _TimeUp(Exception):
    """Raised when the in-flight deadline passes; unwinds the current search."""


# ---------------------------------------------------------------------------
# Evaluation tables (PeSTO / "Rofchade" tapered values)
# ---------------------------------------------------------------------------
#
# Each table is written rank 8 (top) down to rank 1, files a..h left to right,
# matching how a board is drawn. ``_table`` flattens that into a 64-entry list
# indexed by sq(file, rank) with index 0 = a1, exactly like the rest of the
# kit. Black pieces look the table up mirrored across the middle rank.


def _table(rows: list[tuple[int, ...]]) -> list[int]:
    out = [0] * 64
    for visual_row, row in enumerate(rows):
        rank = 7 - visual_row
        for file, value in enumerate(row):
            out[rank * 8 + file] = value
    return out


_MG_VALUE = {PAWN: 82, KNIGHT: 337, BISHOP: 365, ROOK: 477, QUEEN: 1025, KING: 0}
_EG_VALUE = {PAWN: 94, KNIGHT: 281, BISHOP: 297, ROOK: 512, QUEEN: 936, KING: 0}
_PHASE = {PAWN: 0, KNIGHT: 1, BISHOP: 1, ROOK: 2, QUEEN: 4, KING: 0}

_MG_PST = {
    PAWN: _table([
        (0, 0, 0, 0, 0, 0, 0, 0),
        (98, 134, 61, 95, 68, 126, 34, -11),
        (-6, 7, 26, 31, 65, 56, 25, -20),
        (-14, 13, 6, 21, 23, 12, 17, -23),
        (-27, -2, -5, 12, 17, 6, 10, -25),
        (-26, -4, -4, -10, 3, 3, 33, -12),
        (-35, -1, -20, -23, -15, 24, 38, -22),
        (0, 0, 0, 0, 0, 0, 0, 0),
    ]),
    KNIGHT: _table([
        (-167, -89, -34, -49, 61, -97, -15, -107),
        (-73, -41, 72, 36, 23, 62, 7, -17),
        (-47, 60, 37, 65, 84, 129, 73, 44),
        (-9, 17, 19, 53, 37, 69, 18, 22),
        (-13, 4, 16, 13, 28, 19, 21, -8),
        (-23, -9, 12, 10, 19, 17, 25, -16),
        (-29, -53, -12, -3, -1, 18, -14, -19),
        (-105, -21, -58, -33, -17, -28, -19, -23),
    ]),
    BISHOP: _table([
        (-29, 4, -82, -37, -25, -42, 7, -8),
        (-26, 16, -18, -13, 30, 59, 18, -47),
        (-16, 37, 43, 40, 35, 50, 37, -2),
        (-4, 5, 19, 50, 37, 37, 7, -2),
        (-6, 13, 13, 26, 34, 12, 10, 4),
        (0, 15, 15, 15, 14, 27, 18, 10),
        (4, 15, 16, 0, 7, 21, 33, 1),
        (-33, -3, -14, -21, -13, -12, -39, -21),
    ]),
    ROOK: _table([
        (32, 42, 32, 51, 63, 9, 31, 43),
        (27, 32, 58, 62, 80, 67, 26, 44),
        (-5, 19, 26, 36, 17, 45, 61, 16),
        (-24, -11, 7, 26, 24, 35, -8, -20),
        (-36, -26, -12, -1, 9, -7, 6, -23),
        (-45, -25, -16, -17, 3, 0, -5, -33),
        (-44, -16, -20, -9, -1, 11, -6, -71),
        (-19, -13, 1, 17, 16, 7, -37, -26),
    ]),
    QUEEN: _table([
        (-28, 0, 29, 12, 59, 44, 43, 45),
        (-24, -39, -5, 1, -16, 57, 28, 54),
        (-13, -17, 7, 8, 29, 56, 47, 57),
        (-27, -27, -16, -16, -1, 17, -2, 1),
        (-9, -26, -9, -10, -2, -4, 3, -3),
        (-14, 2, -11, -2, -5, 2, 14, 5),
        (-35, -8, 11, 2, 8, 15, -3, 1),
        (-1, -18, -9, 10, -15, -25, -31, -50),
    ]),
    KING: _table([
        (-65, 23, 16, -15, -56, -34, 2, 13),
        (29, -1, -20, -7, -8, -4, -38, -29),
        (-9, 24, 2, -16, -20, 6, 22, -22),
        (-17, -20, -12, -27, -30, -25, -14, -36),
        (-49, -1, -27, -39, -46, -44, -33, -51),
        (-14, -14, -22, -46, -44, -30, -15, -27),
        (1, 7, -8, -64, -43, -16, 9, 8),
        (-15, 36, 12, -54, 8, -28, 24, 14),
    ]),
}

_EG_PST = {
    PAWN: _table([
        (0, 0, 0, 0, 0, 0, 0, 0),
        (178, 173, 158, 134, 147, 132, 165, 187),
        (94, 100, 85, 67, 56, 53, 82, 84),
        (32, 24, 13, 5, -2, 4, 17, 17),
        (13, 9, -3, -7, -7, -8, 3, -1),
        (4, 7, -6, 1, 0, -5, -1, -8),
        (13, 8, 8, 10, 13, 0, 2, -7),
        (0, 0, 0, 0, 0, 0, 0, 0),
    ]),
    KNIGHT: _table([
        (-58, -38, -13, -28, -31, -27, -63, -99),
        (-25, -8, -25, -2, -9, -25, -24, -52),
        (-24, -20, 10, 9, -1, -9, -19, -41),
        (-17, 3, 22, 22, 22, 11, 8, -18),
        (-18, -6, 16, 25, 16, 17, 4, -18),
        (-23, -3, -1, 15, 10, -3, -20, -22),
        (-42, -20, -10, -5, -2, -20, -23, -44),
        (-29, -51, -23, -15, -22, -18, -50, -64),
    ]),
    BISHOP: _table([
        (-14, -21, -11, -8, -7, -9, -17, -24),
        (-8, -4, 7, -12, -3, -13, -4, -14),
        (2, -8, 0, -1, -2, 6, 0, 4),
        (-3, 9, 12, 9, 14, 10, 3, 2),
        (-6, 3, 13, 19, 7, 10, -3, -9),
        (-12, -3, 8, 10, 13, 3, -7, -15),
        (-14, -18, -7, -1, 4, -9, -15, -27),
        (-23, -9, -23, -5, -9, -16, -5, -17),
    ]),
    ROOK: _table([
        (13, 10, 18, 15, 12, 12, 8, 5),
        (11, 13, 13, 11, -3, 3, 8, 3),
        (7, 7, 7, 5, 4, -3, -5, -3),
        (4, 3, 13, 1, 2, 1, -1, 2),
        (3, 5, 8, 4, -5, -6, -8, -11),
        (-4, 0, -5, -1, -7, -12, -8, -16),
        (-6, -6, 0, 2, -9, -9, -11, -3),
        (-9, 2, 3, -1, -5, -13, 4, -20),
    ]),
    QUEEN: _table([
        (-9, 22, 22, 27, 27, 19, 10, 20),
        (-17, 20, 32, 41, 58, 25, 30, 0),
        (-20, 6, 9, 49, 47, 35, 19, 9),
        (3, 22, 24, 45, 57, 40, 57, 36),
        (-18, 28, 19, 47, 31, 34, 39, 23),
        (-16, -27, 15, 6, 9, 17, 10, 5),
        (-22, -23, -30, -16, -16, -23, -36, -32),
        (-33, -28, -22, -43, -5, -32, -20, -41),
    ]),
    KING: _table([
        (-74, -35, -18, -18, -11, 15, 4, -17),
        (-12, 17, 14, 17, 17, 38, 23, 11),
        (10, 17, 23, 15, 20, 45, 44, 13),
        (-8, 22, 24, 27, 26, 33, 26, 3),
        (-18, -4, 21, 24, 27, 23, 9, -11),
        (-19, -3, 11, 21, 23, 16, 7, -9),
        (-27, -11, 4, 13, 14, 4, -5, -17),
        (-53, -34, -21, -11, -28, -14, -24, -43),
    ]),
}


def _mirror(square: int) -> int:
    return sq(file_of(square), 7 - rank_of(square))


# Precompute, per (color, kind, square), the signed midgame and endgame
# contribution (White positive, Black negative, Black using the mirrored
# square). Indexed by a 12-way piece code = color * 6 + kind so the leaf
# evaluator is a single pass of array lookups.
_MG = [[0] * 64 for _ in range(12)]
_EG = [[0] * 64 for _ in range(12)]
for _kind in (PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING):
    for _s in range(64):
        _wmg = _MG_VALUE[_kind] + _MG_PST[_kind][_s]
        _weg = _EG_VALUE[_kind] + _EG_PST[_kind][_s]
        _MG[WHITE * 6 + _kind][_s] = _wmg
        _EG[WHITE * 6 + _kind][_s] = _weg
        _bmg = _MG_VALUE[_kind] + _MG_PST[_kind][_mirror(_s)]
        _beg = _EG_VALUE[_kind] + _EG_PST[_kind][_mirror(_s)]
        _MG[BLACK * 6 + _kind][_s] = -_bmg
        _EG[BLACK * 6 + _kind][_s] = -_beg

_PHASE_BY_KIND = [
    _PHASE[PAWN], _PHASE[KNIGHT], _PHASE[BISHOP],
    _PHASE[ROOK], _PHASE[QUEEN], _PHASE[KING],
]


def _score(board) -> int:
    """Static evaluation from White's point of view, in centipawns.

    Material and piece-square tables are blended between a midgame and an
    endgame table by the game phase (how much non-pawn material remains), and
    a small bishop-pair bonus is added. No legal-move generation happens here,
    which is what keeps the leaf cheap enough to search deeply.
    """
    mg = 0
    eg = 0
    phase = 0
    white_bishops = 0
    black_bishops = 0
    for s, p in enumerate(board.state.pieces):
        if p is None:
            continue
        kind = p.kind
        code = p.color * 6 + kind
        mg += _MG[code][s]
        eg += _EG[code][s]
        phase += _PHASE_BY_KIND[kind]
        if kind == BISHOP:
            if p.color == WHITE:
                white_bishops += 1
            else:
                black_bishops += 1
    if phase > 24:
        phase = 24
    # Truncate toward zero (not floor) so the blend is exactly antisymmetric
    # under a color swap; floor division would leave a 1cp side bias.
    blended = mg * phase + eg * (24 - phase)
    score = blended // 24 if blended >= 0 else -((-blended) // 24)
    if white_bishops >= 2:
        score += _BISHOP_PAIR
    if black_bishops >= 2:
        score -= _BISHOP_PAIR
    return score


# ---------------------------------------------------------------------------
# Zobrist hashing (self-contained; independent of the student-facing table)
# ---------------------------------------------------------------------------

_zrng = random.Random(0x9E3779B97F4A7C15)
_Z_PIECES = [[_zrng.getrandbits(64) for _ in range(64)] for _ in range(12)]
_Z_SIDE = _zrng.getrandbits(64)
_Z_CASTLE = [_zrng.getrandbits(64) for _ in range(4)]
_Z_EP = [_zrng.getrandbits(64) for _ in range(8)]


# ---------------------------------------------------------------------------
# Transposition table (persistent across a process, size-capped array)
# ---------------------------------------------------------------------------

_TT_BITS = 20
_TT_SIZE = 1 << _TT_BITS
_TT_MASK = _TT_SIZE - 1
_TT = None               # lazily allocated on first search
_GEN = 0                 # search generation, bumped each choose_move for aging


def _ensure_tt() -> None:
    global _TT
    if _TT is None:
        _TT = [None] * _TT_SIZE


def _tt_store_score(score: int, ply: int) -> int:
    """Rebase a root-relative mate score to be relative to this node."""
    if score > _MATE_BOUND:
        return score + ply
    if score < -_MATE_BOUND:
        return score - ply
    return score


def _tt_read_score(score: int, ply: int) -> int:
    """Inverse of ``_tt_store_score``: node-relative back to root-relative."""
    if score > _MATE_BOUND:
        return score - ply
    if score < -_MATE_BOUND:
        return score + ply
    return score


def _is_mate(score: int) -> bool:
    return score > _MATE_BOUND or score < -_MATE_BOUND


# ---------------------------------------------------------------------------
# The search
# ---------------------------------------------------------------------------


class _Search:
    """One search, owning all per-move state. The transposition table and the
    Zobrist keys are module-level so they persist and are shared across moves;
    everything else here is fresh per ``choose_move``."""

    def __init__(self, board):
        global _GEN
        self.board = board
        self._nodes = 0
        self._deadline = None
        self._best_move = None
        self._completed_score = None
        self._completed_depth = 0
        self._killers = [[None, None] for _ in range(_MAX_PLY)]
        self._history = [[[0] * 64 for _ in range(64)] for _ in range(2)]
        self._path = []          # Zobrist keys from the root down (repetition)
        self._null_guard = 0     # >0 while inside a null-move subtree
        self._null_ep = []       # saved en-passant squares for null moves
        self._snap = None
        _GEN += 1
        self._gen = _GEN
        _ensure_tt()

    # --- public entry --------------------------------------------------

    def run(self, time_left_ms: int) -> Move:
        board = self.board
        self._snapshot()
        start = time.perf_counter()
        budget = _budget_seconds(time_left_ms)
        deadline = start + budget
        self._deadline = None        # depth one runs un-aborted
        try:
            for depth in range(1, _MAX_DEPTH + 1):
                if depth >= 2:
                    if (time.perf_counter() - start) > budget * 0.5:
                        break
                    self._deadline = deadline
                score, move = self._search_root(depth)
                if move is not None:
                    self._best_move = move
                    self._completed_score = score
                    self._completed_depth = depth
                if _is_mate(score):
                    break
        except _TimeUp:
            self._restore()
        self._publish()
        mv = self._best_move
        if mv is None:
            legal = board.legal_moves()
            mv = legal[0] if legal else None
        return mv

    # --- root ----------------------------------------------------------

    def _search_root(self, depth: int):
        board = self.board
        key = self._zobrist()
        first = self._best_move
        if first is None:
            tt = self._tt_get(key)
            if tt is not None:
                first = tt[4]
        moves = board.pseudo_legal_moves()
        self._order_moves(moves, first, 0)

        alpha = -INF
        beta = INF
        best = -INF
        best_move = None
        side = board.side_to_move
        move_count = 0
        self._path.append(key)
        try:
            for m in moves:
                board.make_move(m)
                if board.is_in_check(side):
                    board.undo_move()
                    continue
                gives_check = board.is_in_check()
                child_depth = depth - 1
                if move_count == 0:
                    score = -self._negamax(child_depth, -beta, -alpha, 1, gives_check)
                else:
                    score = -self._negamax(child_depth, -alpha - 1, -alpha, 1, gives_check)
                    if alpha < score < beta:
                        score = -self._negamax(child_depth, -beta, -alpha, 1, gives_check)
                board.undo_move()
                move_count += 1
                if score > best:
                    best = score
                    best_move = m
                    if score > alpha:
                        alpha = score
            if best_move is not None:
                self._tt_put(key, depth, _EXACT, _tt_store_score(best, 0), best_move, 0)
            return best, best_move
        finally:
            self._path.pop()

    # --- negamax -------------------------------------------------------

    def _negamax(self, depth: int, alpha: int, beta: int, ply: int, in_check: bool) -> int:
        self._nodes += 1
        if (self._nodes & _CHECK_MASK) == 0:
            self._check_time()
        board = self.board

        if ply > 0 and board.state.halfmove_clock >= 100:
            return _DRAW

        armed = self._deadline is not None
        if in_check and armed and ply < _MAX_PLY - 8:
            depth += 1

        if depth <= 0:
            if armed:
                return self._qsearch(alpha, beta, ply)
            return self._eval_stm(in_check)
        if ply >= _MAX_PLY:
            return self._eval_stm(in_check)

        key = self._zobrist()
        track = self._null_guard == 0
        if track and ply > 0 and self._is_repetition(key, board.state.halfmove_clock):
            return _DRAW

        tt = self._tt_get(key)
        tt_move = None
        if tt is not None:
            tt_move = tt[4]
            if tt[1] >= depth and ply > 0:
                s = _tt_read_score(tt[3], ply)
                flag = tt[2]
                if flag == _EXACT:
                    return s
                if flag == _LOWER:
                    if s > alpha:
                        alpha = s
                elif flag == _UPPER:
                    if s < beta:
                        beta = s
                if alpha >= beta:
                    return s

        if track:
            self._path.append(key)
        try:
            side = board.side_to_move
            is_pv = (beta - alpha) > 1

            # Null-move pruning: hand the opponent a free move at reduced
            # depth; if they still cannot reach beta, this node is too good to
            # need a full search. Skipped in check, in PV nodes, near mate, and
            # with no non-pawn material (zugzwang).
            if (not is_pv) and (not in_check) and depth >= 3 \
                    and beta < _MATE_BOUND and self._has_non_pawn(side):
                r = 3 if depth >= 6 else 2
                self._null_guard += 1
                self._make_null()
                null_score = -self._negamax(depth - 1 - r, -beta, -beta + 1, ply + 1, False)
                self._make_null_undo()
                self._null_guard -= 1
                if null_score >= beta:
                    if null_score > _MATE_BOUND:
                        null_score = beta
                    self._tt_put(key, depth, _LOWER, _tt_store_score(null_score, ply), tt_move, ply)
                    return null_score

            moves = board.pseudo_legal_moves()
            self._order_moves(moves, tt_move, ply)

            if ply < _MAX_PLY:
                kill0, kill1 = self._killers[ply]
            else:
                kill0 = kill1 = None

            best = -INF
            best_move = None
            alpha_orig = alpha
            move_count = 0
            legal = 0
            for m in moves:
                is_cap = self._is_capture(m)
                is_quiet = (not is_cap) and (m.promotion is None)
                board.make_move(m)
                if board.is_in_check(side):
                    board.undo_move()
                    continue
                legal += 1
                gives_check = board.is_in_check()

                reduction = 0
                if (is_quiet and not is_pv and depth >= 3 and move_count >= 3
                        and not in_check and not gives_check
                        and m != kill0 and m != kill1):
                    reduction = 1
                    if move_count >= 6 and depth >= 5:
                        reduction = 2

                child_depth = depth - 1
                reduced = child_depth - reduction
                if reduced < 0:
                    reduced = 0
                if move_count == 0:
                    score = -self._negamax(child_depth, -beta, -alpha, ply + 1, gives_check)
                else:
                    score = -self._negamax(reduced, -alpha - 1, -alpha, ply + 1, gives_check)
                    if reduction and score > alpha:
                        score = -self._negamax(child_depth, -alpha - 1, -alpha, ply + 1, gives_check)
                    if alpha < score < beta:
                        score = -self._negamax(child_depth, -beta, -alpha, ply + 1, gives_check)
                board.undo_move()
                move_count += 1

                if score > best:
                    best = score
                    best_move = m
                    if score > alpha:
                        alpha = score
                        if alpha >= beta:
                            if is_quiet:
                                self._add_killer(ply, m)
                                self._history[side][m.from_sq][m.to_sq] += depth * depth
                            break

            if legal == 0:
                return (-MATE_SCORE + ply) if in_check else _DRAW

            if best <= alpha_orig:
                flag = _UPPER
            elif best >= beta:
                flag = _LOWER
            else:
                flag = _EXACT
            self._tt_put(key, depth, flag, _tt_store_score(best, ply), best_move, ply)
            return best
        finally:
            if track:
                self._path.pop()

    # --- quiescence ----------------------------------------------------

    def _qsearch(self, alpha: int, beta: int, ply: int) -> int:
        """Captures-only quiescence search.

        Stand on the static evaluation, then try only material-changing moves
        (captures and promotions) so the leaf is never scored in the middle of
        a trade. Checks are not resolved here; the main search's check
        extension keeps checking lines out of the quiescence horizon, which is
        what keeps this cheap in sharp positions.
        """
        self._nodes += 1
        if (self._nodes & _CHECK_MASK) == 0:
            self._check_time()
        board = self.board
        side = board.side_to_move

        stand = self._eval_stm(False)
        if stand >= beta:
            return stand
        if stand > alpha:
            alpha = stand
        if ply >= _MAX_PLY:
            return stand
        best = stand

        captures = self._gen_captures(side)
        self._order_captures(captures)
        pieces = board.pieces
        for m in captures:
            victim = pieces[m.to_sq]
            if m.promotion is None and victim is not None:
                if stand + _VAL[victim.kind] + _QDELTA <= alpha:
                    continue
            board.make_move(m)
            if board.is_in_check(side):
                board.undo_move()
                continue
            score = -self._qsearch(-beta, -alpha, ply + 1)
            board.undo_move()
            if score > best:
                best = score
                if score > alpha:
                    alpha = score
                    if alpha >= beta:
                        break
        return best

    # --- move generation / ordering ------------------------------------

    def _gen_captures(self, side):
        """Pseudo-legal captures and promotions only (quiescence move list).

        Mirrors the reference move generation but emits only moves that change
        material: captures, en-passant, and pawn promotions (including the
        non-capturing push to the last rank). Legality is checked by the caller
        when it makes the move.
        """
        board = self.board
        pieces = board.pieces
        ep = board.state.en_passant
        out = []
        for s, p in enumerate(pieces):
            if p is None or p.color != side:
                continue
            kind = p.kind
            f = s & 7
            r = s >> 3
            if kind == PAWN:
                direction = 1 if side == WHITE else -1
                promo_rank = 7 if side == WHITE else 0
                nr = r + direction
                if 0 <= nr < 8:
                    for df in (-1, 1):
                        nf = f + df
                        if 0 <= nf < 8:
                            t = nr * 8 + nf
                            tp = pieces[t]
                            if tp is not None and tp.color != side:
                                if nr == promo_rank:
                                    out.append(Move(s, t, QUEEN))
                                    out.append(Move(s, t, ROOK))
                                    out.append(Move(s, t, BISHOP))
                                    out.append(Move(s, t, KNIGHT))
                                else:
                                    out.append(Move(s, t))
                            elif tp is None and ep is not None and t == ep:
                                out.append(Move(s, t))
                    if nr == promo_rank:
                        t = nr * 8 + f
                        if pieces[t] is None:
                            out.append(Move(s, t, QUEEN))
                            out.append(Move(s, t, ROOK))
                            out.append(Move(s, t, BISHOP))
                            out.append(Move(s, t, KNIGHT))
            elif kind == KNIGHT:
                for df, dr in KNIGHT_OFFSETS:
                    nf, nr = f + df, r + dr
                    if 0 <= nf < 8 and 0 <= nr < 8:
                        t = nr * 8 + nf
                        tp = pieces[t]
                        if tp is not None and tp.color != side:
                            out.append(Move(s, t))
            elif kind == KING:
                for df, dr in KING_OFFSETS:
                    nf, nr = f + df, r + dr
                    if 0 <= nf < 8 and 0 <= nr < 8:
                        t = nr * 8 + nf
                        tp = pieces[t]
                        if tp is not None and tp.color != side:
                            out.append(Move(s, t))
            else:
                if kind == BISHOP:
                    dirs = BISHOP_DIRECTIONS
                elif kind == ROOK:
                    dirs = ROOK_DIRECTIONS
                else:
                    dirs = QUEEN_DIRECTIONS
                for df, dr in dirs:
                    nf, nr = f + df, r + dr
                    while 0 <= nf < 8 and 0 <= nr < 8:
                        t = nr * 8 + nf
                        tp = pieces[t]
                        if tp is None:
                            nf += df
                            nr += dr
                            continue
                        if tp.color != side:
                            out.append(Move(s, t))
                        break
        return out

    def _order_moves(self, moves, tt_move, ply):
        board = self.board
        pieces = board.pieces
        ep = board.state.en_passant
        side = board.side_to_move
        hist = self._history[side]
        if ply < _MAX_PLY:
            kill0, kill1 = self._killers[ply]
        else:
            kill0 = kill1 = None

        def key(m):
            if tt_move is not None and m == tt_move:
                return _ORD_TT
            to = m.to_sq
            victim = pieces[to]
            promo = m.promotion
            if promo is not None:
                base = _ORD_PROMO + _VAL[promo]
                if victim is not None:
                    base += _VAL[victim.kind]
                return base
            is_capture = victim is not None
            if not is_capture and ep is not None and to == ep:
                mover = pieces[m.from_sq]
                if mover is not None and mover.kind == PAWN and (m.from_sq & 7) != (to & 7):
                    is_capture = True
            if is_capture:
                vval = _VAL[victim.kind] if victim is not None else _VAL[PAWN]
                aval = _VAL[pieces[m.from_sq].kind]
                mvvlva = vval * 16 - aval
                if vval >= aval:
                    return _ORD_GOODCAP + mvvlva
                return _ORD_BADCAP + mvvlva
            if m == kill0:
                return _ORD_KILLER0
            if m == kill1:
                return _ORD_KILLER1
            h = hist[m.from_sq][to]
            return h if h < _HIST_CAP else _HIST_CAP

        moves.sort(key=key, reverse=True)

    def _order_captures(self, moves):
        pieces = self.board.pieces

        def key(m):
            base = 0
            promo = m.promotion
            if promo is not None:
                base += 100000 + _VAL[promo]
            victim = pieces[m.to_sq]
            if victim is not None:
                base += _VAL[victim.kind] * 16 - _VAL[pieces[m.from_sq].kind]
            return base

        moves.sort(key=key, reverse=True)

    # --- helpers -------------------------------------------------------

    def _is_capture(self, m) -> bool:
        board = self.board
        pieces = board.pieces
        if pieces[m.to_sq] is not None:
            return True
        ep = board.state.en_passant
        if ep is not None and m.to_sq == ep:
            mover = pieces[m.from_sq]
            if mover is not None and mover.kind == PAWN and (m.from_sq & 7) != (m.to_sq & 7):
                return True
        return False

    def _has_non_pawn(self, side) -> bool:
        for p in self.board.state.pieces:
            if p is not None and p.color == side and p.kind != PAWN and p.kind != KING:
                return True
        return False

    def _add_killer(self, ply, m) -> None:
        if ply >= _MAX_PLY:
            return
        slot = self._killers[ply]
        if slot[0] != m:
            slot[1] = slot[0]
            slot[0] = m

    def _eval_stm(self, in_check) -> int:
        ev = _score(self.board)
        if self.board.side_to_move == WHITE:
            return ev + _TEMPO
        return -ev + _TEMPO

    def _is_repetition(self, key, halfmove) -> bool:
        path = self._path
        n = len(path)
        limit = n - halfmove
        if limit < 0:
            limit = 0
        i = n - 2
        while i >= limit:
            if path[i] == key:
                return True
            i -= 2
        return False

    def _zobrist(self) -> int:
        st = self.board.state
        h = 0
        zp = _Z_PIECES
        for s, p in enumerate(st.pieces):
            if p is not None:
                h ^= zp[p.color * 6 + p.kind][s]
        if st.side_to_move == BLACK:
            h ^= _Z_SIDE
        c = st.castling
        if c.white_kingside:
            h ^= _Z_CASTLE[0]
        if c.white_queenside:
            h ^= _Z_CASTLE[1]
        if c.black_kingside:
            h ^= _Z_CASTLE[2]
        if c.black_queenside:
            h ^= _Z_CASTLE[3]
        ep = st.en_passant
        if ep is not None:
            h ^= _Z_EP[ep & 7]
        return h

    def _tt_get(self, key):
        e = _TT[key & _TT_MASK]
        if e is not None and e[0] == key:
            return e
        return None

    def _tt_put(self, key, depth, flag, score, move, ply) -> None:
        idx = key & _TT_MASK
        e = _TT[idx]
        if e is None or e[5] != self._gen or depth >= e[1]:
            _TT[idx] = (key, depth, flag, score, move, self._gen)

    def _make_null(self) -> None:
        st = self.board.state
        self._null_ep.append(st.en_passant)
        st.en_passant = None
        st.side_to_move = st.side_to_move.other

    def _make_null_undo(self) -> None:
        st = self.board.state
        st.side_to_move = st.side_to_move.other
        st.en_passant = self._null_ep.pop()

    def _check_time(self) -> None:
        if self._deadline is not None and time.perf_counter() >= self._deadline:
            raise _TimeUp()

    def _snapshot(self) -> None:
        st = self.board.state
        history = getattr(self.board, "_history", None)
        self._snap = (
            st.pieces[:], st.side_to_move, st.castling.copy(),
            st.en_passant, st.halfmove_clock, st.fullmove_number,
            len(history) if history is not None else 0,
        )

    def _restore(self) -> None:
        st = self.board.state
        pieces, stm, castling, ep, halfmove, fullmove, hlen = self._snap
        st.pieces[:] = pieces
        st.side_to_move = stm
        st.castling = castling.copy()
        st.en_passant = ep
        st.halfmove_clock = halfmove
        st.fullmove_number = fullmove
        history = getattr(self.board, "_history", None)
        if history is not None:
            del history[hlen:]
        self._null_guard = 0
        self._null_ep.clear()
        self._path.clear()

    def _publish(self) -> None:
        from chessdk.house import _common
        score = self._completed_score
        if score is None:
            white = None
        else:
            white = score if self.board.side_to_move == WHITE else -score
        _common.nodes_visited = self._nodes
        _common.last_score = white
        _common.last_depth = self._completed_depth


def _budget_seconds(time_left_ms: int) -> float:
    """Seconds to spend on this move, from the remaining clock alone.

    We spend roughly a thirtieth of the remaining time, which shrinks as the
    clock runs down so the bot never flags. A communication margin keeps a few
    tens of milliseconds in reserve once the clock gets very low; the in-flight
    deadline plus the always-finish-depth-one rule do the rest.
    """
    t = time_left_ms / 1000.0
    budget = t / 30.0
    margin_cap = t - 0.040
    if budget > margin_cap:
        budget = margin_cap
    if budget < 0.0:
        budget = 0.0
    return budget


def choose_move(board, time_left_ms: int) -> Move:
    return _Search(board).run(time_left_ms)
