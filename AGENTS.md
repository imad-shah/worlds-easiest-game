# Project agent memory

This file is the project's committed home for project-intrinsic agent knowledge: build, test, release, architecture, and sharp-edge notes that should travel with the code.

- Dependencies are managed with uv only. Add packages with `uv add` / `uv add --dev`;
  never hand-edit `pyproject.toml` deps or introduce a second packaging tool.
- Run the tests with `SDL_VIDEODRIVER=dummy uv run pytest`. The dummy driver keeps
  pygame headless; anything needing a real window does not belong in the suite.
  `.github/workflows/ci.yml` runs the same commands on PRs and pushes to `main`.
- Automated tests cover static facts and pure helpers only. Gameplay (moving the player,
  collisions and resets, coins, goals, moving between levels, clicking through screens)
  is tested by hand by the maintainer, so do not add automated tests that simulate playing.
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
