'''The game as the window runs it: the menu it opens on, the levels played by
hand, the win screen, and the learner training on the levels to watch.

The menu offers exactly two options: Start game (START) plays the levels by
hand, and Watch the AI beat the game (WATCH) trains the learner on them from
level 1 in the window, as `watch.Watch` shows it, with as many characters a
generation as the menu's population control says.
'''

import pygame

from worlds_easiest_game import engine, evolve, watch

START = 'Start game'
WATCH = 'Watch the AI beat the game'
# The generation sizes the menu's minus and plus buttons step through, smallest to largest.
POPULATIONS = (evolve.MIN_POPULATION, 5, 10, 25, 50, 100, 150, 200, 250, 300, 400, 500, 750, 1000)
POPULATION_LABEL = 'Characters per generation:'


def step_population(population, direction):
    '''The population one click of minus (`direction` -1) or plus (1) makes of
    `population`: the next of POPULATIONS that way, or `population` itself
    once there is none.'''
    if direction > 0:
        return min((choice for choice in POPULATIONS if choice > population), default=population)
    return max((choice for choice in POPULATIONS if choice < population), default=population)


class Menu:
    '''The card the game opens on: the title, the two options' buttons one above
    the other, and under them the population control for watching, a minus and a
    plus button either side of the number of characters each generation has.

    It keeps the win screen's look (`engine.Screen`): the same title, fonts and
    buttons, stacked in a column wide enough for the longer label. `handle`
    names the option a left click chooses; a click on minus or plus changes
    `population` instead, which starts at `evolve.DEFAULT_POPULATION`.
    '''

    BUTTON_HEIGHT = engine.Screen.BUTTON_SIZE[1]
    BUTTON_PADDING = 40  # px between the longer label and its button's sides
    BUTTON_GAP = 24  # px between the two buttons
    STEPPER_SIZE = 50  # the side of the minus and plus buttons
    SIGN_SIZE = 20  # the length of the bars the minus and plus signs are drawn with
    NUMBER_WIDTH = 110  # px between the minus and plus buttons, where the number goes
    LABEL_FONT_SIZE = 36
    LABEL_GAP = 20  # px between the control's label and its minus button

    def __init__(self):
        self.population = evolve.DEFAULT_POPULATION
        self.surface = pygame.Surface((engine.SCREEN_WIDTH, engine.WINDOW_HEIGHT))
        self.surface.fill(engine.BACKGROUND)
        middle = engine.WINDOW_HEIGHT // 2
        centerx = engine.SCREEN_WIDTH // 2
        title = pygame.font.Font(None, engine.Screen.TITLE_FONT_SIZE).render(engine.TITLE, True, engine.BLACK)
        self.surface.blit(title, title.get_rect(center=(centerx, middle - 150)))

        self.font = pygame.font.Font(None, engine.Screen.BUTTON_FONT_SIZE)
        width = max(self.font.size(label)[0] for label in (START, WATCH)) + 2 * self.BUTTON_PADDING
        self.buttons = {}
        for i, label in enumerate((START, WATCH)):
            button = pygame.Rect(0, 0, width, self.BUTTON_HEIGHT)
            button.center = (centerx, middle - 30 + i * (self.BUTTON_HEIGHT + self.BUTTON_GAP))
            engine.draw_button(self.surface, button, label, self.font)
            self.buttons[label] = button

        # The control's label, minus, the number and plus, in a row centered under the buttons.
        label = pygame.font.Font(None, self.LABEL_FONT_SIZE).render(POPULATION_LABEL, True, engine.BLACK)
        row = label.get_width() + self.LABEL_GAP + 2 * self.STEPPER_SIZE + self.NUMBER_WIDTH
        rowy = middle + 150
        left = centerx - row // 2
        self.surface.blit(label, label.get_rect(midleft=(left, rowy)))
        left += label.get_width() + self.LABEL_GAP
        self.minus = pygame.Rect(left, 0, self.STEPPER_SIZE, self.STEPPER_SIZE)
        self.number = pygame.Rect(self.minus.right, 0, self.NUMBER_WIDTH, self.STEPPER_SIZE)
        self.plus = pygame.Rect(self.number.right, 0, self.STEPPER_SIZE, self.STEPPER_SIZE)
        for rect in (self.minus, self.number, self.plus):
            rect.centery = rowy
        # Minus and plus are drawn as bars rather than set in the font, so they sit exactly centered.
        across = pygame.Rect(0, 0, self.SIGN_SIZE, engine.WALL_THICKNESS)
        down = pygame.Rect(0, 0, engine.WALL_THICKNESS, self.SIGN_SIZE)
        for button, bars in ((self.minus, [across]), (self.plus, [across, down])):
            engine.draw_button(self.surface, button)
            for bar in bars:
                bar.center = button.center
                self.surface.fill(engine.BLACK, bar)
        self.surface = self.surface.convert()

    def handle(self, event):
        '''The option `event` left-clicks, or None; a left click on minus or
        plus steps `population` down or up instead.'''
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return None
        if self.minus.collidepoint(event.pos):
            self.population = step_population(self.population, -1)
        elif self.plus.collidepoint(event.pos):
            self.population = step_population(self.population, 1)
        for label, button in self.buttons.items():
            if button.collidepoint(event.pos):
                return label
        return None

    def update(self, keys):
        pass

    def draw(self, screen):
        screen.blit(self.surface, (0, 0))
        # Centered by its ink, as the digits all stand the same height on the baseline.
        number = self.font.render(str(self.population), True, engine.BLACK)
        ink = number.get_bounding_rect()
        placed = ink.copy()
        placed.center = self.number.center
        screen.blit(number, (placed.x - ink.x, placed.y - ink.y))


class Game:
    '''The states the game can be in: the menu it opens on, each level in turn,
    the win screen after the last one, and the learner training to watch.

    Only the current state is updated, and each level starts fresh when it is
    entered, so nothing moves while a screen is up. A level is drawn under the
    top bar; the menu, the win screen and the watch fill the window.

    `deaths` counts every death since Start game or Restart, across levels.

    Watch the AI beat the game starts a new `watch.Watch` training on `levels` from level 1, with
    the menu's population and the learner's other defaults, and a random seed
    it prints; once Esc stops it, the game is back on the menu.

    With `dev` on, pressing T in a level toggles god mode, which stays as set
    across levels and restarts.
    '''

    def __init__(self, levels, dev=False):
        self.levels = levels
        self.dev = dev
        self.god_mode = False
        self.menu = Menu()  # what the game opens on
        self.won = engine.Screen('You Won!', ['RESTART', 'QUIT'])  # after the last level
        self.bar = engine.TopBar()
        self.play = None
        self.watching = None  # the learner training, while it is on screen
        self.state = self.menu
        self.running = True

    @property
    def deaths(self):
        return self.play.deaths if self.play else 0

    def start_level(self, index):
        '''Play level `index`, carrying the death count on from the level before it.'''
        self.level_index = index
        self.play = engine.Play(self.levels[index], self.deaths if index else 0)
        self.play.god_mode = self.god_mode
        self.state = self.play

    def start_watch(self):
        '''Train the learner on every level, from level 1, on screen.'''
        settings = evolve.Settings(population=self.menu.population)
        seed = evolve.announce(self.levels, settings)
        self.watching = watch.Watch(self.levels, settings, seed, evolve.DEFAULT_GENERATIONS, menu=True)
        self.state = self.watching

    def toggle_god_mode(self):
        self.god_mode = not self.god_mode
        if self.play:
            self.play.god_mode = self.god_mode

    def handle(self, event):
        if (self.dev and self.state is self.play
                and event.type == pygame.KEYDOWN and event.key == pygame.K_t):
            self.toggle_god_mode()
        elif self.state is self.menu:
            choice = self.menu.handle(event)
            if choice == START:
                self.start_level(0)
            elif choice == WATCH:
                self.start_watch()
        elif self.state is self.won:
            choice = self.won.clicked(event)
            if choice == 'RESTART':
                self.start_level(0)
            elif choice == 'QUIT':
                self.running = False
        elif self.state is self.watching:
            self.watching.handle(event)
            if not self.watching.running:
                self.watching = None
                self.state = self.menu

    def update(self, keys):
        '''Advance the current state one STEP with `keys` held.'''
        if self.state is self.watching:
            self.watching.step()
            return
        self.state.update(keys)
        if self.state is self.play and self.play.finished:
            if self.level_index + 1 < len(self.levels):
                self.start_level(self.level_index + 1)
            else:
                self.state = self.won

    def advance(self, keys, steps):
        '''Run a frame of `engine.drive`: `steps` STEPs of the current state with
        `keys` held, or, while watching, whatever the watch runs in a frame.'''
        if self.state is self.watching:
            self.watching.advance(keys, steps)
            return
        for _ in range(steps):
            self.update(keys)

    def draw(self, screen):
        '''Draw the current state onto `screen`, the whole window.'''
        if self.state is not self.play:
            self.state.draw(screen)
            return
        level = self.play.level
        self.bar.draw(screen, engine.coin_text(self.play.attempt.coins_collected, len(level.COINS)),
                      engine.level_text(self.level_index + 1, len(self.levels)), engine.death_text(self.deaths))
        self.play.draw(screen.subsurface(engine.PLAY_AREA))


def run(levels, dev=False):
    '''Open the game on its menu; starting from there plays `levels` in order,
    or trains the learner on them to watch.

    `dev` turns on the developer-only keys: T toggles god mode.
    '''
    screen = engine.open_window()
    engine.drive(Game(levels, dev), screen)
    pygame.quit()
