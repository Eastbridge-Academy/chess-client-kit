"""Focused checks for the magnus_maximus house bot.

The other house bots are covered by the parametrized smoke tests in
``test_house_bots.py``; magnus_maximus carries extra machinery (an in-flight
time abort, a transposition table, a quiescence search) that is worth pinning
down on its own: it must always return a legal move without disturbing the
board it was handed, even on a one-millisecond budget, and it must see a move
ahead well enough to take a free piece and to mate in one.
"""

from __future__ import annotations

import time

import pytest

from chessdk.house.magnus_maximus import choose_move
from chessdk.reference import Board


POSITIONS = [
    "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
    "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1",
    "r4rk1/1pp1qppp/p1np1n2/2b1p1B1/2B1P1b1/P1NP1N2/1PP1QPPP/R4RK1 w - - 0 10",
    "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1",
    "8/8/8/4k3/8/8/4K3/4R3 w - - 0 1",
    "Q6k/8/8/8/8/8/8/4K3 b - - 0 1",  # black in check, must move king
]


@pytest.mark.parametrize("fen", POSITIONS)
@pytest.mark.parametrize("budget_ms", [1, 50, 500])
def test_returns_legal_move_and_leaves_board_untouched(fen, budget_ms):
    board = Board.from_fen(fen)
    before = board.to_fen()
    legal = board.legal_moves()
    move = choose_move(board, budget_ms)
    assert move in legal, f"illegal move {move.uci()} on {fen}"
    assert board.to_fen() == before, "choose_move mutated the board it was given"


def test_one_millisecond_budget_still_returns_quickly():
    # Depth one always completes, so even a 1 ms budget yields a move fast.
    board = Board.from_fen(POSITIONS[1])
    start = time.perf_counter()
    move = choose_move(board, 1)
    elapsed = time.perf_counter() - start
    assert move in board.legal_moves()
    assert elapsed < 2.0, f"1 ms budget took {elapsed:.2f}s (should be near-instant)"


def test_captures_a_hanging_queen():
    # White pawn on e4, black queen on d5: exd5 wins the queen outright.
    board = Board.from_fen("4k3/8/8/3q4/4P3/8/8/4K3 w - - 0 1")
    move = choose_move(board, 300)
    assert move.uci() == "e4d5"


def test_finds_mate_in_one():
    # White rook delivers back-rank mate with Re8#.
    board = Board.from_fen("6k1/5ppp/8/8/8/8/8/4R1K1 w - - 0 1")
    move = choose_move(board, 500)
    assert move.uci() == "e1e8"
