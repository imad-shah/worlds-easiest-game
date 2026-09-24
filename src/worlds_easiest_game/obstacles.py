'''Obstacles: the blue dots that patrol a level or stand guard in it.

A level declares its obstacles as data, one line each:

    OBSTACLES = [
        horizontal(y=220, from_x=295, to_x=681, speed=300),
        vertical(x=400, from_y=210, to_y=350, speed=200, start=0.5),
        loop([(300, 200), (500, 200), (500, 350), (300, 350)], speed=250),
    ]

Those three share one movement model, the patrol: a dot moving at constant
speed around a closed route of axis-aligned waypoints. `horizontal` and `vertical`
are the two-waypoint route, which runs out to the far end and straight back;
`loop` walks every waypoint in order, turning its corners, and closes back to
the first. `start` is where on the route the dot begins, as a fraction of the
route's length, so dots sharing a route can be staggered along it.

The second movement model is rotation: a dot circling a center point at a
fixed distance, turning at a constant angular speed. `cross` declares a whole
spinning cross of them, with or without a dot on its center, in one call:

    OBSTACLES = cross((488, 324), arms=4, dots_per_arm=5, spacing=29, speed=60)

Angles are in degrees on screen: 0 points right, and they grow clockwise, so a
positive speed turns clockwise as the player sees it.

A dot can also stand still, declared by where it stands:

    OBSTACLES = [still(300, 200)]

Every kind answers the same two questions, `period` (seconds until the dot is
back where it started) and `position(seconds)`, so the moving dots and
everything downstream of them treat every obstacle alike.

A declaration is immutable. `spawn` turns a level's declarations into fresh
moving dots each time the level starts.
'''

import math
from dataclasses import dataclass

RADIUS = 11  # to the outside of the black outline; sized from the original game


@dataclass(frozen=True)
class Obstacle:
    '''One patrolling obstacle as a level declares it. Build it with the helpers below.'''

    route: tuple  # waypoints; the last one leads back to the first
    speed: float  # pixels per second
    start: float = 0.0  # fraction of the route's length, in [0, 1)

    def __post_init__(self):
        if len(self.route) < 2:
            raise ValueError('an obstacle route needs at least two waypoints')
        for a, b in self.segments():
            if (a[0] == b[0]) == (a[1] == b[1]):
                raise ValueError(f'route leg {a}->{b} is not horizontal or vertical')
        if not 0 <= self.start < 1:
            raise ValueError(f'start {self.start} is not a fraction of the route')

    def segments(self):
        '''Each leg of the route as a (from, to) pair, including the closing leg.'''
        return list(zip(self.route, self.route[1:] + self.route[:1]))

    @property
    def length(self):
        return sum(math.dist(a, b) for a, b in self.segments())

    def point_at(self, distance):
        '''Where the dot is after travelling `distance` from the first waypoint.'''
        distance %= self.length
        for a, b in self.segments():
            leg = math.dist(a, b)
            if distance < leg:
                t = distance / leg
                return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
            distance -= leg
        return self.route[0]  # only reachable through float rounding on the last leg

    @property
    def period(self):
        '''Seconds to go once around the route.'''
        return self.length / self.speed

    def position(self, seconds):
        '''Where the dot is `seconds` after it set off from its start point.'''
        return self.point_at(self.start * self.length + self.speed * seconds)


@dataclass(frozen=True)
class Orbit:
    '''A dot circling `center` at a fixed distance. Build a cross of them with `cross`.'''

    center: tuple
    radius: float  # pixels from the center; 0 is a dot sitting on the center
    speed: float  # degrees per second; positive turns clockwise on screen
    angle: float = 0.0  # degrees clockwise from pointing right, where the dot starts

    def __post_init__(self):
        if self.radius < 0:
            raise ValueError(f'radius {self.radius} is negative')
        if not self.speed:
            raise ValueError('an orbiting dot needs a speed to turn at')

    @property
    def period(self):
        '''Seconds to go once around the circle.'''
        return 360 / abs(self.speed)

    def position(self, seconds):
        '''Where the dot is `seconds` after it set off from its start angle.'''
        turned = math.radians(self.angle + self.speed * seconds)
        return (self.center[0] + self.radius * math.cos(turned),
                self.center[1] + self.radius * math.sin(turned))


@dataclass(frozen=True)
class Still:
    '''A dot that never moves from `point`. Build it with `still`.'''

    point: tuple

    period = 1.0  # seconds; any time at all brings a dot that never moves back where it started

    def position(self, seconds):
        return self.point


def still(x, y):
    '''A dot standing at (`x`, `y`) for good.'''
    return Still((x, y))


def horizontal(y, from_x, to_x, speed, start=0.0):
    '''A dot sliding side to side along row `y`, starting out from `from_x`.'''
    return Obstacle(((from_x, y), (to_x, y)), speed, start)


def vertical(x, from_y, to_y, speed, start=0.0):
    '''A dot sliding up and down along column `x`, starting out from `from_y`.'''
    return Obstacle(((x, from_y), (x, to_y)), speed, start)


def loop(waypoints, speed, start=0.0):
    '''A dot circling through `waypoints` in order, then back to the first.'''
    return Obstacle(tuple(map(tuple, waypoints)), speed, start)


def cross(center, arms, dots_per_arm, spacing, speed, angle=0.0, inner=None, center_dot=True):
    '''A cross of dots spinning about `center`.

    Its `arms` are spread evenly around the center, the first pointing at `angle`,
    and each is a straight line of `dots_per_arm` dots `spacing` pixels apart. An
    arm's innermost dot is `inner` pixels out from the center, one spacing unless
    given. With `center_dot`, one more dot sits on the center itself. The whole
    cross turns as one at `speed`.
    '''
    center = tuple(center)
    inner = spacing if inner is None else inner
    hub = [Orbit(center, 0, speed, angle)] if center_dot else []
    return hub + [
        Orbit(center, inner + spacing * dot, speed, angle + 360 * arm / arms)
        for arm in range(arms)
        for dot in range(dots_per_arm)
    ]


class MovingObstacle:
    '''The live state of one declared obstacle: how long it has been moving, and
    where that puts it.

    `center` is worked out once per `update`, not each time it is read, since
    every player the dot is checked against reads it.
    '''

    def __init__(self, obstacle):
        self.obstacle = obstacle
        self.elapsed = 0.0  # seconds, wrapped to the obstacle's period
        self.center = obstacle.position(self.elapsed)

    def update(self, dt):
        self.elapsed = (self.elapsed + dt) % self.obstacle.period
        self.center = self.obstacle.position(self.elapsed)

    def touches(self, rect):
        '''Whether this dot overlaps `rect` (anything with left/top/right/bottom).'''
        return circle_touches_rect(self.center, RADIUS, rect)


def spawn(declarations):
    '''Fresh moving dots for a level's OBSTACLES, each at its start point.'''
    return [MovingObstacle(obstacle) for obstacle in declarations]


def circle_touches_rect(center, radius, rect):
    '''Closest-point test: the point of `rect` nearest the center lies inside the circle.

    The rect is taken as the area it covers on screen, `left` up to `right`.
    '''
    cx, cy = center
    nearest_x = min(max(cx, rect.left), rect.right)
    nearest_y = min(max(cy, rect.top), rect.bottom)
    return (cx - nearest_x) ** 2 + (cy - nearest_y) ** 2 < radius ** 2
