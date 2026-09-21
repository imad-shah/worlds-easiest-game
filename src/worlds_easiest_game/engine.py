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
# and scaled to this canvas. Fractional because it is fitted to level 1's walls,
# which sit 18 tiles apart across the course and 6 tiles apart down it.
TILE_SIZE = 41.25
# As in the original, one board is fixed to the canvas for every level: its grid
# runs through this point (level 1's top-left corner), and the tile below-right
# of it is light.
GRID_ORIGIN = (117, 159)
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


def draw_checkerboard(surface, area):
    '''Fill `area` with its part of the floor board anchored at GRID_ORIGIN.

    Tile edges are rounded from the fractional grid, and the tile at GRID_ORIGIN
    is light, so every region of every level shares one continuous board.
    '''
    (ox, oy), size = GRID_ORIGIN, TILE_SIZE
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
    for corners in level.PATH_REGIONS:
        draw_checkerboard(surface, region_rect(*corners))
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


class Menu:
    '''The screen the game opens on: a start button, alone in the middle.'''

    def __init__(self):
        self.surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.surface.fill(BACKGROUND)
        self.start_button = pygame.Rect(0, 0, 220, 70)
        self.start_button.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
        pygame.draw.rect(self.surface, GREEN, self.start_button)
        pygame.draw.rect(self.surface, BLACK, self.start_button, WALL_THICKNESS)
        label = pygame.font.Font(None, 48).render('START', True, BLACK)
        self.surface.blit(label, label.get_rect(center=self.start_button.center))
        self.surface = self.surface.convert()

    def starts_game(self, event):
        '''Whether `event` is a left click on the start button.'''
        return (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                and self.start_button.collidepoint(event.pos))

    def update(self, dt, keys):
        pass

    def draw(self, screen):
        screen.blit(self.surface, (0, 0))


class Play:
    '''One level being played: the player, the obstacles, and what they do each frame.'''

    def __init__(self, level):
        self.level = level
        self.walls = build_walls(level.PLAYFIELD)
        self.level_surface = build_level_surface(level, self.walls)
        self.obstacle_sprite = build_obstacle_sprite()
        self.reset()

    def reset(self):
        '''Put the player back on its spawn and every obstacle back at its start.'''
        self.pos = pygame.Vector2(self.level.PLAYER_SPAWN)
        self.player = pygame.Rect(self.level.PLAYER_SPAWN, PLAYER_SIZE)
        self.dots = obstacles.spawn(self.level.OBSTACLES)

    def update(self, dt, keys):
        velocity = read_input(keys)
        move_player(self.pos, self.player, velocity.x * dt, velocity.y * dt, self.walls)
        for dot in self.dots:
            dot.update(dt)
        if any(dot.touches(self.player) for dot in self.dots):
            self.reset()

    def draw(self, screen):
        screen.blit(self.level_surface, (0, 0))
        pygame.draw.rect(screen, RED, self.player)
        pygame.draw.rect(screen, BLACK, self.player, 5)
        for dot in self.dots:
            draw_obstacle(screen, self.obstacle_sprite, dot)


class Game:
    '''The two states the game can be in: the menu it opens on, then the level.

    Only the current state is updated, so the level stands still, at its start,
    for however long the menu is up.
    '''

    def __init__(self, level):
        self.menu = Menu()
        self.play = Play(level)
        self.state = self.menu

    def handle(self, event):
        if self.state is self.menu and self.menu.starts_game(event):
            self.play.reset()
            self.state = self.play

    def update(self, dt, keys):
        self.state.update(dt, keys)

    def draw(self, screen):
        self.state.draw(screen)


def run(level):
    '''Open the game on its menu; starting from there plays `level`.'''
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    clock = pygame.time.Clock()
    game = Game(level)
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
            game.handle(event)

        keys = pygame.key.get_pressed()
        if keys[pygame.K_q]:
            running = False

        game.update(dt, keys)
        game.draw(screen)
        pygame.display.flip()

    pygame.quit()
