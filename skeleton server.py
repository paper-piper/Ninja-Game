import socket
import threading
import json

SERVER_IP = '127.0.0.1'
SERVER_PORT = 12345

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_socket.bind((SERVER_IP, SERVER_PORT))
server_socket.listen()

clients = {}
player_states = {}


def handle_client(client_socket, address):
    player_id = address[1]  # Use the client's port number as a simple player ID
    player_states[player_id] = {"x": 0, "y": 0, "hp": 100}  # Initialize player state

    while True:
        try:
            data = client_socket.recv(1024).decode()
            if not data:
                break

            player_data = json.loads(data)
            player_states[player_id].update(player_data)  # Update player's state

            # Broadcast updated player state to all clients
            broadcast({"id": player_id, "state": player_states[player_id]}, client_socket)

        except Exception as e:
            print(f"Error handling client {address}: {e}")
            break

    # Clean up on disconnect
    client_socket.close()
    clients.pop(player_id)
    player_states.pop(player_id)
    broadcast_player_left(player_id)
    print(f"Client {address} disconnected")


def broadcast(message, source_socket):
    message_json = json.dumps(message).encode()
    for client_socket in clients.values():
        if client_socket != source_socket:
            try:
                client_socket.send(message_json)
            except Exception as e:
                print(f"Error broadcasting to {client_socket}: {e}")
                client_socket.close()


def broadcast_player_left(player_id):
    for client_socket in clients.values():
        try:
            client_socket.send(json.dumps({"type": "player_left", "id": player_id}).encode())
        except Exception as e:
            print(f"Error sending player left message: {e}")
            client_socket.close()


def start_server():
    print("Server started on port", SERVER_PORT)
    while True:
        client_socket, address = server_socket.accept()
        clients[address[1]] = client_socket
        print(f"Connection from {address} has been established.")

        threading.Thread(target=handle_client, args=(client_socket, address)).start()


if __name__ == "__main__":
    start_server()
