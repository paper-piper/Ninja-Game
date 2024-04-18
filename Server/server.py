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
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.game = GameLogic.Game()
        self.action_queue = Queue()
        self.clients = {}
        self.id_counter = 1   # starts from 1, since id zero is saved for acknowledge messages

    def start_server(self):
        # Start the game in a separate thread
        Thread(target=self.run_game_loop).start()
        # start listening
        logger.info(f"Server started, listening on {SERVER_IP}:{SERVER_PORT}")
        self.server_socket.bind((SERVER_IP, SERVER_PORT))

        while True:
            # handle client inputs
            message, client_address = self.server_socket.recvfrom(1024)
            client_id = next((k for k, v in self.clients.items() if v == client_address), None)
            if not client_id:
                client_id = self.id_counter
                self.clients[self.id_counter] = client_address  # Register client address
                self.id_counter += 1
            self.action_queue.put((client_id, json.loads(message.decode())))

    def run_game_loop(self):
        while True:
            while not self.action_queue.empty():
                player_id, action = self.action_queue.get()
                self.process_action(player_id, action)

            bullet_hits = self.game.update()
            for bullet_hit in bullet_hits:
                self.handle_hit(bullet_hit)
            pygame.time.Clock().tick(60)

    def handle_hit(self, bullet_hit):
        player_id = bullet_hit[0]
        bullet_damage = bullet_hit[1]
        action = {'type': HIT_PLAYER,
                  'action_parameters': [bullet_damage],
                  }
        self.broadcast_game_action(player_id, action)
        print("Detected and sent hit!")

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
                # after sending the client his own character, send all other clients
                for other_client_id, other_client_socket in self.clients.items():
                    if other_client_id != player_id:
                        player = self.game.get_player(other_client_id)
                        action = {'type': PLAYER_INIT,
                                  'action_parameters': [player.name, player.x, player.y],
                                  'player_id': other_client_id
                                  }
                        self.send_message(self.clients[player_id], action)
            else:
                # broadcast the action to all clients
                self.broadcast_game_action(
                    player_id,
                    action
                )

        except Exception as e:
            logger.error(f"caught expedition: {e}")

    def cleanup_client(self, player_id):
        # TODO: integrate this function when client sends 'close' message or isn't active for some time
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

    def send_message(self, client_address, message):
        message_json = json.dumps(message)
        self.server_socket.sendto(message_json.encode(), client_address)

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
