"""Search primitives: minimax, alpha-beta, and move ordering.

This module is the library-side companion to the student's ``search.py``
(introduced in Phase 5). It ships the reference implementation used by
the kit's tests, the Phase 5 house bots, and any tooling that needs a
known-correct search.

The core function ``search(board, depth, eval_fn, alpha, beta)`` runs
classical minimax with alpha-beta pruning, calling ``eval_fn`` only at
the leaves of the search tree. Terminal positions (no legal moves) are
handled by the search itself with mate-distance scoring, so the eval
function never has to know about checkmate or stalemate. The companion
``order_moves`` arranges the legal-move list with captures first and
MVV-LVA priority among captures, which is what makes alpha-beta's
pruning power show up in practice.
"""

from __future__ import annotations

from typing import Callable

from chessdk.evaluation import MATE_SCORE, PIECE_VALUE_CLASSIC
from chessdk.types import Move, WHITE


# Mate scores live in a narrow band near ±MATE_SCORE; we use this threshold
# to detect "is this child score a mate score?" when applying mate-distance
# decay on the way up the tree. The band is wide enough to accommodate
# distances of several thousand plies, well beyond anything reachable in a
# real search.
_MATE_BAND = 1000

# Module-level node counter incremented at the top of every ``search`` call.
# Used by the house bots' shared ``minimax_pick`` helper to report nodes
# and nps to the UCI wrapper, mirroring the ``search.nodes_visited`` pattern
# that the student-facing scaffold uses.
nodes_visited: int = 0


def _decay_mate(score: int) -> int:
    """Adjust a mate score by one ply on the way up the recursion.

    Mate scores carry distance information in their magnitude: a winning
    mate at distance 0 from the leaf is ``+MATE_SCORE``, at distance 1 is
    ``+MATE_SCORE - 1``, and so on. When we propagate this score up one
    level, the distance increases by one ply, so the magnitude shrinks.
    The same arithmetic applies to losing-mate scores in the negative
    direction.

    Non-mate scores pass through unchanged.
    """
    if score >= MATE_SCORE - _MATE_BAND:
        return score - 1
    if score <= -MATE_SCORE + _MATE_BAND:
        return score + 1
    return score


def search(
    board,
    depth: int,
    eval_fn: Callable[[object], int],
    alpha: int = -MATE_SCORE,
    beta: int = MATE_SCORE,
) -> tuple[int, Move | None]:
    """Run minimax with alpha-beta to the given depth.

    Returns ``(score, best_move)`` where ``score`` is the value of the
    position from White's point of view (positive favors White, negative
    favors Black) and ``best_move`` is the move that achieves that score
    under optimal play (or ``None`` at terminal or leaf nodes).

    The search handles terminal positions itself: a position with no
    legal moves and the side to move in check returns a mate score with
    the appropriate sign, and one not in check returns zero (stalemate).
    The ``eval_fn`` is called only when the position has legal moves and
    we've reached depth zero, so the evaluator never has to know about
    checkmate or stalemate.
    """
    global nodes_visited
    nodes_visited += 1
    legal = board.legal_moves()

    if not legal:
        if board.is_in_check():
            return (
                -MATE_SCORE if board.side_to_move == WHITE else MATE_SCORE,
                None,
            )
        return 0, None

    if depth == 0:
        return eval_fn(board), None

    ordered = order_moves(board, legal)
    best_move: Move | None = None

    if board.side_to_move == WHITE:
        best_score = -MATE_SCORE - 1
        for move in ordered:
            board.make_move(move)
            child_score, _ = search(board, depth - 1, eval_fn, alpha, beta)
            board.undo_move()
            child_score = _decay_mate(child_score)
            if child_score > best_score:
                best_score = child_score
                best_move = move
            if best_score > alpha:
                alpha = best_score
            if alpha >= beta:
                break
        return best_score, best_move

    best_score = MATE_SCORE + 1
    for move in ordered:
        board.make_move(move)
        child_score, _ = search(board, depth - 1, eval_fn, alpha, beta)
        board.undo_move()
        child_score = _decay_mate(child_score)
        if child_score < best_score:
            best_score = child_score
            best_move = move
        if best_score < beta:
            beta = best_score
        if alpha >= beta:
            break
    return best_score, best_move


def order_moves(board, moves: list[Move]) -> list[Move]:
    """Sort moves so likely-strong moves come first.

    Captures appear before quiet moves, and within captures the order is
    MVV-LVA: most valuable victim first, with the cheapest attacker
    breaking ties among captures of the same victim. This is the static
    ordering that makes alpha-beta's pruning effective; deeper ordering
    refinements (killer moves, history heuristic, hash moves) come in
    Phase 6.

    The returned list is a new list; the input is not mutated.
    """
    def _key(move: Move) -> tuple[int, int]:
        victim = board.piece_at(move.to_sq)
        if victim is None:
            return (0, 0)
        attacker = board.piece_at(move.from_sq)
        attacker_value = (
            PIECE_VALUE_CLASSIC[attacker.kind] if attacker is not None else 0
        )
        return (PIECE_VALUE_CLASSIC[victim.kind], -attacker_value)

    return sorted(moves, key=_key, reverse=True)
