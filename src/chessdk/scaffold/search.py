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
