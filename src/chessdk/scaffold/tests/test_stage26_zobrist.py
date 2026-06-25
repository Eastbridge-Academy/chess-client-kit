"""Stage 26: Zobrist hashing.

A position's hash has to name the position: the same number for the same
position however you reach it, and (almost surely) a different number for a
different one. We check the student's ``board.zobrist_hash()`` against the
kit's reference hash, that it round-trips through make/undo, that transposing
move orders agree, that the en-passant difference is respected, and that the
side to move and castling rights change it.
"""

from __future__ import annotations

import pytest

from board import Board
from chessdk import parse_square
from chessdk.zobrist import zobrist_hash as reference_hash

STARTPOS = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"


def _play(moves: str) -> Board:
    """Apply a sequence of UCI moves from the starting position."""
    board = Board.from_fen(STARTPOS)
    for uci in moves.split():
        frm, to = parse_square(uci[0:2]), parse_square(uci[2:4])
        promo = uci[4] if len(uci) == 5 else None
        for move in board.legal_moves():
            same_squares = move.from_sq == frm and move.to_sq == to
            same_promo = (promo is None) == (move.promotion is None) and (
                promo is None or move.uci()[-1] == promo
            )
            if same_squares and same_promo:
                board.make_move(move)
                break
        else:
            raise AssertionError(f"illegal move {uci!r} in {moves!r}")
    return board


FENS = [
    STARTPOS,
    "r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 0 1",
    "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1",
    "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1",
    "rnbqkbnr/ppp1pppp/8/3p4/4P3/8/PPPP1PPP/RNBQKBNR w KQkq d6 0 2",
]


@pytest.mark.parametrize("fen", FENS)
def test_matches_reference(fen):
    board = Board.from_fen(fen)
    assert board.zobrist_hash() == reference_hash(board)


@pytest.mark.parametrize("fen", FENS)
def test_round_trips_through_make_undo(fen):
    board = Board.from_fen(fen)
    before = board.zobrist_hash()
    for move in board.legal_moves():
        board.make_move(move)
        board.undo_move()
        assert board.zobrist_hash() == before


def test_transposing_move_orders_agree():
    a = _play("g1f3 g8f6 b1c3 b8c6")   # 1.Nf3 Nf6 2.Nc3 Nc6
    b = _play("b1c3 b8c6 g1f3 g8f6")   # 1.Nc3 Nc6 2.Nf3 Nf6
    assert a.to_fen() == b.to_fen()                # sanity: truly the same position
    assert a.zobrist_hash() == b.zobrist_hash()


def test_en_passant_makes_a_different_position():
    # 1.e4 e5 2.Nf3 ends on a knight move (no en passant available); 1.Nf3 e5
    # 2.e4 ends on the double push, so Black may capture en passant. These are
    # different positions and must hash differently.
    no_ep = _play("e2e4 e7e5 g1f3")
    ep = _play("g1f3 e7e5 e2e4")
    assert no_ep.zobrist_hash() != ep.zobrist_hash()


def test_side_to_move_changes_the_hash():
    board = Board.from_fen(STARTPOS)
    before = board.zobrist_hash()
    board.state.side_to_move = board.state.side_to_move.other
    assert board.zobrist_hash() != before


def test_castling_rights_change_the_hash():
    full = Board.from_fen("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1")
    fewer = Board.from_fen("r3k2r/8/8/8/8/8/8/R3K2R w Kkq - 0 1")
    assert full.zobrist_hash() != fewer.zobrist_hash()
