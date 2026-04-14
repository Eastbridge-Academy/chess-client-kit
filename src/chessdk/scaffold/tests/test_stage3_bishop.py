"""Stage 3, Step 1: bishop moves."""

from __future__ import annotations

import pytest

from board import Board
from chessdk import WHITE
from .conftest import uci_set


@pytest.mark.parametrize(
    "fen, expected_count",
    [
        # Central bishop, empty board: 13 moves (4 + 3 + 4 + 2... let's count from d4)
        # d4 reaches: a1-c3 (3), e3-h8 diagonal from d4: e5 f6 g7 h8 (4), then d4 down-right: e3 f2 g1 (3), d4 up-left: c5 b6 a7 (3) = 13
        ("8/8/8/8/3B4/8/8/8 w - - 0 1", 13),
        # Corner bishop a1: 7 moves (full diagonal)
        ("8/8/8/8/8/8/8/B7 w - - 0 1", 7),
        # Bishop blocked by friendly pawns on all 4 diagonals (one step each)
        ("8/8/8/2P1P3/3B4/2P1P3/8/8 w - - 0 1", 0),
        # Bishop with 4 captures adjacent
        ("8/8/8/2p1p3/3B4/2p1p3/8/8 w - - 0 1", 4),
        # Handout diagram: bishop on e4 with blockers
        ("8/8/2p5/8/4B3/8/2P5/8 w - - 0 1", 9),
    ],
)
def test_bishop_move_counts(fen, expected_count):
    b = Board.from_fen(fen)
    moves = b._bishop_moves(b.side_to_move)
    assert len(moves) == expected_count, (
        f"bishop moves on {fen}: expected {expected_count}, "
        f"got {len(moves)}: {sorted(m.uci() for m in moves)}"
    )


def test_bishop_handout_diagram():
    """Bishop on e4; black pawn on c6 (capture), white pawn on c2 (blocker at d3)."""
    b = Board.from_fen("8/8/2p5/8/4B3/8/2P5/8 w - - 0 1")
    moves = b._bishop_moves(WHITE)
    assert uci_set(moves) == {
        "e4f5", "e4g6", "e4h7",      # up-right
        "e4d5", "e4c6",              # up-left (captures at c6)
        "e4f3", "e4g2", "e4h1",      # down-right
        "e4d3",                      # down-left (stops before c2)
    }


def test_bishop_excludes_friendly_blocker():
    """Bishop can't land on the friendly square."""
    b = Board.from_fen("8/8/8/2P5/3B4/8/8/8 w - - 0 1")
    moves = b._bishop_moves(WHITE)
    # Up-left is blocked immediately by C5; d4 can't reach c5
    assert "d4c5" not in uci_set(moves)


def test_bishop_includes_enemy_capture():
    b = Board.from_fen("8/8/8/2p5/3B4/8/8/8 w - - 0 1")
    moves = b._bishop_moves(WHITE)
    assert "d4c5" in uci_set(moves)
    # But not beyond the capture
    assert "d4b6" not in uci_set(moves)
    assert "d4a7" not in uci_set(moves)
