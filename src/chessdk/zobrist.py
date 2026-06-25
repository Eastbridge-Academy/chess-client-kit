"""Zobrist hashing: a fixed table of random keys for naming chess positions.

A position's hash is the XOR of one key per feature present: a key for each
(piece, square), one for side-to-move, one per castling right, and one per
en-passant file. Two positions reached by different move orders get the same
hash precisely when they are the same position, which is what lets a search
recognise transpositions and reuse work.

The key table is generated once from a fixed seed, so the same position always
hashes to the same value, on every machine and in both the student's board and
the reference board. That reproducibility is the point: it makes a student's
hash directly comparable to the reference for debugging, and lets tests pin
exact values.

The hash deliberately excludes the halfmove and fullmove clocks: two positions
that differ only in those counters are the same position for search purposes.
It does include the en-passant file, because a pawn that can be captured en
passant genuinely makes for a different position.
"""

from __future__ import annotations

import random

from chessdk.squares import file_of
from chessdk.types import WHITE


# A fixed seed freezes the key table. Python's Mersenne-Twister stream is stable
# across versions for getrandbits, so these keys are the same everywhere.
_SEED = 0xC0FFEE_1A7E
_rng = random.Random(_SEED)


def _key() -> int:
    return _rng.getrandbits(64)


# PIECE_KEYS[color * 6 + kind][square] -- 12 piece types x 64 squares.
PIECE_KEYS: list[list[int]] = [[_key() for _ in range(64)] for _ in range(12)]
# XOR this in when it is Black to move (White-to-move is the baseline).
SIDE_KEY: int = _key()
# One per castling right, in the order [WK, WQ, BK, BQ].
CASTLE_KEYS: list[int] = [_key() for _ in range(4)]
# One per file (a..h) of the en-passant target square, when one is set.
EP_FILE_KEYS: list[int] = [_key() for _ in range(8)]


def zobrist_hash(board) -> int:
    """Compute a position's Zobrist hash from scratch.

    Reads the board's current state directly, so it is always correct; an
    incremental version that updates the hash on make/undo is a speed
    optimisation built on top of this, not a replacement for it.
    """
    state = board.state
    h = 0
    for square, piece in enumerate(state.pieces):
        if piece is not None:
            h ^= PIECE_KEYS[piece.color * 6 + piece.kind][square]
    if state.side_to_move != WHITE:
        h ^= SIDE_KEY
    castling = state.castling
    if castling.white_kingside:
        h ^= CASTLE_KEYS[0]
    if castling.white_queenside:
        h ^= CASTLE_KEYS[1]
    if castling.black_kingside:
        h ^= CASTLE_KEYS[2]
    if castling.black_queenside:
        h ^= CASTLE_KEYS[3]
    if state.en_passant is not None:
        h ^= EP_FILE_KEYS[file_of(state.en_passant)]
    return h
