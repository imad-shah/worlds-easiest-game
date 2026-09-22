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
# Coins are the same size as the dots in the original, and outlined the same way.
COIN_RADIUS = obstacles.RADIUS
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
BLUE = '#0000FF'
YELLOW = '#ffff55'  # sampled from the original's coins
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


def build_dot_sprite(fill, radius, supersample=4):
    '''A `fill`-colored dot with a black outline, drawn once for every dot to share.

    It is drawn `supersample` times too big and shrunk down, which smooths its
    edges; pygame draws small circles straight onto the pixel grid as octagons.
    '''
    diameter = radius * 2
    big = pygame.Surface((diameter * supersample,) * 2, pygame.SRCALPHA)
    center = big.get_rect().center
    pygame.draw.circle(big, BLACK, center, radius * supersample)
    pygame.draw.circle(big, fill, center, (radius - OBSTACLE_OUTLINE) * supersample)
    return pygame.transform.smoothscale(big, (diameter, diameter)).convert_alpha()


def build_obstacle_sprite():
    '''The blue dot every obstacle is drawn with.'''
    return build_dot_sprite(BLUE, obstacles.RADIUS)


def build_coin_sprite():
    '''The yellow dot every coin is drawn with.'''
    return build_dot_sprite(YELLOW, COIN_RADIUS)


def draw_centered(surface, sprite, center):
    '''Blit `sprite` centered on `center`, rounded to the nearest pixel.'''
    x, y = center
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


class Screen:
    '''A full-screen card shown outside a level: a title over a row of buttons.

    `clicked` names the button a left click lands on, so the game decides what
    each one does.
    '''

    BUTTON_SIZE = (220, 70)
    BUTTON_GAP = 40

    def __init__(self, title, labels):
        self.surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.surface.fill(BACKGROUND)
        title = pygame.font.Font(None, 84).render(title, True, BLACK)
        self.surface.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 217)))

        width, height = self.BUTTON_SIZE
        row = len(labels) * width + (len(labels) - 1) * self.BUTTON_GAP
        left = (SCREEN_WIDTH - row) // 2
        font = pygame.font.Font(None, 48)
        self.buttons = {}
        for i, label in enumerate(labels):
            button = pygame.Rect(left + i * (width + self.BUTTON_GAP), 0, width, height)
            button.centery = 347
            pygame.draw.rect(self.surface, GREEN, button)
            pygame.draw.rect(self.surface, BLACK, button, WALL_THICKNESS)
            text = font.render(label, True, BLACK)
            self.surface.blit(text, text.get_rect(center=button.center))
            self.buttons[label] = button
        self.surface = self.surface.convert()

    def clicked(self, event):
        '''The label of the button `event` left-clicks, or None.'''
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for label, button in self.buttons.items():
                if button.collidepoint(event.pos):
                    return label
        return None

    def update(self, dt, keys):
        pass

    def draw(self, screen):
        screen.blit(self.surface, (0, 0))


class Play:
    '''One level being played: the player, the obstacles, the coins, and the goal.

    The level is finished once the player has every coin and any part of them
    is on the goal's green. Until then the goal is just another safe zone.

    With `god_mode` on, touching a dot does nothing; everything else is unchanged.
    '''

    GOD_MODE_LABEL = 'GOD MODE'

    def __init__(self, level):
        self.level = level
        self.walls = build_walls(level.PLAYFIELD)
        self.goal = region_rect(*level.GOAL)
        self.level_surface = build_level_surface(level, self.walls)
        self.obstacle_sprite = build_obstacle_sprite()
        self.coin_sprite = build_coin_sprite()
        self.finished = False
        self.god_mode = False
        self.god_mode_label = pygame.font.Font(None, 36).render(self.GOD_MODE_LABEL, True, BLACK)
        self.reset()

    def reset(self):
        '''Put the player back on its spawn, every obstacle at its start, every coin out.'''
        self.pos = pygame.Vector2(self.level.PLAYER_SPAWN)
        self.player = pygame.Rect(self.level.PLAYER_SPAWN, PLAYER_SIZE)
        self.dots = obstacles.spawn(self.level.OBSTACLES)
        self.coins = list(self.level.COINS)

    def update(self, dt, keys):
        velocity = read_input(keys)
        move_player(self.pos, self.player, velocity.x * dt, velocity.y * dt, self.walls)
        for dot in self.dots:
            dot.update(dt)
        if not self.god_mode and any(dot.touches(self.player) for dot in self.dots):
            self.reset()
            return
        self.coins = [coin for coin in self.coins
                      if not obstacles.circle_touches_rect(coin, COIN_RADIUS, self.player)]
        if not self.coins and self.player.colliderect(self.goal):
            self.finished = True

    def draw(self, screen):
        screen.blit(self.level_surface, (0, 0))
        for coin in self.coins:
            draw_centered(screen, self.coin_sprite, coin)
        pygame.draw.rect(screen, RED, self.player)
        pygame.draw.rect(screen, BLACK, self.player, 5)
        for dot in self.dots:
            draw_centered(screen, self.obstacle_sprite, dot.center)
        if self.god_mode:
            screen.blit(self.god_mode_label, (16, 16))


class Game:
    '''The states the game can be in: the menu it opens on, each level in turn,
    and the win screen after the last one.

    Only the current state is updated, and each level starts fresh when it is
    entered, so nothing moves while a screen is up.

    With `dev` on, pressing T in a level toggles god mode, which stays as set
    across levels and restarts.
    '''

    def __init__(self, levels, dev=False):
        self.levels = levels
        self.dev = dev
        self.god_mode = False
        self.menu = Screen("World's Easiest Game", ['START'])  # what the game opens on
        self.won = Screen('You Won!', ['RESTART', 'QUIT'])  # after the last level
        self.play = None
        self.state = self.menu
        self.running = True

    def start_level(self, index):
        self.level_index = index
        self.play = Play(self.levels[index])
        self.play.god_mode = self.god_mode
        self.state = self.play

    def toggle_god_mode(self):
        self.god_mode = not self.god_mode
        if self.play:
            self.play.god_mode = self.god_mode

    def handle(self, event):
        if (self.dev and self.state is self.play
                and event.type == pygame.KEYDOWN and event.key == pygame.K_t):
            self.toggle_god_mode()
        elif self.state is self.menu and self.menu.clicked(event) == 'START':
            self.start_level(0)
        elif self.state is self.won:
            choice = self.won.clicked(event)
            if choice == 'RESTART':
                self.start_level(0)
            elif choice == 'QUIT':
                self.running = False

    def update(self, dt, keys):
        self.state.update(dt, keys)
        if self.state is self.play and self.play.finished:
            if self.level_index + 1 < len(self.levels):
                self.start_level(self.level_index + 1)
            else:
                self.state = self.won

    def draw(self, screen):
        self.state.draw(screen)


def run(levels, dev=False):
    '''Open the game on its menu; starting from there plays `levels` in order.

    `dev` turns on the developer-only keys: T toggles god mode.
    '''
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    clock = pygame.time.Clock()
    game = Game(levels, dev)
    coords = []

    while game.running:
        dt = clock.tick(FPS) / 1000

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                game.running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and DEBUG:
                coords.append(pygame.mouse.get_pos())
                print(coords)
            game.handle(event)

        keys = pygame.key.get_pressed()
        if keys[pygame.K_q]:
            game.running = False

        game.update(dt, keys)
        game.draw(screen)
        pygame.display.flip()

    pygame.quit()
