# Project agent memory

This file is the project's committed home for project-intrinsic agent knowledge: build, test, release, architecture, and sharp-edge notes that should travel with the code.

- Dependencies are managed with uv only. Add packages with `uv add` / `uv add --dev`;
  never hand-edit `pyproject.toml` deps or introduce a second packaging tool.
- Run the tests with `SDL_VIDEODRIVER=dummy uv run pytest`. The dummy driver keeps
  pygame headless; anything needing a real window does not belong in the suite.
  `.github/workflows/ci.yml` runs the same commands on PRs and pushes to `main`.
- Automated tests play the game's real levels only perfectly: a route planned against
  the level's own obstacle data and replayed through the real `Game` or `headless.play`
  without touching a dot, as `tests/test_perfect_run.py` does. Crude scripted play
  (fixed key sequences that walk into walls or dots) on real levels is not wanted.
  Small test-only levels built for one check may each exercise one runner result
  (a death, running out of moves, a coin, sliding along a wall), as `tests/test_headless.py`
  does, and training the learner end to end runs only on such a level, as
  `tests/test_evolve.py` does. Hand playtesting of the real game (collisions and
  resets, coins, goals, moving between levels, clicking through screens) stays with
  the maintainer; otherwise automated tests cover static facts and pure helpers.
- Game logic advances only in fixed steps of `engine.STEP`, and the rules of a level
  live in `engine.Attempt`, which needs no display. The window (`Play`) and the headless
  move-list runners (`headless.play`, and `headless.play_all`, which the learner in
  `evolve` trains through) all step it, so change the rules there, not in any caller.
- The game lives in the `worlds_easiest_game` package under `src/`, and its modules
  import each other by that absolute name. Both entry points, the console script
  declared in `pyproject.toml` and the `game/main.py` launcher, call the same
  `worlds_easiest_game.main`; README.md documents how to run them. Entry points and
  suite alike reach the game as an installed package.

## Maintaining this file

Keep this file for knowledge useful to almost every future agent session in this project.
Do not repeat what the codebase already shows; point to the authoritative file or command instead.
Prefer rewriting or pruning existing entries over appending new ones.
When updating this file, preserve this bar for all agents and keep entries concise.
