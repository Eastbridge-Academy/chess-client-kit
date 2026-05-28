"""Stage 19: ``order_moves`` puts captures first and uses MVV-LVA inside.

We verify two properties on a position with several captures of different
value:

  - Every capture in the ordered list appears before every quiet move.
  - Among captures, the order is most-valuable-victim first, with the
    least-valuable-attacker breaking ties on the same victim.

The reference returns a new list and leaves the input unmodified; the
test does not require students to follow that convention strictly, but
their ``search`` does need the ordered output regardless.
"""

from __future__ import annotations

from board import Board
from chessdk import PIECE_VALUE_CLASSIC
from search import order_moves


# A position with multiple captures of varying victim value: White can
# capture a black queen, a black knight, or a black pawn, with different
# attacker pieces. The order_moves helper should put these in MVV-LVA
# order regardless of the order legal_moves returns them in.
RICH_CAPTURE_FEN = "rnb1kb1r/pp3ppp/2p2n2/q2pp3/Q2PP3/2P2N2/PP3PPP/RNB1KB1R w KQkq - 0 1"


def _is_capture(board, move) -> bool:
    return board.piece_at(move.to_sq) is not None


def test_captures_come_before_quiet_moves():
    board = Board.from_fen(RICH_CAPTURE_FEN)
    ordered = order_moves(board, board.legal_moves())
    seen_quiet = False
    for move in ordered:
        if not _is_capture(board, move):
            seen_quiet = True
        elif seen_quiet:
            quiet_before = [m.uci() for m in ordered if not _is_capture(board, m)]
            raise AssertionError(
                f"capture {move.uci()} came after a quiet move "
                f"({quiet_before[0]} appeared first)"
            )


def test_captures_are_ordered_by_mvv():
    """Among captures, victims of higher value come first."""
    board = Board.from_fen(RICH_CAPTURE_FEN)
    ordered = order_moves(board, board.legal_moves())
    captures = [m for m in ordered if _is_capture(board, m)]
    victim_values = [
        PIECE_VALUE_CLASSIC[board.piece_at(m.to_sq).kind] for m in captures
    ]
    assert victim_values == sorted(victim_values, reverse=True), (
        f"capture victims out of MVV order: {victim_values}"
    )


def test_mvv_lva_breaks_ties_with_least_valuable_attacker():
    """When two captures take the same victim, the cheapest attacker
    should come first (pawn-takes-queen before queen-takes-queen, etc.)."""
    # Position where both a white pawn and a white knight attack the
    # black pawn on d5. The pawn-attacker should come before the
    # knight-attacker in the ordering.
    fen = "rnbqkbnr/ppp1pppp/8/3p4/2P5/2N5/PP1PPPPP/R1BQKBNR w KQkq d6 0 2"
    board = Board.from_fen(fen)
    ordered = order_moves(board, board.legal_moves())
    captures = [m for m in ordered if _is_capture(board, m)]
    d5_captures = [m for m in captures if board.piece_at(m.to_sq).kind.name == "PAWN"]
    if len(d5_captures) >= 2:
        first_attacker = board.piece_at(d5_captures[0].from_sq).kind
        second_attacker = board.piece_at(d5_captures[1].from_sq).kind
        assert PIECE_VALUE_CLASSIC[first_attacker] <= PIECE_VALUE_CLASSIC[second_attacker], (
            f"MVV-LVA violation: first capture's attacker "
            f"({first_attacker.name}) is more valuable than the second's "
            f"({second_attacker.name})"
        )
