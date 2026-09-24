'''Tests for the headless runner's moves and its report of how a run ended.

The runs here are on small synthetic levels built for each check, never on the
game's own levels: those are only ever played on planned routes, in
test_perfect_run.py. Nothing here opens a window or needs a display.
'''

from types import SimpleNamespace

import pygame
import pytest

from worlds_easiest_game import engine, headless
from worlds_easiest_game.headless import Ending, Move, Result
from worlds_easiest_game.obstacles import horizontal

SPAWN = (100, 100)


def box(**names):
    '''A bare 200px square course with the player spawning at SPAWN, a goal
    in the far corner, and no coins or dots, unless `names` says otherwise.'''
    level = dict(PLAYFIELD=[(0, 0), (200, 0), (200, 200), (0, 200)], PLAYER_SPAWN=SPAWN,
                 GOAL=((160, 160), (196, 196)), COINS=[], OBSTACLES=[])
    return SimpleNamespace(**(level | names))


def sign(n):
    return (n > 0) - (n < 0)


def test_there_are_nine_moves_standing_still_and_the_eight_directions():
    assert len(Move) == 9
    assert Move.STAY.velocity == (0, 0)
    directions = {(sign(move.velocity.x), sign(move.velocity.y)) for move in Move}
    assert directions == {(x, y) for x in (-1, 0, 1) for y in (-1, 0, 1)}


@pytest.mark.parametrize('move', list(Move), ids=lambda move: move.name)
def test_a_move_is_the_keyboard_holding_its_keys(move):
    pressed = [key for key in headless.MOVEMENT_KEYS if move.pressed[key]]
    assert frozenset(pressed) == move.value
    assert move.velocity == engine.read_input(move.pressed)


@pytest.mark.parametrize('move', [m for m in Move if m is not Move.STAY], ids=lambda move: move.name)
def test_every_direction_moves_at_player_speed(move):
    assert move.velocity.length() == pytest.approx(engine.PLAYER_SPEED)


def test_running_out_of_moves_reports_the_last_step():
    assert headless.play(box(), [Move.STAY] * 5) == Result(Ending.OUT_OF_MOVES, 5, SPAWN, 0, (), False)


def test_no_moves_ends_at_the_start():
    assert headless.play(box(), []) == Result(Ending.OUT_OF_MOVES, 0, SPAWN, 0, (), False)


def test_a_dot_touching_the_player_ends_the_run_where_it_happened():
    # A dot 1px a step along the player's middle row. The player's left edge is at
    # x=100, so the dot touches once its center is within RADIUS (11px) of it:
    # at 89.5, on step 69.
    dot = horizontal(y=115, from_x=20.5, to_x=180.5, speed=engine.FPS)

    assert headless.play(box(OBSTACLES=[dot]), [Move.STAY] * 200) == Result(Ending.DIED, 69, SPAWN, 0, (), False)


def test_a_death_reports_the_coins_collected_before_it():
    dot = horizontal(y=115, from_x=20.5, to_x=180.5, speed=engine.FPS)
    level = box(OBSTACLES=[dot], COINS=[(115, 115), (20, 20)])

    assert headless.play(level, [Move.STAY] * 200) == Result(Ending.DIED, 69, SPAWN, 1, ((20, 20),), False)


def test_beating_the_level_ends_the_run_on_that_step():
    level = box(GOAL=((90, 90), (140, 140)), COINS=[(115, 115)])

    assert headless.play(level, [Move.STAY] * 10) == Result(Ending.BEATEN, 1, SPAWN, 1, (), False)


def test_a_run_reports_whether_it_reached_the_checkpoint():
    # A checkpoint along the top wall, 20px above the spawn, and one at the far
    # left, out of reach of a player going straight up.
    top = box(CHECKPOINT=((80, 0), (140, 80)))
    far = box(CHECKPOINT=((0, 0), (40, 200)))

    assert headless.play(top, [Move.STAY] * 5).reached_checkpoint is False
    assert headless.play(top, [Move.UP] * 20).reached_checkpoint is True
    assert headless.play(far, [Move.UP] * 20).reached_checkpoint is False


def test_a_move_slides_along_a_wall_as_the_keyboard_does():
    # Down-right from 8px off the right wall's inner face (x=197): the wall stops
    # the player's right edge there while they keep going down.
    level = box(PLAYER_SPAWN=(160, 100))
    result = headless.play(level, [Move.DOWN_RIGHT] * 20)

    down = 20 * Move.DOWN_RIGHT.velocity.y * engine.STEP
    assert result.position == (197 - engine.PLAYER_SIZE[0], round(100 + down))


def test_the_runner_needs_no_display():
    pygame.quit()
    assert not pygame.display.get_init()

    assert headless.play(box(), [Move.RIGHT] * 3).position == (106, 100)


def test_playing_runs_together_ends_each_one_as_playing_it_alone_would():
    # The dot of the tests above, which touches a player standing at the spawn on
    # step 69. The goal is just left of the spawn.
    dot = horizontal(y=115, from_x=20.5, to_x=180.5, speed=engine.FPS)
    level = box(OBSTACLES=[dot], GOAL=((40, 20), (60, 60)))
    move_lists = [
        [Move.STAY] * 200,  # dies
        [Move.STAY] * 10,  # runs out of moves long before the others end
        [],  # has none at all
        [Move.UP] * 20 + [Move.LEFT] * 20,  # beats the level
        [Move.UP] * 300,  # outlasts the dot along the top wall, then runs out
        [Move.DOWN_RIGHT] * 200,  # slides along the walls into the corner
    ]

    together = headless.play_all(level, move_lists)

    assert together == [headless.play(level, moves) for moves in move_lists]
    assert {result.ending for result in together} == set(Ending)


def test_attempts_sharing_dots_see_them_where_they_would_be_alone():
    dot = horizontal(y=115, from_x=20.5, to_x=180.5, speed=engine.FPS)
    level = box(OBSTACLES=[dot])
    dots = engine.Dots(level)
    sharing = [engine.Attempt(level, dots=dots) for _ in range(3)]
    alone = engine.Attempt(level)
    for _ in range(40):
        for attempt in sharing + [alone]:
            attempt.step(Move.STAY.velocity)

    assert dots.steps == 40
    assert [dot.center for dot in dots.moving] == [dot.center for dot in alone.dots.moving]


def test_shared_dots_never_move_back():
    dots = engine.Dots(box(OBSTACLES=[horizontal(y=50, from_x=20, to_x=180, speed=60)]))
    dots.at(5)

    with pytest.raises(ValueError):
        dots.at(4)


def test_runs_step_together_and_say_how_each_ended_as_it_ends():
    dot = horizontal(y=115, from_x=20.5, to_x=180.5, speed=engine.FPS)
    level = box(OBSTACLES=[dot])
    runs = headless.Runs(level, [[Move.STAY] * 200, [Move.STAY] * 10, [], [Move.UP] * 300])

    assert runs.endings == [None, None, Ending.OUT_OF_MOVES, None]
    assert (runs.steps, len(runs.alive)) == (0, 4)
    for _ in range(10):
        runs.step()
    # The second run ends on its last move, not on the step after it.
    assert runs.endings == [None, Ending.OUT_OF_MOVES, Ending.OUT_OF_MOVES, None]
    for _ in range(59):
        runs.step()
    assert runs.steps == 69
    assert runs.endings[0] is Ending.DIED  # the dot reaches the spawn on step 69
    assert runs.alive == [runs.attempts[1], runs.attempts[2], runs.attempts[3]]
    assert not runs.over

    results = runs.finish()

    assert runs.over and runs.steps == 300
    assert results == headless.play_all(level, [[Move.STAY] * 200, [Move.STAY] * 10, [], [Move.UP] * 300])
    runs.step()
    assert runs.steps == 300, 'runs that are over took another step'
