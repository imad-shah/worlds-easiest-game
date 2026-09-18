'''Tests for the level data and the collision geometry derived from it.

The game module is imported for its data and pure helpers only -- nothing here
opens a window, so the suite runs headless (the workflow still pins
SDL_VIDEODRIVER=dummy, since importing pygame is enough to want a safe default).
'''

from collections import defaultdict

import pygame
import pytest

from game import main as game


# The names the game loop reads out of the level data. Renaming or dropping one
# of these breaks the loop, so pin them here.
LEVEL_NAMES = ('PLAYFIELD', 'PATH_REGIONS', 'SAFE_REGIONS', 'PLAYER_SPAWN')


@pytest.mark.parametrize('name', LEVEL_NAMES)
def test_level_supplies_the_names_the_loop_needs(name):
    assert hasattr(game, name), f'the game loop reads {name} off the level data'


def test_playfield_is_a_closed_axis_aligned_polygon():
    polygon = game.PLAYFIELD
    edges = list(zip(polygon, polygon[1:] + polygon[:1]))
    for start, end in edges:
        assert (start[0] == end[0]) != (start[1] == end[1]), (
            f'edge {start}->{end} is neither horizontal nor vertical'
        )


def test_build_walls_makes_one_wall_per_edge_centered_on_it():
    walls = game.build_walls(game.PLAYFIELD, thickness=6)

    assert len(walls) == len(game.PLAYFIELD)
    # The top edge of the left room, walked left to right, grown by half the
    # thickness on every side so it overhangs into both corners.
    assert walls[0] == pygame.Rect(114, 156, 129, 6)
    # The left edge, walked bottom to top, back to the starting corner.
    assert walls[-1] == pygame.Rect(114, 156, 6, 253)


def test_walls_close_every_corner():
    '''Consecutive walls must overlap, or the player leaks out at a corner.'''
    walls = game.build_walls(game.PLAYFIELD)
    for i, wall in enumerate(walls):
        nxt = walls[(i + 1) % len(walls)]
        assert wall.colliderect(nxt), f'gap between wall {i} and wall {i + 1}'


def test_spawn_sits_in_open_space():
    player = pygame.Rect(game.PLAYER_SPAWN, game.PLAYER_SIZE)
    assert player.collidelist(game.WALLS) == -1, 'the player spawns inside a wall'


def test_move_player_slides_along_a_wall_instead_of_sticking():
    '''Pushing diagonally into a wall should still move along the free axis.'''
    wall = pygame.Rect(200, 0, 6, 400)
    pos = pygame.Vector2(100, 100)
    player = pygame.Rect(100, 100, 29, 29)

    for _ in range(20):
        game.move_player(pos, player, 10, 10, [wall])

    assert player.right == wall.left, 'the player did not stop flush against the wall'
    assert player.y == 300, 'the blocked axis also stopped the free one'
    assert pos.x == player.x, 'the float position drifted away from the rect'


def pressed(*keys):
    '''Stand in for pygame.key.get_pressed(): every other key reads as up.'''
    return defaultdict(bool, {key: True for key in keys})


def test_read_input_keeps_diagonals_the_same_speed():
    straight = game.read_input(pressed(pygame.K_d))
    diagonal = game.read_input(pressed(pygame.K_d, pygame.K_s))

    assert straight.length() == pytest.approx(game.PLAYER_SPEED)
    assert diagonal.length() == pytest.approx(game.PLAYER_SPEED)
    assert game.read_input(pressed()).length_squared() == 0
