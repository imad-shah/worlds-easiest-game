'''Tests for the learner: its distance maps and targets, scoring, selection,
mutation, and training level by level.

The distance map to the goal is checked on level 1 as a static fact, with no
play. Training only ever runs on small levels built here for it, never on the
game's own levels, which are only played on planned routes (test_perfect_run.py).
Nothing here opens a window or needs a display.
'''

import math
import random
import sys
from itertools import islice
from types import SimpleNamespace

import pygame
import pytest

from worlds_easiest_game import engine, evolve, headless, levels, obstacles
from worlds_easiest_game.evolve import Heading
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


def gate_with_a_coin():
    '''The gate, with a coin to fetch from a pocket above the start before the
    goal counts.'''
    return SimpleNamespace(
        PLAYFIELD=[(0, 0), (40, 0), (40, -60), (80, -60), (80, 0), (240, 0), (240, 60), (0, 60)],
        PLAYER_SPAWN=(8, 15), GOAL=((200, 0), (240, 60)), COINS=[(60, -40)],
        OBSTACLES=[vertical(x=120, from_y=10, to_y=50, speed=60)], TIME_LIMIT=4)


@pytest.fixture(scope='module')
def level1_distances():
    return evolve.Targets(level1).goal


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
    distances = evolve.Targets(box()).goal

    # The player touches the goal from x=132 and y=132 on, being 29px across.
    assert distances[132, 132] == 0
    assert distances[100, 132] == 32
    assert distances[100, 100] == pytest.approx(32 * math.sqrt(2))


def test_the_distance_to_a_coin_is_zero_wherever_the_player_touches_it():
    level = box(COINS=[(50, 150), (170, 30)])
    targets = evolve.Targets(level)

    assert set(targets.coins) == {(50, 150), (170, 30)}
    for coin, distances in targets.coins.items():
        touching = [place for place, distance in distances.items() if distance == 0]
        assert touching
        for place, distance in distances.items():
            player = pygame.Rect(place, engine.PLAYER_SIZE)
            assert (distance == 0) == obstacles.circle_touches_rect(coin, engine.COIN_RADIUS, player), place


def test_the_distance_to_the_checkpoint_is_zero_wherever_the_player_is_on_it():
    level = box(CHECKPOINT=((0, 0), (40, 40)))
    distances = evolve.Targets(level).checkpoint
    checkpoint = engine.region_rect(*level.CHECKPOINT)

    for place, distance in distances.items():
        assert (distance == 0) == checkpoint.colliderect(pygame.Rect(place, engine.PLAYER_SIZE)), place
    assert evolve.Targets(box()).checkpoint is None


def test_a_distance_map_builds_the_same_way_every_time():
    once, again = evolve.Targets(level1).goal, evolve.Targets(level1).goal

    assert list(once.items()) == list(again.items())


def test_a_run_heads_for_the_nearest_coin_it_has_not_collected():
    # Coins near the spawn's top-left and in the far bottom-left corner.
    near, far = (80, 60), (20, 180)
    targets = evolve.Targets(box(COINS=[far, near]))

    heading = targets.heading((100, 100), (far, near), False)
    assert heading == Heading('coin', targets.coins[near][100, 100], 2)
    assert heading.distance < targets.coins[far][100, 100]
    assert targets.heading((100, 100), (far,), False) == Heading('coin', targets.coins[far][100, 100], 1)


def test_the_goal_is_only_a_target_once_every_coin_is_collected():
    # The goal is in the bottom-right corner, right next to the player; the coin is far away.
    coin = (20, 20)
    targets = evolve.Targets(box(COINS=[coin]))
    by_the_goal = (130, 130)

    assert targets.heading(by_the_goal, (coin,), False).target == 'coin'
    assert targets.heading(by_the_goal, (), False) == Heading('goal', targets.goal[by_the_goal], 0)


def test_the_checkpoint_is_a_target_until_it_is_reached():
    targets = evolve.Targets(box(CHECKPOINT=((0, 0), (40, 40))))

    assert targets.heading((100, 100), (), False) == Heading('goal', targets.goal[100, 100], 1)
    assert targets.heading((60, 60), (), False) == Heading('checkpoint', targets.checkpoint[60, 60], 1)
    assert targets.heading((60, 60), (), True) == Heading('goal', targets.goal[60, 60], 0)


def closeness(distance):
    '''How close a run is on a level with only a goal to reach, `distance` px from it.'''
    return 1 / (1 + distance / engine.TILE_SIZE)


def test_on_a_level_with_only_a_goal_closeness_is_the_share_of_a_tile_walk_left():
    targets = evolve.Targets(box())

    for distance in (0, 1, 50, 700):
        assert targets.closeness(Heading('goal', distance, 0)) == closeness(distance)


def test_every_target_reached_scores_above_any_run_that_reached_one_fewer():
    targets = evolve.Targets(box(COINS=[(20, 20), (20, 180)], CHECKPOINT=((160, 0), (196, 40))))
    walks = [targets.goal, targets.checkpoint, *targets.coins.values()]
    longest = max(distances.longest for distances in walks)
    assert targets.stage == evolve.STEP_UP * (1 + longest / engine.TILE_SIZE)

    for left in range(3):
        # One more target reached, as far from the next one as the level allows,
        # against right on top of a target and still short of it.
        ahead = targets.closeness(Heading('coin', longest, left))
        behind = targets.closeness(Heading('coin', 0, left + 1))
        assert ahead == pytest.approx(evolve.STEP_UP * behind)
        assert targets.closeness(Heading('coin', 1, left)) > targets.closeness(Heading('coin', 2, left))
    assert targets.closeness(Heading('goal', 0, 0)) == 1


def test_a_run_that_collected_the_coin_is_closer_than_every_run_that_has_not():
    level = gate_with_a_coin()
    targets = evolve.Targets(level)
    places = [place for place, _ in targets.goal.items()]

    def closeness(place, coins_out):
        return targets.closeness(targets.heading(place, coins_out, False))

    collected = min(closeness(place, ()) for place in places)
    not_yet = max(closeness(place, tuple(level.COINS)) for place in places)
    assert collected > not_yet
    # Collecting the coin is a step up wherever the player stands to collect it.
    for place, distance in targets.coins[level.COINS[0]].items():
        if distance == 0:
            assert closeness(place, ()) >= evolve.STEP_UP * closeness(place, tuple(level.COINS))


def run(ending, step=100, position=(0, 0)):
    return Result(ending, step, position, 0, (), False)


def test_beating_the_level_scores_above_anything_else():
    last_step_win = evolve.score(run(Ending.BEATEN, step=LIMIT), 1, LIMIT, SETTINGS)
    near_miss = evolve.score(run(Ending.OUT_OF_MOVES), closeness(1), LIMIT, SETTINGS)

    assert last_step_win > near_miss


def test_beating_the_level_in_fewer_steps_scores_higher():
    scores = [evolve.score(run(Ending.BEATEN, step=step), 1, LIMIT, SETTINGS)
              for step in (100, 101, 500, LIMIT)]

    assert scores == sorted(scores, reverse=True)
    assert len(set(scores)) == len(scores)


def test_ending_closer_to_the_goal_scores_higher():
    scores = [evolve.score(run(Ending.OUT_OF_MOVES), closeness(distance), LIMIT, SETTINGS)
              for distance in (1, 2, 50, 700)]

    assert scores == sorted(scores, reverse=True)
    assert len(set(scores)) == len(scores)
    assert min(scores) > 0


@pytest.mark.parametrize('tiles', [0.1, 5, 10, 20])
def test_dying_scores_slightly_below_running_out_of_time_at_the_same_place(tiles):
    distance = tiles * engine.TILE_SIZE
    died = evolve.score(run(Ending.DIED), closeness(distance), LIMIT, SETTINGS)
    timed_out = evolve.score(run(Ending.OUT_OF_MOVES), closeness(distance), LIMIT, SETTINGS)
    a_tile_back = evolve.score(run(Ending.OUT_OF_MOVES), closeness(distance + engine.TILE_SIZE), LIMIT, SETTINGS)

    assert died == pytest.approx(timed_out * (1 - SETTINGS.death_penalty))
    assert died < timed_out
    assert died > a_tile_back, 'hanging back a tile scores better than dying'


def test_a_steep_progress_weight_still_scores_every_run_above_0():
    # Steep enough that far from the goal the closeness rounds to 0.0.
    settings = evolve.Settings(population=30, progress_weight=1e6)
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


@pytest.mark.parametrize('level', levels.LEVELS, ids=lambda level: level.__name__)
def test_every_level_gives_the_learner_its_own_time_limit(level):
    assert level.TIME_LIMIT > 0
    assert evolve.Settings(population=2).time_limit_steps(level) == round(level.TIME_LIMIT * engine.FPS)


def test_each_move_is_held_and_the_run_cut_off_at_the_time_limit():
    moves = [Move.UP, Move.LEFT, Move.DOWN]

    assert list(evolve.steps(moves, 3, 7)) == [Move.UP] * 3 + [Move.LEFT] * 3 + [Move.DOWN]


@pytest.mark.parametrize('bad', [
    dict(population=1), dict(mutation=1.5), dict(hold=0), dict(first_moves=0), dict(growth=-1),
    dict(hold=sys.maxsize + 1),  # more steps than can be counted
    dict(time_limit=0), dict(time_limit=math.inf), dict(time_limit=math.nan),
    dict(time_limit=1e17),  # more steps than can be counted
    dict(progress_weight=0), dict(progress_weight=math.inf), dict(death_penalty=1),
    dict(speed_weight=-1), dict(speed_weight=math.inf),
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


def test_training_learns_each_level_in_turn_and_keeps_its_solution():
    first, second = gate(), gate_with_a_coin()
    training = evolve.Training([first, second], SETTINGS, seed=3, cap=100)
    played = []
    for playing in training.rounds():
        played.append((playing.level, playing.number, playing.generation.beaten, len(training.solutions)))

    assert training.beaten and training.stuck is None
    # Every generation of the first level, then every one of the second, each counted from 1.
    switch = next(i for i, (level, *_) in enumerate(played) if level is second)
    assert all(level is first for level, *_ in played[:switch])
    assert [number for _, number, *_ in played] == [*range(1, switch + 1), *range(1, len(played) - switch + 1)]
    assert [beaten for *_, beaten, _ in played].count(True) == 2
    assert played[switch - 1][2] and played[-1][2]
    # The solution is kept as each level is beaten, before the next starts.
    assert [kept for *_, kept in played] == [0] * switch + [1] * (len(played) - switch)
    assert [solution.level for solution in training.solutions] == [first, second]
    assert [solution.generation for solution in training.solutions] == [switch, len(played) - switch]


def test_each_level_starts_a_new_population_from_its_spawn():
    first, second = gate(), gate_with_a_coin()
    training = evolve.Training([first, second], SETTINGS, seed=3, cap=100)
    rounds = training.rounds()
    playing = next(rounds)
    while playing.level is first:
        playing = next(rounds)

    assert playing.number == 1 and playing.champion is None
    assert all(len(moves) == SETTINGS.first_moves for moves in playing.characters)
    assert all(attempt.player.topleft == second.PLAYER_SPAWN for attempt in playing.runs.attempts)


def test_the_first_level_trains_just_as_it_does_alone():
    training = evolve.Training([gate(), gate_with_a_coin()], SETTINGS, seed=7)
    together = [playing.generation for playing in islice(training.rounds(), 5)]
    alone = first_generations(gate(), 7, 5)

    assert [(g.characters, g.results, g.scores) for g in together] == \
        [(g.characters, g.results, g.scores) for g in alone]


def test_the_same_seed_trains_every_level_the_same_way():
    def solutions(seed):
        training = evolve.Training([gate(), gate_with_a_coin()], SETTINGS, seed=seed, cap=100)
        for _ in training.rounds():
            pass
        return [(solution.generation, solution.moves) for solution in training.solutions]

    assert solutions(3) == solutions(3)


def test_the_kept_solutions_replay_as_one_run_through_every_level():
    training = evolve.Training([gate(), gate_with_a_coin()], SETTINGS, seed=3, cap=100)
    for _ in training.rounds():
        pass

    results = evolve.replay(training.solutions)

    assert results == [solution.result for solution in training.solutions]
    assert [result.ending for result in results] == [Ending.BEATEN] * 2
    assert results[1].coins == 1


def test_training_stops_at_a_level_not_beaten_within_the_cap():
    stuck = gate()
    stuck.TIME_LIMIT = 0.5  # 120px of walking, and the goal is further than that
    training = evolve.Training([gate(), stuck, gate()], SETTINGS, seed=3, cap=40)
    played = [(playing.level, playing.number) for playing in training.rounds()]

    assert len(training.solutions) == 1
    assert training.stuck is stuck and not training.beaten
    assert played[-3:] == [(stuck, 38), (stuck, 39), (stuck, 40)]
    assert training.level_number == 2


def test_train_reports_each_level_and_generation_and_how_it_ended(capsys):
    training = evolve.train([gate(), gate_with_a_coin()], SETTINGS, seed=3, cap=100)

    lines = capsys.readouterr().out.splitlines()
    first, second = training.solutions
    assert lines[0] == 'Level 1 of 2:'
    assert lines[1].startswith('generation    1  best score ')
    assert 'px from the goal' in lines[1] and 'died' in lines[1] and lines[1].endswith('not beaten')
    assert lines[first.generation].endswith('  beaten')
    assert lines[first.generation + 1].startswith(
        f'Level 1 beaten in generation {first.generation}, after ')
    assert lines[first.generation + 1].endswith(
        f'by a list of {len(first.moves)} moves that reached the goal {first.result.step / engine.FPS:.2f} s in.')
    assert lines[first.generation + 2] == 'Level 2 of 2:'
    assert 'best ended with ' in lines[first.generation + 3]
    assert '/1 coins, ' in lines[first.generation + 3]
    beaten = first.generation + 3 + second.generation
    assert lines[beaten].startswith(f'Level 2 beaten in generation {second.generation}, after ')
    assert lines[beaten + 1].startswith(f'Every level beaten, in {first.generation + second.generation} '
                                        'generations and ')
    assert lines[beaten + 2:] == [
        'Replaying the kept solutions, the whole game in one run:',
        f'Level 1: beaten {first.result.step / engine.FPS:.2f} s in.',
        f'Level 2: beaten {second.result.step / engine.FPS:.2f} s in.',
        f'The whole game took {(first.result.step + second.result.step) / engine.FPS:.2f} s of play.',
    ]


def test_train_names_the_level_it_gave_up_on(capsys):
    training = evolve.train([gate(), gate_with_a_coin()], SETTINGS, seed=3, cap=2)

    assert training.stuck is not None
    out = capsys.readouterr().out
    assert out.splitlines()[-1] == f'Level {training.level_number} not beaten in 2 generations.'
    assert 'Replaying' not in out


def test_a_round_scores_the_runs_it_was_stepped_through():
    rounds = evolve.rounds(gate(), SETTINGS, seed=7)
    watched = []
    for playing in islice(rounds, 5):
        for _ in range(30):  # partway, by hand, as the window does
            playing.runs.step()
        watched.append(playing.generation)

    whole = first_generations(gate(), 7, 5)
    assert [(g.characters, g.results, g.scores) for g in watched] == \
        [(g.characters, g.results, g.scores) for g in whole]


def test_a_solution_replays_as_the_winning_run():
    for playing in evolve.rounds(gate(), SETTINGS, seed=3):
        if playing.generation.beaten:
            break
    solution = playing.solution()
    generation = playing.generation

    assert solution.moves == generation.characters[generation.best]
    assert solution.result == generation.results[generation.best]
    assert solution.replay().finish() == [solution.result]


def nearest_alive(playing):
    alive = [i for i, ending in enumerate(playing.runs.endings) if ending is not Ending.DIED]
    return min(alive, key=lambda i: playing.targets.goal[playing.runs.attempts[i].player.topleft])


def test_the_first_generation_is_led_by_the_character_nearest_the_goal():
    playing = next(evolve.rounds(gate(), SETTINGS, seed=7))
    assert playing.champion is None
    leaders = set()
    while not playing.runs.over:
        playing.runs.step()
        assert playing.leader() == nearest_alive(playing)
        leaders.add(playing.leader())

    assert len(leaders) > 1


def test_later_generations_are_led_by_the_last_ones_best_until_it_dies():
    rounds = evolve.rounds(gate(), SETTINGS, seed=3)
    before = next(rounds).generation
    for playing in islice(rounds, 60):
        assert playing.champion == 0
        assert playing.characters[0] == before.characters[before.best]
        if before.results[before.best].ending is Ending.DIED:
            break  # the champion dies again, just as it did
        before = playing.generation
    else:
        pytest.fail('no champion died')

    while playing.runs.endings[0] is None:
        assert playing.leader() == 0
        playing.runs.step()
    assert playing.runs.endings[0] is Ending.DIED
    assert playing.leader() == nearest_alive(playing) != 0
