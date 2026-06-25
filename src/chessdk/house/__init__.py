"""House bots — opponents shipped with the kit.

Each house bot is a function with the same signature as the student's
``choose_move(board, time_left_ms) -> Move``. The set is the local
mirror of the bots that sit on the tournament server's leaderboard at
``arena.eastbrid.ge``; running locally with ``chess-cli play --vs <bot>``
lets students iterate against the same opponents without round-tripping
through the network.

Phase 3 bots: ``random_legal``, ``always_captures``, ``hangs_pieces``.
Phase 4 bots: ``materialist``, ``knightmare``, ``edge_lord``, ``crusader``,
``hoarder``. (Their personalities and scoring functions are unchanged
since v0.4.0; only the search depth scales with the kit version. See
``courses/projects/chess-bot/CLAUDE.md`` for the rule.)
Phase 5 bots: ``magnus_mini``, ``tunnel_vision``, ``greedy_gus``.
Phase 7 bots: ``magnus_maximus`` (the final boss: tapered eval, transposition
table, killer/history ordering, deep iterative deepening).
"""

from __future__ import annotations

from chessdk.house.always_captures import choose_move as always_captures
from chessdk.house.crusader import choose_move as crusader
from chessdk.house.edge_lord import choose_move as edge_lord
from chessdk.house.greedy_gus import choose_move as greedy_gus
from chessdk.house.hangs_pieces import choose_move as hangs_pieces
from chessdk.house.hoarder import choose_move as hoarder
from chessdk.house.knightmare import choose_move as knightmare
from chessdk.house.magnus_maximus import choose_move as magnus_maximus
from chessdk.house.magnus_mini import choose_move as magnus_mini
from chessdk.house.materialist import choose_move as materialist
from chessdk.house.random_legal import choose_move as random_legal
from chessdk.house.tunnel_vision import choose_move as tunnel_vision


HOUSE_BOTS = {
    "random_legal": random_legal,
    "always_captures": always_captures,
    "hangs_pieces": hangs_pieces,
    "materialist": materialist,
    "knightmare": knightmare,
    "edge_lord": edge_lord,
    "crusader": crusader,
    "hoarder": hoarder,
    "magnus_mini": magnus_mini,
    "tunnel_vision": tunnel_vision,
    "greedy_gus": greedy_gus,
    "magnus_maximus": magnus_maximus,
}


__all__ = [
    "HOUSE_BOTS",
    "always_captures",
    "crusader",
    "edge_lord",
    "greedy_gus",
    "hangs_pieces",
    "hoarder",
    "knightmare",
    "magnus_maximus",
    "magnus_mini",
    "materialist",
    "random_legal",
    "tunnel_vision",
]
