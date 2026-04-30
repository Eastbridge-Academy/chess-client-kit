"""Perft validation against published reference counts.

These are the gold-standard correctness checks. A move generator that matches
perft at depth 3 on all three positions is essentially correct.

Position references:
- Starting: any chess engine documentation.
- Kiwipete: https://www.chessprogramming.org/Perft_Results (position 2).
- Position 3: ibid (position 3), designed to expose en-passant pin bugs.
"""

from __future__ import annotations

import pytest

from board import Board


def perft(board: Board, depth: int) -> int:
    if depth == 0:
        return 1
    total = 0
    for move in board.legal_moves():
        board.make_move(move)
        total += perft(board, depth - 1)
        board.undo_move()
    return total


@pytest.mark.parametrize(
    "name, fen, depth, expected",
    [
        ("start-d1", "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", 1, 20),
        ("start-d2", "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", 2, 400),
        ("start-d3", "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", 3, 8902),
        ("kiwipete-d1", "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1", 1, 48),
        ("kiwipete-d2", "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1", 2, 2039),
        ("kiwipete-d3", "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1", 3, 97862),
        ("pos3-d1", "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1", 1, 14),
        ("pos3-d2", "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1", 2, 191),
        ("pos3-d3", "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1", 3, 2812),
        ("pos3-d4", "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1", 4, 43238),
    ],
    ids=lambda x: x if isinstance(x, str) and not x.startswith("rnb") and not x.startswith("r3k") and not x.startswith("8/2p") else None,
)
def test_perft(name, fen, depth, expected):
    b = Board.from_fen(fen)
    got = perft(b, depth)
    assert got == expected, f"perft({name}, depth {depth}): expected {expected}, got {got}"
