'''The game as the window runs it: the menu it opens on, the levels played by
hand, the win screen, and the learner training on the levels to watch.

The menu offers exactly two options: Start game (START) plays the levels by
hand, and Watch the AI beat the game (WATCH) trains the learner on them from
level 1 in the window, as `watch.Watch` shows it, with as many characters a
generation as the menu's population field says. Esc goes back to the menu from
either, at any point.
'''

import pygame

from worlds_easiest_game import engine, evolve, watch

START = 'Start game'
WATCH = 'Watch the AI beat the game'
MAX_POPULATION = 1000  # the most characters a generation watched from the menu can have
POPULATION_LABEL = 'Characters per generation:'
POPULATION_RANGE = f'({evolve.MIN_POPULATION}-{MAX_POPULATION})'
# The most digits the population field holds, enough for any number up to MAX_POPULATION.
POPULATION_DIGITS = len(str(MAX_POPULATION))


def type_into(text, event):
    '''The population field's `text` once key press `event` has been typed into
    it: a digit is added to the end while it holds fewer than POPULATION_DIGITS,
    or replaces a lone 0 so no leading zeros pile up, Backspace deletes the last
    one, and any other key leaves it as it was.'''
    if event.key == pygame.K_BACKSPACE:
        return text[:-1]
    if event.unicode.isascii() and event.unicode.isdigit() and len(text) < POPULATION_DIGITS:
        return event.unicode if text == '0' else text + event.unicode
    return text


def population_from(text):
    '''The population the field's `text` asks for: its number held between
    evolve.MIN_POPULATION and MAX_POPULATION, or evolve.DEFAULT_POPULATION
    when it is empty.'''
    if not text:
        return evolve.DEFAULT_POPULATION
    return max(evolve.MIN_POPULATION, min(MAX_POPULATION, int(text)))


class Menu:
    '''The card the game opens on: the title, the two options' buttons one above
    the other, and under them the population field for watching, where the
    number of characters each generation has is typed, with its allowed range
    beside it.

    It keeps the win screen's look (`engine.Screen`): the same title, fonts and
    buttons, stacked in a column wide enough for the longer label. `handle`
    names the option a left click chooses. A left click on the field focuses it
    and one anywhere else leaves it; while it is `focused`, the keys type into
    its `text` as `type_into` does, and Enter chooses Watch the AI beat the game.
    `text` starts as evolve.DEFAULT_POPULATION, and `population` is what it asks
    for, as `population_from` reads it.
    '''

    BUTTON_HEIGHT = engine.Screen.BUTTON_SIZE[1]
    BUTTON_PADDING = 40  # px between the longer label and its button's sides
    BUTTON_GAP = 24  # px between the two buttons
    FIELD_SIZE = (130, 50)
    CARET_WIDTH = 3
    CARET_GAP = 5  # px between the number's ink and the caret
    LABEL_FONT_SIZE = 36
    LABEL_GAP = 20  # px between the field and the texts either side of it

    def __init__(self):
        self.text = str(evolve.DEFAULT_POPULATION)
        self.focused = False
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

        # The field's label, the field and its range, in a row centered under the buttons.
        label_font = pygame.font.Font(None, self.LABEL_FONT_SIZE)
        label = label_font.render(POPULATION_LABEL, True, engine.BLACK)
        allowed = label_font.render(POPULATION_RANGE, True, engine.BLACK)
        row = label.get_width() + allowed.get_width() + 2 * self.LABEL_GAP + self.FIELD_SIZE[0]
        rowy = middle + 150
        left = centerx - row // 2
        # Set on the baseline that centers their capitals on the row, as the number's digits are.
        cap_height = label_font.metrics('H')[0][3]
        texty = rowy + (cap_height + 1) // 2 - label_font.get_ascent()
        self.surface.blit(label, (left, texty))
        self.field = pygame.Rect((left + label.get_width() + self.LABEL_GAP, 0), self.FIELD_SIZE)
        self.field.centery = rowy
        pygame.draw.rect(self.surface, engine.WHITE, self.field)
        pygame.draw.rect(self.surface, engine.BLACK, self.field, engine.WALL_THICKNESS)
        self.surface.blit(allowed, (self.field.right + self.LABEL_GAP, texty))
        self.surface = self.surface.convert()

    @property
    def population(self):
        return population_from(self.text)

    def handle(self, event):
        '''The option `event` chooses, or None, as the class says; a click or
        key press that chooses none may focus, leave or type into the field.'''
        if event.type == pygame.KEYDOWN and self.focused:
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                return WATCH
            self.text = type_into(self.text, event)
            return None
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return None
        self.focused = self.field.collidepoint(event.pos)
        for label, button in self.buttons.items():
            if button.collidepoint(event.pos):
                return label
        return None

    def update(self, keys):
        pass

    def draw(self, screen):
        screen.blit(self.surface, (0, 0))
        # Centered by its ink, as the digits all stand the same height on the baseline.
        number = self.font.render(self.text, True, engine.BLACK)
        ink = number.get_bounding_rect()
        placed = ink.copy()
        placed.center = self.field.center
        if self.text:
            screen.blit(number, (placed.x - ink.x, placed.y - ink.y))
        if self.focused:
            # A caret as tall as the digits, just after them, or centered in the empty field.
            cap_height = self.font.metrics('0')[0][3]
            caret = pygame.Rect(0, 0, self.CARET_WIDTH, cap_height)
            caret.center = self.field.center
            if self.text:
                caret.left = placed.right + self.CARET_GAP
            screen.fill(engine.BLACK, caret)


class Game:
    '''The states the game can be in: the menu it opens on, each level in turn,
    the win screen after the last one, and the learner training to watch.

    Only the current state is updated, and each level starts fresh when it is
    entered, so nothing moves while a screen is up. A level is drawn under the
    top bar; the menu, the win screen and the watch fill the window.

    `deaths` counts every death since Start game or Restart, across levels.

    Esc in a level or on the win screen goes back to the menu, dropping the
    game played so far: Start game from there plays level 1 afresh.

    Watch the AI beat the game starts a new `watch.Watch` training on `levels`
    from level 1, with the menu's population and the learner's other defaults,
    and a random seed it prints; once Esc stops it, the game is back on the menu.

    With `dev` on, pressing T in a level toggles god mode, which stays as set
    across levels and restarts.
    '''

    def __init__(self, levels, dev=False):
        self.levels = levels
        self.dev = dev
        self.god_mode = False
        self.menu = Menu()  # what the game opens on
        self.won = engine.Screen('You Won!', ['Restart', 'Quit'])  # after the last level
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
        population = self.menu.population
        # Shown on the way back as it was watched, held in range, with the field left.
        self.menu.text = str(population)
        self.menu.focused = False
        settings = evolve.Settings(population=population)
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
        elif (self.state in (self.play, self.won)
              and event.type == pygame.KEYDOWN and event.key == watch.MENU_KEY):
            self.play = None
            self.state = self.menu
        elif self.state is self.menu:
            choice = self.menu.handle(event)
            if choice == START:
                self.start_level(0)
            elif choice == WATCH:
                self.start_watch()
        elif self.state is self.won:
            choice = self.won.clicked(event)
            if choice == 'Restart':
                self.start_level(0)
            elif choice == 'Quit':
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
