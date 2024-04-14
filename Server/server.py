import socket
import json
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


# --------------------------------------- Constants -------------------------------------------------

SERVER_IP = '127.0.0.1'
SERVER_PORT = 12345

# Server actions
MOVE_PLAYER = "move"
SHOOT_PLAYER = "shot"
CREATE_PLAYER = "player_init"
PLAYER_INIT = "player_init"
HIT_PLAYER = "hit"
WIN_PLAYER = "win"


class CommandsServer:
    def __init__(self):
        self.game = GameLogic.Game()
        self.action_queue = Queue()
        self.clients = {}
        self.id_counter = 1   # starts from 1, since id zero is saved for acknowledge messages

    def start_server(self):
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
            # handle client inputs
            Thread(target=self.handle_client, args=(client_socket, )).start()

    def run_game_loop(self):
        while True:
            while not self.action_queue.empty():
                player_id, action = self.action_queue.get()
                self.process_action(player_id, action)

            self.game.update()
            pygame.time.Clock().tick(60)

    def handle_client(self, client_socket):
        # before adding the client, send to him all the current clients.
        for other_client_id, other_client_socket in self.clients.items():
            player = self.game.get_player(other_client_id)
            action = {'type': PLAYER_INIT,
                      'action_parameters': [player.name, player.x, player.y],
                      'player_id': other_client_id
                      }
            self.send_message(client_socket, action)
        player_id = self.id_counter
        self.id_counter += 1
        self.clients[player_id] = client_socket
        try:
            while True:
                message = self.receive_message(client_socket)
                if message:
                    self.action_queue.put((player_id, message))
                    # logger.info(f"Received message grom client id: {player_id}. message: {message}")
        except Exception as e:
            logger.error(f"Error handling client {player_id}: {e}")
        finally:
            self.cleanup_client(player_id)

    def process_action(self, player_id, action):
        try:
            action_type = action['type']
            if action_type == MOVE_PLAYER:
                player_x, player_y = action['action_parameters'][0], action['action_parameters'][1]
                self.game.players[player_id].x = player_x
                self.game.players[player_id].y = player_y
            elif action_type == SHOOT_PLAYER:
                dx, dy = action['action_parameters']  # Unpacking the parameters
                self.game.shoot_player(player_id, dx, dy)

            if action_type == CREATE_PLAYER:
                character_name = action['action_parameters'][0]
                x, y = self.game.create_player(player_id, character_name)
                self.broadcast_game_action(
                    player_id,
                    {'type': action_type, 'action_parameters': [character_name, x, y]}
                )
            else:
                # broadcast the action to all clients
                self.broadcast_game_action(
                    player_id,
                    action
                )

        except Exception as e:
            logger.error(f"caught expedition: {e}")

    def cleanup_client(self, player_id):
        if player_id in self.clients:
            self.clients[player_id].close()
            del self.clients[player_id]
            self.game.delete_player(player_id)

    def broadcast_game_action(self, player_id, action):
        for client_id, client_socket in self.clients.items():
            action_with_id = action.copy()
            action_with_id['player_id'] = '0' if client_id == player_id else player_id
            # logger.info(f"Sent message to client id: {client_id}. the message: {action}")
            self.send_message(client_socket, action_with_id)

    def send_message(self, client_socket, message):
        message_json = json.dumps(message)
        message_length = len(message_json)
        client_socket.sendall(message_length.to_bytes(4, byteorder='big') + message_json.encode())

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
    Thread(target=cmd_server.run_game_loop).start()
    cmd_server.start_server()
