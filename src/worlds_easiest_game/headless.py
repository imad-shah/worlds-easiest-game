'''Playing a level from a list of moves, with no window and no display.

A move is what a player holds for one STEP: one of the eight directions, or
nothing at all. `play` runs a level's `engine.Attempt` one move per step, as fast
as the machine allows, and reports how the run ended:

    result = headless.play(levels.LEVELS[0], [Move.RIGHT, Move.RIGHT, Move.DOWN_RIGHT, ...])
    result.ending, result.step, result.position, result.coins

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


def play(level, moves):
    '''Play `level` from its start, one of `moves` per step.

    The run ends at the first death, on beating the level, or when the moves run out.
    '''
    attempt = engine.Attempt(level)
    ending = Ending.OUT_OF_MOVES
    for move in moves:
        attempt.step(move.velocity)
        if attempt.died:
            ending = Ending.DIED
            break
        if attempt.beaten:
            ending = Ending.BEATEN
            break
    return Result(ending, attempt.steps, attempt.player.topleft, attempt.coins_collected)
