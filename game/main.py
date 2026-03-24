import pygame

# later for refactoring
class Border:
    def __init__(self, top: int, left: int, length: int, width: int):
        pass


def main():
    pygame.init()
    SCREEN_LEN = 1097
    SCREEN_WID = 744
    screen = pygame.display.set_mode((SCREEN_LEN, SCREEN_WID))
    clock = pygame.time.Clock()
    running = True
    BACKGROUND = '#aaa5ff'
    RED = '#ff0000'
    BLACK = '#000000'
    GREEN = '#9ef29b'
    FPS = 120
    player = pygame.Rect(200, 350, 40, 40)

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
        
        screen.fill(BACKGROUND)
        first_rect = pygame.Rect(120, 160, 150, 265)
        pygame.draw.rect(screen, GREEN, first_rect)
        pygame.draw.rect(screen, BLACK, first_rect, 6)

        pygame.draw.rect(screen, RED, player)

        # draws the rectangle and colors interior red
        pygame.draw.rect(screen, RED, player)
        # draws the outline for the red rectangle
        outline_width = 6
        pygame.draw.rect(screen, BLACK, player, outline_width) 

        keys = pygame.key.get_pressed()
        if keys[pygame.K_w]:
            player.y -= 2
        if keys[pygame.K_s]:
            player.y += 2
        if keys[pygame.K_a]:
            player.x -= 2
        if keys[pygame.K_d]:
            player.x += 2

        # iteration 1 uses clamp_ip but this wont work because the player needs to be able to leave the starting area
        # instead, need to calculate all pixels and block them except an escape hole
        player.clamp_ip(first_rect)
        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    
if __name__ == '__main__':
    main()