"""Run a bot on lichess.org through the Bot API.

This drives the same ``choose_move(board, time_left_ms)`` the rest of the kit
uses, talking to lichess directly over HTTP instead of through a UCI bridge.
The lichess clock (``wtime``/``btime``) is handed to ``choose_move`` as
``time_left_ms``, exactly like the local arena and cutechess, so a
time-managed bot needs no changes to play real games.

Requires a **BOT account** token with the ``bot:play`` scope. A normal account
is turned into a bot once, irreversibly, with
``POST /api/bot/account/upgrade`` (there is no web-UI button); after that it
can only play through this API. See the Phase 7 handout for the full setup.

The flow this implements:

  * ``--challenge-ai N``: create a casual game against lichess's Stockfish at
    level N and play it to the end. Self-contained, needs no opponent.
  * otherwise: stream incoming events, accept challenges (optionally filtered
    to one username), and play each game as it starts, one at a time.

Scope is deliberately small (single game at a time, standard chess); the
official ``lichess-bot`` bridge is the tool for 24/7, multi-game hosting.
"""

from __future__ import annotations

import json
import time
from typing import Callable, Iterator

import requests

from chessdk.fen import STARTING_FEN
from chessdk.types import BLACK, Move, WHITE
from chessdk.uci import parse_move


LICHESS = "https://lichess.org"

# Lichess reports castling in standard games as the king's two-square move
# (e1g1), which matches the kit's Move. The Bot API can also use king-to-rook
# notation (e1h1) for Chess960 compatibility; if a streamed move arrives in
# that form, remap it so it resolves against our legal-move list.
_CASTLE_REMAP = {
    "e1h1": "e1g1", "e1a1": "e1c1",
    "e8h8": "e8g8", "e8a8": "e8c8",
}

# Lichess only accepts these initial clock times (seconds) for a challenge;
# an arbitrary value is rejected with a 400, so we snap to the nearest one.
_ALLOWED_CLOCK_LIMITS = (
    0, 15, 30, 45, 60, 90, 120, 180, 240, 300,
    360, 420, 480, 600, 900, 1200, 1500, 1800, 2400, 3000, 3600,
)


def _snap_clock_limit(seconds: int, echo: Callable[[str], None]) -> int:
    if seconds in _ALLOWED_CLOCK_LIMITS:
        return seconds
    nearest = min(_ALLOWED_CLOCK_LIMITS, key=lambda v: abs(v - seconds))
    echo(f"lichess: clock limit {seconds}s is not allowed; using {nearest}s instead.")
    return nearest


class LichessError(RuntimeError):
    """A lichess API call failed in a way the caller should surface."""


class LichessClient:
    """Thin wrapper over the lichess Bot API endpoints this kit needs."""

    def __init__(self, token: str, *, base_url: str = LICHESS, echo: Callable[[str], None] = print) -> None:
        self.base = base_url.rstrip("/")
        self.echo = echo
        self.session = requests.Session()
        self.session.headers["Authorization"] = f"Bearer {token}"

    # -- low-level helpers ---------------------------------------------------

    def _post(self, path: str, *, data: dict | None = None) -> requests.Response:
        """POST with the one rate-limit rule lichess asks for: on a 429, wait a
        full minute before trying again (ignoring 429s gets the account banned).
        """
        while True:
            resp = self.session.post(self.base + path, data=data, timeout=15)
            if resp.status_code == 429:
                self.echo("lichess: rate-limited (429); waiting 60s before retrying ...")
                time.sleep(60)
                continue
            return resp

    def stream(self, path: str) -> Iterator[dict]:
        """Yield parsed JSON objects from an NDJSON stream, reconnecting if the
        connection drops mid-game. Blank keep-alive lines are skipped.
        """
        while True:
            resp = None
            try:
                resp = self.session.get(self.base + path, stream=True, timeout=(10, 65))
                if resp.status_code == 429:
                    self.echo("lichess: rate-limited (429) on stream; waiting 60s ...")
                    time.sleep(60)
                    continue
                if resp.status_code != 200:
                    raise LichessError(f"GET {path} returned {resp.status_code}: {resp.text.strip()}")
                for line in resp.iter_lines():
                    if line:
                        yield json.loads(line)
                return  # stream closed cleanly (e.g. the game ended)
            except (requests.exceptions.ReadTimeout,
                    requests.exceptions.ConnectionError,
                    requests.exceptions.ChunkedEncodingError):
                self.echo("lichess: stream dropped; reconnecting ...")
                continue
            finally:
                # Close the socket promptly when the game ends or the consumer
                # stops reading, so we don't leak a connection between games.
                if resp is not None:
                    resp.close()

    # -- endpoints -----------------------------------------------------------

    def account(self) -> dict:
        resp = self.session.get(self.base + "/api/account", timeout=15)
        if resp.status_code != 200:
            raise LichessError(f"/api/account returned {resp.status_code}: {resp.text.strip()}")
        return resp.json()

    def upgrade_to_bot(self) -> None:
        """Irreversibly turn this account into a BOT account (one-time)."""
        resp = self._post("/api/bot/account/upgrade")
        if resp.status_code >= 400:
            raise LichessError(f"upgrade failed {resp.status_code}: {resp.text.strip()}")

    def challenge_ai(self, level: int, clock_limit: int, clock_increment: int, color: str = "random") -> dict:
        clock_limit = _snap_clock_limit(clock_limit, self.echo)
        clock_increment = max(0, min(60, clock_increment))
        resp = self._post("/api/challenge/ai", data={
            "level": level,
            "clock.limit": clock_limit,
            "clock.increment": clock_increment,
            "color": color,
        })
        if resp.status_code >= 400:
            raise LichessError(f"challenge/ai failed {resp.status_code}: {resp.text.strip()}")
        return resp.json()

    def accept(self, challenge_id: str) -> None:
        self._post(f"/api/challenge/{challenge_id}/accept")

    def decline(self, challenge_id: str, reason: str = "generic") -> None:
        self._post(f"/api/challenge/{challenge_id}/decline", data={"reason": reason})

    def make_move(self, game_id: str, uci: str) -> None:
        resp = self._post(f"/api/bot/game/{game_id}/move/{uci}")
        if resp.status_code >= 400:
            raise LichessError(f"move {uci!r} rejected {resp.status_code}: {resp.text.strip()}")


def _resolve(board, uci: str) -> Move:
    """Turn a UCI string from the game stream into a Move on this board,
    remapping king-to-rook castling notation if needed.
    """
    legal = board.legal_moves()
    try:
        return parse_move(uci, legal)
    except ValueError:
        if uci in _CASTLE_REMAP:
            return parse_move(_CASTLE_REMAP[uci], legal)
        raise


def _build_board(board_cls, initial_fen: str, moves_str: str):
    """Replay the game's move list onto a fresh board to get the live position."""
    fen = STARTING_FEN if (not initial_fen or initial_fen == "startpos") else initial_fen
    board = board_cls.from_fen(fen)
    for uci in moves_str.split():
        board.make_move(_resolve(board, uci))
    return board


def play_game(client: LichessClient, game_id: str, board_cls, choose_move: Callable,
              my_id: str, *, echo: Callable[[str], None] = print) -> None:
    """Stream one game and answer with ``choose_move`` whenever it is our turn."""
    my_color = None
    initial_fen = "startpos"
    last_count = -1

    for event in client.stream(f"/api/bot/game/stream/{game_id}"):
        etype = event.get("type")
        if etype == "gameFull":
            white_id = (event.get("white") or {}).get("id")
            black_id = (event.get("black") or {}).get("id")
            my_color = WHITE if white_id == my_id else BLACK
            initial_fen = event.get("initialFen", "startpos")
            opponent = black_id if my_color == WHITE else white_id
            echo(f"game {game_id}: you are {'White' if my_color == WHITE else 'Black'} vs {opponent}")
            state = event.get("state") or {}
        elif etype == "gameState":
            state = event
        else:
            continue  # chatLine, opponentGone, etc.

        status = state.get("status", "started")
        if status != "started":
            winner = state.get("winner")
            tail = f", winner: {winner}" if winner else ""
            echo(f"game {game_id} finished: {status}{tail}")
            return

        moves_str = state.get("moves", "")
        count = len(moves_str.split())
        if count == last_count:
            continue  # nothing new since we last looked
        last_count = count

        board = _build_board(board_cls, initial_fen, moves_str)
        if board.side_to_move != my_color:
            continue

        my_time = int(state.get("wtime" if my_color == WHITE else "btime", 60000))
        move = choose_move(board, my_time)
        echo(f"  move {count + 1}: {move.uci()}  ({my_time} ms on our clock)")
        client.make_move(game_id, move.uci())


def play_on_lichess(token: str, board_cls, choose_move: Callable, *,
                    challenge_ai_level: int | None = None,
                    clock_limit: int = 180, clock_increment: int = 2,
                    accept_from: str | None = None,
                    echo: Callable[[str], None] = print) -> None:
    """Connect as the token's account and play, either against the AI or by
    accepting incoming challenges.
    """
    client = LichessClient(token, echo=echo)
    me = client.account()
    my_id = me["id"]
    if me.get("title") != "BOT":
        raise LichessError(
            f"account {me.get('username')!r} is not a BOT account. Upgrade it first "
            "with POST /api/bot/account/upgrade (one-time, irreversible)."
        )
    echo(f"connected as {me['username']} (BOT account)")

    if challenge_ai_level is not None:
        echo(f"challenging Stockfish level {challenge_ai_level} "
             f"({clock_limit}+{clock_increment}) ...")
        game = client.challenge_ai(challenge_ai_level, clock_limit, clock_increment)
        play_game(client, game["id"], board_cls, choose_move, my_id, echo=echo)
        return

    want = accept_from.lower() if accept_from else None
    echo("waiting for challenges (Ctrl-C to stop) ...")
    for event in client.stream("/api/stream/event"):
        etype = event.get("type")
        if etype == "challenge":
            ch = event["challenge"]
            cid = ch["id"]
            challenger = (ch.get("challenger") or {}).get("id")
            if (ch.get("variant") or {}).get("key", "standard") != "standard":
                client.decline(cid, "standard")
                continue
            if want and challenger != want:
                client.decline(cid, "generic")
                echo(f"declined challenge from {challenger} (only accepting {accept_from})")
                continue
            echo(f"accepting challenge {cid} from {challenger}")
            client.accept(cid)
        elif etype == "gameStart":
            gid = event["game"]["id"]
            play_game(client, gid, board_cls, choose_move, my_id, echo=echo)
            echo("game finished; waiting for more challenges ...")
