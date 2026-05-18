"""chess-cli: student-facing command-line tool.

Subcommands:

  init       Drop scaffold files (board.py, bot.py, tests/) into the current directory.
  test       Run pytest on your tests.
  perft N    Count moves from a position at depth N (optional --fen, --divide).
  config     Get/set values in a per-project config file.
  info       Show current config and environment info.
  play       Play one or more games against a built-in house bot.
  submit     Upload your bot to the tournament server.
"""

from __future__ import annotations

import json
import subprocess
import sys
from importlib import resources
from pathlib import Path

import click


CONFIG_FILE = ".chess-cli.json"


def load_config() -> dict:
    p = Path(CONFIG_FILE)
    if not p.exists():
        return {}
    return json.loads(p.read_text())


def save_config(cfg: dict) -> None:
    Path(CONFIG_FILE).write_text(json.dumps(cfg, indent=2) + "\n")


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
def main() -> None:
    """Eastbridge chess-bot student CLI."""


# -----------------------------------------------------------------------------
# init
# -----------------------------------------------------------------------------

@main.command()
@click.option("--force", is_flag=True, help="Overwrite existing scaffold files.")
def init(force: bool) -> None:
    """Drop scaffold files (board.py, bot.py, tests/) into the current directory."""
    scaffold_root = resources.files("chessdk").joinpath("scaffold")
    targets = [
        ("board.py", scaffold_root / "board.py"),
        ("bot.py", scaffold_root / "bot.py"),
    ]
    for name, src in targets:
        dest = Path(name)
        if dest.exists() and not force:
            click.echo(f"skipping {name} (already exists; use --force to overwrite)")
            continue
        dest.write_text(src.read_text())
        click.echo(f"wrote {name}")

    tests_dir = Path("tests")
    tests_src = scaffold_root / "tests"
    tests_dir.mkdir(exist_ok=True)
    for child in tests_src.iterdir():
        if child.name == "__pycache__":
            continue
        dest = tests_dir / child.name
        if dest.exists() and not force:
            click.echo(f"skipping tests/{child.name} (already exists; use --force)")
            continue
        dest.write_text(child.read_text())
        click.echo(f"wrote tests/{child.name}")

    # Ensure tests/ is importable as a package so conftest.py is picked up
    # (pytest will handle this automatically, but we also add an empty __init__.py).
    init_file = tests_dir / "__init__.py"
    if not init_file.exists():
        init_file.write_text("")

    click.echo("\nNext: edit board.py, then run `chess-cli test` to see the test suite.")


# -----------------------------------------------------------------------------
# test
# -----------------------------------------------------------------------------

@main.command(context_settings={"ignore_unknown_options": True})
@click.argument("pytest_args", nargs=-1, type=click.UNPROCESSED)
def test(pytest_args: tuple[str, ...]) -> None:
    """Run pytest on your tests (extra args are forwarded to pytest)."""
    if not Path("tests").exists():
        click.echo("No tests/ directory found. Run `chess-cli init` first.", err=True)
        sys.exit(2)
    cmd = [sys.executable, "-m", "pytest", "tests", *pytest_args]
    result = subprocess.run(cmd)
    sys.exit(result.returncode)


# -----------------------------------------------------------------------------
# perft
# -----------------------------------------------------------------------------

def _perft(board, depth: int) -> int:
    """Count leaves in the legal-move tree at depth `depth`.

    Uses the student's `legal_moves`/`make_move`/`undo_move` (Phase 2+).
    """
    if depth == 0:
        return 1
    total = 0
    for move in board.legal_moves():
        board.make_move(move)
        total += _perft(board, depth - 1)
        board.undo_move()
    return total


def _perft_divide(board, depth: int) -> dict[str, int]:
    """For each root legal move, return its subtree perft(depth - 1) count."""
    counts: dict[str, int] = {}
    if depth <= 0:
        return counts
    for move in board.legal_moves():
        board.make_move(move)
        counts[move.uci()] = _perft(board, depth - 1)
        board.undo_move()
    return counts


@main.command()
@click.argument("depth", type=int)
@click.option("--fen", default=None, help="FEN string (defaults to the starting position).")
@click.option("--divide", is_flag=True, help="Print per-root-move counts and compare against the reference.")
def perft(depth: int, fen: str | None, divide: bool) -> None:
    """Count legal moves from a position at the given depth."""
    cwd = Path.cwd().resolve()
    if str(cwd) not in sys.path:
        sys.path.insert(0, str(cwd))
    try:
        from board import Board as StudentBoard  # type: ignore
    except Exception as e:
        raise click.ClickException(f"Could not import Board from board.py: {e}")

    fen = fen or "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    student_board = StudentBoard.from_fen(fen)

    if divide:
        from chessdk.reference import Board as RefBoard

        ref_board = RefBoard.from_fen(fen)
        try:
            student_counts = _perft_divide(student_board, depth)
        except NotImplementedError as e:
            raise click.ClickException(f"board.py raised NotImplementedError: {e}")
        ref_counts = _perft_divide(ref_board, depth)

        student_total = sum(student_counts.values())
        ref_total = sum(ref_counts.values())
        all_moves = sorted(set(student_counts) | set(ref_counts))

        any_diff = False
        click.echo(f"{'move':<8} {'you':>10} {'ref':>10}  status")
        for u in all_moves:
            you = student_counts.get(u, 0)
            ref = ref_counts.get(u, 0)
            if u in student_counts and u in ref_counts and you == ref:
                status = click.style("ok", fg="green")
            elif u not in student_counts:
                status = click.style("missing", fg="red")
                any_diff = True
            elif u not in ref_counts:
                status = click.style("extra", fg="yellow")
                any_diff = True
            else:
                status = click.style(f"diff {you - ref:+d}", fg="red")
                any_diff = True
            click.echo(f"{u:<8} {you:>10} {ref:>10}  {status}")
        click.echo(f"{'TOTAL':<8} {student_total:>10} {ref_total:>10}")
        if any_diff or student_total != ref_total:
            click.echo(click.style("MISMATCH", fg="red"))
            sys.exit(1)
        click.echo(click.style("Match!", fg="green"))
        sys.exit(0)

    try:
        count = _perft(student_board, depth)
    except NotImplementedError as e:
        raise click.ClickException(f"board.py raised NotImplementedError: {e}")
    click.echo(count)


# -----------------------------------------------------------------------------
# config
# -----------------------------------------------------------------------------

@main.group()
def config() -> None:
    """Get/set project-local configuration."""


@config.command("set")
@click.argument("key")
@click.argument("value")
def config_set(key: str, value: str) -> None:
    cfg = load_config()
    cfg[key] = value
    save_config(cfg)
    click.echo(f"set {key} = {value}")


@config.command("get")
@click.argument("key")
def config_get(key: str) -> None:
    cfg = load_config()
    if key not in cfg:
        click.echo(f"(not set)")
        sys.exit(1)
    click.echo(cfg[key])


# -----------------------------------------------------------------------------
# info
# -----------------------------------------------------------------------------

@main.command()
def info() -> None:
    """Show config and environment info."""
    cfg = load_config()
    click.echo("Config:")
    if cfg:
        for k, v in cfg.items():
            display = "***" if "token" in k.lower() else v
            click.echo(f"  {k} = {display}")
    else:
        click.echo("  (empty)")
    click.echo(f"\nPython: {sys.version.split()[0]}")
    click.echo(f"Working dir: {Path.cwd()}")
    click.echo(f"board.py present: {Path('board.py').exists()}")
    click.echo(f"bot.py present: {Path('bot.py').exists()}")
    click.echo(f"tests/ present: {Path('tests').is_dir()}")


# -----------------------------------------------------------------------------
# play
# -----------------------------------------------------------------------------

def _add_cwd_to_path() -> None:
    cwd = Path.cwd().resolve()
    if str(cwd) not in sys.path:
        sys.path.insert(0, str(cwd))


def _import_student_board():
    _add_cwd_to_path()
    try:
        from board import Board as StudentBoard  # type: ignore
    except Exception as e:
        raise click.ClickException(f"Could not import Board from board.py: {e}")
    return StudentBoard


def _import_student_choose_move():
    _add_cwd_to_path()
    try:
        from bot import choose_move  # type: ignore
    except Exception as e:
        raise click.ClickException(f"Could not import choose_move from bot.py: {e}")
    return choose_move


def _play_one_game(board_cls, white_fn, black_fn, time_ms: int, max_plies: int):
    """Play one game; return (result_str, move_list, final_fen).

    `result_str` is in PGN/UCI form: "1-0", "0-1", "1/2-1/2".
    """
    from chessdk.fen import STARTING_FEN
    from chessdk.types import WHITE

    board = board_cls.from_fen(STARTING_FEN)
    moves: list[str] = []
    for _ in range(max_plies):
        legal = board.legal_moves()
        if not legal:
            if board.is_in_check():
                result = "0-1" if board.side_to_move == WHITE else "1-0"
            else:
                result = "1/2-1/2"
            return result, moves, board.to_fen()
        if board.state.halfmove_clock >= 100:
            return "1/2-1/2", moves, board.to_fen()
        pick = white_fn if board.side_to_move == WHITE else black_fn
        move = pick(board, time_ms)
        if move not in legal:
            mover = "white" if board.side_to_move == WHITE else "black"
            raise click.ClickException(
                f"{mover} bot returned an illegal move {move.uci()!r} on "
                f"FEN {board.to_fen()!r}"
            )
        board.make_move(move)
        moves.append(move.uci())
    return "1/2-1/2", moves, board.to_fen()


@main.command()
@click.option(
    "--vs",
    "opponent",
    default="random_legal",
    show_default=True,
    help="Built-in house bot to play against. Use --list-opponents to see the choices.",
)
@click.option("-n", "--games", default=1, show_default=True, type=int)
@click.option(
    "--time-ms",
    default=1000,
    show_default=True,
    type=int,
    help="time_left_ms argument passed to choose_move on every call.",
)
@click.option(
    "--max-plies",
    default=500,
    show_default=True,
    type=int,
    help="Cap each game at this many plies; if reached, the game is declared a draw.",
)
@click.option("--seed", default=None, type=int, help="Seed the house bot RNG for reproducibility.")
@click.option("--quiet", is_flag=True, help="Suppress per-game output.")
@click.option("--show-moves", is_flag=True, help="Print the move list of the last game.")
@click.option("--list-opponents", is_flag=True, help="List available house bots and exit.")
def play(
    opponent: str,
    games: int,
    time_ms: int,
    max_plies: int,
    seed: int | None,
    quiet: bool,
    show_moves: bool,
    list_opponents: bool,
) -> None:
    """Play one or more games of student bot vs a house bot.

    Colors alternate game-by-game. A summary tally is printed at the end from
    the student's perspective (W/L/D).
    """
    from chessdk.house import HOUSE_BOTS

    if list_opponents:
        for name in HOUSE_BOTS:
            click.echo(name)
        return

    if opponent not in HOUSE_BOTS:
        raise click.ClickException(
            f"unknown opponent {opponent!r}; choose from "
            f"{', '.join(sorted(HOUSE_BOTS))} (or pass --list-opponents)"
        )

    if seed is not None:
        for fn in HOUSE_BOTS.values():
            module = sys.modules[fn.__module__]
            if hasattr(module, "_rng"):
                module._rng.seed(seed)

    board_cls = _import_student_board()
    student_choose = _import_student_choose_move()
    house_choose = HOUSE_BOTS[opponent]

    student_w = student_l = student_d = 0
    last_moves: list[str] = []
    last_fen = ""

    for g in range(games):
        student_is_white = (g % 2) == 0
        if student_is_white:
            white_fn, black_fn = student_choose, house_choose
        else:
            white_fn, black_fn = house_choose, student_choose

        try:
            result, last_moves, last_fen = _play_one_game(
                board_cls, white_fn, black_fn, time_ms, max_plies
            )
        except click.ClickException:
            raise
        except Exception as e:
            raise click.ClickException(
                f"game {g + 1} crashed: {type(e).__name__}: {e}"
            )

        if result == "1/2-1/2":
            student_d += 1
            outcome = "draw"
        elif (result == "1-0") == student_is_white:
            student_w += 1
            outcome = "WIN"
        else:
            student_l += 1
            outcome = "loss"

        if not quiet:
            color_label = "white" if student_is_white else "black"
            click.echo(
                f"game {g + 1}/{games}  you={color_label:5s}  "
                f"result={result:7s}  {outcome}"
            )

    click.echo(
        f"\nvs {opponent}: "
        f"{click.style(str(student_w) + 'W', fg='green')} "
        f"{click.style(str(student_l) + 'L', fg='red')} "
        f"{click.style(str(student_d) + 'D', fg='yellow')} "
        f"out of {games}"
    )

    if show_moves and last_moves:
        click.echo("\nlast game moves:")
        click.echo(" ".join(last_moves))
        click.echo(f"final FEN: {last_fen}")


# -----------------------------------------------------------------------------
# submit
# -----------------------------------------------------------------------------

@main.command()
@click.argument("team_name", required=True)
@click.option("--email", default=None, help="Optional contact email.")
@click.option("--bot-file", default="bot.py", show_default=True)
@click.option(
    "--board-file",
    default="board.py",
    show_default=True,
    help="Your Board implementation, uploaded alongside bot.py.",
)
def submit(team_name: str, email: str | None, bot_file: str, board_file: str) -> None:
    """Upload your bot to the tournament server.

    Reads `api_url` and `token` from `.chess-cli.json` in the current
    directory. Both files (`bot.py` and `board.py`) are sent so the server
    can run your bot end-to-end.
    """
    import requests

    cfg = load_config()
    api_url = cfg.get("api_url")
    token = cfg.get("token")
    if not api_url:
        raise click.ClickException(
            "api_url is not set. Run `chess-cli config set api_url <URL>` first."
        )
    if not token:
        raise click.ClickException(
            "token is not set. Run `chess-cli config set token <token>` first."
        )

    bot_path = Path(bot_file)
    board_path = Path(board_file)
    if not bot_path.exists():
        raise click.ClickException(f"{bot_file} not found in {Path.cwd()}")
    if not board_path.exists():
        raise click.ClickException(f"{board_file} not found in {Path.cwd()}")

    payload = {
        "team_name": team_name,
        "email": email,
        "bot_py": bot_path.read_text(),
        "board_py": board_path.read_text(),
    }

    league = cfg.get("league", "chess")
    url = api_url.rstrip("/") + f"/api/v1/leagues/{league}/bots/submit"
    try:
        resp = requests.post(
            url,
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
    except requests.exceptions.RequestException as e:
        raise click.ClickException(
            f"could not reach {url}: {e}\n"
            f"(if the arena server isn't up yet, your instructor will let you know.)"
        )

    if resp.status_code >= 400:
        raise click.ClickException(
            f"server returned {resp.status_code}: {resp.text.strip()}"
        )

    click.echo(click.style(f"submitted as {team_name!r} to {url}", fg="green"))
    try:
        body = resp.json()
        if isinstance(body, dict) and body:
            for k, v in body.items():
                click.echo(f"  {k}: {v}")
    except ValueError:
        if resp.text.strip():
            click.echo(resp.text.strip())


if __name__ == "__main__":
    main()
