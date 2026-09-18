'''The level registry.

To add a level: write `levelN.py` next to this file, giving it the same four
names level 1 has (PLAYER_SPAWN, PLAYFIELD, PATH_REGIONS, SAFE_REGIONS), then
append it to LEVELS below. Nothing in the engine or in main.py has to change.
'''

from levels import level1

# In play order.
LEVELS = [level1]


def current_level():
    '''The level to play right now -- the first one, until there is progression.'''
    return LEVELS[0]
