import socket
import json
import uuid
import pygame
from threading import Thread
import GameLogic
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


class CommandsServer:
    def __init__(self):
        self.game_logic = GameLogic

    def start_server(self):
        # start listening
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((SERVER_IP, SERVER_PORT))
        server_socket.listen()

        # TODO: run the game on another thread, and update it according to the clients
        # Currently the following line stucks the game
        self.game_logic.start_game()

        while True:
            client_socket, address = server_socket.accept()
            # TODO: determent the player ID system
            player_id = str(uuid.uuid4())
            character_data = self.get_character_name(client_socket)
            # TODO: use the GameLogic file to add player

            # handle client inputs
            Thread(target=self.handle_client, args=(client_socket, player_id)).start()

    def get_character_name(self, client_socket):
        # Assuming the client sends character name immediately after connection
        message = self.receive_message(client_socket)
        character_name = message.get("character_name", "Default Character")
        return character_name

    def handle_client(self, client_socket, player_id):
        while True:
            try:
                message = self.receive_message(client_socket)
                if message:
                    self.process_action(player_id, message)
            except Exception as e:
                print(f"Error handling client {player_id}: {e}")
                break
        self.cleanup_client(player_id, client_socket)

    def process_action(self, player_id, message):
        # TODO: use the self.game_logic to process the action (move player, shoot player...)
        pass

    def cleanup_client(self, player_id, client_socket):
        client_socket.close()
        # TODO: remove the player from the gamelogic object

    def broadcast_game_state(self):
        state = self.game_logic.get_game_state()
        for player_id, client_socket in self.game_logic.players.items():
            self.send_message(client_socket, state)

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
