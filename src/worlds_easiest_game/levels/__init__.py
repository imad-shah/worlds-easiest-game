'''The level registry.

To add a level: write `levelN.py` next to this file, giving it the eight names
every level has (PLAYER_SPAWN, PLAYFIELD, PATH_REGIONS, SAFE_REGIONS, GOAL,
COINS, OBSTACLES, and TIME_LIMIT, the seconds a character learning to beat it
gets, at least twice what a perfect run takes; see `evolve`), plus INNER_WALLS
if walls stand inside its course, and CHECKPOINT if, once the player reaches
one of its safe zones, a death puts them back there. Then append it to LEVELS
below. Nothing in the engine or in the entry point has to change. Place the
level where the original has it on screen: every level shares one TILE_SIZE
checkerboard fixed to the canvas at the engine's GRID_ORIGIN, so a level's
position decides its tile colors, and the suite checks every corner lands on a
grid line.

The game plays LEVELS in order: collecting every coin and then reaching the
GOAL finishes a level, and finishing the last one shows the win screen.
'''

from worlds_easiest_game.levels import level1, level2, level3, level4, level5, level6, level7, level8, level9

# In play order.
LEVELS = [level1, level2, level3, level4, level5, level6, level7, level8, level9]
