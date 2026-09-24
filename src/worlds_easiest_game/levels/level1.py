'''Level 1: the course the game has always shipped with.'''

from worlds_easiest_game.obstacles import horizontal

PLAYER_SPAWN = (166, 271)

# The course outline: one closed, axis-aligned polygon walked clockwise from the
# top-left corner. This is the single source of truth -- the walls you collide
# with and the walls you see are both derived from it.
PLAYFIELD = [
    (117, 159), (240, 159), (240, 366), (281, 366), (281, 199), (654, 199),
    (654, 160), (860, 160), (860, 406), (735, 406), (735, 200), (695, 200),
    (695, 365), (322, 365), (322, 406), (117, 406),
]

# The floor, given as (top-left, bottom-right) corner pairs taken straight from
# PLAYFIELD coordinates. Running them out to the wall centerlines means the
# walls, drawn last, cover their edges and no background shows through a seam.
# Together these six regions tile the whole inside of the course.
PATH_REGIONS = [
    ((281, 199), (695, 365)),  # the middle corridor
    ((117, 366), (322, 406)),  # bottom-left passage out of the left room
    ((281, 365), (322, 406)),  # the step up from that passage into the corridor
    ((654, 160), (860, 199)),  # top-right passage into the right room
]

# Painted over the path, so green wins where a room and a passage overlap.
SAFE_REGIONS = [
    ((117, 159), (240, 406)),  # left room
    ((735, 160), (860, 406)),  # right room
]

# Reaching this safe zone with every coin collected finishes the level.
GOAL = ((735, 160), (860, 406))  # the right room

COINS = []

# One dot per row of the middle corridor, which is 166px tall between its walls
# at y=199 and y=365, so each row is a quarter of that. Every dot runs the full
# corridor, from touching the inside of the wall at x=281 to touching the wall
# at x=695. Neighbouring rows start at opposite ends, so they pass each other.
OBSTACLES = [
    horizontal(y=220, from_x=295, to_x=681, speed=300),
    horizontal(y=261, from_x=295, to_x=681, speed=300, start=0.5),
    horizontal(y=303, from_x=295, to_x=681, speed=300),
    horizontal(y=344, from_x=295, to_x=681, speed=300, start=0.5),
]

# How long a learning character gets on the level (see evolve). A perfect run
# takes about 3.3 seconds; this leaves room for waiting on the dots.
TIME_LIMIT = 15  # seconds
