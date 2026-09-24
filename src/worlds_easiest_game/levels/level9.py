'''Level 9: a loop of corridor round a wall island, a checkpoint, then a coin down a dead end.'''

from worlds_easiest_game.obstacles import loop, still

PLAYER_SPAWN = (144, 103)

# The course outline, walked clockwise from its top-left corner. It shares level
# 1's board and level 6's footprint, tile columns 0 to 17 on rows -2 to 7, and
# every corridor in it is two tiles wide. The left part runs from the start down
# columns 0-1 and round the island below to the checkpoint on columns 8-9, rows
# 4-5. A corridor on those rows leads right to columns 12-13, which run the
# full height, with a bar right along rows -2 to -1 and another along rows 6-7.
# An arm drops from the top bar's end down columns 16-17 to the goal on rows 2-3.
PLAYFIELD = [
    (117, 76), (200, 76), (200, 159), (282, 159), (282, 76), (530, 76),
    (530, 324), (612, 324), (612, 76), (860, 76), (860, 324), (777, 324),
    (777, 159), (695, 159), (695, 406), (860, 406), (860, 489), (612, 489),
    (612, 406), (364, 406), (364, 489), (117, 489),
]

# The island the left part's corridor loops round: columns 2-3 on rows 2 to 5,
# columns 4-5 on rows 2-3, and columns 6-7 on rows 0 to 3.
INNER_WALLS = [
    [(200, 242), (364, 242), (364, 159), (447, 159), (447, 324), (282, 324),
     (282, 406), (200, 406)],
]

PATH_REGIONS = [
    ((117, 159), (200, 489)),  # down the left edge from the start
    ((200, 159), (364, 242)),  # the upper route: right above the island,
    ((282, 76), (530, 159)),   # up and right along the top,
    ((447, 159), (530, 324)),  # and down to the checkpoint
    ((200, 406), (364, 489)),  # the lower route: right below the island,
    ((282, 324), (447, 406)),  # and up and right to the checkpoint
    ((530, 324), (612, 406)),  # from the checkpoint to the right part
    ((612, 76), (695, 489)),   # the full-height column
    ((695, 76), (860, 159)),   # the top bar
    ((777, 159), (860, 242)),  # the arm down to the goal
    ((695, 406), (860, 489)),  # the bottom bar, a dead end
]

SAFE_REGIONS = [
    ((117, 76), (200, 159)),   # where the player starts
    ((447, 324), (530, 406)),  # the checkpoint, where the two routes meet
    ((777, 242), (860, 324)),  # the goal, at the foot of the arm
]

# Once reached, a death puts the player back here instead of at the start.
CHECKPOINT = SAFE_REGIONS[1]

# Reaching this safe zone with every coin collected finishes the level.
GOAL = SAFE_REGIONS[2]

# The one coin, where the bottom bar's last four tiles meet.
COINS = [(818, 448)]

# Fifteen dots never move, measured off the original's frames.
STILL = [
    (138, 365), (178, 281), (240, 180), (240, 428), (301, 116), (301, 364),
    (364, 345), (404, 139), (425, 385), (467, 197), (633, 450), (633, 284),
    (673, 202), (736, 139), (800, 202),
]

# Eight dots circle two-by-two blocks of tiles clockwise, through the middles of
# the block's four tiles, a loop one tile on a side; each is listed by the
# top-left of its loop. Three of them run half a lap apart from the other five,
# and as in the frame where the player is at the start, the five are 94px round
# from that corner, along its top, down its right side and part way back along
# its bottom.
SIDE = 41  # px, a tile rounded to a whole pixel, so every loop has one length
BLOCKS = [(303, 180), (468, 97), (138, 427), (303, 427), (798, 97)]
HALF_LAP_BLOCKS = [(138, 180), (633, 97), (633, 345)]
BLOCK_START = 94 / (4 * SIDE)

# Two more dots go back and forth along an L with a short leg three quarters of
# a tile long and a long one two and a quarter, each listed from the end of its
# short leg, where it starts, by the corner, to the end of its long leg: one
# above the checkpoint, right and then up the right side of its corridor, and
# one left of the coin, up and then left along the top of the bottom bar.
L_SHAPES = [
    [(477, 303), (508, 303), (508, 210)],
    [(779, 456), (779, 425), (686, 425)],
]

# Every moving dot goes at level 8's pace, which puts them all within 3px of
# where the original's other three frames show them, 8.7, 14.75 and 16.5 seconds
# after the start.
SPEED = 150


def clockwise(topleft, side):
    '''The corners of a square, clockwise on screen from its top-left one.'''
    x, y = topleft
    return [(x, y), (x + side, y), (x + side, y + side), (x, y + side)]


OBSTACLES = [
    *(still(x, y) for x, y in STILL),
    *(loop(clockwise(corner, SIDE), SPEED, BLOCK_START) for corner in BLOCKS),
    *(loop(clockwise(corner, SIDE), SPEED, BLOCK_START - 0.5) for corner in HALF_LAP_BLOCKS),
    # Out along both legs and straight back: the route turns at the far end and
    # at the corner again on the way back.
    *(loop([start, corner, end, corner], SPEED) for start, corner, end in L_SHAPES),
]

# How long a learning character gets on the level (see evolve). A perfect run
# takes about 8.5 seconds; this leaves room for waiting on the dots.
TIME_LIMIT = 25  # seconds
