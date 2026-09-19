'''The level registry.

To add a level: write `levelN.py` next to this file, giving it the same four
names level 1 has (PLAYER_SPAWN, PLAYFIELD, PATH_REGIONS, SAFE_REGIONS), then
append it to LEVELS below. Nothing in the engine or in the entry point has to
change. Until level progression exists, only LEVELS[0] is ever played.
'''

from worlds_easiest_game.levels import level1

# In play order.
LEVELS = [level1]


def current_level():
    '''The level to play right now -- the first one, until there is progression.'''
    return LEVELS[0]
