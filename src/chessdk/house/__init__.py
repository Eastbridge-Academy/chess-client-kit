"""House bots — opponents shipped with the kit.

Each house bot is a function with the same signature as the student's
`choose_move(board, time_left_ms) -> Move`. The set is the local mirror of
the bots that sit on the tournament server's leaderboard at
`arena.eastbrid.ge`; running locally with `chess-cli play --vs <bot>` lets
students iterate against the same opponents without round-tripping through
the network.
"""

from __future__ import annotations

from chessdk.house.always_captures import choose_move as always_captures
from chessdk.house.hangs_pieces import choose_move as hangs_pieces
from chessdk.house.random_legal import choose_move as random_legal


HOUSE_BOTS = {
    "random_legal": random_legal,
    "always_captures": always_captures,
    "hangs_pieces": hangs_pieces,
}


__all__ = ["HOUSE_BOTS", "always_captures", "hangs_pieces", "random_legal"]
