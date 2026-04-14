"""chess-cli: student-facing command-line tool.

Subcommands:

  init       Drop scaffold files (board.py, bot.py, tests/) into the current directory.
  test       Run pytest on your tests.
  perft N    Count moves from a position at depth N (optional --fen, --divide).
  config     Get/set values in a per-project config file.
  info       Show current config and environment info.
  play       (Week 3+) Play a local match against a house bot.
  submit     (Week 3+) Upload your bot to the tournament server.
"""

from __future__ import annotations

import json
import shutil
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
    if depth == 0:
        return 1
    moves = board.pseudo_legal_moves()
    if depth == 1:
        return len(moves)
    # Week 1 only has pseudo_legal_moves; perft > 1 requires make_move (Week 2+).
    # For now, only depth 1 is supported.
    raise click.ClickException(
        "perft at depth > 1 requires make_move / undo_move (Week 2+). "
        "Only depth 1 works in Week 1."
    )


@main.command()
@click.argument("depth", type=int)
@click.option("--fen", default=None, help="FEN string (defaults to the starting position).")
@click.option("--divide", is_flag=True, help="Print per-root-move counts and compare against the reference.")
def perft(depth: int, fen: str | None, divide: bool) -> None:
    """Count pseudo-legal moves from a position at the given depth."""
    # Import student's Board from cwd
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
            student_moves = student_board.pseudo_legal_moves()
        except NotImplementedError as e:
            raise click.ClickException(f"board.py raised NotImplementedError: {e}")

        student_ucis = sorted(m.uci() for m in student_moves)
        ref_ucis = sorted(m.uci() for m in ref_board.pseudo_legal_moves())

        student_set = set(student_ucis)
        ref_set = set(ref_ucis)
        missing = ref_set - student_set
        extra = student_set - ref_set

        click.echo(f"Your count:      {len(student_ucis)}")
        click.echo(f"Reference count: {len(ref_ucis)}")
        if missing:
            click.echo(click.style(f"Missing moves ({len(missing)}):", fg="red"))
            for u in sorted(missing):
                click.echo(f"  - {u}")
        if extra:
            click.echo(click.style(f"Extra moves ({len(extra)}):", fg="yellow"))
            for u in sorted(extra):
                click.echo(f"  + {u}")
        if not missing and not extra:
            click.echo(click.style("Match!", fg="green"))
        sys.exit(0 if not missing and not extra else 1)

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
# play / submit (Week 3+)
# -----------------------------------------------------------------------------

@main.command()
def play() -> None:
    """Play a local match against a house bot (available in Week 3)."""
    click.echo("`play` is available starting Week 3.", err=True)
    sys.exit(2)


@main.command()
@click.argument("team_name", required=False)
@click.option("--email", default=None)
def submit(team_name: str | None, email: str | None) -> None:
    """Submit your bot to the tournament server (available in Week 3)."""
    click.echo("`submit` is available starting Week 3.", err=True)
    sys.exit(2)


if __name__ == "__main__":
    main()
