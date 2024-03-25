import pygame
from PIL import Image
import random
import math
import json

# Initialize Pygame
pygame.init()

# Set up the display
game_width = 400
game_height = 300
screen_width = 1200
screen_height = 900

screen = pygame.display.set_mode((screen_width, screen_height))
game_surface = pygame.Surface((game_width, game_height))
pygame.display.set_caption("Tank Game")

# Images paths
map_image_path = r'Images/Map/ScaledMap.png'
collision_image_path = r'Images/Map/ScaledCollision.png'

# Load images
map_image = pygame.image.load(map_image_path).convert_alpha()
collision_map = pygame.image.load(collision_image_path).convert_alpha()


# character qualities
CHARACTER_STATS_FILE_PATH = r"Characters.json"

# default player qualities
player_speed = 4


class Character:
    def __init__(self, name, hp, speed, bullet_speed, bullet_image):
        self.name = name
        self.hp = hp
        self.speed = speed
        self.bullet_speed = bullet_speed
        self.bullet_image = bullet_image
        self.sprites = self.load_sprites(name)
        self.faceset = pygame.image.load(f'Images/Characters/{name}/Faceset.png').convert_alpha()

    def load_sprites(self, name):
        sprite_sheet = pygame.image.load(f'Images/Characters/{name}/SeparateAnim/Walk.png').convert_alpha()
        sprites = {
            'down': [],
            'up': [],
            'left': [],
            'right': []
        }
        sprite_size = 16  # Size of each sprite frame, assuming the whole sheet is 64x64 and divided into 4x4
        frames_per_direction = 4  # Assuming there are 4 frames per direction

        for col in range(frames_per_direction):  # 4 columns for each direction
            for row, direction in enumerate(sprites.keys()):  # 4 rows, each representing a direction
                frame = sprite_sheet.subsurface(col * sprite_size, row * sprite_size, sprite_size, sprite_size)
                sprites[direction].append(frame)

        return sprites


class Camera:
    def __init__(self, width, height):
        self.camera = pygame.Rect(0, 0, width, height)
        self.width = width
        self.height = height

    def apply(self, entity):
        return entity.rect.move(self.camera.topleft)

    def update(self, target):
        x = -target.rect.x + int(game_width / 2)
        y = -target.rect.y + int(game_height / 2)

        # limit scrolling to map size
        x = min(0, x)  # left
        y = min(0, y)  # top
        x = max(-(self.width - game_width), x)  # right
        y = max(-(self.height - game_height), y)  # bottom

        self.camera = pygame.Rect(x, y, self.width, self.height)


class Player:
    def __init__(self, character, x, y, width, height):
        # game qualities
        self.x = x
        self.y = y
        self.width = width
        self.height = height

        # default qualities
        self.bullets = []  # Store bullets for each player
        self.rect = pygame.Rect(x, y, width, height)
        self.direction = 'down'  # Initial direction
        self.anim_frame = 0
        self.anim_speed = 10  # Number of frames to wait before switching animation frames
        self.anim_count = 0  # Counter to track animation speed

        # character qualities
        self.speed = character.speed
        self.hp = character.hp
        self.bullet_speed = character.bullet_speed
        self.sprites = character.sprites

    def draw(self, camera, surface):
        frame = self.sprites[self.direction][self.anim_frame]
        surface.blit(frame, camera.apply(self))

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
        if check_collision(self.x + dx, self.y + dy, self.width, self.height):
            self.x += dx
            self.y += dy

        self.rect.x = self.x
        self.rect.y = self.y

    def shoot(self, camera):
        # Get the mouse position on the screen
        mx, my = pygame.mouse.get_pos()

        logical_mx = mx * (game_width / screen_width)
        logical_my = my * (game_height / screen_height)
        # Adjust the mouse coordinates based on the camera's offset
        # Since the camera's x and y represent the top-left corner of the view,
        # you need to add these values to get the correct world position of the mouse
        world_mx = logical_mx - camera.camera.x
        world_my = logical_my - camera.camera.y

        # Calculate the center position of the player
        center_x = self.x + self.width // 2
        center_y = self.y + self.height // 2

        # Calculate the angle between the player's center and the mouse position in the world
        angle = math.atan2(world_my - center_y, world_mx - center_x)

        # Calculate the bullet's direction vector based on the angle
        dx = math.cos(angle) * self.bullet_speed  # Speed of the bullet
        dy = math.sin(angle) * self.bullet_speed  # Speed of the bullet

        # Create and add the new bullet to the bullets list
        self.bullets.append(Bullet(center_x, center_y, dx, dy, 1, self))

    def take_damage(self, damage):
        self.hp -= damage
        if self.hp <= 0:
            self.hp = 0
            # Handle player death here if needed


class AIPlayer(Player):
    def __init__(self, character, x, y, width, height, target_player):
        super().__init__(character, x, y, width, height)
        self.target_player = target_player
        self.shoot_distance = 250  # Distance at which AI starts shooting

    def move(self, camera):
        dx, dy = 0, 0

        # Calculate distance to the target player
        distance_x = self.target_player.x - self.x
        distance_y = self.target_player.y - self.y
        distance = math.hypot(distance_x, distance_y)

        # Move towards or away from the player to maintain a strategic distance
        if distance > self.shoot_distance:
            dx = self.speed if distance_x > 0 else -self.speed
            dy = self.speed if distance_y > 0 else -self.speed
        elif distance < self.shoot_distance - 50:  # Buffer for too close
            dx = -self.speed if distance_x > 0 else self.speed
            dy = -self.speed if distance_y > 0 else self.speed

        # Randomly avoid getting hit (simple dodge behavior)
        if random.random() < 0.1:
            dx = -dx
            dy = -dy

        # Update the direction based on movement
        if abs(distance_x) > abs(distance_y):
            self.direction = 'right' if dx > 0 else 'left'
        else:
            self.direction = 'up' if dy < 0 else 'down'

        # Update position and animation
        if dx != 0 or dy != 0:
            if check_collision(self.x + dx, self.y + dy, self.width, self.height):
                self.x += dx
                self.y += dy
            self.update_animation()

        self.rect.x = self.x
        self.rect.y = self.y

    def update_animation(self):
        self.anim_count += 1
        if self.anim_count >= self.anim_speed:
            self.anim_frame = (self.anim_frame + 1) % 4
            self.anim_count = 0
        else:
            self.anim_frame = 0
            self.anim_count = 0

    def shoot_at_player(self):
        if math.hypot(self.target_player.x - self.x, self.target_player.y - self.y) <= self.shoot_distance:
            angle = math.atan2(self.target_player.y - self.y, self.target_player.x - self.x)
            dx = math.cos(angle) * self.bullet_speed
            dy = math.sin(angle) * self.bullet_speed
            self.bullets.append(Bullet(self.x + self.width // 2, self.y + self.height // 2, dx, dy, 3, self))

    def random_action(self):
        if random.random() < 0.02:  # Chance to shoot at player
            self.shoot_at_player()


class Bullet:
    def __init__(self, x, y, dx, dy, radius, owner, image=None):
        self.x = x
        self.y = y
        self.dx = dx
        self.dy = dy
        self.radius = radius
        self.owner = owner
        self.image = image or pygame.Surface((radius*2, radius*2), pygame.SRCALPHA)
        pygame.draw.circle(self.image, (0, 0, 0), (radius, radius), radius)
        self.rect = pygame.Rect(x - radius, y - radius, radius * 2, radius * 2)

    def move(self):
        if check_collision(int(self.x + self.dx), int(self.y + self.dy), int(self.radius), int(self.radius)):
            self.x += self.dx
            self.y += self.dy
        else:
            return True
        self.rect.x = self.x - self.radius
        self.rect.y = self.y - self.radius
        return False

    def draw(self, camera, surface):
        if self.image:
            surface.blit(self.image, camera.apply(self).topleft)
        else:
            pygame.draw.circle(surface, (0, 0, 0), camera.apply(self).center, self.radius)


class Menu:
    def __init__(self, screen):
        self.screen = screen
        self.screen_width = screen.get_width()
        self.screen_height = screen.get_height()

    def display_main_menu(self):
        continue_menu = True
        while continue_menu:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    quit()
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        continue_menu = False
            self.screen.fill((255, 255, 255))
            font = pygame.font.SysFont("Arial", 48)
            text = font.render("Press Enter to Start", True, (0, 0, 0))
            self.screen.blit(
                text,
                (self.screen_width // 2 - text.get_width() // 2, self.screen_height // 2 - text.get_height() // 2)
            )
            pygame.display.flip()
            pygame.time.Clock().tick(60)


class Game:
    def __init__(self):
        self.map_width, self.map_height = get_image_dimensions(map_image_path)
        self.camera = Camera(self.map_width, self.map_height)

        # Character selection (pseudo-code)
        chosen_character_name = "DarkNinja"  # Example character selection
        character = load_character_from_json(CHARACTER_STATS_FILE_PATH, chosen_character_name)

        self.player = Player(
            character,
            x=game_width // 2,
            y=game_height - 40 - 64 // 2,  # Assume 64x64 character size
            width=64,
            height=64
        )

        # AI player setup
        ai_character_name = "Eskimo"  # Example AI character selection
        ai_character = load_character_from_json(CHARACTER_STATS_FILE_PATH, ai_character_name)
        self.ai_player = AIPlayer(
            ai_character,
            x=game_width // 4,
            y=game_height - 40 - 64 // 2,
            width=64,
            height=64,
            target_player=self.player
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
                self.player.shoot(self.camera)
        return True

    def update_game_objects(self, keys):
        self.player.move(keys, self.camera)
        self.ai_player.move(self.camera)
        self.ai_player.random_action()

        # Update each player's bullets separately
        self.update_bullets(self.player.bullets)
        self.update_bullets(self.ai_player.bullets)

        self.camera.update(self.player)

    def update_bullets(self, bullets):
        for bullet in bullets[:]:
            if bullet.move():
                bullets.remove(bullet)
            elif bullet.x < 0 or bullet.x > self.camera.width or bullet.y < 0 or bullet.y > self.camera.height:
                bullets.remove(bullet)

    def check_collisions(self):
        for bullet in self.player.bullets[:]:
            if bullet.owner != self.ai_player and self.ai_player.rect.collidepoint(bullet.x, bullet.y):
                self.ai_player.take_damage(10)
                self.player.bullets.remove(bullet)

        for bullet in self.ai_player.bullets[:]:
            if bullet.owner != self.player and self.player.rect.collidepoint(bullet.x, bullet.y):
                self.player.take_damage(10)
                self.ai_player.bullets.remove(bullet)

            # Check for win/lose conditions
        if self.player.hp == 0:
            display_end_screen("Lose")
        elif self.ai_player.hp == 0:
            display_end_screen("Win")

    def draw_game_objects(self):
        game_surface.fill((255, 255, 255))
        game_surface.blit(map_image, (self.camera.camera.x, self.camera.camera.y))
        self.player.draw(self.camera, game_surface)
        self.ai_player.draw(self.camera, game_surface)
        for bullet in self.player.bullets:
            bullet.draw(self.camera, game_surface)
        for bullet in self.ai_player.bullets:
            bullet.draw(self.camera, game_surface)

        scaled_surface = pygame.transform.scale(game_surface, (screen_width, screen_height))
        screen.blit(scaled_surface, (0, 0))


def display_end_screen(result):
    font = pygame.font.SysFont("Arial", 48)
    message = "You Win!" if result == "Win" else "You Lose!"
    text = font.render(message, True, (0, 0, 0))
    screen.fill((255, 255, 255))
    screen.blit(text, (screen_width // 2 - text.get_width() // 2, screen_height // 2 - text.get_height() // 2))
    pygame.display.flip()
    pygame.time.wait(3000)


def load_character_from_json(file_path, name):
    with open(file_path, 'r') as file:
        data = json.load(file)

    for char_data in data['characters']:
        if char_data['name'] == name:
            # Assuming the structure of the images directory
            return Character(
                name=char_data['name'],
                hp=char_data['hp'],
                speed=char_data['speed'],
                bullet_speed=char_data['bullet_speed'],
                bullet_image=char_data['bullet_image'],
            )

    raise ValueError(f"No character found with the name {name}")


def get_image_dimensions(image_path):
    with Image.open(image_path) as img:
        width, height = img.size
    return width, height


def check_collision(x, y, width, height):
    try:
        return True
        for i in range(x, x + width):
            for j in range(y, y + height):
                if is_colliding_at(i, j):
                    return False
        return True
    except IndexError:
        return False


def is_colliding_at(x, y):
    # Convert the floating point x and y to integers for pixel checking
    int_x = int(x)
    int_y = int(y)
    try:
        pixel_color = collision_map.get_at((int_x, int_y))
        red, green, blue = pixel_color[:3]
        collidable_color = (255, 255, 255)  # assuming white is the collidable color
        return (red, green, blue) == collidable_color
    except IndexError:
        # Outside the map bounds
        return False


if __name__ == "__main__":
    pygame.init()
    screen = pygame.display.set_mode((screen_width, screen_height))
    pygame.display.set_caption("Ninja Game")

    menu = Menu(screen)
    menu.display_main_menu()

    game = Game()
    game.run()
