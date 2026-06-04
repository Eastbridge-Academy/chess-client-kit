"""Shared helpers for house bots.

One move-selection helper lives here per phase the bots have existed
across. Phase 4's ``pick_best`` runs eval-and-pick at depth one (no
lookahead). Phase 5's ``minimax_pick`` runs alpha-beta to a fixed depth.
Phase 6's ``iterative_pick`` runs iterative deepening on a time budget,
so the bots manage their clock and never flag, deepening only as far as
the budget (or their ``_DEPTH`` cap) allows. All three take the same
per-bot ``_score`` function, which is how one personality deepens as the
kit version moves up; the ``_score`` itself never changes. Each bot's
``choose_move`` calls the current phase's helper, passing its own
``_DEPTH`` as the depth cap.

(Quiescence, the other Phase 6 idea, is the student's tool: in pure
Python it multiplies these evals' cost by an order of magnitude, so the
house bots leave it out and stay fast. ``tunnel_vision`` already gives
students a captures-only opponent to test their quiescence against.)
"""

from __future__ import annotations

import random
import time
from typing import Callable

from chessdk import search as _search_module
from chessdk.evaluation import MATE_SCORE
from chessdk.search import _decay_mate, search
from chessdk.types import Move, WHITE


# Mate scores sit within this band of ±MATE_SCORE; used to stop deepening
# early once a forced mate has been found (no point searching past it).
_MATE_BAND = 1000


# Module-level instrumentation populated by ``minimax_pick`` so the UCI
# wrapper can emit standard ``info`` lines (nodes, nps, score, depth)
# for house bot games. Mirrors the convention students use in their own
# ``search.py`` for Stage 20 of the Phase 5 handout.
nodes_visited: int = 0
last_score: int | None = None
last_depth: int | None = None


def pick_best(
    board,
    score_fn: Callable[[object], int],
    rng: random.Random,
) -> Move:
    """Depth-one eval-and-pick.

    Apply each legal move, score the resulting position with ``score_fn``,
    and return one of the moves whose score is best for the side to move.
    Ties are broken at random via ``rng``.

    Used by Phase 4 house bots. Phase 5 bots use ``minimax_pick`` instead.
    """
    is_max = board.side_to_move == WHITE
    best_score: int | None = None
    best_moves: list[Move] = []
    for move in board.legal_moves():
        board.make_move(move)
        score = score_fn(board)
        board.undo_move()
        if best_score is None:
            best_score, best_moves = score, [move]
        elif (is_max and score > best_score) or (not is_max and score < best_score):
            best_score, best_moves = score, [move]
        elif score == best_score:
            best_moves.append(move)
    return rng.choice(best_moves)


def _reset_counters() -> None:
    global nodes_visited
    nodes_visited = 0
    _search_module.nodes_visited = 0


def _publish_metrics(score: int | None, depth: int) -> None:
    global nodes_visited, last_score, last_depth
    nodes_visited = nodes_visited + _search_module.nodes_visited
    last_score = score
    last_depth = depth


def minimax_pick(
    board,
    score_fn: Callable[[object], int],
    depth: int,
    rng: random.Random,
    capture_only: bool = False,
) -> Move:
    """Alpha-beta search at the root, picking the best move with random
    tiebreaking.

    Iterates over each legal move at the root, runs alpha-beta search to
    ``depth - 1`` on the resulting position with ``score_fn`` at the
    leaves, and returns one of the moves whose score is best for the
    side to move. The reference ``search`` from ``chessdk.search`` does
    the deeper recursion, so ordering at depth two and beyond is the
    captures-first/MVV-LVA arrangement that ``search`` uses internally.

    Setting ``capture_only=True`` restricts the search at every level to
    captures only, which is how the ``tunnel_vision`` house bot expresses
    its tactical-but-positionally-blind personality.
    """
    _reset_counters()
    is_max = board.side_to_move == WHITE
    best_score: int | None = None
    best_moves: list[Move] = []

    root_moves = board.legal_moves()
    if capture_only:
        captures = [m for m in root_moves if board.piece_at(m.to_sq) is not None]
        if captures:
            root_moves = captures
        # Fall back to all legal moves if there are no captures at all,
        # otherwise the bot would forfeit by failing to move.

    for move in root_moves:
        board.make_move(move)
        if capture_only:
            child_score = _capture_only_search(board, depth - 1, score_fn)
        else:
            child_score, _ = search(board, depth - 1, score_fn)
        board.undo_move()
        child_score = _decay_mate(child_score)

        if best_score is None:
            best_score, best_moves = child_score, [move]
        elif (is_max and child_score > best_score) or (
            not is_max and child_score < best_score
        ):
            best_score, best_moves = child_score, [move]
        elif child_score == best_score:
            best_moves.append(move)

    _publish_metrics(best_score, depth)
    return rng.choice(best_moves)


def _capture_only_search(
    board,
    depth: int,
    eval_fn: Callable[[object], int],
    alpha: int = -MATE_SCORE,
    beta: int = MATE_SCORE,
) -> int:
    global nodes_visited
    nodes_visited += 1
    """Search that only considers captures (no quiet moves).

    Used by ``tunnel_vision``: a sharp tactical engine that simply does
    not see positional play. Returns the centipawn score from White's
    point of view. Terminal positions are handled the same way as the
    main search.
    """
    legal = board.legal_moves()
    if not legal:
        if board.is_in_check():
            return -MATE_SCORE if board.side_to_move == WHITE else MATE_SCORE
        return 0

    captures = [m for m in legal if board.piece_at(m.to_sq) is not None]
    if depth == 0 or not captures:
        return eval_fn(board)

    if board.side_to_move == WHITE:
        best = -MATE_SCORE - 1
        for move in captures:
            board.make_move(move)
            child = _capture_only_search(board, depth - 1, eval_fn, alpha, beta)
            board.undo_move()
            child = _decay_mate(child)
            if child > best:
                best = child
            if best > alpha:
                alpha = best
            if alpha >= beta:
                break
        return best

    best = MATE_SCORE + 1
    for move in captures:
        board.make_move(move)
        child = _capture_only_search(board, depth - 1, eval_fn, alpha, beta)
        board.undo_move()
        child = _decay_mate(child)
        if child < best:
            best = child
        if best < beta:
            beta = best
        if alpha >= beta:
            break
    return best


def _move_budget_seconds(time_left_ms: int) -> float:
    """How long to think about this move, in seconds.

    ``time_left_ms`` is the remaining clock, so we spend a fraction of it
    (about a thirtieth, assuming roughly thirty moves left) on the move in
    front of us. This shrinks naturally as the clock runs down, which is
    why a time-managed bot never flags. The floor keeps the bot from
    moving instantly in severe time trouble.
    """
    return max(0.005, (time_left_ms / 1000.0) / 30.0)


def _root_iteration(
    board,
    score_fn: Callable[[object], int],
    depth: int,
    capture_only: bool,
) -> tuple[int | None, list[Move]]:
    """Run one full root search at ``depth``; return (best_score, best_moves).

    Mirrors ``minimax_pick``'s root loop (full window per child, all
    best-scoring moves collected for random tiebreaking); the only
    difference is that it is called once per deepening iteration.
    ``capture_only`` bots keep their all-captures search instead.
    """
    is_max = board.side_to_move == WHITE
    root_moves = board.legal_moves()
    if capture_only:
        captures = [m for m in root_moves if board.piece_at(m.to_sq) is not None]
        if captures:
            root_moves = captures

    best_score: int | None = None
    best_moves: list[Move] = []
    for move in root_moves:
        board.make_move(move)
        if capture_only:
            child_score = _capture_only_search(board, depth - 1, score_fn)
        else:
            child_score, _ = search(board, depth - 1, score_fn)
        board.undo_move()
        child_score = _decay_mate(child_score)

        if best_score is None:
            best_score, best_moves = child_score, [move]
        elif (is_max and child_score > best_score) or (
            not is_max and child_score < best_score
        ):
            best_score, best_moves = child_score, [move]
        elif child_score == best_score:
            best_moves.append(move)

    return best_score, best_moves


def iterative_pick(
    board,
    score_fn: Callable[[object], int],
    max_depth: int,
    rng: random.Random,
    time_left_ms: int,
    capture_only: bool = False,
) -> Move:
    """Iterative deepening on a time budget.

    Deepens one ply at a time, keeping the best move from the last
    completed iteration, and stops when the next iteration would not fit
    in the move's time budget or when ``max_depth`` (the bot's personality
    depth) is reached. Depth one always runs, so the bot returns a legal
    move even on a tiny clock. A forced mate ends the deepening early.

    The bot's ``_DEPTH`` is passed as ``max_depth``, capping how deep the
    bot looks even when it has time to spare; this keeps each bot's
    character (and the calibration the handouts are pinned against) stable
    rather than letting a fast machine deepen arbitrarily.
    """
    _reset_counters()
    start = time.perf_counter()
    budget = _move_budget_seconds(time_left_ms)

    chosen_score: int | None = None
    chosen_moves: list[Move] = []
    reached = 0
    for depth in range(1, max_depth + 1):
        if depth > 1 and (time.perf_counter() - start) > budget * 0.5:
            break
        score, moves = _root_iteration(board, score_fn, depth, capture_only)
        if not moves:
            break
        chosen_score, chosen_moves = score, moves
        reached = depth
        if score is not None and abs(score) >= MATE_SCORE - _MATE_BAND:
            break

    _publish_metrics(chosen_score, reached)
    return rng.choice(chosen_moves)
