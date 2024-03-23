import pygame
import math
from PIL import Image

# Initialize Pygame
pygame.init()

# Set up the display
screen_width = 800
screen_height = 600
screen = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption("Tank Game")

# Images paths
player_image_path = r'Images/MiniGoose.png'
target_image_path = r'Images/target.png'
map_image_path = r'Images/GooseMapBig.jpg'
collision_image_path = r'Images/CollisionMap.jpg'

# Load images
player_image = pygame.image.load(player_image_path).convert_alpha()
target_image = pygame.image.load(target_image_path).convert_alpha()
map_image = pygame.image.load(map_image_path).convert_alpha()
collision_map = pygame.image.load(collision_image_path).convert_alpha()


# player qualities
player_speed = 5


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


class Player:
    def __init__(self, x, y, width, height, speed):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.speed = speed
        self.rect = pygame.Rect(x, y, width, height)

    def draw(self, camera):
        screen.blit(player_image, camera.apply(self))

    def move(self, keys, camera):
        if keys[pygame.K_a]:
            self.x = max(0, self.x - self.speed)
        if keys[pygame.K_d]:
            self.x = min(camera.width - self.width, self.x + self.speed)
        if keys[pygame.K_w]:
            self.y = max(0, self.y - self.speed)
        if keys[pygame.K_s]:
            self.y = min(camera.height - self.height, self.y + self.speed)

        self.rect.x = self.x
        self.rect.y = self.y

    def shoot(self, camera, bullets):
        # Get the mouse position on the screen
        mx, my = pygame.mouse.get_pos()

        # Adjust the mouse coordinates based on the camera's offset
        # Since the camera's x and y represent the top-left corner of the view,
        # you need to add these values to get the correct world position of the mouse
        world_mx = mx - camera.camera.x
        world_my = my - camera.camera.y

        # Calculate the center position of the player
        center_x = self.x + self.width // 2
        center_y = self.y + self.height // 2

        # Calculate the angle between the player's center and the mouse position in the world
        angle = math.atan2(world_my - center_y, world_mx - center_x)

        # Calculate the bullet's direction vector based on the angle
        dx = math.cos(angle) * 10  # Speed of the bullet
        dy = math.sin(angle) * 10  # Speed of the bullet

        # Create and add the new bullet to the bullets list
        bullets.append(Bullet(center_x, center_y, dx, dy, 5))


class Bullet:
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


def handle_events(player, bullets, camera):
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            return False
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            player.shoot(camera, bullets)
    return True


def update_game_objects(player, bullets, camera, keys):
    player.move(keys, camera)
    camera.update(player)
    for bullet in bullets[:]:
        bullet.move()
        if bullet.x < 0 or bullet.x > camera.width or bullet.y < 0 or bullet.y > camera.height:
            bullets.remove(bullet)  # Remove off-screen bullets


def check_collisions(bullets, targets):
    targets_destroyed = 0
    for target in targets[:]:
        target_rect = pygame.Rect(target.x, target.y, target_image.get_width(), target_image.get_height())
        for bullet in bullets:
            if target_rect.collidepoint(bullet.x, bullet.y):
                targets.remove(target)
                bullets.remove(bullet)
                targets_destroyed += 1
                break
    return targets_destroyed


def draw_game_objects(player, bullets, targets, camera):
    screen.fill((255, 255, 255))
    screen.blit(map_image, (camera.camera.x, camera.camera.y))  # Draw the map
    player.draw(camera)
    for bullet in bullets:
        bullet.draw(camera)
    for target in targets:
        target.draw(camera)


def get_image_dimensions(image_path):
    with Image.open(image_path) as img:
        width, height = img.size
    return width, height


def check_collision(x, y):
    # Convert the floating point x and y to integers for pixel checking
    int_x = int(x)
    int_y = int(y)

    # Get the color of the pixel at the (x, y) position of the collision map
    pixel_color = collision_map.get_at((int_x, int_y))

    # Extract the RGB components of the pixel color
    red, green, blue = pixel_color[:3]

    # Define the color that represents collidable areas (e.g., white)
    collidable_color = (255, 255, 255)

    # Check if the pixel color matches the collidable color
    is_colliding = (red, green, blue) == collidable_color

    return is_colliding


def game_loop():
    player_width, player_height = get_image_dimensions(player_image_path)
    tank = Player(screen_width // 2, screen_height - 40 - 10, player_width, player_height, player_speed)
    bullets = []
    targets = [Target(100, 100), Target(350, 200), Target(600, 150)]
    targets_destroyed = 0

    map_width, map_height = get_image_dimensions(map_image_path)
    camera = Camera(map_width, map_height)

    running = True
    while running:
        running = handle_events(tank, bullets, camera)
        keys = pygame.key.get_pressed()
        update_game_objects(tank, bullets, camera, keys)
        targets_destroyed += check_collisions(bullets, targets)
        draw_game_objects(tank, bullets, targets, camera)

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
