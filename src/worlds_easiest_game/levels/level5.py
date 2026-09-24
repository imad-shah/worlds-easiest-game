'''Level 5: a spiral of corridors to the middle, under a cross of dots with gaps to slip through.'''

from worlds_easiest_game.obstacles import cross

PLAYER_SPAWN = (160, 83)

# The course outline, walked clockwise from the top-left corner of the start zone.
# It shares level 1's board: the spiral is tile columns 0 to 16 on rows -2 to 7,
# its corridors one tile wide with a one-tile strip of empty space between them.
# From the top corridor it runs down column 15, left along row 7, up column 2
# into row 0, right, down column 13, left along row 5, up column 4 and right
# along rows 2 and 3 to the goal, with column 5 of row 3 walled off.
PLAYFIELD = [
    (117, 76), (818, 76), (818, 118), (777, 118), (777, 489), (200, 489),
    (200, 200), (117, 200), (117, 159), (694, 159), (694, 406), (282, 406),
    (282, 242), (612, 242), (612, 324), (364, 324), (364, 283), (323, 283),
    (323, 365), (653, 365), (653, 200), (241, 200), (241, 448), (736, 448),
    (736, 118), (117, 118),
]

PATH_REGIONS = [
    ((117, 76), (818, 118)),  # the top corridor, row -2
    ((736, 118), (777, 489)),  # down column 15
    ((200, 448), (777, 489)),  # the bottom corridor, row 7
    ((200, 159), (241, 489)),  # up column 2
    ((117, 159), (694, 200)),  # the second corridor, row 0
    ((653, 200), (694, 406)),  # down column 13
    ((282, 365), (694, 406)),  # row 5
    ((282, 242), (323, 406)),  # up column 4
    ((282, 242), (612, 283)),  # row 2
    ((364, 283), (612, 324)),  # row 3, past the walled-off tile
]

# Painted over the path: the start zone, the two pockets where the spiral turns
# back on itself, and the goal in the middle.
SAFE_REGIONS = [
    ((117, 76), (200, 118)),  # where the player starts, the top corridor's left end
    ((777, 76), (818, 118)),  # the top corridor's right end
    ((117, 159), (158, 200)),  # the second corridor's left end
    ((571, 242), (612, 324)),  # the goal
]

# Reaching this safe zone with every coin collected finishes the level.
GOAL = ((571, 242), (612, 324))  # the middle of the spiral

COINS = []

# The cross, as in the original's frames: four arms of four dots and no dot on
# the center, which is the grid point at column line 9 and row line 3. The dots
# sit 1.5, 3.5, 5.5 and 7.5 tiles out, two tiles apart, which leaves a gap the
# player fits through between each pair, and the tips sweep past the course's
# edges. The first arm starts 19.5 degrees anticlockwise from pointing right, as
# in the frame where the player is still at the start. It turns at level 4's
# pace, one turn every six seconds, which fits how far the cross turns between
# the original's frames while the player walks between them.
CENTER = (488, 283)
OBSTACLES = cross(CENTER, arms=4, dots_per_arm=4, spacing=82.5, inner=62, speed=60,
                  angle=-19.5, center_dot=False)

# How long a learning character gets on the level (see evolve). A perfect run
# takes about 14.1 seconds; this leaves room for waiting on the dots.
TIME_LIMIT = 35  # seconds
