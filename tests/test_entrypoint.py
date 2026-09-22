'''Tests for what the `worlds-easiest-game` console script actually starts.

`main` is pure wiring, so `engine.run` is monkeypatched here and the game loop
never runs -- nothing in this file opens a window.
'''

import pytest

import worlds_easiest_game
from worlds_easiest_game import engine, levels


@pytest.fixture
def played(monkeypatch):
    calls = []
    monkeypatch.setattr(engine, 'run', lambda levels, dev: calls.append((levels, dev)))
    return calls


def test_main_plays_every_level(played):
    '''The entry point must play the game, not the uv scaffold stub.'''
    worlds_easiest_game.main([])

    assert played == [(levels.LEVELS, False)]


def test_dev_flag_turns_on_developer_mode(played):
    worlds_easiest_game.main(['--dev'])

    assert played == [(levels.LEVELS, True)]


def test_unknown_arguments_are_rejected(played):
    with pytest.raises(SystemExit):
        worlds_easiest_game.main(['--god'])
    assert played == []
