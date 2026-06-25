"""Your search function.

``search(board, depth, eval_fn, alpha, beta)`` runs minimax with alpha-beta
pruning. It returns ``(score, best_move)``: a White-relative centipawn score
for the position under optimal play to the given depth, and the move that
achieves that score (or ``None`` at terminal or leaf nodes).

The search handles terminal positions itself (a side with no legal moves
that's in check is mated; not in check is stalemated), so the ``eval_fn``
parameter only ever sees positions with legal moves left to play. Phase 5
builds this up across four stages: Stage 17 introduces minimax with mate
distance, Stage 18 adds alpha-beta cutoffs, Stage 19 adds the move-ordering
helper below, and Stage 20 instruments the whole thing.

Phase 6 adds two more functions to this file: ``search_iterative`` (Stages
21--22), which deepens the search one ply at a time on a time budget so the
bot always has a move ready and never flags, and ``quiesce`` (Stage 23),
which resolves the captures at a leaf before scoring it so the evaluator is
never fooled by a piece that hangs one ply past the horizon.
"""

from __future__ import annotations

from typing import Callable

from board import Board
from chessdk import MATE_SCORE, Move


def search(
    board: Board,
    depth: int,
    eval_fn: Callable[[Board], int],
    alpha: int = -MATE_SCORE,
    beta: int = MATE_SCORE,
) -> tuple[int, Move | None]:
    """Return ``(best_score_for_position, best_move)`` after searching to
    the given depth."""
    raise NotImplementedError("search: implement in Phase 5 (Stage 17)")


def order_moves(board: Board, moves: list[Move]) -> list[Move]:
    """Return ``moves`` sorted to put likely-strong moves first."""
    raise NotImplementedError("order_moves: implement in Phase 5 (Stage 19)")


def search_iterative(
    board: Board,
    eval_fn: Callable[[Board], int],
    max_depth: int = 64,
    time_budget_ms: int | None = None,
) -> tuple[int, Move | None]:
    """Iterative deepening: search depth 1, then 2, and so on, returning the
    ``(score, move)`` of the deepest iteration that finished.

    With ``time_budget_ms`` set, stop deepening once the budget for this
    move is (about half) spent, after always completing at least depth one,
    so the bot returns a legal move even on a tiny clock. With it left as
    ``None``, deepen all the way to ``max_depth``. Set the module-level
    ``last_depth`` and ``last_score`` for the UCI display as you go.
    """
    raise NotImplementedError(
        "search_iterative: implement in Phase 6 (Stages 21-22)"
    )


def quiesce(
    board: Board,
    alpha: int,
    beta: int,
    eval_fn: Callable[[Board], int],
) -> int:
    """Resolve the pending captures, then evaluate (quiescence search).

    Return a White-relative score for the position after the capture
    sequence has played itself out, so the static evaluator only ever
    judges a settled position. This is a smarter leaf evaluator: wrap your
    static ``evaluate`` in it and hand the result to the search as the leaf
    scorer (Phase 6, Stage 23).
    """
    raise NotImplementedError("quiesce: implement in Phase 6 (Stage 23)")


def search_tt(
    board: Board,
    depth: int,
    eval_fn: Callable[[Board], int],
    tt: dict,
    alpha: int = -MATE_SCORE,
    beta: int = MATE_SCORE,
) -> tuple[int, Move | None]:
    """Alpha-beta search with a transposition table (Phase 7, Stages 27-28).

    The same shape as ``search``, plus ``tt``: a dictionary mapping a
    position's ``board.zobrist_hash()`` to ``(depth, flag, score, best_move)``.
    Probe it on entry (trust a deep-enough entry's score according to its bound
    flag, and try its stored best move first), and store what you found on
    exit. It must return the same score as plain ``search`` at the same depth.
    """
    raise NotImplementedError("search_tt: implement in Phase 7 (Stages 27-28)")
