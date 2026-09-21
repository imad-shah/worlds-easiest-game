'''Tests for what the `worlds-easiest-game` console script actually starts.

`main` is pure wiring, so `engine.run` is monkeypatched here and the game loop
never runs -- nothing in this file opens a window.
'''

import worlds_easiest_game
from worlds_easiest_game import engine, levels


def test_main_plays_every_level(monkeypatch):
    '''The entry point must play the game, not the uv scaffold stub.'''
    played = []
    monkeypatch.setattr(engine, 'run', played.append)

    worlds_easiest_game.main()

    assert played == [levels.LEVELS]
