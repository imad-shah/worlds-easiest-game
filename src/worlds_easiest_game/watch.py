'''Watching the learner train on the game's levels, in the game window.

Training goes level by level, as `evolve.Training` goes. Each generation plays
as an `evolve.Round`, whose runs step together one STEP at a time at the game's
own pace, every character still alive drawn where it is as the red player
square. Those are the very runs the learner scores: the round is scored from
them once they have all ended, and the next generation starts at once, on the
next level once one beats this one. A plain readout at the top-left takes the
place of the top bar. F switches to fast mode and back, and B between drawing
every character and only the one the round is following
(`evolve.Round.leader`). Once the last level is beaten, the winning runs kept
for every level are replayed one after another, the whole game in one run, and
the last of them then stays on screen until the window is closed.
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


def readout(level, levels, generation, alive, steps):
    '''The readout's numbers, on one line: the level on screen out of all
    `levels`, the generation, how many of its characters no dot has touched,
    and the steps its run has taken.'''
    return f'Level: {level}/{levels}   Generation: {generation}   Alive: {alive}   Steps: {steps}'


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
    '''The learner training on `levels` in order from `seed` as `settings` says,
    shown in the window as `engine.drive` runs it, for up to `cap` generations a
    level.

    Each frame runs as many steps of the generation on screen as real time has
    covered, or, in `fast` mode, trains for FAST_FRAME whatever that takes. With
    `best_only` on, only the round's leader is drawn. Once a generation beats
    its level, the next generation is the first on the next level. Once the last
    level is beaten, each level's kept solution is replayed in turn, at the
    game's own pace, `replayed` being the one on screen; if a level plays `cap`
    generations without being beaten, training stops. Either way the last
    frame stays until the window is closed.
    '''

    def __init__(self, levels, settings, seed, cap):
        self.levels = levels
        self.learner = evolve.Training(levels, settings, seed, cap)
        self.log = evolve.Log(self.learner)
        self.rounds = self.learner.rounds()
        self.round = next(self.rounds)
        self.runs = self.round.runs  # what is on screen: the round's runs, or a solution's replay
        self.replayed = None  # which level's solution is on screen, once every level is beaten
        self.given_up = False
        self.fast = False
        self.best_only = False
        self.running = True
        self.level_surfaces = [engine.build_level_surface(level, engine.level_walls(level)) for level in levels]
        self.obstacle_sprite = engine.build_obstacle_sprite()
        self.coin_sprite = engine.build_coin_sprite()
        self.font = pygame.font.Font(None, engine.BAR_FONT_SIZE)
        self.hint_font = pygame.font.Font(None, HINT_FONT_SIZE)

    @property
    def training(self):
        return self.replayed is None and not self.given_up

    @property
    def level_index(self):
        '''Where the level on screen is in `levels`.'''
        return self.learner.level_number - 1 if self.replayed is None else self.replayed

    def handle(self, event):
        if self.training and event.type == pygame.KEYDOWN:
            if event.key == FAST_KEY:
                self.fast = not self.fast
            elif event.key == BEST_KEY:
                self.best_only = not self.best_only

    def step(self):
        '''Advance the runs on screen one STEP. Once a generation's runs have all
        ended and been shown where they ended, it is scored and reported, and the
        next STEP starts the next generation, or the replay of the first level's
        solution once every level is beaten; once a replay has ended, the next
        STEP starts the next level's.'''
        if not self.runs.over:
            self.runs.step()
        elif self.training:
            self.log.round(self.round)
            following = next(self.rounds, None)
            if following is not None:
                self.round, self.runs = following, following.runs
                return
            self.log.end()
            if self.learner.beaten:
                self.replay(0)
            else:
                self.given_up = True
        elif self.replayed is not None and self.replayed + 1 < len(self.levels):
            self.replay(self.replayed + 1)

    def replay(self, index):
        '''Put the replay of level `index`'s solution on screen.'''
        self.replayed = index
        self.runs = self.learner.solutions[index].replay()

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
        '''The attempts to draw: every one alive, or just the round's leader.'''
        if self.best_only and self.training:
            leader = self.round.leader()
            return [] if leader is None else [self.runs.attempts[leader]]
        return self.runs.alive

    def hint(self):
        '''The hint line: the keys while training, and after it, how it ended.
        The readout says which level and generation it ended on.'''
        if self.training:
            return keys_hint(self.fast, self.best_only)
        if self.given_up:
            return 'Not beaten, training stopped   Q: quit'
        if not (self.runs.over and self.replayed + 1 == len(self.levels)):
            return 'Replaying the whole game'
        return 'Every level beaten!   Q: quit'

    def draw(self, screen):
        '''Draw the level and the characters onto `screen`, the whole window,
        with the readout over its top-left corner.'''
        screen.fill(engine.BACKGROUND, (0, 0, engine.SCREEN_WIDTH, engine.BAR_HEIGHT))
        play = screen.subsurface(engine.PLAY_AREA)
        play.blit(self.level_surfaces[self.level_index], (0, 0))
        shown = self.shown()
        # A coin is drawn while any character drawn has not collected it.
        for coin in self.levels[self.level_index].COINS:
            if any(coin in attempt.coins for attempt in shown):
                engine.draw_centered(play, self.coin_sprite, coin)
        for attempt in shown:
            engine.draw_player(play, attempt.player)
        for dot in self.runs.dots.moving:
            engine.draw_centered(play, self.obstacle_sprite, dot.center)

        if self.replayed is None:
            generation = self.round.number
        else:
            generation = self.learner.solutions[self.replayed].generation
        draw_line(screen, self.font, readout(self.level_index + 1, len(self.levels), generation,
                                             len(self.runs.alive), self.runs.steps), READOUT_TOP)
        draw_line(screen, self.hint_font, self.hint(), self.hint_top)

    @property
    def hint_top(self):
        '''How far the hint line's glyph box is from the window's top, under the numbers.'''
        return READOUT_TOP + self.font.get_linesize() + HINT_GAP


def run(levels, settings, seed, cap):
    '''Train on `levels` in the window, as `Watch` shows it, until the window is closed.

    Returns the `evolve.Training`.
    '''
    screen = engine.open_window()
    watch = Watch(levels, settings, seed, cap)
    engine.drive(watch, screen)
    pygame.quit()
    return watch.learner
