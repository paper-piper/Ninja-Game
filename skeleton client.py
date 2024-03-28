# Client code
import pygame
import socket
import threading
import json

SERVER_IP = '127.0.0.1'
SERVER_PORT = 12345

# Create a client socket and connect to the server
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect((SERVER_IP, SERVER_PORT))

other_players = {}  # Dictionary to store other players by some unique ID (e.g., their address)


def receive_data():
    while True:
        try:
            # Receive data from the server
            data = client_socket.recv(1024).decode()
            if not data:
                break

            # Deserialize the JSON string
            player_data = json.loads(data)

            # Update the corresponding 'OtherPlayer' object's position
            player_id = player_data['id']
            if player_id not in other_players:
                # This is a new player, so we create a new 'OtherPlayer' instance
                other_players[player_id] = OtherPlayer(...)  # Initialize with received data
            else:
                # Update the existing player's position
                other_players[player_id].update_position(player_data['position'])

        except:
            break


# Start the thread to receive data from the server
thread = threading.Thread(target=receive_data)
thread.start()

# Main game loop
running = True
while running:
    # Your existing game loop logic here...
    # For example, handling local player input and sending it to the server:

    keys = pygame.key.get_pressed()
    if keys[pygame.K_w]:  # Just an example with one key
        # Send player's new position to the server
        player_position = {'x': Player.x, 'y': Player.y}
        client_socket.send(json.dumps(player_position).encode())

    # Then you'd have logic here to draw other players
    for other_player in other_players.values():
        other_player.draw()

pygame.quit()


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
        if check_collision(self.x + dx, self.y + dy, self.width, self.height):
            self.x += dx
            self.y += dy

        self.rect.x = self.x
        self.rect.y = self.y

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


class ExternalPlayer(Player):
    def __init__(self, character, x, y, width, height, target_player):
        super().__init__(character, x, y, width, height)
        self.target_player = target_player
        self.destination = self.choose_destination()
        self.shoot_distance = 20

    def choose_destination(self):
        # Choose a random destination on the map
        while True:
            x = random.randint(0, MAP_WIDTH - self.width)
            y = random.randint(0, MAP_HEIGHT - self.height)
            if check_collision(x, y, self.width, self.height):
                return x, y

    def move_towards_destination(self):
        dx, dy = 0, 0

        distance_x = abs(self.destination[0] - self.x)
        distance_y = abs(self.destination[1] - self.y)

        if distance_x > distance_y:  # Prioritize horizontal movement
            if self.x < self.destination[0]:
                dx = self.speed
            elif self.x > self.destination[0]:
                dx = -self.speed
        else:  # Prioritize vertical movement
            if self.y < self.destination[1]:
                dy = self.speed
            elif self.y > self.destination[1]:
                dy = -self.speed

        return dx, dy

    def move(self, camera):
        dx, dy = self.move_towards_destination()

        # Check if AI has reached its destination or if the destination is blocked
        if (self.x, self.y) == self.destination or not check_collision(self.x + dx, self.y + dy, self.width, self.height):
            self.destination = self.choose_destination()

        # Update the direction based on movement
        if dx > 0:
            self.direction = 'right'
        elif dx < 0:
            self.direction = 'left'
        elif dy > 0:
            self.direction = 'down'
        elif dy < 0:
            self.direction = 'up'

        # Update position and animation
        if dx != 0 or dy != 0:
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
            self.bullets.append(Bullet(self.x + self.width // 2, self.y + self.height // 2, dx, dy, 3, self.bullet_damage, self, self.shooting_cooldown, self.bullet_image))

    def random_action(self):
        if random.random() < SHOOTING_CHANCE:  # Chance to shoot at player
            self.shoot_at_player()
