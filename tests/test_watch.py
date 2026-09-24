'''Tests for watching the learner train in the window: the readout, the frame it
draws, and that the runs it shows are the runs the learner scores.

Training here only ever runs on a small level built for it, never on the game's
own levels. Frames are drawn offscreen and sampled; the dummy video driver gives
the surfaces a display to convert to without opening a window.
'''

import math
import os
from itertools import islice
from types import SimpleNamespace

import pygame
import pytest

from worlds_easiest_game import engine, evolve, watch
from worlds_easiest_game.headless import Ending
from worlds_easiest_game.obstacles import vertical

SETTINGS = evolve.Settings(population=30)
RED = pygame.Color(engine.RED)
READOUT = pygame.Rect(0, 0, 320, 120)  # the window's top-left corner, where the readout goes


def gate():
    '''A corridor with a dot sweeping up and down across its middle, which a
    character has to time its way past to reach the goal at the far end.'''
    return SimpleNamespace(
        PLAYFIELD=[(100, 200), (340, 200), (340, 260), (100, 260)], PLAYER_SPAWN=(108, 215),
        PATH_REGIONS=[((100, 200), (340, 260))], SAFE_REGIONS=[((300, 200), (340, 260))],
        GOAL=((300, 200), (340, 260)), COINS=[],
        OBSTACLES=[vertical(x=220, from_y=210, to_y=250, speed=60)], TIME_LIMIT=3)


@pytest.fixture(scope='module')
def display():
    os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
    pygame.init()
    pygame.display.set_mode((engine.SCREEN_WIDTH, engine.WINDOW_HEIGHT))
    yield
    pygame.quit()


@pytest.fixture
def quiet(monkeypatch):
    '''Keep the generations' report lines out of the test output.'''
    monkeypatch.setattr(evolve, 'report', lambda generation: None)
    monkeypatch.setattr(evolve, 'give_up', lambda cap: None)


def test_readout_text():
    assert watch.readout(8, 500, 15) == ['Generation: 8', 'Alive: 500', 'Steps: 15']


@pytest.mark.parametrize('fast, best_only, hint', [
    (False, False, 'F: fast mode   B: best only   Q: quit'),
    (True, False, 'F: normal speed   B: best only   Q: quit'),
    (False, True, 'F: fast mode   B: show all   Q: quit'),
])
def test_keys_hint(fast, best_only, hint):
    assert watch.keys_hint(fast, best_only) == hint


def press(key):
    return pygame.event.Event(pygame.KEYDOWN, key=key)


def frame(shown):
    '''Draw `shown`, a Watch, into a fresh window-sized surface.'''
    window = pygame.Surface((engine.SCREEN_WIDTH, engine.WINDOW_HEIGHT))
    shown.draw(window)
    return window


def red_pixels(window):
    '''Every red pixel in the play area, in play-area coordinates.'''
    return {(x, y - engine.BAR_HEIGHT) for x in range(engine.SCREEN_WIDTH)
            for y in range(engine.BAR_HEIGHT, engine.WINDOW_HEIGHT) if window.get_at((x, y)) == RED}


def inside(pixels, players):
    return all(any(player.collidepoint(pixel) for player in players) for pixel in pixels)


@pytest.fixture
def shown(display, quiet):
    '''A Watch partway through its first generation, once some characters have died.'''
    shown = watch.Watch(gate(), SETTINGS, seed=3, cap=60)
    while len(shown.runs.alive) == SETTINGS.population:
        shown.step()
    assert shown.round.number == 1 and len(shown.runs.alive) > 1
    return shown


def test_a_frame_draws_every_character_alive_and_the_readout(shown):
    window = frame(shown)
    alive = [attempt.player for attempt in shown.runs.alive]

    red = red_pixels(window)
    assert all(any(player.collidepoint(pixel) for pixel in red) for player in alive)
    assert inside(red, alive), 'red drawn where no character alive stands'

    # No top bar: the window's top edge is the background, apart from the readout.
    assert window.get_at((engine.SCREEN_WIDTH - 1, 0)) == pygame.Color(engine.BACKGROUND)
    ink = [(x, y) for x in range(engine.SCREEN_WIDTH) for y in range(engine.BAR_HEIGHT)
           if window.get_at((x, y)) != pygame.Color(engine.BACKGROUND)]
    assert ink and all(READOUT.collidepoint(pixel) for pixel in ink)
    assert min(x for x, _ in ink) == engine.BAR_MARGIN
    assert pygame.Color(engine.WHITE) in [window.get_at(pixel) for pixel in ink]


def test_the_readout_draws_the_watch_s_own_numbers(shown):
    lines = watch.readout(shown.round.number, len(shown.runs.alive), shown.runs.steps)
    window = frame(shown)
    expected = pygame.Surface(READOUT.size)
    expected.fill(engine.BACKGROUND)
    bottom = watch.READOUT_TOP
    for line in lines:
        watch.draw_line(expected, shown.font, line, bottom)
        bottom += shown.font.get_linesize()

    assert lines[1] == f'Alive: {len(shown.runs.alive)}' != f'Alive: {SETTINGS.population}'
    for x in range(READOUT.width):
        for y in range(watch.READOUT_TOP, bottom):
            assert window.get_at((x, y)) == expected.get_at((x, y)), (x, y)


def test_best_only_draws_just_the_round_s_leader(shown):
    every = frame(shown)
    shown.handle(press(watch.BEST_KEY))
    assert shown.best_only
    window = frame(shown)
    leader = shown.runs.attempts[shown.round.leader()].player

    red = red_pixels(window)
    assert red and inside(red, [leader])
    # The readout still counts the whole generation; only the hint line changes.
    numbers = pygame.Rect(0, 0, READOUT.width, watch.READOUT_TOP + 3 * shown.font.get_linesize())
    assert all(window.get_at((x, y)) == every.get_at((x, y))
               for x in range(numbers.width) for y in range(numbers.height))

    shown.handle(press(watch.BEST_KEY))
    assert not shown.best_only


def test_the_runs_drawn_are_the_runs_the_learner_scores(display, monkeypatch):
    reported = []
    monkeypatch.setattr(evolve, 'report', reported.append)
    monkeypatch.setattr(evolve, 'give_up', lambda cap: None)
    shown = watch.Watch(gate(), SETTINGS, seed=7, cap=4)
    last_drawn = {}  # each generation's last frame: where each character alive was drawn
    while shown.training:
        assert shown.runs is shown.round.runs
        last_drawn[shown.round.number] = {i: attempt.player.topleft for i, attempt in enumerate(shown.runs.attempts)
                                          if attempt in shown.runs.alive}
        shown.step()

    scored = list(islice(evolve.generations(gate(), SETTINGS, seed=7), 4))
    assert [(g.characters, g.results, g.scores) for g in reported] == \
        [(g.characters, g.results, g.scores) for g in scored]
    for generation in scored:
        assert last_drawn[generation.number] == {i: result.position for i, result in enumerate(generation.results)
                                                 if result.ending is not Ending.DIED}


def test_f_switches_to_fast_mode_and_back(display, quiet):
    shown = watch.Watch(gate(), SETTINGS, seed=7, cap=1000)
    shown.advance(None, 1)
    assert (shown.round.number, shown.runs.steps) == (1, 1)

    shown.handle(press(watch.FAST_KEY))
    assert shown.fast
    shown.advance(None, 1)  # a frame's worth of training, whatever real time is due
    assert shown.round.number > 1 or shown.runs.steps > 2

    shown.handle(press(watch.FAST_KEY))
    assert not shown.fast
    before = (shown.round.number, shown.runs.steps)
    shown.advance(None, 1)
    assert shown.round.number > before[0] or shown.runs.steps == before[1] + 1


def test_the_winning_run_is_replayed_and_then_stays(display, quiet):
    shown = watch.Watch(gate(), SETTINGS, seed=3, cap=60)
    shown.hurry(math.inf)

    winner = shown.winner
    assert winner and winner.beaten and not shown.training
    assert shown.runs is not shown.round.runs and shown.runs.steps == 0
    assert shown.hint() == 'Replaying the winning run'
    shown.handle(press(watch.FAST_KEY))
    assert not shown.fast, 'F switched to fast mode after training'

    shown.advance(None, 10_000)

    assert shown.runs.finish() == [winner.results[winner.best]]
    assert shown.round.number == winner.number
    assert shown.hint() == f'Beaten in generation {winner.number}!   Q: quit'
    red = red_pixels(frame(shown))
    assert red and inside(red, [shown.runs.attempts[0].player])


def test_training_stops_after_the_cap(display, quiet):
    shown = watch.Watch(gate(), SETTINGS, seed=3, cap=2)
    shown.hurry(math.inf)

    assert shown.given_up and shown.winner is None and shown.round.number == 2
    assert shown.hint() == 'Not beaten in 2 generations   Q: quit'
