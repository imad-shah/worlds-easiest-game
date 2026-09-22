'''Tests for obstacle movement and contact, all pure geometry -- no window.'''

import math

import pygame
import pytest

from worlds_easiest_game import engine, levels, obstacles
from worlds_easiest_game.obstacles import (
    MovingObstacle,
    Obstacle,
    Orbit,
    circle_touches_rect,
    cross,
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


def test_orbit_turns_clockwise_on_screen():
    '''Angles grow clockwise as the player sees it: from pointing right, down, then left.'''
    dot = MovingObstacle(Orbit((100, 100), radius=50, speed=90))

    assert dot.center == pytest.approx((150, 100))
    assert advance(dot, 1) == pytest.approx((100, 150)), 'did not turn down, clockwise'
    assert advance(dot, 1) == pytest.approx((50, 100))
    assert advance(dot, 3) == pytest.approx((100, 150)), 'did not wrap past a full turn'


def test_orbit_starts_at_its_angle_and_a_negative_speed_turns_back():
    assert MovingObstacle(Orbit((0, 0), radius=10, speed=30, angle=270)).center == pytest.approx((0, -10))
    backwards = MovingObstacle(Orbit((0, 0), radius=10, speed=-45))
    assert advance(backwards, 2) == pytest.approx((0, -10)), 'did not turn anticlockwise'


def test_orbit_keeps_its_distance_and_period():
    orbit = Orbit((30, 40), radius=25, speed=-72, angle=10)
    assert orbit.period == 5
    dot = MovingObstacle(orbit)
    start = dot.center
    for _ in range(37):
        assert math.dist(advance(dot, 0.137), (30, 40)) == pytest.approx(25)
    assert advance(MovingObstacle(orbit), orbit.period) == pytest.approx(start)


def test_orbit_does_not_depend_on_the_frame_rate():
    declaration = Orbit((0, 0), radius=80, speed=60, angle=15)
    one_frame = advance(MovingObstacle(declaration), 3.3)
    many_frames = advance(MovingObstacle(declaration), 3.3, steps=397)

    assert many_frames == pytest.approx(one_frame)


@pytest.mark.parametrize('radius, speed', [(-1, 30), (10, 0)])
def test_orbit_needs_a_distance_and_a_speed(radius, speed):
    with pytest.raises(ValueError):
        Orbit((0, 0), radius, speed)


def test_cross_is_a_center_dot_and_evenly_spaced_straight_arms():
    dots = cross((200, 100), arms=4, dots_per_arm=3, spacing=20, speed=45, angle=10)

    assert len(dots) == 1 + 4 * 3
    assert {(dot.center, dot.speed) for dot in dots} == {((200, 100), 45)}, 'the cross does not turn as one'
    assert [dot.radius for dot in dots] == [0] + [20, 40, 60] * 4
    assert sorted({dot.angle for dot in dots[1:]}) == [10, 100, 190, 280]
    # An arm stays a straight line out from the center as the cross turns.
    moving = obstacles.spawn(dots)
    for dot in moving:
        dot.update(1.7)
    arm = [dot.center for dot in moving[:4]]
    headings = {round(math.degrees(math.atan2(y - 100, x - 200)), 6) for x, y in arm[1:]}
    assert arm[0] == pytest.approx((200, 100)), 'the center dot moved'
    assert headings == {round(10 + 45 * 1.7, 6)}


def test_cross_can_leave_out_its_center_dot_and_start_its_arms_further_out():
    dots = cross((0, 0), arms=4, dots_per_arm=4, spacing=30, speed=-50, inner=45, center_dot=False)

    assert len(dots) == 4 * 4
    assert [dot.radius for dot in dots] == [45, 75, 105, 135] * 4
    assert sorted({dot.angle for dot in dots}) == [0, 90, 180, 270]


def sample_centers(declaration, samples=360):
    '''Where a dot is at evenly spaced moments over one full period of its movement.'''
    dot = MovingObstacle(declaration)
    centers = []
    for _ in range(samples):
        dot.update(declaration.period / samples)
        centers.append(dot.center)
    return centers


@pytest.mark.parametrize('level', levels.LEVELS, ids=lambda level: level.__name__)
def test_dots_keep_to_the_course(level):
    '''Patrolling dots never overlap a wall; turning dots cross the floor on every turn.

    Patrols run along corridors, so they must clear the walls entirely. A spinning
    cross sweeps wherever its arms reach, and in the original its dots pass over
    walls, stepped corners and the empty space around a course, so each turning dot
    is only held to turning about a point on the canvas and passing over the
    walkable floor at some point in its turn.
    '''
    walls = engine.build_walls(level.PLAYFIELD)
    floor = [engine.region_rect(*corners) for corners in level.PATH_REGIONS + level.SAFE_REGIONS]
    canvas = pygame.Rect(0, 0, engine.SCREEN_WIDTH, engine.SCREEN_HEIGHT)
    for declaration in level.OBSTACLES:
        centers = sample_centers(declaration)
        if isinstance(declaration, Obstacle):
            for center in centers:
                assert not any(
                    circle_touches_rect(center, obstacles.RADIUS, wall) for wall in walls
                ), f'{declaration} runs into a wall at {center}'
        else:
            assert canvas.collidepoint(declaration.center), f'{declaration} turns about a point off the canvas'
            assert any(circle_touches_rect(center, obstacles.RADIUS, region)
                       for center in centers for region in floor), f'{declaration} never crosses the floor'
