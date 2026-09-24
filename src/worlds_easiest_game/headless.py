'''Playing a level from a list of moves, with no window and no display.

A move is what a player holds for one STEP: one of the eight directions, or
nothing at all. `play` runs a level's `engine.Attempt` one move per step, as fast
as the machine allows, and reports how the run ended:

    result = headless.play(levels.LEVELS[0], [Move.RIGHT, Move.RIGHT, Move.DOWN_RIGHT, ...])
    result.ending, result.step, result.position, result.coins, result.coins_out

`play_all` plays many lists of moves on one level at once and reports each run
just as `play` would. `Runs` plays them the same way one step at a time, the
way a whole generation of learning characters plays (see `evolve`), so they
can be drawn as they go (see `watch`).

A move reaches the attempt through `engine.read_input`, from the keys it holds,
so it moves the player exactly as the keyboard does: diagonals no faster than
straight lines, sliding along walls. The game logic advances only in fixed
steps, so the same moves on the same level always end the same way.
'''

from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType

import pygame

from worlds_easiest_game import engine

MOVEMENT_KEYS = (pygame.K_w, pygame.K_a, pygame.K_s, pygame.K_d)


class Move(Enum):
    '''The movement keys held for one step, named for the way they move the player.'''

    STAY = frozenset()
    UP = frozenset({pygame.K_w})
    DOWN = frozenset({pygame.K_s})
    LEFT = frozenset({pygame.K_a})
    RIGHT = frozenset({pygame.K_d})
    UP_LEFT = frozenset({pygame.K_w, pygame.K_a})
    UP_RIGHT = frozenset({pygame.K_w, pygame.K_d})
    DOWN_LEFT = frozenset({pygame.K_s, pygame.K_a})
    DOWN_RIGHT = frozenset({pygame.K_s, pygame.K_d})

    def __init__(self, keys):
        # What pygame.key.get_pressed() reports for the movement keys while this
        # move is held, and the velocity the keyboard's rules give it.
        self.pressed = MappingProxyType({key: key in keys for key in MOVEMENT_KEYS})
        self.velocity = engine.read_input(self.pressed)


class Ending(Enum):
    '''How a run ended.'''

    DIED = 'died'  # a dot touched the player
    BEATEN = 'beaten'  # every coin collected, then the goal reached
    OUT_OF_MOVES = 'out of moves'


@dataclass(frozen=True)
class Result:
    '''How a run ended, and where it left the player.'''

    ending: Ending
    step: int  # the step it ended on, counting from 1; 0 if it had no moves
    position: tuple  # the player's top-left corner then, in play-area pixels
    coins: int  # coins collected by then
    coins_out: tuple  # the centers of the coins not collected by then, in the level's order
    reached_checkpoint: bool  # whether the player had been on the level's CHECKPOINT by then


def play(level, moves):
    '''Play `level` from its start, one of `moves` per step.

    The run ends at the first death, on beating the level, or when the moves run out.
    '''
    return play_all(level, [moves])[0]


def play_all(level, move_lists):
    '''Play `level` once from each list in `move_lists`, and report each run as `play` would.

    The runs play together, as `Runs`, sharing one set of dots.
    '''
    return Runs(level, move_lists).finish()


class Runs:
    '''Runs of one level, one from each list in `move_lists`, started together and
    stepped together, sharing one set of dots.

    The dots move once a step for all of the runs instead of once for each. `step`
    advances every run still going by one step, so the runs can be watched as they
    play; a run that ends drops out while the rest play on, and `endings` says
    how each one ended, or None while it is still going. `finish` plays out the
    rest and reports each run as `play` would.
    '''

    def __init__(self, level, move_lists):
        self.dots = engine.Dots(level)
        self.attempts = [engine.Attempt(level, dots=self.dots) for _ in move_lists]
        self.endings = [None] * len(self.attempts)
        self.steps = 0  # steps taken by the runs that have gone longest
        # Each run still going, with the move it takes next, so a run whose moves
        # have run out ends on its last step rather than on the one after.
        self.going = []
        for i, moves in enumerate(move_lists):
            self._queue(i, iter(moves))

    def _queue(self, i, moves):
        '''Line up run `i`'s next move from `moves`, or end it if it has none.'''
        move = next(moves, None)
        if move is None:
            self.endings[i] = Ending.OUT_OF_MOVES
        else:
            self.going.append((i, move, moves))

    @property
    def over(self):
        return not self.going

    @property
    def alive(self):
        '''The attempts of the runs no dot has touched, going or not.'''
        return [attempt for attempt, ending in zip(self.attempts, self.endings) if ending is not Ending.DIED]

    def step(self):
        '''Advance every run still going by one step.'''
        if self.over:
            return
        self.steps += 1
        going, self.going = self.going, []
        for i, move, moves in going:
            attempt = self.attempts[i]
            attempt.step(move.velocity)
            if attempt.died:
                self.endings[i] = Ending.DIED
            elif attempt.beaten:
                self.endings[i] = Ending.BEATEN
            else:
                self._queue(i, moves)

    def finish(self):
        '''Play every run to its end, and report each one as `play` would.'''
        while not self.over:
            self.step()
        return [result(ending, attempt) for ending, attempt in zip(self.endings, self.attempts)]


def result(ending, attempt):
    '''The `Result` of a run that ended as `ending`, with `attempt` where it ended.'''
    return Result(ending, attempt.steps, attempt.player.topleft, attempt.coins_collected,
                  tuple(attempt.coins), attempt.reached_checkpoint)
