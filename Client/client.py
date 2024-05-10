import socket
import json
import time
import pygame
import GameMenu
import Game
from threading import Thread
import logging
from queue import Queue
import ast


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
MOVE_PLAYER = 'move'
SHOOT_PLAYER = 'shoot'
PLAYER_INIT = 'player_init'
HIT_PLAYER = 'hit'

# Server response keys
ACTION_TYPE = 'type'
ACTION_PARAMETERS = 'action_parameters'
PLAYER_ID = 'player_id'

UPDATE_DELAY = 0.2


class GameClient:
    def __init__(self, character_name, update_delay, audio) -> None:
        """
        Initialize the client with the server's IP address and port, and set up game and networking components.
        :param character_name: the character in-game which you will play
        :param update_delay: the delay between each movement update
        :param audio: a bool which determent if to mute the game audio
        """
        self.game = Game.Game(audio)
        self.server_ip = SERVER_IP
        self.server_port = SERVER_PORT
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.running = True
        # the amount of seconds which the client will update the server
        self.update_delay = update_delay
        self.action_queue = Queue()
        self.character_name = character_name
        self.target_positions = {}

    def send_character_init(self, character_name) -> None:
        """
        Send the initial character choice to the server.
        :param character_name: The name of the character chosen by the user
        """
        message = {'type': PLAYER_INIT, 'action_parameters': [character_name]}
        self.send_message(message)

    def send_move_action(self, x, y) -> None:
        """
        Send a movement action to the server, indicating the direction the player wishes to move.
        :param x:
        :param y:
        :return:
        """
        message = {'type': MOVE_PLAYER, 'action_parameters': [x, y]}
        self.send_message(message)

    def send_shoot_action(self, dx, dy) -> None:
        """
        Send a shoot action to the server, indicating the direction of the shot.
        :param dx: the x vector
        :param dy: the y vector
        """
        message = {'type': SHOOT_PLAYER, 'action_parameters': [dx, dy]}
        self.send_message(message)

    def send_message(self, message) -> None:
        """
        Serialize and send a message to the server.
        :param message: The message dictionary to send
        """
        try:
            message_str = json.dumps(message)
            message_length = len(message_str)
            full_message = str(message_length) + message_str
            self.client_socket.sendto(message_str.encode(), (self.server_ip, self.server_port))
            # logger.info(f"Sent message: {message}")
        except socket.error as e:
            logger.error(f"Socket error during message sending: {e}")
        except json.JSONEncoder as e:
            logger.error(f"JSON encode error during message sending: {e}")

    def receive_game_update(self) -> None:
        """
        Receive and process the updated game state from the server.
        """
        try:
            message, _ = self.client_socket.recvfrom(1024)
            game_update = json.loads(message.decode())
            if validate_json_game_update(game_update):
                self.action_queue.put(game_update)
        except socket.timeout as st:
            logger.error(f"Socket timeout error: {st}")
        except Exception as ae:
            logger.error(f"Error receiving game state: {ae}.")

    def handle_key_events(self) -> None:
        """
        Process keyboard events and update the game object accordingly
        """
        try:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.send_shoot_action(*self.game.get_mouse_angle())
            keys = pygame.key.get_pressed()
            if keys[pygame.K_a]:
                # '0' means the client's player
                self.game.move_player('0', 'left')
            elif keys[pygame.K_d]:
                self.game.move_player('0', 'right')
            elif keys[pygame.K_w]:
                self.game.move_player('0', 'up')
            elif keys[pygame.K_s]:
                self.game.move_player('0', 'down')
        except pygame.error as e:
            logger.error(f"Pygame error in handling key events: {e}")

    def handle_movements(self) -> None:
        """
        in each tick of the game, move each player by a bit to the actual position
        :return:
        """
        try:
            for player_id, (target_x, target_y) in self.target_positions.items():
                current_x, current_y = self.game.players[player_id].x, self.game.players[player_id].y
                # Determine the direction to move based on target position
                if target_x > current_x:
                    self.game.move_player(player_id, 'right')
                elif target_x < current_x:
                    self.game.move_player(player_id, 'left')

                if target_y > current_y:
                    self.game.move_player(player_id, 'down')
                elif target_y < current_y:
                    self.game.move_player(player_id, 'up')
        except KeyError as a:
            logger.error(f"Key error in handling movements: {a}")

    def process_action_queue(self) -> None:
        """
        Process all pending actions from the server, updating game state accordingly.
        """
        try:
            while not self.action_queue.empty():
                action = self.action_queue.get()
                action_type = action.get(ACTION_TYPE)
                action_params = action.get(ACTION_PARAMETERS, [])
                player_id = action.get(PLAYER_ID)

                if action_type == PLAYER_INIT:
                    logger.info(f"Got the player from server! {action_params[0], action_params[1], action_params[2]}")
                    self.game.create_player(player_id, *action_params)

                elif action_type == MOVE_PLAYER and player_id != '0':
                    x, y = action_params[0], action_params[1]
                    self.target_positions[player_id] = (x, y)

                elif action_type == SHOOT_PLAYER:
                    self.game.shoot_player(player_id, *action_params)

                elif action_type == HIT_PLAYER:
                    self.game.players[player_id].take_damage(action_params[0])
                    print(f"He was shot! {action_params}")
        except KeyError as keyrr:
            logger.error(f"Key error processing action queue: {keyrr}")

    def send_player_state(self):
        """
        in every update delay, send the player coordinates
        :return:
        """
        while self.running:
            if self.game.player:
                x, y = self.game.player.x, self.game.player.y
                self.send_move_action(x, y)
                time.sleep(self.update_delay)

    def get_server_updates(self):
        while self.running:
            self.receive_game_update()

    def start(self):
        """
        Initialize the game, connect to the server, and start the main game loop.
        """
        try:
            # All the threads are dependent on the self.running variable
            # constantly get updates from server and push methods into the action queue
            Thread(target=self.get_server_updates).start()
            self.send_character_init(self.character_name)

            # every 0.2 second send the player's x and y coordinate
            Thread(target=self.send_player_state).start()

            # every tick, update the game state according to user input and actions from server
            while self.running:
                self.process_action_queue()
                self.handle_key_events()
                self.handle_movements()

                # if the game ended, stop all the threads
                is_over = self.game.update()
                if is_over:
                    self.running = False
                    return
                pygame.time.Clock().tick(60)
        except Exception as exp:
            logger.error(f"Unhandled exception in start method: {exp}")


def validate_json_game_update(game_update):
    if not isinstance(game_update, dict):
        logger.error("Message is not a dictionary")
        return False

    if ACTION_TYPE not in game_update or game_update[ACTION_TYPE] not in [MOVE_PLAYER,
                                                                          SHOOT_PLAYER,
                                                                          PLAYER_INIT,
                                                                          HIT_PLAYER]:
        logger.error("Invalid or missing 'type' in message")
        return False

    if ACTION_PARAMETERS not in game_update:
        logger.error("Missing 'action_parameters' in message")
        return False

    if PLAYER_ID not in game_update:
        logger.error("Missing 'PLAYER_ID' in message")
        return False

    return True


if __name__ == "__main__":
    valid_message = {
        ACTION_TYPE: PLAYER_INIT,
        ACTION_PARAMETERS: "[DarkNinja, 20, 30]",
        PLAYER_ID: 123
    }
    invalid_message = {
        ACTION_TYPE: MOVE_PLAYER,
        ACTION_PARAMETERS: "[2, 3]",
    }  # doesn't have player id
    assert validate_json_game_update(valid_message)
    assert not validate_json_game_update(invalid_message)
    pygame.init()
    try:
        menu = GameMenu.Menu()
        settings, character = menu.run()
        client = GameClient(character, UPDATE_DELAY, settings['sound'] == 'on')
        client.start()
        pygame.quit()
    except Exception as main_loop_exception:
        logger.error(f"Unhandled exception in main loop: {main_loop_exception}")
