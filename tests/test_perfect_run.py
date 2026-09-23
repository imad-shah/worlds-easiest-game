'''Perfect runs: every level cleared without a death, by the game and by the headless runner.

Each level's route is planned from the level's own data before it is played. The
dots are deterministic, so a beam search over time, stepping the dots and moving
the player with the engine's own helpers one fixed step at a time, finds a route
of moves that never touches one. The routes are then replayed through the real
Game, one step at a time, from a left click on START to the win screen, and
through `headless.play`, which must beat each level the same way every time.
Nothing is scripted by hand: a level the planner cannot clear is a level the
tests cannot pass.

The dummy video driver gives the screens and level surfaces a display to convert
to without opening a window.
'''

import math
import os
from collections import deque

import pygame
import pytest

from worlds_easiest_game import engine, headless, levels, obstacles
from worlds_easiest_game.headless import Ending, Move

STEPS_PER_CHOICE = 3  # the planner picks a move, then holds it this many steps
CLEARANCE = 4  # px kept between the player and every dot, on top of touching distance
BEAM = 100  # partial routes kept after each choice
MAX_CHOICES = 1200  # 30 seconds of play per level
CELL = 4  # px; the grid the distance fields and the beam's duplicate check use


def dot_steps(level, steps):
    '''Where every dot is at the end of each step, stepped exactly as an Attempt steps them.'''
    dots = obstacles.spawn(level.OBSTACLES)
    centers = []
    for _ in range(steps):
        for dot in dots:
            dot.update(engine.STEP)
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
    '''The move for each step that clears `level` without touching a dot, or None.

    A route collects the coins in the order the level declares them, then heads for
    the goal. Coins and the goal count as reached by the same tests an Attempt uses.
    '''
    walls = engine.level_walls(level)
    goal = engine.region_rect(*level.GOAL)
    coins = list(level.COINS)
    to_coin = [distance_field(level, walls, lambda player, coin=coin:
                              obstacles.circle_touches_rect(coin, engine.COIN_RADIUS, player))
               for coin in coins]
    to_goal = distance_field(level, walls, goal.colliderect)
    dots = dot_steps(level, MAX_CHOICES * STEPS_PER_CHOICE)

    def remaining(route):
        '''How far a route has left to go: fewer coins out first, then distance.'''
        pos, _, left = route[:3]
        if left:
            return len(left), to_coin[coins.index(left[0])](pos)
        return 0, to_goal(pos)

    # A route: position, player rect, coins left, and the moves that led there.
    routes = [(pygame.Vector2(level.PLAYER_SPAWN), pygame.Rect(level.PLAYER_SPAWN, engine.PLAYER_SIZE),
               tuple(coins), ())]
    for choice in range(MAX_CHOICES):
        seen = {}
        for pos, player, left, moves in routes:
            for move in Move:
                velocity = move.velocity
                new_pos, new_player, new_left = pygame.Vector2(pos), player.copy(), left
                for step in range(choice * STEPS_PER_CHOICE, (choice + 1) * STEPS_PER_CHOICE):
                    engine.move_player(new_pos, new_player, velocity.x * engine.STEP,
                                       velocity.y * engine.STEP, walls)
                    if any(obstacles.circle_touches_rect(dot, obstacles.RADIUS + CLEARANCE, new_player)
                           for dot in dots[step]):
                        break
                    new_left = tuple(coin for coin in new_left
                                     if not obstacles.circle_touches_rect(coin, engine.COIN_RADIUS, new_player))
                    if not new_left and new_player.colliderect(goal):
                        finishing = step - choice * STEPS_PER_CHOICE + 1
                        return [m for m in moves for _ in range(STEPS_PER_CHOICE)] + [move] * finishing
                else:
                    key = (snap(new_pos, (0, 0)), new_left)
                    if key not in seen:
                        seen[key] = (new_pos, new_player, new_left, (*moves, move))
        routes = sorted(seen.values(), key=remaining)[:BEAM]
        if not routes:
            return None
    return None


@pytest.fixture(scope='module')
def routes():
    '''Every level's planned route, in play order.'''
    planned = [plan(level) for level in levels.LEVELS]
    for level, route in zip(levels.LEVELS, planned):
        assert route is not None, f'no dot-free route through {level.__name__}'
    return planned


@pytest.fixture(scope='module')
def display():
    os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
    pygame.init()
    pygame.display.set_mode((engine.SCREEN_WIDTH, engine.SCREEN_HEIGHT))
    yield
    pygame.quit()


def test_a_planned_route_clears_every_level_without_a_death(routes, display):
    game = engine.Game(levels.LEVELS)
    start = game.menu.buttons['START'].center
    game.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=start, button=1))

    for level, route in zip(levels.LEVELS, routes):
        play = game.play
        assert play.level is level
        attempt = play.attempt  # a touch starts the level over with a fresh attempt
        for step, move in enumerate(route):
            assert game.state is play, f'{level.__name__} ended {len(route) - step} steps early'
            game.update(move.pressed)
            assert play.attempt is attempt, f'a dot touched the player in {level.__name__}, step {step}'
        assert play.finished, f'the route ran out before finishing {level.__name__}'
        assert attempt.coins == [], f'{level.__name__} finished with coins still out'
        if hasattr(level, 'CHECKPOINT'):
            assert attempt.respawn == engine.centered_spawn(engine.region_rect(*level.CHECKPOINT)), (
                f'the route through {level.__name__} never reached its checkpoint'
            )

    assert game.state is game.won
    assert game.deaths == 0
    assert engine.death_text(game.deaths) == 'DEATHS: 0'


@pytest.mark.parametrize('index', range(len(levels.LEVELS)),
                         ids=[level.__name__ for level in levels.LEVELS])
def test_the_runner_beats_every_level_on_its_planned_route_the_same_way_every_time(routes, index):
    level, route = levels.LEVELS[index], routes[index]
    result = headless.play(level, route)

    assert result.ending is Ending.BEATEN
    assert result.beaten
    assert result.step == len(route)
    assert result.coins == len(level.COINS)
    assert all(headless.play(level, route) == result for _ in range(3))


@pytest.mark.parametrize('index', range(len(levels.LEVELS)),
                         ids=[level.__name__ for level in levels.LEVELS])
def test_the_runner_ends_where_the_game_ends(routes, display, index):
    '''The window steps the same Attempt, so a route leaves the player where the runner says.'''
    level, route = levels.LEVELS[index], routes[index]
    play = engine.Play(level)
    for move in route:
        play.update(move.pressed)
    attempt = play.attempt

    assert play.finished and play.deaths == 0
    assert headless.play(level, route) == headless.Result(
        Ending.BEATEN, attempt.steps, attempt.player.topleft, attempt.coins_collected)
