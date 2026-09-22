'''World's Easiest Game -- a recreation of "World's Hardest Game".

`main` is what the `worlds-easiest-game` console script runs; `game/main.py`
calls the same function.
'''

import argparse

from worlds_easiest_game import engine, levels


def parse_args(argv=None):
    '''The command line: `--dev` turns on developer-only keys (T toggles god mode).'''
    parser = argparse.ArgumentParser(prog='worlds-easiest-game')
    parser.add_argument('--dev', action='store_true',
                        help='developer mode: press T in a level to toggle god mode')
    return parser.parse_args(argv)


def main(argv=None) -> None:
    engine.run(levels.LEVELS, dev=parse_args(argv).dev)
