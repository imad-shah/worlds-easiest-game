'''Tests for obstacle movement and contact, all pure geometry -- no window.'''

import pygame
import pytest

from worlds_easiest_game import engine, levels, obstacles
from worlds_easiest_game.obstacles import (
    MovingObstacle,
    circle_touches_rect,
    horizontal,
    loop,
    vertical,
)


def advance(dot, seconds, steps=1):
    for _ in range(steps):
        dot.update(seconds / steps)
    return dot.center


def test_horizontal_reverses_at_both_ends():
    dot = MovingObstacle(horizontal(y=50, from_x=100, to_x=200, speed=100))

    assert dot.center == (100, 50)
    assert advance(dot, 0.5) == pytest.approx((150, 50))
    assert advance(dot, 0.7) == pytest.approx((180, 50)), 'did not turn back at to_x'
    assert advance(dot, 1.0) == pytest.approx((120, 50)), 'did not turn back at from_x'
    assert advance(dot, 0.2) == pytest.approx((140, 50)), 'did not head out again'


def test_vertical_moves_along_its_column():
    dot = MovingObstacle(vertical(x=30, from_y=300, to_y=100, speed=50))

    assert advance(dot, 1) == pytest.approx((30, 250)), 'did not head toward to_y first'
    assert advance(dot, 4) == pytest.approx((30, 150)), 'did not turn back at to_y'


def test_loop_turns_its_corners_and_wraps_around():
    square = [(0, 0), (100, 0), (100, 100), (0, 100)]
    dot = MovingObstacle(loop(square, speed=100))

    assert advance(dot, 0.5) == pytest.approx((50, 0))
    assert advance(dot, 1.0) == pytest.approx((100, 50)), 'did not turn the first corner'
    assert advance(dot, 1.0) == pytest.approx((50, 100))
    assert advance(dot, 1.0) == pytest.approx((0, 50)), 'did not head back to the start'
    assert advance(dot, 1.0) == pytest.approx((50, 0)), 'did not wrap past the start'


def test_movement_does_not_depend_on_the_frame_rate():
    declaration = loop([(0, 0), (80, 0), (80, 60), (0, 60)], speed=90)
    one_frame = advance(MovingObstacle(declaration), 3.3)
    many_frames = advance(MovingObstacle(declaration), 3.3, steps=397)

    assert many_frames == pytest.approx(one_frame)


def test_start_places_the_dot_part_way_along_its_route():
    ahead = MovingObstacle(horizontal(y=0, from_x=0, to_x=100, speed=100, start=0.5))
    assert ahead.center == (100, 0)
    assert advance(ahead, 0.25) == pytest.approx((75, 0)), 'start=0.5 should head back'

    ring = [(0, 0), (100, 0), (100, 100), (0, 100)]
    assert MovingObstacle(loop(ring, speed=1, start=0.25)).center == (100, 0)
    assert MovingObstacle(loop(ring, speed=1, start=0.625)).center == (50, 100)


def test_spawn_starts_fresh_moving_state_from_the_same_declarations():
    declarations = [horizontal(y=0, from_x=0, to_x=100, speed=100)]
    first = obstacles.spawn(declarations)
    advance(first[0], 0.3)

    again = obstacles.spawn(declarations)
    assert again[0].center == (0, 0), 'the declaration picked up the moved state'


@pytest.mark.parametrize('route', [
    [(0, 0), (10, 10)],  # diagonal
    [(0, 0)],  # nowhere to go
    [(0, 0), (0, 0)],  # zero-length leg
])
def test_routes_must_be_axis_aligned(route):
    with pytest.raises(ValueError):
        loop(route, speed=1)


def test_start_must_be_a_fraction_of_the_route():
    with pytest.raises(ValueError):
        horizontal(y=0, from_x=0, to_x=10, speed=1, start=1)


def test_contact_on_each_side_of_the_rect():
    rect = pygame.Rect(100, 100, 30, 30)  # covers x and y from 100 to 130
    r = obstacles.RADIUS

    assert circle_touches_rect((115, 115), r, rect), 'center inside the rect'
    assert circle_touches_rect((100 - r + 1, 115), r, rect), 'overlapping the left edge'
    assert circle_touches_rect((130 + r - 1, 115), r, rect), 'overlapping the right edge'
    assert not circle_touches_rect((100 - r - 1, 115), r, rect)
    assert not circle_touches_rect((115, 130 + r + 1), r, rect)


def test_a_dot_off_the_corner_is_a_near_miss():
    '''Inside the rect's bounding square around the circle, but past the curve.'''
    rect = pygame.Rect(100, 100, 30, 30)
    r = obstacles.RADIUS
    # Offset diagonally so each axis is within r of the corner, but the
    # distance to the corner is about 1.3 r.
    offset = 0.9 * r
    near_miss = (100 - offset, 100 - offset)
    assert not circle_touches_rect(near_miss, r, rect)
    assert pygame.Rect(near_miss[0] - r, near_miss[1] - r, 2 * r, 2 * r).colliderect(rect), (
        'not a near miss: even the bounding boxes do not overlap'
    )
    assert circle_touches_rect((100 - 0.6 * r, 100 - 0.6 * r), r, rect)


def test_moving_obstacle_touches_the_player_rect():
    dot = MovingObstacle(horizontal(y=115, from_x=0, to_x=200, speed=100))
    player = pygame.Rect(100, 100, 29, 29)

    assert not dot.touches(player)
    advance(dot, 0.95)
    assert dot.touches(player)


@pytest.mark.parametrize('level', levels.LEVELS, ids=lambda level: level.__name__)
def test_dots_stay_inside_the_walls(level):
    '''Sampled along each route, no dot ever overlaps a wall of the course.'''
    walls = engine.build_walls(level.PLAYFIELD)
    for declaration in level.OBSTACLES:
        dot = MovingObstacle(declaration)
        for _ in range(200):
            dot.update(declaration.length / declaration.speed / 200)
            assert not any(
                circle_touches_rect(dot.center, obstacles.RADIUS, wall) for wall in walls
            ), f'{declaration} runs into a wall at {dot.center}'
