"""UCI (Universal Chess Interface) adapter.

Reads UCI commands from stdin, calls the student's `bot.choose_move` to pick
moves, writes responses to stdout. Run via the `chess-bot-uci` console script,
which loads `bot.py` and `board.py` from the current working directory.

UCI commands handled:

  uci          → id name / id author / uciok
  isready      → readyok
  ucinewgame   → reset internal board
  position     → load FEN or starting position, optionally apply moves
  go           → call choose_move, print bestmove
  quit         → exit cleanly

Other commands (`stop`, `setoption`, `debug`, ...) are accepted and silently
ignored; we don't run async search, so there is nothing to stop.
"""

from __future__ import annotations

import sys
import traceback
from pathlib import Path
from typing import Callable, TextIO

from chessdk.fen import STARTING_FEN
from chessdk.squares import parse_square
from chessdk.types import BISHOP, KNIGHT, Move, QUEEN, ROOK, WHITE


DEFAULT_TIME_MS = 1000

_PROMO_CHARS = {"n": KNIGHT, "b": BISHOP, "r": ROOK, "q": QUEEN}

# Stable marker for the fatal desync banner. The arena's match worker greps
# the engine's captured stderr for this string to classify the failure, so
# changing it requires a matching change in arena_worker/games/chess/engine.py.
DESYNC_MARKER = "GAME STATE DESYNC"


class GameDesyncError(Exception):
    """The game contains a move the student's board says is illegal.

    Raised during ``position`` replay when an actually-played game move
    cannot be resolved against the student board's ``legal_moves()``. That
    means the student's move generation disagrees with the real game: if we
    carried on, the board would silently stay at a stale position and every
    later ``go`` would compute a move for the wrong position (typically
    surfacing as a baffling "illegal move" loss several plies later).
    """


def _desync_report(board, uci: str, ply: int) -> str:
    """Build the student-facing explanation for a position-replay desync."""
    try:
        fen = board.to_fen()
    except Exception:  # noqa: BLE001 - a buggy board must not mask the report
        fen = "<your board's to_fen() raised an exception>"
    try:
        legal = " ".join(sorted(m.uci() for m in board.legal_moves()))
    except Exception:  # noqa: BLE001
        legal = "<your board's legal_moves() raised an exception>"
    return (
        f"Your board rejected the game move '{uci}' (ply {ply} of this game).\n"
        "That move was actually played in the game, so it is legal -- but your\n"
        "board's legal_moves() does not include it. Your move generation has\n"
        "diverged from the real game; continuing would mean playing from a\n"
        "stale, incorrect position, so the engine is stopping here instead.\n"
        "\n"
        "Position right before the rejected move (as your board sees it):\n"
        f"  FEN: {fen}\n"
        f"  your legal_moves(): {legal}\n"
        "\n"
        f"Debug tip: load this FEN into your Board and work out why '{uci}' is\n"
        "missing from legal_moves(). A common cause is an is_attacked() /\n"
        "check-detection bug that wrongly excludes a legal move."
    )


def parse_move(uci: str, legal_moves: list[Move]) -> Move:
    """Resolve a UCI move string against a list of legal moves.

    UCI gives us only `(from, to[, promotion])`; whether a move is castling
    or en passant is implicit. We look up the matching `Move` object in the
    legal-move list so the caller can hand it straight to `make_move`.
    """
    if len(uci) not in (4, 5):
        raise ValueError(f"bad UCI move {uci!r}")
    from_sq = parse_square(uci[0:2])
    to_sq = parse_square(uci[2:4])
    promotion = _PROMO_CHARS[uci[4].lower()] if len(uci) == 5 else None
    for m in legal_moves:
        if m.from_sq == from_sq and m.to_sq == to_sq and m.promotion == promotion:
            return m
    raise ValueError(f"move {uci!r} not in current legal moves")


def _load_student_modules(working_dir: Path) -> tuple[type, Callable]:
    """Import board.Board and bot.choose_move from the given working dir."""
    s = str(working_dir.resolve())
    if s not in sys.path:
        sys.path.insert(0, s)
    import board  # type: ignore  # noqa: I001
    import bot  # type: ignore

    return board.Board, bot.choose_move


def _apply_position(line: str, board_cls: type):
    tokens = line.split()
    i = 1  # skip "position"
    if i < len(tokens) and tokens[i] == "startpos":
        board = board_cls.from_fen(STARTING_FEN)
        i += 1
    elif i < len(tokens) and tokens[i] == "fen":
        i += 1
        if len(tokens) < i + 6:
            raise ValueError(f"position fen needs 6 fields: {line!r}")
        board = board_cls.from_fen(" ".join(tokens[i : i + 6]))
        i += 6
    else:
        raise ValueError(f"bad position command: {line!r}")

    if i < len(tokens) and tokens[i] == "moves":
        i += 1
        for ply, uci in enumerate(tokens[i:], start=1):
            try:
                move = parse_move(uci, board.legal_moves())
            except ValueError as exc:
                raise GameDesyncError(_desync_report(board, uci, ply)) from exc
            board.make_move(move)
    return board


def _parse_go_time(line: str, side_to_move) -> int:
    """Pick a reasonable `time_left_ms` to pass to choose_move."""
    tokens = line.split()
    wtime = btime = movetime = None
    i = 1
    while i < len(tokens):
        tok = tokens[i]
        if tok in ("wtime", "btime", "movetime", "winc", "binc", "depth", "nodes", "movestogo"):
            if i + 1 < len(tokens):
                value = int(tokens[i + 1])
                if tok == "wtime":
                    wtime = value
                elif tok == "btime":
                    btime = value
                elif tok == "movetime":
                    movetime = value
                i += 2
            else:
                i += 1
        else:
            i += 1
    if movetime is not None:
        return movetime
    if side_to_move == WHITE and wtime is not None:
        return wtime
    if btime is not None:
        return btime
    return DEFAULT_TIME_MS


def run(
    board_cls: type | None = None,
    choose_move: Callable | None = None,
    working_dir: Path | None = None,
    in_stream: TextIO | None = None,
    out_stream: TextIO | None = None,
) -> None:
    """Run the UCI loop until `quit` (or stdin closes).

    `board_cls` and `choose_move` may be provided directly (useful for
    tests); if either is missing, both are imported from `board.py` and
    `bot.py` in `working_dir` (default: cwd).
    """
    if in_stream is None:
        in_stream = sys.stdin
    if out_stream is None:
        out_stream = sys.stdout

    if board_cls is None or choose_move is None:
        if working_dir is None:
            working_dir = Path.cwd()
        loaded_board, loaded_choose = _load_student_modules(working_dir)
        if board_cls is None:
            board_cls = loaded_board
        if choose_move is None:
            choose_move = loaded_choose

    def emit(line: str) -> None:
        out_stream.write(line + "\n")
        out_stream.flush()

    board = board_cls.from_fen(STARTING_FEN)

    for raw in in_stream:
        line = raw.strip()
        if not line:
            continue
        try:
            if line == "uci":
                emit("id name eastbridge-bot")
                emit("id author Eastbridge")
                emit("uciok")
            elif line == "isready":
                emit("readyok")
            elif line == "ucinewgame":
                board = board_cls.from_fen(STARTING_FEN)
            elif line.startswith("position"):
                # A failed `position` is fatal. If we swallowed the error and
                # carried on (as `go` errors are), `board` would silently stay
                # at the *previous* position and every later move would be
                # computed from a stale board -- which the tournament server
                # then flags as an illegal move with no hint of the real cause.
                try:
                    board = _apply_position(line, board_cls)
                except GameDesyncError as exc:
                    banner = f"========== {DESYNC_MARKER} -- ENGINE STOPPING =========="
                    print(banner, file=sys.stderr)
                    print(str(exc), file=sys.stderr)
                    print("=" * len(banner), file=sys.stderr)
                    sys.stderr.flush()
                    raise SystemExit(70) from exc
                except Exception:
                    traceback.print_exc(file=sys.stderr)
                    print(
                        "fatal: applying the 'position' command failed (see above); "
                        "continuing would leave the engine playing from a stale "
                        "board, so it is stopping here.",
                        file=sys.stderr,
                    )
                    sys.stderr.flush()
                    raise SystemExit(70) from None
            elif line.startswith("go"):
                time_left_ms = _parse_go_time(line, board.side_to_move)
                move = choose_move(board, time_left_ms)
                emit(f"bestmove {move.uci()}")
            elif line == "quit":
                return
            elif line == "stop":
                pass  # we don't run async search
            # Silently ignore unknown commands (UCI convention).
        except Exception:
            # A crash inside the student's code shouldn't kill the loop;
            # surface the trace on stderr (visible in the GUI's engine log).
            traceback.print_exc(file=sys.stderr)
            sys.stderr.flush()


def main() -> None:
    run()


if __name__ == "__main__":
    main()
