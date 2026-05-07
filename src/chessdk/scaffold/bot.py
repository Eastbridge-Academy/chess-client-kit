"""Your bot.

`choose_move` is what the UCI loop calls every time it's your turn to play.
It receives the current `Board` and the remaining clock time in milliseconds,
and must return one of the legal moves on the board.

For Week 1 and Week 2 this function is unused. Week 3 wires it up and starts
submitting your bot to the tournament.
"""

from __future__ import annotations

from board import Board
from chessdk import Move


def choose_move(board: Board, time_left_ms: int) -> Move:
    """Return the move your bot wants to play, given the current board."""
    raise NotImplementedError("choose_move: implement in Week 3 (Stage 9)")
