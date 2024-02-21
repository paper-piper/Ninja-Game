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
tank_image = pygame.image.load(r'Images/TankModel.png').convert_alpha()
target_image = pygame.image.load(r'Images/target.png').convert_alpha()
map_image = pygame.image.load(r'Images/map.jpg').convert_alpha()


class Camera:
    def __init__(self, width, height):
        self.camera = pygame.Rect(0, 0, width, height)
        self.width = width
        self.height = height

    def apply(self, entity):
        return entity.rect.move(self.camera.topleft)

    def update(self, target):
        x = -target.rect.x + int(screen_width / 2)
        y = -target.rect.y + int(screen_height / 2)

        # limit scrolling to map size
        x = min(0, x)  # left
        y = min(0, y)  # top
        x = max(-(self.width - screen_width), x)  # right
        y = max(-(self.height - screen_height), y)  # bottom

        self.camera = pygame.Rect(x, y, self.width, self.height)


class Tank:
    def __init__(self, x, y, width, height, speed):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.speed = speed
        self.rect = pygame.Rect(x, y, width, height)

    def draw(self, camera):
        screen.blit(tank_image, camera.apply(self))

    def move(self, keys):
        if keys[pygame.K_a]:
            self.x -= self.speed
        if keys[pygame.K_d]:
            self.x += self.speed
        if keys[pygame.K_w]:
            self.y -= self.speed
        if keys[pygame.K_s]:
            self.y += self.speed
        self.rect.x = self.x
        self.rect.y = self.y


class Cannonball:
    def __init__(self, x, y, dx, dy, radius):
        self.x = x
        self.y = y
        self.dx = dx
        self.dy = dy
        self.radius = radius
        self.rect = pygame.Rect(x - radius, y - radius, radius * 2, radius * 2)

    def move(self):
        self.x += self.dx
        self.y += self.dy
        self.rect.x = self.x - self.radius
        self.rect.y = self.y - self.radius

    def draw(self, camera):
        pygame.draw.circle(screen, (0, 0, 0), camera.apply(self).center, self.radius)


class Target:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.rect = pygame.Rect(x, y, target_image.get_width(), target_image.get_height())

    def draw(self, camera):
        screen.blit(target_image, camera.apply(self))


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


def handle_events(tank, cannonballs, camera):
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            return False
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Shoot a cannonball
            mx, my = pygame.mouse.get_pos()
            mx += camera.camera.x
            my += camera.camera.y
            angle = math.atan2(my - tank.y, mx - tank.x)
            dx = math.cos(angle) * 10
            dy = math.sin(angle) * 10
            cannonballs.append(Cannonball(tank.x + tank.width // 2, tank.y, dx, dy, 5))
    return True


def update_game_objects(tank, cannonballs, camera, keys):
    tank.move(keys)
    camera.update(tank)
    for cannonball in cannonballs[:]:
        cannonball.move()
        if cannonball.x < 0 or cannonball.x > camera.width or cannonball.y < 0 or cannonball.y > camera.height:
            cannonballs.remove(cannonball)  # Remove off-screen cannonballs


def check_collisions(cannonballs, targets):
    targets_destroyed = 0
    for target in targets[:]:
        target_rect = pygame.Rect(target.x, target.y, target_image.get_width(), target_image.get_height())
        for cannonball in cannonballs:
            if target_rect.collidepoint(cannonball.x, cannonball.y):
                targets.remove(target)
                cannonballs.remove(cannonball)
                targets_destroyed += 1
                break
    return targets_destroyed


def draw_game_objects(tank, cannonballs, targets, camera):
    screen.fill((255, 255, 255))
    screen.blit(map_image, (camera.camera.x, camera.camera.y))  # Draw the map
    tank.draw(camera)
    for cannonball in cannonballs:
        cannonball.draw(camera)
    for target in targets:
        target.draw(camera)


def game_loop():
    tank = Tank(screen_width // 2, screen_height - 40 - 10, 40, 20, 5)
    cannonballs = []
    targets = [Target(100, 100), Target(350, 200), Target(600, 150)]
    targets_destroyed = 0

    camera = Camera(1000, 1000)  # Assuming the map size is 1000x1000

    running = True
    while running:
        running = handle_events(tank, cannonballs, camera)
        keys = pygame.key.get_pressed()
        update_game_objects(tank, cannonballs, camera, keys)
        targets_destroyed += check_collisions(cannonballs, targets)
        draw_game_objects(tank, cannonballs, targets, camera)

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
