"""Tests for chess-cli submit's local-module bundling.

Regression test for the gap where students who split code across files
(evaluation.py, search.py, helpers) had only bot.py and board.py uploaded,
so their bot crashed on import during server-side validation and was
rejected with an opaque 'engine process died' error.
"""

from __future__ import annotations

from pathlib import Path

from chessdk.cli import collect_local_modules


def _write(root: Path, name: str, body: str) -> Path:
    path = root / name
    path.write_text(body)
    return path


def test_bundles_transitive_local_imports(tmp_path: Path) -> None:
    bot = _write(
        tmp_path,
        "bot.py",
        "from board import Board\nfrom evaluation import evaluate\nimport search\n",
    )
    board = _write(tmp_path, "board.py", "from chessdk.base import BaseBoard\n")
    _write(tmp_path, "evaluation.py", "import helpers\n\ndef evaluate(b):\n    return 0\n")
    _write(tmp_path, "search.py", "def pick(b):\n    return None\n")
    _write(tmp_path, "helpers.py", "VALUE = 1\n")
    # Files nobody imports must NOT be bundled.
    _write(tmp_path, "test_illegal_move.py", "import board\n")
    _write(tmp_path, "scratch.py", "print('debugging')\n")

    extras = collect_local_modules(tmp_path, [bot, board])

    assert set(extras) == {"evaluation.py", "search.py", "helpers.py"}
    assert "def evaluate" in extras["evaluation.py"]


def test_self_contained_bot_bundles_nothing(tmp_path: Path) -> None:
    bot = _write(tmp_path, "bot.py", "import random\nfrom board import Board\nfrom chessdk import Move\n")
    board = _write(tmp_path, "board.py", "from chessdk.base import BaseBoard\n")

    assert collect_local_modules(tmp_path, [bot, board]) == {}


def test_unparsable_entry_is_skipped(tmp_path: Path) -> None:
    bot = _write(tmp_path, "bot.py", "def broken(:\n")
    board = _write(tmp_path, "board.py", "import evaluation\n")
    _write(tmp_path, "evaluation.py", "def evaluate(b):\n    return 0\n")

    extras = collect_local_modules(tmp_path, [bot, board])

    assert set(extras) == {"evaluation.py"}
