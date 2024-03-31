import pygame
from PIL import Image
import math
import json

# Initialize Pygame
pygame.init()

# Set up the display
screen_width = 800
screen_height = 600
SCREEN = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption("Tank Game")

# Images paths
MAP_IMAGE_PATH = r'Images/Map/detailedMap.png'
collision_image_path = r'Images/Map/UpdatedCollisoin.png'
CHARACTER_STATS_FILE_PATH = "Characters.json"

MAP_WIDTH = 0
MAP_HEIGHT = 0
# Load images
map_image = pygame.image.load(MAP_IMAGE_PATH).convert_alpha()
collision_map = pygame.image.load(collision_image_path).convert_alpha()

# player qualities
player_speed = 4
CHARACTER_WIDTH = 32
CHARACTER_HEIGHT = 32
SHOOTING_CHANCE = 0.05


class Camera:
    def __init__(self, width, height):
        self.camera = pygame.Rect(0, 0, width, height)
        self.width = width
        self.height = height
        self.speed = 5  # Camera movement speed

    def apply(self, entity):
        return entity.rect.move(self.camera.topleft)

    def update(self, keys):
        # Initialize x and y to the current camera position
        x, y = self.camera.x, self.camera.y
        # Movement of the camera based on keyboard input
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            x = max(x - self.speed, 0)  # left
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            x = min(x + self.speed, self.width - screen_width)  # right
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            y = max(y - self.speed, 0)  # up
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            y = min(y + self.speed, self.height - screen_height)  # down

        self.camera = pygame.Rect(x, y, self.width, self.height)

    def follow_target(self, target):
        x = -target.rect.x + int(screen_width / 2)
        y = -target.rect.y + int(screen_height / 2)

        # limit scrolling to map size
        x = min(0, x)  # left
        y = min(0, y)  # top
        x = max(-(self.width - screen_width), x)  # right
        y = max(-(self.height - screen_height), y)  # bottom

        self.camera = pygame.Rect(x, y, self.width, self.height)


class Character:
    def __init__(self, name, hp, speed, bullet_speed, bullet_damage, bullet_lifespan, shooting_cooldown):
        self.name = name
        self.hp = hp
        self.speed = speed
        self.bullet_speed = bullet_speed
        self.bullet_damage = bullet_damage
        self.bullet_lifespan = bullet_lifespan
        self.shooting_cooldown = shooting_cooldown
        self.bullet_image = pygame.image.load(f'Images/Characters/{name}/Weapon.png').convert_alpha()
        self.faceset = pygame.image.load(f'Images/Characters/{name}/Faceset.png').convert_alpha()
        self.sprites = self.load_sprites(name)

    def load_sprites(self, name):
        sprite_sheet = pygame.image.load(f'Images/Characters/{name}/SeparateAnim/Walk.png').convert_alpha()
        sprites = {
            'down': [],
            'up': [],
            'left': [],
            'right': []
        }
        original_sprite_size = 16  # Original size of the sprite
        scaled_sprite_size = 32  # New size of the sprite after scaling

        for col, direction in enumerate(sprites.keys()):
            for row in range(4):  # Assuming 4 frames per direction
                # Extract the original frame from the sprite sheet
                original_frame = sprite_sheet.subsurface(col * original_sprite_size, row * original_sprite_size,
                                                         original_sprite_size, original_sprite_size)
                # Scale the frame
                scaled_frame = pygame.transform.scale(original_frame, (scaled_sprite_size, scaled_sprite_size))
                sprites[direction].append(scaled_frame)

        return sprites


class Player:
    def __init__(self, character, x, y, width, height):
        # game qualities
        self.x = x
        self.y = y
        self.width = width
        self.height = height

        # default qualities
        self.last_shot_time = 0
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
        self.bullet_image = character.bullet_image
        self.sprites = character.sprites
        self.bullet_damage = character.bullet_damage
        self.shooting_cooldown = character.shooting_cooldown

    def draw(self, camera):
        frame = self.sprites[self.direction][self.anim_frame]
        SCREEN.blit(frame, camera.apply(self))

    def move(self, direction):
        dx = dy = 0
        if direction == 'left':
            dx = -self.speed
            self.direction = 'left'
        elif direction == 'right':
            dx = self.speed
            self.direction = 'right'
        if direction == 'up':
            dy = -self.speed
            self.direction = 'up'
        if direction == 'down':
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

    def shoot(self, angle):
        current_time = pygame.time.get_ticks()
        if current_time - self.last_shot_time > self.shooting_cooldown:
            self.last_shot_time = current_time

            # Adjust the mouse coordinates based on the camera's offset
            # Since the camera's x and y represent the top-left corner of the view,
            # you need to add these values to get the correct world position of the mouse

            # Calculate the center position of the player
            center_x = self.x + self.width // 2
            center_y = self.y + self.height // 2

            # Calculate the bullet's direction vector based on the angle
            dx = math.cos(angle) * self.bullet_speed  # Speed of the bullet
            dy = math.sin(angle) * self.bullet_speed  # Speed of the bullet

            # Create and add the new bullet to the bullets list
            self.bullets.append(Bullet(
                center_x,
                center_y,
                dx,
                dy,
                3,
                self.bullet_damage,
                self,
                self.shooting_cooldown,
                self.bullet_image)
            )

    def take_damage(self, damage):
        self.hp -= damage
        if self.hp <= 0:
            self.hp = 0
            # Handle player death here if needed


class Bullet:
    def __init__(self, x, y, dx, dy, radius, damage, owner, lifespan, sprite_sheet, frames_number=2):
        self.x = x
        self.y = y
        self.dx = dx
        self.dy = dy
        self.radius = radius
        self.damage = damage
        self.owner = owner
        self.lifespan = lifespan
        self.anim_frame = 0
        self.anim_speed = 10  # You can adjust this to make the animation faster or slower
        self.anim_count = 0

        # If a sprite sheet path is provided, load it; otherwise, create a surface and draw a circle on it.
        if sprite_sheet:
            self.sprites = self.load_bullet_sprites(sprite_sheet, frames_number)
            self.image = self.sprites[self.anim_frame]  # Start with the first frame
        else:
            self.image = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(self.image, (0, 0, 0), (radius, radius), radius)

        self.rect = pygame.Rect(x - radius, y - radius, radius * 2, radius * 2)

    def load_bullet_sprites(self, sprite_sheet, frames_number):
        frames = []  # Assuming that frames are laid out horizontally
        frame_width = sprite_sheet.get_width() // frames_number
        for i in range(frames_number):
            frame = sprite_sheet.subsurface(i * frame_width, 0, frame_width, sprite_sheet.get_height())
            scaled_frame = pygame.transform.scale(frame, (frame_width * 2, frame_width * 2))

            frames.append(scaled_frame)
        return frames

    def move(self):
        self.lifespan -= 1  # Decrease lifespan each frame
        if self.lifespan <= 0:
            return True  # Signal to remove this bullet
        did_collide = False
        if check_collision(int(self.x + self.dx), int(self.y + self.dy), int(self.radius), int(self.radius)):
            self.x += self.dx
            self.y += self.dy
        else:
            did_collide = True
        self.rect.x = self.x - self.radius
        self.rect.y = self.y - self.radius

        # Update animation
        self.anim_count += 1
        if self.anim_count >= self.anim_speed:
            self.anim_frame = (self.anim_frame + 1) % len(self.sprites)
            self.anim_count = 0
            self.image = self.sprites[self.anim_frame]  # Update the image to the next frame
        return did_collide

    def draw(self, camera):
        if self.image:
            SCREEN.blit(self.image, camera.apply(self).topleft)
        else:
            pygame.draw.circle(SCREEN, (0, 0, 0), camera.apply(self).center, self.radius)


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
    def __init__(self, screen):
        self.screen = screen
        self.map_width, self.map_height = get_image_dimensions(MAP_IMAGE_PATH)
        self.camera = Camera(self.map_width, self.map_height)
        self.players = {}

    def create_player(self, player_id, character_name, x, y):
        character = load_character_from_json(CHARACTER_STATS_FILE_PATH, character_name)
        player = Player(
            character,
            x,
            y,
            CHARACTER_WIDTH,
            CHARACTER_HEIGHT
        )
        self.players[player_id] = player

    def delete_player(self, player_id):
        if player_id in self.players:
            del self.players[player_id]

    def move_player(self, player_id, direction):
        if player_id in self.players:
            self.players[player_id].move(direction)

    def shoot_player(self, player_id, angle):
        if player_id in self.players:
            self.players[player_id].shoot(angle)

    def run(self):
        running = True
        # TODO: add winning
        while running:
            keys = pygame.key.get_pressed()
            self.camera.update(keys)  # Update camera based on keyboard input

            running = self.handle_events()
            self.update_bullets()
            self.draw_game_objects()
            pygame.display.flip()
            pygame.time.Clock().tick(60)

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
        return True

    def update_bullets(self):
        for player_id, player in self.players.items():
            for bullet in player.bullets[:]:
                bullet.move()  # Assuming 'move' method updates the bullet's position

                # Check if the bullet is out of bounds or hits another player
                if not self.within_bounds(bullet) or self.check_bullet_hit(player_id, bullet):
                    player.bullets.remove(bullet)

    def within_bounds(self, bullet):
        return 0 <= bullet.x <= self.map_width and 0 <= bullet.y <= self.map_height

    def check_bullet_hit(self, shooter_id, bullet):
        for player_id, player in self.players.items():
            if player_id != shooter_id and player.rect.collidepoint(bullet.x, bullet.y):
                player.take_damage(bullet.damage)
                return True  # Bullet hit a player
        return False  # No hit detected

    def draw_game_objects(self):
        self.screen.fill((255, 255, 255))
        self.screen.blit(map_image, (self.camera.camera.x, self.camera.camera.y))
        for player in self.players.values():
            player.draw(self.camera)
            for bullet in player.bullets:
                bullet.draw(self.camera)


def display_end_screen(result):
    font = pygame.font.SysFont("Arial", 48)
    if result == "Win":
        message = "You Win!"
    else:
        message = "You Lose!"
    text = font.render(message, True, (0, 0, 0))
    SCREEN.fill((255, 255, 255))
    SCREEN.blit(text, (screen_width // 2 - text.get_width() // 2, screen_height // 2 - text.get_height() // 2))
    pygame.display.flip()
    pygame.time.wait(300)  # Wait 3 seconds before closing or restarting the game


def load_character_from_json(file_path, name):
    with open(file_path, 'r') as file:
        data = json.load(file)

    for char_data in data['characters']:
        if char_data['name'] == name:
            return Character(
                name=char_data['name'],
                hp=char_data['hp'],
                speed=char_data['speed'],
                bullet_speed=char_data['bullet_speed'],
                bullet_damage=char_data['bullet_damage'],
                bullet_lifespan=char_data['bullet_lifespan'],
                shooting_cooldown=char_data['shooting_cooldown']
            )

    raise ValueError(f"No character found with the name {name}")


def get_image_dimensions(image_path):
    with Image.open(image_path) as img:
        width, height = img.size
    return width, height


def check_collision(x, y, width, height):
    """

    :param x:
    :param y:
    :param width:
    :param height:
    :return: bool, true if you can move, false if not
    """
    try:
        # Loop through the edges of the rectangle
        for i in range(x, x + width):
            for j in [y, y + height - 1]:  # Check top and bottom borders
                if is_colliding_at(i, j):
                    return False

        for i in [x, x + width - 1]:
            for j in range(y, y + height):  # Check left and right borders
                if is_colliding_at(i, j):
                    return False

        return True
    except IndexError:
        return False


def is_colliding_at(x, y):
    int_x = int(x)
    int_y = int(y)
    pixel_color = collision_map.get_at((int_x, int_y))
    alpha = pixel_color[3]
    return not alpha == 0


def start_game():
    global MAP_WIDTH, MAP_HEIGHT, SCREEN
    pygame.init()
    SCREEN = pygame.display.set_mode((screen_width, screen_height))
    pygame.display.set_caption("Ninja Game")
    MAP_WIDTH, MAP_HEIGHT = get_image_dimensions(MAP_IMAGE_PATH)
    game = Game(SCREEN)
    game.run()
    winning_state = True
    display_end_screen(winning_state)


# TODO: remove this line before running skeleton server
if __name__ == "__main__":
    start_game()
