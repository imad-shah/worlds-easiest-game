import pygame

'''
TODO:
1. draw the checkerboard onto LEVEL_SURFACE (it is already pre-rendered once)
2. add enemies + the blue dots
'''


# constants
SCREEN_WIDTH = 981
SCREEN_HEIGHT = 574
FPS = 120
PLAYER_SPEED = 240  # pixels per second
PLAYER_SIZE = (29, 29)
PLAYER_SPAWN = (166, 271)
WALL_THICKNESS = 6
DEBUG = False  # click anywhere to print coordinates, for laying out new levels

# colors
BACKGROUND = '#aaa5ff'
RED = '#ff0000'
BLACK = '#000000'
GREEN = '#9ef29b'
WHITE = '#FFFFFF'

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


def region_rect(topleft, bottomright):
    '''Rect spanning two polygon corners, inclusive of both.'''
    left, top = topleft
    right, bottom = bottomright
    return pygame.Rect(left, top, (right - left) + 1, (bottom - top) + 1)


def build_walls(polygon, thickness=WALL_THICKNESS):
    '''Turn each polygon edge into a solid Rect centered on that edge.

    The half-thickness overhang on every side is what fills in the corners
    where a horizontal and a vertical edge meet.
    '''
    half = thickness // 2
    walls = []
    for start, end in zip(polygon, polygon[1:] + polygon[:1]):
        left, right = sorted((start[0], end[0]))
        top, bottom = sorted((start[1], end[1]))
        walls.append(pygame.Rect(left - half, top - half,
                                 (right - left) + thickness,
                                 (bottom - top) + thickness))
    return walls


WALLS = build_walls(PLAYFIELD)


def build_level_surface():
    '''Draw the static parts of the level once, so the loop only has to blit it.'''
    surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    surface.fill(BACKGROUND)
    for corners in PATH_REGIONS:
        pygame.draw.rect(surface, WHITE, region_rect(*corners))
    for corners in SAFE_REGIONS:
        pygame.draw.rect(surface, GREEN, region_rect(*corners))
    for wall in WALLS:
        pygame.draw.rect(surface, BLACK, wall)
    return surface.convert()


def move_player(pos, player, dx, dy, walls):
    '''Move one axis at a time so the player slides along a wall instead of sticking.

    `pos` is the float position (Vector2) that survives between frames; `player`
    is the integer Rect used for collision and drawing. On a hit the Rect is
    snapped flush against the wall and the float position is resynced to match.
    '''
    if dx:
        pos.x += dx
        player.x = round(pos.x)
        hit = False
        for wall in walls:
            if player.colliderect(wall):
                hit = True
                if dx > 0:
                    player.right = min(player.right, wall.left)
                else:
                    player.left = max(player.left, wall.right)
        if hit:
            pos.x = player.x

    if dy:
        pos.y += dy
        player.y = round(pos.y)
        hit = False
        for wall in walls:
            if player.colliderect(wall):
                hit = True
                if dy > 0:
                    player.bottom = min(player.bottom, wall.top)
                else:
                    player.top = max(player.top, wall.bottom)
        if hit:
            pos.y = player.y


def read_input(keys):
    '''Return a velocity vector of length PLAYER_SPEED, so diagonals aren't faster.'''
    direction = pygame.Vector2(0, 0)
    if keys[pygame.K_w]:
        direction.y -= 1
    if keys[pygame.K_s]:
        direction.y += 1
    if keys[pygame.K_a]:
        direction.x -= 1
    if keys[pygame.K_d]:
        direction.x += 1
    if direction.length_squared() == 0:
        return direction
    return direction.normalize() * PLAYER_SPEED


def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    clock = pygame.time.Clock()
    level_surface = build_level_surface()

    pos = pygame.Vector2(PLAYER_SPAWN)
    player = pygame.Rect(PLAYER_SPAWN, PLAYER_SIZE)
    running = True
    coords = []

    while running:
        dt = clock.tick(FPS) / 1000

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and DEBUG:
                coords.append(pygame.mouse.get_pos())
                print(coords)

        keys = pygame.key.get_pressed()
        if keys[pygame.K_q]:
            running = False

        velocity = read_input(keys)
        move_player(pos, player, velocity.x * dt, velocity.y * dt, WALLS)

        screen.blit(level_surface, (0, 0))
        pygame.draw.rect(screen, RED, player)
        pygame.draw.rect(screen, BLACK, player, 5)

        pygame.display.flip()

    pygame.quit()


if __name__ == '__main__':
    main()
