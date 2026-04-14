"""Shared pytest fixtures and helpers."""

from __future__ import annotations

import pytest

from board import Board
from chessdk import BLACK, Move, WHITE


@pytest.fixture
def board_factory():
    """Returns a function that builds a Board from a FEN string."""
    return Board.from_fen


def uci_set(moves: list[Move]) -> set[str]:
    """Collect a list of Move objects into a set of UCI strings."""
    return {m.uci() for m in moves}
