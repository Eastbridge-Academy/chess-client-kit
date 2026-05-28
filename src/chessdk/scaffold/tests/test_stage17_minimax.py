"""Stage 17: ``search`` runs minimax with terminal handling and mate distance.

The tests supply a simple material-only evaluation function so that the
student's evaluator is not under test here, only their search. We verify:

  - On a position with no legal moves, the search returns the right score
    (mate magnitude with the right sign, or zero for stalemate).
  - Mate-in-one is found at depth one and scored as ``MATE_SCORE - 1``.
  - The same mate-in-one is still scored as ``MATE_SCORE - 1`` at deeper
    searches (the mate distance does not change with depth).
  - A mate-in-two position at depth three returns ``MATE_SCORE - 3``.
  - On a normal position, the search returns a legal move.
"""

from __future__ import annotations

from board import Board
from chessdk import MATE_SCORE, PIECE_VALUE_CLASSIC, WHITE
from search import search


def _material(board) -> int:
    """Simple material-only evaluator for testing.

    Search handles terminal positions itself, so this function is only
    called on positions with legal moves; no checkmate/stalemate logic
    is needed here.
    """
    total = 0
    for piece in board.pieces:
        if piece is None:
            continue
        sign = 1 if piece.color == WHITE else -1
        total += sign * PIECE_VALUE_CLASSIC[piece.kind]
    return total


# ---------------------------------------------------------------------------
# Terminal positions: checkmate and stalemate handling lives in search.
# ---------------------------------------------------------------------------


def test_checkmate_position_scores_mate_for_white():
    """Black has been mated on the back rank; from White's POV the score
    is mate-magnitude positive."""
    board = Board.from_fen("R5k1/5ppp/8/8/8/8/8/6K1 b - - 1 1")
    score, _ = search(board, 0, _material)
    assert score == MATE_SCORE


def test_checkmate_position_scores_mate_for_black():
    """White has been mated by fool's mate; mate-magnitude negative."""
    board = Board.from_fen("rnb1kbnr/pppp1ppp/8/4p3/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 0 1")
    score, _ = search(board, 0, _material)
    assert score == -MATE_SCORE


def test_stalemate_position_scores_zero():
    """Black to move with no legal moves and not in check; stalemate is a draw."""
    board = Board.from_fen("k7/8/1Q6/2K5/8/8/8/8 b - - 0 1")
    score, _ = search(board, 0, _material)
    assert score == 0


# ---------------------------------------------------------------------------
# Mate distance: shorter mates score higher in magnitude than longer mates.
# ---------------------------------------------------------------------------


def test_mate_in_one_at_depth_one_scores_mate_minus_one():
    """White plays Rd8# (back-rank mate); search at depth one should find
    it and report a score of MATE_SCORE - 1."""
    board = Board.from_fen("6k1/5ppp/8/8/8/8/5PPP/3R2K1 w - - 0 1")
    score, move = search(board, 1, _material)
    assert score == MATE_SCORE - 1
    assert move is not None and move.uci() == "d1d8"


def test_mate_in_one_at_depth_three_still_scores_mate_minus_one():
    """The same mate-in-one position at a deeper search still scores as
    mate at distance one ply (the mate is found at the first ply, not at
    a deeper level)."""
    board = Board.from_fen("6k1/5ppp/8/8/8/8/5PPP/3R2K1 w - - 0 1")
    score, _ = search(board, 3, _material)
    assert score == MATE_SCORE - 1


def test_mate_in_two_at_depth_three_scores_mate_minus_three():
    """K+Q vs K endgame: 1.Kg6 Kg8 2.Qa8#. Three plies to mate, so the
    score should be MATE_SCORE - 3."""
    board = Board.from_fen("7k/8/5K2/8/8/8/8/Q7 w - - 0 1")
    score, _ = search(board, 3, _material)
    assert score == MATE_SCORE - 3


# ---------------------------------------------------------------------------
# Normal positions: search returns a legal move.
# ---------------------------------------------------------------------------


def test_search_at_starting_position_returns_legal_move():
    board = Board()
    score, move = search(board, 2, _material)
    assert move is not None
    assert move in board.legal_moves()
