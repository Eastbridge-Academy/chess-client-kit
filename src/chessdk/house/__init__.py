"""House bots — opponents shipped with the kit.

Each house bot is a function with the same signature as the student's
``choose_move(board, time_left_ms) -> Move``. The set is the local mirror
of the bots that sit on the tournament server's leaderboard at
``arena.eastbrid.ge``; running locally with ``chess-cli play --vs <bot>``
lets students iterate against the same opponents without round-tripping
through the network.

Phase 3 bots: ``random_legal``, ``always_captures``, ``hangs_pieces``.
Phase 4 bots: ``materialist``, ``knightmare``, ``edge_lord``, ``crusader``,
``hoarder``.
"""

from __future__ import annotations

from chessdk.house.always_captures import choose_move as always_captures
from chessdk.house.crusader import choose_move as crusader
from chessdk.house.edge_lord import choose_move as edge_lord
from chessdk.house.hangs_pieces import choose_move as hangs_pieces
from chessdk.house.hoarder import choose_move as hoarder
from chessdk.house.knightmare import choose_move as knightmare
from chessdk.house.materialist import choose_move as materialist
from chessdk.house.random_legal import choose_move as random_legal


HOUSE_BOTS = {
    "random_legal": random_legal,
    "always_captures": always_captures,
    "hangs_pieces": hangs_pieces,
    "materialist": materialist,
    "knightmare": knightmare,
    "edge_lord": edge_lord,
    "crusader": crusader,
    "hoarder": hoarder,
}


__all__ = [
    "HOUSE_BOTS",
    "always_captures",
    "crusader",
    "edge_lord",
    "hangs_pieces",
    "hoarder",
    "knightmare",
    "materialist",
    "random_legal",
]
