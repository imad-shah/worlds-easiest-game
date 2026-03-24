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
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.color = color
        self.border_color = border_color
        self.border_width = border_width
    
    def draw(self, screen):
        rect = (self.x, self.y, self.width, self.height)
        pygame.draw.rect(screen, self.color, rect)
        pygame.draw.rect(screen, self.border_color, rect, self.border_width)

    def contains_rec(self, other):
        return (
            other.x >= self.x and
            other.y >= self.y and
            other.x + other.width <= self.x + self.width and
            other.y + other.height <= self.y + self.height
        )


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

        speed = 2
        dx = dy = 0
        keys = pygame.key.get_pressed()
        if keys[pygame.K_w]:
            dy -= speed
        if keys[pygame.K_s]:
            dy += speed
        if keys[pygame.K_a]:
            dx -= speed
        if keys[pygame.K_d]:
            dx += speed

        if dx != 0:
            future_pos = Rectangle(player.x + dx, player.y, player.width, player.height, player.color)
            for rec in rectangles:
                if rec.contains_rec(future_pos):
                    player.x += dx

        if dy != 0:
            future_pos = Rectangle(player.x, player.y + dy, player.width, player.height, player.color)
            for rec in rectangles:
                if rec.contains_rec(future_pos):
                    player.y += dy

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    
if __name__ == '__main__':
    main()
