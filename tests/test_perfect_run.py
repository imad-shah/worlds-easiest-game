'''A perfect run of the whole game: Start, every level cleared without a death, the win screen.

Each level's route is planned from the level's own data before it is played. The
dots are deterministic, so a beam search over time, stepping the dots and moving
the player with the engine's own helpers at the game's own frame rate, finds a
route that never touches one. The route is then replayed through the real Game,
one frame at a time, from a left click on START. Nothing is scripted by hand: a
level the planner cannot clear is a level the test cannot pass.

The dummy video driver gives the screens and level surfaces a display to convert
to without opening a window.
'''

import math
import os
from collections import defaultdict, deque

import pygame
import pytest

from worlds_easiest_game import engine, levels, obstacles

DT = 1 / engine.FPS
FRAMES_PER_STEP = 3  # the planner picks a direction, then holds it this many frames
CLEARANCE = 4  # px kept between the player and every dot, on top of touching distance
BEAM = 100  # partial routes kept after each step
MAX_STEPS = 1200  # 30 seconds of play per level
CELL = 4  # px; the grid the distance fields and the beam's duplicate check use

# Every way to hold the movement keys, standing still included.
MOVES = [frozenset(key for key in (vertical, horizontal) if key)
         for vertical in (None, pygame.K_w, pygame.K_s)
         for horizontal in (None, pygame.K_a, pygame.K_d)]


def held(keys):
    '''What pygame.key.get_pressed() reports while exactly `keys` are held.'''
    return defaultdict(bool, dict.fromkeys(keys, True))


def dot_frames(level, frames):
    '''Where every dot is at the end of each frame, stepped exactly as Play steps them.'''
    dots = obstacles.spawn(level.OBSTACLES)
    centers = []
    for _ in range(frames):
        for dot in dots:
            dot.update(DT)
        centers.append([dot.center for dot in dots])
    return centers


def distance_field(level, walls, reached):
    '''Walking distance from every CELL-grid player position to one that `reached` accepts.'''
    xs = [x for x, _ in level.PLAYFIELD]
    ys = [y for _, y in level.PLAYFIELD]
    free = {}
    for x in range(min(xs), max(xs), CELL):
        for y in range(min(ys), max(ys), CELL):
            player = pygame.Rect((x, y), engine.PLAYER_SIZE)
            if player.collidelist(walls) == -1:
                free[x, y] = player
    distance = {cell: 0 for cell, player in free.items() if reached(player)}
    queue = deque(distance)
    while queue:
        x, y = cell = queue.popleft()
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                step = (x + dx * CELL, y + dy * CELL)
                if step in free and step not in distance:
                    distance[step] = distance[cell] + CELL * math.hypot(dx, dy)
                    queue.append(step)
    origin = (min(xs), min(ys))
    return lambda pos: distance.get(snap(pos, origin), math.inf)


def snap(pos, origin):
    return tuple(o + round((p - o) / CELL) * CELL for p, o in zip(pos, origin))


def plan(level):
    '''The keys to hold on each frame to clear `level` without touching a dot, or None.

    A route collects the coins in the order the level declares them, then heads for
    the goal. Coins and the goal count as reached by the same tests Play uses.
    '''
    walls = engine.build_walls(level.PLAYFIELD)
    goal = engine.region_rect(*level.GOAL)
    coins = list(level.COINS)
    to_coin = [distance_field(level, walls, lambda player, coin=coin:
                              obstacles.circle_touches_rect(coin, engine.COIN_RADIUS, player))
               for coin in coins]
    to_goal = distance_field(level, walls, goal.colliderect)
    dots = dot_frames(level, MAX_STEPS * FRAMES_PER_STEP)

    def remaining(route):
        '''How far a route has left to go: fewer coins out first, then distance.'''
        pos, _, left = route[:3]
        if left:
            return len(left), to_coin[coins.index(left[0])](pos)
        return 0, to_goal(pos)

    # A route: position, player rect, coins left, and the moves that led there.
    routes = [(pygame.Vector2(level.PLAYER_SPAWN), pygame.Rect(level.PLAYER_SPAWN, engine.PLAYER_SIZE),
               tuple(coins), ())]
    for step in range(MAX_STEPS):
        seen = {}
        for pos, player, left, moves in routes:
            for move in MOVES:
                velocity = engine.read_input(held(move))
                new_pos, new_player, new_left = pygame.Vector2(pos), player.copy(), left
                for frame in range(step * FRAMES_PER_STEP, (step + 1) * FRAMES_PER_STEP):
                    engine.move_player(new_pos, new_player, velocity.x * DT, velocity.y * DT, walls)
                    if any(obstacles.circle_touches_rect(dot, obstacles.RADIUS + CLEARANCE, new_player)
                           for dot in dots[frame]):
                        break
                    new_left = tuple(coin for coin in new_left
                                     if not obstacles.circle_touches_rect(coin, engine.COIN_RADIUS, new_player))
                    if not new_left and new_player.colliderect(goal):
                        finishing = frame - step * FRAMES_PER_STEP + 1
                        return [held(m) for m in moves for _ in range(FRAMES_PER_STEP)] + [held(move)] * finishing
                else:
                    key = (snap(new_pos, (0, 0)), new_left)
                    if key not in seen:
                        seen[key] = (new_pos, new_player, new_left, (*moves, move))
        routes = sorted(seen.values(), key=remaining)[:BEAM]
        if not routes:
            return None
    return None


@pytest.fixture(scope='module')
def display():
    os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
    pygame.init()
    pygame.display.set_mode((engine.SCREEN_WIDTH, engine.SCREEN_HEIGHT))
    yield
    pygame.quit()


def test_a_planned_route_clears_every_level_without_a_death(display):
    routes = [plan(level) for level in levels.LEVELS]
    for level, route in zip(levels.LEVELS, routes):
        assert route is not None, f'no dot-free route through {level.__name__}'

    game = engine.Game(levels.LEVELS)
    start = game.menu.buttons['START'].center
    game.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=start, button=1))

    for level, route in zip(levels.LEVELS, routes):
        play = game.play
        assert play.level is level
        dots = play.dots  # a touch resets the level, which spawns fresh dots
        for frame, keys in enumerate(route):
            assert game.state is play, f'{level.__name__} ended {len(route) - frame} frames early'
            game.update(DT, keys)
            assert play.dots is dots, f'a dot touched the player in {level.__name__}, frame {frame}'
        assert play.finished, f'the route ran out before finishing {level.__name__}'
        assert play.coins == [], f'{level.__name__} finished with coins still out'

    assert game.state is game.won
    assert game.deaths == 0
    assert engine.death_text(game.deaths) == 'DEATHS: 0'
