"""End-to-end tests for chessdk.uci against the reference Board."""

from __future__ import annotations

import io

import pytest

from chessdk.fen import STARTING_FEN
from chessdk.house import always_captures, random_legal
from chessdk.reference import Board
from chessdk.uci import _apply_position, _parse_go_time, parse_move, run
from chessdk.types import BLACK, KNIGHT, QUEEN, WHITE


def drive(commands: list[str], choose_move) -> list[str]:
    """Feed `commands` (one per line) to the UCI loop and collect output."""
    in_stream = io.StringIO("\n".join(commands) + "\n")
    out_stream = io.StringIO()
    run(
        board_cls=Board,
        choose_move=choose_move,
        in_stream=in_stream,
        out_stream=out_stream,
    )
    return out_stream.getvalue().splitlines()


def test_uci_handshake():
    out = drive(["uci", "isready", "quit"], random_legal)
    assert "uciok" in out
    assert "readyok" in out
    assert any(line.startswith("id name") for line in out)


def test_position_startpos_then_go():
    out = drive(
        ["position startpos", "go wtime 1000 btime 1000", "quit"], random_legal
    )
    bestmoves = [line for line in out if line.startswith("bestmove ")]
    assert len(bestmoves) == 1
    move_uci = bestmoves[0].split()[1]
    # Must be one of White's 20 opening moves.
    assert len(move_uci) == 4
    assert move_uci[:2] in {f"{f}{r}" for f in "abcdefgh" for r in "12"}


def test_position_with_moves_advances_state():
    out = drive(
        [
            "position startpos moves e2e4 e7e5",
            "go movetime 100",
            "quit",
        ],
        random_legal,
    )
    bestmoves = [line for line in out if line.startswith("bestmove ")]
    assert len(bestmoves) == 1
    # White's second move; valid second moves don't include e2e4 (pawn now on e4)
    move_uci = bestmoves[0].split()[1]
    assert move_uci != "e2e4"


def test_position_fen():
    # Black to move, only legal move is to recapture
    fen = "rnbqkbnr/pppp1ppp/8/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R b KQkq - 1 2"
    out = drive(
        [f"position fen {fen}", "go movetime 100", "quit"], always_captures
    )
    bestmoves = [line for line in out if line.startswith("bestmove ")]
    assert len(bestmoves) == 1


def test_unknown_commands_are_ignored():
    out = drive(
        [
            "debug on",
            "setoption name Hash value 16",
            "stop",
            "uci",
            "quit",
        ],
        random_legal,
    )
    assert "uciok" in out


def test_quit_terminates_loop_immediately():
    out = drive(["quit", "uci"], random_legal)
    # We should never have processed the post-quit `uci`.
    assert "uciok" not in out


def test_bot_exception_does_not_crash_loop():
    def crashing(board, time_left_ms):
        raise RuntimeError("boom")

    out = drive(
        [
            "position startpos",
            "go movetime 100",
            "uci",
            "quit",
        ],
        crashing,
    )
    # The bot crashed, so no bestmove for the first go, but the loop
    # survived and processed the subsequent `uci`.
    assert "uciok" in out


def test_apply_position_startpos():
    board = _apply_position("position startpos", Board)
    assert board.to_fen() == STARTING_FEN


def test_apply_position_fen_with_moves():
    fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    board = _apply_position(f"position fen {fen} moves e2e4 e7e5 g1f3", Board)
    # White just played Nf3; black to move, knight on f3.
    from chessdk.squares import parse_square
    f3 = parse_square("f3")
    piece = board.piece_at(f3)
    assert piece is not None and piece.kind == KNIGHT and piece.color == WHITE


def test_parse_move_resolves_promotion():
    # White pawn on e7, ready to promote.
    fen = "8/4P3/8/8/8/8/8/k6K w - - 0 1"
    board = Board.from_fen(fen)
    move = parse_move("e7e8q", board.legal_moves())
    assert move.promotion == QUEEN


def test_parse_move_rejects_illegal():
    board = Board.from_fen(STARTING_FEN)
    with pytest.raises(ValueError):
        parse_move("e2e5", board.legal_moves())  # pawn can't jump 3


def test_parse_go_time_prefers_movetime():
    assert _parse_go_time("go wtime 60000 btime 60000 movetime 5000", WHITE) == 5000


def test_parse_go_time_uses_side_clock():
    assert _parse_go_time("go wtime 30000 btime 25000", WHITE) == 30000
    assert _parse_go_time("go wtime 30000 btime 25000", BLACK) == 25000


def test_parse_go_time_default_when_missing():
    assert _parse_go_time("go infinite", WHITE) == 1000
