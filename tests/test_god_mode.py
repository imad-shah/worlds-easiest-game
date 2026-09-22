'''Tests for the developer-only god mode's T toggle.

No play is scripted: the toggle is driven by single key events. The dummy video
driver gives the surfaces a display to convert to without opening a window.
'''

import os

import pygame
import pytest

from worlds_easiest_game import engine
from worlds_easiest_game.levels import level1


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

