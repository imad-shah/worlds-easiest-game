'''World's Easiest Game -- a recreation of "World's Hardest Game".

`main` is what the `worlds-easiest-game` console script runs; `game/main.py`
calls the same function.
'''

import argparse
import dataclasses
import os
import random
import sys

# pygame prints a banner the first time it is imported unless this is set; the
# game's own modules all import it, so it is set before any of them load.
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')

from worlds_easiest_game import engine, evolve, levels, watch  # noqa: E402

# The learner's settings the `train` command offers, each with what it sets.
TRAINING_OPTIONS = {
    'hold': (int, 'steps each move in a list is held for'),
    'first_moves': (int, 'moves in each list of the first generation'),
    'growth': (int, 'moves a child plays past where its parent\'s run ended'),
    'backtrack': (int, 'most of its parent\'s last moves a child replaces with new ones'),
    'persistence': (float, 'chance a new random move repeats the one before it'),
    'parents': (float, 'share of each generation, the best-ranked, that children come from'),
    'spot': (int, 'px; runs ending in the same square of this size rank behind the best of them'),
    'death_cost': (float, 'tiles further from its target a run that died counts as'),
    'time_limit': (float, 'seconds a character has on each level (default: each level\'s own)'),
}
DEFAULT_GENERATIONS = 1000


def parse_args(argv=None):
    '''The command line: play the game, or `train` a learner to beat every level
    in turn, in the window with `--watch`.

    Playing takes `--dev`, which turns on developer-only keys (T toggles god mode).
    Training gathers its options into `settings`, an `evolve.Settings`.
    '''
    parser = argparse.ArgumentParser(prog='worlds-easiest-game')
    parser.add_argument('--dev', action='store_true',
                        help='developer mode: press T in a level to toggle god mode')
    commands = parser.add_subparsers(dest='command', title='commands',
                                     description='with no command, the game opens in a window')
    train = commands.add_parser('train', help='learn to beat every level over generations',
                                description='Learn to beat every level in turn over generations of '
                                            'characters, printing a line per generation: with no window, '
                                            'as fast as the machine allows, or in the window with --watch.')
    train.add_argument('population', type=int, help='characters in each generation')
    train.add_argument('--watch', action='store_true',
                       help='train in the game window, drawing every character as it plays')
    train.add_argument('--seed', type=int, help='seed to train from; random, and printed, unless given')
    train.add_argument('--generations', type=int, default=DEFAULT_GENERATIONS,
                       help='give up after this many generations on one level (default: %(default)s)')
    defaults = {field.name: field.default for field in dataclasses.fields(evolve.Settings)}
    for name, (kind, help) in TRAINING_OPTIONS.items():
        if defaults[name] is not None:
            help = f'{help} (default: {defaults[name]})'
        train.add_argument(f'--{name.replace("_", "-")}', type=kind, help=help)
    args = parser.parse_args(argv)
    if args.command == 'train':
        if args.dev:
            parser.error('--dev is for playing the game, not for training')
        if not 1 <= args.generations <= sys.maxsize:
            train.error(f'--generations must be at least 1 and at most {sys.maxsize}')
        chosen = {name: getattr(args, name) for name in TRAINING_OPTIONS if getattr(args, name) is not None}
        try:
            args.settings = evolve.Settings(population=args.population, **chosen)
        except ValueError as problem:
            train.error(str(problem))
    return args


def train(args):
    '''Train on every level in turn as `args` says, in the window with `--watch`;
    whether every level was beaten.'''
    seed = random.randrange(2 ** 32) if args.seed is None else args.seed
    print(f'Training on all {len(levels.LEVELS)} levels in turn: '
          f'{args.settings.population} characters a generation, seed {seed}.')
    learn = watch.run if args.watch else evolve.train
    return learn(levels.LEVELS, args.settings, seed, args.generations).beaten


def main(argv=None) -> None:
    args = parse_args(argv)
    if args.command == 'train':
        if not train(args):
            raise SystemExit(1)
    else:
        engine.run(levels.LEVELS, dev=args.dev)
