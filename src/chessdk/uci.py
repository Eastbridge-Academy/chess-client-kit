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

import argparse
import sys
import traceback
from pathlib import Path
from typing import Callable, TextIO

from chessdk.fen import STARTING_FEN
from chessdk.squares import parse_square
from chessdk.types import BISHOP, KNIGHT, Move, QUEEN, ROOK, WHITE


DEFAULT_TIME_MS = 1000

_PROMO_CHARS = {"n": KNIGHT, "b": BISHOP, "r": ROOK, "q": QUEEN}


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
        for uci in tokens[i:]:
            move = parse_move(uci, board.legal_moves())
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
                board = _apply_position(line, board_cls)
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
    from chessdk.house import HOUSE_BOTS

    parser = argparse.ArgumentParser(
        prog="chess-bot-uci",
        description=(
            "Run a chess bot as a UCI engine on stdin/stdout. With no "
            "arguments, loads board.py and bot.py from the current "
            "working directory; with --house, runs a named built-in bot "
            "against the reference Board (no working-directory files needed)."
        ),
    )
    parser.add_argument(
        "--house",
        metavar="NAME",
        default=None,
        help=(
            "Run a built-in house bot instead of loading from cwd. "
            "Choices: " + ", ".join(sorted(HOUSE_BOTS)) + "."
        ),
    )
    args = parser.parse_args()

    if args.house is None:
        run()
        return

    if args.house not in HOUSE_BOTS:
        available = ", ".join(sorted(HOUSE_BOTS))
        print(
            f"chess-bot-uci: unknown house bot {args.house!r}; "
            f"choose from {available}",
            file=sys.stderr,
        )
        sys.exit(2)

    from chessdk.reference import Board

    run(board_cls=Board, choose_move=HOUSE_BOTS[args.house])


# -----------------------------------------------------------------------------
# Per-house-bot console entry points.
#
# Each house bot is also installed as its own ``chess-bot-<name>`` executable
# so that GUIs (cutechess-gui, Arena, Banksia, etc.) that expect a single
# command path without arguments can point at one of these directly. The
# function below builds one main() per bot and the pyproject.toml's
# [project.scripts] section maps each name to its entry point.
# -----------------------------------------------------------------------------


def _make_house_main(bot_name: str):
    def _main() -> None:
        from chessdk.house import HOUSE_BOTS
        from chessdk.reference import Board

        run(board_cls=Board, choose_move=HOUSE_BOTS[bot_name])

    _main.__name__ = f"main_{bot_name}"
    _main.__qualname__ = _main.__name__
    _main.__doc__ = f"UCI entry point for the {bot_name!r} house bot."
    return _main


main_materialist = _make_house_main("materialist")
main_knightmare = _make_house_main("knightmare")
main_edge_lord = _make_house_main("edge_lord")
main_crusader = _make_house_main("crusader")
main_hoarder = _make_house_main("hoarder")
main_magnus_mini = _make_house_main("magnus_mini")
main_tunnel_vision = _make_house_main("tunnel_vision")
main_greedy_gus = _make_house_main("greedy_gus")
main_random_legal = _make_house_main("random_legal")
main_always_captures = _make_house_main("always_captures")
main_hangs_pieces = _make_house_main("hangs_pieces")


if __name__ == "__main__":
    main()
