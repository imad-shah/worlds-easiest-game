'''Level 4: a big cross of dots spinning in a round room, with a coin at three of its sides.'''

from worlds_easiest_game.obstacles import cross

PLAYER_SPAWN = (474, 127)

# The course outline, walked clockwise from the top-left corner of the start zone.
# It shares level 1's board: the room is tile columns 5 to 12 on rows 0 to 7,
# stepped round with rows 4, 6, 8, 8, 8, 8, 6 and 4 tiles wide, and centered
# across the canvas as the original centers it. The start zone is columns 8 and
# 9 on the three rows above the room, and the exit is columns 2 to 4 on the
# room's middle two rows, 3 and 4.
PLAYFIELD = [
    (447, 35), (530, 35), (530, 159), (571, 159), (571, 200), (612, 200),
    (612, 241), (653, 241), (653, 406), (612, 406), (612, 448), (571, 448),
    (571, 489), (406, 489), (406, 448), (364, 448), (364, 406), (323, 406),
    (323, 365), (200, 365), (200, 283), (323, 283), (323, 241), (364, 241),
    (364, 200), (406, 200), (406, 159), (447, 159),
]

PATH_REGIONS = [
    ((406, 159), (571, 200)),  # row 0
    ((364, 200), (612, 241)),  # row 1
    ((323, 241), (653, 406)),  # rows 2 to 5
    ((364, 406), (612, 448)),  # row 6
    ((406, 448), (571, 489)),  # row 7
]

SAFE_REGIONS = [
    ((447, 35), (530, 159)),  # the start zone, above the room
    ((200, 283), (323, 365)),  # the exit, left of the room
]

# Reaching this safe zone with every coin collected finishes the level.
GOAL = ((200, 283), (323, 365))  # the exit

# Centers of the coins to collect: three tiles above, right of and below the
# middle of the room, each on a grid line, as in the original.
CENTER = (488, 324)
COINS = [(488, 200), (612, 324), (488, 448)]

# The cross, as in the original's frame: four arms of five dots about 0.7 of a
# tile apart around a center dot, the tips reaching over the room's stepped
# corners, and the first arm 37 degrees clockwise from pointing right.
# One turn every six seconds moves the tips at about 150px/s, level 3's speed.
OBSTACLES = cross(CENTER, arms=4, dots_per_arm=5, spacing=29, speed=60, angle=37)

# How long a learning character gets on the level (see evolve). A perfect run
# takes about 4.0 seconds; this leaves room for waiting on the dots.
TIME_LIMIT = 15  # seconds
