import socket
import json
import uuid
import pygame
from threading import Thread
import math

# ------------------------------------------ Protocol -----------------------------------------------
"""
player input examples (the first four bytes are saved for length):
0016{
  "type": "player_init",
  "character_name": "Dark Ninja"
}
0032{
  "type": "action",
  "action": "move",
  "direction": "up"  // Could be "up", "down", "left", or "right"
}
0035{
  "type": "action",
  "action": "shoot",
  "angle": 45.0  // Angle in degrees or radians depending on implementation
}


"""

# --------------------------------------- Constants -------------------------------------------------
SERVER_IP = '127.0.0.1'
SERVER_PORT = 12345
clients = {}
MAP_IMAGE_PATH = r'Images/Map/detailedMap.png'
collision_image_path = r'Images/Map/UpdatedCollisoin.png'
CHARACTER_STATS_FILE_PATH = "Characters.json"
map_image = pygame.image.load(MAP_IMAGE_PATH).convert_alpha()
collision_map = pygame.image.load(collision_image_path).convert_alpha()


# Helper function for loading character stats
def load_character_from_json(name):
    with open(CHARACTER_STATS_FILE_PATH, 'r') as file:
        data = json.load(file)
    for char_data in data['characters']:
        if char_data['name'] == name:
            return char_data
    raise ValueError(f"No character found with the name {name}")


class CommandsServer:
    def __init__(self):
        self.game_logic = GameLogic()

    def start_server(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((SERVER_IP, SERVER_PORT))
        server_socket.listen()

        # TODO: start running the game
        while True:
            client_socket, address = server_socket.accept()
            # TODO: determent the player ID system
            player_id = str(uuid.uuid4())
            character_data = self.get_player_stats(client_socket)
            self.game_logic.add_player(player_id, character_data)
            Thread(target=self.handle_client, args=(client_socket, player_id)).start()

    def get_player_stats(self, client_socket):
        # Assuming the client sends character name immediately after connection
        message = self.receive_message(client_socket)
        character_name = message.get("character_name", "Default Character")
        # stuff like height, width x and y will be determent by the server.
        character_data = load_character_from_json(character_name)
        return character_data

    def handle_client(self, client_socket, player_id):
        while True:
            try:
                message = self.receive_message(client_socket)
                if message:
                    self.game_logic.process_action(player_id, message)
            except Exception as e:
                print(f"Error handling client {player_id}: {e}")
                break
        self.cleanup_client(player_id, client_socket)

    def cleanup_client(self, player_id, client_socket):
        client_socket.close()
        self.game_logic.remove_player(player_id)

    def broadcast_game_state(self):
        state = self.game_logic.get_game_state()
        for player_id, client_socket in self.game_logic.players.items():
            self.send_message(client_socket, state)

    def send_message(self, socket, message):
        message_json = json.dumps(message)
        message_length = len(message_json)
        header = message_length.to_bytes(4, byteorder='big')
        socket.sendall(header + message_json.encode())

    def receive_message(self, socket):
        header = socket.recv(4)
        if not header:
            return None

        message_length = int.from_bytes(header, byteorder='big')
        message_data = bytearray()

        while len(message_data) < message_length:
            next_byte = socket.recv(1)
            if not next_byte:
                raise Exception("Connection lost while receiving the message")
            message_data.extend(next_byte)

        return json.loads(message_data.decode())


class GameLogic:
    def __init__(self):
        self.players = {}

    def add_player(self, player_id, character):
        # Initialize player and game state
        # TODO: determent stuff like height width x and y
        self.players[player_id] = GameLogic.Player(character, player_id)

    def remove_player(self, player_id):
        # Remove player from game state
        del self.players[player_id]

    def process_action(self, player_id, action):
        # Update game state based on player action
        player = self.players.get(player_id)
        if player and 'action' in action:
            if action['action'] == 'move':
                player.move(action['direction'])
            elif action['action'] == 'shoot':
                player.shoot(action['angle'])

    def get_game_state(self):
        # Return the current state of the game
        return {player_id: player.to_dict() for player_id, player in self.players.items()}

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
        """
        Player class to encapsulate player attributes and methods.
        """

        def __init__(self, character, player_id, x, y):
            # id
            self.id = player_id

            # Position and size
            self.x = x
            self.y = y
            self.width = character.width
            self.height = character.height
            self.rect = pygame.Rect(x, y, character.width, character.height)

            # Movement
            self.speed = character.speed
            self.hp = character.hp

            # Bullet qualities
            self.last_shot_time = 0
            self.bullets = []
            self.bullet_speed = character.bullet_speed
            self.bullet_damage = character.bullet_damage
            self.shooting_cooldown = character.shooting_cooldown

        def move(self, direction):
            dx = dy = 0
            if direction == 'up':
                dy -= self.speed
            elif direction == 'down':
                dy += self.speed
            elif direction == 'left':
                dx -= self.speed
            elif direction == 'right':
                dx += self.speed

            if check_collision(self.x + dx, self.y + dy, self.width, self.height):
                self.x += dx
                self.y += dy
                self.rect.x = self.x
                self.rect.y = self.y

        def to_json(self):
            player_state = {
                "x": self.x,
                "y": self.y,
                "width": self.width,
                "height": self.height,
                "speed": self.speed,
                "hp": self.hp,
                "bullet_speed": self.bullet_speed,
                "bullet_damage": self.bullet_damage,
                "shooting_cooldown": self.shooting_cooldown,
                "bullets": self.bullets,  # Assuming bullets are represented in a way that can be serialized
            }
            return json.dumps(player_state)

        def shoot(self, camera):
            current_time = pygame.time.get_ticks()
            if current_time - self.last_shot_time > self.shooting_cooldown:
                self.last_shot_time = current_time
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
                dx = math.cos(angle) * self.bullet_speed  # Speed of the bullet
                dy = math.sin(angle) * self.bullet_speed  # Speed of the bullet

                # Create and add the new bullet to the bullets list
                self.bullets.append(GameLogic.Bullet(
                    center_x,
                    center_y,
                    dx,
                    dy,
                    3,
                    self.bullet_damage,
                    self,
                    self.shooting_cooldown
                )
                )

    class Bullet:
        def __init__(self, x, y, dx, dy, radius, damage, owner, lifespan):
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
            return did_collide


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


# Start the server
if __name__ == "__main__":
    game_server = CommandsServer()
    game_server.start_server()
