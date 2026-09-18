# Project agent memory

This file is the project's committed home for project-intrinsic agent knowledge: build, test, release, architecture, and sharp-edge notes that should travel with the code.

- Dependencies are managed with uv only. Add packages with `uv add` / `uv add --dev`;
  never hand-edit `pyproject.toml` deps or introduce a second packaging tool.
- Run the tests with `SDL_VIDEODRIVER=dummy uv run pytest`. The dummy driver keeps
  pygame headless; anything needing a real window does not belong in the suite.
  `.github/workflows/ci.yml` runs the same commands on PRs and pushes to `main`.
- The game is launched with `python game/main.py`, which puts `game/` on sys.path, so its
  modules import each other as `engine` / `levels`. `pythonpath = ["game"]` in
  `[tool.pytest.ini_options]` gives the suite that same root; import them the same way.

## Maintaining this file

Keep this file for knowledge useful to almost every future agent session in this project.
Do not repeat what the codebase already shows; point to the authoritative file or command instead.
Prefer rewriting or pruning existing entries over appending new ones.
When updating this file, preserve this bar for all agents and keep entries concise.
