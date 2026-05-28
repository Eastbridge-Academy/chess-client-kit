"""Stage 13: ``evaluate(board)`` reflects material and recognizes terminal positions.

We assert direction and rough magnitude on positions with a clear material
imbalance, plus the three terminal cases: White checkmated, Black checkmated,
and stalemate. Your piece values and other weights are your own choices —
the assertions below only pin down sign and order-of-magnitude, never exact
centipawns.
"""

from __future__ import annotations

import pytest

from board import Board
from evaluation import evaluate


# ---------------------------------------------------------------------------
# Material direction across a few imbalanced starting positions.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "fen,description,lo,hi",
    [
        # Starting position: symmetric, score should be near zero
        (
            "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            "starting position",
            -200, 200,
        ),
        # Black missing queen: white up a queen (~900 cp)
        (
            "rnb1kbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            "white up a queen",
            500, 1500,
        ),
        # White missing queen: black up a queen
        (
            "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNB1KBNR w KQkq - 0 1",
            "black up a queen",
            -1500, -500,
        ),
        # Black missing both rooks: white up ~1000 cp
        (
            "1nbqkbn1/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            "white up two rooks",
            600, 1600,
        ),
        # White missing knight and bishop: black up ~600 cp
        (
            "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/R2QK2R w KQkq - 0 1",
            "black up two minor pieces",
            -1100, -400,
        ),
    ],
)
def test_material_direction(fen: str, description: str, lo: int, hi: int):
    board = Board.from_fen(fen)
    score = evaluate(board)
    assert lo <= score <= hi, (
        f"{description}: evaluate returned {score}, expected in [{lo}, {hi}]"
    )


# ---------------------------------------------------------------------------
# Terminal positions: checkmate and stalemate.
# ---------------------------------------------------------------------------


def test_black_is_checkmated_evaluates_strongly_positive():
    """Black is back-rank mated; White has just won, so the eval should be
    enormous and positive (centipawns far above any material imbalance)."""
    # White rook on a8 delivers mate; Black king on g8 has nowhere to go.
    fen = "R5k1/5ppp/8/8/8/8/8/6K1 b - - 1 1"
    board = Board.from_fen(fen)
    score = evaluate(board)
    assert score >= 100_000, (
        f"expected a mate-magnitude positive score, got {score}"
    )


def test_white_is_checkmated_evaluates_strongly_negative():
    """White is mated by fool's mate. Eval should be enormous and negative."""
    fen = "rnb1kbnr/pppp1ppp/8/4p3/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 0 1"
    board = Board.from_fen(fen)
    score = evaluate(board)
    assert score <= -100_000, (
        f"expected a mate-magnitude negative score, got {score}"
    )


def test_stalemate_evaluates_near_zero():
    """Black to move with no legal moves and not in check. Stalemate is a
    draw, so the eval should be near zero — definitely not mate-magnitude."""
    # Black king on a8, white king on c5, white queen on b6.
    fen = "k7/8/1Q6/2K5/8/8/8/8 b - - 0 1"
    board = Board.from_fen(fen)
    score = evaluate(board)
    assert abs(score) < 100, (
        f"expected stalemate to score near zero, got {score}"
    )
