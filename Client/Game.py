import pygame
from PIL import Image
import math
import json
import logging
import os
import random
import threading
import time

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
pygame.display.set_caption("Ninja Game")

# Images paths
MAP_IMAGE_PATH = r'../Assets/Map/map.png'
PLAYER_COLLISION_MAP_PATH = r'../Assets/Map/player_collision.png'
BULLET_COLLISION_MAP_PATH = r'../Assets/Map/bullet_collision.png'
CHARACTER_STATS_FILE_PATH = r"../Characters.json"
MAIN_MENU_IMAGE_PATH = r'../Assets/Map/map.png'
WINNING_IMAGE_PATH = r'../Assets/GUI/WinTextImage.png'
LOSING_IMAGE_PATH = r'../Assets/GUI/LostTextImage.png'
MAP_WIDTH = 0
MAP_HEIGHT = 0

# Load images
map_image = pygame.image.load(MAP_IMAGE_PATH).convert_alpha()
winning_image = pygame.image.load(WINNING_IMAGE_PATH).convert_alpha()
losing_image = pygame.image.load(LOSING_IMAGE_PATH).convert_alpha()

player_collision_map = pygame.image.load(PLAYER_COLLISION_MAP_PATH).convert_alpha()
bullet_collision_map = pygame.image.load(BULLET_COLLISION_MAP_PATH).convert_alpha()

# Music paths
MUSIC_PATH = "../Assets/Music/Game"
winning_theme_path = "../Assets/Music/Winning_Theme.ogg"
losing_theme_path = "../Assets/Music/Losing_Theme.ogg"
# Font paths
NORMAL_FONT_PATH = r'../Assets/font/NormalFont.ttf'
FONT = pygame.font.Font(NORMAL_FONT_PATH, 36)  # Set the font for the menu text

# player qualities
CHARACTER_WIDTH = 32
CHARACTER_HEIGHT = 32

# GUI paths
hearts_file_path = r"../Assets/GUI/Hearts.png"
heart_width = 16
heart_height = 13

# Load music and sounds effects
UPDATE_MUSIC_DELAY = 1000  # in milliseconds, a second
pygame.mixer.init()
hit_sound_path = r"../Assets/SoundEffects/Game/Hit.wav"
kill_sound_path = r"../Assets/SoundEffects/Game/Kill.wav"
hit_sound = pygame.mixer.Sound(hit_sound_path)
kill_sound = pygame.mixer.Sound(kill_sound_path)


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
        """
        Initiate character qualities (from the Characters.json file). this is a part of the player class
        :param name: character name
        :param hp: character hp points
        :param speed: character's number of pixels allowed to move every tick
        :param bullet_speed: the number of pixels the bullet is moving every tick
        :param bullet_damage: the damage the bullet causes
        :param bullet_lifespan: the amount of ticks the bullet can go before getting deleted automatically
        :param shooting_cooldown: how much time the user can wait before shooting again (kinda)
        """
        self.name = name
        self.hp = hp
        self.speed = speed
        self.bullet_speed = bullet_speed
        self.bullet_damage = bullet_damage
        self.bullet_lifespan = bullet_lifespan
        self.shooting_cooldown = shooting_cooldown
        original_dead_image = pygame.image.load(f'../Assets/Characters/{name}/SeparateAnim/Dead.png').convert_alpha()
        self.dead_image = pygame.transform.scale(original_dead_image, (32, 32))
        self.bullet_image = pygame.image.load(f'../Assets/Characters/{name}/Weapon.png').convert_alpha()
        self.sprites = self.load_sprites(name)

    def load_sprites(self, name):
        """
        load the sprite images of some character
        :param name: the character name
        :return:
        """
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
        """
        the actual in game object of the player
        :param character: a character class instance with all the specific character qualities
        :param x: the player's x coordinate
        :param y: the player's y coordinate
        :param width: the player's width (32)
        :param height: the player's height (32)
        """
        # game qualities
        self.x = x
        self.y = y
        self.width = width
        self.height = height

        # default qualities
        self.dead = False
        self.last_shot_time = 0
        self.bullets = []  # Store bullets for each player
        self.rect = pygame.Rect(x, y, width, height)
        self.direction = 'down'  # Initial direction
        self.anim_frame = 0
        self.anim_speed = 10  # Number of frames to wait before switching animation frames
        self.anim_count = 0  # Counter to track animation speed

        # character qualities
        self.dead_image = character.dead_image
        self.speed = character.speed
        self.max_hp = character.hp
        self.hp = character.hp
        self.bullet_speed = character.bullet_speed
        self.bullet_image = character.bullet_image
        self.sprites = character.sprites
        self.bullet_damage = character.bullet_damage
        self.shooting_cooldown = character.shooting_cooldown

    def draw(self, camera):
        """
        draw the player into the screen
        :param camera: the camera in which the player is drawn to
        :return:
        """
        if not self.dead:
            frame = self.sprites[self.direction][self.anim_frame]
        else:
            frame = self.dead_image
        SCREEN.blit(frame, camera.apply(self))

    def move(self, direction):
        """
        move the player to some direction by his speed
        :param direction: to which direction to move (up, down, left, right)
        :return:
        """
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
        if check_collision(self.x + dx, self.y + dy, self.width, self.height, True):
            self.x += dx
            self.y += dy

        self.rect.x = self.x
        self.rect.y = self.y

    def shoot(self, dx, dy):
        """
        make the player shoot a bullet
        :param dx: the x vector of the bullet
        :param dy: the y vector of the bullet
        :return:
        """
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
        """
        make player take damage
        :param damage: the amount of damage
        :return:
        """
        self.hp -= damage
        if self.hp <= 0:
            # Handle player death here if needed
            self.dead = True
            kill_sound.play()
            self.hp = 0
        else:
            hit_sound.play()


class Bullet:
    def __init__(self, x, y, dx, dy, radius, damage, owner, lifespan, sprite_sheet, frames_number=2):
        """
        Initialize a Bullet instance with position, movement, appearance, and behavior settings.
        :param x: The initial x-coordinate of the bullet
        :param y: The initial y-coordinate of the bullet
        :param dx: The change in x-coordinate per frame
        :param dy: The change in y-coordinate per frame
        :param radius: The radius of the bullet
        :param damage: The damage the bullet will cause on hit
        :param owner: The entity that fired the bullet
        :param lifespan: The number of frames before the bullet expires
        :param sprite_sheet: The path to the sprite sheet image
        :param frames_number: The number of frames in the sprite sheet (default is 2)
        :return: None
        """
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
        """
        Load and prepare bullet sprites from a sprite sheet.
        :param sprite_sheet: The sprite sheet surface from which to extract bullet frames
        :param frames_number: The number of frames in the sprite sheet
        :return: A list of pygame.Surface objects each representing a frame of the bullet's animation
        """
        frames = []  # Assuming that frames are laid out horizontally
        frame_width = sprite_sheet.get_width() // frames_number
        for i in range(frames_number):
            frame = sprite_sheet.subsurface(i * frame_width, 0, frame_width, sprite_sheet.get_height())
            scaled_frame = pygame.transform.scale(frame, (frame_width * 2, frame_width * 2))

            frames.append(scaled_frame)
        return frames

    def move(self):
        """
        Update the bullet's position based on its speed and check for collision.
        :return: Boolean indicating if a collision occurred (True if it did, False otherwise)
        """
        self.lifespan -= 1  # Decrease lifespan each frame
        if self.lifespan <= 0:
            return True  # Signal to remove this bullet
        did_collide = False
        if check_collision(int(self.x + self.dx), int(self.y + self.dy), int(self.radius), int(self.radius), False):
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
        """
        Draw the bullet on the screen at its current position.
        :param camera: The camera handling the screen offset and focus
        :return: None
        """
        if self.image:
            SCREEN.blit(self.image, camera.apply(self).topleft)
        else:
            pygame.draw.circle(SCREEN, (0, 0, 0), camera.apply(self).center, self.radius)


class Game:
    def __init__(self, audio):
        """
        Initialize the Game environment, setting up the audio, map, camera, and player entities.
        :param audio: Boolean indicating whether the audio is enabled
        :return: None
        """
        try:
            if not audio:
                pygame.mixer.music.set_volume(0)
            global MAP_WIDTH, MAP_HEIGHT
            MAP_WIDTH, MAP_HEIGHT = get_image_dimensions(MAP_IMAGE_PATH)
            self.screen = pygame.display.set_mode((screen_width, screen_height))
            self.map_width, self.map_height = MAP_WIDTH, MAP_HEIGHT
            self.camera = Camera(self.map_width, self.map_height)
            self.players = {}
            self.stop_music = False
            self.game_over_music_playing = False
            thread = threading.Thread(target=self.play_random_music)
            thread.start()
            self.player = None

        except Exception as e:
            logger.error(f"Game initialization error: {e}")

    def game_over(self, win):
        """
        Display the game over screen based on the game result.
        """
        # Indicate that game over music is playing
        self.game_over_music_playing = True

        # Play game over music
        if win:
            pygame.mixer.music.load(winning_theme_path)
        else:
            pygame.mixer.music.load(losing_theme_path)
        pygame.mixer.music.play()
        # Select the appropriate image based on the win parameter
        image = winning_image if win else losing_image

        # Position the image at the top center of the screen
        # Assuming the screen's size is 800x600 as mentioned
        screen_center_x = self.screen.get_rect().centerx
        image_width = image.get_width()

        # Calculate the position to center the image on the screen
        image_position = (screen_center_x - image_width // 2, 20)

        # Blit the image onto the screen at the calculated position
        self.screen.blit(image, image_position)
        pygame.display.flip()
        # Wait for the music to finish before continuing with random music
        time.sleep(2)
        pygame.mixer.music.stop()

        # Indicate that game over music has finished
        self.game_over_music_playing = False

    def update(self):
        """
        Update the game state by moving bullets, drawing game objects, and managing UI updates.
        :return: None
        """
        try:
            self.update_bullets()
            self.draw_game_objects()
            if self.player:
                self.camera.follow_target(self.player)
                self.draw_player_gui()
            # check for game over
            if self.player:
                if self.player.dead:
                    self.game_over(False)
                    return True   # the game is over and lost
                elif (all(player.dead for player in self.players.values() if player != self.player)
                      and len(self.players) > 1):
                    self.game_over(True)
                    return True  # the game is over and won

            pygame.display.flip()
            return False  # the game continues

        except Exception as e:
            logger.error(f"Error updating game state: {e}")

    def draw_player_gui(self):
        """
        Draw the player's health interface on the game screen.
        :return: None
        """
        hearts_surface = pygame.image.load(hearts_file_path)
        scale_factor = 3

        # Scale dimensions
        scaled_heart_width = heart_width * scale_factor
        scaled_heart_height = heart_height * scale_factor

        # Scale the image surface
        hearts_surface = pygame.transform.scale(
            hearts_surface,
            (heart_width * 5 * scale_factor, heart_height * scale_factor))

        # Calculate number of hearts to display
        num_full_hearts = self.player.hp // 4
        partial_heart = self.player.hp % 4
        num_empty_hearts = ((self.player.max_hp // 4)
                            - num_full_hearts
                            - (1 if partial_heart > 0 else 0)
                            + (1 if self.player.max_hp % 4 != 0 else 0))

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
            partial_heart_rect = pygame.Rect(
                (4 - partial_heart) * scaled_heart_width,
                0,
                scaled_heart_width, scaled_heart_height
            )
            self.screen.blit(hearts_surface, (x, y), partial_heart_rect)
            x += scaled_heart_width

        # Draw empty hearts
        for i in range(num_empty_hearts):
            empty_heart_rect = pygame.Rect(4 * scaled_heart_width, 0, scaled_heart_width, scaled_heart_height)
            self.screen.blit(hearts_surface, (x, y), empty_heart_rect)
            x += scaled_heart_width

    def create_player(self, player_id, character_name, x, y):
        """
        Create and register a new player in the game.
        :param player_id: Unique identifier for the player
        :param character_name: The name of the character model to load
        :param x: The initial x-coordinate for the player
        :param y: The initial y-coordinate for the player
        :return: None
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
        """
        Remove a player from the game based on their unique identifier.
        :param player_id: The unique identifier of the player to remove
        :return: None
        """
        if player_id in self.players:
            del self.players[player_id]

    def move_player(self, player_id, direction):
        """
        Update the specified player's position based on the provided direction.
        :param player_id: The unique identifier of the player to move
        :param direction: The direction in which to move the player
        :return: None
        """
        if player_id in self.players:
            self.players[player_id].move(direction)

    def shoot_player(self, player_id, dx, dy):
        """
        Command a player to shoot a bullet in the specified direction.
        :param player_id: The unique identifier of the shooting player
        :param dx: The x-component of the bullet's velocity
        :param dy: The y-component of the bullet's velocity
        :return: None
        """
        if player_id in self.players:
            self.players[player_id].shoot(dx, dy)

    def check_for_quit(self):
        """
        Check if the game has received a quit event.
        :return: Boolean indicating if the game should continue running (False if it should quit)
        """
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
        return True

    def update_bullets(self):
        """
        Update the positions of all bullets, remove those that have collided or expired.
        :return: None
        """
        for player_id, player in self.players.items():
            for bullet in player.bullets[:]:
                if bullet.move():  # Moving the bullet and checking collision in the same time
                    player.bullets.remove(bullet)
                # Check if the bullet is out of bounds or hits another player
                elif not self.within_bounds(bullet) or self.check_bullet_hit(player_id, bullet):
                    player.bullets.remove(bullet)

    def check_bullet_hit(self, shooter_id, bullet):
        """
        Check if a bullet has hit any player other than the shooter.
        :param shooter_id: The unique identifier of the player who shot
        :param bullet: The bullet instance to check for collisions
        :return: Boolean indicating if a hit was detected (True if it was, False otherwise)
        """
        for player_id, player in self.players.items():
            if player_id != shooter_id and player.rect.collidepoint(bullet.x, bullet.y):
                return True  # Bullet hit a player
        return False  # No hit detected

    def within_bounds(self, bullet):
        """
        Determine if a bullet is within the game's boundaries.
        :param bullet: The bullet instance to check
        :return: Boolean indicating if the bullet is within bounds (True if it is, False otherwise)
        """
        return 0 <= bullet.x <= self.map_width and 0 <= bullet.y <= self.map_height

    def draw_game_objects(self):
        """
        Draw all game-related objects, including the map, players, and bullets, to the screen.
        :return: None
        """
        try:
            self.screen.fill((255, 255, 255))
            map_offset_x = -self.camera.camera.x
            map_offset_y = -self.camera.camera.y
            self.screen.blit(map_image, (map_offset_x, map_offset_y))
            # First, draw all dead players
            for player in self.players.values():
                if player.dead:  # Check if the player is dead
                    player.draw(self.camera)
                    for bullet in player.bullets:
                        bullet.draw(self.camera)

            # Second, draw all players who are not the main player and are not dead
            for player in self.players.values():
                if not player.dead and player != self.player:
                    player.draw(self.camera)
                    for bullet in player.bullets:
                        bullet.draw(self.camera)

            # Lastly, draw the main player, unless they are dead
            if self.player:
                if not self.player.dead:
                    self.player.draw(self.camera)
                    for bullet in self.player.bullets:
                        bullet.draw(self.camera)
        except Exception as e:
            logger.error(f"Error drawing game objects: {e}")

    def get_mouse_angle(self):
        """
        Calculate the angle between the player's position and the mouse cursor position.
        :return: A tuple (dx, dy) representing the direction vector for a bullet based on the calculated angle
        """
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

    def play_random_music(self):
        """
        Continuously play random music tracks from a specified directory, handling track selection and looping.
        :return: None
        """
        # Fetch all .wav files from the specified directory
        music_files = [file for file in os.listdir(MUSIC_PATH) if file.endswith('.ogg')]
        if not music_files:
            print("No music files found in the directory.")
            return

        # Function to play a selected music file
        def play_music():
            # Randomly select a music file
            selected_file = random.choice(music_files)
            full_path = os.path.join(MUSIC_PATH, selected_file)

            # Load and play the selected music file
            pygame.mixer.music.load(full_path)
            pygame.mixer.music.play()

        # Continue playing music
        while not self.stop_music:
            if not self.game_over_music_playing:  # Only play random music if not in game over state
                if not pygame.mixer.music.get_busy():
                    play_music()
            pygame.time.wait(UPDATE_MUSIC_DELAY)
        pygame.mixer.music.stop()

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


def check_collision(x, y, width, height, is_player):
    """

    :param x:
    :param y:
    :param width:
    :param height:
    :param is_player: if is player, use player collision else bullet collision
    :return: bool, true if you can move, false if not
    """
    try:
        # Loop through the edges of the rectangle
        for i in range(x, x + width):
            for j in [y, y + height - 1]:  # Check top and bottom borders
                if is_colliding_at(i, j, is_player):
                    return False

        for i in [x, x + width - 1]:
            for j in range(y, y + height):  # Check left and right borders
                if is_colliding_at(i, j, is_player):
                    return False

        return True
    except IndexError:
        return False


def is_colliding_at(x, y, is_player):
    """
    checking if some pixel is colliding with a map object
    :param x: the pixel's x
    :param y: the pixel's y
    :param is_player: if is player, use player collision else bullet collision
    :return:
    """
    int_x = int(x)
    int_y = int(y)
    if is_player:
        pixel_color = player_collision_map.get_at((int_x, int_y))
    else:
        pixel_color = bullet_collision_map.get_at((int_x, int_y))
    alpha = pixel_color[3]
    return not alpha == 0
