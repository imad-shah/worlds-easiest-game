import pygame

# display
SCREEN_LEN = 1097
SCREEN_WID = 744
FPS = 120

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
        pygame.draw.rect(screen, self.border_color, self.rect, self.border_width)


def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_LEN, SCREEN_WID))
    clock = pygame.time.Clock()
    running = True
    player = Rectangle(175, 275, 40, 40, RED)
    rectangles = [
        Rectangle(120, 160, 150, 265, GREEN), # left green
        Rectangle(742, 160, 150, 265, GREEN), # right green
        Rectangle(315, 198, 385, 187, WHITE), # middle screen
    ]

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
        
        screen.fill(BACKGROUND)
        for rect in rectangles:
            rect.draw(screen)
        player.draw(screen)
        keys = pygame.key.get_pressed()
        if keys[pygame.K_w]:
            player.rect.y -= 2
        if keys[pygame.K_s]:
            player.rect.y += 2
        if keys[pygame.K_a]:
            player.rect.x -= 2
        if keys[pygame.K_d]:
            player.rect.x += 2

        print(pygame.mouse.get_pos())
        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    
if __name__ == '__main__':
    main()