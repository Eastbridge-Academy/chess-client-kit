"""Stage 27: a transposition table built on the hash counts perft correctly.

A perft (count every leaf of the move tree to some depth) that memoises its
counts by ``(zobrist_hash, depth)`` must give exactly the same totals as a
plain perft. If it does, the hash is a sound dictionary key: positions that
are really the same collapse together, and positions that differ do not
collide into a wrong count. This is the catch-all correctness floor for the
table, and it also catches a hash that forgets a feature (drop the en-passant
keys, say, and two positions with different legal moves would share a count).
"""

from __future__ import annotations

import pytest

from board import Board


def _plain_perft(board, depth):
    if depth == 0:
        return 1
    total = 0
    for move in board.legal_moves():
        board.make_move(move)
        total += _plain_perft(board, depth - 1)
        board.undo_move()
    return total


def _tt_perft(board, depth, tt):
    if depth == 0:
        return 1
    key = (board.zobrist_hash(), depth)
    if key in tt:
        return tt[key]
    total = 0
    for move in board.legal_moves():
        board.make_move(move)
        total += _tt_perft(board, depth - 1, tt)
        board.undo_move()
    tt[key] = total
    return total


CASES = [
    ("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", 3),
    ("r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 0 1", 3),
    ("r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1", 3),
]


@pytest.mark.parametrize("fen,depth", CASES)
def test_tt_perft_equals_plain_perft(fen, depth):
    plain = _plain_perft(Board.from_fen(fen), depth)
    memoised = _tt_perft(Board.from_fen(fen), depth, {})
    assert memoised == plain
