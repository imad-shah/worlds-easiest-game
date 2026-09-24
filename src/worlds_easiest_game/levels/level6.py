'''Level 6: two long corridors joined at the right, guarded by synchronized crosses.'''

from worlds_easiest_game.obstacles import cross

PLAYER_SPAWN = (144, 103)

# Tile columns 0-18, with four-row corridors on rows -2..2 and 4..8. The
# two-row turn at the right joins them; the start and goal extend to the left.
PLAYFIELD = [
    (117, 76), (860, 76), (860, 489), (117, 489), (117, 406),
    (200, 406), (200, 324), (695, 324), (695, 241), (200, 241),
    (200, 159), (117, 159),
]

PATH_REGIONS = [
    ((200, 76), (860, 241)),   # upper corridor
    ((200, 324), (860, 489)),  # lower corridor
]

SAFE_REGIONS = [
    ((117, 76), (200, 159)),   # start
    ((695, 241), (860, 324)),  # turn
    ((117, 406), (200, 489)),  # goal
]

GOAL = SAFE_REGIONS[-1]

# Half a tile into the lower corridor, one and a half tiles left of each cross.
COINS = [(220, 345), (385, 345), (550, 345), (715, 345)]

# The centers fall every four columns on each corridor's middle grid line.
# Each cross has a hub and two dots on each arm. All share one phase and speed;
# at the starting phase the right arms tilt slightly upward, as in frame A.
CENTERS = [(x, y) for y in (159, 406) for x in (282, 447, 612, 777)]
OBSTACLES = [dot for center in CENTERS
             for dot in cross(center, arms=4, dots_per_arm=2, spacing=34,
                              speed=60, angle=-12)]

# How long a learning character gets on the level (see evolve). A perfect run
# takes about 20.8 seconds; this leaves room for waiting on the dots.
TIME_LIMIT = 50  # seconds
