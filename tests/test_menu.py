'''Tests for the menu the game opens on: its two options, the population control
for watching the learner, and moving from the menu to each option and back.

Nothing is played by hand here: the menu is driven by single clicks and key
presses, and the only training runs on a small level built for it, never on the
game's own levels. Frames are drawn offscreen and sampled; the dummy video
driver gives the surfaces a display to convert to without opening a window.
'''

import math
import os
import random
from types import SimpleNamespace

import pygame
import pytest

from worlds_easiest_game import app, engine, evolve, levels, watch
from worlds_easiest_game.obstacles import vertical


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


def click(rect):
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=rect.center, button=1)


def press(key):
    return pygame.event.Event(pygame.KEYDOWN, key=key)


def frame(shown):
    '''Draw `shown`, anything with a `draw(screen)`, into a fresh window-sized surface.'''
    window = pygame.Surface((engine.SCREEN_WIDTH, engine.WINDOW_HEIGHT))
    shown.draw(window)
    return window


def ink(window, area):
    '''The bounding box of everything but the background inside `area` of `window`, or None.'''
    points = [(x, y) for x in range(area.left, area.right) for y in range(area.top, area.bottom)
              if window.get_at((x, y)) != pygame.Color(engine.BACKGROUND)]
    if not points:
        return None
    xs, ys = zip(*points)
    return pygame.Rect(min(xs), min(ys), max(xs) - min(xs) + 1, max(ys) - min(ys) + 1)


def test_the_menu_offers_exactly_the_two_options(display):
    assert list(app.Game(levels.LEVELS).menu.buttons) == ['Start game', 'Watch the AI beat the game']


def test_the_watch_button_sits_beneath_the_start_button_and_the_control_beneath_both(display):
    menu = app.Menu()
    start, watching = menu.buttons[app.START], menu.buttons[app.WATCH]

    assert start.size == watching.size and start.centerx == watching.centerx == engine.SCREEN_WIDTH // 2
    assert start.bottom < watching.top
    assert all(watching.bottom < rect.top for rect in (menu.minus, menu.number, menu.plus))
    assert menu.minus.right == menu.number.left and menu.number.right == menu.plus.left
    window = pygame.Rect(0, 0, engine.SCREEN_WIDTH, engine.WINDOW_HEIGHT)
    assert all(window.contains(rect) for rect in (start, watching, menu.minus, menu.plus))
    assert menu.surface.get_size() == window.size


def test_each_option_s_label_fits_its_button(display):
    menu = app.Menu()
    for label, button in menu.buttons.items():
        width, height = menu.font.size(label)
        assert width < button.width - 2 * engine.WALL_THICKNESS and height < button.height, label


def test_the_buttons_are_drawn_green_outlined_in_black(display):
    menu = app.Menu()
    window = frame(menu)
    for button in (*menu.buttons.values(), menu.minus, menu.plus):
        assert window.get_at(button.topleft) == pygame.Color(engine.BLACK)
        assert window.get_at((button.left + engine.WALL_THICKNESS, button.top + engine.WALL_THICKNESS)) == (
            pygame.Color(engine.GREEN))


def test_the_population_starts_at_the_learner_s_default(display):
    assert app.Menu().population == evolve.DEFAULT_POPULATION == 300


def test_the_population_choices_run_from_the_learner_s_minimum_up_and_include_the_default():
    assert app.POPULATIONS[0] == evolve.MIN_POPULATION == 2
    assert list(app.POPULATIONS) == sorted(set(app.POPULATIONS))
    assert evolve.DEFAULT_POPULATION in app.POPULATIONS
    for population in app.POPULATIONS:
        evolve.Settings(population=population)
    with pytest.raises(ValueError, match='at least 2'):
        evolve.Settings(population=evolve.MIN_POPULATION - 1)


@pytest.mark.parametrize('population, direction, stepped', [
    (300, 1, 400),
    (300, -1, 250),
    (5, -1, 2),
    (2, -1, 2),
    (1000, 1, 1000),
    (1000, -1, 750),
    (320, -1, 300),
    (320, 1, 400),
])
def test_step_population(population, direction, stepped):
    assert app.step_population(population, direction) == stepped


def test_minus_and_plus_step_the_population_and_choose_no_option(display):
    menu = app.Menu()

    assert menu.handle(click(menu.plus)) is None
    assert menu.population == 400
    assert menu.handle(click(menu.minus)) is None
    assert menu.handle(click(menu.minus)) is None
    assert menu.population == 250
    menu.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=menu.minus.center, button=3))
    assert menu.population == 250, 'a right click stepped the population'


def test_the_population_cannot_go_below_2_or_above_the_largest_choice(display):
    menu = app.Menu()
    for _ in range(len(app.POPULATIONS)):
        menu.handle(click(menu.minus))
    assert menu.population == 2
    for _ in range(len(app.POPULATIONS)):
        menu.handle(click(menu.plus))
    assert menu.population == app.POPULATIONS[-1]


def test_the_menu_draws_the_population_centered_between_minus_and_plus(display):
    menu = app.Menu()
    shown = frame(menu)
    menu.handle(click(menu.plus))
    stepped = frame(menu)

    changed = [(x, y) for x in range(engine.SCREEN_WIDTH) for y in range(engine.WINDOW_HEIGHT)
               if shown.get_at((x, y)) != stepped.get_at((x, y))]
    assert changed and all(menu.number.collidepoint(point) for point in changed)
    for window in (shown, stepped):
        number = ink(window, menu.number)
        assert abs(number.centerx - menu.number.centerx) <= 1 and abs(number.centery - menu.number.centery) <= 1


def test_the_population_label_s_capitals_share_the_number_s_center_line(display):
    menu = app.Menu()
    window = frame(menu)
    band = pygame.Rect(0, menu.minus.top, menu.minus.left, menu.minus.height)
    label = ink(window, band)
    # The label's first glyph is its capital C, up to the first column with no ink.
    right = label.left
    while ink(window, pygame.Rect(right, band.top, 1, band.height)):
        right += 1
    capital = ink(window, pygame.Rect(label.left, band.top, right - label.left, band.height))
    number = ink(window, menu.number)

    assert label.right < menu.minus.left
    assert abs(capital.centery - number.centery) <= 1 and abs(capital.centery - menu.minus.centery) <= 1


def test_start_game_plays_the_first_level_by_hand(display):
    game = app.Game(levels.LEVELS)
    game.handle(click(game.menu.buttons[app.START]))

    assert game.state is game.play and game.play.level is levels.LEVELS[0]
    assert game.watching is None


@pytest.fixture
def watching(display, capsys):
    '''A game on a small level, just switched from the menu, one click down, to watching.'''
    game = app.Game([gate()])
    game.handle(click(game.menu.minus))
    game.handle(click(game.menu.buttons[app.WATCH]))
    return game


def test_watch_trains_the_game_s_levels_with_the_menu_s_population(watching, capsys):
    shown = watching.state

    assert isinstance(shown, watch.Watch) and shown is watching.watching
    assert shown.levels == watching.levels and shown.level_index == 0
    assert shown.learner.settings == evolve.Settings(population=250)
    assert shown.learner.cap == evolve.DEFAULT_GENERATIONS
    assert shown.menu and shown.training
    [line] = capsys.readouterr().out.splitlines()
    assert line.startswith('Training on all 1 levels in turn: 250 characters a generation, seed ')


def test_the_game_runs_and_draws_the_watch_while_it_is_on(watching):
    shown = watching.watching
    watching.advance(None, 5)
    assert shown.runs.steps == 5
    watching.update(None)
    assert shown.runs.steps == 6

    assert frame(watching).get_view('2').raw == frame(shown).get_view('2').raw
    watching.handle(press(watch.FAST_KEY))
    assert shown.fast and watching.state is shown


def test_esc_goes_back_to_the_menu_and_the_menu_still_works(watching):
    watching.handle(press(watch.MENU_KEY))

    assert watching.state is watching.menu and watching.watching is None
    assert watching.menu.population == 250, 'the menu forgot the population chosen'
    watching.handle(click(watching.menu.buttons[app.START]))
    assert watching.state is watching.play


def test_a_watch_from_the_menu_says_how_to_go_back_at_the_top_right(watching):
    shown = watching.watching
    window = frame(watching)
    shown.menu = False
    plain = frame(watching)
    changed = [(x, y) for x in range(engine.SCREEN_WIDTH) for y in range(engine.WINDOW_HEIGHT)
               if window.get_at((x, y)) != plain.get_at((x, y))]
    xs, ys = zip(*changed)
    label = pygame.Rect(min(xs), min(ys), max(xs) - min(xs) + 1, max(ys) - min(ys) + 1)

    assert label.right == engine.SCREEN_WIDTH - engine.BAR_MARGIN
    # In the band above the play area, clear of the numbers however long they get.
    assert label.bottom <= engine.BAR_HEIGHT
    numbers = engine.BAR_MARGIN + shown.font.size(watch.readout(9, 9, 1000, 1000, 10_000))[0]
    assert label.left > numbers
    assert label.width == shown.hint_font.render(watch.MENU_HINT, True, engine.WHITE).get_bounding_rect().width
    # On the numbers' baseline, where their capitals end (the label has no descenders).
    capital = shown.font.render('L', True, engine.WHITE).get_bounding_rect()
    assert label.bottom == watch.READOUT_TOP + capital.bottom


def test_esc_does_nothing_in_a_watch_started_from_the_command_line(display):
    shown = watch.Watch([gate()], evolve.Settings(population=2), seed=1, cap=1)
    shown.handle(press(watch.MENU_KEY))

    assert shown.running
    top_right = pygame.Rect(640, 0, engine.SCREEN_WIDTH - 640, engine.BAR_HEIGHT)
    assert ink(frame(shown), top_right) is None


def test_a_watch_from_the_menu_beats_the_game_replays_it_and_goes_back(display, capsys):
    random.seed(3)  # the seed the menu's watch picks
    game = app.Game([gate(), gate()])
    while game.menu.population > 25:
        game.handle(click(game.menu.minus))
    game.handle(click(game.menu.buttons[app.WATCH]))
    shown = game.watching
    shown.hurry(math.inf)
    assert shown.learner.beaten and shown.replayed == 0
    assert shown.hint() == 'Replaying the whole game'

    game.advance(None, 10_000)
    assert shown.replayed == 1 and shown.runs.over
    assert shown.hint() == 'Every level beaten!   Q: quit'
    game.handle(press(watch.MENU_KEY))
    assert game.state is game.menu
