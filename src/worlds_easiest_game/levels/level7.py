'''Level 7: level 2's room two rows taller, with a coin in each corner.'''

from worlds_easiest_game.obstacles import vertical

PLAYER_SPAWN = (144, 268)

# The course outline, walked clockwise from the top-left corner of the left safe
# zone. It shares level 1's board: the room is level 2's tile columns 3 to 14,
# grown by a row above and below to rows -1 to 6 and so centered down the canvas
# as the original centers it, its top-left tile light. The safe zones are level
# 2's, three columns wide on the room's middle two rows, 2 and 3.
PLAYFIELD = [
    (117, 241), (240, 241), (240, 118), (735, 118), (735, 241), (860, 241),
    (860, 324), (735, 324), (735, 448), (240, 448), (240, 324), (117, 324),
]

PATH_REGIONS = [
    ((240, 118), (735, 448)),  # the room
]

# Painted over the path, so the openings into the room stay green.
SAFE_REGIONS = [
    ((117, 241), (240, 324)),  # left, where the player starts
    ((735, 241), (860, 324)),  # right
]

# Reaching this safe zone with every coin collected finishes the level.
GOAL = ((735, 241), (860, 324))  # the right zone

# Centers of the coins to collect: the middle of each of the room's corner tiles,
# anticlockwise from the top-left one.
COINS = [(261, 138), (261, 427), (715, 427), (715, 138)]

# Level 2's dots, one per tile column of the room, each in the middle of its
# column and running to the same 26px short of the far wall, at the same speed.
# Here the odd columns start near the top wall and the even ones near the bottom,
# so, as in the original's frame, the room's first column is the higher one just
# as the two rows pass each other in the middle of the room.
TOP_COLUMNS = (261, 344, 426, 509, 591, 674)  # tile columns 3, 5, ... 13
BOTTOM_COLUMNS = (303, 385, 468, 550, 633, 715)  # tile columns 4, 6, ... 14

OBSTACLES = [
    *(vertical(x=x, from_y=144, to_y=422, speed=300) for x in TOP_COLUMNS),
    *(vertical(x=x, from_y=422, to_y=144, speed=300) for x in BOTTOM_COLUMNS),
]

# How long a learning character gets on the level (see evolve). A perfect run
# takes about 5.6 seconds; this leaves room for waiting on the dots.
TIME_LIMIT = 20  # seconds
