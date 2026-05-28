"""Shared helpers for house bots.

Two move-selection helpers live here, one for each phase the bots have
existed across. Phase 4's ``pick_best`` runs eval-and-pick at depth one
(no lookahead). Phase 5's ``minimax_pick`` runs proper alpha-beta search
at the given depth, using the same per-bot scoring function at the
leaves. Each Phase 4 bot's ``choose_move`` calls one of these helpers,
which is how the same personality (a ``_score`` function) gets to deepen
as the kit version moves up.
"""

from __future__ import annotations

import random
from typing import Callable

from chessdk.evaluation import MATE_SCORE
from chessdk.search import _decay_mate, search
from chessdk.types import Move, WHITE


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

    return rng.choice(best_moves)


def _capture_only_search(
    board,
    depth: int,
    eval_fn: Callable[[object], int],
    alpha: int = -MATE_SCORE,
    beta: int = MATE_SCORE,
) -> int:
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
