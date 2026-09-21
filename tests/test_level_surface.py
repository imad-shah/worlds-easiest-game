'''Tests for the pre-rendered level surface: the checkerboard floor and the safe zones.

These build the real surface and sample its pixels. The dummy video driver gives
`convert()` a display to match without opening a window.
'''

import pygame
import pytest

from worlds_easiest_game import engine, levels
from worlds_easiest_game.levels import level1


LIGHT = pygame.Color(engine.TILE_LIGHT)
DARK = pygame.Color(engine.TILE_DARK)
GREEN = pygame.Color(engine.GREEN)


@pytest.fixture(scope='module')
def surface():
    pygame.display.init()
    pygame.display.set_mode((1, 1))
    yield engine.build_level_surface(level1, engine.build_walls(level1.PLAYFIELD))
    pygame.display.quit()


def tile_center(col, row):
    '''The pixel at the middle of a tile of level 1's grid.'''
    ox, oy = engine.grid_origin(level1.PLAYFIELD)
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


def test_safe_regions_stay_solid_green(surface):
    inset = engine.WALL_THICKNESS
    for corners in level1.SAFE_REGIONS:
        region = engine.region_rect(*corners).inflate(-2 * inset, -2 * inset)
        for x in range(region.left, region.right, 7):
            for y in range(region.top, region.bottom, 7):
                assert surface.get_at((x, y)) == GREEN, (x, y)


@pytest.mark.parametrize('level', levels.LEVELS, ids=lambda level: level.__name__)
def test_every_wall_falls_on_a_grid_line(level):
    '''A level's walls must sit on its floor grid, or tiles get sliced by them.

    Walls are hand-placed in whole pixels, so allow a little slack -- anything
    under half a wall thickness is hidden underneath the wall.
    '''
    origin = engine.grid_origin(level.PLAYFIELD)
    for corner in level.PLAYFIELD:
        for coord, anchor in zip(corner, origin):
            offset = (coord - anchor) / engine.TILE_SIZE
            drift = abs(offset - round(offset)) * engine.TILE_SIZE
            assert drift < engine.WALL_THICKNESS / 2, f'{corner} is {drift:.1f}px off the grid'
