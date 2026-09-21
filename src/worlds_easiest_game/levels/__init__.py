'''The level registry.

To add a level: write `levelN.py` next to this file, giving it the same five
names level 1 has (PLAYER_SPAWN, PLAYFIELD, PATH_REGIONS, SAFE_REGIONS,
OBSTACLES), then append it to LEVELS below. Nothing in the engine or in the
entry point has to change. Place the level where the original has it on screen: every level shares
one TILE_SIZE checkerboard fixed to the canvas at the engine's GRID_ORIGIN, so a
level's position decides its tile colors, and the suite checks every corner
lands on a grid line. Until level progression exists, only LEVELS[0] is ever
played.
'''

from worlds_easiest_game.levels import level1

# In play order.
LEVELS = [level1]


def current_level():
    '''The level to play right now -- the first one, until there is progression.'''
    return LEVELS[0]
