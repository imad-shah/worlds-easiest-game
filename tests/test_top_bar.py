'''Tests for the black bar across the top of the window: its labels' text and where it draws them.

These draw the real bar and a level frame and sample their pixels. The dummy video
driver gives the surfaces a display to convert to without opening a window.
'''

import os

import pygame
import pytest

from worlds_easiest_game import app, engine, levels
from worlds_easiest_game.levels import level1


@pytest.fixture(scope='module')
def display():
    os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
    pygame.init()
    pygame.display.set_mode((engine.SCREEN_WIDTH, engine.WINDOW_HEIGHT))
    yield
    pygame.quit()


@pytest.mark.parametrize('collected, total, text', [
    (0, 0, 'COINS: 0/0'),
    (1, 3, 'COINS: 1/3'),
    (3, 3, 'COINS: 3/3'),
])
def test_coin_text(collected, total, text):
    assert engine.coin_text(collected, total) == text


@pytest.mark.parametrize('number, total, text', [(1, 5, 'LEVEL 1/5'), (3, 30, 'LEVEL 3/30')])
def test_level_text(number, total, text):
    assert engine.level_text(number, total) == text


@pytest.mark.parametrize('deaths, text', [(0, 'DEATHS: 0'), (1, 'DEATHS: 1'), (108, 'DEATHS: 108')])
def test_death_text(deaths, text):
    assert engine.death_text(deaths) == text


def ink(surface, area):
    '''The bounding box of the white text inside `area` of a black bar.'''
    xs, ys = [], []
    for x in range(area.left, area.right):
        for y in range(area.top, area.bottom):
            if surface.get_at((x, y))[:3] != (0, 0, 0):
                xs.append(x)
                ys.append(y)
    return pygame.Rect(min(xs), min(ys), max(xs) - min(xs) + 1, max(ys) - min(ys) + 1)


@pytest.fixture(scope='module')
def bar(display):
    surface = pygame.Surface((engine.SCREEN_WIDTH, engine.WINDOW_HEIGHT))
    surface.fill(engine.BACKGROUND)
    engine.TopBar().draw(surface, 'COINS: 1/3', '3/5', 'DEATHS: 108')
    return surface


def thirds():
    third = engine.SCREEN_WIDTH // 3
    return [pygame.Rect(i * third, 0, third, engine.BAR_HEIGHT) for i in range(3)]


def test_bar_is_black_across_the_top_and_ends_at_the_play_area(bar):
    for x in (0, engine.SCREEN_WIDTH // 2, engine.SCREEN_WIDTH - 1):
        assert bar.get_at((x, 0)) == pygame.Color(engine.BLACK)
        assert bar.get_at((x, engine.BAR_HEIGHT - 1)) == pygame.Color(engine.BLACK)
        assert bar.get_at((x, engine.BAR_HEIGHT)) == pygame.Color(engine.BACKGROUND)


def test_labels_sit_left_middle_and_right_on_one_line(bar):
    left, middle, right = (ink(bar, third) for third in thirds())
    assert left.left == engine.BAR_MARGIN
    assert abs(middle.centerx - engine.SCREEN_WIDTH // 2) <= 1
    assert right.right == engine.SCREEN_WIDTH - engine.BAR_MARGIN
    # All capitals and digits, so one baseline means one top and one bottom,
    # and the line is centered in the bar.
    assert left.top == middle.top == right.top
    assert left.bottom == middle.bottom == right.bottom
    assert left.top == engine.BAR_HEIGHT - left.bottom


def test_labels_are_white(bar):
    left = ink(bar, thirds()[0])
    colors = {tuple(bar.get_at((x, y))) for x in range(left.left, left.right)
              for y in range(left.top, left.bottom)}
    assert tuple(pygame.Color(engine.WHITE)) in colors


def draw_level(god_mode):
    game = app.Game(levels.LEVELS)
    game.start_level(0)
    game.play.god_mode = god_mode
    window = pygame.Surface((engine.SCREEN_WIDTH, engine.WINDOW_HEIGHT))
    game.draw(window)
    return game, window


def test_a_level_is_drawn_below_the_bar(display):
    '''The play area starts under the bar, so every level coordinate keeps its place in it.'''
    game, window = draw_level(god_mode=False)
    level = game.play.level_surface
    for point in [(0, 0), (engine.SCREEN_WIDTH - 1, engine.SCREEN_HEIGHT - 1),
                  engine.region_rect(*level1.GOAL).center, level1.PLAYFIELD[0]]:
        x, y = point
        assert window.get_at((x, y + engine.BAR_HEIGHT)) == level.get_at(point), point
    assert ink(window, thirds()[0]).left == engine.BAR_MARGIN


def test_god_mode_label_sits_in_the_play_area_clear_of_the_bar(display):
    _, plain = draw_level(god_mode=False)
    _, god = draw_level(god_mode=True)
    bar = pygame.Rect(0, 0, engine.SCREEN_WIDTH, engine.BAR_HEIGHT)
    changed = [(x, y) for x in range(engine.SCREEN_WIDTH) for y in range(0, engine.WINDOW_HEIGHT, 2)
               if plain.get_at((x, y)) != god.get_at((x, y))]
    assert changed, 'no GOD MODE label drawn'
    assert not any(bar.collidepoint(point) for point in changed)
    # Bottom left of the play area, below every course.
    assert all(x < engine.SCREEN_WIDTH // 3 and y > engine.BAR_HEIGHT + max(
        corner[1] for level in levels.LEVELS for corner in level.PLAYFIELD) for x, y in changed)


def test_menu_and_win_screens_fill_the_window(display):
    game = app.Game(levels.LEVELS)
    for screen in (game.menu, game.won):
        assert screen.surface.get_size() == (engine.SCREEN_WIDTH, engine.WINDOW_HEIGHT)
        for button in screen.buttons.values():
            assert screen.surface.get_rect().contains(button)


def test_the_window_is_titled_with_the_games_name(display):
    engine.open_window()

    assert pygame.display.get_caption()[0] == "World's Easiest Game"
