import pygame

'''
currently: using the actual borders as the visual borders, which leads 
to sprite getting stuck on 1 frame edges

instead: 

1) should draw the borders in a discernable color like red,
2) hide them once complete
3) then draw the visual borders over the real borders using old method of drawing the square again
with the dark outline, width ~6


'''

# display
SCREEN_LEN = 1097
SCREEN_WID = 744
FPS = 120
PLAYER_SPEED = 2

# colors
BACKGROUND = '#aaa5ff'
RED = '#ff0000'
BLACK = '#000000'
GREEN = '#9ef29b'
WHITE = '#FFFFFF'


class Rectangle:
    def __init__(self, x: int, y: int, width: int, height: int, color: str, border_color=BLACK, border_width=6):
        self.rect = pygame.Rect(x, y, width, height)
        self.color = color
        self.border_color = border_color
        self.border_width = border_width
        
    
    def draw(self, screen):
        pygame.draw.rect(screen, self.color, self.rect)
        # pygame.draw.rect(screen, self.border_color, self.rect, self.border_width)

    
def can_move(future_pos, lines):
    for line in lines:
        if future_pos.clipline(line):
            return False
    return True

def move_player(player, dx, dy, zones):
    if dx != 0:
        future_pos = player.rect.copy()
        future_pos.x += dx
        if can_move(future_pos, zones):
            player.rect.x += dx

    if dy != 0:
        future_pos = player.rect.copy()
        future_pos.y += dy
        if can_move(future_pos, zones):
            player.rect.y += dy


def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_LEN, SCREEN_WID))
    clock = pygame.time.Clock()
    running = True
    player = Rectangle(175, 275, 40, 40, RED)
    zones = [
        Rectangle(120, 160, 150, 265, GREEN), # left green
        Rectangle(742, 160, 150, 265, GREEN), # right green
        Rectangle(315, 205, 385, 187, WHITE), # middle screen
        Rectangle(271, 367, 120, 51, WHITE, WHITE, 6) # working on connection (left)
    ]
    lines = [
        # starting square level one
        ((120, 161), (120, 423)), # left
        ((119, 161), (270, 161)), # up
        ((270, 159), (270, 367)), # right
        ((119, 421), (390, 421)), # bottom

        # connection from start square bottom to middle square bottom
        ((390, 424), (390, 390)),

        # middle square 
        ((390, 392), (699, 392)), # bottom

        # connection from starting square right to middle square
        ((268, 369), (315, 369)),
    ]

    while running:
        coords = []
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

        move_player(player, dx, dy, lines)

        screen.fill(BACKGROUND)
        for zone in zones:
            zone.draw(screen)
        for line in lines:
            pygame.draw.line(screen, BLACK, line[0], line[1], 6)
        player.draw(screen)
        

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    
if __name__ == '__main__':
    main()
