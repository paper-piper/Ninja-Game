import pygame
from PIL import Image
import math
import json
import logging

# Initialize pygame
pygame.init()

# Initialize logger
logger = logging.getLogger("Game")
logger.setLevel(logging.DEBUG)
file_handler = logging.FileHandler('Game.log')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s - Line: %(lineno)d',
                                            datefmt='%Y-%m-%d %H:%M:%S'))
logger.addHandler(file_handler)

# Configure PIL logger to not propagate messages to the root logger
pil_logger = logging.getLogger('PIL')
pil_logger.setLevel(logging.WARNING)
pil_logger.propagate = False

# Set up the display
screen_width = 800
screen_height = 600
SCREEN = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption("Tank Game")

# Images paths
MAP_IMAGE_PATH = r'../Assets/Map/detailedMap.png'
COLLISION_IMAGE_PATH = r'../Assets/Map/UpdatedCollision.png'
CHARACTER_STATS_FILE_PATH = r"../Characters.json"
MAIN_MENU_IMAGE_PATH = r'../Assets/Map/detailedMap.png'

# Music paths

# Font paths
NORMAL_FONT_PATH = r'../Assets/font/NormalFont.ttf'
FONT = pygame.font.Font(NORMAL_FONT_PATH, 36)  # Set the font for the menu text

MAP_WIDTH = 0
MAP_HEIGHT = 0

# Load images
map_image = pygame.image.load(MAP_IMAGE_PATH).convert_alpha()
collision_map = pygame.image.load(COLLISION_IMAGE_PATH).convert_alpha()

# player qualities
CHARACTER_WIDTH = 32
CHARACTER_HEIGHT = 32

# GUI paths
hearts_file_path = r"../Assets/GUI/Hearts.png"
heart_width = 16
heart_height = 13

# Load music and sounds effects
hit_sound_path = r"../Assets/SoundEffects/Hit.wav"
pygame.mixer.init()
hit_sound = pygame.mixer.Sound(hit_sound_path)


class Camera:
    def __init__(self, width, height):
        """
        Initialize the camera with the given width and height of the view.
        :param width: Width of the camera view
        :param height: Height of the camera view
        """
        self.camera = pygame.Rect(0, 0, screen_width, screen_height)
        self.width = width
        self.height = height
        self.speed = 5  # Camera movement speed

    def apply(self, entity):
        """
        Adjust the entity's position based on the camera's current position.
        :param entity: The entity to which the camera's position will be applied
        :return: The adjusted position of the entity
        """
        return entity.rect.move(-self.camera.x, -self.camera.y)

    def update(self, direction):
        """
        Update the camera's position based on the given direction.
        :param direction: The direction to move the camera ('left', 'right', 'up', 'down')
        """
        if direction == 'left':
            self.camera.x = max(self.camera.x - self.speed, 0)
        elif direction == 'right':
            self.camera.x = min(self.camera.x + self.speed, self.width - screen_width)
        if direction == 'up':
            self.camera.y = max(self.camera.y - self.speed, 0)
        elif direction == 'down':
            self.camera.y = min(self.camera.y + self.speed, self.height - screen_height)

    def follow_target(self, target):
        """
        Make the camera follow the target entity.
        :param target: The target entity that the camera should follow
        """
        # FIXME the x and y calculation is reversed twice. working, but weird
        x = -target.rect.x + int(screen_width / 2)
        y = -target.rect.y + int(screen_height / 2)

        # limit scrolling to map size
        x = min(0, x)  # left
        y = min(0, y)  # top
        x = max(-(self.width - screen_width), x)  # right
        y = max(-(self.height - screen_height), y)  # bottom

        self.camera = pygame.Rect(-x, -y, self.width, self.height)


class Character:
    def __init__(self, name, hp, speed, bullet_speed, bullet_damage, bullet_lifespan, shooting_cooldown):
        self.name = name
        self.hp = hp
        self.speed = speed
        self.bullet_speed = bullet_speed
        self.bullet_damage = bullet_damage
        self.bullet_lifespan = bullet_lifespan
        self.shooting_cooldown = shooting_cooldown
        self.bullet_image = pygame.image.load(f'../Assets/Characters/{name}/Weapon.png').convert_alpha()
        self.faceset = pygame.image.load(f'../Assets/Characters/{name}/Faceset.png').convert_alpha()
        self.sprites = self.load_sprites(name)

    def load_sprites(self, name):
        sprite_sheet = pygame.image.load(f'../Assets/Characters/{name}/SeparateAnim/Walk.png').convert_alpha()
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
        self.max_hp = character.hp
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

    def shoot(self, dx, dy):
        current_time = pygame.time.get_ticks()
        if current_time - self.last_shot_time > self.shooting_cooldown:
            self.last_shot_time = current_time

            # Adjust the mouse coordinates based on the camera's offset
            # Since the camera's x and y represent the top-left corner of the view,
            # you need to add these values to get the correct world position of the mouse

            # Calculate the center position of the player
            center_x = self.x + self.width // 2
            center_y = self.y + self.height // 2

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
        hit_sound.play()
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


class Game:
    def __init__(self):
        """
        Initialize the game, setting up the map, camera, and player entities.
        """
        try:
            global MAP_WIDTH, MAP_HEIGHT
            MAP_WIDTH, MAP_HEIGHT = get_image_dimensions(MAP_IMAGE_PATH)
            self.screen = pygame.display.set_mode((screen_width, screen_height))
            self.map_width, self.map_height = MAP_WIDTH, MAP_HEIGHT
            self.camera = Camera(self.map_width, self.map_height)
            self.players = {}
            self.player = None
        except Exception as e:
            logger.error(f"Game initialization error: {e}")

    def update(self):
        """
        Update the game state, including moving bullets and drawing game objects.
        """
        try:
            self.update_bullets()
            self.draw_game_objects()
            if self.player:
                self.camera.follow_target(self.player)
                self.draw_player_gui()
            pygame.display.flip()

        except Exception as e:
            logger.error(f"Error updating game state: {e}")

    def draw_player_gui(self):
        hearts_surface = pygame.image.load(hearts_file_path)
        scale_factor = 3

        # Scale dimensions
        scaled_heart_width = heart_width * scale_factor
        scaled_heart_height = heart_height * scale_factor

        # Scale the image surface
        hearts_surface = pygame.transform.scale(hearts_surface, (heart_width * 5 * scale_factor, heart_height * scale_factor))

        # Calculate number of hearts to display
        num_full_hearts = self.player.hp // 4
        partial_heart = self.player.hp % 4
        num_empty_hearts = (self.player.max_hp // 4) - num_full_hearts - (1 if partial_heart > 0 else 0)

        # Coordinates to draw the hearts
        x = 10  # starting x position (10 pixels from the left)
        y = self.screen.get_height() - scaled_heart_height - 10  # 10 pixels above the bottom

        # Draw full hearts
        for i in range(num_full_hearts):
            full_heart_rect = pygame.Rect(0, 0, scaled_heart_width, scaled_heart_height)
            self.screen.blit(hearts_surface, (x, y), full_heart_rect)
            x += scaled_heart_width

        # Draw partial heart if any
        if partial_heart > 0:
            partial_heart_rect = pygame.Rect((4 - partial_heart) * scaled_heart_width, 0, scaled_heart_width, scaled_heart_height)
            self.screen.blit(hearts_surface, (x, y), partial_heart_rect)
            x += scaled_heart_width

        # Draw empty hearts
        for i in range(num_empty_hearts):
            empty_heart_rect = pygame.Rect(4 * scaled_heart_width, 0, scaled_heart_width, scaled_heart_height)
            self.screen.blit(hearts_surface, (x, y), empty_heart_rect)
            x += scaled_heart_width

    def create_player(self, player_id, character_name, x, y):
        """
        player id 0 means itself
        :param player_id:
        :param character_name:
        :param x:
        :param y:
        :return:
        """
        character = load_character_from_json(character_name)
        player = Player(
            character,
            x,
            y,
            CHARACTER_WIDTH,
            CHARACTER_HEIGHT
        )
        self.players[player_id] = player
        if player_id == '0':
            self.player = player
        # logger.info(f"Created new player ({character_name}) in x = {x}, y = {y}")

    def delete_player(self, player_id):
        if player_id in self.players:
            del self.players[player_id]

    def move_player(self, player_id, direction):
        if player_id in self.players:
            self.players[player_id].move(direction)

    def shoot_player(self, player_id, dx, dy):
        if player_id in self.players:
            self.players[player_id].shoot(dx, dy)

    def check_for_quit(self):
        """
        checks for quiting game
        :return:
        """
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
        return True

    def update_bullets(self):
        for player_id, player in self.players.items():
            for bullet in player.bullets[:]:
                if bullet.move():  # Moving the bullet and checking collision in the same time
                    player.bullets.remove(bullet)
                # Check if the bullet is out of bounds or hits another player
                elif not self.within_bounds(bullet):  #  or self.check_bullet_hit(player_id, bullet):
                    player.bullets.remove(bullet)

    def within_bounds(self, bullet):
        return 0 <= bullet.x <= self.map_width and 0 <= bullet.y <= self.map_height

    def draw_game_objects(self):
        """
        Draw all game objects, including players and bullets, to the screen.
        """
        try:
            self.screen.fill((255, 255, 255))
            map_offset_x = -self.camera.camera.x
            map_offset_y = -self.camera.camera.y
            self.screen.blit(map_image, (map_offset_x, map_offset_y))
            for player in self.players.values():
                player.draw(self.camera)
                for bullet in player.bullets:
                    bullet.draw(self.camera)
        except Exception as e:
            logger.error(f"Error drawing game objects: {e}")

    def get_mouse_angle(self):
        mx, my = pygame.mouse.get_pos()

        # Adjust the mouse coordinates based on the camera's offset
        # Since the camera's x and y represent the top-left corner of the view,
        # you need to add these values to get the correct world position of the mouse
        world_mx = mx + self.camera.camera.x
        world_my = my + self.camera.camera.y

        # Calculate the center position of the player
        center_x = self.player.x + self.player.width // 2
        center_y = self.player.y + self.player.height // 2

        # Calculate the angle between the player's center and the mouse position in the world
        angle = math.atan2(world_my - center_y, world_mx - center_x)

        # Calculate the bullet's direction vector based on the angle
        dx = math.cos(angle) * self.player.bullet_speed  # Speed of the bullet
        dy = math.sin(angle) * self.player.bullet_speed  # Speed of the bullet
        return dx, dy


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


def load_character_from_json(name):
    """
    Load character data from a JSON file.
    :param name: The name of the character to load
    :return: A Character object
    """
    try:
        with open(CHARACTER_STATS_FILE_PATH, 'r') as file:
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
    except json.JSONDecodeError as e:
        logger.error(f"JSON Decode Error: {e}")
        raise
    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        raise
    except Exception as e:
        logger.error(f"Error loading character data: {e}")
        raise


def get_image_dimensions(image_path):
    """
    Get the dimensions of an image.
    :param image_path: Path to the image file
    :return: A tuple containing the width and height of the image
    """
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
