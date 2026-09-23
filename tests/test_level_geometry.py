'''Tests for the level data and the collision geometry derived from it.

The engine and the level data are imported for their constants and pure helpers
only -- nothing here opens a window or needs a display.
'''

import math
from collections import defaultdict

import pygame
import pytest

from worlds_easiest_game import engine, levels, obstacles
from worlds_easiest_game.levels import level1, level2, level3, level4, level5, level6, level7, level8, level9
from worlds_easiest_game.obstacles import circle_touches_rect

# The names the game loop reads out of the level data. Renaming or dropping one
# of these breaks the loop, so pin them here for every registered level.
LEVEL_NAMES = ('PLAYFIELD', 'PATH_REGIONS', 'SAFE_REGIONS', 'GOAL', 'PLAYER_SPAWN', 'COINS',
               'OBSTACLES')


@pytest.mark.parametrize('level', levels.LEVELS, ids=lambda level: level.__name__)
@pytest.mark.parametrize('name', LEVEL_NAMES)
def test_level_supplies_the_names_the_loop_needs(name, level):
    assert hasattr(level, name), f'the game loop reads {name} off the level data'


@pytest.mark.parametrize('level', levels.LEVELS, ids=lambda level: level.__name__)
def test_every_outline_is_a_closed_axis_aligned_polygon(level):
    for polygon in engine.level_outlines(level):
        edges = list(zip(polygon, polygon[1:] + polygon[:1]))
        for start, end in edges:
            assert (start[0] == end[0]) != (start[1] == end[1]), (
                f'edge {start}->{end} is neither horizontal nor vertical'
            )


def test_build_walls_makes_one_wall_per_edge_centered_on_it():
    walls = engine.build_walls(level1.PLAYFIELD, thickness=6)

    assert len(walls) == len(level1.PLAYFIELD)
    # The top edge of the left room, walked left to right, grown by half the
    # thickness on every side so it overhangs into both corners.
    assert walls[0] == pygame.Rect(114, 156, 129, 6)
    # The left edge, walked bottom to top, back to the starting corner.
    assert walls[-1] == pygame.Rect(114, 156, 6, 253)


@pytest.mark.parametrize('level', levels.LEVELS, ids=lambda level: level.__name__)
def test_walls_close_every_corner(level):
    '''Consecutive walls must overlap, or the player leaks out at a corner.'''
    for outline in engine.level_outlines(level):
        walls = engine.build_walls(outline)
        for i, wall in enumerate(walls):
            nxt = walls[(i + 1) % len(walls)]
            assert wall.colliderect(nxt), f'gap between wall {i} and wall {i + 1} of {outline}'


@pytest.mark.parametrize('level', levels.LEVELS, ids=lambda level: level.__name__)
def test_spawn_sits_in_open_space(level):
    walls = engine.level_walls(level)
    player = pygame.Rect(level.PLAYER_SPAWN, engine.PLAYER_SIZE)
    assert player.collidelist(walls) == -1, 'the player spawns inside a wall'


@pytest.mark.parametrize('level', levels.LEVELS, ids=lambda level: level.__name__)
def test_spawn_is_in_a_safe_zone(level):
    player = pygame.Rect(level.PLAYER_SPAWN, engine.PLAYER_SIZE)
    assert any(engine.region_rect(*corners).contains(player) for corners in level.SAFE_REGIONS), (
        'the player does not start in a safe zone'
    )


def test_levels_1_and_2_start_in_the_left_safe_zone():
    for level in (level1, level2):
        leftmost = min((engine.region_rect(*corners) for corners in level.SAFE_REGIONS),
                       key=lambda region: region.left)
        assert leftmost.contains(pygame.Rect(level.PLAYER_SPAWN, engine.PLAYER_SIZE)), level.__name__


@pytest.mark.parametrize('level', levels.LEVELS, ids=lambda level: level.__name__)
def test_goal_is_a_safe_zone_the_level_cannot_start_finished_on(level):
    '''A goal the player spawns on only finishes the level once a coin has been fetched.'''
    assert level.GOAL in level.SAFE_REGIONS, 'the goal is not one of the safe zones'
    player = pygame.Rect(level.PLAYER_SPAWN, engine.PLAYER_SIZE)
    if player.colliderect(engine.region_rect(*level.GOAL)):
        assert level.COINS, 'the level starts finished'


@pytest.mark.parametrize('level', levels.LEVELS, ids=lambda level: level.__name__)
def test_coins_sit_on_the_floor_clear_of_walls(level):
    walls = engine.level_walls(level)
    floor = [engine.region_rect(*corners) for corners in level.PATH_REGIONS + level.SAFE_REGIONS]
    for coin in level.COINS:
        assert any(region.collidepoint(coin) for region in floor), f'{coin} is off the course'
        assert not any(circle_touches_rect(coin, engine.COIN_RADIUS, wall) for wall in walls), (
            f'{coin} overlaps a wall'
        )


def test_level2_coin_is_in_the_middle_of_the_room():
    (left, top), (right, bottom) = level2.PATH_REGIONS[0]
    [coin] = level2.COINS
    assert coin == pytest.approx(((left + right) / 2, (top + bottom) / 2), abs=1)
    assert level1.COINS == [], 'level 1 has no coins in the original'


def test_level2_dots_each_own_a_column_and_alternate_rows():
    '''Six dots start by the top wall and six by the bottom, in alternating columns.'''
    starts = sorted(dot.route[0] for dot in level2.OBSTACLES)
    assert len({x for x, _ in starts}) == 12, 'two dots share a column'
    top, bottom = min(y for _, y in starts), max(y for _, y in starts)
    rows = [y for _, y in starts]
    assert rows == [bottom, top] * 6, 'the rows do not alternate, starting at the left'
    gaps = {b[0] - a[0] for a, b in zip(starts, starts[1:])}
    assert max(gaps) - min(gaps) <= 1, 'the columns are not evenly spaced'
    for dot in level2.OBSTACLES:
        assert {y for _, y in dot.route} == {top, bottom}, f'{dot} does not cross the room'


def test_level3_coin_is_in_the_extra_tile():
    '''The one coin sits in the middle of the tile above the course's top-left corner.'''
    (left, top), (right, bottom) = level3.PATH_REGIONS[0]
    [coin] = level3.COINS
    assert coin == pytest.approx(((left + right) / 2, (top + bottom) / 2), abs=1)


def test_level3_goal_is_the_zone_the_player_starts_in():
    [zone] = level3.SAFE_REGIONS
    player = pygame.Rect(level3.PLAYER_SPAWN, engine.PLAYER_SIZE)
    assert level3.GOAL == zone
    assert engine.region_rect(*zone).contains(player)


def test_level3_ring_turns_clockwise_with_a_one_dot_gap():
    '''Eleven dots share one route around the safe zone, a tile apart, with one slot empty.'''
    [route] = {dot.route for dot in level3.OBSTACLES}
    assert len({dot.speed for dot in level3.OBSTACLES}) == 1, 'the ring does not turn as one'
    assert len(level3.OBSTACLES) == 11
    (x0, y0), (x1, y1) = route[0], route[1]
    assert y0 == y1 and x1 > x0, 'the ring does not start clockwise, rightward along the top'
    safe = engine.region_rect(*level3.SAFE_REGIONS[0])
    assert (min(x for x, _ in route) < safe.left and max(x for x, _ in route) > safe.right
            and min(y for _, y in route) < safe.top and max(y for _, y in route) > safe.bottom), (
        'the ring does not go around the safe zone'
    )
    assert level3.OBSTACLES[0].length / 12 == pytest.approx(engine.TILE_SIZE, abs=1), (
        'twelve dots spaced a tile apart would not fill the ring'
    )
    slots = sorted(dot.start * 12 for dot in level3.OBSTACLES)
    spacing = [b - a for a, b in zip(slots, slots[1:] + [slots[0] + 12])]
    assert sorted(spacing) == pytest.approx([1] * 10 + [2]), 'the dots are not a tile apart with one gap'


def tile_line(col=None, row=None):
    '''The pixel a grid line of the floor board falls on, rounded as the walls are.'''
    ox, oy = engine.GRID_ORIGIN
    return round(ox + col * engine.TILE_SIZE) if row is None else round(oy + row * engine.TILE_SIZE)


def test_level4_room_is_a_stepped_circle_with_zones_above_and_left():
    '''Rows 4, 6, 8, 8, 8, 8, 6 and 4 tiles wide, centered on grid column line 9.'''
    rows = sorted(level4.PATH_REGIONS, key=lambda corners: corners[0][1])
    widths = []
    for (left, top), (right, bottom) in rows:
        tiles = round((bottom - top) / engine.TILE_SIZE)
        widths += [round((right - left) / engine.TILE_SIZE)] * tiles
        assert (left + right) / 2 == pytest.approx(tile_line(col=9), abs=1), 'a row is off center'
    assert widths == [4, 6, 8, 8, 8, 8, 6, 4]
    assert rows[0][0][1] == tile_line(row=0) and rows[-1][1][1] == tile_line(row=8)

    start = engine.region_rect(*level4.SAFE_REGIONS[0])
    assert (start.left, start.right - 1, start.top, start.bottom - 1) == (
        tile_line(col=8), tile_line(col=10), tile_line(row=-3), tile_line(row=0)
    ), 'the start zone is not two tiles wide and three tall above the room'
    goal = engine.region_rect(*level4.GOAL)
    assert (goal.left, goal.right - 1, goal.top, goal.bottom - 1) == (
        tile_line(col=2), tile_line(col=5), tile_line(row=3), tile_line(row=5)
    ), 'the exit is not three tiles wide on the room\'s middle two rows, left of it'
    assert level4.GOAL in level4.SAFE_REGIONS and level4.GOAL != level4.SAFE_REGIONS[0]


def test_level4_starts_just_above_the_room_in_its_middle():
    player = pygame.Rect(level4.PLAYER_SPAWN, engine.PLAYER_SIZE)
    assert engine.region_rect(*level4.SAFE_REGIONS[0]).contains(player)
    assert player.centerx == pytest.approx(tile_line(col=9), abs=1)
    assert 0 < tile_line(row=0) - player.bottom < engine.TILE_SIZE / 2


def test_level4_coins_sit_three_tiles_above_right_of_and_below_the_middle():
    cx, cy = level4.CENTER
    assert (cx, cy) == (tile_line(col=9), tile_line(row=4))
    three = 3 * engine.TILE_SIZE
    expected = [(cx, cy - three), (cx + three, cy), (cx, cy + three)]
    assert len(level4.COINS) == 3
    for coin, spot in zip(level4.COINS, expected):
        assert coin == pytest.approx(spot, abs=1)


def test_level4_cross_spins_clockwise_with_its_tips_over_the_steps():
    '''21 dots: four arms of five around a center dot on the middle of the room.'''
    assert len(level4.OBSTACLES) == 21
    assert {(dot.center, dot.speed > 0) for dot in level4.OBSTACLES} == {(level4.CENTER, True)}
    reach = max(dot.radius for dot in level4.OBSTACLES)
    # The steps' inner corners are 2 tiles across and 3 along from the middle.
    step_corner = math.hypot(2, 3) * engine.TILE_SIZE
    assert step_corner - obstacles.RADIUS < reach < step_corner, (
        'the tips do not pass over the stepped corners without reaching past them'
    )


def region_tiles(corners):
    """A region's (left, top, right, bottom) in tile lines of the floor board."""
    (left, top), (right, bottom) = corners
    ox, oy = engine.GRID_ORIGIN
    return tuple(round((coord - anchor) / engine.TILE_SIZE)
                 for coord, anchor in zip((left, top, right, bottom), (ox, oy, ox, oy)))


def test_level5_starts_at_the_top_left_and_ends_in_the_middle():
    """A 2-tile start zone at the top corridor's left end, the 1-by-2 goal in the spiral's middle."""
    start, *_ = level5.SAFE_REGIONS
    assert region_tiles(start) == (0, -2, 2, -1)
    assert engine.region_rect(*start).contains(pygame.Rect(level5.PLAYER_SPAWN, engine.PLAYER_SIZE))
    assert region_tiles(level5.GOAL) == (11, 2, 12, 4)
    pockets = sorted(region_tiles(corners) for corners in level5.SAFE_REGIONS[1:] if corners != level5.GOAL)
    assert pockets == [(0, 0, 1, 1), (16, -2, 17, -1)], 'the pockets are not at the spiral\'s two turns'
    assert level5.COINS == [], 'level 5 has no coins in the original'


def test_level5_cross_turns_clockwise_with_player_sized_gaps_in_its_arms():
    """16 dots, four arms of four around an empty center, 1.5 to 7.5 tiles out."""
    assert len(level5.OBSTACLES) == 16
    assert {(dot.center, dot.speed > 0) for dot in level5.OBSTACLES} == {(level5.CENTER, True)}
    assert level5.CENTER == (tile_line(col=9), tile_line(row=3))
    assert all(dot.radius > 0 for dot in level5.OBSTACLES), 'a dot sits on the center'
    arms = defaultdict(list)
    for dot in level5.OBSTACLES:
        arms[dot.angle % 360].append(dot.radius)
    assert len(arms) == 4 and len({round(angle % 90, 6) for angle in arms}) == 1, 'the arms are not a cross'
    for radii in arms.values():
        tiles = [radius / engine.TILE_SIZE for radius in sorted(radii)]
        assert tiles == pytest.approx([1.5, 3.5, 5.5, 7.5], abs=0.03)
        gap = (sorted(radii)[1] - sorted(radii)[0]) - 2 * obstacles.RADIUS
        assert max(engine.PLAYER_SIZE) < gap < 2 * engine.TILE_SIZE, 'the player cannot slip between two dots'
    # The tips reach past the top of the course, 5 tiles above the center.
    top = min(y for _, y in level5.PLAYFIELD)
    assert max(dot.radius for dot in level5.OBSTACLES) > level5.CENTER[1] - top + obstacles.RADIUS


def test_level6_zones_and_coins_follow_the_two_corridors():
    assert [region_tiles(corners) for corners in level6.PATH_REGIONS] == [
        (2, -2, 18, 2), (2, 4, 18, 8),
    ]
    assert [region_tiles(corners) for corners in level6.SAFE_REGIONS] == [
        (0, -2, 2, 0), (14, 2, 18, 4), (0, 6, 2, 8),
    ]
    assert level6.GOAL == level6.SAFE_REGIONS[-1]
    assert engine.region_rect(*level6.SAFE_REGIONS[0]).contains(
        pygame.Rect(level6.PLAYER_SPAWN, engine.PLAYER_SIZE))
    assert len(level6.COINS) == 4
    for col, coin in zip((2.5, 6.5, 10.5, 14.5), level6.COINS):
        assert coin == pytest.approx((tile_line(col=col), tile_line(row=4.5)), abs=1)


def test_level6_crosses_have_one_shared_phase_and_speed():
    assert len(level6.OBSTACLES) == 8 * 9
    centers = {(tile_line(col=col), tile_line(row=row))
               for row in (0, 6) for col in (4, 8, 12, 16)}
    assert set(level6.CENTERS) == centers
    assert {dot.center for dot in level6.OBSTACLES} == centers
    assert {dot.speed for dot in level6.OBSTACLES} == {60}
    for center in centers:
        dots = [dot for dot in level6.OBSTACLES if dot.center == center]
        assert sorted(dot.radius for dot in dots) == [0] + [34] * 4 + [68] * 4
        assert {dot.angle % 90 for dot in dots} == {78}, 'the crosses do not start in phase'
    for seconds in (0, 0.4, 1.25):
        offsets = [
            tuple((round(x - center[0], 6), round(y - center[1], 6))
                  for dot in level6.OBSTACLES if dot.center == center
                  for x, y in [dot.position(seconds)])
            for center in level6.CENTERS
        ]
        assert all(offset == offsets[0] for offset in offsets[1:]), 'the crosses drift out of sync'


def test_level7_is_level2s_room_two_rows_taller_with_a_coin_in_each_corner():
    assert [region_tiles(corners) for corners in level7.PATH_REGIONS] == [(3, -1, 15, 7)]
    assert [region_tiles(corners) for corners in level7.SAFE_REGIONS] == [(0, 2, 3, 4), (15, 2, 18, 4)]
    assert level7.GOAL == level7.SAFE_REGIONS[1]
    assert engine.region_rect(*level7.SAFE_REGIONS[0]).contains(
        pygame.Rect(level7.PLAYER_SPAWN, engine.PLAYER_SIZE))
    corners = [(3.5, -0.5), (3.5, 6.5), (14.5, 6.5), (14.5, -0.5)]
    assert len(level7.COINS) == 4
    for (col, row), coin in zip(corners, level7.COINS):
        assert coin == pytest.approx((tile_line(col=col), tile_line(row=row)), abs=1)


def test_level7_dots_cross_the_room_in_alternating_columns():
    """One dot per room column, running the full height, level 2's margin short of each wall."""
    starts = sorted(dot.route[0] for dot in level7.OBSTACLES)
    assert [x for x, _ in starts] == pytest.approx(
        [tile_line(col=col + 0.5) for col in range(3, 15)], abs=1), 'not one dot per room column'
    top, bottom = tile_line(row=-1) + 26, tile_line(row=7) - 26
    assert [y for _, y in starts] == [top, bottom] * 6, 'the room\'s first column does not start at the top'
    assert {dot.speed for dot in level7.OBSTACLES} == {300}
    for dot in level7.OBSTACLES:
        assert {y for _, y in dot.route} == {top, bottom}, f'{dot} does not cross the room'
    # Halfway down, the two rows pass each other in the middle of the room.
    middle = level7.OBSTACLES[0].period / 4
    assert {round(dot.position(middle)[1]) for dot in level7.OBSTACLES} == {(top + bottom) / 2}


def test_level8_starts_in_a_notch_and_ends_right_of_the_course():
    """The start is the tile cut into the top-left square, the goal two by two off the right block."""
    start, goal = level8.SAFE_REGIONS
    assert region_tiles(start) == (4, -1, 5, 0)
    assert engine.region_rect(*start).contains(pygame.Rect(level8.PLAYER_SPAWN, engine.PLAYER_SIZE))
    assert level8.GOAL == goal and region_tiles(goal) == (13, 2, 15, 4)
    assert len(level8.INNER_WALLS) == 7, 'six squares and the wall between the blocks'


def test_level8_coins_sit_in_three_corner_tiles():
    corners = [(3.5, 7.5), (12.5, -1.5), (12.5, 7.5)]  # bottom left, top right, bottom right
    assert len(level8.COINS) == 3
    for (col, row), coin in zip(corners, level8.COINS):
        assert coin == (tile_line(col=col), tile_line(row=row))


def clockwise(route):
    """Whether a route turns clockwise on screen, where y grows downward."""
    return sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(route, route[1:] + route[:1])) > 0


def route_tiles(route):
    """A route's bounding box, (left, top, right, bottom), in tiles of the floor board."""
    xs, ys = [x for x, _ in route], [y for _, y in route]
    ox, oy = engine.GRID_ORIGIN
    return tuple((coord - anchor) / engine.TILE_SIZE
                 for coord, anchor in zip((min(xs), min(ys), max(xs), max(ys)), (ox, oy, ox, oy)))


def test_level8_side_dots_circle_their_squares_in_step_and_mirrored():
    """Three dots clockwise round the left squares, three anticlockwise round the right ones."""
    assert len(level8.OBSTACLES) == 7
    left, right, [middle] = level8.OBSTACLES[:3], level8.OBSTACLES[3:6], level8.OBSTACLES[6:]
    for dots, first_col, turns_clockwise in ((left, 3.5, True), (right, 9.5, False)):
        for dot, top_row in zip(dots, (-1.5, 1.5, 4.5)):
            # Along the middles of the corridors round a two-by-two square.
            assert route_tiles(dot.route) == pytest.approx(
                (first_col, top_row, first_col + 3, top_row + 3), abs=0.02)
            assert clockwise(dot.route) == turns_clockwise
    assert {dot.speed for dot in left + right} == {150}
    assert len({dot.length for dot in left + right}) == 1, 'the loops drift apart'

    mirror = 2 * tile_line(col=8)  # the course is symmetric about column line 8
    for seconds in (0, 0.7, 2.25, 9.6, 61):
        offsets = set()
        for a, b in zip(left, right):
            (ax, ay), (bx, by) = a.position(seconds), b.position(seconds)
            assert (bx, by) == pytest.approx((mirror - ax, ay)), 'the right block does not mirror the left'
            offsets.add((round(ax - a.route[0][0], 6), round(ay - a.route[0][1], 6)))
        assert len(offsets) == 1, 'the side dots are not at the same point of their loops'


def test_level8_middle_dot_circles_the_wall_between_the_blocks_clockwise():
    """Up the left block's inner column, across the top corridor, down, and back along the bottom one."""
    middle = level8.OBSTACLES[6]
    assert route_tiles(middle.route) == pytest.approx((6.5, -0.5, 9.5, 6.5), abs=0.02)
    assert clockwise(middle.route)


def test_level9_starts_top_left_with_a_checkpoint_in_the_middle_and_the_goal_off_an_arm():
    start, checkpoint, goal = level9.SAFE_REGIONS
    assert region_tiles(start) == (0, -2, 2, 0)
    assert engine.region_rect(*start).contains(pygame.Rect(level9.PLAYER_SPAWN, engine.PLAYER_SIZE))
    assert level9.CHECKPOINT == checkpoint and region_tiles(checkpoint) == (8, 4, 10, 6)
    assert level9.GOAL == goal and region_tiles(goal) == (16, 2, 18, 4)
    assert len(level9.INNER_WALLS) == 1, 'one island for the left part to loop round'


def test_level9_coin_sits_at_the_dead_end_of_the_bottom_bar():
    assert level9.COINS == [(tile_line(col=17), tile_line(row=7))]


def test_centered_spawn_stands_the_player_in_the_middle_of_an_area():
    area = pygame.Rect(447, 324, 84, 83)
    player = pygame.Rect(engine.centered_spawn(area), engine.PLAYER_SIZE)
    assert area.contains(player)
    assert player.center == area.center


def test_level9_checkpoint_is_a_safe_place_to_come_back_to():
    """Centered on the checkpoint, the player is clear of the walls, and no dot ever reaches it."""
    checkpoint = engine.region_rect(*level9.CHECKPOINT)
    player = pygame.Rect(engine.centered_spawn(checkpoint), engine.PLAYER_SIZE)
    assert checkpoint.contains(player)
    assert player.collidelist(engine.level_walls(level9)) == -1
    for declaration in level9.OBSTACLES:
        dot = obstacles.MovingObstacle(declaration)
        for _ in range(200):
            dot.update(declaration.period / 200)
            assert not circle_touches_rect(dot.center, obstacles.RADIUS, checkpoint), declaration


def test_level9_dots_are_fifteen_still_eight_circling_and_two_on_ls():
    still = [dot for dot in level9.OBSTACLES if isinstance(dot, obstacles.Still)]
    moving = [dot for dot in level9.OBSTACLES if not isinstance(dot, obstacles.Still)]
    assert len(still) == 15 and len(moving) == 10
    assert {dot.speed for dot in moving} == {150}


def test_level9_circling_dots_go_clockwise_round_two_by_two_blocks_half_a_lap_apart():
    """Through the middles of a block's four tiles, three of the eight half a lap from the rest."""
    circling = [dot for dot in level9.OBSTACLES if isinstance(dot, obstacles.Obstacle)][:8]
    blocks = [(4, 0), (8, -2), (0, 6), (4, 6), (16, -2), (0, 0), (12, -2), (12, 4)]
    for dot, (col, row) in zip(circling, blocks):
        assert route_tiles(dot.route) == pytest.approx((col + 0.5, row + 0.5, col + 1.5, row + 1.5), abs=0.02)
        assert clockwise(dot.route)
        assert dot.route[0] == min(dot.route), 'the loop does not start from its top-left corner'
    assert len({dot.length for dot in circling}) == 1, 'the loops drift apart'
    starts = [dot.start for dot in circling]
    assert len(set(starts[:5])) == len(set(starts[5:])) == 1
    assert (starts[0] - starts[5]) % 1 == pytest.approx(0.5)


def test_level9_l_dots_run_out_along_a_short_leg_and_a_long_one_and_back():
    """Each goes out from the end of its short leg, round the corner, and straight back."""
    l_dots = [dot for dot in level9.OBSTACLES if isinstance(dot, obstacles.Obstacle)][8:]
    assert len(l_dots) == 2
    for dot in l_dots:
        start, corner, end, back = dot.route
        assert back == corner and dot.start == 0
        legs = (math.dist(start, corner), math.dist(corner, end))
        assert legs[0] / engine.TILE_SIZE == pytest.approx(0.75, abs=0.02)
        assert legs[1] / engine.TILE_SIZE == pytest.approx(2.25, abs=0.02)
    (middle_start, middle_corner, middle_end, _), (coin_start, coin_corner, coin_end, _) = (
        dot.route for dot in l_dots)
    # Above the checkpoint: right, then up. Beside the coin: up, then left.
    assert middle_corner[0] > middle_start[0] and middle_end[1] < middle_corner[1]
    assert coin_corner[1] < coin_start[1] and coin_end[0] < coin_corner[0]


def test_move_player_slides_along_a_wall_instead_of_sticking():
    '''Pushing diagonally into a wall should still move along the free axis.'''
    wall = pygame.Rect(200, 0, 6, 400)
    pos = pygame.Vector2(100, 100)
    player = pygame.Rect(100, 100, 29, 29)

    for _ in range(20):
        engine.move_player(pos, player, 10, 10, [wall])

    assert player.right == wall.left, 'the player did not stop flush against the wall'
    assert player.y == 300, 'the blocked axis also stopped the free one'
    assert pos.x == player.x, 'the float position drifted away from the rect'


def pressed(*keys):
    '''Stand in for pygame.key.get_pressed(): every other key reads as up.'''
    return defaultdict(bool, {key: True for key in keys})


def test_read_input_keeps_diagonals_the_same_speed():
    straight = engine.read_input(pressed(pygame.K_d))
    diagonal = engine.read_input(pressed(pygame.K_d, pygame.K_s))

    assert straight.length() == pytest.approx(engine.PLAYER_SPEED)
    assert diagonal.length() == pytest.approx(engine.PLAYER_SPEED)
    assert engine.read_input(pressed()).length_squared() == 0
