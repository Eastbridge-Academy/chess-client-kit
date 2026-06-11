"""Stage 23: quiescence resolves captures before the evaluator weighs in.

Using a material-only evaluator (so only the search is under test), we check:

  - In a quiet position with no captures available, quiescence returns the
    plain static score (the stand-pat baseline).
  - After a poisoned capture (a piece grabs a defended pawn), quiescence
    sees the recapture and scores the position near its true, bad value,
    well below the naive static count.
  - When a free capture is on offer, quiescence takes it and reflects the
    gain.
  - A depth-one search given a quiescent leaf evaluator declines the
    poisoned capture instead of walking into it.
"""

from __future__ import annotations

from board import Board
from chessdk import PIECE_VALUE_CLASSIC, MATE_SCORE, WHITE
from search import quiesce, search


def _material(board) -> int:
    total = 0
    for piece in board.pieces:
        if piece is None:
            continue
        sign = 1 if piece.color == WHITE else -1
        total += sign * PIECE_VALUE_CLASSIC[piece.kind]
    return total


# White is up a rook for two pawns. The only capture, Rxa5, loses the rook
# to b6xa5; a quiescence search must see through it.
HORIZON = "4k3/8/1p6/p7/8/8/8/R3K3 w - - 0 1"

# White queen can grab an undefended pawn on d7 for free.
FREE_PAWN = "7k/3p4/8/8/8/8/8/3QK3 w - - 0 1"

# A six-ply forced exchange on e5 (the handout's worked example): White's
# d4 pawn, Nf3 and Re1 contest the e5 pawn, which Black's d6 pawn, Nc6, Bg7
# and Re8 defend. If both sides keep capturing (1.dxe5 dxe5 2.Nxe5 Nxe5
# 3.Rxe5 Bxe5) the material swings +1, 0, +1, -2, +1, -4: every odd ply
# reads "White up a pawn" and every even ply reads level, so a fixed-depth
# search oscillates as it deepens and never settles until the captures
# resolve.
DEEP_EXCHANGE = "4r1k1/ppp2pbp/2np4/4p3/3P4/5N2/PPP2PPP/2B1R1K1 w - - 0 1"


def test_quiescence_in_quiet_position_equals_static():
    """No captures at the start, so quiescence is just the static score."""
    board = Board()
    assert quiesce(board, -MATE_SCORE, MATE_SCORE, _material) == _material(board)


def test_quiescence_sees_through_poisoned_capture():
    """After Rxa5 (Black to move), quiescence sees b6xa5 and scores the
    position at the resolved material (White has lost the rook for a pawn),
    not the naive +400 the static count would report."""
    board = Board.from_fen(HORIZON)
    rxa5 = next(m for m in board.legal_moves() if m.uci() == "a1a5")
    board.make_move(rxa5)
    naive = _material(board)  # +400: rook plus the grabbed pawn, recapture unseen
    resolved = quiesce(board, -MATE_SCORE, MATE_SCORE, _material)
    assert naive == 400
    assert resolved == -100, (
        f"quiescence scored the poisoned capture at {resolved}; after b6xa5 "
        f"White is down a rook for two pawns, which is -100"
    )
    assert resolved < naive


def test_quiescence_takes_free_material():
    """A free pawn is there for the taking; quiescence should grab it."""
    board = Board.from_fen(FREE_PAWN)
    stand_pat = _material(board)  # +800
    score = quiesce(board, -MATE_SCORE, MATE_SCORE, _material)
    assert score > stand_pat, "quiescence should take the free pawn on d7"
    assert score == 900


def test_search_declines_poisoned_capture():
    """Given a quiescent leaf evaluator, a depth-one search keeps its rook."""
    board = Board.from_fen(HORIZON)

    def quiescent_eval(b):
        return quiesce(b, -MATE_SCORE, MATE_SCORE, _material)

    score, move = search(board, 1, quiescent_eval)
    assert move.uci() != "a1a5", "search should not grab the poisoned pawn"
    assert score == 300, f"keeping the rook is worth +300, search reports {score}"


def test_quiescence_resolves_deep_exchange():
    """A six-ply forced exchange: a depth-3 search stops mid-chain (just
    after 2.Nxe5) and reads White up a pawn; quiescence plays the captures
    out and sees the exchange is level."""
    def quiescent_eval(b):
        return quiesce(b, -MATE_SCORE, MATE_SCORE, _material)

    plain, _ = search(Board.from_fen(DEEP_EXCHANGE), 3, _material)
    quiesced, _ = search(Board.from_fen(DEEP_EXCHANGE), 3, quiescent_eval)
    assert plain == 100, (
        f"a plain depth-3 search halts just after 2.Nxe5 and should read "
        f"exactly a pawn up (+100); got {plain}"
    )
    assert quiesced == 0, (
        f"with a quiescent leaf the same search resolves the exchange to "
        f"level (0); got {quiesced}"
    )
    assert quiesced < plain
