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


def test_position_replay_desync_is_fatal(capsys):
    """A game move the board's legal_moves() rejects must kill the engine.

    If the loop swallowed the error (pre-0.3.3 behavior), the board would
    silently stay at the previous position and the bot would compute its
    next move from a stale board -- surfacing later as a baffling illegal
    move. Simulate a desync with a board whose legal_moves() wrongly omits
    a real move.
    """

    class StrictBoard(Board):
        def legal_moves(self):
            return [m for m in super().legal_moves() if m.uci() != "e2e4"]

    in_stream = io.StringIO("position startpos moves e2e4\ngo movetime 100\nquit\n")
    out_stream = io.StringIO()
    with pytest.raises(SystemExit) as excinfo:
        run(
            board_cls=StrictBoard,
            choose_move=random_legal,
            in_stream=in_stream,
            out_stream=out_stream,
        )
    assert excinfo.value.code == 70
    err = capsys.readouterr().err
    assert "GAME STATE DESYNC" in err
    assert "rejected the game move 'e2e4'" in err
    assert "FEN: rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1" in err
    assert "your legal_moves():" in err
    # No bestmove must have been emitted from the stale board.
    assert "bestmove" not in out_stream.getvalue()


def test_position_replay_failure_of_make_move_is_fatal(capsys):
    """Any other failure while applying `position` must also stop the engine."""

    class ExplodingBoard(Board):
        def make_move(self, move):
            raise RuntimeError("boom in make_move")

    in_stream = io.StringIO("position startpos moves e2e4\nquit\n")
    with pytest.raises(SystemExit) as excinfo:
        run(
            board_cls=ExplodingBoard,
            choose_move=random_legal,
            in_stream=in_stream,
            out_stream=io.StringIO(),
        )
    assert excinfo.value.code == 70
    err = capsys.readouterr().err
    assert "boom in make_move" in err
    assert "stale" in err


def test_go_crash_still_keeps_loop_alive():
    """`go`-time crashes keep the previous (still correct) board and loop."""

    def crashing(board, time_left_ms):
        raise RuntimeError("boom")

    in_stream = io.StringIO("position startpos\ngo movetime 100\nuci\nquit\n")
    out_stream = io.StringIO()
    run(
        board_cls=Board,
        choose_move=crashing,
        in_stream=in_stream,
        out_stream=out_stream,
    )
    assert "uciok" in out_stream.getvalue()
