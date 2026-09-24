'''Tests for watching the learner train in the window: the readout, the frame it
draws, that the runs it shows are the runs the learner scores, moving on from
level to level, and the replay of the whole game.

Training here only ever runs on small levels built for it, never on the game's
own levels. Frames are drawn offscreen and sampled; the dummy video driver gives
the surfaces a display to convert to without opening a window.
'''

import math
import os
from itertools import islice
from types import SimpleNamespace

import pygame
import pytest

from worlds_easiest_game import engine, evolve, levels, obstacles, watch
from worlds_easiest_game.headless import Ending
from worlds_easiest_game.obstacles import vertical

SETTINGS = evolve.Settings(population=30)
RED = pygame.Color(engine.RED)
YELLOW = pygame.Color(engine.YELLOW)
READOUT = pygame.Rect(0, 0, 640, 60)  # the window's top-left corner, where the readout goes


def gate():
    '''A corridor with a dot sweeping up and down across its middle, which a
    character has to time its way past to reach the goal at the far end.'''
    return SimpleNamespace(
        PLAYFIELD=[(100, 200), (340, 200), (340, 260), (100, 260)], PLAYER_SPAWN=(108, 215),
        PATH_REGIONS=[((100, 200), (340, 260))], SAFE_REGIONS=[((300, 200), (340, 260))],
        GOAL=((300, 200), (340, 260)), COINS=[],
        OBSTACLES=[vertical(x=220, from_y=210, to_y=250, speed=60)], TIME_LIMIT=3)


def gate_with_a_coin():
    '''The gate, with a coin to fetch from a pocket above the start before the
    goal counts.'''
    return SimpleNamespace(
        PLAYFIELD=[(100, 200), (140, 200), (140, 140), (180, 140), (180, 200), (340, 200), (340, 260),
                   (100, 260)],
        PLAYER_SPAWN=(108, 215), PATH_REGIONS=[((100, 200), (340, 260)), ((140, 140), (180, 200))],
        SAFE_REGIONS=[((300, 200), (340, 260))], GOAL=((300, 200), (340, 260)), COINS=[(160, 160)],
        OBSTACLES=[vertical(x=220, from_y=210, to_y=250, speed=60)], TIME_LIMIT=4)


@pytest.fixture(scope='module')
def display():
    os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
    pygame.init()
    pygame.display.set_mode((engine.SCREEN_WIDTH, engine.WINDOW_HEIGHT))
    yield
    pygame.quit()


def test_readout_text():
    assert watch.readout(3, 9, 8, 500, 15) == 'Level: 3/9   Generation: 8   Alive: 500   Steps: 15'


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
def shown(display):
    '''A Watch partway through its first generation, once some characters have died.'''
    shown = watch.Watch([gate()], SETTINGS, seed=3, cap=60)
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


def numbers_drawn(window, shown, numbers):
    '''Whether `window` shows the readout's `numbers` line, and nothing else, above the hint line.'''
    expected = pygame.Surface(READOUT.size)
    expected.fill(engine.BACKGROUND)
    watch.draw_line(expected, shown.font, numbers, watch.READOUT_TOP)
    return all(window.get_at((x, y)) == expected.get_at((x, y))
               for x in range(READOUT.width) for y in range(shown.hint_top))


def test_the_readout_draws_the_watch_s_own_numbers(shown):
    numbers = watch.readout(1, 1, shown.round.number, len(shown.runs.alive), shown.runs.steps)

    assert f'Alive: {len(shown.runs.alive)}' in numbers and f'Alive: {SETTINGS.population}' not in numbers
    assert numbers_drawn(frame(shown), shown, numbers)


HINTS = [watch.keys_hint(fast, best_only) for fast in (False, True) for best_only in (False, True)] + [
    'Not beaten, training stopped   Q: quit', 'Replaying the whole game', 'Every level beaten!   Q: quit']


def test_the_readout_stays_clear_of_every_level_s_course_and_dots(shown):
    '''The numbers fit in the bar's height, and the hint line under them, in the
    play area's top edge, never covers a wall or anywhere a dot goes.'''
    numbers = shown.font.size(watch.readout(9, 9, 1000, 1000, 10_000))
    assert engine.BAR_MARGIN + numbers[0] < engine.SCREEN_WIDTH - engine.BAR_MARGIN
    assert watch.READOUT_TOP + numbers[1] <= engine.BAR_HEIGHT
    hint = pygame.Rect(0, shown.hint_top, engine.BAR_MARGIN + max(shown.hint_font.size(text)[0] for text in HINTS),
                       shown.hint_font.get_height())

    for level in levels.LEVELS:
        first, *rest = engine.level_walls(level)
        assert first.unionall(rest).top + engine.BAR_HEIGHT > hint.bottom, level.__name__
        for dot in level.OBSTACLES:
            period = getattr(dot, 'period', engine.STEP)
            for step in range(math.ceil(period / engine.STEP)):
                x, y = dot.position(step * engine.STEP)
                reach = pygame.Rect(0, 0, 2 * obstacles.RADIUS, 2 * obstacles.RADIUS)
                reach.center = (round(x), round(y) + engine.BAR_HEIGHT)
                assert not hint.colliderect(reach), (level.__name__, dot)


def test_best_only_draws_just_the_round_s_leader(shown):
    every = frame(shown)
    shown.handle(press(watch.BEST_KEY))
    assert shown.best_only
    window = frame(shown)
    leader = shown.runs.attempts[shown.round.leader()].player

    red = red_pixels(window)
    assert red and inside(red, [leader])
    # The readout still counts the whole generation; only the hint line changes.
    assert all(window.get_at((x, y)) == every.get_at((x, y))
               for x in range(READOUT.width) for y in range(shown.hint_top))

    shown.handle(press(watch.BEST_KEY))
    assert not shown.best_only


def test_the_runs_drawn_are_the_runs_the_learner_scores(display):
    shown = watch.Watch([gate()], SETTINGS, seed=7, cap=4)
    last_drawn = {}  # each generation's last frame: where each character alive was drawn
    played = {}  # each generation, as the watch scored it
    while shown.training:
        assert shown.runs is shown.round.runs
        playing = shown.round
        last_drawn[playing.number] = {i: attempt.player.topleft for i, attempt in enumerate(shown.runs.attempts)
                                      if attempt in shown.runs.alive}
        shown.step()
        if shown.round is not playing or not shown.training:
            played[playing.number] = playing.generation

    scored = list(islice(evolve.generations(gate(), SETTINGS, seed=7), 4))
    assert [(g.characters, g.results, g.scores) for g in played.values()] == \
        [(g.characters, g.results, g.scores) for g in scored]
    for generation in scored:
        assert last_drawn[generation.number] == {i: result.position for i, result in enumerate(generation.results)
                                                 if result.ending is not Ending.DIED}


def test_f_switches_to_fast_mode_and_back(display):
    shown = watch.Watch([gate()], SETTINGS, seed=7, cap=1000)
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


def yellow_pixels(window):
    '''Every coin-yellow pixel in the play area, in play-area coordinates.'''
    return {(x, y - engine.BAR_HEIGHT) for x in range(engine.SCREEN_WIDTH)
            for y in range(engine.BAR_HEIGHT, engine.WINDOW_HEIGHT) if window.get_at((x, y)) == YELLOW}


def test_once_a_level_is_beaten_the_window_moves_on_to_the_next(display):
    first, second = gate(), gate_with_a_coin()
    shown = watch.Watch([first, second], SETTINGS, seed=3, cap=100)
    before = frame(shown)
    while shown.round.level is first:
        shown.step()

    assert shown.training and shown.round.number == 1 and shown.level_index == 1
    assert [solution.level for solution in shown.learner.solutions] == [first]
    window = frame(shown)
    # The second level's pocket, the coin in it, and its readout.
    pocket = (160, 145 + engine.BAR_HEIGHT)
    assert before.get_at(pocket) == pygame.Color(engine.BACKGROUND) != window.get_at(pocket)
    assert yellow_pixels(window)
    assert numbers_drawn(window, shown, watch.readout(2, 2, 1, len(shown.runs.alive), shown.runs.steps))


def test_a_coin_is_drawn_until_every_character_drawn_has_collected_it(display):
    shown = watch.Watch([gate_with_a_coin()], SETTINGS, seed=3, cap=100)
    while all(attempt.coins for attempt in shown.runs.alive):
        shown.step()
    assert any(attempt.coins for attempt in shown.runs.alive)
    assert yellow_pixels(frame(shown))

    shown.handle(press(watch.BEST_KEY))
    leader = shown.runs.attempts[shown.round.leader()]
    assert bool(yellow_pixels(frame(shown))) == bool(leader.coins)


def test_once_every_level_is_beaten_the_whole_game_is_replayed_and_then_stays(display):
    shown = watch.Watch([gate(), gate_with_a_coin()], SETTINGS, seed=3, cap=100)
    shown.hurry(math.inf)

    first, second = shown.learner.solutions
    assert shown.learner.beaten and not shown.training
    assert shown.replayed == 0 and shown.level_index == 0 and shown.runs.steps == 0
    assert shown.hint() == 'Replaying the whole game'
    shown.handle(press(watch.FAST_KEY))
    assert not shown.fast, 'F switched to fast mode after training'

    for _ in range(first.result.step):
        shown.advance(None, 1)
    assert shown.runs.over and shown.runs.finish() == [first.result]
    red = red_pixels(frame(shown))
    assert red and inside(red, [shown.runs.attempts[0].player])
    shown.advance(None, 1)
    assert shown.replayed == 1 and shown.level_index == 1 and shown.runs.steps == 0

    shown.advance(None, 10_000)

    assert shown.runs.finish() == [second.result]
    assert shown.hint() == 'Every level beaten!   Q: quit'
    window = frame(shown)
    red = red_pixels(window)
    assert red and inside(red, [shown.runs.attempts[0].player])
    assert not yellow_pixels(window), 'the replay collected the coin'


def test_training_stops_after_the_cap(display):
    shown = watch.Watch([gate(), gate()], SETTINGS, seed=3, cap=2)
    shown.hurry(math.inf)

    assert shown.given_up and not shown.learner.beaten and shown.round.number == 2
    assert shown.hint() == 'Not beaten, training stopped   Q: quit'
    frame(shown)  # still draws the last generation where it ended
