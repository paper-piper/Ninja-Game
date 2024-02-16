import pygame
import math

# Initialize Pygame
pygame.init()

# Set up the display
screen_width = 800
screen_height = 600
screen = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption("Tank Game")

# Load images
tank_image = pygame.image.load(r'C:\Users\yonat\PycharmProjects\LearningPyGame\Images\tank_model.jpg').convert_alpha()
target_image = pygame.image.load(r'C:\Users\yonat\PycharmProjects\LearningPyGame\Images\taget.jpg').convert_alpha()

# Set up the tank
tank_width = 40
tank_height = 20
tank_x = screen_width // 2
tank_y = screen_height - tank_height - 10
tank_speed = 5

# Set up the cannonball
cannonball_radius = 5
cannonball_speed = 10
cannonballs = []

# Set up the target
targets = [(100, 100), (350, 200), (600, 150)]
targets_destroyed = 0


def main_menu():
    menu = True
    while menu:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                quit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    menu = False
        screen.fill((255, 255, 255))
        font = pygame.font.SysFont(None, 48)
        text = font.render("Press Enter to Start", True, (0, 0, 0))
        screen.blit(text, (screen_width // 2 - text.get_width() // 2, screen_height // 2 - text.get_height() // 2))
        pygame.display.flip()
        pygame.time.Clock().tick(60)


def game_loop():
    global tank_x, tank_y, targets_destroyed
    running = True
    while running:
        # Handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # Shoot a cannonball
                mx, my = pygame.mouse.get_pos()
                angle = math.atan2(my - tank_y, mx - tank_x)
                dx = math.cos(angle) * cannonball_speed
                dy = math.sin(angle) * cannonball_speed
                cannonballs.append([tank_x + tank_width // 2, tank_y, dx, dy])

        # Handle keys
        keys = pygame.key.get_pressed()
        if keys[pygame.K_a]:
            tank_x -= tank_speed
        if keys[pygame.K_d]:
            tank_x += tank_speed
        if keys[pygame.K_w]:
            tank_y -= tank_speed
        if keys[pygame.K_s]:
            tank_y += tank_speed

        # Update cannonballs
        for cannonball in cannonballs:
            cannonball[0] += cannonball[2]  # Move the cannonball
            cannonball[1] += cannonball[3]
            if cannonball[0] < 0 or cannonball[0] > screen_width or cannonball[1] < 0 or cannonball[1] > screen_height:
                cannonballs.remove(cannonball)  # Remove off-screen cannonballs

        # Check for collisions
        for target in targets[:]:
            target_rect = pygame.Rect(target[0], target[1], target_image.get_width(), target_image.get_height())
            for cannonball in cannonballs:
                if target_rect.collidepoint(cannonball[0], cannonball[1]):
                    targets.remove(target)
                    cannonballs.remove(cannonball)
                    targets_destroyed += 1
                    break

        # Draw everything
        screen.fill((255, 255, 255))
        screen.blit(tank_image, (tank_x, tank_y))
        for cannonball in cannonballs:
            pygame.draw.circle(screen, (0, 0, 0), (int(cannonball[0]), int(cannonball[1])), cannonball_radius)
        for target in targets:
            screen.blit(target_image, target)

        # Check for game over
        if targets_destroyed == 3:
            font = pygame.font.SysFont(None, 48)
            text = font.render("You Win!", True, (0, 0, 0))
            screen.blit(text, (screen_width // 2 - text.get_width() // 2, screen_height // 2 - text.get_height() // 2))

        pygame.display.flip()
        pygame.time.Clock().tick(60)

    pygame.quit()


if __name__ == "__main__":
    main_menu()
    game_loop()
