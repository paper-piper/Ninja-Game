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
sprite_sheet_path = r'Images/Walk.png'

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
    def __init__(self, x, y, width, height, speed, sprite_sheet_path):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.speed = speed
        self.rect = pygame.Rect(x, y, width, height)
        self.direction = 'down'  # Initial direction
        self.anim_frame = 0
        self.anim_speed = 10  # Number of frames to wait before switching animation frames
        self.anim_count = 0  # Counter to track animation speed
        self.sprites = {}  # Initialize the sprites dictionary
        self.load_sprites(sprite_sheet_path)

    def load_sprites(self, sprite_sheet_path):
        sprite_sheet = pygame.image.load(sprite_sheet_path).convert_alpha()
        directions = ['down', 'up', 'left', 'right']  # Assuming this order in columns
        self.sprites = {direction: [] for direction in directions}
        for col, direction in enumerate(directions):
            for row in range(4):  # Assuming 4 frames per direction
                frame = sprite_sheet.subsurface(col * self.width, row * self.height, self.width, self.height)
                self.sprites[direction].append(frame)

    def draw(self, camera):
        frame = self.sprites[self.direction][self.anim_frame]
        screen.blit(frame, camera.apply(self))

    def move(self, keys, camera):
        dx = dy = 0
        if keys[pygame.K_a]:
            dx = -self.speed
            self.direction = 'left'
        if keys[pygame.K_d]:
            dx = self.speed
            self.direction = 'right'
        if keys[pygame.K_w]:
            dy = -self.speed
            self.direction = 'up'
        if keys[pygame.K_s]:
            dy = self.speed
            self.direction = 'down'

        if dx != 0 or dy != 0:
            self.anim_count += 1
            if self.anim_count >= self.anim_speed:
                self.anim_frame = (self.anim_frame + 1) % 4
                self.anim_count = 0  # Reset counter after updating frame
        else:
            self.anim_frame = 0  # Reset to first frame if not moving
            self.anim_count = 0  # Reset counter when player stops

        # Check collision before actual move
        if check_collision(self.x + dx, self.y + dy):
            self.x += dx
            self.y += dy

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
        if check_collision(self.x + self.dx, self.y + self.dy):
            self.x += self.dx
            self.y += self.dy
        else:
            return True
        self.rect.x = self.x - self.radius
        self.rect.y = self.y - self.radius
        return False

    def draw(self, camera):
        pygame.draw.circle(screen, (0, 0, 0), camera.apply(self).center, self.radius)


class Target:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.rect = pygame.Rect(x, y, target_image.get_width(), target_image.get_height())

    def draw(self, camera):
        screen.blit(target_image, camera.apply(self))


class Menu:
    def __init__(self, screen):
        self.screen = screen
        self.screen_width = screen.get_width()
        self.screen_height = screen.get_height()

    def display_main_menu(self):
        menu = True
        while menu:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    quit()
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        menu = False
            self.screen.fill((255, 255, 255))
            font = pygame.font.SysFont(None, 48)
            text = font.render("Press Enter to Start", True, (0, 0, 0))
            self.screen.blit(text, (self.screen_width // 2 - text.get_width() // 2, self.screen_height // 2 - text.get_height() // 2))
            pygame.display.flip()
            pygame.time.Clock().tick(60)


class Game:
    def __init__(self, screen):
        self.screen = screen
        self.bullets = []
        self.targets = [Target(100, 100), Target(350, 200), Target(600, 150)]
        self.map_width, self.map_height = get_image_dimensions(map_image_path)
        self.camera = Camera(self.map_width, self.map_height)

        with Image.open(sprite_sheet_path) as img:
            frame_width, frame_height = img.size[0] // 4, img.size[1] // 4  # Assuming 4 frames per direction

        self.player = Player(
            x=screen_width // 2,
            y=screen_height - 40 - frame_height // 2,
            width=frame_width,
            height=frame_height,
            speed=player_speed,
            sprite_sheet_path=sprite_sheet_path
        )

    def run(self):
        running = True
        while running:
            running = self.handle_events()
            keys = pygame.key.get_pressed()
            self.update_game_objects(keys)
            self.check_collisions()
            self.draw_game_objects()
            pygame.display.flip()
            pygame.time.Clock().tick(60)

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.player.shoot(self.camera, self.bullets)
        return True

    def update_game_objects(self, keys):
        self.player.move(keys, self.camera)
        self.camera.update(self.player)
        for bullet in self.bullets[:]:
            if bullet.move():
                self.bullets.remove(bullet)  # remove collided bullets
            elif bullet.x < 0 or bullet.x > self.camera.width or bullet.y < 0 or bullet.y > self.camera.height:
                self.bullets.remove(bullet)  # remove off-screen bullets

    def check_collisions(self):
        for target in self.targets[:]:
            target_rect = pygame.Rect(target.x, target.y, target_image.get_width(), target_image.get_height())
            for bullet in self.bullets:
                if target_rect.collidepoint(bullet.x, bullet.y):
                    self.targets.remove(target)
                    self.bullets.remove(bullet)
                    break

    def draw_game_objects(self):
        self.screen.fill((255, 255, 255))
        self.screen.blit(map_image, (self.camera.camera.x, self.camera.camera.y))
        self.player.draw(self.camera)
        for bullet in self.bullets:
            bullet.draw(self.camera)
        for target in self.targets:
            target.draw(self.camera)


def get_image_dimensions(image_path):
    with Image.open(image_path) as img:
        width, height = img.size
    return width, height


def check_collision(x, y):
    try:
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
    except IndexError as i:
        return False


if __name__ == "__main__":
    pygame.init()
    screen = pygame.display.set_mode((screen_width, screen_height))
    pygame.display.set_caption("Ninja Game")

    menu = Menu(screen)
    menu.display_main_menu()

    game = Game(screen)
    game.run()
