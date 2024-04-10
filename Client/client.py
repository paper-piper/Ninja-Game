import random
import socket
import json
import pygame
import GameLogic
from threading import Thread
import logging
from queue import Queue

logging.basicConfig(
    filename='client.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s - Line: %(lineno)d',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("client")

SERVER_IP = '127.0.0.1'
SERVER_PORT = 12345

# Client actions
MOVE_PLAYER = "move"
SHOOT_PLAYER = "shot"
CREATE_PLAYER = "player_init"

# Server response keys
ACTION_TYPE = 'type'
ACTION_PARAMETERS = 'action_parameters'
PLAYER_ID = 'player_id'

character = "DarkNinja"


class GameClient:
    def __init__(self):
        """
        Initialize the client with the server's IP address and port, and set up game and networking components.
        """
        self.game = GameLogic.Game()
        self.server_ip = SERVER_IP
        self.server_port = SERVER_PORT
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.settimeout(0.2)  # Set the timeout to a small amount
        self.running = True
        self.action_queue = Queue()

    def connect_to_server(self):
        """
        Establish a connection to the game server using a TCP socket.
        """
        try:
            self.client_socket.connect((self.server_ip, self.server_port))
            logger.info("Connected to server successfully.")
        except socket.error as e:
            logger.error(f"Socket error occurred: {e}")
        except Exception as e:
            logger.exception(f"Failed to connect to server: {e}")

    def get_character_name(self):
        """
        Retrieve the character name selected by the user.
        :return string: The character name chosen by the user
        """
        return character

    def handle_key_events(self):
        """
        Process keyboard events and send appropriate actions to the server based on key presses.
        """
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.send_shoot_action(*self.game.get_mouse_angle())
        keys = pygame.key.get_pressed()
        if keys[pygame.K_a]:
            self.send_move_action('left')
        elif keys[pygame.K_d]:
            self.send_move_action('right')
        elif keys[pygame.K_w]:
            self.send_move_action('up')
        elif keys[pygame.K_s]:
            self.send_move_action('down')

    def send_character_init(self, character_name):
        """
        Send the initial character choice to the server.
        :param character_name: The name of the character chosen by the user
        """
        message = {'type': CREATE_PLAYER, 'action_parameters': [character_name]}
        self.send_message(message)

    def send_move_action(self, direction):
        """
        Send a movement action to the server, indicating the direction the player wishes to move.
        :param direction: The direction to move (e.g., 'up', 'down', 'left', 'right')
        """
        message = {'type': MOVE_PLAYER, 'action_parameters': [direction]}
        self.send_message(message)

    def send_shoot_action(self, dx, dy):
        """
        Send a shoot action to the server, indicating the direction of the shot.
        :param dx: the x vector
        :param dy: the y vector
        """
        message = {'type': SHOOT_PLAYER, 'action_parameters': [dx, dy]}
        self.send_message(message)

    def send_message(self, message):
        """
        Serialize and send a message to the server.
        :param message: The message dictionary to send
        """
        try:
            message_str = json.dumps(message)
            message_length = len(message_str)
            self.client_socket.sendall(message_length.to_bytes(4, byteorder='big') + message_str.encode())
            logger.info(f"Sent message: {message}")
        except socket.error as e:
            logger.error(f"Socket error during message sending: {e}")
        except Exception as e:
            logger.error(f"Failed to send message: {e}")

    def receive_game_update(self):
        """
        Receive and process the updated game state from the server.
        """
        try:
            header = self.client_socket.recv(4)
            if not header:
                return
            message_length = int.from_bytes(header, byteorder='big')
            message = self.client_socket.recv(message_length)
            if not message:
                return
            game_update = json.loads(message.decode())
            self.action_queue.put(game_update)
            logger.info(f"Received action from server: {game_update}")
        except socket.error:
            # happens all the time, don't need to worry
            return
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
        except Exception as e:
            logger.error(f"Error receiving game state: {e}")

    def process_action_queue(self):
        """
        Process all pending actions from the server, updating game state accordingly.
        """
        try:
            action = self.action_queue.get()
            action_type = action.get(ACTION_TYPE)
            action_parameters = action.get(ACTION_PARAMETERS, [])
            player_id = action.get(PLAYER_ID)

            if action_type == CREATE_PLAYER:
                self.game.create_player(player_id, *action_parameters)
            elif action_type == MOVE_PLAYER:
                self.game.move_player(player_id, *action_parameters)
            elif action_type == SHOOT_PLAYER:
                self.game.shoot_player(player_id, *action_parameters)
        except Exception as e:
            logger.error(f"Error processing action queue: {e}")

    def run_game_loop(self):
        try:
            while self.running:
                while not self.action_queue.empty():
                    self.process_action_queue()
                self.game.update()
                pygame.time.Clock().tick(60)
        except Exception as e:
            logger.error(f"Error running game loop: {e}")

    def start(self):
        """
        Initialize the game, connect to the server, and start the main game loop.
        """
        try:
            Thread(target=self.run_game_loop).start()

            self.connect_to_server()
            character_name = self.get_character_name()
            self.send_character_init(character_name)
            pygame.init()
            while self.running:
                self.handle_key_events()
                self.receive_game_update()
        except Exception as e:
            logger.error(f"Error in main game loop: {e}")


if __name__ == "__main__":
    if random.randint(1,3) == 1:
        character = 'Eskimo'
    client = GameClient()
    client.start()