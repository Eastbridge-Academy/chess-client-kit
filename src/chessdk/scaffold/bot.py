"""Your bot.

``choose_move`` is what the UCI loop calls every time it's your turn to play.
It receives the current ``Board`` and the remaining clock time in milliseconds,
and must return one of the legal moves on the board.

For Phases 1 and 2 this function is unused. Phase 3 wires it up and submits
to the tournament. Phase 4 rebuilds it around an evaluation function (see
``evaluation.py``). Phase 5 wraps that evaluator in a search (see
``search.py``) so the bot can look several plies ahead, which makes the
hang-detection stopgap from Phase 4 redundant; this is the phase where
you get to delete that code.
"""

from __future__ import annotations

from board import Board
from chessdk import Move


def choose_move(board: Board, time_left_ms: int) -> Move:
    """Return the move your bot wants to play, given the current board."""
    raise NotImplementedError("choose_move: implement in Phase 3 (Stage 9)")
