'''Tests for the menu the game opens on: its two options, the population field
for watching the learner, and moving from the menu to each option and back.

Nothing is played by hand here: the menu is driven by single clicks and key
presses, and the only training runs on a small level built for it, never on the
game's own levels. Frames are drawn offscreen and sampled; the dummy video
driver gives the surfaces a display to convert to without opening a window.
'''

import math
import os
import random
from types import SimpleNamespace

import pygame
import pytest

from worlds_easiest_game import app, engine, evolve, levels, watch
from worlds_easiest_game.obstacles import vertical


def gate():
    '''A corridor with a dot sweeping up and down across its middle, which a
    character has to time its way past to reach the goal at the far end.'''
    return SimpleNamespace(
        PLAYFIELD=[(100, 200), (340, 200), (340, 260), (100, 260)], PLAYER_SPAWN=(108, 215),
        PATH_REGIONS=[((100, 200), (340, 260))], SAFE_REGIONS=[((300, 200), (340, 260))],
        GOAL=((300, 200), (340, 260)), COINS=[],
        OBSTACLES=[vertical(x=220, from_y=210, to_y=250, speed=60)], TIME_LIMIT=3)


@pytest.fixture(scope='module')
def display():
    os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
    pygame.init()
    pygame.display.set_mode((engine.SCREEN_WIDTH, engine.WINDOW_HEIGHT))
    yield
    pygame.quit()


def click(rect):
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=rect.center, button=1)


def press(key):
    return pygame.event.Event(pygame.KEYDOWN, key=key)


def frame(shown):
    '''Draw `shown`, anything with a `draw(screen)`, into a fresh window-sized surface.'''
    window = pygame.Surface((engine.SCREEN_WIDTH, engine.WINDOW_HEIGHT))
    shown.draw(window)
    return window


def ink(window, area):
    '''The bounding box of everything but the background inside `area` of `window`, or None.'''
    points = [(x, y) for x in range(area.left, area.right) for y in range(area.top, area.bottom)
              if window.get_at((x, y)) != pygame.Color(engine.BACKGROUND)]
    if not points:
        return None
    xs, ys = zip(*points)
    return pygame.Rect(min(xs), min(ys), max(xs) - min(xs) + 1, max(ys) - min(ys) + 1)


def test_the_menu_offers_exactly_the_two_options(display):
    assert list(app.Game(levels.LEVELS).menu.buttons) == ['Start game', 'Watch the AI beat the game']


def test_the_watch_button_sits_beneath_the_start_button_and_the_field_beneath_both(display):
    menu = app.Menu()
    start, watching = menu.buttons[app.START], menu.buttons[app.WATCH]

    assert start.size == watching.size and start.centerx == watching.centerx == engine.SCREEN_WIDTH // 2
    assert start.bottom < watching.top
    assert watching.bottom < menu.field.top
    window = pygame.Rect(0, 0, engine.SCREEN_WIDTH, engine.WINDOW_HEIGHT)
    assert all(window.contains(rect) for rect in (start, watching, menu.field))
    assert menu.surface.get_size() == window.size


def test_each_option_s_label_fits_its_button(display):
    menu = app.Menu()
    for label, button in menu.buttons.items():
        width, height = menu.font.size(label)
        assert width < button.width - 2 * engine.WALL_THICKNESS and height < button.height, label


def test_the_buttons_are_drawn_green_and_the_field_white_outlined_in_black(display):
    menu = app.Menu()
    window = frame(menu)
    inside = (engine.WALL_THICKNESS, engine.WALL_THICKNESS)
    for rect, fill in (*((button, engine.GREEN) for button in menu.buttons.values()), (menu.field, engine.WHITE)):
        assert window.get_at(rect.topleft) == pygame.Color(engine.BLACK)
        assert window.get_at(rect.move(inside).topleft) == pygame.Color(fill)


def test_the_population_starts_at_the_learner_s_default(display):
    menu = app.Menu()
    assert menu.text == '300' and menu.population == evolve.DEFAULT_POPULATION == 300
    assert not menu.focused


def test_the_range_the_field_allows_is_the_learner_s_minimum_up_to_1000():
    assert (evolve.MIN_POPULATION, app.MAX_POPULATION) == (2, 1000)
    assert app.POPULATION_RANGE == '(2-1000)'
    evolve.Settings(population=app.MAX_POPULATION)
    with pytest.raises(ValueError, match='at least 2'):
        evolve.Settings(population=evolve.MIN_POPULATION - 1)


def typed(key, unicode=''):
    return pygame.event.Event(pygame.KEYDOWN, key=key, unicode=unicode)


def digit(character):
    return typed(ord(character), character)


@pytest.mark.parametrize('text, event, result', [
    ('24', digit('6'), '246'),
    ('', digit('0'), '0'),
    ('100', digit('0'), '1000'),
    ('1000', digit('5'), '1000'),
    ('9999', digit('1'), '9999'),
    ('246', typed(pygame.K_BACKSPACE, '\b'), '24'),
    ('', typed(pygame.K_BACKSPACE, '\b'), ''),
    ('24', typed(pygame.K_a, 'a'), '24'),
    ('24', typed(pygame.K_MINUS, '-'), '24'),
    ('24', typed(pygame.K_PERIOD, '.'), '24'),
    ('24', typed(pygame.K_SPACE, ' '), '24'),
    ('24', typed(pygame.K_LSHIFT), '24'),
    ('24', typed(pygame.K_KP6, '6'), '246'),
    ('24', typed(pygame.K_2, '\u00b2'), '24'),  # a superscript two is a digit to Python, not to the field
])
def test_type_into(text, event, result):
    assert app.type_into(text, event) == result


@pytest.mark.parametrize('text, population', [
    ('246', 246),
    ('2', 2),
    ('1000', 1000),
    ('1', 2),
    ('0', 2),
    ('0005', 5),
    ('1001', 1000),
    ('9999', 1000),
    ('', 300),
])
def test_population_from(text, population):
    assert app.population_from(text) == population


def type_text(menu, text):
    for character in text:
        menu.handle(digit(character))


def test_the_field_takes_typing_only_once_clicked_and_until_a_click_elsewhere(display):
    menu = app.Menu()
    type_text(menu, '5')
    assert menu.text == '300', 'typed into the field before it was clicked'

    assert menu.handle(click(menu.field)) is None
    assert menu.focused
    for _ in range(3):
        menu.handle(typed(pygame.K_BACKSPACE, '\b'))
    type_text(menu, '246')
    assert menu.text == '246' and menu.population == 246

    menu.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(5, 5), button=1))
    assert not menu.focused
    type_text(menu, '1')
    assert menu.text == '246'
    menu.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=menu.field.center, button=3))
    assert not menu.focused, 'a right click focused the field'


def test_enter_in_the_field_chooses_watching(display):
    menu = app.Menu()
    assert menu.handle(typed(pygame.K_RETURN, '\r')) is None, 'Enter chose watching with the field not focused'
    menu.handle(click(menu.field))
    assert menu.handle(typed(pygame.K_RETURN, '\r')) == app.WATCH
    assert menu.handle(typed(pygame.K_KP_ENTER, '\r')) == app.WATCH


def draw_differences(first, second):
    return [(x, y) for x in range(engine.SCREEN_WIDTH) for y in range(engine.WINDOW_HEIGHT)
            if first.get_at((x, y)) != second.get_at((x, y))]


def test_the_menu_draws_the_typed_number_centered_in_the_field(display):
    menu = app.Menu()
    shown = frame(menu)
    menu.text = '1000'
    longest = frame(menu)

    changed = draw_differences(shown, longest)
    assert changed and all(menu.field.collidepoint(point) for point in changed)
    inside = menu.field.inflate(-2 * engine.WALL_THICKNESS, -2 * engine.WALL_THICKNESS)
    for window in (shown, longest):
        number = ink(window, inside)
        assert abs(number.centerx - menu.field.centerx) <= 1 and abs(number.centery - menu.field.centery) <= 1


def field_ink(window, menu):
    '''Where anything but the field's white is drawn inside its outline.'''
    inside = menu.field.inflate(-2 * engine.WALL_THICKNESS, -2 * engine.WALL_THICKNESS)
    points = [(x, y) for x in range(inside.left, inside.right) for y in range(inside.top, inside.bottom)
              if window.get_at((x, y)) != pygame.Color(engine.WHITE)]
    xs, ys = zip(*points)
    return pygame.Rect(min(xs), min(ys), max(xs) - min(xs) + 1, max(ys) - min(ys) + 1)


def test_a_focused_field_shows_a_caret_after_the_number_or_centered_when_empty(display):
    menu = app.Menu()
    unfocused = frame(menu)
    menu.handle(click(menu.field))
    menu.text = '1000'
    number = field_ink(frame(menu), menu)
    menu.focused = False
    assert number.right > field_ink(frame(menu), menu).right + menu.CARET_GAP, 'no caret after the number'
    menu.focused = True
    inside = menu.field.inflate(-2 * engine.WALL_THICKNESS, -2 * engine.WALL_THICKNESS)
    assert inside.contains(number), 'the caret ran past the field'
    assert field_ink(unfocused, menu).centery - 1 <= number.centery <= field_ink(unfocused, menu).centery + 1

    menu.text = ''
    caret = field_ink(frame(menu), menu)
    assert caret.width == menu.CARET_WIDTH
    assert abs(caret.centerx - menu.field.centerx) <= 1 and abs(caret.centery - menu.field.centery) <= 1


def text_band(window, menu, left, right):
    '''The ink on the field's row between x `left` and `right`.'''
    return ink(window, pygame.Rect(left, menu.field.top, right - left, menu.field.height))


def test_the_field_s_label_and_range_sit_either_side_with_their_capitals_on_its_center_line(display):
    menu = app.Menu()
    window = frame(menu)
    label = text_band(window, menu, 0, menu.field.left)
    allowed = text_band(window, menu, menu.field.right, engine.SCREEN_WIDTH)
    # The label's first glyph is its capital C, up to the first column with no ink.
    right = label.left
    while ink(window, pygame.Rect(right, menu.field.top, 1, menu.field.height)):
        right += 1
    capital = ink(window, pygame.Rect(label.left, menu.field.top, right - label.left, menu.field.height))
    # The range's digits stand on the baseline without descenders, like the capitals.
    digits = text_band(window, menu, allowed.left + 12, allowed.right - 12)

    assert label.right < menu.field.left < menu.field.right < allowed.left
    assert menu.field.left - label.right == pytest.approx(allowed.left - menu.field.right, abs=4)
    assert abs(capital.centery - menu.field.centery) <= 1 and abs(digits.centery - menu.field.centery) <= 1
    assert abs((label.left + allowed.right) / 2 - engine.SCREEN_WIDTH / 2) <= 3


def test_start_game_plays_the_first_level_by_hand(display):
    game = app.Game(levels.LEVELS)
    game.handle(click(game.menu.buttons[app.START]))

    assert game.state is game.play and game.play.level is levels.LEVELS[0]
    assert game.watching is None


def test_esc_in_a_level_drops_the_game_and_goes_back_to_the_menu(display):
    game = app.Game(levels.LEVELS)
    game.handle(click(game.menu.buttons[app.START]))
    game.start_level(2)  # as if the first two were beaten, dying on the way
    game.play.deaths = 4

    game.handle(press(watch.MENU_KEY))
    assert game.state is game.menu and game.play is None and game.deaths == 0
    assert list(game.menu.buttons) == [app.START, app.WATCH]
    game.update(None)
    assert game.state is game.menu

    game.handle(click(game.menu.buttons[app.START]))
    assert game.state is game.play and game.play.level is levels.LEVELS[0]
    assert game.level_index == 0 and game.deaths == 0


def test_esc_on_the_win_screen_goes_back_to_the_menu(display):
    game = app.Game(levels.LEVELS)
    game.handle(click(game.menu.buttons[app.START]))
    game.state = game.won

    game.handle(press(watch.MENU_KEY))
    assert game.state is game.menu and game.play is None


def test_other_keys_in_a_level_stay_in_it(display):
    game = app.Game(levels.LEVELS)
    game.handle(click(game.menu.buttons[app.START]))
    for key in (pygame.K_BACKSPACE, pygame.K_RETURN, pygame.K_w):
        game.handle(press(key))
    assert game.state is game.play


def start_watching(game, text):
    '''Type `text` into the menu's field, then click Watch the AI beat the game.'''
    game.handle(click(game.menu.field))
    game.menu.text = ''
    for character in text:
        game.handle(pygame.event.Event(pygame.KEYDOWN, key=ord(character), unicode=character))
    game.handle(click(game.menu.buttons[app.WATCH]))


@pytest.fixture
def watching(display, capsys):
    '''A game on a small level, just switched from the menu, with 246 typed, to watching.'''
    game = app.Game([gate()])
    start_watching(game, '246')
    return game


def test_watch_trains_the_game_s_levels_with_the_menu_s_population(watching, capsys):
    shown = watching.state

    assert isinstance(shown, watch.Watch) and shown is watching.watching
    assert shown.levels == watching.levels and shown.level_index == 0
    assert shown.learner.settings == evolve.Settings(population=246)
    assert shown.learner.cap == evolve.DEFAULT_GENERATIONS
    assert shown.menu and shown.training
    [line] = capsys.readouterr().out.splitlines()
    assert line.startswith('Training on all 1 levels in turn: 246 characters a generation, seed ')


def test_the_game_runs_and_draws_the_watch_while_it_is_on(watching):
    shown = watching.watching
    watching.advance(None, 5)
    assert shown.runs.steps == 5
    watching.update(None)
    assert shown.runs.steps == 6

    assert frame(watching).get_view('2').raw == frame(shown).get_view('2').raw
    watching.handle(press(watch.FAST_KEY))
    assert shown.fast and watching.state is shown


def test_esc_goes_back_to_the_menu_and_the_menu_still_works(watching):
    watching.handle(press(watch.MENU_KEY))

    assert watching.state is watching.menu and watching.watching is None
    assert watching.menu.population == 246 and watching.menu.text == '246', 'the menu forgot the population chosen'
    watching.handle(click(watching.menu.buttons[app.START]))
    assert watching.state is watching.play


@pytest.mark.parametrize('text, population', [('1', 2), ('5000', 1000), ('', 300)])
def test_watch_starts_with_the_typed_population_held_in_range(display, capsys, text, population):
    game = app.Game([gate()])
    start_watching(game, text)

    assert game.watching.learner.settings.population == population
    game.handle(press(watch.MENU_KEY))
    assert game.menu.text == str(population), 'the field did not show the population watched'


def test_enter_in_the_field_starts_watching(display, capsys):
    game = app.Game([gate()])
    game.handle(click(game.menu.field))
    game.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_BACKSPACE, unicode='\b'))
    game.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, unicode='\r'))

    assert game.state is game.watching and game.watching.learner.settings.population == 30
    game.handle(press(watch.MENU_KEY))
    assert game.menu.text == '30' and not game.menu.focused


def test_a_watch_from_the_menu_says_how_to_go_back_at_the_top_right(watching):
    shown = watching.watching
    window = frame(watching)
    shown.menu = False
    plain = frame(watching)
    changed = [(x, y) for x in range(engine.SCREEN_WIDTH) for y in range(engine.WINDOW_HEIGHT)
               if window.get_at((x, y)) != plain.get_at((x, y))]
    xs, ys = zip(*changed)
    label = pygame.Rect(min(xs), min(ys), max(xs) - min(xs) + 1, max(ys) - min(ys) + 1)

    assert label.right == engine.SCREEN_WIDTH - engine.BAR_MARGIN
    # In the band above the play area, clear of the numbers however long they get.
    assert label.bottom <= engine.BAR_HEIGHT
    numbers = engine.BAR_MARGIN + shown.font.size(watch.readout(9, 9, 1000, 1000, 10_000))[0]
    assert label.left > numbers
    assert label.width == shown.hint_font.render(watch.MENU_HINT, True, engine.WHITE).get_bounding_rect().width
    # On the numbers' baseline, where their capitals end (the label has no descenders).
    capital = shown.font.render('L', True, engine.WHITE).get_bounding_rect()
    assert label.bottom == watch.READOUT_TOP + capital.bottom


def test_esc_does_nothing_in_a_watch_started_from_the_command_line(display):
    shown = watch.Watch([gate()], evolve.Settings(population=2), seed=1, cap=1)
    shown.handle(press(watch.MENU_KEY))

    assert shown.running
    top_right = pygame.Rect(640, 0, engine.SCREEN_WIDTH - 640, engine.BAR_HEIGHT)
    assert ink(frame(shown), top_right) is None


def test_a_watch_from_the_menu_beats_the_game_replays_it_and_goes_back(display, capsys):
    random.seed(3)  # the seed the menu's watch picks
    game = app.Game([gate(), gate()])
    start_watching(game, '25')
    shown = game.watching
    shown.hurry(math.inf)
    assert shown.learner.beaten and shown.replayed == 0
    assert shown.hint() == 'Replaying the whole game'

    game.advance(None, 10_000)
    assert shown.replayed == 1 and shown.runs.over
    assert shown.hint() == 'Every level beaten!   Q: quit'
    game.handle(press(watch.MENU_KEY))
    assert game.state is game.menu
