'''Tests for the developer-only god mode: the T toggle and dot contact while it is on.

No play is scripted: the toggle is driven by single key events, and dot contact
is checked by placing a dot on the player directly. The dummy video driver gives
the surfaces a display to convert to without opening a window.
'''

import os
from collections import defaultdict

import pygame
import pytest

from worlds_easiest_game import engine
from worlds_easiest_game.levels import level1

NO_KEYS = defaultdict(bool)


@pytest.fixture(scope='module')
def display():
    os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
    pygame.init()
    pygame.display.set_mode((engine.SCREEN_WIDTH, engine.SCREEN_HEIGHT))
    yield
    pygame.quit()


def press(key):
    return pygame.event.Event(pygame.KEYDOWN, key=key)


def test_t_does_nothing_without_dev(display):
    game = engine.Game([level1])
    game.start_level(0)
    game.handle(press(pygame.K_t))
    assert not game.god_mode
    assert not game.play.god_mode


def test_t_toggles_once_per_press_in_dev(display):
    game = engine.Game([level1], dev=True)
    game.start_level(0)
    game.handle(press(pygame.K_t))
    assert game.play.god_mode
    game.handle(pygame.event.Event(pygame.KEYUP, key=pygame.K_t))
    assert game.play.god_mode
    game.handle(press(pygame.K_t))
    assert not game.play.god_mode


def test_t_is_ignored_off_a_level(display):
    game = engine.Game([level1], dev=True)
    game.handle(press(pygame.K_t))
    assert not game.god_mode


def test_god_mode_carries_into_the_next_level(display):
    game = engine.Game([level1, level1], dev=True)
    game.start_level(0)
    game.handle(press(pygame.K_t))
    game.start_level(1)
    assert game.play.god_mode


def touch_a_dot(play):
    '''Put the player squarely on the first dot.'''
    play.player.center = [round(c) for c in play.dots[0].center]
    play.pos.update(play.player.topleft)


def test_dot_contact_resets_without_god_mode(display):
    play = engine.Play(level1)
    play.coins = play.coins[1:]
    touch_a_dot(play)
    play.update(0, NO_KEYS)
    assert play.coins == list(level1.COINS)
    assert play.player.topleft == tuple(level1.PLAYER_SPAWN)


def test_dot_contact_does_nothing_in_god_mode(display):
    play = engine.Play(level1)
    play.god_mode = True
    play.coins = play.coins[1:]
    dots = play.dots
    touch_a_dot(play)
    spot = play.player.topleft
    play.update(0, NO_KEYS)
    assert play.dots is dots
    assert play.coins == list(level1.COINS)[1:]
    assert play.player.topleft != tuple(level1.PLAYER_SPAWN)
    assert play.player.topleft == spot
