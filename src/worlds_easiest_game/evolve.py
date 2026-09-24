'''Learning to beat a level over generations of characters, with no window.

A character is a list of moves (`headless.Move`), each held for `Settings.hold`
steps. A generation is a population of characters that all play the level
together through `headless.play_all`, each until it dies, beats the level, or
its moves run out, and is then scored. The next generation keeps the best
character unchanged and fills the rest with children of characters picked in
proportion to their scores, each a copy of its parent's moves with a few
changed at random. The first generation's lists are short, and every generation
adds a few random moves to its children's lists, up to the level's time limit,
so the early moves are worked out before the later ones matter:

    for generation in evolve.generations(level, evolve.Settings(population=300), seed=1):
        generation.best_score, generation.best_distance, generation.deaths, generation.beaten

A character is scored by where its run ended, measured as the distance it still
had to walk to the goal along the level's corridors (`distance_map`). The same
seed always trains the same way.
'''

import heapq
import math
import random
from dataclasses import dataclass
from functools import cached_property
from itertools import chain, count, islice, repeat

import pygame

from worlds_easiest_game import engine, headless
from worlds_easiest_game.headless import Ending, Move

MOVES = list(Move)
# What a move can change to when a child's copy of it changes.
OTHER_MOVES = {move: [other for other in MOVES if other is not move] for move in MOVES}

# The eight ways to step between neighbouring places, with how far each one walks.
NEIGHBOURS = [(dx, dy, math.hypot(dx, dy)) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if dx or dy]


def distance_map(level):
    '''How far the player has to walk to reach `level`'s goal from each place they can stand.

    A place is where the player's top-left corner is, in whole play-area pixels,
    and the player can stand there when their whole body is clear of the walls.
    The walk goes from place to neighbouring place, straight or diagonally, so it
    follows the corridors and never cuts through a wall. The places touching the
    goal are 0 away, by the same test an Attempt uses to call the level beaten.
    Places the player cannot reach the goal from are left out.
    '''
    walls = engine.level_walls(level)
    goal = engine.region_rect(*level.GOAL)
    corners = [corner for outline in engine.level_outlines(level) for corner in outline]
    left, top = (min(axis) for axis in zip(*corners))
    right, bottom = (max(axis) for axis in zip(*corners))
    player = pygame.Rect((0, 0), engine.PLAYER_SIZE)

    def clear(x, y):
        player.topleft = (x, y)
        return left <= x <= right and top <= y <= bottom and player.collidelist(walls) == -1

    distances = {}
    for x in range(left, right + 1):
        for y in range(top, bottom + 1):
            player.topleft = (x, y)
            if player.colliderect(goal) and clear(x, y):
                distances[x, y] = 0.0
    closed = set()  # places known not to be clear
    frontier = [(0.0, place) for place in distances]
    heapq.heapify(frontier)
    while frontier:
        distance, (x, y) = heapq.heappop(frontier)
        if distance > distances[x, y]:
            continue  # already reached by a shorter walk
        for dx, dy, length in NEIGHBOURS:
            place = (x + dx, y + dy)
            if distance + length < distances.get(place, math.inf) and place not in closed:
                if not clear(*place):
                    closed.add(place)
                    continue
                distances[place] = distance + length
                heapq.heappush(frontier, (distance + length, place))
    return distances


@dataclass(frozen=True)
class Settings:
    '''What shapes the learning. Every setting but the population size has a default.'''

    population: int  # characters in each generation
    mutation: float = 0.015  # the chance each move a child copies is changed to another
    hold: int = 12  # steps each move in a list is held for
    first_moves: int = 10  # moves in each list of the first generation
    growth: int = 3  # moves added to the lists each generation, up to the time limit
    time_limit: float | None = None  # seconds a character has; the level's TIME_LIMIT unless given
    # How the scoring rules count; see `score`.
    progress_weight: float = 8.0
    death_penalty: float = 0.1
    speed_weight: float = 1.0

    def __post_init__(self):
        checks = [
            (self.population >= 2, 'the population must be at least 2'),
            (0 <= self.mutation <= 1, 'the mutation rate must be between 0 and 1'),
            (self.hold >= 1, 'a move must be held for at least 1 step'),
            (self.first_moves >= 1, 'the first lists must have at least 1 move'),
            (self.growth >= 0, 'the growth must not be negative'),
            (self.time_limit is None or 0 < self.time_limit < math.inf,
             'the time limit must be positive and finite'),
            (self.progress_weight > 0, 'the progress weight must be positive'),
            (0 <= self.death_penalty < 1, 'the death penalty must be at least 0 and below 1'),
            (self.speed_weight >= 0, 'the speed weight must not be negative'),
        ]
        for ok, problem in checks:
            if not ok:
                raise ValueError(problem)

    def time_limit_steps(self, level):
        '''The most steps a character gets on `level`.'''
        limit = level.TIME_LIMIT if self.time_limit is None else self.time_limit
        return max(1, round(limit * engine.FPS))

    def moves_allowed(self, level, generation):
        '''How long the lists of generation `generation` (counting from 1) are on `level`.'''
        cap = -(-self.time_limit_steps(level) // self.hold)  # enough moves to fill the time limit
        return min(self.first_moves + self.growth * (generation - 1), cap)


def score(result, distance, limit, settings):
    '''How well a run went, by the scoring rules; higher is better, and always above 0.

    A run that beat the level scores 1, plus up to `speed_weight` more for the
    share of the time limit (`limit` steps) it had left. Any other run scores its
    closeness to the goal, `1 / (1 + tiles)` for the `distance` in floor tiles it
    still had to walk from where it ended, raised to the power `progress_weight`,
    which is below 1 anywhere off the goal; a death takes `death_penalty` of that away.
    A steep `progress_weight` can shrink that to nothing far from the goal, so
    it never goes below the smallest number above 0.
    '''
    if result.ending is Ending.BEATEN:
        return 1 + settings.speed_weight * (1 - result.step / limit)
    closeness = 1 / (1 + distance / engine.TILE_SIZE)
    points = closeness ** settings.progress_weight
    if result.ending is Ending.DIED:
        points *= 1 - settings.death_penalty
    return max(points, math.ulp(0.0))


def child(parent, length, mutation, rng):
    '''A copy of `parent` with each move changed to another at `mutation` odds,
    then random moves added until it is `length` long.'''
    moves = [rng.choice(OTHER_MOVES[move]) if rng.random() < mutation else move for move in parent]
    return moves + rng.choices(MOVES, k=length - len(moves))


def next_generation(characters, scores, length, mutation, rng):
    '''The generation after `characters`, which scored `scores`, and as many.

    The best character comes first and unchanged, so it plays exactly as it did.
    Every other place goes to a `child` of a parent picked at odds in proportion
    to its score, with lists `length` moves long and `mutation` odds of each
    copied move changing.
    '''
    best = max(range(len(characters)), key=scores.__getitem__)
    parents = rng.choices(characters, weights=scores, k=len(characters) - 1)
    return [characters[best]] + [child(parent, length, mutation, rng) for parent in parents]


@dataclass(frozen=True)
class Generation:
    '''One generation, played and scored.'''

    number: int  # counting from 1
    characters: list  # each a list of moves
    results: list  # how each one's run went, as `headless.Result`
    distances: list  # how far each one still had to walk to the goal when its run ended
    scores: list

    @cached_property
    def best(self):
        '''Where the best-scoring character is in the generation.'''
        return max(range(len(self.scores)), key=self.scores.__getitem__)

    @property
    def best_score(self):
        return self.scores[self.best]

    @property
    def best_distance(self):
        return self.distances[self.best]

    @property
    def deaths(self):
        return sum(result.ending is Ending.DIED for result in self.results)

    @property
    def beaten(self):
        '''Whether a character beat the level; if one did, the best one has.'''
        return self.results[self.best].ending is Ending.BEATEN


def steps(moves, hold, limit):
    '''The move for each step of a character's run: each of `moves` held for
    `hold` steps, cut off after `limit` steps.'''
    return islice(chain.from_iterable(repeat(move, hold) for move in moves), limit)


def generations(level, settings, seed=None):
    '''Every generation that learns to play `level`, in turn, from the first.

    The same `seed` always gives the same generations.
    '''
    rng = random.Random(seed)
    distances = distance_map(level)
    limit = settings.time_limit_steps(level)
    length = settings.moves_allowed(level, 1)
    characters = [rng.choices(MOVES, k=length) for _ in range(settings.population)]
    for number in count(1):
        results = headless.play_all(level, [steps(moves, settings.hold, limit) for moves in characters])
        ended = [distances[result.position] for result in results]
        scores = [score(result, distance, limit, settings) for result, distance in zip(results, ended)]
        yield Generation(number, characters, results, ended, scores)
        characters = next_generation(characters, scores, settings.moves_allowed(level, number + 1),
                                     settings.mutation, rng)


def summary(generation):
    '''One line on how `generation` went, for following a training run.'''
    total = len(generation.characters)
    return (f'generation {generation.number:4}  best score {generation.best_score:<9.3g}  '
            f'best ended {generation.best_distance:3.0f} px from the goal  '
            f'died {generation.deaths:{len(str(total))}}/{total}  '
            f'{"beaten" if generation.beaten else "not beaten"}')


def train(level, settings, seed, cap):
    '''Train on `level`, printing a `summary` of each generation, until a
    character beats it or `cap` generations have played.

    Returns the generation that beat the level, or None.
    '''
    for generation in islice(generations(level, settings, seed), cap):
        print(summary(generation), flush=True)
        if generation.beaten:
            winner = generation.results[generation.best]
            print(f'Beaten in generation {generation.number}, by a list of '
                  f'{len(generation.characters[generation.best])} moves that reached the goal '
                  f'{winner.step / engine.FPS:.2f} s in.')
            return generation
    print(f'Not beaten in {cap} generations.')
    return None
