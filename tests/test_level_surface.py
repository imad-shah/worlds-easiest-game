'''Tests for the pre-rendered level surface: the checkerboard floor and the safe zones.

These build the real surface and sample its pixels. The dummy video driver gives
`convert()` a display to match without opening a window.
'''

import os
from types import SimpleNamespace

import pygame
import pytest

from worlds_easiest_game import engine, levels
from worlds_easiest_game.levels import level1, level2


LIGHT = pygame.Color(engine.TILE_LIGHT)
DARK = pygame.Color(engine.TILE_DARK)
GREEN = pygame.Color(engine.GREEN)


@pytest.fixture(scope='module')
def display():
    os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
    pygame.display.init()
    pygame.display.set_mode((1, 1))
    yield
    pygame.display.quit()


def build(level):
    return engine.build_level_surface(level, engine.build_walls(level.PLAYFIELD))


@pytest.fixture(scope='module')
def surface(display):
    return build(level1)


def tile_corner(col, row):
    '''The top-left pixel of a tile of the floor board.'''
    ox, oy = engine.GRID_ORIGIN
    return round(ox + col * engine.TILE_SIZE), round(oy + row * engine.TILE_SIZE)


def tile_center(col, row):
    '''The pixel at the middle of a tile of the floor board.'''
    ox, oy = engine.GRID_ORIGIN
    return (round(ox + (col + 0.5) * engine.TILE_SIZE),
            round(oy + (row + 0.5) * engine.TILE_SIZE))


def test_path_tiles_alternate_colors(surface):
    '''Every tile of the middle corridor (columns 4-13, rows 1-4) alternates.'''
    for col in range(4, 14):
        for row in range(1, 5):
            expected = LIGHT if (col + row) % 2 == 0 else DARK
            assert surface.get_at(tile_center(col, row)) == expected, (col, row)


@pytest.mark.parametrize('inside, outside', [
    ((284, 386), (278, 386)),  # bottom-left passage, below the corridor's left wall
    ((698, 180), (691, 180)),  # top-right passage, above the corridor's right wall
])
def test_passage_tiles_change_color_where_the_corridor_wall_would_be(surface, inside, outside):
    '''As in the original, the grid lines up with the walls in the narrow passages.'''
    colors = {tuple(surface.get_at(inside)), tuple(surface.get_at(outside))}
    assert colors == {tuple(LIGHT), tuple(DARK)}


@pytest.mark.parametrize('level', levels.LEVELS, ids=lambda level: level.__name__)
def test_safe_regions_stay_solid_green(display, level):
    surface = build(level)
    inset = engine.WALL_THICKNESS
    for corners in level.SAFE_REGIONS:
        region = engine.region_rect(*corners).inflate(-2 * inset, -2 * inset)
        for x in range(region.left, region.right, 7):
            for y in range(region.top, region.bottom, 7):
                assert surface.get_at((x, y)) == GREEN, (x, y)


def test_level2_room_is_a_twelve_by_six_board_starting_dark(display):
    '''The room spans tile columns 3-14 and all six rows, its top-left tile dark as in the original.'''
    surface = build(level2)
    for col in range(3, 15):
        for row in range(6):
            expected = LIGHT if (col + row) % 2 == 0 else DARK
            assert surface.get_at(tile_center(col, row)) == expected, (col, row)


def test_board_is_fixed_to_the_canvas_not_to_the_level(display):
    '''A course that starts on a dark tile of the board keeps it dark.

    Level 3 of the original sits 7 tiles right of level 1, so its top-left tile is dark.
    '''
    (left, top), (right, bottom) = tile_corner(7, 0), tile_corner(9, 2)
    level = SimpleNamespace(
        PLAYFIELD=[(left, top), (right, top), (right, bottom), (left, bottom)],
        PATH_REGIONS=[((left, top), (right, bottom))],
        SAFE_REGIONS=[],
    )
    surface = engine.build_level_surface(level, engine.build_walls(level.PLAYFIELD))
    assert surface.get_at(tile_center(7, 0)) == DARK
    assert surface.get_at(tile_center(8, 0)) == LIGHT


@pytest.mark.parametrize('level', levels.LEVELS, ids=lambda level: level.__name__)
def test_every_wall_falls_on_a_grid_line(level):
    '''A level's walls must sit on the floor board's grid, or tiles get sliced by them.

    Walls are hand-placed in whole pixels, so allow a little slack -- anything
    under half a wall thickness is hidden underneath the wall.
    '''
    for corner in level.PLAYFIELD:
        for coord, anchor in zip(corner, engine.GRID_ORIGIN):
            offset = (coord - anchor) / engine.TILE_SIZE
            drift = abs(offset - round(offset)) * engine.TILE_SIZE
            assert drift < engine.WALL_THICKNESS / 2, f'{corner} is {drift:.1f}px off the grid'
