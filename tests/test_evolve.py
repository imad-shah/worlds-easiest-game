'''Tests for the learner: its distance map, scoring, selection, mutation, and training.

The distance map is checked on level 1 as a static fact, with no play. Training
only ever runs on small levels built here for it, never on the game's own
levels, which are only played on planned routes (test_perfect_run.py). Nothing
here opens a window or needs a display.
'''

import math
import random
from types import SimpleNamespace

import pygame
import pytest

from worlds_easiest_game import engine, evolve, headless
from worlds_easiest_game.headless import Ending, Move, Result
from worlds_easiest_game.levels import level1
from worlds_easiest_game.obstacles import vertical

SETTINGS = evolve.Settings(population=30)
LIMIT = 1000  # steps, for scoring


def box(**names):
    '''A bare 200px square course with the goal in its bottom-right corner.'''
    level = dict(PLAYFIELD=[(0, 0), (200, 0), (200, 200), (0, 200)], PLAYER_SPAWN=(100, 100),
                 GOAL=((160, 160), (196, 196)), COINS=[], OBSTACLES=[], TIME_LIMIT=2)
    return SimpleNamespace(**(level | names))


def gate():
    '''A corridor with a dot sweeping up and down across its middle, which a
    character has to time its way past to reach the goal at the far end.'''
    return SimpleNamespace(
        PLAYFIELD=[(0, 0), (240, 0), (240, 60), (0, 60)], PLAYER_SPAWN=(8, 15),
        GOAL=((200, 0), (240, 60)), COINS=[],
        OBSTACLES=[vertical(x=120, from_y=10, to_y=50, speed=60)], TIME_LIMIT=3)


@pytest.fixture(scope='module')
def level1_distances():
    return evolve.distance_map(level1)


def test_the_distance_is_zero_wherever_the_player_touches_the_goal(level1_distances):
    goal = engine.region_rect(*level1.GOAL)
    for place, distance in level1_distances.items():
        touching = goal.colliderect(pygame.Rect(place, engine.PLAYER_SIZE))
        assert (distance == 0) == touching, place


def test_the_distance_shrinks_along_level1s_corridors(level1_distances):
    # The player's top-left corner at points along the way through level 1: down
    # the left room, along the passage under the corridor, up into it, across it
    # to its top-right corner, and along the passage into the right room.
    route = [level1.PLAYER_SPAWN, (166, 372), (288, 372), (288, 300), (450, 250), (600, 205),
             (660, 166), (700, 166), (707, 166)]
    distances = [level1_distances[place] for place in route]

    assert distances == sorted(distances, reverse=True)
    assert len(set(distances)) == len(distances), 'the distance stood still along the way'
    assert distances[-1] == 0


def test_the_distance_walks_around_walls_not_through_them(level1_distances):
    # Either side of the wall between the left room and the corridor, 79px apart:
    # the walk between them goes down to the passage under the corridor and back up.
    room, corridor = (208, 205), (287, 205)

    assert level1_distances[room] - level1_distances[corridor] > 4 * math.dist(room, corridor)


def test_the_distance_leaves_out_places_the_player_does_not_fit(level1_distances):
    # The left room's right wall runs from x=237: at x=208 the player's right edge
    # is flush with it; a pixel further and they would overlap it.
    assert (208, 205) in level1_distances
    assert (209, 205) not in level1_distances


def test_the_distance_counts_whole_pixels_straight_and_diagonally():
    distances = evolve.distance_map(box())

    # The player touches the goal from x=132 and y=132 on, being 29px across.
    assert distances[132, 132] == 0
    assert distances[100, 132] == 32
    assert distances[100, 100] == pytest.approx(32 * math.sqrt(2))


def run(ending, step=100, position=(0, 0)):
    return Result(ending, step, position, 0)


def test_beating_the_level_scores_above_anything_else():
    last_step_win = evolve.score(run(Ending.BEATEN, step=LIMIT), 0, LIMIT, SETTINGS)
    near_miss = evolve.score(run(Ending.OUT_OF_MOVES), 1, LIMIT, SETTINGS)

    assert last_step_win > near_miss


def test_beating_the_level_in_fewer_steps_scores_higher():
    scores = [evolve.score(run(Ending.BEATEN, step=step), 0, LIMIT, SETTINGS)
              for step in (100, 101, 500, LIMIT)]

    assert scores == sorted(scores, reverse=True)
    assert len(set(scores)) == len(scores)


def test_ending_closer_to_the_goal_scores_higher():
    scores = [evolve.score(run(Ending.OUT_OF_MOVES), distance, LIMIT, SETTINGS)
              for distance in (1, 2, 50, 700)]

    assert scores == sorted(scores, reverse=True)
    assert len(set(scores)) == len(scores)
    assert min(scores) > 0


@pytest.mark.parametrize('tiles', [0.1, 5, 10, 20])
def test_dying_scores_slightly_below_running_out_of_time_at_the_same_place(tiles):
    distance = tiles * engine.TILE_SIZE
    died = evolve.score(run(Ending.DIED), distance, LIMIT, SETTINGS)
    timed_out = evolve.score(run(Ending.OUT_OF_MOVES), distance, LIMIT, SETTINGS)
    a_tile_back = evolve.score(run(Ending.OUT_OF_MOVES), distance + engine.TILE_SIZE, LIMIT, SETTINGS)

    assert died == pytest.approx(timed_out * (1 - SETTINGS.death_penalty))
    assert died < timed_out
    assert died > a_tile_back, 'hanging back a tile scores better than dying'


def test_a_steep_progress_weight_still_scores_every_run_above_0():
    settings = evolve.Settings(population=30, progress_weight=math.inf)
    generations = evolve.generations(gate(), settings, seed=3)
    first, second = next(generations), next(generations)

    assert not first.beaten
    assert min(first.scores + second.scores) > 0


def test_the_best_character_carries_over_unchanged():
    rng = random.Random(1)
    characters = [rng.choices(evolve.MOVES, k=20) for _ in range(10)]
    scores = [rng.random() for _ in characters]
    best = characters[scores.index(max(scores))]
    children = evolve.next_generation(characters, scores, 25, 1, rng)  # every copied move changes

    assert len(children) == 10
    assert children[0] == best
    assert all(len(child) == 25 for child in children[1:])


def test_parents_are_picked_in_proportion_to_their_scores():
    strong, weak = [Move.LEFT] * 5, [Move.RIGHT] * 5
    characters, scores = [strong, weak] * 2000, [3, 1] * 2000

    children = evolve.next_generation(characters, scores, 5, 0, random.Random(1))[1:]

    assert children.count(strong) / len(children) == pytest.approx(0.75, abs=0.02)


@pytest.mark.parametrize('rate', [0, 0.015, 0.1])
def test_a_child_changes_its_parents_moves_at_the_mutation_rate(rate):
    rng = random.Random(1)
    parent = rng.choices(evolve.MOVES, k=100_000)

    child = evolve.child(parent, len(parent), rate, rng)

    changed = sum(ours != theirs for ours, theirs in zip(child, parent))
    assert changed / len(parent) == pytest.approx(rate, abs=0.002)


def test_a_child_adds_random_moves_after_its_parents():
    parent = [Move.STAY] * 10
    child = evolve.child(parent, 1010, 0, random.Random(1))

    assert child[:10] == parent
    assert set(child[10:]) == set(Move)


def test_lists_start_short_and_grow_each_generation_up_to_the_time_limit():
    settings = evolve.Settings(population=2, first_moves=4, growth=3, hold=12, time_limit=1)

    lengths = [settings.moves_allowed(box(), generation) for generation in range(1, 6)]

    assert lengths == [4, 7, 10, 10, 10]  # 10 moves of 12 steps cover the 120 steps of a second


def test_the_time_limit_is_the_levels_own_unless_given():
    assert evolve.Settings(population=2).time_limit_steps(box()) == 2 * engine.FPS
    assert evolve.Settings(population=2, time_limit=0.5).time_limit_steps(box()) == engine.FPS // 2


def test_level1_gives_the_learner_a_time_limit():
    assert level1.TIME_LIMIT > 0


def test_each_move_is_held_and_the_run_cut_off_at_the_time_limit():
    moves = [Move.UP, Move.LEFT, Move.DOWN]

    assert list(evolve.steps(moves, 3, 7)) == [Move.UP] * 3 + [Move.LEFT] * 3 + [Move.DOWN]


@pytest.mark.parametrize('bad', [
    dict(population=1), dict(mutation=1.5), dict(hold=0), dict(first_moves=0), dict(growth=-1),
    dict(time_limit=0), dict(time_limit=math.inf), dict(progress_weight=0), dict(death_penalty=1),
    dict(speed_weight=-1),
])
def test_settings_out_of_range_are_refused(bad):
    with pytest.raises(ValueError):
        evolve.Settings(**(dict(population=10) | bad))


def first_generations(level, seed, count):
    generations = evolve.generations(level, SETTINGS, seed)
    return [next(generations) for _ in range(count)]


def test_the_same_seed_trains_the_same_way():
    once, again = first_generations(gate(), 7, 8), first_generations(gate(), 7, 8)
    other = first_generations(gate(), 8, 1)

    assert [(g.characters, g.results, g.scores) for g in once] == \
        [(g.characters, g.results, g.scores) for g in again]
    assert other[0].characters != once[0].characters


def test_training_learns_to_time_its_way_past_a_dot():
    level = gate()
    generations = []
    for generation in evolve.generations(level, SETTINGS, seed=3):
        generations.append(generation)
        if generation.beaten or generation.number == 60:
            break

    assert generations[-1].beaten, 'no character got past the dot'
    assert sum(generation.deaths for generation in generations) > 0
    best_scores = [generation.best_score for generation in generations]
    assert best_scores == sorted(best_scores), 'the best score dropped'
    winner = generations[-1].characters[generations[-1].best]
    replay = headless.play(level, evolve.steps(winner, SETTINGS.hold, SETTINGS.time_limit_steps(level)))
    assert replay == generations[-1].results[generations[-1].best]
    assert replay.ending is Ending.BEATEN


def test_train_reports_each_generation_and_how_it_ended(capsys):
    beaten = evolve.train(gate(), SETTINGS, seed=3, cap=60)

    lines = capsys.readouterr().out.splitlines()
    assert len(lines) == beaten.number + 1
    assert lines[0].startswith('generation    1  best score ')
    assert 'px from the goal' in lines[0] and 'died' in lines[0] and lines[0].endswith('not beaten')
    assert lines[-2].endswith('  beaten')
    moves = len(beaten.characters[beaten.best])
    assert lines[-1].startswith(f'Beaten in generation {beaten.number}, by a list of {moves} moves')


def test_train_gives_up_at_the_cap(capsys):
    assert evolve.train(gate(), SETTINGS, seed=3, cap=2) is None

    lines = capsys.readouterr().out.splitlines()
    assert len(lines) == 3
    assert lines[-1] == 'Not beaten in 2 generations.'
