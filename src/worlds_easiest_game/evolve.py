'''Learning to beat the game over generations of characters, level by level, with no window.

A character is a list of moves (`headless.Move`), each held for `Settings.hold`
steps. A generation is a population of characters that all play a level
together through `headless.Runs`, each until it dies, beats the level, or its
moves run out, and is then scored. The next generation keeps the best
character unchanged and fills the rest with children of the best-ranked
characters (see `ranking`). A child plays its parent's moves up to a random
point at most a few moves before where its parent's run ended, then new random
moves, up to a few past that end (see `child`): so learning picks up where
each run got to, and usually tries something else shortly before where it
died. It can replay its parent's ending instead, though, when it goes back no
moves, or when its new moves repeat its parent's, as they often do along a
straight dash. The first generation's lists are short, and they grow only as
far as the runs get, up to the level's time limit, so the early moves are
worked out before the later ones matter:

    for generation in evolve.generations(level, evolve.Settings(population=300), seed=1):
        generation.best_score, generation.best_distance, generation.deaths, generation.beaten

A character is scored by where its run ended, measured as the distance it still
had to walk along the level's corridors to the next of its `Targets`: a coin it
has not collected, or the checkpoint it has not reached, and then the goal. A
run that died counts as having ended a few tiles further back, so waiting where
it is safe beats rushing in to die a little closer. The same seed always trains
the same way. `rounds` gives each generation as it starts to play, as a
`Round`, so its runs can be watched step by step (see `watch`) before they are
scored.

`Training` learns a list of levels in order: once a generation beats a level,
its best character's moves are kept as that level's `Solution`, and a new
population starts on the next level. Once the last level is beaten, the
solutions together are one run of the whole game, which `replay` plays.
'''

import heapq
import math
import random
import sys
import time
from array import array
from dataclasses import dataclass
from functools import cached_property, partial
from itertools import chain, count, islice, repeat
from typing import NamedTuple

import pygame

from worlds_easiest_game import engine, headless, obstacles
from worlds_easiest_game.headless import Ending, Move

MOVES = list(Move)

# The eight ways to step between neighbouring places, with how far each one walks.
NEIGHBOURS = [(dx, dy, math.hypot(dx, dy)) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if dx or dy]
# The least that reaching a target (a coin or the checkpoint) multiplies a run's closeness by.
STEP_UP = 2


class Floor:
    '''Every place the player can stand on `level`, for working out how far apart they are.

    A place is where the player's top-left corner is, in whole play-area pixels,
    and the player can stand there when their whole body is clear of the walls.
    The places are kept in one flat grid over the course, so a walk to each of
    the level's targets (`distances`) is quick to work out and small to keep.
    '''

    def __init__(self, level):
        corners = [corner for outline in engine.level_outlines(level) for corner in outline]
        self.left, self.top = (min(axis) for axis in zip(*corners))
        self.right, self.bottom = (max(axis) for axis in zip(*corners))
        # A border one place wide runs round the grid and is never clear, so every
        # place on the course has all eight of its neighbours on the grid.
        self.width = self.right - self.left + 3
        self.clear = bytearray(self.width * (self.bottom - self.top + 3))
        self._mark(self.left, self.top, self.right, self.bottom, 1)
        width, height = engine.PLAYER_SIZE
        for wall in engine.level_walls(level):
            # Every place the player's body would overlap the wall from.
            self._mark(wall.left - width + 1, wall.top - height + 1, wall.right - 1, wall.bottom - 1, 0)

    def _mark(self, left, top, right, bottom, clear):
        '''Set whether the places from (left, top) to (right, bottom), inclusive
        and cut to the course, are `clear`.'''
        left, right = max(left, self.left), min(right, self.right)
        for y in range(max(top, self.top), min(bottom, self.bottom) + 1):
            if left <= right:
                start = self.index((left, y))
                self.clear[start:start + right - left + 1] = bytes([clear]) * (right - left + 1)

    def index(self, place):
        '''Where `place` is in the grid, or None if it is off the course.'''
        x, y = place
        if self.left <= x <= self.right and self.top <= y <= self.bottom:
            return (y - self.top + 1) * self.width + (x - self.left + 1)
        return None

    def place(self, index):
        '''The place at `index` in the grid.'''
        y, x = divmod(index, self.width)
        return (x - 1 + self.left, y - 1 + self.top)

    def distances(self, zone, reached):
        '''How far the player has to walk from each place to reach a target, as `Distances`.

        `reached` says whether the player, a Rect, has reached the target, by the
        same test an Attempt uses, and can only say so while the player overlaps
        `zone`, a Rect. The places it says so for are 0 away. The walk goes from
        place to neighbouring place, straight or diagonally, so it follows the
        corridors and never cuts through a wall.
        '''
        walks = array('d', [math.inf]) * len(self.clear)
        width, height = engine.PLAYER_SIZE
        player = pygame.Rect((0, 0), engine.PLAYER_SIZE)
        frontier = []
        for x in range(max(zone.left - width + 1, self.left), min(zone.right - 1, self.right) + 1):
            for y in range(max(zone.top - height + 1, self.top), min(zone.bottom - 1, self.bottom) + 1):
                i = self.index((x, y))
                player.topleft = (x, y)
                if self.clear[i] and reached(player):
                    walks[i] = 0.0
                    frontier.append((0.0, i))
        neighbours = [(dx + dy * self.width, length) for dx, dy, length in NEIGHBOURS]
        clear = self.clear
        while frontier:
            walked, i = heapq.heappop(frontier)
            if walked > walks[i]:
                continue  # already reached by a shorter walk
            for step, length in neighbours:
                further = walked + length
                if further < walks[i + step] and clear[i + step]:
                    walks[i + step] = further
                    heapq.heappush(frontier, (further, i + step))
        return Distances(self, walks)


class Distances:
    '''How far the player has to walk to reach one target from each place on a `Floor`.

    `distances[place]` is the walk from `place`, and math.inf from anywhere the
    player cannot reach the target from, or cannot stand; only the places they
    can reach it from are `in` it.
    '''

    def __init__(self, floor, walks):
        self.floor = floor
        self.walks = walks

    def __getitem__(self, place):
        i = self.floor.index(place)
        return math.inf if i is None else self.walks[i]

    def __contains__(self, place):
        return self[place] < math.inf

    def items(self):
        '''Every place the target can be reached from, with how far it is.'''
        return ((self.floor.place(i), walk) for i, walk in enumerate(self.walks) if walk < math.inf)

    @cached_property
    def longest(self):
        '''The longest walk to the target from anywhere it can be reached from.'''
        return max((walk for walk in self.walks if walk < math.inf), default=0.0)


class Heading(NamedTuple):
    '''What a run was heading for when it ended, and how far it still had to go.'''

    target: str  # 'goal', 'coin' or 'checkpoint'
    distance: float  # px it still had to walk to that target
    left: int  # targets not reached yet: its coins still out, and the checkpoint unless reached


def coin_zone(coin):
    '''A Rect covering all of a coin, so a player touching it overlaps the Rect.'''
    radius = math.ceil(engine.COIN_RADIUS)
    return pygame.Rect(math.floor(coin[0]) - radius, math.floor(coin[1]) - radius, 2 * radius + 2, 2 * radius + 2)


def touches_coin(coin, player):
    '''Whether `player`, a Rect, touches `coin`, the test an Attempt collects it by.'''
    return obstacles.circle_touches_rect(coin, engine.COIN_RADIUS, player)


class Targets:
    '''What a character on `level` heads for, and how far away each one is along the corridors.

    The level's coins are targets until collected, and so is its CHECKPOINT, if
    it has one, until reached; the goal becomes one once every coin is
    collected, since only then does reaching it beat the level. A run heads for
    whichever target it has left is the nearest walk away. A distance map to
    each target is worked out once, when the Targets are made.

    `closeness` scores where a run ended: as on a level with only a goal to
    reach, `1 / (1 + tiles)` for the `tiles` it still had to walk to its target,
    plus `death_cost` more tiles if it died there, but divided by `stage` for
    every coin it had still out, and for the checkpoint until reached. `stage`
    is STEP_UP times `1 + tiles + death_cost` for the longest walk to any
    target on the level, so a run that has reached one more target is always
    closer than one that has not, wherever and however each ended, and
    collecting a coin or reaching the checkpoint at least multiplies a run's
    closeness by STEP_UP.
    '''

    def __init__(self, level, death_cost=0.0):
        self.death_cost = death_cost
        floor = Floor(level)
        goal = engine.region_rect(*level.GOAL)
        self.goal = floor.distances(goal, goal.colliderect)
        self.coins = {coin: floor.distances(coin_zone(coin), partial(touches_coin, coin)) for coin in level.COINS}
        checkpoint = getattr(level, 'CHECKPOINT', None)
        self.checkpoint = None
        if checkpoint:
            checkpoint = engine.region_rect(*checkpoint)
            self.checkpoint = floor.distances(checkpoint, checkpoint.colliderect)
        walks = [self.goal, *self.coins.values(), *filter(None, [self.checkpoint])]
        longest = max(distances.longest for distances in walks)
        self.stage = STEP_UP * (1 + longest / engine.TILE_SIZE + death_cost)

    def heading(self, position, coins_out, reached_checkpoint):
        '''What a run at `position`, with `coins_out` not collected yet, heads for
        next, as a `Heading`.'''
        left = [('coin', self.coins[coin]) for coin in coins_out]
        if self.checkpoint and not reached_checkpoint:
            left.append(('checkpoint', self.checkpoint))
        choices = left if coins_out else [*left, ('goal', self.goal)]
        target, distance = min(((target, distances[position]) for target, distances in choices),
                               key=lambda choice: choice[1])
        return Heading(target, distance, len(left))

    def closeness(self, heading, died=False):
        '''How close a run heading as `heading` has come to beating the level,
        having `died` there or not: 1 on the goal, and above 0 anywhere it can
        still reach it from.'''
        tiles = heading.distance / engine.TILE_SIZE + (self.death_cost if died else 0)
        return 1 / (1 + tiles) / self.stage ** heading.left


@dataclass(frozen=True)
class Settings:
    '''What shapes the learning. Every setting but the population size has a default.'''

    population: int  # characters in each generation
    hold: int = 12  # steps each move in a list is held for
    first_moves: int = 10  # moves in each list of the first generation
    growth: int = 3  # moves a child plays past where its parent's run ended, up to the time limit
    backtrack: int = 5  # most of its parent's last moves a child replaces with new ones
    persistence: float = 0.6  # the chance a new random move repeats the one before it
    parents: float = 0.2  # the share of each generation, the best-ranked, that children come from
    spot: int = 20  # px; the side of the squares a run's end is placed in, for `ranking`
    death_cost: float = 3.0  # tiles further from its target a run that died counts as
    time_limit: float | None = None  # seconds a character has; the level's TIME_LIMIT unless given

    def __post_init__(self):
        checks = [
            (self.population >= 2, 'the population must be at least 2'),
            (self.first_moves >= 1, 'the first lists must have at least 1 move'),
            (self.growth >= 1, 'the growth must be at least 1 move'),
            (self.backtrack >= 0, 'the backtrack must not be negative'),
            (0 <= self.persistence < 1, 'the persistence must be at least 0 and below 1'),
            (0 < self.parents <= 1, 'the parents\' share must be above 0 and at most 1'),
            (self.spot >= 1, 'the spots must be at least 1 px wide'),
            (0 <= self.death_cost < math.inf, 'the death cost must be at least 0 and finite'),
            # A run is counted out step by step, so a move's steps and the run's must fit in a Python index.
            (1 <= self.hold <= sys.maxsize,
             f'a move must be held for at least 1 step and at most {sys.maxsize} steps'),
            (self.time_limit is None or 0 < self.time_limit * engine.FPS <= sys.maxsize,
             f'the time limit must be positive and at most {sys.maxsize / engine.FPS:.3g} seconds'),
        ]
        for ok, problem in checks:
            if not ok:
                raise ValueError(problem)

    def time_limit_steps(self, level):
        '''The most steps a character gets on `level`.'''
        limit = level.TIME_LIMIT if self.time_limit is None else self.time_limit
        return max(1, round(limit * engine.FPS))

    def most_moves(self, level):
        '''The most moves a list can have on `level`: enough to fill its time limit.'''
        return -(-self.time_limit_steps(level) // self.hold)


def score(result, closeness, limit):
    '''How well a run went; higher is better.

    A run that beat the level scores 1, plus the share of the time limit
    (`limit` steps) it had left, so the sooner the better. Any other run scores
    its `closeness` to beating the level (`Targets.closeness`), which is below 1.
    '''
    if result.ending is Ending.BEATEN:
        return 1 + (1 - result.step / limit)
    return closeness


def played(moves, result, hold):
    '''How many of `moves`, each held for `hold` steps, a run that ended as
    `result` played: every one it started, including the one it ended on.'''
    return min(len(moves), -(-result.step // hold))


def random_moves(count, before, persistence, rng):
    '''`count` random moves, following the move `before` (None if there is
    none). Each repeats the move before it at `persistence` odds, and is
    otherwise any of the nine, so straight runs and long waits come up often.'''
    moves = []
    for _ in range(count):
        before = before if before is not None and rng.random() < persistence else rng.choice(MOVES)
        moves.append(before)
    return moves


def child(parent, ended, settings, most, rng):
    '''A child of `parent`, whose run ended during its move `ended` (counting
    from 1), on a level whose lists hold at most `most` moves.

    It keeps its parent's moves up to a point 0 to `settings.backtrack` moves
    before that end, picked at random, and plays new `random_moves` from there,
    up to `settings.growth` moves past it.
    '''
    kept = parent[:max(0, ended - rng.randint(0, settings.backtrack))]
    length = min(ended + settings.growth, most)
    return kept + random_moves(length - len(kept), kept[-1] if kept else None, settings.persistence, rng)


def ranking(results, scores, spot):
    '''Every character, by where it is in the generation's ranking, best first.

    A character ranks by its score, but only the best of those whose runs ended
    in the same `spot`-px square of the level, with as many coins collected
    (whichever coins they are) and the checkpoint reached or not, ranks among
    the others; the rest of them come after every such best one. So the
    best-ranked are spread over every place the runs have got to, not crowded
    onto one.
    '''
    best_first = sorted(range(len(scores)), key=scores.__getitem__, reverse=True)
    spots, firsts, crowded = set(), [], []
    for i in best_first:
        result = results[i]
        x, y = result.position
        place = (x // spot, y // spot, result.coins, result.reached_checkpoint)
        (crowded if place in spots else firsts).append(i)
        spots.add(place)
    return firsts + crowded


def next_generation(generation, settings, most, rng):
    '''The generation after `generation` (a `Generation`), and as many, with
    lists of at most `most` moves.

    The best character comes first and unchanged, so it plays exactly as it did.
    Every other place goes to a `child` of a parent picked at random from the
    best-ranked `settings.parents` share of the generation (see `ranking`).
    '''
    ranked = ranking(generation.results, generation.scores, settings.spot)
    parents = ranked[:max(1, round(settings.parents * len(ranked)))]
    characters, results = generation.characters, generation.results
    children = [characters[generation.best]]
    for i in (rng.choice(parents) for _ in range(len(characters) - 1)):
        moves = characters[i]
        children.append(child(moves, played(moves, results[i], settings.hold), settings, most, rng))
    return children


@dataclass(frozen=True)
class Generation:
    '''One generation, played and scored.'''

    number: int  # counting from 1
    characters: list  # each a list of moves
    results: list  # how each one's run went, as `headless.Result`
    headings: list  # what each one was heading for when its run ended, as `Heading`
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
        return self.headings[self.best].distance

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


class Round:
    '''A generation at play: its characters' runs on `level`, stepping together,
    and then how they scored.

    `runs` (a `headless.Runs`) can be stepped one step at a time to watch the
    runs play; `generation` plays out whatever is left of them and scores them,
    so the runs watched are the very runs that are scored.
    '''

    def __init__(self, level, number, characters, settings, targets):
        self.level = level
        self.number = number  # counting from 1
        self.characters = characters
        self.settings = settings
        self.targets = targets  # the level's `Targets`
        self.limit = settings.time_limit_steps(level)
        self.runs = headless.Runs(level, [steps(moves, settings.hold, self.limit) for moves in characters])

    @property
    def champion(self):
        '''Where the best character of the generation before is in this one, which
        `next_generation` carries over unchanged as the first; None in the first generation.'''
        return 0 if self.number > 1 else None

    def closeness(self, attempt):
        '''How close `attempt`, one of the runs, is to beating the level now (`Targets.closeness`).'''
        heading = self.targets.heading(attempt.player.topleft, attempt.coins, attempt.reached_checkpoint)
        return self.targets.closeness(heading)

    def leader(self):
        '''The character to follow as the runs play: the `champion` until a dot
        touches it, and otherwise the character alive now that is closest to
        beating the level. None once every character has died.'''
        alive = [i for i, ending in enumerate(self.runs.endings) if ending is not Ending.DIED]
        if self.champion in alive:
            return self.champion
        return max(alive, key=lambda i: self.closeness(self.runs.attempts[i]), default=None)

    @cached_property
    def generation(self):
        '''This generation, played and scored.'''
        results = self.runs.finish()
        headings = [self.targets.heading(result.position, result.coins_out, result.reached_checkpoint)
                    for result in results]
        scores = [score(result, self.targets.closeness(heading, result.ending is Ending.DIED), self.limit)
                  for result, heading in zip(results, headings)]
        return Generation(self.number, self.characters, results, headings, scores)

    def solution(self):
        '''The best character's moves, kept as this level's `Solution`.'''
        generation = self.generation
        return Solution(self.level, self.number, generation.characters[generation.best],
                        self.settings.hold, self.limit, generation.results[generation.best])


def level_rounds(level, settings, rng):
    '''Every generation that learns to play `level`, in turn, from the first, as it
    starts to play (a `Round`), bred with `rng`, a `random.Random`.

    The next generation is bred once the one before it has been scored, which
    plays out whatever of it is left.
    '''
    targets = Targets(level, settings.death_cost)
    most = settings.most_moves(level)
    length = min(settings.first_moves, most)
    characters = [random_moves(length, None, settings.persistence, rng) for _ in range(settings.population)]
    for number in count(1):
        playing = Round(level, number, characters, settings, targets)
        yield playing
        characters = next_generation(playing.generation, settings, most, rng)


def rounds(level, settings, seed=None):
    '''Every generation that learns to play `level` alone, as `level_rounds` gives
    them. The same `seed` always gives the same generations.'''
    return level_rounds(level, settings, random.Random(seed))


def generations(level, settings, seed=None):
    '''Every generation that learns to play `level` alone, in turn, from the first,
    played and scored. The same `seed` always gives the same generations.
    '''
    return (playing.generation for playing in rounds(level, settings, seed))


@dataclass(frozen=True)
class Solution:
    '''A level's kept solution: the moves of the character that beat it.'''

    level: object
    generation: int  # the generation that beat the level, counting from 1
    moves: list
    hold: int  # steps each move is held for
    limit: int  # the level's time limit, in steps
    result: headless.Result  # how its winning run ended

    def replay(self):
        '''A fresh run of the moves alone, as `headless.Runs`, which plays out just
        as the winning run did.'''
        return headless.Runs(self.level, [steps(self.moves, self.hold, self.limit)])


class Training:
    '''Learning to beat `levels` in order, one level at a time, as `settings` says.

    `rounds` gives every generation in turn, as it starts to play. Each level is
    learned as `level_rounds` learns it, by a population that starts from the
    level's spawn, all bred from one `random.Random(seed)`, so the same seed
    always trains the same way. Once a generation beats its level, its best
    character's moves are kept in `solutions`, and learning moves on to the next
    level. It ends once the last level is beaten, when the solutions together
    are one run of the whole game, or once a level has played `cap` generations
    without being beaten, which is then `stuck`.
    '''

    def __init__(self, levels, settings, seed=None, cap=None):
        self.levels = levels
        self.settings = settings
        self.cap = cap
        self.rng = random.Random(seed)
        self.solutions = []  # each level's `Solution`, in order, as it is beaten
        self.stuck = None  # the level not beaten within `cap` generations, if one was not

    @property
    def level_number(self):
        '''Which level, counting from 1, is being learned, or was learned last.'''
        return min(len(self.solutions) + 1, len(self.levels))

    @property
    def beaten(self):
        '''Whether every level has been beaten.'''
        return len(self.solutions) == len(self.levels)

    def rounds(self):
        '''Every generation in turn, level by level, as it starts to play (a
        `Round`). The next one starts once the one before it has been scored.'''
        for level in self.levels:
            for playing in level_rounds(level, self.settings, self.rng):
                yield playing
                if playing.generation.beaten:
                    self.solutions.append(playing.solution())
                    break
                if playing.number == self.cap:
                    self.stuck = level
                    return


def replay(solutions):
    '''Play `solutions` one after another, the whole game in one run when there is
    one for every level: how each run ended, as `headless.Result`.'''
    return [solution.replay().finish()[0] for solution in solutions]


def heading_text(heading):
    return {'goal': 'the goal', 'coin': 'a coin', 'checkpoint': 'the checkpoint'}[heading.target]


def summary(generation, coins=0):
    '''One line on how `generation` went, on a level with `coins` coins, for
    following a training run.'''
    total = len(generation.characters)
    best = generation.results[generation.best]
    heading = generation.headings[generation.best]
    collected = f'with {best.coins}/{coins} coins, ' if coins else ''
    return (f'generation {generation.number:4}  best score {generation.best_score:<9.3g}  '
            f'best ended {collected}{generation.best_distance:3.0f} px from {heading_text(heading)}  '
            f'died {generation.deaths:{len(str(total))}}/{total}  '
            f'{"beaten" if generation.beaten else "not beaten"}')


def duration(seconds):
    '''`seconds` of training, as a person would say it.'''
    minutes, seconds = divmod(round(seconds), 60)
    return f'{minutes} min {seconds} s' if minutes else f'{seconds} s'


class Log:
    '''Prints how `training` goes: which level it is learning, a `summary` line
    for each generation, and how each level was beaten.'''

    def __init__(self, training):
        self.training = training
        # When training began, and when it began on the level it is on: when the one before was beaten.
        self.started = self.level_started = time.perf_counter()
        self.generations = 0  # played so far, on every level

    def round(self, playing):
        '''Print how `playing`, the latest Round, went, once it has been scored.'''
        number, total = self.training.level_number, len(self.training.levels)
        if playing.number == 1:
            print(f'Level {number} of {total}:', flush=True)
        generation = playing.generation
        self.generations += 1
        print(summary(generation, len(playing.level.COINS)), flush=True)
        if generation.beaten:
            beaten = time.perf_counter()
            winner = generation.results[generation.best]
            print(f'Level {number} beaten in generation {generation.number}, after '
                  f'{duration(beaten - self.level_started)} of training, by a list of '
                  f'{len(generation.characters[generation.best])} moves that reached the goal '
                  f'{winner.step / engine.FPS:.2f} s in.', flush=True)
            self.level_started = beaten

    def end(self):
        '''Print how training ended.'''
        training = self.training
        if training.beaten:
            print(f'Every level beaten, in {self.generations} generations and '
                  f'{duration(time.perf_counter() - self.started)} of training.', flush=True)
        elif training.stuck is not None:
            print(f'Level {training.level_number} not beaten in {training.cap} generations.', flush=True)


def train(levels, settings, seed, cap):
    '''Train on `levels` in order, printing how it goes, until every level is
    beaten or a level has played `cap` generations without being beaten. Once
    every level is beaten, replay the kept solutions end to end.

    Returns the `Training`.
    '''
    training = Training(levels, settings, seed, cap)
    log = Log(training)
    for playing in training.rounds():
        log.round(playing)
    log.end()
    if training.beaten:
        print('Replaying the kept solutions, the whole game in one run:', flush=True)
        results = replay(training.solutions)
        for number, result in enumerate(results, 1):
            print(f'Level {number}: {result.ending.value} {result.step / engine.FPS:.2f} s in.', flush=True)
        played = sum(result.step for result in results) / engine.FPS
        print(f'The whole game took {played:.2f} s of play.', flush=True)
    return training
