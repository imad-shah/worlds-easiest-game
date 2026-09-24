'''Tests for what the `worlds-easiest-game` console script actually starts.

`main` is pure wiring, so `engine.run`, `evolve.train`, and `watch.run` are
monkeypatched here and neither the game loop nor any training runs -- nothing in
this file opens a window.
'''

import dataclasses
import subprocess
import sys

import pytest

import worlds_easiest_game
from worlds_easiest_game import engine, evolve, levels, watch


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


@pytest.fixture
def trained(monkeypatch):
    '''Every call to evolve.train, each beating the level at once.'''
    calls = []
    monkeypatch.setattr(evolve, 'train', lambda *args: calls.append(args) or 'the winning generation')
    return calls


def test_train_learns_level1_with_the_default_settings_and_the_population_given(trained, played):
    worlds_easiest_game.main(['train', '300', '--seed', '7'])

    assert trained == [(levels.LEVELS[0], evolve.Settings(population=300), 7,
                        worlds_easiest_game.DEFAULT_GENERATIONS)]
    assert played == []


@pytest.fixture
def watched(monkeypatch):
    '''Every call to watch.run, each beating the level at once.'''
    calls = []
    monkeypatch.setattr(watch, 'run', lambda *args: calls.append(args) or 'the winning generation')
    return calls


def test_train_with_watch_trains_the_same_way_in_the_window(trained, watched, played):
    worlds_easiest_game.main(['train', '300', '--watch', '--seed', '7', '--generations', '50',
                              '--mutation', '0.02'])

    assert watched == [(levels.LEVELS[0], evolve.Settings(population=300, mutation=0.02), 7, 50)]
    assert trained == []
    assert played == []


def test_train_with_watch_fails_when_no_character_beats_the_level(monkeypatch):
    monkeypatch.setattr(watch, 'run', lambda *args: None)
    with pytest.raises(SystemExit) as exit:
        worlds_easiest_game.main(['train', '10', '--watch', '--seed', '1'])
    assert exit.value.code == 1


def test_importing_the_game_prints_no_pygame_banner():
    imported = subprocess.run([sys.executable, '-c', 'import worlds_easiest_game.engine'],
                              capture_output=True, text=True, check=True)

    assert imported.stdout == ''
    assert imported.stderr == ''


def test_train_takes_every_setting_from_the_command_line(trained):
    worlds_easiest_game.main([
        'train', '50', '--generations', '20', '--mutation', '0.02', '--hold', '6',
        '--first-moves', '4', '--growth', '1', '--time-limit', '9.5', '--progress-weight', '3',
        '--death-penalty', '0.2', '--speed-weight', '2',
    ])

    [(_, settings, _, cap)] = trained
    assert cap == 20
    assert settings == evolve.Settings(population=50, mutation=0.02, hold=6, first_moves=4, growth=1,
                                       time_limit=9.5, progress_weight=3, death_penalty=0.2,
                                       speed_weight=2)


def test_every_setting_but_the_population_has_a_command_line_option():
    options = set(worlds_easiest_game.TRAINING_OPTIONS) | {'population'}

    assert options == {field.name for field in dataclasses.fields(evolve.Settings)}


def test_train_picks_a_seed_and_prints_it_unless_given(trained, capsys):
    worlds_easiest_game.main(['train', '10'])

    [(_, _, seed, _)] = trained
    assert capsys.readouterr().out == f'Training on level 1: 10 characters a generation, seed {seed}.\n'


def test_train_fails_when_no_character_beats_the_level(monkeypatch):
    monkeypatch.setattr(evolve, 'train', lambda *args: None)
    with pytest.raises(SystemExit) as exit:
        worlds_easiest_game.main(['train', '10', '--seed', '1'])
    assert exit.value.code == 1


@pytest.mark.parametrize('argv', [
    ['train'],
    ['train', '1'],
    ['train', '10', '--generations', '0'],
    ['train', '10', '--generations', '10000000000000000000'],
    ['train', '10', '--death-penalty', '1'],
    ['train', '10', '--time-limit', 'inf'],
    ['train', '10', '--time-limit', '1e17'],
    ['train', '10', '--hold', '10000000000000000000'],
    ['train', '10', '--speed-weight', 'inf'],
    ['--dev', 'train', '10'],
    ['--dev', 'train', '10', '--watch'],
    ['train', '1', '--watch'],
])
def test_bad_training_arguments_are_rejected(trained, argv):
    with pytest.raises(SystemExit) as exit:
        worlds_easiest_game.main(argv)
    assert exit.value.code == 2
    assert trained == []
