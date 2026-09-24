'''Watching the learner train on a level, in the game window.

Each generation plays as an `evolve.Round`, whose runs step together one STEP
at a time at the game's own pace, every character still alive drawn where it
is as the red player square. Those are the very runs the learner scores: the
round is scored from them once they have all ended, and the next generation
starts at once. A plain readout at the top-left takes the place of the top
bar. F switches to fast mode and back, and B between drawing every character
and only the one the round is following (`evolve.Round.leader`). Once a
generation beats the level, its winning run is replayed alone, and then stays
on screen until the window is closed.
'''

import time

import pygame

from worlds_easiest_game import engine, evolve

FAST_KEY = pygame.K_f
BEST_KEY = pygame.K_b
# In fast mode each frame trains for this long, then draws where training has got to.
FAST_FRAME = 1 / 30  # seconds
READOUT_TOP = 8  # px from the window's top to the readout
HINT_FONT_SIZE = 24
HINT_GAP = 6  # px between the readout's numbers and its hint line


def readout(generation, alive, steps):
    '''The readout's lines: the generation on screen, how many of its characters
    no dot has touched, and the steps its run has taken.'''
    return [f'Generation: {generation}', f'Alive: {alive}', f'Steps: {steps}']


def keys_hint(fast, best_only):
    '''The hint line while training: what F and B switch to.'''
    speed = 'normal speed' if fast else 'fast mode'
    shown = 'show all' if best_only else 'best only'
    return f'F: {speed}   B: {shown}   Q: quit'


def draw_line(screen, font, text, y):
    '''Draw a white line of the readout in `font`, with its glyph box's top at
    `y` and its ink starting BAR_MARGIN from the window's left edge, as the top
    bar's left label does.'''
    label = font.render(text, True, engine.WHITE)
    screen.blit(label, (engine.BAR_MARGIN - label.get_bounding_rect().x, y))


class Watch:
    '''The learner training on `level` from `seed` as `settings` says, shown in the
    window as `engine.drive` runs it, for up to `cap` generations.

    Each frame runs as many steps of the generation on screen as real time has
    covered, or, in `fast` mode, trains for FAST_FRAME whatever that takes. With
    `best_only` on, only the round's leader is drawn. Once a generation beats
    the level, `winner` is that generation and its best character's run is
    replayed at the game's own pace; after `cap` generations without one,
    training stops. Either way the last frame stays until the window is closed.
    '''

    def __init__(self, level, settings, seed, cap):
        self.cap = cap
        self.rounds = evolve.rounds(level, settings, seed)
        self.round = next(self.rounds)
        self.runs = self.round.runs  # what is on screen: the round's runs, or the winner's replay
        self.winner = None
        self.given_up = False
        self.fast = False
        self.best_only = False
        self.running = True
        self.level_surface = engine.build_level_surface(level, engine.level_walls(level))
        self.obstacle_sprite = engine.build_obstacle_sprite()
        self.font = pygame.font.Font(None, engine.BAR_FONT_SIZE)
        self.hint_font = pygame.font.Font(None, HINT_FONT_SIZE)

    @property
    def training(self):
        return self.winner is None and not self.given_up

    def handle(self, event):
        if self.training and event.type == pygame.KEYDOWN:
            if event.key == FAST_KEY:
                self.fast = not self.fast
            elif event.key == BEST_KEY:
                self.best_only = not self.best_only

    def step(self):
        '''Advance the runs on screen one STEP. Once a generation's runs have all
        ended and been shown where they ended, it is scored and reported, and the
        next STEP starts the next generation, or the replay of its winner.'''
        if not (self.training and self.runs.over):
            self.runs.step()
        else:
            generation = self.round.generation
            evolve.report(generation)
            if generation.beaten:
                self.winner = generation
                self.runs = self.round.replay(generation.best)
            elif generation.number >= self.cap:
                evolve.give_up(self.cap)
                self.given_up = True
            else:
                self.round = next(self.rounds)
                self.runs = self.round.runs

    def hurry(self, until):
        '''Train as fast as the machine allows until `until`, a `time.perf_counter()`
        time, or until training ends.'''
        while self.training and time.perf_counter() < until:
            self.step()

    def advance(self, keys, steps):
        '''Run a frame of `engine.drive`: `steps` STEPs, or FAST_FRAME of training in fast mode.'''
        if self.fast and self.training:
            self.hurry(time.perf_counter() + FAST_FRAME)
        else:
            for _ in range(steps):
                self.step()

    def shown(self):
        '''The players to draw: every one alive, or just the round's leader.'''
        if self.best_only and self.training:
            leader = self.round.leader()
            return [] if leader is None else [self.runs.attempts[leader].player]
        return [attempt.player for attempt in self.runs.alive]

    def hint(self):
        if self.training:
            return keys_hint(self.fast, self.best_only)
        if self.given_up:
            return f'Not beaten in {self.cap} generations   Q: quit'
        if not self.runs.over:
            return 'Replaying the winning run'
        return f'Beaten in generation {self.winner.number}!   Q: quit'

    def draw(self, screen):
        '''Draw the level and the characters onto `screen`, the whole window,
        with the readout over its top-left corner.'''
        screen.fill(engine.BACKGROUND, (0, 0, engine.SCREEN_WIDTH, engine.BAR_HEIGHT))
        play = screen.subsurface(engine.PLAY_AREA)
        play.blit(self.level_surface, (0, 0))
        for player in self.shown():
            engine.draw_player(play, player)
        for dot in self.runs.dots.moving:
            engine.draw_centered(play, self.obstacle_sprite, dot.center)

        y = READOUT_TOP
        for line in readout(self.round.number, len(self.runs.alive), self.runs.steps):
            draw_line(screen, self.font, line, y)
            y += self.font.get_linesize()
        draw_line(screen, self.hint_font, self.hint(), y + HINT_GAP)


def run(level, settings, seed, cap):
    '''Train on `level` in the window, as `Watch` shows it, until the window is closed.

    Returns the generation that beat the level, or None.
    '''
    screen = engine.open_window()
    watch = Watch(level, settings, seed, cap)
    engine.drive(watch, screen)
    pygame.quit()
    return watch.winner
