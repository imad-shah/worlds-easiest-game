'''World's Easiest Game -- a recreation of "World's Hardest Game".

`main` is what the `worlds-easiest-game` console script runs; `game/main.py`
calls the same function.
'''

from worlds_easiest_game import engine, levels


def main() -> None:
    engine.run(levels.current_level())
