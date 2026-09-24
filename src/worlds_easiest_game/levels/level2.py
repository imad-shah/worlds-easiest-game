'''Level 2: a wide room between two safe zones, with dots crossing it up and down.'''

from worlds_easiest_game.obstacles import vertical

PLAYER_SPAWN = (144, 268)

# The course outline, walked clockwise from the top-left corner of the left safe
# zone. It shares level 1's board: the room runs from tile column 3 to 15 and
# the full six rows, and each safe zone is three columns wide on rows 2 and 3.
PLAYFIELD = [
    (117, 241), (240, 241), (240, 159), (735, 159), (735, 241), (860, 241),
    (860, 324), (735, 324), (735, 406), (240, 406), (240, 324), (117, 324),
]

PATH_REGIONS = [
    ((240, 159), (735, 406)),  # the room
]

# Painted over the path, so the openings into the room stay green.
SAFE_REGIONS = [
    ((117, 241), (240, 324)),  # left, where the player starts
    ((735, 241), (860, 324)),  # right
]

# Reaching this safe zone with every coin collected finishes the level.
GOAL = ((735, 241), (860, 324))  # the right zone

# Centers of the coins to collect. The one coin sits in the middle of the room.
COINS = [(488, 283)]

# One dot per tile column of the room, each in the middle of its column. Dots in
# the even columns start near the top wall and those in the odd columns near the
# bottom one, and each runs to the same 26px short of the far wall, as in the
# original. Moving in step, the two rows pass each other in the middle of the room.
TOP_COLUMNS = (303, 385, 468, 550, 633, 715)  # tile columns 4, 6, ... 14
BOTTOM_COLUMNS = (261, 344, 426, 509, 591, 674)  # tile columns 3, 5, ... 13

OBSTACLES = [
    *(vertical(x=x, from_y=185, to_y=380, speed=300) for x in TOP_COLUMNS),
    *(vertical(x=x, from_y=380, to_y=185, speed=300) for x in BOTTOM_COLUMNS),
]

# How long a learning character gets on the level (see evolve). A perfect run
# takes about 2.7 seconds; this leaves room for waiting on the dots.
TIME_LIMIT = 15  # seconds
