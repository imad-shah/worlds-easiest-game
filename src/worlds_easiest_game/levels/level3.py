'''Level 3: a ring of dots turning around a safe zone, with one gap to slip out through.'''

from worlds_easiest_game.obstacles import loop

PLAYER_SPAWN = (474, 268)

# The course outline, walked clockwise from the top-left corner of the extra
# tile the coin sits in. It shares level 1's board, 7 tiles to its right: the
# course is tile columns 7 to 10 on rows 1 to 4, and the extra tile is column 7
# on row 0.
PLAYFIELD = [
    (406, 159), (447, 159), (447, 200), (571, 200), (571, 365), (406, 365),
]

PATH_REGIONS = [
    ((406, 159), (447, 200)),  # the extra tile, above the top-left corner
    ((406, 200), (571, 365)),  # the course
]

# Painted over the path: the two-by-two tiles in the middle of the course.
SAFE_REGIONS = [
    ((447, 241), (530, 324)),  # where the player starts
]

# Reaching this safe zone with every coin collected finishes the level. It is
# the one the player starts in, so the level is out to the coin and back.
GOAL = ((447, 241), (530, 324))

# Centers of the coins to collect. The one coin sits in the middle of the extra tile.
COINS = [(427, 180)]

# The ring: the middle of each of the twelve tiles around the safe zone, walked
# clockwise from the top-left one. Twelve dots spaced a tile apart would fill it;
# one slot is left empty, so the gap turns around the safe zone with the dots.
# Every dot starts three quarters of a tile past its slot, as in the original's
# frames, with the gap in the middle of the top row.
RING = [(427, 221), (550, 221), (550, 344), (427, 344)]
SLOTS = 12
GAP = 1  # the empty slot, counted clockwise from the top-left corner

OBSTACLES = [
    loop(RING, speed=150, start=(slot + 0.75) / SLOTS)
    for slot in range(SLOTS) if slot != GAP
]
