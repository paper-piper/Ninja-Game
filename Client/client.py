import socket
import json
import pygame
import GameLogic
from threading import Thread
import ast
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
        Initialize the client with the server's IP address and port.
        """
        self.game = GameLogic.Game()
        self.server_ip = SERVER_IP
        self.server_port = SERVER_PORT
        self.client_socket = None
        self.running = True
        self.action_queue = Queue()

    def connect_to_server(self):
        """
        Establish a connection to the server.
        """
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.client_socket.connect((self.server_ip, self.server_port))
            logger.info("Connected to server successfully.")
        except Exception as e:
            logger.exception(f"Failed to connect to server: {e}")

    def send_character_init(self, character_name):
        """
        Send the initial character choice to the server.
        :param character_name: The name of the character chosen by the user
        """
        message = {'type': CREATE_PLAYER, 'action_parameter': character_name}
        self.send_message(message)

    def get_character_name(self):
        """
        Prompt the user to enter a character name.
        :return: The character name chosen by the user
        """
        return character

    def handle_key_events(self):
        """
        Detect and process key events to send move and shoot actions to the server.
        """
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:
            self.send_move_action('left')
        elif keys[pygame.K_RIGHT]:
            self.send_move_action('right')
        elif keys[pygame.K_UP]:
            self.send_move_action('up')
        elif keys[pygame.K_DOWN]:
            self.send_move_action('down')
        if keys[pygame.K_SPACE]:
            self.send_shoot_action(45)  # Example angle

    def send_move_action(self, direction):
        """
        Send a move action to the server.
        :param direction: The direction to move (e.g., 'up', 'down', 'left', 'right')
        """
        message = {'type': MOVE_PLAYER, 'action_parameter': direction}
        self.send_message(message)

    def send_shoot_action(self, angle):
        """
        Send a shoot action to the server.
        :param angle: The angle at which to shoot
        """
        message = {'type': SHOOT_PLAYER, 'action_parameter': angle}
        self.send_message(message)

    def send_message(self, message):
        """
        Send a message to the server.
        :param message: The message to send (as a dictionary)
        """
        message_str = json.dumps(message)
        message_length = len(message_str)
        self.client_socket.sendall(message_length.to_bytes(4, byteorder='big') + message_str.encode())

    def receive_game_update(self):
        """
        Receive the updated game state from the server.
        """
        # Placeholder for receiving game state updates
        try:
            header = self.client_socket.recv(4)
            if not header:
                return None
            message_length = int.from_bytes(header, byteorder='big')
            message = self.client_socket.recv(message_length)
            if not message:
                return None
            game_update = json.loads(message.decode())
            self.action_queue.put(game_update)
            logger.info(f"Received action from server: {game_update}")
        except Exception as e:
            logger.error(f"Error receiving game state: {e}")

    def process_action_queue(self):
        while not self.action_queue.empty():
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

    def start(self):
        """
        Start the client, connect to the server, and begin the game loop.
        """
        pygame.init()  # Ensure pygame is initialized
        self.connect_to_server()
        character_name = self.get_character_name()
        self.send_character_init(character_name)

        while self.running:
            self.handle_key_events()
            self.receive_game_update()
            self.process_action_queue()
            self.game.update()
            pygame.time.Clock().tick(60)  # Control the frame rate


if __name__ == "__main__":
    client = GameClient()
    client.start()
