import pygame
from PIL import Image
import json
import random
import logging

# Initialize logger
logger = logging.getLogger("GameLogic")
logger.setLevel(logging.DEBUG)
file_handler = logging.FileHandler('GameLogic.log')
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
# SCREEN = pygame.display.set_mode((screen_width, screen_height))

pygame.display.set_caption("Tank Game")

# Assets paths
MAP_IMAGE_PATH = r'../Assets/Map/map.png'
PLAYER_COLLISION_MAP_PATH = r'../Assets/Map/player_collision.png'
BULLET_COLLISION_MAP_PATH = r'../Assets/Map/bullet_collision.png'
CHARACTER_STATS_FILE_PATH = "../Characters.json"

MAP_WIDTH = 0
MAP_HEIGHT = 0
# Load images
# map_image = pygame.image.load(MAP_IMAGE_PATH).convert_alpha()
player_collision_map = Image.open(PLAYER_COLLISION_MAP_PATH)
bullet_collision_map = Image.open(BULLET_COLLISION_MAP_PATH)

# player qualities
player_speed = 4
CHARACTER_WIDTH = 32
CHARACTER_HEIGHT = 32
SHOOTING_CHANCE = 0.05


class Character:
    def __init__(self, name, hp, speed, bullet_speed, bullet_damage, bullet_lifespan, shooting_cooldown):
        """
        Initializes a new character with specific attributes.
        :param name: Name of the character
        :param hp: Health points of the character
        :param speed: Movement speed of the character
        :param bullet_speed: Speed of the bullets fired by this character
        :param bullet_damage: Damage dealt by each bullet
        :param bullet_lifespan: How long the bullet exists before disappearing
        :param shooting_cooldown: Cooldown time between shots
        """
        self.name = name
        self.hp = hp
        self.speed = speed
        self.bullet_speed = bullet_speed
        self.bullet_damage = bullet_damage
        self.bullet_lifespan = bullet_lifespan
        self.shooting_cooldown = shooting_cooldown


class Player:
    def __init__(self, character, x, y, width, height):
        """
        Initializes a new player with specific position and dimensions.
        :param character: A Character object representing the player's character
        :param x: Initial x-coordinate of the player
        :param y: Initial y-coordinate of the player
        :param width: Width of the player
        :param height: Height of the player
        """
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
        self.name = character.name
        self.speed = character.speed
        self.hp = character.hp
        self.bullet_speed = character.bullet_speed
        self.bullet_damage = character.bullet_damage
        self.shooting_cooldown = character.shooting_cooldown

    def set_cords(self, x, y):
        """
        Updates the player's x and y coordinates and accordingly updates their rect position.
        :param x: New x-coordinate of the player
        :param y: New y-coordinate of the player
        """

        self.x = x
        self.y = y
        self.rect.x = self.x
        self.rect.y = self.y

    def move(self, direction):
        """
        Moves the player in a given direction and handles animation frame updates.
        :param direction: The direction to move ('left', 'right', 'up', 'down')
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
        Handles the shooting mechanics for a player, creating a bullet if the cooldown period has passed.
        :param dx: X-component of the bullet's direction
        :param dy: Y-component of the bullet's direction
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
                self.shooting_cooldown)
            )

    def take_damage(self, damage):
        """
        Decreases the player's health by a specified amount and handles player death if health reaches zero.
        :param damage: Amount of damage to apply to the player
        """
        self.hp -= damage
        if self.hp <= 0:
            self.hp = 0


class Bullet:
    def __init__(self, x, y, dx, dy, radius, damage, owner, lifespan):
        """
        Initializes a new bullet with specific attributes and position.
        :param x: Initial x-coordinate of the bullet
        :param y: Initial y-coordinate of the bullet
        :param dx: X-component of the bullet's movement
        :param dy: Y-component of the bullet's movement
        :param radius: Radius of the bullet
        :param damage: Damage the bullet can inflict
        :param owner: The player or character that fired the bullet
        :param lifespan: How long the bullet exists before disappearing
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

        self.rect = pygame.Rect(x - radius, y - radius, radius * 2, radius * 2)

    def move(self):
        """
        Updates the bullet's position and decreases its lifespan. Also handles collision checks.
        :return: True if the bullet should be removed (either expired lifespan or collided), False otherwise
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

        return did_collide


class Game:
    def __init__(self):
        """
        Initializes the game environment, setting up the map dimensions and camera.
        """
        global MAP_WIDTH, MAP_HEIGHT
        MAP_WIDTH, MAP_HEIGHT = get_image_dimensions(MAP_IMAGE_PATH)
        # screen = pygame.display.set_mode((screen_width, screen_height))
        # self.screen = screen
        self.map_width, self.map_height = get_image_dimensions(MAP_IMAGE_PATH)
        self.players: dict[str, Player] = {}

    def create_player(self, player_id, character_name):
        """
        Creates a new player based on a character name and places them at a random position on the map.
        :param player_id: Identifier for the new player
        :param character_name: Name of the character to base the player on
        :return: Tuple (x, y) representing the position where the player was created
        """

        x, y = self.find_random_free_position(CHARACTER_WIDTH, CHARACTER_HEIGHT)
        if not x:
            logger.error("Didn't found any x,y for the player to be created")
        character = load_character_from_json(CHARACTER_STATS_FILE_PATH, character_name)
        player = Player(
            character,
            x,
            y,
            CHARACTER_WIDTH,
            CHARACTER_HEIGHT
        )
        self.players[player_id] = player
        # logger.info(f"Created new player ({character_name}) in x = {x}, y = {y}")
        # return 20, 30
        return x, y

    def find_random_free_position(self, character_width, character_height):
        """
        Find a random position within the map where an object of the given size can be placed without collision.

        :param character_width: The width of the object to place
        :param character_height: The height of the object to place
        :return: A tuple (x, y) representing the top-left corner of the free area found
        """
        max_attempts = 100  # Limit the number of attempts to find a free spot
        for _ in range(max_attempts):
            x = random.randint(0, MAP_WIDTH - character_width)
            y = random.randint(0, MAP_HEIGHT - character_height)

            if check_collision(x, y, character_width, character_height, True):
                return x, y  # Found a free spot

        # If no free spot is found after max_attempts
        return 100, 50

    def delete_player(self, player_id):
        """
        Removes a player from the game based on their identifier.
        :param player_id: Identifier of the player to remove
        """

        if player_id in self.players:
            del self.players[player_id]

    def set_cords(self, player_id, x, y):
        """
        Sets new coordinates for a player identified by player_id.

        :param player_id: Identifier of the player
        :param x: New x-coordinate
        :param y: New y-coordinate
        """
        if player_id in self.players:
            self.players[player_id].set_cords(x, y)

    def shoot_player(self, player_id, dx, dy):
        """
        Triggers the shooting mechanism for a specific player.
        :param player_id: Identifier of the shooting player
        :param dx: X-component of the bullet's direction
        :param dy: Y-component of the bullet's direction
        """

        if player_id in self.players:
            self.players[player_id].shoot(dx, dy)

    def update_bullets(self):
        """
        Updates the positions of all bullets, checks for hits, and manages out-of-bounds bullets.
        :return: bullet_hits: List of bullet hits including the impacted player IDs and the damage dealt
        """

        bullet_hits = []
        for player_id, player in self.players.items():
            for bullet in player.bullets[:]:
                bullet.move()  # Assuming 'move' method updates the bullet's position

                # Check if the bullet is out of bounds or hits another player
                if not self.within_bounds(bullet):
                    player.bullets.remove(bullet)
                hit_player_id = self.check_bullet_hit(player_id, bullet)
                if hit_player_id:
                    player.bullets.remove(bullet)
                    logger.info(f"Detected player hit! on player id {hit_player_id}")
                    bullet_hits.append((hit_player_id, bullet.damage))

        return bullet_hits

    def within_bounds(self, bullet):
        """
        Checks whether a bullet's position is within the bounds of the map.

        :param bullet: The bullet to check
        :return: True if the bullet is within the map bounds, otherwise False
        """

        return 0 <= bullet.x <= self.map_width and 0 <= bullet.y <= self.map_height

    def check_bullet_hit(self, shooter_id, bullet):
        """
        Checks if a bullet has hit any player except the shooter.
        :param shooter_id: ID of the player who shot bullet
        :param bullet: The bullet to check for hits
        :return: ID of the player hit by the bullet, if any
        """

        for player_id, player in self.players.items():
            if player_id != shooter_id and player.rect.collidepoint(bullet.x, bullet.y):
                player.take_damage(bullet.damage)
                return player_id  # Bullet hit a player
        return None  # No hit detected

    def get_player(self, player_id):
        """
        Retrieves a player object based on player ID.
        :param player_id: ID of the player to retrieve
        :return: The Player object associated with the given ID
        """

        return self.players[player_id]


def load_character_from_json(file_path, name):
    """
    Loads character data from a JSON file and creates a Character object.
    :param file_path: Path to the JSON file containing character data
    :param name: Name of the character to load
    :return: A Character object with data loaded from the file
    """

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
    """
    Calculates the dimensions of an image.
    :param image_path: Path to the image file
    :return: Tuple (width, height) representing the dimensions of the image
    """

    with Image.open(image_path) as img:
        width, height = img.size
    return width, height


def check_collision(x, y, width, height, is_player):
    """
    Checks for collision at specified coordinates with specified dimensions, using different collision maps based on the entity type.
    :param x: X-coordinate of the top-left corner to check
    :param y: Y-coordinate of the top-left corner to check
    :param width: Width of the area to check
    :param height: Height of the area to check
    :param is_player: True if checking for player collisions, False for bullet collisions
    :return: True if a collision is detected, False otherwise
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
    Determines if a given point collides with an obstacle on the map, based on whether it's a player or a bullet.
    :param x: X-coordinate of the point to check
    :param y: Y-coordinate of the point to check
    :param is_player: True if the point is related to a player, False if related to a bullet
    :return: True if there is a collision at the specified point, otherwise False
    """

    try:
        int_x = int(x)
        int_y = int(y)
        if is_player:
            pixel_color = player_collision_map.getpixel((int_x, int_y))
        else:
            pixel_color = bullet_collision_map.getpixel((int_x, int_y))
        alpha = pixel_color[3]
        return not alpha == 0
    except Exception as e:
        return True
