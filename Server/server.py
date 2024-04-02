import socket
import json
import uuid
import pygame
from threading import Thread
from queue import Queue
import GameLogic
import logging

# Initialize logger
logging.basicConfig(
    filename='server.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s - Line: %(lineno)d',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("server")
# ------------------------------------------ Protocol -----------------------------------------------
"""
From Client to Server
Communication protocol:
<message length>{
  "type": "<action type>",
  "character_name": "<character name>"
}
action types (from client to server):
- player_init
- move
- shot

action types (from server to client):
- player_init
- move
- shot
- hit
- win
- game status
"""

# --------------------------------------- Constants -------------------------------------------------
MOVE_PLAYER = "move"
SHOOT_PLAYER = "shot"
CREATE_PLAYER = "player_init"

SERVER_IP = '127.0.0.1'
SERVER_PORT = 12345
id_counter = 0
clients = {}

MAP_IMAGE_PATH = r'../Assets/Map/detailedMap.png'
collision_image_path = r'../Assets/Map/UpdatedCollisoin.png'
CHARACTER_STATS_FILE_PATH = "../Characters.json"


class CommandsServer:
    def __init__(self):
        self.game = GameLogic.Game()
        self.action_queue = Queue()

    def start_server(self):
        global id_counter
        # Start the game in a separate thread
        Thread(target=self.run_game_loop).start()
        # start listening
        logger.info(f"Server started, listening on {SERVER_IP}:{SERVER_PORT}")
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((SERVER_IP, SERVER_PORT))
        server_socket.listen()

        while True:
            client_socket, address = server_socket.accept()
            player_id = id_counter
            id_counter += 1

            # handle client inputs
            Thread(target=self.handle_client, args=(client_socket, player_id)).start()

    def run_game_loop(self):
        while True:
            # Process actions from the queue
            while not self.action_queue.empty():
                player_id, action = self.action_queue.get()
                logger.info(f"Received new action! from player id: {player_id}, action: {action}")
                self.process_action(player_id, action)
                self.broadcast_game_action(player_id, action)

            # self.handle_camera_movement()

            # Update the game state
            self.game.update()
            pygame.time.Clock().tick(60)

    def handle_camera_movement(self):
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.game.move_camera('left')
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.game.move_camera('right')
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            self.game.move_camera('up')
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            self.game.move_camera('down')

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()

    def get_character_name(self, client_socket):
        """
        get the character name from the client
        :param client_socket:
        :return: None
        """
        # Assuming the client sends character name immediately after connection
        message = self.receive_message(client_socket)
        character_name = message.get("character_name", "Default Character")
        return character_name

    def handle_client(self, client_socket, player_id):
        logger.info(f"New client connected with id: {player_id}")
        init_message = self.receive_message(client_socket)
        logger.info(f"Client with id: {player_id} send init message: {init_message}")
        self.action_queue.put((player_id, init_message))
        while True:
            try:
                message = self.receive_message(client_socket)
                if message:
                    self.action_queue.put((player_id, message))
            except Exception as e:
                print(f"Error handling client {player_id}: {e}")
                break
        self.cleanup_client(player_id, client_socket)

    def process_action(self, player_id, action):
        """
        json message example:
        {
          "type": "move_player",
          "character_name": "Dark Ninja"
        }
        :param player_id:
        :param action:
        :return:
        """
        # Process the action (move, shoot, etc.) using the game logic
        if action['type'] == MOVE_PLAYER:
            self.game.move_player(player_id, action['direction'])
        elif action['type'] == SHOOT_PLAYER:
            self.game.shoot_player(player_id, action['angle'])
        elif action['type'] == CREATE_PLAYER:
            logger.info(f"Creating new player with name {action['character_name']}")
            self.game.create_player(player_id, action['character_name'])

    def cleanup_client(self, player_id, client_socket):
        client_socket.close()
        self.game.delete_player(player_id)

    def broadcast_game_action(self, player_id, action):
        for client_id, client_socket in self.game.players.items():
            action_with_id = action.copy()
            action_with_id['player_id'] = player_id
            self.send_message(client_socket, action_with_id)

    def send_message(self, client_socket, message):
        message_json = json.dumps(message)
        message_length = len(message_json)
        header = message_length.to_bytes(4, byteorder='big')
        client_socket.sendall(header + message_json.encode())

    def receive_message(self, client_socket):
        header = client_socket.recv(4)
        if not header:
            return None

        message_length = int.from_bytes(header, byteorder='big')
        message_data = bytearray()

        while len(message_data) < message_length:
            next_byte = client_socket.recv(1)
            if not next_byte:
                raise Exception("Connection lost while receiving the message")
            message_data.extend(next_byte)

        return json.loads(message_data.decode())


if __name__ == "__main__":
    cmd_server = CommandsServer()
    cmd_server.start_server()
