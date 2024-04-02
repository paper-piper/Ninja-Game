import socket
import json
import pygame
import GameLogic
from threading import Thread
import logging
from queue import Queue


logging.basicConfig(
    filename='server.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s - Line: %(lineno)d',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("server")

SERVER_IP = '127.0.0.1'
SERVER_PORT = 12345

MOVE_PLAYER = "move"
SHOOT_PLAYER = "shot"
CREATE_PLAYER = "player_init"

CHARACTER_NAME = "DarkNinja"


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
        message = {'type': CREATE_PLAYER, 'character_name': character_name}
        self.send_message(message)

    def get_character_name(self):
        """
        Prompt the user to enter a character name.
        :return: The character name chosen by the user
        """
        return CHARACTER_NAME

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

        # Example shooting action on space key press
        if keys[pygame.K_SPACE]:
            self.send_shoot_action(45)  # Example angle

    def send_move_action(self, direction):
        """
        Send a move action to the server.
        :param direction: The direction to move (e.g., 'up', 'down', 'left', 'right')
        """
        message = {'type': MOVE_PLAYER, 'direction': direction}
        self.send_message(message)

    def send_shoot_action(self, angle):
        """
        Send a shoot action to the server.
        :param angle: The angle at which to shoot
        """
        message = {'type': SHOOT_PLAYER, 'angle': angle}
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
        while self.running:
            if not self.action_queue.empty():
                action = self.action_queue.get()
                # Process the action received from the server
                logger.info(f"Processing action: {action}")
                # Example processing logic
                if action['type'] == MOVE_PLAYER:
                    self.game.move_player()
                elif action['type'] == SHOOT_PLAYER:
                    # Handle shoot player action
                    pass

    def run_game_loop(self):
        while True:
            # Process actions from the queue
            while not self.action_queue.empty():
                player_id, action = self.action_queue.get()
                logger.info(f"Received new action! from player id: {player_id}, action: {action}")
                self.process_action(player_id, action)

            # self.handle_camera_movement()

            # Update the game state
            self.game.update()
            pygame.time.Clock().tick(60)

    def start(self):
        """
        Start the client, connect to the server, and begin the game loop.
        """
        Thread(target=self.run_game_loop).start()

        self.connect_to_server()
        character_name = self.get_character_name()
        self.send_character_init(character_name)

        for _ in range(2):
            self.send_move_action("right")
            pygame.time.Clock().tick(120)
        while self.running:
            self.handle_key_events()
            self.receive_game_update()
            pygame.time.delay(50)  # To prevent too rapid execution


if __name__ == "__main__":
    client = GameClient()
    client.start()
