import pygame

# constants
SCREEN_LEN = 981
SCREEN_WID = 574
FPS = 120
PLAYER_SPEED = 2

# colors
BACKGROUND = '#aaa5ff'
RED = '#ff0000'
BLACK = '#000000'
GREEN = '#9ef29b'
WHITE = '#FFFFFF'

def can_move(future_pos, lines):
    for line in lines:
        if future_pos.clipline(line):
            return False
    return True

def move_player(player, dx, dy, lines):
    if dx != 0:
        future_pos = player.copy()
        future_pos.x += dx
        if can_move(future_pos, lines):
            player.x += dx

    if dy != 0:
        future_pos = player.copy()
        future_pos.y += dy
        if can_move(future_pos, lines):
            player.y += dy

black_borders = [
    ((117, 159), (240, 159)),
    ((117, 158), (117, 407)),
    ((117, 406), (323, 406)),
    ((322, 406), (322, 365)),
    ((322, 365), (696, 365)),
    ((695, 365), (695, 201)),
    ((694, 200), (736, 200)),
    ((735, 200), (735, 407)),
    ((735, 406), (861, 406)),
    ((860, 405), (860, 160)),
    ((860, 160), (654, 160)),
    ((654, 159), (654, 200)),
    ((654, 199), (281, 199)),
    ((281, 199), (281, 365)),
    ((284, 366), (240, 366)),
    ((240, 369), (240, 158)),
]

red_borders = [
    ((117, 159), (240, 159)),
    ((117, 158), (117, 407)),
    ((117, 406), (323, 406)),
    ((322, 406), (322, 365)),
    ((322, 365), (696, 365)),
    ((695, 365), (695, 202)),
    ((697, 200), (733, 200)),
    ((735, 200), (735, 407)),
    ((735, 406), (861, 406)),
    ((860, 405), (860, 160)),
    ((860, 160), (654, 160)),
    ((654, 159), (654, 200)),
    ((654, 199), (281, 199)),
    ((281, 199), (281, 365)),
    ((284, 366), (240, 366)),
    ((240, 369), (240, 158)),

]


def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_LEN, SCREEN_WID))
    clock = pygame.time.Clock()
    player = pygame.Rect(166, 271, 23, 25)
    running = True
    coords = []

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.MOUSEBUTTONDOWN:
                x, y = pygame.mouse.get_pos()
                coords.append((x, y))
                print(coords)

        dx = dy = 0
        keys = pygame.key.get_pressed()
        if keys[pygame.K_w]:
            dy -= PLAYER_SPEED
        if keys[pygame.K_s]:
            dy += PLAYER_SPEED
        if keys[pygame.K_a]:
            dx -= PLAYER_SPEED
        if keys[pygame.K_d]:
            dx += PLAYER_SPEED

        move_player(player, dx, dy, red_borders)


        screen.fill(BACKGROUND)
        for line in black_borders:
            pygame.draw.line(screen, BLACK, line[0], line[1], 6)
        # for line in red_borders:
        #     pygame.draw.line(screen, RED, line[0], line[1])
        pygame.draw.rect(screen, RED, player)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()


if __name__ == '__main__':
    main()


