import math

import pygame

from worlds_easiest_game import obstacles


# constants
SCREEN_WIDTH = 981
SCREEN_HEIGHT = 574
FPS = 120
PLAYER_SPEED = 240  # pixels per second
PLAYER_SIZE = (29, 29)
WALL_THICKNESS = 6
OBSTACLE_OUTLINE = 4.5  # of obstacles.RADIUS, measured from the original game
# The floor tiles, measured off the original's screenshots (about 43.4px there)
# and scaled to this canvas. Fractional because it is fitted to level 1's walls, which sit 18
# tiles apart across the course and 6 tiles apart down it.
TILE_SIZE = 41.25
DEBUG = False  # click anywhere to print coordinates, for laying out new levels

# colors
BACKGROUND = '#aaa5ff'
RED = '#ff0000'
BLACK = '#000000'
GREEN = '#9ef29b'
WHITE = '#FFFFFF'
BLUE = '#0000FF'
TILE_LIGHT = '#f7f7ff'  # the two floor tiles, sampled from the original
TILE_DARK = '#e6e6fd'


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


def grid_origin(polygon):
    '''The point the floor grid is anchored to: the course's top-left bounding corner.

    The original lays every wall on its tile grid, so anchoring there lines the
    tiles up with all of a level's walls without the level saying anything more.
    '''
    return min(x for x, _ in polygon), min(y for _, y in polygon)


def draw_checkerboard(surface, area, origin, size=TILE_SIZE):
    '''Fill `area` with alternating tiles from the grid whose corner sits at `origin`.

    Tile edges are rounded from the fractional grid, and the tile at `origin` is
    light, so every region of a level shares one continuous board.
    '''
    ox, oy = origin
    cols = range(math.floor((area.left - ox) / size), math.ceil((area.right - ox) / size))
    rows = range(math.floor((area.top - oy) / size), math.ceil((area.bottom - oy) / size))
    for col in cols:
        left, right = round(ox + col * size), round(ox + (col + 1) * size)
        for row in rows:
            top, bottom = round(oy + row * size), round(oy + (row + 1) * size)
            color = TILE_LIGHT if (col + row) % 2 == 0 else TILE_DARK
            tile = pygame.Rect(left, top, right - left, bottom - top)
            pygame.draw.rect(surface, color, tile.clip(area))


def build_level_surface(level, walls):
    '''Draw the static parts of the level once, so the loop only has to blit it.'''
    surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    surface.fill(BACKGROUND)
    origin = grid_origin(level.PLAYFIELD)
    for corners in level.PATH_REGIONS:
        draw_checkerboard(surface, region_rect(*corners), origin)
    for corners in level.SAFE_REGIONS:
        pygame.draw.rect(surface, GREEN, region_rect(*corners))
    for wall in walls:
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


def build_obstacle_sprite(supersample=4):
    '''A blue dot with a black outline, drawn once for every obstacle to share.

    It is drawn `supersample` times too big and shrunk down, which smooths its
    edges; pygame draws small circles straight onto the pixel grid as octagons.
    '''
    diameter = obstacles.RADIUS * 2
    big = pygame.Surface((diameter * supersample,) * 2, pygame.SRCALPHA)
    center = big.get_rect().center
    pygame.draw.circle(big, BLACK, center, obstacles.RADIUS * supersample)
    pygame.draw.circle(big, BLUE, center,
                       (obstacles.RADIUS - OBSTACLE_OUTLINE) * supersample)
    return pygame.transform.smoothscale(big, (diameter, diameter)).convert_alpha()


def draw_obstacle(surface, sprite, obstacle):
    '''Blit the obstacle sprite centered on where the obstacle is now.'''
    x, y = obstacle.center
    surface.blit(sprite, sprite.get_rect(center=(round(x), round(y))))


def build_contact_notice():
    '''The notice shown in the top right while the player touches an obstacle.

    A stand-in so contact can be seen working, until touching one resets the level.
    '''
    text = pygame.font.Font(None, 26).render('In contact with an obstacle', True, WHITE)
    notice = pygame.Surface((text.get_width() + 20, text.get_height() + 12))
    notice.fill(BLACK)
    notice.blit(text, (10, 6))
    return notice


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


def run(level):
    '''Play one level: everything here is the same whichever level is handed in.'''
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    clock = pygame.time.Clock()
    walls = build_walls(level.PLAYFIELD)
    level_surface = build_level_surface(level, walls)
    obstacle_sprite = build_obstacle_sprite()
    contact_notice = build_contact_notice()
    contact_notice_pos = contact_notice.get_rect(topright=(SCREEN_WIDTH - 10, 10))
    dots = obstacles.spawn(level.OBSTACLES)

    pos = pygame.Vector2(level.PLAYER_SPAWN)
    player = pygame.Rect(level.PLAYER_SPAWN, PLAYER_SIZE)
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
        move_player(pos, player, velocity.x * dt, velocity.y * dt, walls)
        for dot in dots:
            dot.update(dt)

        screen.blit(level_surface, (0, 0))
        pygame.draw.rect(screen, RED, player)
        pygame.draw.rect(screen, BLACK, player, 5)
        for dot in dots:
            draw_obstacle(screen, obstacle_sprite, dot)
        if any(dot.touches(player) for dot in dots):
            screen.blit(contact_notice, contact_notice_pos)

        pygame.display.flip()

    pygame.quit()
