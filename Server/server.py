import socket
import json
import pygame
from threading import Thread, Timer
from queue import Queue
import GameLogic
import logging
import time

# Initialize logger
logging.basicConfig(
    filename='server.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s - Line: %(lineno)d',
    datefmt='%d %H:%M:%S'
)
logger = logging.getLogger("server")


# --------------------------------------- Constants -------------------------------------------------

SERVER_IP = '0.0.0.0'
SERVER_PORT = 12345
DISCONNECT_TIMEOUT = 10  # seconds

# Action types
MOVE_PLAYER = 'move'
SHOOT_PLAYER = 'shoot'
PLAYER_INIT = 'player_init'
HIT_PLAYER = 'hit'

# Action parameters
ACTION_TYPE = 'type'
ACTION_PARAMETERS = 'action_parameters'


class CommandsServer:
    def __init__(self):
        """
        Initialize the server, creating a server socket, game instance, action queue,
        clients dictionary, and ID counter.
        """
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.game = GameLogic.Game()
        self.action_queue = Queue()
        self.clients = {}
        self.last_active = {}  # Stores last activity time for each client
        self.id_counter = 1   # starts from 1, since id zero is saved for acknowledge messages
        self.running = True  # to manage all the threads

    def start_server(self):
        """
        Start the server by initiating the game loop in a separate thread and binding
        the server socket to listen for incoming client messages.
        """
        Thread(target=self.run_game_loop).start()
        # start listening
        logger.info(f"Server started, listening on {SERVER_IP}:{SERVER_PORT}")
        self.server_socket.bind((SERVER_IP, SERVER_PORT))
        self.check_for_timeouts()  # Start the timeout check loop

        while self.running:
            message, client_address = self.server_socket.recvfrom(1024)
            client_id = next((k for k, v in self.clients.items() if v == client_address), None)
            if not client_id:
                client_id = self.id_counter
                self.clients[self.id_counter] = client_address
                self.id_counter += 1

            self.last_active[client_id] = time.time()  # Update last active time
            self.action_queue.put((client_id, json.loads(message.decode())))

    def check_for_timeouts(self):
        current_time = time.time()
        to_remove = []
        for client_id, last_time in self.last_active.items():
            if current_time - last_time > DISCONNECT_TIMEOUT:
                to_remove.append(client_id)

        for client_id in to_remove:
            self.cleanup_client(client_id)
            logger.info(f"Client {client_id} has been disconnected due to inactivity.")
        if self.running:
            Timer(1, self.check_for_timeouts).start()  # Schedule next check in 1 second

    def run_game_loop(self):
        """
        Continuously process game actions from the action queue and update the game state,
        handling any bullet hits that occur.
        """
        while self.running:
            while not self.action_queue.empty():
                player_id, action = self.action_queue.get()
                self.process_action(player_id, action)

            dead_players, bullet_hits = self.game.update_bullets()
            for bullet_hit in bullet_hits:
                self.handle_hit(bullet_hit)
            for dead_player_id in dead_players:
                self.handle_dead(dead_player_id)
            pygame.time.Clock().tick(60)

    def handle_dead(self, dead_player_id):
        logger.info(f"A player has died! with id ({dead_player_id})")
        # TODO: make player dead and then check for game over. if the game is over reset the server

    def handle_hit(self, bullet_hit):
        """
        Process a bullet hit by determining the impacted player and sending the damage
        action to all clients.
        :param bullet_hit: a tuple containing the player ID and the bullet damage
        """
        player_id = bullet_hit[0]
        bullet_damage = bullet_hit[1]
        action = {'type': HIT_PLAYER,
                  'action_parameters': [bullet_damage],
                  }
        self.broadcast_game_action(player_id, action)
        print("Detected and sent hit!")

    def process_action(self, player_id, action):
        """
        Handle an action received from a client based on the action type (e.g., move, shoot,
        or create player), and propagate it to relevant clients or update game state accordingly.
        :param player_id: the unique ID of the player who initiated the action
        :param action: the data received
        """
        try:
            action_type = action[ACTION_TYPE]
            if action_type == MOVE_PLAYER:
                player_x, player_y = action[ACTION_PARAMETERS][0], action[ACTION_PARAMETERS][1]
                self.game.set_cords(player_id, player_x, player_y)
            elif action_type == SHOOT_PLAYER:
                dx, dy = action[ACTION_PARAMETERS]  # Unpacking the parameters
                self.game.shoot_player(player_id, dx, dy)

            if action_type == PLAYER_INIT:
                self.handle_player_init(action, action_type, player_id)
            else:
                # Broadcast the action to all clients
                self.broadcast_game_action(
                    player_id,
                    action
                )

        except Exception as e:
            logger.error(f"caught expedition: {e}")

    def handle_player_init(self, action, action_type, player_id):
        """
        send the client his own character, and all the other client
        :param action:
        :param action_type:
        :param player_id:
        :return:
        """
        character_name = action[ACTION_PARAMETERS][0]
        x, y = self.game.create_player(player_id, character_name)
        logger.info(f"Created player named {character_name} in: {x},{y}")
        self.broadcast_game_action(
            player_id,
            {ACTION_TYPE: action_type, ACTION_PARAMETERS: [character_name, x, y]}
        )
        # After sending the client his own character, send all other clients
        for other_client_id, other_client_socket in self.clients.items():
            if other_client_id != player_id:
                player = self.game.get_player(other_client_id)
                action = {ACTION_TYPE: PLAYER_INIT,
                          ACTION_PARAMETERS: [player.name, player.x, player.y],
                          'player_id': other_client_id
                          }
                self.send_message(self.clients[player_id], action)

    def cleanup_client(self, player_id):
        """
        Clean up a client's data from the server, typically called when a client disconnects or
        sends a 'close' message.
        :param player_id: the unique ID of the client to clean up
        """
        if player_id in self.clients:
            del self.clients[player_id]
            del self.last_active[player_id]
            self.game.delete_player(player_id)
            logger.info(f"Cleaned up data for disconnected client {player_id}.")

    def broadcast_game_action(self, player_id, action):
        """
        Broadcast a game action to all connected clients, including details of the player
        and the action to be taken.
        :param player_id: the unique ID of the player associated with the action
        :param action: the data to be broadcast
        """
        for client_id, client_socket in self.clients.items():
            action_with_id = action.copy()
            action_with_id['player_id'] = '0' if client_id == player_id else player_id
            # logger.info(f"Sent message to client id: {client_id}. the message: {action}")
            self.send_message(client_socket, action_with_id)

    def send_message(self, client_address, message):
        """
        Send a message to a specific client using their address.
        :param client_address: the socket address of the client
        :param message: the message data to be sent, in JSON format
        """
        message_json = json.dumps(message)
        self.server_socket.sendto(message_json.encode(), client_address)


if __name__ == "__main__":
    cmd_server = CommandsServer()
    cmd_server.start_server()
