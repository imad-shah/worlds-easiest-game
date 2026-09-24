import math
import time

import pygame

from worlds_easiest_game import obstacles


# constants
TITLE = "World's Easiest Game"  # the window's title, and the menu's
# The play area every level is laid out on; level coordinates are relative to it.
SCREEN_WIDTH = 981
SCREEN_HEIGHT = 574
# The black bar across the top of the window, as in the original. It sits above
# the play area rather than over it, since some courses reach the play area's top.
BAR_HEIGHT = 40
BAR_FONT_SIZE = 32
BAR_MARGIN = 16  # px between the bar's side labels and the window's edges
WINDOW_HEIGHT = BAR_HEIGHT + SCREEN_HEIGHT
PLAY_AREA = (0, BAR_HEIGHT, SCREEN_WIDTH, SCREEN_HEIGHT)  # where the play area sits in the window
FPS = 120
# The game logic only ever advances by this much, so where the player and the dots
# are depends on how many steps have run and the keys held for each, never on how
# long a frame took to draw. The window runs FPS steps for every second of real time.
STEP = 1 / FPS
# The most real time one drawn frame may catch up on. After a longer stall (the
# window dragged, the machine asleep) the game loses the rest rather than running
# a burst of steps to make it up.
MAX_FRAME_TIME = 0.1
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
DEBUG = False  # click anywhere to print play-area coordinates, for laying out new levels

# colors
BACKGROUND = '#aaa5ff'
RED = '#ff0000'
BLACK = '#000000'
WHITE = '#ffffff'
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


def centered_spawn(area):
    '''Where the player's top-left corner goes for the player to stand centered on `area`.'''
    player = pygame.Rect((0, 0), PLAYER_SIZE)
    player.center = area.center
    return player.topleft


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


def level_outlines(level):
    '''The course outline, then the outline of each wall standing inside the course.

    A level lists those inner walls, if it has any, as INNER_WALLS: closed,
    axis-aligned polygons like PLAYFIELD, around space that is not floor.
    '''
    return [level.PLAYFIELD, *getattr(level, 'INNER_WALLS', ())]


def level_walls(level):
    '''Every wall of `level`, built from each of its outlines.'''
    return [wall for outline in level_outlines(level) for wall in build_walls(outline)]


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

    `pos` is the float position (Vector2) that survives between steps; `player`
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


def draw_player(surface, player):
    '''Draw the red player square at `player`, a Rect.'''
    pygame.draw.rect(surface, RED, player)
    pygame.draw.rect(surface, BLACK, player, 5)


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


def coin_text(collected, total):
    '''The bar's left label: coins collected on the level out of its total.'''
    return f'COINS: {collected}/{total}'


def level_text(number, total):
    '''The bar's middle label: the current level out of the total.'''
    return f'LEVEL {number}/{total}'


def death_text(deaths):
    '''The bar's right label.'''
    return f'DEATHS: {deaths}'


class TopBar:
    '''The black bar across the top of the window, with three white labels in it.

    The labels share one font and one baseline; the left one hugs the left edge,
    the middle one is centered, and the right one hugs the right.
    '''

    def __init__(self):
        self.font = pygame.font.Font(None, BAR_FONT_SIZE)

    def draw(self, screen, left, middle, right):
        screen.fill(BLACK, (0, 0, SCREEN_WIDTH, BAR_HEIGHT))
        # Every label is set on one baseline, which centers the capitals in the bar
        # (the labels have no descenders), and is placed by its ink rather than
        # its glyph boxes, so the margins and the middle come out exact.
        cap_height = self.font.metrics('H')[0][3]
        top = (BAR_HEIGHT + cap_height) // 2 - self.font.get_ascent()
        for text, edge, x in ((left, 'left', BAR_MARGIN),
                              (middle, 'centerx', SCREEN_WIDTH // 2),
                              (right, 'right', SCREEN_WIDTH - BAR_MARGIN)):
            label = self.font.render(text, True, WHITE)
            ink = label.get_bounding_rect()
            placed = ink.copy()
            setattr(placed, edge, x)
            screen.blit(label, (placed.x - ink.x, top))


class Screen:
    '''A full-window card shown outside a level: a title over a row of buttons.

    `clicked` names the button a left click lands on, so the game decides what
    each one does.
    '''

    BUTTON_SIZE = (220, 70)
    BUTTON_GAP = 40

    def __init__(self, title, labels):
        self.surface = pygame.Surface((SCREEN_WIDTH, WINDOW_HEIGHT))
        self.surface.fill(BACKGROUND)
        middle = WINDOW_HEIGHT // 2
        title = pygame.font.Font(None, 84).render(title, True, BLACK)
        self.surface.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, middle - 70)))

        width, height = self.BUTTON_SIZE
        row = len(labels) * width + (len(labels) - 1) * self.BUTTON_GAP
        left = (SCREEN_WIDTH - row) // 2
        font = pygame.font.Font(None, 48)
        self.buttons = {}
        for i, label in enumerate(labels):
            button = pygame.Rect(left + i * (width + self.BUTTON_GAP), 0, width, height)
            button.centery = middle + 60
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

    def update(self, keys):
        pass

    def draw(self, screen):
        screen.blit(self.surface, (0, 0))


class Dots:
    '''A level's dots, moving, which any number of attempts started together can share.

    `at(steps)` moves every dot on to where it is once `steps` STEPs have run
    since the start, one STEP at a time, and returns them. Attempts sharing one
    set step in turn and each ask for the step they have reached, so only the
    first to ask moves the dots, once for all of them. No attempt can ask for a
    step the dots have already moved past.
    '''

    def __init__(self, level):
        self.moving = obstacles.spawn(level.OBSTACLES)
        self.steps = 0

    def at(self, steps):
        if steps < self.steps:
            raise ValueError(f'the dots have already moved past step {steps}, to step {self.steps}')
        while self.steps < steps:
            for dot in self.moving:
                dot.update(STEP)
            self.steps += 1
        return self.moving


class Attempt:
    '''One try at a level by its rules alone, from the spawn until it ends.

    The player starts on `spawn` (the level's own spawn unless given), every dot
    at its start, and every coin out. `step` advances all of it by one STEP: the
    player moves at `velocity` (as `read_input` gives it), then the dots move,
    then a dot touching the player ends the attempt as `died`, before any coin it
    is on is collected. Otherwise the coins the player touches are collected, and
    the attempt is `beaten` once the player has every coin and any part of them
    is on the goal's green. Until then the goal is just another safe zone.
    `steps` counts the steps taken.

    A level may name one safe zone its CHECKPOINT. Once any part of the player
    has been on it, `respawn`, where a death puts them back, is centered on it
    instead of on the attempt's spawn; everything else a death resets is unchanged.

    An attempt moves its own `dots` unless given a set of `Dots` to share with
    other attempts started at the same time; the dots are where they would be
    for this attempt alone either way, since they never depend on the player.

    Nothing here draws or needs a display, so an attempt can be stepped without a
    window, as fast as the machine allows. The window plays a level as a series of
    attempts, through `Play`, and `headless.play` runs a single one (and
    `headless.play_all` many at once, sharing their `Dots`), so all follow the
    same rules.
    '''

    def __init__(self, level, spawn=None, dots=None):
        spawn = level.PLAYER_SPAWN if spawn is None else spawn
        self.level = level
        self.walls = level_walls(level)
        self.goal = region_rect(*level.GOAL)
        checkpoint = getattr(level, 'CHECKPOINT', None)
        self.checkpoint = region_rect(*checkpoint) if checkpoint else None
        self.respawn = spawn  # where a death puts the player back
        self.pos = pygame.Vector2(spawn)  # where the player is, to the fraction
        self.player = pygame.Rect(spawn, PLAYER_SIZE)
        self.dots = Dots(level) if dots is None else dots
        self.coins = list(level.COINS)
        self.steps = 0
        self.died = False
        self.beaten = False

    def step(self, velocity, god_mode=False):
        '''Advance one STEP. With `god_mode` on, touching a dot does nothing.'''
        self.steps += 1
        move_player(self.pos, self.player, velocity.x * STEP, velocity.y * STEP, self.walls)
        dots = self.dots.at(self.steps)
        if not god_mode and any(dot.touches(self.player) for dot in dots):
            self.died = True
            return
        if self.checkpoint and self.player.colliderect(self.checkpoint):
            self.respawn = centered_spawn(self.checkpoint)
        self.coins = [coin for coin in self.coins
                      if not obstacles.circle_touches_rect(coin, COIN_RADIUS, self.player)]
        if not self.coins and self.player.colliderect(self.goal):
            self.beaten = True

    @property
    def coins_collected(self):
        return len(self.level.COINS) - len(self.coins)


class Play:
    '''One level being played in the window: one `Attempt` after another until one beats it.

    A dot touching the player is a death: the level starts over with a fresh
    attempt, the player back on the `respawn` of the attempt that died, every dot
    at its start and every coin out.

    `deaths` counts every touch of a dot, starting from the count it is given.
    With `god_mode` on, touching a dot does nothing and is not a death; everything
    else is unchanged.
    '''

    GOD_MODE_LABEL = 'GOD MODE'

    def __init__(self, level, deaths=0):
        self.level = level
        self.deaths = deaths
        self.attempt = Attempt(level)
        self.level_surface = build_level_surface(level, self.attempt.walls)
        self.obstacle_sprite = build_obstacle_sprite()
        self.coin_sprite = build_coin_sprite()
        self.god_mode = False
        self.god_mode_label = pygame.font.Font(None, 36).render(self.GOD_MODE_LABEL, True, BLACK)

    def update(self, keys):
        '''Advance one STEP with `keys` held, as pygame.key.get_pressed() reports them.'''
        self.attempt.step(read_input(keys), self.god_mode)
        if self.attempt.died:
            self.deaths += 1
            self.attempt = Attempt(self.level, self.attempt.respawn)

    @property
    def finished(self):
        return self.attempt.beaten

    def draw(self, screen):
        '''Draw the level onto `screen`, a play-area-sized surface.'''
        attempt = self.attempt
        screen.blit(self.level_surface, (0, 0))
        for coin in attempt.coins:
            draw_centered(screen, self.coin_sprite, coin)
        draw_player(screen, attempt.player)
        for dot in attempt.dots.moving:
            draw_centered(screen, self.obstacle_sprite, dot.center)
        if self.god_mode:
            # Bottom left, the one corner every course stays clear of.
            screen.blit(self.god_mode_label,
                        self.god_mode_label.get_rect(bottomleft=(16, SCREEN_HEIGHT - 16)))


class Game:
    '''The states the game can be in: the menu it opens on, each level in turn,
    and the win screen after the last one.

    Only the current state is updated, and each level starts fresh when it is
    entered, so nothing moves while a screen is up. A level is drawn under the
    top bar; the menu and win screens fill the window.

    `deaths` counts every death since Start or Restart, across levels.

    With `dev` on, pressing T in a level toggles god mode, which stays as set
    across levels and restarts.
    '''

    def __init__(self, levels, dev=False):
        self.levels = levels
        self.dev = dev
        self.god_mode = False
        self.menu = Screen(TITLE, ['START'])  # what the game opens on
        self.won = Screen('You Won!', ['RESTART', 'QUIT'])  # after the last level
        self.bar = TopBar()
        self.play = None
        self.state = self.menu
        self.running = True

    @property
    def deaths(self):
        return self.play.deaths if self.play else 0

    def start_level(self, index):
        '''Play level `index`, carrying the death count on from the level before it.'''
        self.level_index = index
        self.play = Play(self.levels[index], self.deaths if index else 0)
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

    def update(self, keys):
        '''Advance the current state one STEP with `keys` held.'''
        self.state.update(keys)
        if self.state is self.play and self.play.finished:
            if self.level_index + 1 < len(self.levels):
                self.start_level(self.level_index + 1)
            else:
                self.state = self.won

    def advance(self, keys, steps):
        '''Run `steps` STEPs of the current state with `keys` held, as a frame of `drive` does.'''
        for _ in range(steps):
            self.update(keys)

    def draw(self, screen):
        '''Draw the current state onto `screen`, the whole window.'''
        if self.state is not self.play:
            self.state.draw(screen)
            return
        level = self.play.level
        self.bar.draw(screen, coin_text(self.play.attempt.coins_collected, len(level.COINS)),
                      level_text(self.level_index + 1, len(self.levels)), death_text(self.deaths))
        self.play.draw(screen.subsurface(PLAY_AREA))


def open_window():
    '''Start pygame and open the game window, titled with the game's name.'''
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption(TITLE)
    return screen


def drive(game, screen):
    '''Run `game` in the window `screen` until it stops `running`, at real-time pace.

    Each frame hands `game.handle` every event, then `game.advance` the keys held
    and how many STEPs of real time the frame covers, then has `game.draw` the
    window. Pressing Q or closing the window stops it.
    '''
    coords = []
    unstepped = 0.0  # real time drawn frames have taken that no step has covered yet
    last_frame = time.perf_counter()

    while game.running:
        # Wait until the next step is due, timed finer than the whole milliseconds
        # pygame.time.Clock rounds to, so a frame runs exactly one step whenever
        # the machine keeps up rather than drifting against STEP.
        now = time.perf_counter()
        while unstepped + (now - last_frame) < STEP:
            time.sleep(STEP - (unstepped + (now - last_frame)))
            now = time.perf_counter()
        unstepped += min(now - last_frame, MAX_FRAME_TIME)
        last_frame = now

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                game.running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and DEBUG:
                x, y = pygame.mouse.get_pos()
                coords.append((x, y - BAR_HEIGHT))
                print(coords)
            game.handle(event)

        keys = pygame.key.get_pressed()
        if keys[pygame.K_q]:
            game.running = False

        # Run a step for every STEP of real time the frame took, carrying the
        # remainder over, so the game keeps real-time pace whatever the frame rate.
        steps = 0
        while unstepped >= STEP:
            steps += 1
            unstepped -= STEP
        game.advance(keys, steps)
        game.draw(screen)
        pygame.display.flip()


def run(levels, dev=False):
    '''Open the game on its menu; starting from there plays `levels` in order.

    `dev` turns on the developer-only keys: T toggles god mode.
    '''
    screen = open_window()
    drive(Game(levels, dev), screen)
    pygame.quit()
