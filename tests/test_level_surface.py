'''Tests for the pre-rendered level surface: the checkerboard floor and the safe zones.

These build the real surface and sample its pixels. The dummy video driver gives
`convert()` a display to match without opening a window.
'''

import os
from types import SimpleNamespace

import pygame
import pytest

from worlds_easiest_game import engine, levels
from worlds_easiest_game.levels import level1, level2, level3, level4, level5, level6, level7, level8


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
    return engine.build_level_surface(level, engine.level_walls(level))


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


def test_level3_is_a_four_by_four_board_with_one_tile_above_it(display):
    '''Columns 7-10 on rows 1-4, plus column 7 on row 0, with the middle two by two green.'''
    surface = build(level3)
    tiles = [(col, row) for col in range(7, 11) for row in range(1, 5)] + [(7, 0)]
    for col, row in tiles:
        if col in (8, 9) and row in (2, 3):
            expected = GREEN
        else:
            expected = LIGHT if (col + row) % 2 == 0 else DARK
        assert surface.get_at(tile_center(col, row)) == expected, (col, row)
    assert surface.get_at(tile_center(8, 0)) == pygame.Color(engine.BACKGROUND), 'no tile beside the extra one'


def test_level4_is_a_stepped_room_on_the_shared_board(display):
    '''Columns 5-12 on rows 0-7, stepped round, starting dark at its top-left tile as in the original.'''
    surface = build(level4)
    spans = {0: (7, 11), 1: (6, 12), 2: (5, 13), 3: (5, 13), 4: (5, 13), 5: (5, 13), 6: (6, 12), 7: (7, 11)}
    for row, (first, stop) in spans.items():
        for col in range(first, stop):
            expected = LIGHT if (col + row) % 2 == 0 else DARK
            assert surface.get_at(tile_center(col, row)) == expected, (col, row)
        for col in (first - 1, stop):
            if not (row in (3, 4) and col == 4):  # the exit, left of the middle rows
                assert surface.get_at(tile_center(col, row)) == pygame.Color(engine.BACKGROUND), (col, row)
    assert surface.get_at(tile_center(7, 0)) == DARK
    for col, row in [(8, -1), (9, -3), (2, 3), (4, 4)]:
        assert surface.get_at(tile_center(col, row)) == GREEN, (col, row)


# Level 5 tile by tile, as the original's frames show it: columns 0 to 16 on rows
# -2 to 7. S is the start zone, P a pocket where the spiral turns, G the goal, a
# dot floor and # empty space, both between corridors and around the spiral.
LEVEL5_TILES = """
SS..............P
###############.#
P.............#.#
##.##########.#.#
##.#.......G#.#.#
##.#.#.....G#.#.#
##.#.########.#.#
##.#..........#.#
##.############.#
##..............#
"""


def assert_tiles(surface, tile_map, left, top):
    '''Check every tile of `tile_map`, and a ring of empty space around it.

    The map's top-left mark is the tile at column `left` and row `top`: a dot is
    floor, # empty space or walls, and any letter a safe zone.
    '''
    rows = tile_map.split()
    tiles = {(left + col, top + row): mark
             for row, line in enumerate(rows) for col, mark in enumerate(line)}
    for col in range(left - 1, left + len(rows[0]) + 1):
        for row in range(top - 1, top + len(rows) + 1):
            mark = tiles.get((col, row), '#')
            if mark == '.':
                expected = LIGHT if (col + row) % 2 == 0 else DARK
            elif mark == '#':
                expected = pygame.Color(engine.BACKGROUND)
            else:
                expected = GREEN
            assert surface.get_at(tile_center(col, row)) == expected, (col, row, mark)


def test_level5_is_a_spiral_of_one_tile_corridors(display):
    assert_tiles(build(level5), LEVEL5_TILES, 0, -2)


def test_level6_has_two_checkerboard_corridors_with_a_green_turn(display):
    surface = build(level6)
    for col in range(18):
        for row in range(-2, 8):
            safe = (col < 2 and row < 0) or (col >= 14 and row in (2, 3)) or (
                col < 2 and row >= 6)
            floor = (col >= 2 and row in (*range(-2, 2), *range(4, 8)))
            if safe:
                expected = GREEN
            elif floor:
                expected = LIGHT if (col + row) % 2 == 0 else DARK
            else:
                expected = pygame.Color(engine.BACKGROUND)
            assert surface.get_at(tile_center(col, row)) == expected, (col, row)


def test_level7_room_is_a_twelve_by_eight_board_starting_light(display):
    '''Columns 3-14 on rows -1 to 6, its top-left tile light as in the original, between green zones.'''
    surface = build(level7)
    for col in range(3, 15):
        for row in range(-1, 7):
            expected = LIGHT if (col + row) % 2 == 0 else DARK
            assert surface.get_at(tile_center(col, row)) == expected, (col, row)
    for col in (*range(3), *range(15, 18)):
        for row in (2, 3):
            assert surface.get_at(tile_center(col, row)) == GREEN, (col, row)
        for row in (1, 4):
            assert surface.get_at(tile_center(col, row)) == pygame.Color(engine.BACKGROUND), (col, row)


# Level 8 tile by tile, as the original's frames show it: columns 3 to 14 on rows
# -2 to 7. S is the start, cut into the top-left square, and G the goal.
LEVEL8_TILES = """
....##....##
.S#....##.##
.##.##.##.##
....##....##
.##.##.##.GG
.##.##.##.GG
....##....##
.##.##.##.##
.##....##.##
....##....##
"""


def test_level8_is_two_blocks_of_corridors_around_wall_squares(display):
    assert_tiles(build(level8), LEVEL8_TILES, 3, -2)


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
    corners = [corner for outline in engine.level_outlines(level) for corner in outline]
    for corner in corners:
        for coord, anchor in zip(corner, engine.GRID_ORIGIN):
            offset = (coord - anchor) / engine.TILE_SIZE
            drift = abs(offset - round(offset)) * engine.TILE_SIZE
            assert drift < engine.WALL_THICKNESS / 2, f'{corner} is {drift:.1f}px off the grid'
