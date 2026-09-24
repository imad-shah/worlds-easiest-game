'''Level 8: two blocks of corridors around wall squares, joined top and bottom, with dots circling every wall.'''

from worlds_easiest_game.obstacles import loop

PLAYER_SPAWN = (288, 124)

# The course outline, walked clockwise from its top-left corner. It shares level
# 1's board: the course is tile columns 3 to 12 on rows -2 to 7, centered with
# its goal across the canvas as the original centers them. A block four columns
# wide stands on each side, 3 to 6 and 9 to 12, joined by one-row corridors
# across columns 7 and 8 on rows -1 and 6. The goal sticks out of the right
# block's outer wall, columns 13 and 14 on rows 2 and 3.
PLAYFIELD = [
    (241, 76), (406, 76), (406, 118), (488, 118), (488, 76), (653, 76),
    (653, 242), (736, 242), (736, 324), (653, 324), (653, 489), (488, 489),
    (488, 448), (406, 448), (406, 489), (241, 489),
]

# The walls standing inside the course: in each block, three two-by-two squares
# stacked in its middle two columns, with a one-row corridor between each; and
# the wall between the blocks, columns 7 and 8 on rows 0 to 5. The top-left
# square has its top-left tile cut out for the player to start in.
INNER_WALLS = [
    [(323, 118), (364, 118), (364, 200), (282, 200), (282, 159), (323, 159)],
    [(282, 242), (364, 242), (364, 324), (282, 324)],
    [(282, 365), (364, 365), (364, 448), (282, 448)],
    [(406, 159), (488, 159), (488, 406), (406, 406)],
    [(530, 118), (612, 118), (612, 200), (530, 200)],
    [(530, 242), (612, 242), (612, 324), (530, 324)],
    [(530, 365), (612, 365), (612, 448), (530, 448)],
]

# The corridors around the squares: each block's outer and inner columns and
# the four rows across it, plus the two corridors joining the blocks.
PATH_REGIONS = [
    ((241, 76), (282, 489)),  # the left block's outer column
    ((364, 76), (406, 489)),  # its inner column
    ((612, 76), (653, 489)),  # the right block's outer column
    ((488, 76), (530, 489)),  # its inner column
    *(((left, top), (right, bottom))  # the four rows across each block
      for left, right in ((241, 406), (488, 653))
      for top, bottom in ((76, 118), (200, 242), (324, 365), (448, 489))),
    ((406, 118), (488, 159)),  # the top corridor joining the blocks
    ((406, 406), (488, 448)),  # the bottom one
]

SAFE_REGIONS = [
    ((282, 118), (323, 159)),  # where the player starts, cut into the top-left square
    ((653, 242), (736, 324)),  # the goal, right of the right block
]

# Reaching this safe zone with every coin collected finishes the level.
GOAL = ((653, 242), (736, 324))

# Centers of the coins to collect: the bottom-left, top-right and bottom-right
# corner tiles of the course.
COINS = [(261, 468), (633, 97), (633, 468)]

# Every side dot circles one square along the middles of the corridors around
# it, a loop three tiles on a side. The left three go clockwise from their
# loop's top-left corner and the right three anticlockwise from its top-right,
# so the right block mirrors the left, and all six start 53px along the top as
# in the original's frame where the player is at the start.
LOOP = 124  # px, three tiles rounded to a whole pixel, so every loop has one length
LEFT, RIGHT = 261, 633  # the middle of each block's outer column
INNER_LEFT, INNER_RIGHT = LEFT + LOOP, RIGHT - LOOP  # the middle of each inner column
TOPS = (97, 221, 345)  # the middle of the row above each square
SIDE_START = 53 / (4 * LOOP)

# The middle dot circles the wall between the blocks clockwise, along both
# inner columns and the joining corridors, starting 150px up the left inner
# column as in that same frame. It goes a little faster than the side dots,
# 158px/s to their 150 (level 3's pace), which puts every dot where the
# original's other two frames show them, 9 and 9.6 seconds after the start.
MIDDLE = [(INNER_LEFT, 427), (INNER_LEFT, 138), (INNER_RIGHT, 138), (INNER_RIGHT, 427)]
MIDDLE_START = 150 / (2 * (LOOP + 427 - 138))

OBSTACLES = [
    *(loop([(LEFT, top), (INNER_LEFT, top), (INNER_LEFT, top + LOOP), (LEFT, top + LOOP)],
           speed=150, start=SIDE_START) for top in TOPS),
    *(loop([(RIGHT, top), (INNER_RIGHT, top), (INNER_RIGHT, top + LOOP), (RIGHT, top + LOOP)],
           speed=150, start=SIDE_START) for top in TOPS),
    loop(MIDDLE, speed=158, start=MIDDLE_START),
]

# How long a learning character gets on the level (see evolve). A perfect run
# takes about 9.2 seconds; this leaves room for waiting on the dots.
TIME_LIMIT = 25  # seconds
