import socket
import json
import pygame

SERVER_IP = '127.0.0.1'
SERVER_PORT = 12345


class GameClient:
    def __init__(self):
        """
        Initialize the client with the server's IP address and port.
        """
        self.server_ip = SERVER_IP
        self.server_port = SERVER_PORT
        self.client_socket = None
        self.running = True

    def connect_to_server(self):
        """
        Establish a connection to the server.
        """
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.client_socket.connect((self.server_ip, self.server_port))
            print("Connected to server successfully.")
        except Exception as e:
            print(f"Failed to connect to server: {e}")

    def send_character_init(self, character_name):
        """
        Send the initial character choice to the server.
        :param character_name: The name of the character chosen by the user
        """
        message = {'type': 'player_init', 'character_name': character_name}
        self.send_message(message)

    def get_character_name(self):
        """
        Prompt the user to enter a character name.
        :return: The character name chosen by the user
        """
        return input("Enter your character name: ")

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
        message = {'type': 'move', 'direction': direction}
        self.send_message(message)

    def send_shoot_action(self, angle):
        """
        Send a shoot action to the server.
        :param angle: The angle at which to shoot
        """
        message = {'type': 'shoot', 'angle': angle}
        self.send_message(message)

    def send_message(self, message):
        """
        Send a message to the server.
        :param message: The message to send (as a dictionary)
        """
        message_str = json.dumps(message)
        message_length = len(message_str)
        self.client_socket.sendall(message_length.to_bytes(4, byteorder='big') + message_str.encode())

    def receive_game_state(self):
        """
        Receive the updated game state from the server.
        """
        # Placeholder for receiving game state updates
        pass

    def start(self):
        """
        Start the client, connect to the server, and begin the game loop.
        """
        self.connect_to_server()
        character_name = self.get_character_name()
        self.send_character_init(character_name)

        while self.running:
            self.handle_key_events()
            self.receive_game_state()

if __name__ == "__main__":
    client = GameClient()
    client.start()
