'''Tests for the game's two states: the menu it opens on, and the level it starts.

Events are built by hand and handed to the game, so the loop never runs. The
dummy video driver gives `convert()` a display to match without opening a window.
'''

import os
from collections import defaultdict

import pygame
import pytest

from worlds_easiest_game import engine, levels, obstacles
from worlds_easiest_game.levels import level1


@pytest.fixture(scope='module')
def display():
    os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
    pygame.display.init()
    pygame.font.init()
    pygame.display.set_mode((1, 1))
    yield
    pygame.font.quit()
    pygame.display.quit()


@pytest.fixture
def game(display):
    return engine.Game(levels.current_level())


def click(pos, button=1):
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pos, button=button)


def no_keys():
    '''Stand in for pygame.key.get_pressed() with nothing held down.'''
    return defaultdict(bool)


def dot_centers(play):
    return [dot.center for dot in play.dots]


def start_centers():
    return [dot.center for dot in obstacles.spawn(level1.OBSTACLES)]


def test_game_opens_on_the_menu(game):
    assert game.state is game.menu


def test_clicking_start_enters_the_level(game):
    game.handle(click(game.menu.start_button.center))
    assert game.state is game.play


def test_only_a_left_click_on_start_leaves_the_menu(game):
    button = game.menu.start_button
    game.handle(click((5, 5)))
    game.handle(click(button.center, button=3))
    game.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
    assert game.state is game.menu


def test_time_on_the_menu_does_not_move_the_level(game):
    game.update(30, no_keys())
    game.handle(click(game.menu.start_button.center))

    assert dot_centers(game.play) == start_centers()
    assert game.play.player.topleft == level1.PLAYER_SPAWN


def test_touching_an_obstacle_resets_player_and_obstacles(game):
    game.handle(click(game.menu.start_button.center))
    play = game.play
    play.update(0.2, no_keys())
    assert dot_centers(play) != start_centers(), 'the dots never moved'

    # Walk the player straight onto the first dot, then let one frame pass.
    x, y = play.dots[0].center
    play.pos.update(x, y)
    play.player.center = (round(x), round(y))
    play.update(0, no_keys())

    assert play.player.topleft == level1.PLAYER_SPAWN
    assert play.pos == pygame.Vector2(level1.PLAYER_SPAWN)
    assert dot_centers(play) == start_centers()


def test_a_frame_without_contact_does_not_reset(game):
    game.handle(click(game.menu.start_button.center))
    game.update(0.1, defaultdict(bool, {pygame.K_d: True}))

    assert game.play.player.x > level1.PLAYER_SPAWN[0], 'the player was sent back to spawn'
