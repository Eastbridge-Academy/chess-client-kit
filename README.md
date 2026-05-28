# chess-client-kit

Student client kit for the Eastbridge Academy chess-bot project. Provides the `chessdk` Python library and the `chess-cli` tool.

Students install it with:

```bash
uv tool install git+https://github.com/Eastbridge-Academy/chess-client-kit@v0.5.1
```

and then, in their own working directory:

```bash
chess-cli init                       # drop scaffold files: board.py, bot.py, evaluation.py, search.py, tests/
chess-cli test                       # run this phase's pytest suite
chess-cli perft 3                    # count legal moves at depth 3
chess-cli perft 3 --divide           # compare per-root-move counts against the reference
chess-cli play --vs random_legal     # play one game against a built-in opponent
chess-cli submit "Team Name"         # upload bot to the tournament server
chess-bot-uci                        # speak UCI on stdin/stdout (for cutechess, etc.)
```

## Contents

- `src/chessdk/` — library: primitives, FEN parser, square helpers, reference implementation, CLI.
- `src/chessdk/scaffold/` — files dropped into the student's working directory by `chess-cli init`.

See `projects/chess-bot/` in the `eastbridge-courses` repository for the per-phase handouts that drive this kit.

## License

MIT.
